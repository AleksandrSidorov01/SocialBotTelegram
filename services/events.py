"""Random events system."""
import random
from typing import Dict, Callable
from sqlalchemy.ext.asyncio import AsyncSession
from database.models import Chat, EventType
from database.crud import ChatCRUD, EventCRUD


class RandomEvent:
    """Base class for random events."""

    def __init__(self, name: str, description: str, probability: float = 0.3):
        self.name = name
        self.description = description
        self.probability = probability

    async def execute(self, session: AsyncSession, chat: Chat) -> Dict:
        """Execute the event. Override in subclasses."""
        raise NotImplementedError


class FindBoxEvent(RandomEvent):
    """Pet finds a mysterious box."""

    def __init__(self):
        super().__init__(
            name="Mysterious Box",
            description="Питомец нашел странную коробку...",
            probability=0.2
        )

    async def execute(self, session: AsyncSession, chat: Chat) -> Dict:
        """Execute box event."""
        # Random outcome
        outcomes = [
            {
                "type": "positive",
                "message": "В коробке была еда! +50 к голоду! 🎁",
                "stats": {"hunger": min(100, chat.hunger + 50)}
            },
            {
                "type": "positive",
                "message": "В коробке был энергетик! +30 к энергии! ⚡",
                "stats": {"energy": min(100, chat.energy + 30)}
            },
            {
                "type": "positive",
                "message": "В коробке были игрушки! +40 к настроению! 🎮",
                "stats": {"mood": min(100, chat.mood + 40)}
            },
            {
                "type": "negative",
                "message": "Коробка была с плесенью! -20 к здоровью! 🤢",
                "stats": {"health": max(0, chat.health - 20)}
            },
            {
                "type": "xp",
                "message": "В коробке был учебник! +50 XP! 📚",
                "xp": 50
            },
        ]

        outcome = random.choice(outcomes)

        # Apply outcome
        if "stats" in outcome:
            await ChatCRUD.update_stats(session, chat.chat_id, **outcome["stats"])

        if "xp" in outcome:
            await ChatCRUD.add_xp(session, chat.chat_id, outcome["xp"])

        await EventCRUD.create(
            session,
            chat.chat_id,
            EventType.RANDOM_EVENT,
            f"Событие: {self.description}\n{outcome['message']}"
        )

        return {
            "event": self.name,
            "message": outcome["message"],
            "type": outcome.get("type", "xp")
        }


class VisitorEvent(RandomEvent):
    """A visitor comes to the pet."""

    def __init__(self):
        super().__init__(
            name="Visitor",
            description="К питомцу пришел гость!",
            probability=0.15
        )

    async def execute(self, session: AsyncSession, chat: Chat) -> Dict:
        """Execute visitor event."""
        visitors = [
            {
                "name": "Добрая фея",
                "message": "Добрая фея восстановила все показатели! ✨",
                "effect": "heal_all"
            },
            {
                "name": "Злой тролль",
                "message": "Злой тролль украл еду! -30 к голоду! 👹",
                "effect": {"hunger": max(0, chat.hunger - 30)}
            },
            {
                "name": "Веселый клоун",
                "message": "Клоун развеселил питомца! +50 к настроению! 🤡",
                "effect": {"mood": min(100, chat.mood + 50)}
            },
        ]

        visitor = random.choice(visitors)

        # Apply effect
        if visitor["effect"] == "heal_all":
            await ChatCRUD.update_stats(
                session,
                chat.chat_id,
                hunger=100,
                mood=100,
                energy=100,
                health=100
            )
        elif isinstance(visitor["effect"], dict):
            await ChatCRUD.update_stats(session, chat.chat_id, **visitor["effect"])

        await EventCRUD.create(
            session,
            chat.chat_id,
            EventType.RANDOM_EVENT,
            f"Событие: {visitor['name']}\n{visitor['message']}"
        )

        return {
            "event": self.name,
            "visitor": visitor["name"],
            "message": visitor["message"]
        }


class WeatherEvent(RandomEvent):
    """Weather affects the pet."""

    def __init__(self):
        super().__init__(
            name="Weather Change",
            description="Погода изменилась!",
            probability=0.25
        )

    async def execute(self, session: AsyncSession, chat: Chat) -> Dict:
        """Execute weather event."""
        weather_types = [
            {
                "type": "Солнечно",
                "emoji": "☀️",
                "message": "Отличная погода! +20 к настроению!",
                "effect": {"mood": min(100, chat.mood + 20)}
            },
            {
                "type": "Дождь",
                "emoji": "🌧️",
                "message": "Идет дождь... -10 к настроению",
                "effect": {"mood": max(0, chat.mood - 10)}
            },
            {
                "type": "Гроза",
                "emoji": "⛈️",
                "message": "Гроза напугала питомца! -20 к настроению, -15 к энергии",
                "effect": {
                    "mood": max(0, chat.mood - 20),
                    "energy": max(0, chat.energy - 15)
                }
            },
            {
                "type": "Снег",
                "emoji": "❄️",
                "message": "Снег! Питомец радуется! +15 к настроению",
                "effect": {"mood": min(100, chat.mood + 15)}
            },
        ]

        weather = random.choice(weather_types)

        await ChatCRUD.update_stats(session, chat.chat_id, **weather["effect"])

        await EventCRUD.create(
            session,
            chat.chat_id,
            EventType.RANDOM_EVENT,
            f"Погода: {weather['type']} {weather['emoji']}\n{weather['message']}"
        )

        return {
            "event": self.name,
            "weather": weather["type"],
            "message": f"{weather['emoji']} {weather['message']}"
        }


class EventManager:
    """Manage random events."""

    def __init__(self):
        self.events = [
            FindBoxEvent(),
            VisitorEvent(),
            WeatherEvent(),
        ]

    async def trigger_random_event(
        self,
        session: AsyncSession,
        chat: Chat
    ) -> Dict | None:
        """
        Attempt to trigger a random event.
        Returns event result or None if no event triggered.
        """
        if not chat.is_alive or chat.is_sleeping:
            return None

        # Roll for event
        if random.random() > 0.3:  # 30% chance overall
            return None

        # Choose event
        event = random.choice(self.events)

        # Roll for specific event
        if random.random() > event.probability:
            return None

        # Execute event
        result = await event.execute(session, chat)
        return result
