from typing import List, Optional
import re
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton
from config import config

class KeyboardBuilder:
    """Билдер для создания клавиатур с улучшенным UX"""
    
    @staticmethod
    def _normalize_bot_url(url: Optional[str]) -> Optional[str]:
        """Нормализует введенную ссылку на бота/канал к корректному HTTP(S)/tg:// URL.
        Возвращает None, если нормализация невозможна.
        """
        if not url:
            return None
        u = url.strip()
        if not u:
            return None
        # tg deep link
        if u.startswith("tg://"):
            return u
        # handle @username
        if u.startswith("@"):
            return f"https://t.me/{u[1:]}"
        # handle bare username
        if re.fullmatch(r"[A-Za-z0-9_]{5,32}", u):
            return f"https://t.me/{u}"
        # handle t.me without scheme
        if u.startswith("t.me/") or u.startswith("telegram.me/") or u.startswith("telegram.dog/"):
            return f"https://{u}"
        # pass through http(s)
        if u.startswith("http://") or u.startswith("https://"):
            return u
        return None

    @staticmethod
    def main_menu(user_id: int, is_admin: bool = False) -> InlineKeyboardBuilder:
        """Главное меню с современным дизайном"""
        builder = InlineKeyboardBuilder()
        
        # Основные кнопки с красивыми эмодзи
        builder.button(
            text=f"{config.EMOJI['rocket']} Заказать", 
            callback_data="order_bot"
        )
        builder.button(
            text=f"{config.EMOJI['handshake']} В команду", 
            callback_data="join_team"
        )
        
        # Вторая строка
        builder.button(
            text=f"{config.EMOJI['trophy']} Портфолио", 
            callback_data="portfolio"
        )
        builder.button(
            text=f"{config.EMOJI['bulb']} Консультация", 
            callback_data="consultation"
        )
        
        # Третья строка
        builder.button(
            text=f"{config.EMOJI['gift']} Реферальная система", 
            callback_data="referral_system"
        )
        
        # Канал отдельной кнопкой
        builder.button(
            text=f"{config.EMOJI['star']} Подписаться на Codif", 
            url=config.CHANNEL_LINK
        )
        
        # Админская кнопка
        if is_admin:
            builder.button(
                text=f"{config.EMOJI['crown']} Админ-панель", 
                callback_data="admin_panel"
            )
        
        # Красивое расположение: 2x2 + 1 + 1 + админ
        if is_admin:
            builder.adjust(2, 2, 1, 1, 1)
        else:
            builder.adjust(2, 2, 1, 1)
        return builder.as_markup()

    @staticmethod
    def order_type_selection() -> InlineKeyboardBuilder:
        """Выбор типа заказа: бот или мини-приложение"""
        builder = InlineKeyboardBuilder()
        
        builder.button(
            text=f"{config.EMOJI['robot']} Телеграм бот", 
            callback_data="order_type_bot"
        )
        builder.button(
            text=f"{config.EMOJI['phone']} Мини-приложение", 
            callback_data="order_type_miniapp"
        )
        
        builder.button(
            text=f"{config.EMOJI['back']} Назад", 
            callback_data="back_to_main"
        )
        
        builder.adjust(1, 1, 1)
        return builder.as_markup()

    @staticmethod
    def back_button(callback_data: str = "cancel_questionnaire") -> InlineKeyboardBuilder:
        """Стильная кнопка возврата"""
        builder = InlineKeyboardBuilder()
        builder.button(
            text=f"{config.EMOJI['back']} Назад", 
            callback_data=callback_data
        )
        return builder.as_markup()

    @staticmethod
    def portfolio_navigation(
        current_index: int,
        total: int,
        show_details: bool = False,
        bot_url: Optional[str] = None,
    ) -> InlineKeyboardBuilder:
        """Навигация по портфолио с прогресс-баром"""
        builder = InlineKeyboardBuilder()
        
        # Прогресс-бар
        progress = f"📊 {current_index + 1}/{total}"
        
        # Кнопки навигации
        if total > 1:
            builder.button(
                text=f"{config.EMOJI['back']}", 
                callback_data=f"portfolio_prev_{current_index}"
            )
            builder.button(
                text=f"{config.EMOJI['next']}", 
                callback_data=f"portfolio_next_{current_index}"
            )
            # Метка прогресса (неактивная кнопка)
            builder.button(
                text=progress,
                callback_data="portfolio_progress"
            )
        
        # Кнопка подробностей
        if not show_details:
            builder.button(
                text=f"{config.EMOJI['info']} Подробнее", 
                callback_data=f"portfolio_details_{current_index}"
            )
        else:
            builder.button(
                text=f"{config.EMOJI['back']} К списку", 
                callback_data=f"portfolio_back_{current_index}"
            )
        
        # Кнопка перехода к боту (если есть)
        safe_url = KeyboardBuilder._normalize_bot_url(bot_url)
        if safe_url:
            builder.button(
                text=f"{config.EMOJI['next']} Перейти к боту",
                url=safe_url
            )

        # Кнопка возврата
        builder.button(
            text=f"{config.EMOJI['back']} В главное меню", 
            callback_data="back_to_main"
        )
        
        # Настройка расположения
        if total > 1:
            if safe_url:
                builder.adjust(2, 1, 1, 1, 1)
            else:
                builder.adjust(2, 1, 1, 1)
        else:
            # Без навигации: прогресс как 1/1
            builder.button(
                text=progress,
                callback_data="portfolio_progress"
            )
            if safe_url:
                builder.adjust(1, 1, 1, 1)
            else:
                builder.adjust(1, 1, 1)
        
        return builder.as_markup()

    @staticmethod
    def admin_menu() -> InlineKeyboardBuilder:
        """Админ-панель с современным дизайном и мониторингом"""
        builder = InlineKeyboardBuilder()
        
        # Основные разделы админки
        builder.button(
            text=f"{config.EMOJI['orders']} Заказы", 
            callback_data="admin_orders"
        )
        builder.button(
            text=f"{config.EMOJI['team']} Команда", 
            callback_data="admin_team"
        )
        builder.button(
            text=f"{config.EMOJI['consultation']} Консультации", 
            callback_data="admin_consultations"
        )
        builder.button(
            text=f"{config.EMOJI['diamond']} Рефералы", 
            callback_data="admin_referrals"
        )
        
        # Новые функции мониторинга
        builder.button(
            text="📊 Мониторинг", 
            callback_data="system_monitor"
        )
        builder.button(
            text="⚙️ Настройки", 
            callback_data="admin_settings"
        )
        
        builder.button(
            text=f"{config.EMOJI['back']} Назад", 
            callback_data="back_to_main"
        )
        
        builder.adjust(2, 2, 2, 1)
        return builder.as_markup()

    @staticmethod
    def admin_section_menu(section_name: str, back_to: str = "admin_panel") -> InlineKeyboardBuilder:
        """Меню раздела админки с корректными callback-ами списка"""
        builder = InlineKeyboardBuilder()

        # Маппинг названий разделов к ключам callback
        section_key_map = {
            "заявок на разработку": "orders",
            "заявки на разработку": "orders",
            "orders": "orders",
            "заявок в команду": "applications",
            "заявки в команду": "applications",
            "applications": "applications",
            "консультаций": "consultations",
            "консультации": "consultations",
            "consultations": "consultations",
        }
        normalized = section_name.strip().lower()
        section_key = section_key_map.get(normalized, normalized)

        builder.button(
            text=f"📋 Список {section_name}",
            callback_data=f"admin_{section_key}_list"
        )
        builder.button(
            text=f"{config.EMOJI['back']} В админ-меню",
            callback_data=back_to
        )

        builder.adjust(1)
        return builder.as_markup()

    @staticmethod
    def item_actions(
        item_id: int, 
        user_id: int, 
        current_index: int, 
        total: int,
        item_type: str,
        show_contact: bool = True
    ) -> InlineKeyboardBuilder:
        """Действия с элементом (заявка, консультация и т.д.)"""
        builder = InlineKeyboardBuilder()
        
        # Навигация
        if total > 1:
            builder.button(
                text=f"{config.EMOJI['back']}", 
                callback_data=f"{item_type}_prev_{current_index}"
            )
            builder.button(
                text=f"{config.EMOJI['next']}", 
                callback_data=f"{item_type}_next_{current_index}"
            )
        
        # Основные действия для заказов
        if item_type == "order":
            builder.button(
                text=f"{config.EMOJI['money']} Установить цену", 
                callback_data=f"order_set_price_{item_id}"
            )
            builder.button(
                text=f"{config.EMOJI['error']} Отклонить", 
                callback_data=f"{item_type}_reject_{item_id}"
            )
        else:
            # Для остальных типов - стандартные действия
            builder.button(
                text=f"{config.EMOJI['success']} Принять", 
                callback_data=f"{item_type}_accept_{item_id}"
            )
            builder.button(
                text=f"{config.EMOJI['error']} Отклонить", 
                callback_data=f"{item_type}_reject_{item_id}"
            )
        
        # Специальные действия для консультаций
        if item_type == "consult":
            builder.button(
                text=f"✉️ Ответить", 
                callback_data=f"consult_reply_{item_id}"
            )
            builder.button(
                text=f"{config.EMOJI['success']} Завершить", 
                callback_data=f"consult_complete_{item_id}"
            )
        
        # Связь с пользователем
        if show_contact:
            builder.button(
                text=f"{config.EMOJI['contact']} Связаться", 
                url=f"tg://user?id={user_id}"
            )
        
        # Возврат к списку (с маппингом ключей)
        list_key_map = {
            "order": "orders",
            "app": "applications",
            "consult": "consultations",
        }
        list_key = list_key_map.get(item_type, f"{item_type}s")
        builder.button(
            text=f"{config.EMOJI['back']} К списку",
            callback_data=f"admin_{list_key}_list"
        )
        
        # Настройка расположения
        if total > 1:
            if item_type == "order":
                builder.adjust(2, 2, 2, 1, 1)  # Navigation, order actions, contact, back
            elif item_type == "consult":
                builder.adjust(2, 2, 2, 1, 1)  # Navigation, actions, special actions, contact, back
            else:
                builder.adjust(2, 2, 1, 1)  # Navigation, actions, contact, back
        else:
            if item_type == "order":
                builder.adjust(2, 2, 1)  # Order actions, contact, back
            elif item_type == "consult":
                builder.adjust(2, 2, 1, 1)  # Actions, special actions, contact, back
            else:
                builder.adjust(2, 1, 1)  # Actions, contact, back
        
        return builder.as_markup()

    @staticmethod
    def portfolio_management() -> InlineKeyboardBuilder:
        """Управление портфолио"""
        builder = InlineKeyboardBuilder()
        
        builder.button(
            text=f"{config.EMOJI['add']} Добавить проект", 
            callback_data="portfolio_add"
        )
        builder.button(
            text=f"{config.EMOJI['edit']} Редактировать проект", 
            callback_data="portfolio_edit_list"
        )
        builder.button(
            text=f"{config.EMOJI['delete']} Удалить проект", 
            callback_data="portfolio_delete_list"
        )
        builder.button(
            text=f"{config.EMOJI['back']} В админ-меню", 
            callback_data="admin_panel"
        )
        
        builder.adjust(1)
        return builder.as_markup()

    @staticmethod
    def portfolio_edit(project_id: int) -> InlineKeyboardBuilder:
        """Редактирование проекта"""
        builder = InlineKeyboardBuilder()
        
        builder.button(
            text=f"{config.EMOJI['edit']} Название", 
            callback_data=f"pedit_title_{project_id}"
        )
        builder.button(
            text=f"{config.EMOJI['edit']} Описание", 
            callback_data=f"pedit_desc_{project_id}"
        )
        builder.button(
            text=f"{config.EMOJI['edit']} Детали", 
            callback_data=f"pedit_details_{project_id}"
        )
        builder.button(
            text=f"{config.EMOJI['edit']} Стоимость", 
            callback_data=f"pedit_cost_{project_id}"
        )
        builder.button(
            text=f"{config.EMOJI['edit']} Технологии", 
            callback_data=f"pedit_tech_{project_id}"
        )
        builder.button(
            text=f"{config.EMOJI['edit']} Длительность", 
            callback_data=f"pedit_duration_{project_id}"
        )
        builder.button(
            text=f"{config.EMOJI['edit']} Видео",
            callback_data=f"pedit_video_{project_id}"
        )
        builder.button(
            text=f"{config.EMOJI['edit']} Ссылка на бота",
            callback_data=f"pedit_bot_{project_id}"
        )
        builder.button(
            text=f"{config.EMOJI['back']} К управлению", 
            callback_data="admin_portfolio"
        )
        
        builder.adjust(2, 2, 2, 2, 1)
        return builder.as_markup()

    @staticmethod
    def portfolio_delete_confirm(project_id: int) -> InlineKeyboardBuilder:
        """Подтверждение удаления проекта"""
        builder = InlineKeyboardBuilder()
        
        builder.button(
            text=f"{config.EMOJI['success']} Да, удалить", 
            callback_data=f"pdelete_confirm_{project_id}"
        )
        builder.button(
            text=f"{config.EMOJI['error']} Отмена", 
            callback_data="admin_portfolio"
        )
        
        return builder.as_markup()

    @staticmethod
    def project_list(projects: List, action_prefix: str) -> InlineKeyboardBuilder:
        """Список проектов для выбора"""
        builder = InlineKeyboardBuilder()
        
        for project in projects:
            # Обрезаем название если слишком длинное
            title = project.title[:30] + "..." if len(project.title) > 30 else project.title
            builder.button(
                text=title, 
                callback_data=f"{action_prefix}_{project.id}"
            )
        
        builder.button(
            text=f"{config.EMOJI['back']} Назад", 
            callback_data="admin_portfolio"
        )
        
        builder.adjust(1)
        return builder.as_markup()

    @staticmethod
    def back_to_admin_menu() -> InlineKeyboardBuilder:
        """Возврат в админ-меню"""
        builder = InlineKeyboardBuilder()
        builder.button(
            text=f"{config.EMOJI['back']} В админ-меню", 
            callback_data="admin_panel"
        )
        return builder.as_markup()

    @staticmethod
    def success_action(action: str = "back_to_main") -> InlineKeyboardBuilder:
        """Стильная кнопка после успешного действия"""
        builder = InlineKeyboardBuilder()
        builder.button(
            text=f"{config.EMOJI['sparkles']} В главное меню", 
            callback_data=action
        )
        return builder.as_markup()

