import asyncio
import logging
import signal
import sys
from contextlib import asynccontextmanager

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web

from config import config
from app.handlers.admin import admin_router
from app.handlers.main import main_router
from app.utils.scheduler import start_scheduler, stop_scheduler
from app.utils.performance_monitor import performance_monitor

# Настройка логирования
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format=config.LOG_FORMAT,
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

class BotApplication:
    """Основной класс приложения бота"""
    
    def __init__(self):
        self.bot = Bot(token=config.BOT_TOKEN)
        self.dp = Dispatcher(storage=MemoryStorage())
        self.app = None
        self.webhook_path = None
        self.webhook_url = None
        
        # Регистрация роутеров
        self.dp.include_router(main_router)
        self.dp.include_router(admin_router)
        
        # Обработчики сигналов для graceful shutdown
        self._setup_signal_handlers()
    
    def _setup_signal_handlers(self):
        """Настройка обработчиков сигналов"""
        for sig in (signal.SIGINT, signal.SIGTERM):
            signal.signal(sig, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Обработчик сигналов для graceful shutdown"""
        logger.info(f"Received signal {signum}, shutting down gracefully...")
        asyncio.create_task(self.shutdown())
    
    async def setup_webhook(self, webhook_url: str, webhook_path: str = "/webhook"):
        """Настройка webhook"""
        try:
            self.webhook_url = webhook_url
            self.webhook_path = webhook_path
            
            # Установка webhook
            await self.bot.set_webhook(
                url=f"{webhook_url}{webhook_path}",
                drop_pending_updates=True
            )
            
            # Создание aiohttp приложения
            self.app = web.Application()
            
            # Настройка webhook handler
            webhook_handler = SimpleRequestHandler(
                dispatcher=self.dp,
                bot=self.bot
            )
            webhook_handler.register(self.app, path=webhook_path)
            
            logger.info(f"Webhook set to {webhook_url}{webhook_path}")
            
        except Exception as e:
            logger.error(f"Failed to setup webhook: {e}")
            raise
    
    async def setup_polling(self):
        """Настройка polling"""
        try:
            # Удаляем webhook если был установлен
            await self.bot.delete_webhook(drop_pending_updates=True)
            logger.info("Polling mode enabled")
            
        except Exception as e:
            logger.error(f"Failed to setup polling: {e}")
            raise
    
    async def start_polling(self):
        """Запуск бота в режиме polling с планировщиком задач"""
        try:
            logger.info("Starting bot in polling mode...")
            
            # Запускаем планировщик задач в фоне
            scheduler_task = asyncio.create_task(start_scheduler())
            
            # Запускаем polling
            await self.dp.start_polling(self.bot)
            
        except Exception as e:
            logger.error(f"Error in polling mode: {e}")
            stop_scheduler()  # Останавливаем планировщик при ошибке
            raise
    
    async def start_webhook(self, host: str = "0.0.0.0", port: int = 8000):
        """Запуск бота в режиме webhook"""
        try:
            if not self.app:
                raise ValueError("Webhook not set up. Call setup_webhook() first.")
            
            logger.info(f"Starting webhook server on {host}:{port}")
            web.run_app(
                self.app,
                host=host,
                port=port,
                access_log=logger
            )
            
        except Exception as e:
            logger.error(f"Error in webhook mode: {e}")
            raise
    
    async def shutdown(self):
        """Graceful shutdown бота"""
        try:
            logger.info("Shutting down bot...")
            
            # Остановка планировщика задач
            stop_scheduler()
            
            # Остановка polling если запущен
            if self.dp._polling:
                await self.dp.stop_polling()
            
            # Удаление webhook
            await self.bot.delete_webhook()
            
            # Закрытие сессии бота
            await self.bot.session.close()
            
            logger.info("Bot shutdown completed")
            
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
        finally:
            # Завершение программы
            sys.exit(0)
    
    async def health_check(self):
        """Проверка здоровья бота"""
        try:
            me = await self.bot.get_me()
            logger.info(f"Bot health check passed: @{me.username}")
            return True
        except Exception as e:
            logger.error(f"Bot health check failed: {e}")
            return False

@asynccontextmanager
async def bot_lifetime():
    """Контекстный менеджер для жизненного цикла бота"""
    bot_app = BotApplication()
    try:
        yield bot_app
    finally:
        await bot_app.shutdown()

async def main():
    """Главная функция запуска"""
    try:
        logger.info("Starting Codif Bot...")
        
        async with bot_lifetime() as bot_app:
            # Проверка здоровья бота
            if not await bot_app.health_check():
                logger.error("Bot health check failed, exiting...")
                return
            
            # Определение режима запуска
            if len(sys.argv) > 1 and sys.argv[1] == "webhook":
                # Webhook режим
                webhook_url = sys.argv[2] if len(sys.argv) > 2 else "https://your-domain.com"
                await bot_app.setup_webhook(webhook_url)
                await bot_app.start_webhook()
            else:
                # Polling режим (по умолчанию)
                await bot_app.start_polling()
    
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down...")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise

if __name__ == "__main__":
    try:
        # Запуск бота
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Failed to start bot: {e}")
        sys.exit(1)



