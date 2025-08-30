"""
Модуль для мониторинга производительности бота
"""
import time
import psutil
import logging
from typing import Dict, Any, Optional
from functools import wraps
from datetime import datetime, timedelta
import asyncio

logger = logging.getLogger(__name__)

class PerformanceMonitor:
    """Монитор производительности"""
    
    def __init__(self):
        self.metrics = {
            'requests_count': 0,
            'avg_response_time': 0.0,
            'errors_count': 0,
            'active_users': set(),
            'peak_memory': 0.0,
            'start_time': time.time()
        }
        self.response_times = []
    
    def record_request(self, user_id: int, response_time: float, success: bool = True):
        """Записать метрики запроса"""
        self.metrics['requests_count'] += 1
        self.metrics['active_users'].add(user_id)
        
        if not success:
            self.metrics['errors_count'] += 1
        
        # Обновляем среднее время ответа
        self.response_times.append(response_time)
        if len(self.response_times) > 1000:  # Храним только последние 1000 запросов
            self.response_times.pop(0)
        
        self.metrics['avg_response_time'] = sum(self.response_times) / len(self.response_times)
        
        # Обновляем пиковое использование памяти
        current_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        if current_memory > self.metrics['peak_memory']:
            self.metrics['peak_memory'] = current_memory
    
    def get_system_stats(self) -> Dict[str, Any]:
        """Получить системную статистику"""
        process = psutil.Process()
        
        return {
            'cpu_percent': psutil.cpu_percent(interval=1),
            'memory_mb': process.memory_info().rss / 1024 / 1024,
            'memory_percent': process.memory_percent(),
            'threads_count': process.num_threads(),
            'uptime_hours': (time.time() - self.metrics['start_time']) / 3600
        }
    
    def get_bot_stats(self) -> Dict[str, Any]:
        """Получить статистику бота"""
        return {
            'total_requests': self.metrics['requests_count'],
            'avg_response_time_ms': round(self.metrics['avg_response_time'] * 1000, 2),
            'errors_count': self.metrics['errors_count'],
            'active_users_count': len(self.metrics['active_users']),
            'error_rate_percent': round((self.metrics['errors_count'] / max(self.metrics['requests_count'], 1)) * 100, 2),
            'peak_memory_mb': round(self.metrics['peak_memory'], 2)
        }
    
    def format_stats_message(self) -> str:
        """Форматировать статистику для отправки"""
        system_stats = self.get_system_stats()
        bot_stats = self.get_bot_stats()
        
        return f"""
🖥️ <b>Системная статистика</b>
━━━━━━━━━━━━━━━━━━━━━━

💾 <b>Память:</b> {system_stats['memory_mb']:.1f} MB ({system_stats['memory_percent']:.1f}%)
🔥 <b>CPU:</b> {system_stats['cpu_percent']:.1f}%
🧵 <b>Потоки:</b> {system_stats['threads_count']}
⏰ <b>Время работы:</b> {system_stats['uptime_hours']:.1f} ч

🤖 <b>Статистика бота</b>
━━━━━━━━━━━━━━━━━━━━━━

📊 <b>Запросов:</b> {bot_stats['total_requests']}
⚡ <b>Среднее время ответа:</b> {bot_stats['avg_response_time_ms']} мс
❌ <b>Ошибок:</b> {bot_stats['errors_count']} ({bot_stats['error_rate_percent']}%)
👥 <b>Активных пользователей:</b> {bot_stats['active_users_count']}
📈 <b>Пик памяти:</b> {bot_stats['peak_memory_mb']} MB
"""

# Глобальный монитор
performance_monitor = PerformanceMonitor()

def monitor_performance(func_name: str = ""):
    """Декоратор для мониторинга производительности функций"""
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            user_id = None
            success = True
            
            # Пытаемся извлечь user_id из аргументов
            try:
                if args and hasattr(args[0], 'from_user'):
                    user_id = args[0].from_user.id
                elif args and hasattr(args[0], 'message') and hasattr(args[0].message, 'from_user'):
                    user_id = args[0].message.from_user.id
            except:
                pass
            
            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                success = False
                logger.error(f"Error in {func_name or func.__name__}: {e}")
                raise
            finally:
                response_time = time.time() - start_time
                if user_id:
                    performance_monitor.record_request(user_id, response_time, success)
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            success = True
            
            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                success = False
                logger.error(f"Error in {func_name or func.__name__}: {e}")
                raise
            finally:
                response_time = time.time() - start_time
                # Для синхронных функций не записываем метрики пользователей
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    return decorator

class HealthChecker:
    """Проверка здоровья системы"""
    
    @staticmethod
    def check_database_health() -> tuple[bool, str]:
        """Проверка состояния базы данных"""
        try:
            from app.db.database import DatabaseManager
            # Простой запрос для проверки соединения
            DatabaseManager.get_client_orders_count()
            return True, "Database OK"
        except Exception as e:
            return False, f"Database Error: {str(e)}"
    
    @staticmethod
    def check_memory_usage() -> tuple[bool, str]:
        """Проверка использования памяти"""
        try:
            memory_percent = psutil.Process().memory_percent()
            if memory_percent > 80:
                return False, f"High memory usage: {memory_percent:.1f}%"
            return True, f"Memory usage OK: {memory_percent:.1f}%"
        except Exception as e:
            return False, f"Memory check error: {str(e)}"
    
    @staticmethod
    def check_disk_space() -> tuple[bool, str]:
        """Проверка дискового пространства"""
        try:
            disk_usage = psutil.disk_usage('/')
            free_percent = (disk_usage.free / disk_usage.total) * 100
            if free_percent < 10:
                return False, f"Low disk space: {free_percent:.1f}% free"
            return True, f"Disk space OK: {free_percent:.1f}% free"
        except Exception as e:
            return False, f"Disk check error: {str(e)}"
    
    @staticmethod
    def get_health_report() -> Dict[str, Any]:
        """Получить полный отчет о здоровье системы"""
        checks = [
            ("Database", HealthChecker.check_database_health()),
            ("Memory", HealthChecker.check_memory_usage()),
            ("Disk", HealthChecker.check_disk_space())
        ]
        
        all_healthy = all(check[1][0] for check in checks)
        
        return {
            'healthy': all_healthy,
            'checks': {name: {'status': status, 'message': message} for name, (status, message) in checks},
            'timestamp': datetime.now().isoformat()
        }
