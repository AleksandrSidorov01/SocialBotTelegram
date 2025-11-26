"""Inline keyboards for bot."""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_gamble_keyboard() -> InlineKeyboardMarkup:
    """Get keyboard for gambling."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🎲 Рискнуть!", callback_data="gamble_play"),
                InlineKeyboardButton(text="❌ Отмена", callback_data="gamble_cancel"),
            ]
        ]
    )


def get_random_event_keyboard(event_type: str) -> InlineKeyboardMarkup:
    """Get keyboard for random events."""
    if event_type == "box":
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="📦 Открыть", callback_data="event_box_open"),
                    InlineKeyboardButton(text="🗑️ Выкинуть", callback_data="event_box_throw"),
                ]
            ]
        )
    return None
