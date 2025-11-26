"""Pet logic and state management."""
from datetime import datetime, timedelta
from typing import Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from database.models import Chat, PetStage, EventType
from database.crud import ChatCRUD, EventCRUD, UserCRUD
from config import config
from bot.utils import format_user_mention


class PetLogic:
    """Handle pet state management and logic."""

    @staticmethod
    async def tick_stats(session: AsyncSession, chat: Chat) -> Tuple[bool, bool]:
        """
        Decrease pet stats over time.
        Returns: (is_alive, is_critical)
        """
        if not chat.is_alive:
            return False, False

        # Calculate decay
        decay = config.STAT_DECAY_PER_TICK

        # Decrease stats
        new_hunger = max(0, chat.hunger - decay)
        new_mood = max(0, chat.mood - decay)
        new_energy = max(0, chat.energy - decay)

        # Calculate health based on other stats
        # Health decreases if any stat is critically low
        health_penalty = 0
        if new_hunger < 20:
            health_penalty += 10
        if new_mood < 20:
            health_penalty += 5
        if new_energy < 20:
            health_penalty += 5

        new_health = max(0, chat.health - health_penalty)

        # Update stats
        await ChatCRUD.update_stats(
            session,
            chat.chat_id,
            hunger=new_hunger,
            mood=new_mood,
            energy=new_energy,
            health=new_health
        )

        # Check if pet died
        if new_health <= 0:
            await ChatCRUD.kill_pet(session, chat.chat_id)
            await EventCRUD.create(
                session,
                chat.chat_id,
                EventType.DEATH,
                f"Питомец {chat.pet_name} умер от пренебрежения... 💀"
            )
            return False, True

        # Check if critical
        is_critical = new_health < config.CRITICAL_HEALTH_THRESHOLD
        if is_critical:
            await EventCRUD.create(
                session,
                chat.chat_id,
                EventType.CRITICAL_HEALTH,
                f"Здоровье {chat.pet_name} критически низкое! ({new_health}%) 🚨"
            )

        await ChatCRUD.update_last_tick(session, chat.chat_id)
        return True, is_critical

    @staticmethod
    async def feed(
        session: AsyncSession,
        chat: Chat,
        user_id: int,
        first_name: Optional[str] = None,
        username: Optional[str] = None
    ) -> dict:
        """
        Feed the pet.
        Returns: dict with result info
        """
        if not chat.is_alive:
            return {"success": False, "message": "Питомец мертв 💀"}

        # Check if pet is sleeping
        if chat.is_sleeping:
            return {"success": False, "message": f"{chat.pet_name} спит. Не буди его 😴"}

        # Increase hunger
        new_hunger = min(100, chat.hunger + 30)
        new_mood = min(100, chat.mood + 5)  # Slightly improve mood

        await ChatCRUD.update_stats(
            session,
            chat.chat_id,
            hunger=new_hunger,
            mood=new_mood
        )

        # Add XP
        await ChatCRUD.add_xp(session, chat.chat_id, config.XP_PER_FEED)

        # Get user mention
        user_mention = format_user_mention(user_id, first_name, username)

        # Log event
        await EventCRUD.create(
            session,
            chat.chat_id,
            EventType.FEED,
            f"Пользователь покормил {chat.pet_name}",
            user_id=user_id
        )

        return {
            "success": True,
            "message": f"{user_mention} покормил питомца.\nГолод: {new_hunger}%",
            "hunger": new_hunger,
            "mood": new_mood
        }

    @staticmethod
    async def play(
        session: AsyncSession,
        chat: Chat,
        user_id: int,
        first_name: Optional[str] = None,
        username: Optional[str] = None
    ) -> dict:
        """
        Play with the pet.
        Returns: dict with result info
        """
        if not chat.is_alive:
            return {"success": False, "message": "Питомец мертв 💀"}

        if chat.is_sleeping:
            return {"success": False, "message": f"{chat.pet_name} спит. Не буди его 😴"}

        # Check if pet has enough energy
        if chat.energy < 20:
            return {
                "success": False,
                "message": f"{chat.pet_name} слишком устал для игр."
            }

        # Update stats
        new_mood = min(100, chat.mood + 20)
        new_energy = max(0, chat.energy - 10)
        new_hunger = max(0, chat.hunger - 5)  # Playing makes hungry

        await ChatCRUD.update_stats(
            session,
            chat.chat_id,
            mood=new_mood,
            energy=new_energy,
            hunger=new_hunger
        )

        # Add XP
        await ChatCRUD.add_xp(session, chat.chat_id, config.XP_PER_GAME)

        # Get user mention
        user_mention = format_user_mention(user_id, first_name, username)

        # Log event
        await EventCRUD.create(
            session,
            chat.chat_id,
            EventType.PLAY,
            f"Пользователь поиграл с {chat.pet_name}",
            user_id=user_id
        )

        return {
            "success": True,
            "message": f"{user_mention} поиграл с питомцем.\nНастроение: {new_mood}%",
            "mood": new_mood,
            "energy": new_energy
        }

    @staticmethod
    def is_night_time() -> bool:
        """Check if it's night time (pet should sleep)."""
        current_hour = datetime.utcnow().hour
        night_start = config.NIGHT_START_HOUR
        night_end = config.NIGHT_END_HOUR

        if night_start < night_end:
            # Night doesn't cross midnight (e.g., 22-6)
            return night_start <= current_hour < night_end
        else:
            # Night crosses midnight (e.g., 0-7)
            return current_hour >= night_start or current_hour < night_end

    @staticmethod
    async def check_sleep_status(session: AsyncSession, chat: Chat) -> None:
        """Update pet's sleep status based on time."""
        is_night = PetLogic.is_night_time()

        if is_night and not chat.is_sleeping:
            # Put pet to sleep
            chat.is_sleeping = True
            await session.commit()
        elif not is_night and chat.is_sleeping:
            # Wake pet up
            chat.is_sleeping = False
            # Restore energy
            new_energy = min(100, chat.energy + 50)
            await ChatCRUD.update_stats(session, chat.chat_id, energy=new_energy)

    @staticmethod
    async def disturb_at_night(
        session: AsyncSession,
        chat: Chat,
        user_id: int,
        first_name: Optional[str] = None,
        username: Optional[str] = None
    ) -> dict:
        """
        Handle night disturbance (penalty).
        Returns: dict with result info
        """
        if not chat.is_sleeping:
            return {"disturbed": False}

        # Penalty: lose health
        new_health = max(0, chat.health - 15)
        new_mood = max(0, chat.mood - 20)

        await ChatCRUD.update_stats(
            session,
            chat.chat_id,
            health=new_health,
            mood=new_mood
        )

        # Get user mention
        user_mention = format_user_mention(user_id, first_name, username)

        # Log event
        await EventCRUD.create(
            session,
            chat.chat_id,
            EventType.NIGHT_DISTURB,
            f"Пользователь разбудил {chat.pet_name} ночью!",
            user_id=user_id
        )

        return {
            "disturbed": True,
            "message": f"{user_mention} разбудил {chat.pet_name}!\nПитомец потерял здоровье 😡\nЗдоровье: {new_health}%",
            "health": new_health
        }

    @staticmethod
    def get_status_emoji(value: int) -> str:
        """Get emoji based on stat value."""
        if value >= 80:
            return "💚"
        elif value >= 60:
            return "💛"
        elif value >= 40:
            return "🧡"
        elif value >= 20:
            return "❤️"
        else:
            return "💔"

    @staticmethod
    def get_stage_emoji(stage: PetStage) -> str:
        """Get emoji for pet stage."""
        emoji_map = {
            PetStage.EGG: "🥚",
            PetStage.BABY: "🐣",
            PetStage.TEEN: "🐥",
            PetStage.ADULT: "🦆",
            PetStage.ANCIENT: "🦉"
        }
        return emoji_map.get(stage, "❓")

    @staticmethod
    def format_status(chat: Chat) -> str:
        """Format pet status as a message."""
        stage_emoji = PetLogic.get_stage_emoji(chat.pet_stage)
        status = "💀 МЕРТВ" if not chat.is_alive else "😴 Спит" if chat.is_sleeping else "✅ Живой"

        return f"""
🐾 **{chat.pet_name}** {stage_emoji}
Тип: {chat.pet_type.value.title()} | Уровень: {chat.level}
Статус: {status}

📊 **Показатели:**
{PetLogic.get_status_emoji(chat.hunger)} Голод: {chat.hunger}%
{PetLogic.get_status_emoji(chat.mood)} Настроение: {chat.mood}%
{PetLogic.get_status_emoji(chat.energy)} Энергия: {chat.energy}%
{PetLogic.get_status_emoji(chat.health)} Здоровье: {chat.health}%

⭐ Опыт: {chat.xp} XP
🎂 Возраст: {(datetime.utcnow() - chat.created_at).days} дней
        """.strip()