# Создаем экземпляр билдера
kb = KeyboardBuilder()

# Функции для обратной совместимости
def main_menu_keyboard(user_id: int, is_admin: bool = False):
    return kb.main_menu(user_id, is_admin)

def back_keyboard():
    return kb.back_button()

def portfolio_keyboard(current_index: int, total: int):
    return kb.portfolio_navigation(current_index, total)

def back_to_portfolio_keyboard(current_index: int):
    return kb.portfolio_navigation(current_index, 1, show_details=True)

def admin_menu_keyboard():
    return kb.admin_menu()

def admin_orders_keyboard():
    return kb.admin_section_menu("заявок на разработку")

def team_orders_keyboard():
    return kb.admin_section_menu("заявок в команду")

def cons_orders_keyboard():
    return kb.admin_section_menu("консультаций")

def order_actions_keyboard(order_id: int, user_id: int, current_index: int, total: int):
    return kb.item_actions(order_id, user_id, current_index, total, "order")

def application_actions_keyboard(app_id: int, user_id: int, current_index: int, total: int):
    return kb.item_actions(app_id, user_id, current_index, total, "app")

def consultation_actions_keyboard(req_id: int, user_id: int, current_index: int, total: int):
    return kb.item_actions(req_id, user_id, current_index, total, "consult")

