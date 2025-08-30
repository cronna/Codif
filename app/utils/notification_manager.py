import logging
from typing import List, Optional
from aiogram import Bot
from config import config

logger = logging.getLogger(__name__)

class NotificationManager:
    """Менеджер для отправки уведомлений администраторам"""
    
    def __init__(self):
        self.admin_ids = config.ADMIN_IDS
        self.notification_queue = []
        self.max_retries = 3
    
    async def notify_admins(
        self, 
        message: str, 
        bot: Bot, 
        parse_mode: str = "HTML"
    ) -> List[int]:
        """Отправка уведомления всем администраторам"""
        successful_sends = []
        
        for admin_id in self.admin_ids:
            try:
                await bot.send_message(
                    chat_id=admin_id,
                    text=message,
                    parse_mode=parse_mode
                )
                successful_sends.append(admin_id)
                logger.info(f"Notification sent to admin {admin_id}")
                
            except Exception as e:
                logger.error(f"Failed to send notification to admin {admin_id}: {e}")
        
        return successful_sends
    
    async def notify_admin(
        self, 
        admin_id: int, 
        message: str, 
        bot: Bot, 
        parse_mode: str = "HTML"
    ) -> bool:
        """Отправка уведомления конкретному администратору"""
        try:
            await bot.send_message(
                chat_id=admin_id,
                text=message,
                parse_mode=parse_mode
            )
            logger.info(f"Notification sent to admin {admin_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send notification to admin {admin_id}: {e}")
            return False
    
    async def notify_new_order(
        self, 
        username: str, 
        user_id: int, 
        project_name: str, 
        budget: str, 
        bot: Bot
    ) -> List[int]:
        """Уведомление о новой заявке на разработку"""
        message = (
            f"📋 <b>Новая заявка на разработку!</b>\n\n"
            f"👤 Пользователь: @{username}\n"
            f"🆔 ID: {user_id}\n"
            f"📝 Проект: {project_name}\n"
            f"💰 Бюджет: {budget}\n\n"
            f"⏰ Время: {self._get_current_time()}"
        )
        
        return await self.notify_admins(message, bot)
    
    async def notify_new_application(
        self, 
        username: str, 
        user_id: int, 
        full_name: str, 
        role: str, 
        experience: str, 
        bot: Bot
    ) -> List[int]:
        """Уведомление о новой заявке в команду"""
        message = (
            f"👥 <b>Новая заявка в команду!</b>\n\n"
            f"👤 Пользователь: @{username}\n"
            f"🆔 ID: {user_id}\n"
            f"📝 Имя: {full_name}\n"
            f"🎭 Роль: {role}\n"
            f"💼 Опыт: {experience[:100]}...\n\n"
            f"⏰ Время: {self._get_current_time()}"
        )
        
        return await self.notify_admins(message, bot)
    
    async def notify_new_consultation(
        self, 
        username: str, 
        user_id: int, 
        question: str, 
        bot: Bot
    ) -> List[int]:
        """Уведомление о новом запросе на консультацию"""
        message = (
            f"💬 <b>Новый запрос на консультацию!</b>\n\n"
            f"👤 Пользователь: @{username}\n"
            f"🆔 ID: {user_id}\n"
            f"❓ Вопрос: {question[:200]}...\n\n"
            f"⏰ Время: {self._get_current_time()}"
        )
        
        return await self.notify_admins(message, bot)
    
    async def notify_portfolio_update(
        self, 
        action: str, 
        project_title: str, 
        admin_username: str, 
        bot: Bot
    ) -> List[int]:
        """Уведомление об обновлении портфолио"""
        action_emoji = {
            "add": "➕",
            "edit": "✏️", 
            "delete": "🗑️"
        }
        
        message = (
            f"{action_emoji.get(action, '📝')} <b>Обновление портфолио</b>\n\n"
            f"🔧 Действие: {action.capitalize()}\n"
            f"📝 Проект: {project_title}\n"
            f"👤 Админ: @{admin_username}\n\n"
            f"⏰ Время: {self._get_current_time()}"
        )
        
        return await self.notify_admins(message, bot)
    
    async def notify_error(
        self, 
        error_message: str, 
        context: str, 
        bot: Bot
    ) -> List[int]:
        """Уведомление об ошибке"""
        message = (
            f"⚠️ <b>Ошибка в боте!</b>\n\n"
            f"🔧 Контекст: {context}\n"
            f"❌ Ошибка: {error_message}\n\n"
            f"⏰ Время: {self._get_current_time()}"
        )
        
        return await self.notify_admins(message, bot)
    
    async def notify_stats(
        self, 
        stats: dict, 
        bot: Bot
    ) -> List[int]:
        """Уведомление со статистикой"""
        message = (
            f"📊 <b>Статистика бота</b>\n\n"
            f"👥 Всего пользователей: {stats.get('total_users', 0)}\n"
            f"📋 Заявок на разработку: {stats.get('orders', 0)}\n"
            f"👥 Заявок в команду: {stats.get('applications', 0)}\n"
            f"💬 Консультаций: {stats.get('consultations', 0)}\n"
            f"🎨 Проектов в портфолио: {stats.get('portfolio', 0)}\n\n"
            f"⏰ Время: {self._get_current_time()}"
        )
        
        return await self.notify_admins(message, bot)
    
    def _get_current_time(self) -> str:
        """Получение текущего времени в читаемом формате"""
        from datetime import datetime
        return datetime.now().strftime("%d.%m.%Y %H:%M:%S")
    
    def add_admin(self, admin_id: int) -> None:
        """Добавление нового администратора"""
        if admin_id not in self.admin_ids:
            self.admin_ids.append(admin_id)
            logger.info(f"Added new admin: {admin_id}")
    
    def remove_admin(self, admin_id: int) -> None:
        """Удаление администратора"""
        if admin_id in self.admin_ids:
            self.admin_ids.remove(admin_id)
            logger.info(f"Removed admin: {admin_id}")
    
    def get_admin_list(self) -> List[int]:
        """Получение списка администраторов"""
        return self.admin_ids.copy()
    
    def is_admin(self, user_id: int) -> bool:
        """Проверка, является ли пользователь администратором"""
        return user_id in self.admin_ids

# Синглтон-экземпляр для удобного импорта
notification_manager = NotificationManager()
