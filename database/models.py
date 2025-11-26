"""Database models for the Tamagochi bot."""
from datetime import datetime
from sqlalchemy import (
    BigInteger, String, Integer, Boolean, DateTime,
    ForeignKey, Text, Float, Enum as SQLEnum
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from typing import Optional, List
import enum


class Base(DeclarativeBase):
    """Base class for all models."""
    pass


class PetStage(enum.Enum):
    """Pet evolution stages."""
    EGG = "egg"
    BABY = "baby"
    TEEN = "teen"
    ADULT = "adult"
    ANCIENT = "ancient"


class PetType(enum.Enum):
    """Pet types based on chat behavior."""
    NORMAL = "normal"          # Default, neutral chat
    GOBLIN = "goblin"          # Chat with lots of cursing
    MEME_CAT = "meme_cat"      # Friendly chat with memes
    CYBER_BOT = "cyber_bot"    # Tech chat with code
    TROLL = "troll"            # Chaotic chat
    ANGEL = "angel"            # Very polite chat


class Chat(Base):
    """Model for group chats (each chat has one pet)."""
    __tablename__ = "chats"

    chat_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    pet_name: Mapped[str] = mapped_column(String(50), default="Питомец")
    pet_stage: Mapped[PetStage] = mapped_column(
        SQLEnum(PetStage),
        default=PetStage.EGG
    )
    pet_type: Mapped[PetType] = mapped_column(
        SQLEnum(PetType),
        default=PetType.NORMAL
    )

    # Stats (0-100)
    hunger: Mapped[int] = mapped_column(Integer, default=100)
    mood: Mapped[int] = mapped_column(Integer, default=100)
    energy: Mapped[int] = mapped_column(Integer, default=100)
    health: Mapped[int] = mapped_column(Integer, default=100)

    # XP and leveling
    xp: Mapped[int] = mapped_column(Integer, default=0)
    level: Mapped[int] = mapped_column(Integer, default=1)

    # Status
    is_alive: Mapped[bool] = mapped_column(Boolean, default=True)
    is_sleeping: Mapped[bool] = mapped_column(Boolean, default=False)

    # Counters for evolution path
    cursing_count: Mapped[int] = mapped_column(Integer, default=0)
    meme_count: Mapped[int] = mapped_column(Integer, default=0)
    code_count: Mapped[int] = mapped_column(Integer, default=0)
    caps_count: Mapped[int] = mapped_column(Integer, default=0)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow
    )
    last_tick: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow
    )
    last_interaction: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True
    )
    death_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True
    )

    # Relationships
    users: Mapped[List["User"]] = relationship(
        "User",
        back_populates="chat",
        cascade="all, delete-orphan"
    )
    events: Mapped[List["Event"]] = relationship(
        "Event",
        back_populates="chat",
        cascade="all, delete-orphan"
    )


class User(Base):
    """Model for user statistics in specific chats."""
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    chat_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("chats.chat_id", ondelete="CASCADE"),
        nullable=False
    )
    username: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    first_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Statistics
    karma_points: Mapped[int] = mapped_column(Integer, default=0)
    feed_count: Mapped[int] = mapped_column(Integer, default=0)
    play_count: Mapped[int] = mapped_column(Integer, default=0)
    message_count: Mapped[int] = mapped_column(Integer, default=0)
    night_disturb_count: Mapped[int] = mapped_column(Integer, default=0)  # Вредитель

    # Gambling stats
    gamble_wins: Mapped[int] = mapped_column(Integer, default=0)
    gamble_losses: Mapped[int] = mapped_column(Integer, default=0)

    # Timestamps
    first_interaction: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow
    )
    last_interaction: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow
    )

    # Relationships
    chat: Mapped["Chat"] = relationship("Chat", back_populates="users")

    def __repr__(self):
        return f"<User {self.user_id} in chat {self.chat_id}>"


class EventType(enum.Enum):
    """Types of events that can occur."""
    BIRTH = "birth"              # Pet was born
    DEATH = "death"              # Pet died
    EVOLUTION = "evolution"      # Pet evolved
    FEED = "feed"                # Someone fed the pet
    PLAY = "play"                # Someone played with pet
    GAMBLE_WIN = "gamble_win"    # Won gambling
    GAMBLE_LOSS = "gamble_loss"  # Lost gambling
    RANDOM_EVENT = "random_event"  # Random event occurred
    CRITICAL_HEALTH = "critical_health"  # Health dropped critically
    NIGHT_DISTURB = "night_disturb"  # Someone woke the pet at night


class Event(Base):
    """Model for logging important events."""
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    chat_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("chats.chat_id", ondelete="CASCADE"),
        nullable=False
    )
    event_type: Mapped[EventType] = mapped_column(SQLEnum(EventType))
    user_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    description: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow
    )

    # Relationships
    chat: Mapped["Chat"] = relationship("Chat", back_populates="events")

    def __repr__(self):
        return f"<Event {self.event_type} in chat {self.chat_id}>"
