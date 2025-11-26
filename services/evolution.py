"""Pet evolution system."""
from typing import Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from database.models import Chat, PetStage, PetType, EventType
from database.crud import ChatCRUD, EventCRUD


class EvolutionSystem:
    """Handle pet evolution logic."""

    # XP thresholds for each stage
    STAGE_THRESHOLDS = {
        PetStage.EGG: 0,
        PetStage.BABY: 100,      # Level 2
        PetStage.TEEN: 500,      # Level 6
        PetStage.ADULT: 1500,    # Level 16
        PetStage.ANCIENT: 5000,  # Level 51
    }

    # Type determination based on behavior counters
    TYPE_THRESHOLDS = {
        PetType.GOBLIN: {"cursing_count": 50},
        PetType.TROLL: {"caps_count": 100, "cursing_count": 30},
        PetType.MEME_CAT: {"meme_count": 50},
        PetType.CYBER_BOT: {"code_count": 50},
        PetType.ANGEL: {"cursing_count": 0, "message_threshold": 200},  # No cursing, lots of messages
    }

    @staticmethod
    def get_next_stage(current_stage: PetStage) -> Optional[PetStage]:
        """Get the next evolution stage."""
        stage_order = [
            PetStage.EGG,
            PetStage.BABY,
            PetStage.TEEN,
            PetStage.ADULT,
            PetStage.ANCIENT
        ]

        try:
            current_index = stage_order.index(current_stage)
            if current_index < len(stage_order) - 1:
                return stage_order[current_index + 1]
        except ValueError:
            pass

        return None

    @staticmethod
    def determine_pet_type(chat: Chat) -> PetType:
        """
        Determine pet type based on chat behavior.
        This is called when evolving from BABY to TEEN.
        """
        # Count total messages (approximate)
        total_interactions = (
            chat.cursing_count +
            chat.meme_count +
            chat.code_count +
            chat.caps_count
        )

        # Check for specific types (order matters - most specific first)

        # Angel: No cursing at all, lots of positive interactions
        if chat.cursing_count == 0 and total_interactions >= 200:
            return PetType.ANGEL

        # Cyber Bot: Lots of code
        if chat.code_count >= 50:
            return PetType.CYBER_BOT

        # Meme Cat: Lots of memes/stickers
        if chat.meme_count >= 50:
            return PetType.MEME_CAT

        # Troll: High caps AND some cursing
        if chat.caps_count >= 100 and chat.cursing_count >= 30:
            return PetType.TROLL

        # Goblin: Lots of cursing
        if chat.cursing_count >= 50:
            return PetType.GOBLIN

        # Default: Normal
        return PetType.NORMAL

    @staticmethod
    async def check_and_evolve(
        session: AsyncSession,
        chat: Chat
    ) -> Tuple[bool, Optional[PetStage], Optional[PetType]]:
        """
        Check if pet should evolve and perform evolution.
        Returns: (evolved, new_stage, new_type)
        """
        if not chat.is_alive:
            return False, None, None

        next_stage = EvolutionSystem.get_next_stage(chat.pet_stage)
        if not next_stage:
            return False, None, None

        # Check if pet has enough XP for next stage
        required_xp = EvolutionSystem.STAGE_THRESHOLDS[next_stage]
        if chat.xp < required_xp:
            return False, None, None

        # Determine new type (only changes at certain stages)
        new_type = chat.pet_type

        if next_stage == PetStage.TEEN:
            # First major evolution - determine type based on chat behavior
            new_type = EvolutionSystem.determine_pet_type(chat)
        elif next_stage == PetStage.ADULT:
            # Keep the type but could add variations here
            pass
        elif next_stage == PetStage.ANCIENT:
            # Ancient stage - keep type
            pass

        # Perform evolution
        await ChatCRUD.evolve(session, chat.chat_id, next_stage, new_type)

        # Log event
        evolution_message = EvolutionSystem.get_evolution_message(
            chat.pet_name,
            next_stage,
            new_type
        )
        await EventCRUD.create(
            session,
            chat.chat_id,
            EventType.EVOLUTION,
            evolution_message
        )

        return True, next_stage, new_type

    @staticmethod
    def get_evolution_message(
        pet_name: str,
        new_stage: PetStage,
        new_type: PetType
    ) -> str:
        """Generate evolution announcement message."""
        stage_messages = {
            PetStage.BABY: f"🎉 {pet_name} вылупился из яйца! Теперь это малыш!",
            PetStage.TEEN: f"🌟 {pet_name} подрос! Эволюция в {new_type.value.upper()}!",
            PetStage.ADULT: f"💪 {pet_name} стал взрослым {new_type.value}!",
            PetStage.ANCIENT: f"👑 {pet_name} достиг древней стадии! Легенда чата!",
        }

        base_message = stage_messages.get(
            new_stage,
            f"{pet_name} эволюционировал!"
        )

        # Add type-specific flavor text for TEEN stage
        if new_stage == PetStage.TEEN:
            type_flavor = {
                PetType.GOBLIN: "\n😈 Вы слишком много ругались! Теперь это гоблин!",
                PetType.TROLL: "\n🧌 Слишком много капса и злости! Это тролль!",
                PetType.MEME_CAT: "\n😸 Мемы и стикеры сделали своё дело! Мем-кот рожден!",
                PetType.CYBER_BOT: "\n🤖 Обсуждение кода привело к созданию кибер-бота!",
                PetType.ANGEL: "\n😇 Дружелюбное общение создало ангела!",
                PetType.NORMAL: "\n🐱 Обычный, но милый питомец!",
            }
            base_message += type_flavor.get(new_type, "")

        return base_message

    @staticmethod
    def get_type_emoji(pet_type: PetType) -> str:
        """Get emoji for pet type."""
        emoji_map = {
            PetType.NORMAL: "🐱",
            PetType.GOBLIN: "👺",
            PetType.TROLL: "🧌",
            PetType.MEME_CAT: "😹",
            PetType.CYBER_BOT: "🤖",
            PetType.ANGEL: "😇",
        }
        return emoji_map.get(pet_type, "❓")

    @staticmethod
    def get_type_description(pet_type: PetType) -> str:
        """Get description for pet type."""
        descriptions = {
            PetType.NORMAL: "Обычный питомец",
            PetType.GOBLIN: "Злобное существо, любит мат и хаос",
            PetType.TROLL: "Провокатор, кормится капсом и конфликтами",
            PetType.MEME_CAT: "Веселый кот, обожает мемы",
            PetType.CYBER_BOT: "Технологичное существо, любит код",
            PetType.ANGEL: "Добрый и светлый питомец",
        }
        return descriptions.get(pet_type, "Неизвестный тип")
