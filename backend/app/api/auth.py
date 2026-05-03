import hashlib
import hmac
import json
import logging
from urllib.parse import parse_qsl

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.settings import get_settings
from app.models import User

log = logging.getLogger(__name__)


def _verify_init_data(init_data: str, bot_token: str) -> dict[str, str]:
    """Validate Telegram WebApp initData per https://core.telegram.org/bots/webapps#validating-data."""
    parsed = dict(parse_qsl(init_data, keep_blank_values=True))
    received_hash = parsed.pop("hash", None)
    if not received_hash:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "missing hash")

    data_check_string = "\n".join(
        f"{k}={v}" for k, v in sorted(parsed.items())
    )
    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    expected = hmac.new(
        secret_key, data_check_string.encode(), hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(expected, received_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "bad signature")

    return parsed


async def _upsert_user(
    session: AsyncSession,
    *,
    tg_user_id: int,
    tg_username: str | None = None,
    first_name: str | None = None,
) -> User:
    result = await session.execute(select(User).where(User.tg_user_id == tg_user_id))
    user = result.scalar_one_or_none()
    if user is None:
        user = User(
            tg_user_id=tg_user_id,
            tg_username=tg_username,
            first_name=first_name,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
    return user


async def current_user(
    authorization: str | None = Header(default=None),
    session: AsyncSession = Depends(get_session),
) -> User:
    settings = get_settings()

    if settings.dev_fake_user_id:
        return await _upsert_user(
            session,
            tg_user_id=settings.dev_fake_user_id,
            tg_username="dev",
            first_name="Dev",
        )

    if not authorization or not authorization.startswith("tma "):
        log.warning(
            "auth: missing/bad header — got %r",
            (authorization[:20] + "...") if authorization else None,
        )
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "missing tma auth header")

    init_data = authorization.removeprefix("tma ").strip()
    try:
        parsed = _verify_init_data(init_data, settings.bot_token)
    except HTTPException as e:
        log.warning("auth: %s — initData prefix=%r", e.detail, init_data[:60])
        raise

    user_json = parsed.get("user")
    if not user_json:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "no user in initData")
    tg = json.loads(user_json)

    return await _upsert_user(
        session,
        tg_user_id=int(tg["id"]),
        tg_username=tg.get("username"),
        first_name=tg.get("first_name"),
    )
