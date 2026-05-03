import asyncio
import logging
from contextlib import asynccontextmanager

from aiogram.types import Update
from fastapi import FastAPI, Header, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware

from app.api.fit import router as fit_router
from app.api.model import router as model_router
from app.api.popular import router as popular_router
from app.api.routes import router as api_router
from app.api.search import router as search_router
from app.bot.bot import build_bot, build_dispatcher
from app.core.settings import get_settings

log = logging.getLogger("printscout")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()

    if settings.dev_fake_user_id:
        log.warning(
            "!!! DEV_FAKE_USER_ID=%s — Telegram auth is BYPASSED. "
            "MUST be unset in production. !!!",
            settings.dev_fake_user_id,
        )

    bot = build_bot() if settings.bot_token else None
    dp = build_dispatcher() if bot else None
    app.state.bot = bot
    app.state.dp = dp

    polling_task: asyncio.Task | None = None

    if bot and dp:
        if settings.public_base_url.startswith("https://"):
            await bot.set_webhook(
                url=settings.webhook_url,
                secret_token=settings.webhook_secret,
                drop_pending_updates=True,
            )
            log.info("bot: webhook mode at %s", settings.webhook_url)
        else:
            # Local dev: drop any leftover webhook and run long-poll in the background.
            await bot.delete_webhook(drop_pending_updates=True)
            log.warning(
                "bot: polling mode (PUBLIC_BASE_URL is not https). "
                "Polling consumes Telegram updates — only one instance can run at a time."
            )
            polling_task = asyncio.create_task(
                dp.start_polling(bot, handle_signals=False)
            )
    try:
        yield
    finally:
        if polling_task:
            polling_task.cancel()
            try:
                await polling_task
            except (asyncio.CancelledError, Exception):  # noqa: BLE001
                pass
        if bot:
            await bot.session.close()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="PrintScout", lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.webapp_url, "http://localhost:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router)
    app.include_router(search_router)
    app.include_router(fit_router)
    app.include_router(model_router)
    app.include_router(popular_router)

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post(settings.webhook_path)
    async def telegram_webhook(
        request: Request,
        x_telegram_bot_api_secret_token: str | None = Header(default=None),
    ) -> dict[str, bool]:
        if x_telegram_bot_api_secret_token != settings.webhook_secret:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "bad secret")
        bot = request.app.state.bot
        dp = request.app.state.dp
        if bot is None or dp is None:
            raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "bot disabled")
        payload = await request.json()
        update = Update.model_validate(payload)
        await dp.feed_update(bot, update)
        return {"ok": True}

    return app


app = create_app()
