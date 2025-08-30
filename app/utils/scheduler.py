"""
Модуль для автоматических задач и очистки кэша
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Callable, Dict, Any
from app.utils.cache_manager import cache

logger = logging.getLogger(__name__)

class TaskScheduler:
    """Планировщик автоматических задач"""
    
    def __init__(self):
        self.tasks: Dict[str, Dict[str, Any]] = {}
        self.running = False
    
    def add_task(self, name: str, func: Callable, interval_minutes: int):
        """Добавить задачу в планировщик"""
        self.tasks[name] = {
            'func': func,
            'interval': interval_minutes,
            'last_run': None,
            'next_run': datetime.now() + timedelta(minutes=interval_minutes)
        }
        logger.info(f"Added scheduled task: {name} (every {interval_minutes} minutes)")
    
    async def start(self):
        """Запустить планировщик"""
        self.running = True
        logger.info("Task scheduler started")
        
        while self.running:
            try:
                current_time = datetime.now()
                
                for task_name, task_info in self.tasks.items():
                    if current_time >= task_info['next_run']:
                        try:
                            # Выполняем задачу
                            if asyncio.iscoroutinefunction(task_info['func']):
                                await task_info['func']()
                            else:
                                task_info['func']()
                            
                            # Обновляем время следующего запуска
                            task_info['last_run'] = current_time
                            task_info['next_run'] = current_time + timedelta(minutes=task_info['interval'])
                            
                            logger.debug(f"Executed scheduled task: {task_name}")
                            
                        except Exception as e:
                            logger.error(f"Error executing scheduled task {task_name}: {e}")
                
                # Спим 30 секунд перед следующей проверкой
                await asyncio.sleep(30)
                
            except Exception as e:
                logger.error(f"Error in task scheduler: {e}")
                await asyncio.sleep(60)  # Ждем минуту при ошибке
    
    def stop(self):
        """Остановить планировщик"""
        self.running = False
        logger.info("Task scheduler stopped")

# Глобальный планировщик
scheduler = TaskScheduler()

# Автоматические задачи
def cleanup_expired_cache():
    """Очистка просроченного кэша"""
    try:
        expired_count = cache.cleanup_expired()
        if expired_count > 0:
            logger.info(f"Cleaned up {expired_count} expired cache entries")
    except Exception as e:
        logger.error(f"Error cleaning up cache: {e}")

def log_cache_stats():
    """Логирование статистики кэша"""
    try:
        stats = cache.get_stats()
        logger.info(f"Cache stats: {stats['active_items']} active, {stats['expired_items']} expired")
    except Exception as e:
        logger.error(f"Error getting cache stats: {e}")

def cleanup_old_sessions():
    """Очистка старых сессий пользователей"""
    try:
        from app.db.database import db
        # Удаляем сессии старше 24 часов
        cutoff_time = datetime.now() - timedelta(hours=24)
        # Здесь можно добавить логику очистки старых сессий
        logger.debug("Cleaned up old user sessions")
    except Exception as e:
        logger.error(f"Error cleaning up sessions: {e}")

# Инициализация автоматических задач
def init_scheduled_tasks():
    """Инициализация автоматических задач"""
    # Очистка кэша каждые 15 минут
    scheduler.add_task("cache_cleanup", cleanup_expired_cache, 15)
    
    # Статистика кэша каждый час
    scheduler.add_task("cache_stats", log_cache_stats, 60)
    
    # Очистка старых сессий каждые 6 часов
    scheduler.add_task("session_cleanup", cleanup_old_sessions, 360)
    
    logger.info("Scheduled tasks initialized")

async def start_scheduler():
    """Запуск планировщика задач"""
    init_scheduled_tasks()
    await scheduler.start()

def stop_scheduler():
    """Остановка планировщика задач"""
    scheduler.stop()
