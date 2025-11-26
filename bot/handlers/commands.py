"""Command handlers."""
import random
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message
from database.engine import async_session
from database.crud import ChatCRUD, UserCRUD, EventCRUD
from database.models import EventType
from services.pet_logic import PetLogic
from services.evolution import EvolutionSystem
from bot.keyboards.inline import get_gamble_keyboard
from bot.utils import format_user_mention_from_db, format_user_mention_from_tg

router = Router()


@router.message(Command("start"))
async def cmd_start(message: Message):
    """Start command - create or revive pet."""
    if message.chat.type == "private":
        await message.answer(
            "Привет! Я бот-Тамагочи.\n\n"
            "Добавь меня в групповой чат, чтобы завести виртуального питомца.\n"
            "Все участники группы смогут заботиться о нем вместе!"
        )
        return

    async with async_session() as session:
        chat = await ChatCRUD.get_or_create(session, message.chat.id)

        if not chat.is_alive:
            # Revive pet
            await ChatCRUD.revive_pet(session, message.chat.id)
            await EventCRUD.create(
                session,
                message.chat.id,
                EventType.BIRTH,
                "Новый питомец родился!"
            )
            await message.answer(
                "🥚 **Новый питомец родился!**\n\n"
                "Заботьтесь о нем вместе с участниками чата.\n\n"
                "**Команды:**\n"
                "/status - Состояние питомца\n"
                "/feed - Покормить\n"
                "/play - Поиграть\n"
                "/gamble - Казино\n"
                "/leaderboard - Таблица лидеров\n"
                "/history - История событий"
            )
        else:
            await message.answer(
                f"Питомец {chat.pet_name} уже живет в этом чате.\n"
                f"Используй /status чтобы посмотреть его состояние."
            )


@router.message(Command("status"))
async def cmd_status(message: Message):
    """Show pet status."""
    if message.chat.type == "private":
        await message.answer("Эта команда работает только в группах!")
        return

    async with async_session() as session:
        chat = await ChatCRUD.get(session, message.chat.id)
        if not chat:
            await message.answer("В этом чате еще нет питомца! Используй /start")
            return

        status_text = PetLogic.format_status(chat)
        await message.answer(status_text)


@router.message(Command("feed"))
async def cmd_feed(message: Message):
    """Feed the pet."""
    if message.chat.type == "private":
        await message.answer("Эта команда работает только в группах!")
        return

    async with async_session() as session:
        chat = await ChatCRUD.get(session, message.chat.id)
        if not chat:
            await message.answer("В этом чате еще нет питомца! Используй /start")
            return

        # Check night disturbance
        if chat.is_sleeping:
            disturb_result = await PetLogic.disturb_at_night(
                session,
                chat,
                message.from_user.id,
                message.from_user.first_name,
                message.from_user.username
            )
            if disturb_result["disturbed"]:
                await UserCRUD.increment_stat(
                    session,
                    message.from_user.id,
                    message.chat.id,
                    "night_disturb_count"
                )
                await message.answer(disturb_result["message"], parse_mode="Markdown")
                return

        # Feed pet
        result = await PetLogic.feed(
            session,
            chat,
            message.from_user.id,
            message.from_user.first_name,
            message.from_user.username
        )

        # Update user stats
        if result["success"]:
            await UserCRUD.increment_stat(
                session,
                message.from_user.id,
                message.chat.id,
                "feed_count"
            )
            await UserCRUD.increment_stat(
                session,
                message.from_user.id,
                message.chat.id,
                "karma_points",
                5
            )

        await message.answer(result["message"], parse_mode="Markdown")


