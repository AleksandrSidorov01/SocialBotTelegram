"""Background task scheduler."""
import asyncio
import logging
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import select
from database.models import Chat
from database.engine import async_session
from services.pet_logic import PetLogic
from services.evolution import EvolutionSystem
from services.events import EventManager
from config import config

logger = logging.getLogger(__name__)


class BotScheduler:
    """Scheduler for background tasks."""

    def __init__(self, bot):
        self.scheduler = AsyncIOScheduler()
        self.bot = bot
        self.event_manager = EventManager()

    async def tick_all_pets(self):
        """Tick stats for all active pets."""
        logger.info("Starting pet stats tick...")

        async with async_session() as session:
            # Get all alive chats
            result = await session.execute(
                select(Chat).where(Chat.is_alive == True)
            )
            chats = result.scalars().all()

            logger.info(f"Ticking {len(chats)} pets...")

            for chat in chats:
                try:
                    # Check sleep status
                    await PetLogic.check_sleep_status(session, chat)

                    # Tick stats
                    is_alive, is_critical = await PetLogic.tick_stats(session, chat)

                    if not is_alive:
                        # Pet died, notify chat
                        try:
                            await self.bot.send_message(
                                chat.chat_id,
                                f"💀 {chat.pet_name} умер от пренебрежения...\n"
                                f"Используйте /start чтобы завести нового питомца."
                            )
                        except Exception as e:
                            logger.error(f"Failed to send death message to {chat.chat_id}: {e}")

                    elif is_critical:
                        # Critical health, send alert
                        try:
                            await self.bot.send_message(
                                chat.chat_id,
                                f"🚨 ВНИМАНИЕ! {chat.pet_name} при смерти!\n"
                                f"Здоровье: {chat.health}%\n"
                                f"Срочно покормите и позаботьтесь о питомце!"
                            )
                        except Exception as e:
                            logger.error(f"Failed to send critical alert to {chat.chat_id}: {e}")

                    # Check for evolution
                    if is_alive:
                        evolved, new_stage, new_type = await EvolutionSystem.check_and_evolve(
                            session,
                            chat
                        )
                        if evolved:
                            # Refresh chat to get updated data
                            await session.refresh(chat)
                            message = EvolutionSystem.get_evolution_message(
                                chat.pet_name,
                                new_stage,
                                new_type
                            )
                            try:
                                await self.bot.send_message(chat.chat_id, message)
                            except Exception as e:
                                logger.error(f"Failed to send evolution message to {chat.chat_id}: {e}")

                except Exception as e:
                    logger.error(f"Error ticking pet for chat {chat.chat_id}: {e}")

        logger.info("Pet stats tick completed.")

    async def trigger_random_events(self):
        """Trigger random events for active pets."""
        logger.info("Checking for random events...")

        async with async_session() as session:
            # Get all alive, awake chats
            result = await session.execute(
                select(Chat).where(
                    Chat.is_alive == True,
                    Chat.is_sleeping == False
                )
            )
            chats = result.scalars().all()

            for chat in chats:
                try:
                    event_result = await self.event_manager.trigger_random_event(
                        session,
                        chat
                    )

                    if event_result:
                        # Send event notification to chat
                        try:
                            await self.bot.send_message(
                                chat.chat_id,
                                f"🎲 **Случайное событие!**\n\n{event_result['message']}"
                            )
                        except Exception as e:
                            logger.error(f"Failed to send event message to {chat.chat_id}: {e}")

                except Exception as e:
                    logger.error(f"Error triggering event for chat {chat.chat_id}: {e}")

        logger.info("Random events check completed.")

    def start(self):
        """Start the scheduler."""
        # Add jobs

        # Tick stats every N minutes
        self.scheduler.add_job(
            self.tick_all_pets,
            trigger=IntervalTrigger(minutes=config.TICK_INTERVAL_MINUTES),
            id="tick_stats",
            name="Tick pet stats",
            replace_existing=True,
        )

        # Random events check every 30 minutes
        self.scheduler.add_job(
            self.trigger_random_events,
            trigger=IntervalTrigger(minutes=30),
            id="random_events",
            name="Trigger random events",
            replace_existing=True,
        )

        # Sleep check every hour
        async def check_sleep_all():
            async with async_session() as session:
                result = await session.execute(select(Chat).where(Chat.is_alive == True))
                chats = result.scalars().all()
                for chat in chats:
                    try:
                        await PetLogic.check_sleep_status(session, chat)
                    except Exception as e:
                        logger.error(f"Error checking sleep for {chat.chat_id}: {e}")

        self.scheduler.add_job(
            check_sleep_all,
            trigger=IntervalTrigger(hours=1),
            id="check_sleep",
            name="Check sleep status",
            replace_existing=True,
        )

        self.scheduler.start()
        logger.info("Scheduler started successfully.")

    def shutdown(self):
        """Shutdown the scheduler."""
        self.scheduler.shutdown()
        logger.info("Scheduler shut down.")
