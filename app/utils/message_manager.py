import logging
from typing import Optional, Dict, Any, List
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InputMediaVideo, MessageEntity

logger = logging.getLogger(__name__)

class MessageManager:
    """Менеджер для управления сообщениями бота"""
    
    def __init__(self):
        self.user_main_messages: Dict[int, int] = {}  # {user_id: message_id}
        self.last_question_message_id: Dict[int, int] = {}  # {user_id: message_id}
        self.success_message_id: Dict[int, int] = {}  # {user_id: message_id}
    
    def set_main_message(self, user_id: int, message_id: int) -> None:
        """Установка ID главного сообщения пользователя"""
        self.user_main_messages[user_id] = message_id
    
    def get_main_message(self, user_id: int) -> Optional[int]:
        """Получение ID главного сообщения пользователя"""
        return self.user_main_messages.get(user_id)
    
    def clear_main_message(self, user_id: int) -> None:
        """Очистка ID главного сообщения пользователя"""
        if user_id in self.user_main_messages:
            del self.user_main_messages[user_id]
    
    def set_last_question(self, user_id: int, message_id: int) -> None:
        """Установка ID последнего вопроса"""
        self.last_question_message_id[user_id] = message_id
    
    def get_last_question(self, user_id: int) -> Optional[int]:
        """Получение ID последнего вопроса"""
        return self.last_question_message_id.get(user_id)
    
    def clear_last_question(self, user_id: int) -> None:
        """Очистка ID последнего вопроса"""
        if user_id in self.last_question_message_id:
            del self.last_question_message_id[user_id]
    
    def set_success_message(self, user_id: int, message_id: int) -> None:
        """Установка ID сообщения об успехе"""
        self.success_message_id[user_id] = message_id
    
    def get_success_message(self, user_id: int) -> Optional[int]:
        """Получение ID сообщения об успехе"""
        return self.success_message_id.get(user_id)
    
    def clear_success_message(self, user_id: int) -> None:
        """Очистка ID сообщения об успехе"""
        if user_id in self.success_message_id:
            del self.success_message_id[user_id]
    
    async def edit_main_message(
        self, 
        user_id: int, 
        text: str, 
        message_id: Optional[int] = None, 
        reply_markup: Optional[InlineKeyboardMarkup] = None,
        bot: Optional[Bot] = None,
        entities: Optional[List[MessageEntity]] = None,
    ) -> bool:
        """Редактирование главного сообщения пользователя"""
        try:
            if message_id is None:
                message_id = self.get_main_message(user_id)

            if message_id is None or bot is None:
                return False

            # 1) Пытаемся отредактировать как текстовое сообщение
            try:
                await bot.edit_message_text(
                    chat_id=user_id,
                    message_id=message_id,
                    text=text,
                    reply_markup=reply_markup,
                    parse_mode=None if entities else "HTML",
                    entities=entities,
                )
                return True
            except Exception as edit_text_err:
                # 2) Если сообщение было медиа — пробуем отредактировать подпись
                try:
                    await bot.edit_message_caption(
                        chat_id=user_id,
                        message_id=message_id,
                        caption=text,
                        reply_markup=reply_markup,
                        parse_mode=None if entities else "HTML",
                        caption_entities=entities,
                    )
                    return True
                except Exception as edit_caption_err:
                    # 3) В крайнем случае — отправляем новое сообщение и запоминаем его как главное
                    try:
                        sent = await bot.send_message(
                            chat_id=user_id,
                            text=text,
                            reply_markup=reply_markup,
                            parse_mode=None if entities else "HTML",
                            entities=entities,
                        )
                        self.set_main_message(user_id, sent.message_id)
                        return True
                    except Exception as send_err:
                        logger.error(
                            f"Error editing main message for user {user_id}: text_err={edit_text_err}; "
                            f"caption_err={edit_caption_err}; send_err={send_err}"
                        )
                        return False
        except Exception as e:
            logger.error(f"Unexpected error in edit_main_message for user {user_id}: {e}")
            return False

    async def show_main_video(
        self,
        user_id: int,
        caption: str,
        video_url: str,
        reply_markup: Optional[InlineKeyboardMarkup] = None,
        bot: Optional[Bot] = None,
        caption_entities: Optional[List[MessageEntity]] = None,
    ) -> bool:
        """Показывает (или заменяет) главное сообщение на видео с подписью.
        Если редактирование невозможно, отправляет новое и запоминает его как главное.
        """
        try:
            if bot is None:
                return False

            main_id = self.get_main_message(user_id)
            if main_id:
                # Попытка заменить медиа
                try:
                    media = InputMediaVideo(
                        media=video_url,
                        caption=caption,
                        parse_mode=None if caption_entities else "HTML",
                        caption_entities=caption_entities,
                    )
                    await bot.edit_message_media(
                        chat_id=user_id,
                        message_id=main_id,
                        media=media,
                        reply_markup=reply_markup,
                    )
                    return True
                except Exception:
                    # Если нельзя заменить (например, предыдущее сообщение было текстом)
                    pass

            sent = await bot.send_video(
                chat_id=user_id,
                video=video_url,
                caption=caption,
                reply_markup=reply_markup,
                parse_mode=None if caption_entities else "HTML",
                caption_entities=caption_entities,
            )
            self.set_main_message(user_id, sent.message_id)
            return True
        except Exception as e:
            logger.error(f"Error showing main video for user {user_id}: {e}")
            return False

    @staticmethod
    def build_custom_emoji_entities(text: str, emoji_char_to_id: Dict[str, str]) -> List[MessageEntity]:
        """Создает entities для кастомных (premium) эмодзи по их символам в тексте.
        emoji_char_to_id: {"🎨": "custom_emoji_id", ...}
        Возвращает список MessageEntity с корректными UTF-16 offset/length.
        """
        entities: List[MessageEntity] = []
        if not emoji_char_to_id:
            return entities

        def utf16_offset(s: str) -> int:
            return len(s.encode("utf-16-le")) // 2

        text_len = len(text)
        i = 0
        while i < text_len:
            ch = text[i]
            if ch in emoji_char_to_id and emoji_char_to_id[ch]:
                offset_units = utf16_offset(text[:i])
                entities.append(
                    MessageEntity(
                        type="custom_emoji",
                        offset=offset_units,
                        length=1,
                        custom_emoji_id=emoji_char_to_id[ch],
                    )
                )
            i += 1
        return entities
    
    async def delete_message(
        self, 
        user_id: int, 
        message_id: int, 
        bot: Bot
    ) -> bool:
        """Удаление сообщения"""
        try:
            await bot.delete_message(user_id, message_id)
            return True
        except Exception as e:
            logger.error(f"Error deleting message {message_id} for user {user_id}: {e}")
            return False
    
    async def delete_last_question(self, user_id: int, bot: Bot) -> bool:
        """Удаление последнего вопроса"""
        message_id = self.get_last_question(user_id)
        if message_id:
            success = await self.delete_message(user_id, message_id, bot)
            if success:
                self.clear_last_question(user_id)
            return success
        return False
    
    async def delete_success_message(self, user_id: int, bot: Bot) -> bool:
        """Удаление сообщения об успехе"""
        message_id = self.get_success_message(user_id)
        if message_id:
            success = await self.delete_message(user_id, message_id, bot)
            if success:
                self.clear_success_message(user_id)
            return success
        return False
    
    def clear_user_data(self, user_id: int) -> None:
        """Очистка всех данных пользователя"""
        self.clear_main_message(user_id)
        self.clear_last_question(user_id)
        self.clear_success_message(user_id)
    
    def get_user_stats(self) -> Dict[str, int]:
        """Получение статистики по пользователям"""
        return {
            "total_users": len(self.user_main_messages),
            "active_questions": len(self.last_question_message_id),
            "success_messages": len(self.success_message_id)
        }

# Экспортируем синглтон-экземпляр для удобного импорта
message_manager = MessageManager()
