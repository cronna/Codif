"""
Модуль для создания красивых UI компонентов
"""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from typing import List, Dict, Any, Optional
import math

class UIComponents:
    """Компоненты для создания красивого интерфейса"""
    
    # Эмодзи для различных состояний
    STATUS_EMOJIS = {
        'new': '🆕',
        'accepted': '✅',
        'rejected': '❌',
        'completed': '🎉',
        'paid': '💰',
        'processing': '⏳',
        'pending': '⏰',
        'confirmed': '✔️',
        'failed': '💥'
    }
    
    CATEGORY_EMOJIS = {
        'bot': '🤖',
        'miniapp': '📱',
        'consultation': '💡',
        'team': '🤝',
        'portfolio': '🏆',
        'referral': '💎',
        'admin': '👑',
        'stats': '📊',
        'settings': '⚙️'
    }
    
    @staticmethod
    def create_status_text(status: str, item_type: str = '') -> str:
        """Создание текста статуса с эмодзи"""
        emoji = UIComponents.STATUS_EMOJIS.get(status, '📋')
        status_names = {
            'new': 'Новая',
            'accepted': 'Принята',
            'rejected': 'Отклонена',
            'completed': 'Завершена',
            'paid': 'Оплачена',
            'processing': 'В обработке',
            'pending': 'Ожидает',
            'confirmed': 'Подтверждена',
            'failed': 'Ошибка'
        }
        return f"{emoji} {status_names.get(status, status.title())}"
    
    @staticmethod
    def create_paginated_keyboard(
        items: List[Dict[str, Any]], 
        page: int = 0, 
        per_page: int = 5,
        callback_prefix: str = "item",
        show_navigation: bool = True
    ) -> InlineKeyboardMarkup:
        """Создание клавиатуры с пагинацией"""
        keyboard = InlineKeyboardMarkup(inline_keyboard=[])
        
        total_pages = math.ceil(len(items) / per_page)
        start_idx = page * per_page
        end_idx = start_idx + per_page
        
        # Добавляем элементы текущей страницы
        for item in items[start_idx:end_idx]:
            status_emoji = UIComponents.STATUS_EMOJIS.get(item.get('status', ''), '📋')
            item_title = item.get('title', f"ID: {item.get('id', 'N/A')}")
            button_text = f"{status_emoji} {item_title}"
            
            keyboard.inline_keyboard.append([
                InlineKeyboardButton(
                    text=button_text,
                    callback_data=f"{callback_prefix}_{item.get('id')}"
                )
            ])
        
        # Добавляем навигацию если нужно
        if show_navigation and total_pages > 1:
            nav_buttons = []
            
            if page > 0:
                nav_buttons.append(
                    InlineKeyboardButton(text="⬅️ Назад", callback_data=f"page_{page-1}")
                )
            
            nav_buttons.append(
                InlineKeyboardButton(text=f"📄 {page+1}/{total_pages}", callback_data="current_page")
            )
            
            if page < total_pages - 1:
                nav_buttons.append(
                    InlineKeyboardButton(text="Вперед ➡️", callback_data=f"page_{page+1}")
                )
            
            keyboard.inline_keyboard.append(nav_buttons)
        
        return keyboard
    
    @staticmethod
    def create_action_keyboard(actions: List[Dict[str, str]], back_button: bool = True) -> InlineKeyboardMarkup:
        """Создание клавиатуры с действиями"""
        keyboard = InlineKeyboardMarkup(inline_keyboard=[])
        
        # Группируем кнопки по 2 в ряд для лучшего вида
        for i in range(0, len(actions), 2):
            row = []
            for j in range(2):
                if i + j < len(actions):
                    action = actions[i + j]
                    row.append(InlineKeyboardButton(
                        text=action['text'],
                        callback_data=action['callback']
                    ))
            keyboard.inline_keyboard.append(row)
        
        # Добавляем кнопку "Назад" если нужно
        if back_button:
            keyboard.inline_keyboard.append([
                InlineKeyboardButton(text="🔙 Назад", callback_data="back")
            ])
        
        return keyboard
    
    @staticmethod
    def format_order_info(order: Dict[str, Any]) -> str:
        """Форматирование информации о заказе"""
        status_text = UIComponents.create_status_text(order.get('status', 'new'))
        order_emoji = UIComponents.CATEGORY_EMOJIS.get(order.get('order_type', 'bot'), '🤖')
        
        info = f"""
{order_emoji} <b>Заказ #{order.get('id', 'N/A')}</b>
━━━━━━━━━━━━━━━━━━━━━━

📋 <b>Проект:</b> {order.get('project_name', 'Не указан')}
📊 <b>Статус:</b> {status_text}
💰 <b>Бюджет:</b> {order.get('budget', 'Не указан')}
⏰ <b>Сроки:</b> {order.get('deadlines', 'Не указаны')}

📝 <b>Функционал:</b>
{order.get('functionality', 'Не описан')}
"""
        
        if order.get('final_price'):
            info += f"\n💎 <b>Финальная цена:</b> {order.get('final_price')} руб."
        
        if order.get('admin_notes'):
            info += f"\n📌 <b>Заметки админа:</b>\n{order.get('admin_notes')}"
        
        return info
    
    @staticmethod
    def format_referral_stats(stats: Dict[str, Any]) -> str:
        """Форматирование реферальной статистики"""
        total_earned = stats.get('total_earned', 0)
        total_paid = stats.get('total_paid', 0)
        balance = stats.get('balance', 0)
        total_referrals = stats.get('total_referrals', 0)
        referral_code = stats.get('referral_code', 'N/A')
        
        return f"""💎 <b>Ваша реферальная статистика</b>
━━━━━━━━━━━━━━━━━━━━━━

👥 <b>Приглашено:</b> {total_referrals} человек
💰 <b>Заработано:</b> {total_earned:.2f} руб.
💳 <b>Выплачено:</b> {total_paid:.2f} руб.
💎 <b>Баланс:</b> {balance:.2f} руб.

🔗 <b>Ваш код:</b> <code>{referral_code}</code>
📊 <b>Комиссия:</b> 25% с каждого заказа
"""
    
    @staticmethod
    def create_progress_bar(current: int, total: int, width: int = 10) -> str:
        """Создание текстовой полосы прогресса"""
        if total == 0:
            return "▱" * width
        
        filled = int((current / total) * width)
        empty = width - filled
        
        return "▰" * filled + "▱" * empty
    
    @staticmethod
    def format_admin_summary(data: Dict[str, Any]) -> str:
        """Форматирование сводки для админа"""
        new_orders = data.get('new_orders', 0)
        processing_orders = data.get('processing_orders', 0)
        completed_orders = data.get('completed_orders', 0)
        team_applications = data.get('team_applications', 0)
        consultations = data.get('consultations', 0)
        pending_payouts = data.get('pending_payouts', 0)
        total_revenue = data.get('total_revenue', 0)
        pending_payouts_amount = data.get('pending_payouts_amount', 0)
        
        return f"""👑 <b>Панель администратора</b>
━━━━━━━━━━━━━━━━━━━━━━

📊 <b>Статистика:</b>
• 🆕 Новых заказов: {new_orders}
• ⏳ В обработке: {processing_orders}
• ✅ Завершенных: {completed_orders}
• 👥 Заявок в команду: {team_applications}
• 💡 Консультаций: {consultations}
• 💎 Выплат рефералам: {pending_payouts}

💰 <b>Финансы:</b>
• Общий оборот: {total_revenue:.2f} руб.
• К выплате рефералам: {pending_payouts_amount:.2f} руб.
"""
