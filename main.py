"""Main bot entry point."""
import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from config import config
from database.engine import init_db
from bot.handlers import commands, messages, callbacks
from services.scheduler import BotScheduler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def main():
    """Main function to run the bot."""
    # Validate config
    if not config.BOT_TOKEN:
        logger.error("BOT_TOKEN is not set in .env file!")
        return

    # Initialize database
    logger.info("Initializing database...")
    await init_db()
    logger.info("Database initialized successfully.")

    # Create bot and dispatcher
    bot = Bot(
        token=config.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN)
    )
    dp = Dispatcher()

    # Register routers
    dp.include_router(commands.router)
    dp.include_router(callbacks.router)
    dp.include_router(messages.router)

    # Initialize and start scheduler
    logger.info("Starting scheduler...")
    scheduler = BotScheduler(bot)
    scheduler.start()

    # Start bot
    logger.info("Bot is starting...")
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        # Cleanup
        logger.info("Shutting down...")
        scheduler.shutdown()
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user.")
