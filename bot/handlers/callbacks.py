"""Callback query handlers."""
import random
from aiogram import Router, F
from aiogram.types import CallbackQuery
from database.engine import async_session
from database.crud import ChatCRUD, UserCRUD, EventCRUD
from database.models import EventType
from bot.utils import format_user_mention_from_tg

router = Router()


@router.callback_query(F.data == "gamble_play")
async def callback_gamble_play(callback: CallbackQuery):
    """Handle gambling play."""
    async with async_session() as session:
        chat = await ChatCRUD.get(session, callback.message.chat.id)
        if not chat or not chat.is_alive:
            await callback.answer("Питомец мертв!", show_alert=True)
            return

        # 50/50 chance
        won = random.choice([True, False])

        if won:
            # Win: +50 hunger
            new_hunger = min(100, chat.hunger + 50)
            await ChatCRUD.update_stats(session, chat.chat_id, hunger=new_hunger)

            await UserCRUD.increment_stat(
                session,
                callback.from_user.id,
                callback.message.chat.id,
                "gamble_wins"
            )
            await UserCRUD.increment_stat(
                session,
                callback.from_user.id,
                callback.message.chat.id,
                "karma_points",
                10
            )

            user_mention = format_user_mention_from_tg(callback.from_user)

            await EventCRUD.create(
                session,
                chat.chat_id,
                EventType.GAMBLE_WIN,
                f"Пользователь выиграл в казино!",
                user_id=callback.from_user.id
            )

            await callback.message.edit_text(
                f"🎉 **ВЫИГРАЛ!**\n\n"
                f"{user_mention} выиграл в казино!\n"
                f"Голод питомца: {new_hunger}% (+50)",
                parse_mode="Markdown"
            )
        else:
            # Lose: -30 hunger
            new_hunger = max(0, chat.hunger - 30)
            await ChatCRUD.update_stats(session, chat.chat_id, hunger=new_hunger)

            await UserCRUD.increment_stat(
                session,
                callback.from_user.id,
                callback.message.chat.id,
                "gamble_losses"
            )
            await UserCRUD.increment_stat(
                session,
                callback.from_user.id,
                callback.message.chat.id,
                "karma_points",
                -5
            )

            user_mention = format_user_mention_from_tg(callback.from_user)

            await EventCRUD.create(
                session,
                chat.chat_id,
                EventType.GAMBLE_LOSS,
                f"Пользователь проиграл в казино",
                user_id=callback.from_user.id
            )

            await callback.message.edit_text(
                f"😢 **ПРОИГРАЛ!**\n\n"
                f"{user_mention} проиграл в казино...\n"
                f"Голод питомца: {new_hunger}% (-30)",
                parse_mode="Markdown"
            )

    await callback.answer()


@router.callback_query(F.data == "gamble_cancel")
async def callback_gamble_cancel(callback: CallbackQuery):
    """Cancel gambling."""
    await callback.message.edit_text("Игра отменена.")
    await callback.answer()
