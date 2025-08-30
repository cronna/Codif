import logging
import traceback
import functools
from typing import Any, Callable, Optional
from aiogram import types
from aiogram.exceptions import TelegramAPIError

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

class ErrorHandler:
    
    @staticmethod
    def log_error(error: Exception, context: str = "", user_id: Optional[int] = None):
        error_msg = f"Error in {context}: {str(error)}"
        if user_id:
            error_msg += f" | User: {user_id}"
        
        logger.error(error_msg)
        logger.debug(traceback.format_exc())
    
    @staticmethod
    def handle_telegram_error(error: TelegramAPIError, message: types.Message = None):
        user_id = message.from_user.id if message else None
        
        if "message is not modified" in str(error).lower():
            logger.warning(f"Message not modified for user {user_id}")
            return False
        elif "message to edit not found" in str(error).lower():
            logger.warning(f"Message to edit not found for user {user_id}")
            return False
        elif "bot was blocked" in str(error).lower():
            logger.info(f"Bot blocked by user {user_id}")
            return False
        else:
            ErrorHandler.log_error(error, "Telegram API", user_id)
            return True
    
    @staticmethod
    def safe_execute(func: Callable, *args, **kwargs) -> tuple[bool, Any]:
        try:
            result = func(*args, **kwargs)
            return True, result
        except Exception as e:
            ErrorHandler.log_error(e, func.__name__)
            return False, None

def error_handler(context: str = ""):
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except TelegramAPIError as e:
                message = args[0] if args and isinstance(args[0], types.Message) else None
                if ErrorHandler.handle_telegram_error(e, message):
                    raise
            except Exception as e:
                user_id = None
                if args:
                    if isinstance(args[0], types.Message):
                        user_id = args[0].from_user.id
                    elif isinstance(args[0], types.CallbackQuery):
                        user_id = args[0].from_user.id
                
                ErrorHandler.log_error(e, context or func.__name__, user_id)
                raise
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                ErrorHandler.log_error(e, context or func.__name__)
                raise
        
        return async_wrapper if hasattr(func, '__code__') and func.__code__.co_flags & 0x80 else sync_wrapper
    return decorator

def safe_message_send(bot, chat_id: int, text: str, **kwargs) -> bool:
    try:
        bot.send_message(chat_id=chat_id, text=text, **kwargs)
        return True
    except TelegramAPIError as e:
        if "bot was blocked" in str(e).lower():
            logger.info(f"Bot blocked by user {chat_id}")
        else:
            logger.error(f"Failed to send message to {chat_id}: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error sending message to {chat_id}: {e}")
        return False
