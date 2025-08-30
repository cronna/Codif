"""
Модуль для кэширования данных и улучшения производительности
"""
import json
import time
from typing import Any, Optional, Dict, Callable
from functools import wraps
import logging

logger = logging.getLogger(__name__)

class CacheManager:
    """Менеджер кэширования для улучшения производительности"""
    
    def __init__(self, default_ttl: int = 300):  # 5 минут по умолчанию
        self._cache: Dict[str, Dict[str, Any]] = {}
        self.default_ttl = default_ttl
    
    def get(self, key: str) -> Optional[Any]:
        """Получение значения из кэша"""
        if key not in self._cache:
            return None
        
        cache_item = self._cache[key]
        
        # Проверяем TTL
        if time.time() > cache_item['expires_at']:
            del self._cache[key]
            return None
        
        return cache_item['value']
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Сохранение значения в кэш"""
        ttl = ttl or self.default_ttl
        self._cache[key] = {
            'value': value,
            'expires_at': time.time() + ttl,
            'created_at': time.time()
        }
    
    def delete(self, key: str) -> bool:
        """Удаление значения из кэша"""
        if key in self._cache:
            del self._cache[key]
            return True
        return False
    
    def clear(self) -> None:
        """Очистка всего кэша"""
        self._cache.clear()
    
    def cleanup_expired(self) -> int:
        """Очистка просроченных записей"""
        current_time = time.time()
        expired_keys = [
            key for key, item in self._cache.items()
            if current_time > item['expires_at']
        ]
        
        for key in expired_keys:
            del self._cache[key]
        
        return len(expired_keys)
    
    def get_stats(self) -> Dict[str, Any]:
        """Получение статистики кэша"""
        current_time = time.time()
        active_items = sum(
            1 for item in self._cache.values()
            if current_time <= item['expires_at']
        )
        
        return {
            'total_items': len(self._cache),
            'active_items': active_items,
            'expired_items': len(self._cache) - active_items
        }

# Глобальный экземпляр кэша
cache = CacheManager()

def cached(ttl: int = 300, key_func: Optional[Callable] = None):
    """Декоратор для кэширования результатов функций"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Генерируем ключ кэша
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                cache_key = f"{func.__name__}:{hash(str(args) + str(sorted(kwargs.items())))}"
            
            # Пытаемся получить из кэша
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                logger.debug(f"Cache hit for {cache_key}")
                return cached_result
            
            # Выполняем функцию и кэшируем результат
            result = func(*args, **kwargs)
            cache.set(cache_key, result, ttl)
            logger.debug(f"Cache miss for {cache_key}, result cached")
            
            return result
        return wrapper
    return decorator

class DataValidator:
    """Валидатор данных для защиты от ошибок"""
    
    @staticmethod
    def validate_user_input(text: str, max_length: int = 1000, min_length: int = 1) -> tuple[bool, str]:
        """Валидация пользовательского ввода"""
        if not text or not text.strip():
            return False, "Текст не может быть пустым"
        
        text = text.strip()
        
        if len(text) < min_length:
            return False, f"Текст слишком короткий (минимум {min_length} символов)"
        
        if len(text) > max_length:
            return False, f"Текст слишком длинный (максимум {max_length} символов)"
        
        # Проверка на подозрительные символы
        suspicious_chars = ['<script', 'javascript:', 'onclick=', 'onerror=']
        text_lower = text.lower()
        
        for char in suspicious_chars:
            if char in text_lower:
                return False, "Текст содержит недопустимые символы"
        
        return True, text
    
    @staticmethod
    def validate_budget(budget: str) -> tuple[bool, str]:
        """Валидация бюджета"""
        if not budget or not budget.strip():
            return False, "Бюджет не может быть пустым"
        
        budget = budget.strip()
        
        # Проверяем, что это разумный бюджет
        budget_lower = budget.lower()
        valid_patterns = [
            'руб', 'рублей', 'тысяч', 'тыс', '$', 'долларов', 'евро', '€',
            'договорная', 'обсуждаемый', 'по договоренности'
        ]
        
        has_valid_pattern = any(pattern in budget_lower for pattern in valid_patterns)
        has_numbers = any(char.isdigit() for char in budget)
        
        if not (has_valid_pattern or has_numbers):
            return False, "Укажите корректный бюджет (например: '50000 руб.' или 'договорная')"
        
        return True, budget
    
    @staticmethod
    def validate_phone(phone: str) -> tuple[bool, str]:
        """Валидация номера телефона"""
        if not phone:
            return False, "Номер телефона не может быть пустым"
        
        # Убираем все кроме цифр и +
        cleaned_phone = ''.join(char for char in phone if char.isdigit() or char == '+')
        
        # Проверяем формат
        if len(cleaned_phone) < 10:
            return False, "Номер телефона слишком короткий"
        
        if len(cleaned_phone) > 15:
            return False, "Номер телефона слишком длинный"
        
        # Проверяем российские номера
        if cleaned_phone.startswith('+7') or cleaned_phone.startswith('8'):
            if len(cleaned_phone) not in [11, 12]:  # +7XXXXXXXXXX или 8XXXXXXXXXX
                return False, "Некорректный формат российского номера"
        
        return True, cleaned_phone
    
    @staticmethod
    def validate_card_number(card_number: str) -> tuple[bool, str]:
        """Валидация номера карты (базовая)"""
        if not card_number:
            return False, "Номер карты не может быть пустым"
        
        # Убираем пробелы и дефисы
        cleaned_card = ''.join(char for char in card_number if char.isdigit())
        
        if len(cleaned_card) < 13 or len(cleaned_card) > 19:
            return False, "Некорректная длина номера карты"
        
        # Маскируем номер для безопасности
        masked_card = cleaned_card[:4] + '*' * (len(cleaned_card) - 8) + cleaned_card[-4:]
        
        return True, masked_card

# Функции для работы с кэшем статистики
@cached(ttl=60)  # Кэшируем на 1 минуту
def get_admin_stats_cached():
    """Кэшированная статистика для админа"""
    from app.db.database import DatabaseManager
    return DatabaseManager.get_admin_dashboard_stats()

@cached(ttl=300)  # Кэшируем на 5 минут
def get_portfolio_cached():
    """Кэшированное портфолио"""
    from app.db.database import DatabaseManager
    return DatabaseManager.get_all_portfolio_projects()

def invalidate_admin_cache():
    """Инвалидация кэша админа при изменениях"""
    cache.delete("get_admin_stats_cached:")
    
def invalidate_portfolio_cache():
    """Инвалидация кэша портфолио при изменениях"""
    cache.delete("get_portfolio_cached:")