def portfolio_manage_keyboard():
    return kb.portfolio_management()

def portfolio_edit_keyboard(project_id: int):
    return kb.portfolio_edit(project_id)

def portfolio_delete_confirm_keyboard(project_id: int):
    return kb.portfolio_delete_confirm(project_id)

def back_to_admin_menu_keyboard():
    return kb.back_to_admin_menu()

def portfolio_project_list_keyboard(projects, action_prefix: str):
    return kb.project_list(projects, action_prefix)

# ===== Referral keyboards (helpers used by referral handlers) =====
def back_button():
    """Wrapper to keep compatibility with handlers expecting back_button()."""
    return kb.back_button()

def referral_main_menu_keyboard():
    """Main menu for referral system."""
    builder = InlineKeyboardBuilder()
    builder.button(text=f"{config.EMOJI['chart']} Статистика", callback_data="referral_stats")
    builder.button(text=f"{config.EMOJI['link']} Моя ссылка", callback_data="referral_link")
    builder.button(text=f"{config.EMOJI['wallet']} Настроить выплаты", callback_data="referral_setup_wallet")
    builder.button(text=f"{config.EMOJI['history']} Начисления", callback_data="referral_earnings")
    builder.button(text=f"{config.EMOJI['money']} Запросить выплату", callback_data="request_payout")
    builder.button(text=f"{config.EMOJI['back']} В главное меню", callback_data="back_to_main")
    builder.adjust(2, 1, 1, 1)
    return builder.as_markup()

