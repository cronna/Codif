import logging
from typing import Optional, Dict, Any, List
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InputMediaVideo, MessageEntity

logger = logging.getLogger(__name__)

class MessageManager:
    
    def __init__(self):
        self.user_main_messages: Dict[int, int] = {}
        self.last_question_message_id: Dict[int, int] = {}
        self.success_message_id: Dict[int, int] = {}
    
    def set_main_message(self, user_id: int, message_id: int) -> None:
        self.user_main_messages[user_id] = message_id
    
    def get_main_message(self, user_id: int) -> Optional[int]:
        return self.user_main_messages.get(user_id)
    
    def clear_main_message(self, user_id: int) -> None:
        if user_id in self.user_main_messages:
            del self.user_main_messages[user_id]
    
    def set_last_question(self, user_id: int, message_id: int) -> None:
        self.last_question_message_id[user_id] = message_id
    
    def get_last_question(self, user_id: int) -> Optional[int]:
        return self.last_question_message_id.get(user_id)
    
    def clear_last_question(self, user_id: int) -> None:
        if user_id in self.last_question_message_id:
            del self.last_question_message_id[user_id]
    
    def set_success_message(self, user_id: int, message_id: int) -> None:
        self.success_message_id[user_id] = message_id
    
    def get_success_message(self, user_id: int) -> Optional[int]:
        return self.success_message_id.get(user_id)
    
    def clear_success_message(self, user_id: int) -> None:
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
        try:
            if message_id is None:
                message_id = self.get_main_message(user_id)

            if message_id is None or bot is None:
                return False

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
        try:
            if bot is None:
                return False

            main_id = self.get_main_message(user_id)
            if main_id:
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
        try:
            await bot.delete_message(user_id, message_id)
            return True
        except Exception as e:
            logger.error(f"Error deleting message {message_id} for user {user_id}: {e}")
            return False
    
    async def delete_last_question(self, user_id: int, bot: Bot) -> bool:
        message_id = self.get_last_question(user_id)
        if message_id:
            success = await self.delete_message(user_id, message_id, bot)
            if success:
                self.clear_last_question(user_id)
            return success
        return False
    
    async def delete_success_message(self, user_id: int, bot: Bot) -> bool:
        message_id = self.get_success_message(user_id)
        if message_id:
            success = await self.delete_message(user_id, message_id, bot)
            if success:
                self.clear_success_message(user_id)
            return success
        return False
    
    def clear_user_data(self, user_id: int) -> None:
        self.clear_main_message(user_id)
        self.clear_last_question(user_id)
        self.clear_success_message(user_id)
    
    def get_user_stats(self) -> Dict[str, int]:
        return {
            "total_users": len(self.user_main_messages),
            "active_questions": len(self.last_question_message_id),
            "success_messages": len(self.success_message_id)
        }

message_manager = MessageManager()
