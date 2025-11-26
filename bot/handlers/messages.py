"""Message handlers for organic interaction."""
import re
from aiogram import Router, F
from aiogram.types import Message
from database.engine import async_session
from database.crud import ChatCRUD, UserCRUD
from config import config

router = Router()


def contains_bad_words(text: str) -> bool:
    """Check if message contains bad words."""
    text_lower = text.lower()
    for word in config.BAD_WORDS:
        if word in text_lower:
            return True
    return False


def is_mostly_caps(text: str) -> bool:
    """Check if message is mostly in CAPS."""
    if len(text) < 10:
        return False

    letters = [c for c in text if c.isalpha()]
    if not letters:
        return False

    caps_count = sum(1 for c in letters if c.isupper())
    return caps_count / len(letters) > 0.7


def contains_code(text: str) -> bool:
    """Check if message contains code snippets."""
    # Simple heuristic: contains common programming patterns
    code_patterns = [
        r'def\s+\w+',  # Python function
        r'function\s+\w+',  # JS function
        r'class\s+\w+',  # Class definition
        r'import\s+',  # Import statement
        r'const\s+\w+\s*=',  # JS const
        r'let\s+\w+\s*=',  # JS let
        r'var\s+\w+\s*=',  # JS var
        r'\w+\(\)',  # Function call
        r'{\s*\w+:\s*\w+',  # Object literal
        r'<\w+>.*</\w+>',  # HTML tags
    ]

    for pattern in code_patterns:
        if re.search(pattern, text):
            return True
    return False


@router.message(F.chat.type.in_({"group", "supergroup"}), F.text)
async def handle_group_message(message: Message):
    """Handle regular group messages for organic interaction."""
    # Ignore bot commands
    if message.text.startswith('/'):
        return

    async with async_session() as session:
        chat = await ChatCRUD.get(session, message.chat.id)
        if not chat or not chat.is_alive:
            return

        # Get or create user
        await UserCRUD.get_or_create(
            session,
            message.from_user.id,
            message.chat.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name
        )

        # Increment message count
        await UserCRUD.increment_stat(
            session,
            message.from_user.id,
            message.chat.id,
            "message_count"
        )

        # Add small XP for each message
        await ChatCRUD.add_xp(session, message.chat.id, config.XP_PER_MESSAGE)

        # Slightly increase hunger (organic feeding through activity)
        new_hunger = min(100, chat.hunger + 1)
        await ChatCRUD.update_stats(session, chat.chat_id, hunger=new_hunger)

        # Analyze message content and update behavior counters
        text = message.text

        # Check for bad words
        if contains_bad_words(text):
            await ChatCRUD.increment_behavior_counter(
                session,
                message.chat.id,
                "cursing_count"
            )
            # Decrease mood
            new_mood = max(0, chat.mood - 2)
            await ChatCRUD.update_stats(session, chat.chat_id, mood=new_mood)

        # Check for caps
        if is_mostly_caps(text):
            await ChatCRUD.increment_behavior_counter(
                session,
                message.chat.id,
                "caps_count"
            )
            # Decrease mood slightly
            new_mood = max(0, chat.mood - 1)
            await ChatCRUD.update_stats(session, chat.chat_id, mood=new_mood)

        # Check for code
        if contains_code(text):
            await ChatCRUD.increment_behavior_counter(
                session,
                message.chat.id,
                "code_count"
            )


@router.message(F.chat.type.in_({"group", "supergroup"}), F.sticker)
async def handle_sticker(message: Message):
    """Handle stickers (count as memes)."""
    async with async_session() as session:
        chat = await ChatCRUD.get(session, message.chat.id)
        if not chat or not chat.is_alive:
            return

        # Increment meme counter
        await ChatCRUD.increment_behavior_counter(
            session,
            message.chat.id,
            "meme_count"
        )

        # Increase mood
        new_mood = min(100, chat.mood + 2)
        await ChatCRUD.update_stats(session, chat.chat_id, mood=new_mood)


@router.message(F.chat.type.in_({"group", "supergroup"}), F.photo)
async def handle_photo(message: Message):
    """Handle photos (might be memes)."""
    async with async_session() as session:
        chat = await ChatCRUD.get(session, message.chat.id)
        if not chat or not chat.is_alive:
            return

        # Check caption for bad words or code
        if message.caption:
            if contains_bad_words(message.caption):
                await ChatCRUD.increment_behavior_counter(
                    session,
                    message.chat.id,
                    "cursing_count"
                )
            if contains_code(message.caption):
                await ChatCRUD.increment_behavior_counter(
                    session,
                    message.chat.id,
                    "code_count"
                )

        # Count as meme if no caption or fun caption
        if not message.caption or len(message.caption) < 50:
            await ChatCRUD.increment_behavior_counter(
                session,
                message.chat.id,
                "meme_count"
            )
            new_mood = min(100, chat.mood + 1)
            await ChatCRUD.update_stats(session, chat.chat_id, mood=new_mood)