def referral_wallet_methods_keyboard():
    """Wallet method selection keyboard (card or SBP)."""
    builder = InlineKeyboardBuilder()
    builder.button(text=f"{config.EMOJI['card']} Банковская карта", callback_data="wallet_method_card")
    builder.button(text=f"{config.EMOJI['phone']} СБП (по номеру)", callback_data="wallet_method_sbp")
    builder.button(text=f"{config.EMOJI['back']} Назад", callback_data="referral_system")
    builder.adjust(1, 1, 1)
    return builder.as_markup()

def referral_earnings_actions_keyboard():
    """Actions below earnings list."""
    builder = InlineKeyboardBuilder()
    builder.button(text=f"{config.EMOJI['money']} Запросить выплату", callback_data="request_payout")
    builder.button(text=f"{config.EMOJI['back']} Назад", callback_data="referral_system")
    builder.adjust(1, 1)
    return builder.as_markup()

# ===== Admin keyboards for order management and referral payouts =====
def admin_referral_payouts_keyboard():
    """Admin referral payouts management."""
    builder = InlineKeyboardBuilder()
    builder.button(text="📋 Список запросов на выплату", callback_data="admin_payouts_list")
    builder.button(text=f"{config.EMOJI['back']} В админ-меню", callback_data="admin_panel")
    builder.adjust(1, 1)
    return builder.as_markup()

