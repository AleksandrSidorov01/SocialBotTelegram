"""CRUD operations for database models."""
from datetime import datetime
from typing import Optional, List
from sqlalchemy import select, update, delete, desc, func
from sqlalchemy.ext.asyncio import AsyncSession
from .models import Chat, User, Event, PetStage, PetType, EventType


class ChatCRUD:
    """CRUD operations for Chat model."""

    @staticmethod
    async def get_or_create(session: AsyncSession, chat_id: int) -> Chat:
        """Get existing chat or create new one."""
        result = await session.execute(
            select(Chat).where(Chat.chat_id == chat_id)
        )
        chat = result.scalar_one_or_none()

        if not chat:
            chat = Chat(chat_id=chat_id)
            session.add(chat)
            await session.commit()
            await session.refresh(chat)

        return chat

    @staticmethod
    async def get(session: AsyncSession, chat_id: int) -> Optional[Chat]:
        """Get chat by ID."""
        result = await session.execute(
            select(Chat).where(Chat.chat_id == chat_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def update_stats(
        session: AsyncSession,
        chat_id: int,
        hunger: Optional[int] = None,
        mood: Optional[int] = None,
        energy: Optional[int] = None,
        health: Optional[int] = None,
    ) -> None:
        """Update pet stats."""
        update_data = {}
        if hunger is not None:
            update_data["hunger"] = max(0, min(100, hunger))
        if mood is not None:
            update_data["mood"] = max(0, min(100, mood))
        if energy is not None:
            update_data["energy"] = max(0, min(100, energy))
        if health is not None:
            update_data["health"] = max(0, min(100, health))

        update_data["last_interaction"] = datetime.utcnow()

        await session.execute(
            update(Chat)
            .where(Chat.chat_id == chat_id)
            .values(**update_data)
        )
        await session.commit()

    @staticmethod
    async def add_xp(
        session: AsyncSession,
        chat_id: int,
        xp_amount: int
    ) -> Chat:
        """Add XP to pet and handle leveling."""
        chat = await ChatCRUD.get(session, chat_id)
        if not chat:
            return None

        chat.xp += xp_amount
        # Simple leveling: 100 XP per level
        new_level = (chat.xp // 100) + 1
        if new_level > chat.level:
            chat.level = new_level

        await session.commit()
        await session.refresh(chat)
        return chat

    @staticmethod
    async def kill_pet(session: AsyncSession, chat_id: int) -> None:
        """Mark pet as dead."""
        await session.execute(
            update(Chat)
            .where(Chat.chat_id == chat_id)
            .values(
                is_alive=False,
                death_at=datetime.utcnow(),
                health=0
            )
        )
        await session.commit()

    @staticmethod
    async def revive_pet(session: AsyncSession, chat_id: int) -> None:
        """Revive pet (reset to egg stage)."""
        await session.execute(
            update(Chat)
            .where(Chat.chat_id == chat_id)
            .values(
                is_alive=True,
                death_at=None,
                pet_stage=PetStage.EGG,
                pet_type=PetType.NORMAL,
                hunger=100,
                mood=100,
                energy=100,
                health=100,
                xp=0,
                level=1,
                cursing_count=0,
                meme_count=0,
                code_count=0,
                caps_count=0,
                created_at=datetime.utcnow()
            )
        )
        await session.commit()

    @staticmethod
    async def evolve(
        session: AsyncSession,
        chat_id: int,
        new_stage: PetStage,
        new_type: PetType
    ) -> None:
        """Evolve pet to new stage and type."""
        await session.execute(
            update(Chat)
            .where(Chat.chat_id == chat_id)
            .values(
                pet_stage=new_stage,
                pet_type=new_type
            )
        )
        await session.commit()

    @staticmethod
    async def increment_behavior_counter(
        session: AsyncSession,
        chat_id: int,
        counter_type: str,
        amount: int = 1
    ) -> None:
        """Increment behavior counters (cursing, meme, code, caps)."""
        valid_counters = ["cursing_count", "meme_count", "code_count", "caps_count"]
        if counter_type not in valid_counters:
            return

        chat = await ChatCRUD.get(session, chat_id)
        if chat:
            current_value = getattr(chat, counter_type)
            setattr(chat, counter_type, current_value + amount)
            await session.commit()

    @staticmethod
    async def update_last_tick(session: AsyncSession, chat_id: int) -> None:
        """Update last tick timestamp."""
        await session.execute(
            update(Chat)
            .where(Chat.chat_id == chat_id)
            .values(last_tick=datetime.utcnow())
        )
        await session.commit()


class UserCRUD:
    """CRUD operations for User model."""

    @staticmethod
    async def get_or_create(
        session: AsyncSession,
        user_id: int,
        chat_id: int,
        username: Optional[str] = None,
        first_name: Optional[str] = None
    ) -> User:
        """Get existing user or create new one."""
        result = await session.execute(
            select(User).where(
                User.user_id == user_id,
                User.chat_id == chat_id
            )
        )
        user = result.scalar_one_or_none()

        if not user:
            user = User(
                user_id=user_id,
                chat_id=chat_id,
                username=username,
                first_name=first_name
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
        else:
            # Update username/first_name if changed
            if username and user.username != username:
                user.username = username
            if first_name and user.first_name != first_name:
                user.first_name = first_name
            user.last_interaction = datetime.utcnow()
            await session.commit()

        return user

    @staticmethod
    async def increment_stat(
        session: AsyncSession,
        user_id: int,
        chat_id: int,
        stat_name: str,
        amount: int = 1
    ) -> None:
        """Increment user statistic."""
        valid_stats = [
            "karma_points", "feed_count", "play_count",
            "message_count", "night_disturb_count",
            "gamble_wins", "gamble_losses"
        ]
        if stat_name not in valid_stats:
            return

        user = await UserCRUD.get_or_create(session, user_id, chat_id)
        current_value = getattr(user, stat_name)
        setattr(user, stat_name, current_value + amount)
        await session.commit()

    @staticmethod
    async def get_leaderboard(
        session: AsyncSession,
        chat_id: int,
        stat_name: str,
        limit: int = 10
    ) -> List[User]:
        """Get top users by specific stat."""
        result = await session.execute(
            select(User)
            .where(User.chat_id == chat_id)
            .order_by(desc(getattr(User, stat_name)))
            .limit(limit)
        )
        return result.scalars().all()


class EventCRUD:
    """CRUD operations for Event model."""

    @staticmethod
    async def create(
        session: AsyncSession,
        chat_id: int,
        event_type: EventType,
        description: str,
        user_id: Optional[int] = None
    ) -> Event:
        """Create new event."""
        event = Event(
            chat_id=chat_id,
            event_type=event_type,
            user_id=user_id,
            description=description
        )
        session.add(event)
        await session.commit()
        await session.refresh(event)
        return event

    @staticmethod
    async def get_recent(
        session: AsyncSession,
        chat_id: int,
        limit: int = 10
    ) -> List[Event]:
        """Get recent events for a chat."""
        result = await session.execute(
            select(Event)
            .where(Event.chat_id == chat_id)
            .order_by(desc(Event.created_at))
            .limit(limit)
        )
        return result.scalars().all()

    @staticmethod
    async def count_by_type(
        session: AsyncSession,
        chat_id: int,
        event_type: EventType
    ) -> int:
        """Count events of specific type."""
        result = await session.execute(
            select(func.count(Event.id))
            .where(
                Event.chat_id == chat_id,
                Event.event_type == event_type
            )
        )
        return result.scalar()
