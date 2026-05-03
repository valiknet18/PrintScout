from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    WebAppInfo,
)

from app.core.settings import get_settings

router = Router(name="root")


@router.message(CommandStart())
async def on_start(message: Message) -> None:
    settings = get_settings()
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Open PrintScout",
                    web_app=WebAppInfo(url=settings.webapp_url),
                )
            ]
        ]
    )
    await message.answer(
        "Welcome to <b>PrintScout</b>.\n\n"
        "Add your 3D printer once and search models that actually fit on your bed — "
        "across Printables, Thingiverse, and more.",
        reply_markup=kb,
    )
