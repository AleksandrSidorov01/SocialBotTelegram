"""Utility functions for the bot."""
from typing import Optional
from aiogram.types import User as TgUser
from database.models import User as DbUser


def format_user_mention(
    user_id: int,
    first_name: Optional[str] = None,
    username: Optional[str] = None
) -> str:
    """
    Format user mention as a clickable link.

    Returns a Telegram markdown link in format: [Display Name](tg://user?id=USER_ID)

    Args:
        user_id: Telegram user ID
        first_name: User's first name
        username: User's username (without @)

    Returns:
        Formatted mention string
    """
    # Determine display name
    if first_name:
        display_name = first_name
    elif username:
        display_name = f"@{username}"
    else:
        display_name = "Пользователь"

    # Create markdown link
    return f"[{display_name}](tg://user?id={user_id})"


def format_user_mention_from_tg(user: TgUser) -> str:
    """
    Format user mention from Telegram User object.

    Args:
        user: aiogram User object

    Returns:
        Formatted mention string
    """
    return format_user_mention(user.id, user.first_name, user.username)


def format_user_mention_from_db(user: DbUser) -> str:
    """
    Format user mention from database User object.

    Args:
        user: Database User object

    Returns:
        Formatted mention string
    """
    return format_user_mention(user.user_id, user.first_name, user.username)