def admin_payment_confirmations_keyboard():
    """Admin payment confirmations management."""
    builder = InlineKeyboardBuilder()
    builder.button(text="📋 Принятые заказы", callback_data="admin_accepted_orders_list")
    builder.button(text=f"{config.EMOJI['back']} В админ-меню", callback_data="admin_panel")
    builder.adjust(1, 1)
    return builder.as_markup()

def payout_actions_keyboard(payout_id: int, current_index: int, total: int):
    """Actions for referral payout management."""
    builder = InlineKeyboardBuilder()
    
    # Navigation
    if total > 1:
        builder.button(
            text=f"{config.EMOJI['back']}", 
            callback_data=f"payout_prev_{current_index}"
        )
        builder.button(
            text=f"{config.EMOJI['next']}", 
            callback_data=f"payout_next_{current_index}"
        )
    
    # Actions
    builder.button(
        text=f"{config.EMOJI['success']} Одобрить", 
        callback_data=f"payout_approve_{payout_id}"
    )
    builder.button(
        text=f"{config.EMOJI['error']} Отклонить", 
        callback_data=f"payout_reject_{payout_id}"
    )
    builder.button(
        text=f"✅ Выплачено", 
        callback_data=f"payout_complete_{payout_id}"
    )
    
    # Back to list
    builder.button(
        text=f"{config.EMOJI['back']} К списку",
        callback_data="admin_payouts_list"
    )
    
    # Layout
    if total > 1:
        builder.adjust(2, 2, 1, 1)
    else:
        builder.adjust(2, 1, 1)
    
    return builder.as_markup()

def accepted_order_actions_keyboard(order_id: int, current_index: int, total: int):
    """Actions for accepted orders (payment confirmation)."""
    builder = InlineKeyboardBuilder()
    
    # Navigation
    if total > 1:
        builder.button(
            text=f"{config.EMOJI['back']}", 
            callback_data=f"accepted_order_prev_{current_index}"
        )
        builder.button(
            text=f"{config.EMOJI['next']}", 
            callback_data=f"accepted_order_next_{current_index}"
        )
    
    # Actions
    builder.button(
        text=f"✅ Подтвердить оплату", 
        callback_data=f"confirm_payment_{order_id}"
    )
    builder.button(
        text=f"{config.EMOJI['edit']} Изменить цену", 
        callback_data=f"order_edit_price_{order_id}"
    )
    
    # Back to list
    builder.button(
        text=f"{config.EMOJI['back']} К списку",
        callback_data="admin_accepted_orders_list"
    )
    
    # Layout
    if total > 1:
        builder.adjust(2, 2, 1)
    else:
        builder.adjust(2, 1)
    
    return builder.as_markup()