@router.message(Command("play"))
async def cmd_play(message: Message):
    """Play with the pet."""
    if message.chat.type == "private":
        await message.answer("Эта команда работает только в группах!")
        return

    async with async_session() as session:
        chat = await ChatCRUD.get(session, message.chat.id)
        if not chat:
            await message.answer("В этом чате еще нет питомца! Используй /start")
            return

        # Check night disturbance
        if chat.is_sleeping:
            disturb_result = await PetLogic.disturb_at_night(
                session,
                chat,
                message.from_user.id,
                message.from_user.first_name,
                message.from_user.username
            )
            if disturb_result["disturbed"]:
                await UserCRUD.increment_stat(
                    session,
                    message.from_user.id,
                    message.chat.id,
                    "night_disturb_count"
                )
                await message.answer(disturb_result["message"], parse_mode="Markdown")
                return

        # Play with pet
        result = await PetLogic.play(
            session,
            chat,
            message.from_user.id,
            message.from_user.first_name,
            message.from_user.username
        )

        # Update user stats
        if result["success"]:
            await UserCRUD.increment_stat(
                session,
                message.from_user.id,
                message.chat.id,
                "play_count"
            )
            await UserCRUD.increment_stat(
                session,
                message.from_user.id,
                message.chat.id,
                "karma_points",
                3
            )

        await message.answer(result["message"], parse_mode="Markdown")


@router.message(Command("gamble"))
async def cmd_gamble(message: Message):
    """Start gambling game."""
    if message.chat.type == "private":
        await message.answer("Эта команда работает только в группах!")
        return

    async with async_session() as session:
        chat = await ChatCRUD.get(session, message.chat.id)
        if not chat:
            await message.answer("В этом чате еще нет питомца! Используй /start")
            return

        if not chat.is_alive:
            await message.answer("Питомец мертв 💀")
            return

        if chat.hunger < 30:
            await message.answer(
                f"**Казино на еду**\n\n"
                f"Текущий голод: {chat.hunger}%\n\n"
                f"Слишком голодно для игры. Сначала покорми питомца."
            )
            return

        await message.answer(
            f"🎰 **Казино на еду**\n\n"
            f"Текущий голод питомца: {chat.hunger}%\n\n"
            f"Рискнешь? Шанс 50/50:\n"
            f"• Выиграл: +50% голода\n"
            f"• Проиграл: -30% голода",
            reply_markup=get_gamble_keyboard()
        )


@router.message(Command("leaderboard"))
async def cmd_leaderboard(message: Message):
    """Show leaderboard."""
    if message.chat.type == "private":
        await message.answer("Эта команда работает только в группах!")
        return

    async with async_session() as session:
        # Get top feeders
        top_feeders = await UserCRUD.get_leaderboard(
            session,
            message.chat.id,
            "feed_count",
            5
        )

        # Get top karma
        top_karma = await UserCRUD.get_leaderboard(
            session,
            message.chat.id,
            "karma_points",
            5
        )

        # Get top disturbers
        top_disturbers = await UserCRUD.get_leaderboard(
            session,
            message.chat.id,
            "night_disturb_count",
            3
        )

        text = "🏆 **Таблица лидеров**\n\n"

        text += "👑 **Топ Заботливых:**\n"
        for i, user in enumerate(top_feeders, 1):
            user_mention = format_user_mention_from_db(user)
            text += f"{i}. {user_mention}: {user.feed_count} кормлений\n"

        text += "\n⭐ **Топ по Карме:**\n"
        for i, user in enumerate(top_karma, 1):
            user_mention = format_user_mention_from_db(user)
            text += f"{i}. {user_mention}: {user.karma_points} очков\n"

        if top_disturbers and top_disturbers[0].night_disturb_count > 0:
            text += "\n😈 **Топ Вредителей:**\n"
            for i, user in enumerate(top_disturbers, 1):
                user_mention = format_user_mention_from_db(user)
                text += f"{i}. {user_mention}: {user.night_disturb_count} раз будил\n"

        await message.answer(text, parse_mode="Markdown")


@router.message(Command("history"))
async def cmd_history(message: Message):
    """Show recent events."""
    if message.chat.type == "private":
        await message.answer("Эта команда работает только в группах!")
        return

    async with async_session() as session:
        events = await EventCRUD.get_recent(session, message.chat.id, 10)

        if not events:
            await message.answer("История событий пуста.")
            return

        text = "📜 **История событий:**\n\n"
        for event in events:
            timestamp = event.created_at.strftime("%d.%m %H:%M")

            # Get user mention if user_id exists
            event_text = event.description
            if event.user_id:
                user = await UserCRUD.get_or_create(session, event.user_id, message.chat.id)
                user_mention = format_user_mention_from_db(user)
                # Replace "Пользователь" with actual mention
                event_text = event_text.replace("Пользователь", user_mention)

            text += f"[{timestamp}] {event_text}\n"

        await message.answer(text, parse_mode="Markdown")
