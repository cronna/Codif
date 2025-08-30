import logging
from typing import Optional, Dict, Any, List
from aiogram import types, F, Router, Bot
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import config
from app.db.database import db
from app.keyboards import kb
from app.fsm import AdminStates
from app.utils.message_manager import MessageManager
from app.utils.notification_manager import NotificationManager
from app.utils.error_handler import error_handler, ErrorHandler
from app.utils.ui_components import UIComponents
from app.utils.cache_manager import DataValidator, cache, invalidate_admin_cache
from app.utils.performance_monitor import monitor_performance, performance_monitor

admin_router = Router()

# Менеджеры
message_manager = MessageManager()
notification_manager = NotificationManager()

# ================== ОСНОВНЫЕ ФУНКЦИИ АДМИНКИ ================== #

@admin_router.callback_query(F.data == "system_monitor")
@error_handler("system_monitor")
async def system_monitor(callback: types.CallbackQuery, bot: Bot):
    """Мониторинг системы для админов"""
    if callback.from_user.id not in config.ADMIN_IDS:
        await callback.answer("Доступ запрещен!", show_alert=True)
        return
    
    # Получаем статистику производительности
    stats_message = performance_monitor.format_stats_message()
    
    # Добавляем информацию о здоровье системы
    from app.utils.performance_monitor import HealthChecker
    health_report = HealthChecker.get_health_report()
    
    health_status = "✅ Система работает нормально" if health_report['healthy'] else "⚠️ Обнаружены проблемы"
    
    full_message = f"{stats_message}\n\n🏥 <b>Состояние системы:</b> {health_status}"
    
    # Добавляем детали проблем если есть
    if not health_report['healthy']:
        full_message += "\n\n🔍 <b>Детали проблем:</b>"
        for check_name, check_data in health_report['checks'].items():
            if not check_data['status']:
                full_message += f"\n• {check_name}: {check_data['message']}"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Обновить", callback_data="system_monitor")],
        [InlineKeyboardButton(text="🧹 Очистить кэш", callback_data="clear_cache")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_panel")]
    ])
    
    await callback.message.edit_text(full_message, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()

@admin_router.callback_query(F.data == "clear_cache")
@error_handler("clear_cache")
async def clear_cache(callback: types.CallbackQuery, bot: Bot):
    """Очистка кэша системы"""
    if callback.from_user.id not in config.ADMIN_IDS:
        await callback.answer("Доступ запрещен!", show_alert=True)
        return
    
    cache.clear()
    await callback.answer("🧹 Кэш очищен!", show_alert=True)
    
    # Обновляем статистику
    await system_monitor(callback, bot)

@admin_router.callback_query(F.data == "admin_panel")
@error_handler("admin_panel")
@monitor_performance("admin_panel")
async def admin_panel(callback: types.CallbackQuery, state: FSMContext, bot: Bot):
    """Главное меню админ-панели с улучшенной производительностью"""
    if callback.from_user.id not in config.ADMIN_IDS:
        await callback.answer("Доступ запрещен!", show_alert=True)
        return
    
    # Получаем кэшированную статистику
    admin_stats = cache.get("admin_dashboard_stats")
    if not admin_stats:
        admin_stats = db.get_admin_dashboard_stats()
        cache.set("admin_dashboard_stats", admin_stats, ttl=60)  # Кэш на 1 минуту
    
    # Форматируем красивое сообщение
    stats_message = UIComponents.format_admin_summary(admin_stats)
    
    await state.set_state(AdminMenu.main)
    await message_manager.edit_main_message(
        callback.from_user.id,
        stats_message,
        callback.message.message_id,
        kb.admin_menu(),
        bot
    )
    await callback.answer()

# ================== УПРАВЛЕНИЕ ЗАЯВКАМИ НА РАЗРАБОТКУ ================== #

@admin_router.callback_query(F.data == "admin_orders")
async def admin_orders(callback: types.CallbackQuery, state: FSMContext, bot: Bot):
    """Меню управления заявками на разработку"""
    await state.set_state(AdminMenu.client_orders)
    await message_manager.edit_main_message(
        callback.from_user.id,
        "📋 Управление заявками на разработку",
        callback.message.message_id,
        kb.admin_section_menu("заявок на разработку"),
        bot
    )
    await callback.answer()

@admin_router.callback_query(F.data == "admin_orders_list")
async def admin_orders_list(callback: types.CallbackQuery, state: FSMContext, bot: Bot):
    """Список заявок на разработку"""
    orders = db.get_client_orders()
    if not orders:
        await callback.answer("Нет доступных заявок!", show_alert=True)
        return
    
    # Сохраняем список ID и текущий индекс
    order_ids = [order.id for order in orders]
    await state.update_data(order_ids=order_ids, current_index=0)
    
    # Показываем первую заявку
    await show_order_details(callback, order_ids[0], 0, len(order_ids), bot)
    await callback.answer()

async def show_order_details(callback: types.CallbackQuery, order_id: int, current_index: int, total: int, bot: Bot):
    """Детализация заявки на разработку"""
    order = db.get_client_order(order_id)
    if not order:
        await callback.answer("Заявка не найдена!", show_alert=True)
        return
    
    text = (
        f"📋 Заявка #{order.id}\n"
        f"👤 Пользователь: @{order.username}\n"
        f"🔄 Статус: {order.status}\n\n"
        f"<b>Проект:</b> {order.project_name}\n"
        f"<b>Функционал:</b> {order.functionality}\n"
        f"<b>Сроки:</b> {order.deadlines}\n"
        f"<b>Бюджет:</b> {order.budget}"
    )
    
    await message_manager.edit_main_message(
        callback.from_user.id,
        text,
        callback.message.message_id,
        kb.item_actions(order.id, order.user_id, current_index, total, "order"),
        bot
    )

@admin_router.callback_query(F.data.startswith("order_prev_"))
async def order_prev(callback: types.CallbackQuery, state: FSMContext, bot: Bot):
    """Переход к предыдущей заявке"""
    data = await state.get_data()
    order_ids = data.get('order_ids', [])
    current_index = data.get('current_index', 0)
    
    if not order_ids:
        await callback.answer("Нет доступных заявок!", show_alert=True)
        return
    
    new_index = (current_index - 1) % len(order_ids)
    await state.update_data(current_index=new_index)
    await show_order_details(callback, order_ids[new_index], new_index, len(order_ids), bot)
    await callback.answer()

@admin_router.callback_query(F.data.startswith("order_next_"))
async def order_next(callback: types.CallbackQuery, state: FSMContext, bot: Bot):
    """Переход к следующей заявке"""
    data = await state.get_data()
    order_ids = data.get('order_ids', [])
    current_index = data.get('current_index', 0)
    
    if not order_ids:
        await callback.answer("Нет доступных заявок!", show_alert=True)
        return
    
    new_index = (current_index + 1) % len(order_ids)
    await state.update_data(current_index=new_index)
    await show_order_details(callback, order_ids[new_index], new_index, len(order_ids), bot)
    await callback.answer()

@admin_router.callback_query(F.data.startswith("order_accept_"))
async def order_accept(callback: types.CallbackQuery, state: FSMContext, bot: Bot):
    """Принятие заявки на разработку (с удалением)"""
    order_id = int(callback.data.split("_")[2])
    data = await state.get_data()
    order_ids = data.get('order_ids', [])
    current_index = data.get('current_index', 0)
    
    # Удаляем заявку из БД
    if db.delete_client_order(order_id):
        await callback.answer("Заявка принята и удалена!", show_alert=True)
    else:
        await callback.answer("Заявка не найдена!", show_alert=True)
        return
    
    # Обновляем список заявок
    if order_id in order_ids:
        order_ids.remove(order_id)
    
    if not order_ids:
        # Возвращаемся если заявок больше нет
        await admin_orders(callback, state, bot)
        return
    
    # Переходим к следующей заявке
    new_index = current_index
    if current_index >= len(order_ids):
        new_index = len(order_ids) - 1
    
    await state.update_data(order_ids=order_ids, current_index=new_index)
    await show_order_details(callback, order_ids[new_index], new_index, len(order_ids), bot)
    await callback.answer()

@admin_router.callback_query(F.data.startswith("order_reject_"))
async def order_reject(callback: types.CallbackQuery, state: FSMContext, bot: Bot):
    """Отклонение заявки на разработку (с удалением)"""
    order_id = int(callback.data.split("_")[2])
    data = await state.get_data()
    order_ids = data.get('order_ids', [])
    current_index = data.get('current_index', 0)
    
    # Удаляем заявку из БД
    if db.delete_client_order(order_id):
        await callback.answer("Заявка отклонена и удалена!", show_alert=True)
    else:
        await callback.answer("Заявка не найдена!", show_alert=True)
        return
    
    # Обновляем список заявок
    if order_id in order_ids:
        order_ids.remove(order_id)
    
    if not order_ids:
        # Возвращаемся если заявок больше нет
        await admin_orders(callback, state, bot)
        return
    
    # Переходим к следующей заявке
    new_index = current_index
    if current_index >= len(order_ids):
        new_index = len(order_ids) - 1
    
    await state.update_data(order_ids=order_ids, current_index=new_index)
    await show_order_details(callback, order_ids[new_index], new_index, len(order_ids), bot)
    await callback.answer()

@admin_router.callback_query(F.data.startswith("order_contact_"))
async def order_contact(callback: types.CallbackQuery, state: FSMContext, bot: Bot):
    """Связь с клиентом по заявке"""
    parts = callback.data.split("_")
    order_id = int(parts[2])
    user_id = int(parts[3])
    
    await callback.answer(f"Ссылка для связи: tg://user?id={user_id}", show_alert=True)
    data = await state.get_data()
    current_index = data.get('current_index', 0)
    total = len(data.get('order_ids', []))
    await show_order_details(callback, order_id, current_index, total, bot)
    await callback.answer()

# ================== УПРАВЛЕНИЕ ЗАЯВКАМИ В КОМАНДУ ================== #

@admin_router.callback_query(F.data == "admin_applications")
async def admin_applications(callback: types.CallbackQuery, state: FSMContext, bot: Bot):
    """Меню управления заявками в команду"""
    await state.set_state(AdminMenu.team_applications)
    await message_manager.edit_main_message(
        callback.from_user.id,
        "👥 Управление заявками в команду",
        callback.message.message_id,
        kb.admin_section_menu("заявок в команду"),
        bot
    )
    await callback.answer()

@admin_router.callback_query(F.data == "admin_applications_list")
async def admin_applications_list(callback: types.CallbackQuery, state: FSMContext, bot: Bot):
    """Список заявок в команду"""
    applications = db.get_team_applications()
    if not applications:
        await callback.answer("Нет доступных заявок!", show_alert=True)
        return
    
    # Сохраняем список ID и текущий индекс
    app_ids = [app.id for app in applications]
    await state.update_data(app_ids=app_ids, current_index=0)
    
    # Показываем первую заявку
    await show_application_details(callback, app_ids[0], 0, len(app_ids), bot)
    await callback.answer()

async def show_application_details(callback: types.CallbackQuery, app_id: int, current_index: int, total: int, bot: Bot):
    """Детализация заявки в команду"""
    app = db.get_team_application(app_id)
    if not app:
        await callback.answer("Заявка не найдена!", show_alert=True)
        return
    
    text = (
        f"👥 Заявка #{app.id}\n"
        f"👤 Пользователь: @{app.username}\n"
        f"🔄 Статус: {app.status}\n\n"
        f"<b>Имя:</b> {app.full_name}\n"
        f"<b>Возраст:</b> {app.age}\n"
        f"<b>Опыт:</b> {app.experience}\n"
        f"<b>Стек:</b> {app.stack}\n"
        f"<b>О себе:</b> {app.about}\n"
        f"<b>Мотивация:</b> {app.motivation}\n"
        f"<b>Роль:</b> {app.role}"
    )
    
    await message_manager.edit_main_message(
        callback.from_user.id,
        text,
        callback.message.message_id,
        kb.item_actions(app.id, app.user_id, current_index, total, "app"),
        bot
    )

@admin_router.callback_query(F.data.startswith("app_prev_"))
async def app_prev(callback: types.CallbackQuery, state: FSMContext, bot: Bot):
    """Переход к предыдущей заявке"""
    data = await state.get_data()
    app_ids = data.get('app_ids', [])
    current_index = data.get('current_index', 0)
    
    if not app_ids:
        await callback.answer("Нет доступных заявок!", show_alert=True)
        return
    
    new_index = (current_index - 1) % len(app_ids)
    await state.update_data(current_index=new_index)
    await show_application_details(callback, app_ids[new_index], new_index, len(app_ids), bot)
    await callback.answer()

@admin_router.callback_query(F.data.startswith("app_next_"))
async def app_next(callback: types.CallbackQuery, state: FSMContext, bot: Bot):
    """Переход к следующей заявке"""
    data = await state.get_data()
    app_ids = data.get('app_ids', [])
    current_index = data.get('current_index', 0)
    
    if not app_ids:
        await callback.answer("Нет доступных заявок!", show_alert=True)
        return
    
    new_index = (current_index + 1) % len(app_ids)
    await state.update_data(current_index=new_index)
    await show_application_details(callback, app_ids[new_index], new_index, len(app_ids), bot)
    await callback.answer()

@admin_router.callback_query(F.data.startswith("app_accept_"))
async def app_accept(callback: types.CallbackQuery, state: FSMContext, bot: Bot):
    """Принятие заявки в команду (с удалением)"""
    app_id = int(callback.data.split("_")[2])
    data = await state.get_data()
    app_ids = data.get('app_ids', [])
    current_index = data.get('current_index', 0)
    
    # Удаляем заявку из БД
    if db.delete_team_application(app_id):
        await callback.answer("Заявка принята и удалена!", show_alert=True)
    else:
        await callback.answer("Заявка не найдена!", show_alert=True)
        return
    
    # Обновляем список заявок
    if app_id in app_ids:
        app_ids.remove(app_id)
    
    if not app_ids:
        # Возвращаемся если заявок больше нет
        await admin_applications(callback, state, bot)
        return
    
    # Переходим к следующей заявке
    new_index = current_index
    if current_index >= len(app_ids):
        new_index = len(app_ids) - 1
    
    await state.update_data(app_ids=app_ids, current_index=new_index)
    await show_application_details(callback, app_ids[new_index], new_index, len(app_ids), bot)
    await callback.answer()

@admin_router.callback_query(F.data.startswith("app_reject_"))
async def app_reject(callback: types.CallbackQuery, state: FSMContext, bot: Bot):
    """Отклонение заявки в команду (с удалением)"""
    app_id = int(callback.data.split("_")[2])
    data = await state.get_data()
    app_ids = data.get('app_ids', [])
    current_index = data.get('current_index', 0)
    
    # Удаляем заявку из БД
    if db.delete_team_application(app_id):
        await callback.answer("Заявка отклонена и удалена!", show_alert=True)
    else:
        await callback.answer("Заявка не найдена!", show_alert=True)
        return
    
    # Обновляем список заявок
    if app_id in app_ids:
        app_ids.remove(app_id)
    
    if not app_ids:
        # Возвращаемся если заявок больше нет
        await admin_applications(callback, state, bot)
        return
    
    # Переходим к следующей заявке
    new_index = current_index
    if current_index >= len(app_ids):
        new_index = len(app_ids) - 1
    
    await state.update_data(app_ids=app_ids, current_index=new_index)
    await show_application_details(callback, app_ids[new_index], new_index, len(app_ids), bot)
    await callback.answer()

@admin_router.callback_query(F.data.startswith("app_contact_"))
async def app_contact(callback: types.CallbackQuery, state: FSMContext):
    """Связь с соискателем"""
    parts = callback.data.split("_")
    app_id = int(parts[2])
    user_id = int(parts[3])
    
    await callback.answer(f"Ссылка для связи: tg://user?id={user_id}", show_alert=True)
    data = await state.get_data()
    current_index = data.get('current_index', 0)
    total = len(data.get('app_ids', []))
    await show_application_details(callback, app_id, current_index, total)

# ================== УПРАВЛЕНИЕ КОНСУЛЬТАЦИЯМИ ================== #

@admin_router.callback_query(F.data == "admin_consultations")
async def admin_consultations(callback: types.CallbackQuery, state: FSMContext, bot: Bot):
    """Меню управления консультациями"""
    await state.set_state(AdminMenu.consultations)
    await message_manager.edit_main_message(
        callback.from_user.id,
        "💬 Управление консультациями",
        callback.message.message_id,
        kb.admin_section_menu("консультаций"),
        bot
    )
    await callback.answer()

@admin_router.callback_query(F.data == "admin_consultations_list")
async def admin_consultations_list(callback: types.CallbackQuery, state: FSMContext, bot: Bot):
    """Список запросов на консультацию"""
    consultations = db.get_consultation_requests()
    if not consultations:
        await callback.answer("Нет доступных запросов!", show_alert=True)
        return
    
    # Сохраняем список ID и текущий индекс
    req_ids = [req.id for req in consultations]
    await state.update_data(req_ids=req_ids, current_index=0)
    
    # Показываем первую консультацию
    await show_consultation_details(callback, req_ids[0], 0, len(req_ids), bot)
    await callback.answer()

async def show_consultation_details(callback: types.CallbackQuery, req_id: int, current_index: int, total: int, bot: Bot):
    """Детализация запроса на консультацию"""
    req = db.get_consultation_request(req_id)
    if not req:
        await callback.answer("Запрос не найден!", show_alert=True)
        return
    
    text = (
        f"💬 Консультация #{req.id}\n"
        f"👤 Пользователь: @{req.username}\n"
        f"🔄 Статус: {req.status}\n\n"
        f"<b>Вопрос:</b>\n{req.question}"
    )
    
    await message_manager.edit_main_message(
        callback.from_user.id,
        text,
        callback.message.message_id,
        kb.item_actions(req.id, req.user_id, current_index, total, "consult"),
        bot
    )

@admin_router.callback_query(F.data.startswith("consult_prev_"))
async def consult_prev(callback: types.CallbackQuery, state: FSMContext, bot: Bot):
    """Переход к предыдущей консультации"""
    data = await state.get_data()
    req_ids = data.get('req_ids', [])
    current_index = data.get('current_index', 0)
    
    if not req_ids:
        await callback.answer("Нет доступных запросов!", show_alert=True)
        return
    
    new_index = (current_index - 1) % len(req_ids)
    await state.update_data(current_index=new_index)
    await show_consultation_details(callback, req_ids[new_index], new_index, len(req_ids), bot)
    await callback.answer()

@admin_router.callback_query(F.data.startswith("consult_next_"))
async def consult_next(callback: types.CallbackQuery, state: FSMContext, bot: Bot):
    """Переход к следующей консультации"""
    data = await state.get_data()
    req_ids = data.get('req_ids', [])
    current_index = data.get('current_index', 0)
    
    if not req_ids:
        await callback.answer("Нет доступных запросов!", show_alert=True)
        return
    
    new_index = (current_index + 1) % len(req_ids)
    await state.update_data(current_index=new_index)
    await show_consultation_details(callback, req_ids[new_index], new_index, len(req_ids), bot)
    await callback.answer()

@admin_router.callback_query(F.data.startswith("consult_reply_"))
async def consult_reply(callback: types.CallbackQuery, state: FSMContext):
    """Ответ на консультацию"""
    req_id = int(callback.data.split("_")[2])
    await state.set_state(AdminResponse.consultation)
    await state.update_data(req_id=req_id)
    
    await callback.message.answer(
        "Введите ваш ответ пользователю:",
        reply_markup=kb.back_to_admin_menu()
    )
    await callback.answer()

@admin_router.message(AdminResponse.consultation)
async def process_consult_reply(message: types.Message, state: FSMContext, bot: Bot):
    """Обработка ответа на консультацию"""
    data = await state.get_data()
    req_id = data['req_id']
    
    req = db.get_consultation_request(req_id)
    if req:
        # Отправляем ответ пользователю
        try:
            await bot.send_message(
                req.user_id,
                f"✉️ Ответ на ваш вопрос (#{req_id}):\n\n{message.text}"
            )
            db.update_consultation_request(req_id, {"status": "answered"})
            await message.answer("✅ Ответ отправлен пользователю!")
        except Exception as e:
            await message.answer(f"❌ Ошибка отправки: {str(e)}")
    else:
        await message.answer("❌ Запрос не найден!")
    
    await state.clear()
    await bot.delete_message(message.chat.id, message.message_id)

@admin_router.callback_query(F.data.startswith("consult_contact_"))
async def consult_contact(callback: types.CallbackQuery, state: FSMContext):
    """Связь по консультации"""
    parts = callback.data.split("_")
    req_id = int(parts[2])
    user_id = int(parts[3])
    
    await callback.answer(f"Ссылка для связи: tg://user?id={user_id}", show_alert=True)
    data = await state.get_data()
    current_index = data.get('current_index', 0)
    total = len(data.get('req_ids', []))
    await show_consultation_details(callback, req_id, current_index, total)

@admin_router.callback_query(F.data.startswith("consult_complete_"))
async def consult_complete(callback: types.CallbackQuery, state: FSMContext, bot: Bot):
    """Завершение консультации (с удалением)"""
    req_id = int(callback.data.split("_")[2])
    data = await state.get_data()
    req_ids = data.get('req_ids', [])
    current_index = data.get('current_index', 0)
    
    # Удаляем запрос из БД
    if db.delete_consultation_request(req_id):
        await callback.answer("Консультация завершена и удалена!", show_alert=True)
    else:
        await callback.answer("Запрос не найден!", show_alert=True)
        return
    
    # Обновляем список запросов
    if req_id in req_ids:
        req_ids.remove(req_id)
    
    if not req_ids:
        # Возвращаемся если запросов больше нет
        await admin_consultations(callback, state, bot)
        return
    
    # Переходим к следующему запросу
    new_index = current_index
    if current_index >= len(req_ids):
        new_index = len(req_ids) - 1
    
    await state.update_data(req_ids=req_ids, current_index=new_index)
    await show_consultation_details(callback, req_ids[new_index], new_index, len(req_ids), bot)

# ================== УПРАВЛЕНИЕ ПОРТФОЛИО ================== #

@admin_router.callback_query(F.data == "admin_portfolio")
async def admin_portfolio(callback: types.CallbackQuery, state: FSMContext, bot: Bot):
    """Меню управления портфолио"""
    await state.set_state(AdminMenu.portfolio_manage)
    await message_manager.edit_main_message(
        callback.from_user.id,
        "🎨 Управление портфолио",
        callback.message.message_id,
        kb.portfolio_management(),
        bot
    )
    await callback.answer()

@admin_router.callback_query(F.data == "portfolio_add")
async def portfolio_add_start(callback: types.CallbackQuery, state: FSMContext):
    """Начало добавления проекта в портфолио"""
    await state.set_state(PortfolioManage.add_title)
    await callback.message.answer(
        "Введите название проекта:",
        reply_markup=kb.back_to_admin_menu()
    )
    await callback.answer()

@admin_router.message(PortfolioManage.add_title)
async def portfolio_add_title(message: types.Message, state: FSMContext):
    """Обработка названия проекта"""
    await state.update_data(title=message.text)
    await state.set_state(PortfolioManage.add_description)
    await message.answer(
        "Введите краткое описание проекта:",
        reply_markup=kb.back_to_admin_menu()
    )

@admin_router.message(PortfolioManage.add_description)
async def portfolio_add_description(message: types.Message, state: FSMContext):
    """Обработка описания проекта"""
    await state.update_data(description=message.text)
    await state.set_state(PortfolioManage.add_details)
    await message.answer(
        "Введите детали проекта:",
        reply_markup=kb.back_to_admin_menu()
    )

@admin_router.message(PortfolioManage.add_details)
async def portfolio_add_details(message: types.Message, state: FSMContext):
    """Обработка деталей проекта"""
    await state.update_data(details=message.text)
    await state.set_state(PortfolioManage.add_cost)
    await message.answer(
        "Введите стоимость проекта (число или текст):",
        reply_markup=kb.back_to_admin_menu()
    )

@admin_router.message(PortfolioManage.add_cost)
async def portfolio_add_cost(message: types.Message, state: FSMContext):
    """Сохранение стоимости и переход к технологиям"""
    await state.update_data(cost=message.text)
    await state.set_state(PortfolioManage.add_technologies)
    await message.answer(
        "Перечислите технологии (через запятую), например: Python, Aiogram, PostgreSQL",
        reply_markup=kb.back_to_admin_menu()
    )

@admin_router.message(PortfolioManage.add_technologies)
async def portfolio_add_technologies(message: types.Message, state: FSMContext):
    """Обработка технологий проекта"""
    await state.update_data(technologies=message.text)
    await state.set_state(PortfolioManage.add_duration)
    await message.answer(
        "Укажите длительность (например: 2 недели, 10 дней, 1 месяц):",
        reply_markup=kb.back_to_admin_menu()
    )

@admin_router.message(PortfolioManage.add_duration)
async def portfolio_add_duration(message: types.Message, state: FSMContext):
    """Обработка длительности проекта"""
    await state.update_data(duration=message.text)
    await state.set_state(PortfolioManage.add_video)
    await message.answer(
        "Отправьте ссылку на видео проекта (Telegram/YouTube) или напишите 'пропустить':",
        reply_markup=kb.back_to_admin_menu()
    )

@admin_router.message(PortfolioManage.add_video)
async def portfolio_add_video(message: types.Message, state: FSMContext):
    """Обработка видео URL"""
    text = (message.text or "").strip()
    if text and text.lower() != "пропустить":
        await state.update_data(video_url=text)
    await state.set_state(PortfolioManage.add_bot_url)
    await message.answer(
        "Если есть, отправьте ссылку на бота для этого проекта или напишите 'пропустить':",
        reply_markup=kb.back_to_admin_menu()
    )

@admin_router.message(PortfolioManage.add_bot_url)
async def portfolio_add_bot_url(message: types.Message, state: FSMContext, bot: Bot):
    """Финальное сохранение проекта (video_url и bot_url опциональны)"""
    data = await state.get_data()
    bot_url = None
    text = (message.text or "").strip()
    if text and text.lower() != "пропустить":
        bot_url = text

    project_data = {
        "title": data["title"],
        "description": data["description"],
        "details": data["details"],
        "cost": data["cost"],
        "technologies": data.get("technologies"),
        "duration": data.get("duration"),
        "video_url": data.get("video_url"),
        "bot_url": bot_url,
    }

    project = db.create_portfolio_project(project_data)
    if project:
        await message.answer("✅ Проект успешно добавлен в портфолио!")
    else:
        await message.answer("❌ Ошибка при добавлении проекта!")

    await state.clear()
    await bot.delete_message(message.chat.id, message.message_id)

@admin_router.callback_query(F.data == "portfolio_edit_list")
async def portfolio_edit_list(callback: types.CallbackQuery, bot: Bot):
    """Список проектов для редактирования"""
    projects = db.get_portfolio_projects()
    if not projects:
        await callback.answer("Портфолио пусто!", show_alert=True)
        return
    
    text = "✏️ Выберите проект для редактирования:\n\n"
    await message_manager.edit_main_message(
        callback.from_user.id,
        text,
        callback.message.message_id,
        kb.project_list(projects, "pedit_select"),
        bot
    )
    await callback.answer()

@admin_router.callback_query(F.data.startswith("pedit_select_"))
async def portfolio_edit_select(callback: types.CallbackQuery, bot: Bot):
    """Выбор проекта для редактирования"""
    project_id = int(callback.data.split("_")[2])
    project = db.get_portfolio_project(project_id)
    if project:
        text = (
            f"✏️ Редактирование проекта:\n\n"
            f"<b>Название:</b> {project.title}\n"
            f"<b>Описание:</b> {project.description}\n"
            f"<b>Стоимость:</b> {project.cost}"
        )
        await message_manager.edit_main_message(
            callback.from_user.id,
            text,
            callback.message.message_id,
            kb.portfolio_edit(project.id),
            bot
        )
    else:
        await callback.answer("Проект не найден!", show_alert=True)
    await callback.answer()

@admin_router.callback_query(F.data.startswith("pedit_title_"))
async def portfolio_edit_title(callback: types.CallbackQuery, state: FSMContext):
    """Редактирование названия проекта"""
    project_id = int(callback.data.split("_")[2])
    await state.set_state(PortfolioManage.edit_field)
    await state.update_data(project_id=project_id, field="title")
    
    project = db.get_portfolio_project(project_id)
    await callback.message.answer(
        f"Текущее название: {project.title}\nВведите новое название:",
        reply_markup=kb.back_to_admin_menu()
    )
    await callback.answer()

@admin_router.callback_query(F.data.startswith("pedit_desc_"))
async def portfolio_edit_desc(callback: types.CallbackQuery, state: FSMContext):
    """Редактирование описания проекта"""
    project_id = int(callback.data.split("_")[2])
    await state.set_state(PortfolioManage.edit_field)
    await state.update_data(project_id=project_id, field="description")
    
    project = db.get_portfolio_project(project_id)
    await callback.message.answer(
        f"Текущее описание: {project.description}\nВведите новое описание:",
        reply_markup=kb.back_to_admin_menu()
    )
    await callback.answer()

@admin_router.callback_query(F.data.startswith("pedit_details_"))
async def portfolio_edit_details(callback: types.CallbackQuery, state: FSMContext):
    """Редактирование деталей проекта"""
    project_id = int(callback.data.split("_")[2])
    await state.set_state(PortfolioManage.edit_field)
    await state.update_data(project_id=project_id, field="details")
    
    project = db.get_portfolio_project(project_id)
    await callback.message.answer(
        f"Текущие детали: {project.details}\nВведите новые детали:",
        reply_markup=kb.back_to_admin_menu()
    )
    await callback.answer()

@admin_router.callback_query(F.data.startswith("pedit_cost_"))
async def portfolio_edit_cost(callback: types.CallbackQuery, state: FSMContext):
    """Редактирование стоимости проекта"""
    project_id = int(callback.data.split("_")[2])
    await state.set_state(PortfolioManage.edit_field)
    await state.update_data(project_id=project_id, field="cost")
    
    project = db.get_portfolio_project(project_id)
    await callback.message.answer(
        f"Текущая стоимость: {project.cost}\nВведите новую стоимость:",
        reply_markup=kb.back_to_admin_menu()
    )
    await callback.answer()

@admin_router.callback_query(F.data.startswith("pedit_tech_"))
async def portfolio_edit_tech(callback: types.CallbackQuery, state: FSMContext):
    """Редактирование технологий проекта"""
    project_id = int(callback.data.split("_")[2])
    await state.set_state(PortfolioManage.edit_field)
    await state.update_data(project_id=project_id, field="technologies")

    project = db.get_portfolio_project(project_id)
    current = project.technologies if project else "—"
    await callback.message.answer(
        f"Текущие технологии: {current}\nВведите новые (через запятую):",
        reply_markup=kb.back_to_admin_menu()
    )
    await callback.answer()

@admin_router.callback_query(F.data.startswith("pedit_duration_"))
async def portfolio_edit_duration(callback: types.CallbackQuery, state: FSMContext):
    """Редактирование длительности проекта"""
    project_id = int(callback.data.split("_")[2])
    await state.set_state(PortfolioManage.edit_field)
    await state.update_data(project_id=project_id, field="duration")

    project = db.get_portfolio_project(project_id)
    current = project.duration if project else "—"
    await callback.message.answer(
        f"Текущая длительность: {current}\nВведите новую длительность:",
        reply_markup=kb.back_to_admin_menu()
    )
    await callback.answer()

@admin_router.callback_query(F.data.startswith("pedit_video_"))
async def portfolio_edit_video(callback: types.CallbackQuery, state: FSMContext):
    """Редактирование видео проекта"""
    project_id = int(callback.data.split("_")[2])
    await state.set_state(PortfolioManage.edit_field)
    await state.update_data(project_id=project_id, field="video_url")

    project = db.get_portfolio_project(project_id)
    current = project.video_url if project else "—"
    await callback.message.answer(
        f"Текущее видео: {current}\nОтправьте новую ссылку или 'очистить' для удаления:",
        reply_markup=kb.back_to_admin_menu()
    )
    await callback.answer()

@admin_router.callback_query(F.data.startswith("pedit_bot_"))
async def portfolio_edit_bot(callback: types.CallbackQuery, state: FSMContext):
    """Редактирование ссылки на бота"""
    project_id = int(callback.data.split("_")[2])
    await state.set_state(PortfolioManage.edit_field)
    await state.update_data(project_id=project_id, field="bot_url")

    project = db.get_portfolio_project(project_id)
    current = project.bot_url if project else "—"
    await callback.message.answer(
        f"Текущая ссылка: {current}\nОтправьте новую ссылку или 'очистить' для удаления:",
        reply_markup=kb.back_to_admin_menu()
    )
    await callback.answer()

@admin_router.message(PortfolioManage.edit_field)
async def portfolio_edit_field(message: types.Message, state: FSMContext, bot: Bot):
    """Сохранение изменений проекта"""
    data = await state.get_data()
    project_id = data['project_id']
    field = data['field']
    text = (message.text or "").strip()
    new_value = None if text.lower() in ("очистить", "удалить") else text
    
    project = db.update_portfolio_project(project_id, {field: new_value})
    if project:
        await message.answer(f"✅ {field.capitalize()} успешно обновлено!")
    else:
        await message.answer("❌ Проект не найден!")
    
    await state.clear()
    await bot.delete_message(message.chat.id, message.message_id)

@admin_router.callback_query(F.data == "portfolio_delete_list")
async def portfolio_delete_list(callback: types.CallbackQuery, bot: Bot):
    """Список проектов для удаления"""
    projects = db.get_portfolio_projects()
    if not projects:
        await callback.answer("Портфолио пусто!", show_alert=True)
        return
    
    text = "🗑️ Выберите проект для удаления:\n\n"
    await message_manager.edit_main_message(
        callback.from_user.id,
        text,
        callback.message.message_id,
        kb.project_list(projects, "pdelete_select"),
        bot
    )
    await callback.answer()

@admin_router.callback_query(F.data.startswith("pdelete_select_"))
async def portfolio_delete_select(callback: types.CallbackQuery, bot: Bot):
    """Подтверждение удаления проекта"""
    project_id = int(callback.data.split("_")[2])
    project = db.get_portfolio_project(project_id)
    if project:
        text = (
            f"🗑️ Вы уверены, что хотите удалить проект?\n\n"
            f"<b>{project.title}</b>\n"
            f"{project.description}"
        )
        await message_manager.edit_main_message(
            callback.from_user.id,
            text,
            callback.message.message_id,
            kb.portfolio_delete_confirm(project.id),
            bot
        )
    else:
        await callback.answer("Проект не найден!", show_alert=True)
    await callback.answer()

@admin_router.callback_query(F.data.startswith("pdelete_confirm_"))
async def portfolio_delete_confirm(callback: types.CallbackQuery):
    """Удаление проекта"""
    project_id = int(callback.data.split("_")[2])
    if db.delete_portfolio_project(project_id):
        await callback.answer("✅ Проект удален!", show_alert=True)
        await admin_portfolio(callback)
    else:
        await callback.answer("❌ Проект не найден!", show_alert=True)
    await callback.answer()

@admin_router.callback_query(F.data.startswith("order_set_price_"))
async def order_set_price(callback: types.CallbackQuery, state: FSMContext):
    """Установка окончательной цены заказа"""
    order_id = int(callback.data.split("_")[3])
    await state.set_state(OrderManagement.set_price)
    await state.update_data(order_id=order_id)
    
    order = db.get_client_order(order_id)
    if order:
        await callback.message.answer(
            f"💰 Установка цены для заказа #{order.id}\n\n"
            f"📋 <b>Проект:</b> {order.project_name}\n"
            f"💼 <b>Бюджет клиента:</b> {order.budget}\n\n"
            f"Введите окончательную цену в рублях (только число):",
            reply_markup=kb.back_to_admin_menu(),
            parse_mode="HTML"
        )
    else:
        await callback.answer("Заказ не найден!", show_alert=True)
    await callback.answer()

@admin_router.message(OrderManagement.set_price)
async def process_set_price(message: types.Message, state: FSMContext, bot: Bot):
    """Обработка установки цены"""
    try:
        price = float(message.text.replace(",", ".").replace(" ", ""))
        if price <= 0:
            await message.answer("❌ Цена должна быть больше нуля!")
            return
        
        data = await state.get_data()
        order_id = data['order_id']
        
        await state.update_data(final_price=price)
        await state.set_state(OrderManagement.add_notes)
        
        await message.answer(
            f"💰 Цена установлена: {price:,.2f}₽\n\n"
            f"📝 Добавьте заметки для клиента (или напишите 'пропустить'):",
            reply_markup=kb.back_to_admin_menu()
        )
        
    except ValueError:
        await message.answer("❌ Введите корректную цену (только цифры)!")

@admin_router.message(OrderManagement.add_notes)
async def process_add_notes(message: types.Message, state: FSMContext, bot: Bot):
    """Обработка заметок и сохранение заказа"""
    data = await state.get_data()
    order_id = data['order_id']
    final_price = data['final_price']
    
    notes = message.text.strip() if message.text.strip().lower() != 'пропустить' else None
    
    # Сохраняем окончательную цену
    if db.set_order_final_price(order_id, final_price, notes):
        order = db.get_client_order(order_id)
        
        # Уведомляем клиента
        try:
            client_message = (
                f"✅ <b>Ваш заказ принят!</b>\n\n"
                f"📋 <b>Проект:</b> {order.project_name}\n"
                f"💰 <b>Стоимость:</b> {final_price:,.2f}₽\n"
            )
            if notes:
                client_message += f"📝 <b>Комментарий:</b> {notes}\n"
            
            client_message += (
                f"\n💳 Для оплаты свяжитесь с администратором.\n"
                f"После подтверждения оплаты мы приступим к работе!"
            )
            
            await bot.send_message(
                order.user_id,
                client_message,
                parse_mode="HTML"
            )
        except Exception as e:
            print(f"Error notifying client: {e}")
        
        await message.answer(
            f"✅ Заказ #{order_id} принят!\n"
            f"💰 Цена: {final_price:,.2f}₽\n"
            f"📨 Клиент уведомлен",
            reply_markup=kb.back_to_admin_menu()
        )
    else:
        await message.answer("❌ Ошибка сохранения заказа!")
    
    await state.clear()
    await bot.delete_message(message.chat.id, message.message_id)

@admin_router.callback_query(F.data == "admin_payment_confirmations")
async def admin_payment_confirmations(callback: types.CallbackQuery, state: FSMContext, bot: Bot):
    """Меню подтверждения оплат"""
    await state.set_state(AdminMenu.payment_confirmations)
    await message_manager.edit_main_message(
        callback.from_user.id,
        "💳 Подтверждение оплат заказов",
        callback.message.message_id,
        admin_payment_confirmations_keyboard(),
        bot
    )
    await callback.answer()

@admin_router.callback_query(F.data == "admin_accepted_orders_list")
async def admin_accepted_orders_list(callback: types.CallbackQuery, state: FSMContext, bot: Bot):
    """Список принятых заказов для подтверждения оплаты"""
    orders = db.get_accepted_orders_for_payment()
    if not orders:
        await callback.answer("Нет заказов ожидающих оплату!", show_alert=True)
        return
    
    # Сохраняем список ID и текущий индекс
    order_ids = [order.id for order in orders]
    await state.update_data(accepted_order_ids=order_ids, current_index=0)
    
    # Показываем первый заказ
    await show_accepted_order_details(callback, order_ids[0], 0, len(order_ids), bot)
    await callback.answer()

async def show_accepted_order_details(callback: types.CallbackQuery, order_id: int, current_index: int, total: int, bot: Bot):
    """Детализация принятого заказа"""
    order = db.get_client_order(order_id)
    if not order:
        await callback.answer("Заказ не найден!", show_alert=True)
        return
    
    text = (
        f"💳 Заказ #{order.id} - Подтверждение оплаты\n"
        f"👤 Клиент: @{order.username}\n"
        f"💰 Цена: {order.final_price:,.2f}₽\n\n"
        f"<b>Проект:</b> {order.project_name}\n"
        f"<b>Функционал:</b> {order.functionality}\n"
        f"<b>Сроки:</b> {order.deadlines}\n"
    )
    
    if order.admin_notes:
        text += f"<b>Заметки:</b> {order.admin_notes}\n"
    
    await message_manager.edit_main_message(
        callback.from_user.id,
        text,
        callback.message.message_id,
        accepted_order_actions_keyboard(order.id, current_index, total),
        bot
    )

@admin_router.callback_query(F.data.startswith("accepted_order_prev_"))
async def accepted_order_prev(callback: types.CallbackQuery, state: FSMContext, bot: Bot):
    """Переход к предыдущему принятому заказу"""
    data = await state.get_data()
    order_ids = data.get('accepted_order_ids', [])
    current_index = data.get('current_index', 0)
    
    if not order_ids:
        await callback.answer("Нет доступных заказов!", show_alert=True)
        return
    
    new_index = (current_index - 1) % len(order_ids)
    await state.update_data(current_index=new_index)
    await show_accepted_order_details(callback, order_ids[new_index], new_index, len(order_ids), bot)
    await callback.answer()

@admin_router.callback_query(F.data.startswith("accepted_order_next_"))
async def accepted_order_next(callback: types.CallbackQuery, state: FSMContext, bot: Bot):
    """Переход к следующему принятому заказу"""
    data = await state.get_data()
    order_ids = data.get('accepted_order_ids', [])
    current_index = data.get('current_index', 0)
    
    if not order_ids:
        await callback.answer("Нет доступных заказов!", show_alert=True)
        return
    
    new_index = (current_index + 1) % len(order_ids)
    await state.update_data(current_index=new_index)
    await show_accepted_order_details(callback, order_ids[new_index], new_index, len(order_ids), bot)
    await callback.answer()

@admin_router.callback_query(F.data.startswith("confirm_payment_"))
async def confirm_payment(callback: types.CallbackQuery, state: FSMContext, bot: Bot):
    """Подтверждение оплаты заказа"""
    order_id = int(callback.data.split("_")[2])
    
    if db.confirm_order_payment(order_id):
        order = db.get_client_order(order_id)
        
        # Уведомляем клиента
        try:
            await bot.send_message(
                order.user_id,
                f"✅ <b>Оплата подтверждена!</b>\n\n"
                f"📋 Заказ #{order.id}: {order.project_name}\n"
                f"💰 Сумма: {order.final_price:,.2f}₽\n\n"
                f"🚀 Мы приступаем к работе над вашим проектом!",
                parse_mode="HTML"
            )
        except Exception as e:
            print(f"Error notifying client: {e}")
        
        # Проверяем реферальные начисления
        referral_user = db.get_referral_user(order.user_id)
        if referral_user and referral_user.referred_by:
            try:
                referrer_stats = db.get_referral_stats(referral_user.referred_by)
                if referrer_stats:
                    commission = order.final_price * 0.25
                    await bot.send_message(
                        referral_user.referred_by,
                        f"💰 <b>Новое начисление!</b>\n\n"
                        f"👤 Ваш реферал оплатил заказ\n"
                        f"💵 Начислено: {commission:,.2f}₽\n"
                        f"💳 Доступно к выводу: {referrer_stats['balance']:,.2f}₽",
                        parse_mode="HTML"
                    )
            except Exception as e:
                print(f"Error notifying referrer: {e}")
        
        await callback.answer("✅ Оплата подтверждена! Клиент уведомлен.", show_alert=True)
        
        # Обновляем список
        data = await state.get_data()
        order_ids = data.get('accepted_order_ids', [])
        if order_id in order_ids:
            order_ids.remove(order_id)
        
        if not order_ids:
            await admin_payment_confirmations(callback, state, bot)
            return
        
        current_index = data.get('current_index', 0)
        if current_index >= len(order_ids):
            current_index = len(order_ids) - 1
        
        await state.update_data(accepted_order_ids=order_ids, current_index=current_index)
        await show_accepted_order_details(callback, order_ids[current_index], current_index, len(order_ids), bot)
    else:
        await callback.answer("❌ Ошибка подтверждения оплаты!", show_alert=True)

@admin_router.callback_query(F.data.startswith("order_edit_price_"))
async def order_edit_price(callback: types.CallbackQuery, state: FSMContext):
    """Изменение цены принятого заказа"""
    order_id = int(callback.data.split("_")[3])
    await state.set_state(OrderManagement.set_price)
    await state.update_data(order_id=order_id, editing_price=True)
    
    order = db.get_client_order(order_id)
    if order:
        await callback.message.answer(
            f"💰 Изменение цены заказа #{order.id}\n\n"
            f"📋 <b>Проект:</b> {order.project_name}\n"
            f"💰 <b>Текущая цена:</b> {order.final_price:,.2f}₽\n\n"
            f"Введите новую цену в рублях:",
            reply_markup=kb.back_to_admin_menu(),
            parse_mode="HTML"
        )
    else:
        await callback.answer("Заказ не найден!", show_alert=True)
    await callback.answer()

# ================== УПРАВЛЕНИЕ РЕФЕРАЛЬНЫМИ ВЫПЛАТАМИ ================== #

@admin_router.callback_query(F.data == "admin_referral_payouts")
async def admin_referral_payouts(callback: types.CallbackQuery, state: FSMContext, bot: Bot):
    """Меню управления реферальными выплатами"""
    await state.set_state(AdminMenu.referral_payouts)
    await message_manager.edit_main_message(
        callback.from_user.id,
        "💸 Управление реферальными выплатами",
        callback.message.message_id,
        admin_referral_payouts_keyboard(),
        bot
    )
    await callback.answer()

@admin_router.callback_query(F.data == "admin_payouts_list")
async def admin_payouts_list(callback: types.CallbackQuery, state: FSMContext, bot: Bot):
    """Список запросов на выплату"""
    payouts = db.get_pending_payouts()
    if not payouts:
        await callback.answer("Нет запросов на выплату!", show_alert=True)
        return
    
    # Сохраняем список ID и текущий индекс
    payout_ids = [payout.id for payout in payouts]
    await state.update_data(payout_ids=payout_ids, current_index=0)
    
    # Показываем первую выплату
    await show_payout_details(callback, payout_ids[0], 0, len(payout_ids), bot)
    await callback.answer()

async def show_payout_details(callback: types.CallbackQuery, payout_id: int, current_index: int, total: int, bot: Bot):
    """Детализация запроса на выплату"""
    payout = db.get_referral_payout(payout_id)
    if not payout:
        await callback.answer("Выплата не найдена!", show_alert=True)
        return
    
    # Получаем информацию о реферере
    referrer_stats = db.get_referral_stats(payout.referrer_id)
    
    text = (
        f"💸 Запрос на выплату #{payout.id}\n"
        f"👤 Реферер: ID {payout.referrer_id}\n"
        f"💰 Сумма: {payout.amount:,.2f}₽\n"
        f"💳 Метод: {payout.method}\n"
        f"📝 Реквизиты: {payout.recipient_info}\n"
        f"📅 Дата запроса: {payout.created_at.strftime('%d.%m.%Y %H:%M')}\n\n"
    )
    
    if referrer_stats:
        text += (
            f"📊 <b>Статистика реферера:</b>\n"
            f"👥 Всего рефералов: {referrer_stats['total_referrals']}\n"
            f"💵 Всего заработано: {referrer_stats['total_earned']:,.2f}₽\n"
            f"💳 Баланс: {referrer_stats['balance']:,.2f}₽\n"
        )
    
    if payout.admin_notes:
        text += f"\n📋 Заметки: {payout.admin_notes}"
    
    await message_manager.edit_main_message(
        callback.from_user.id,
        text,
        callback.message.message_id,
        payout_actions_keyboard(payout.id, current_index, total),
        bot
    )

@admin_router.callback_query(F.data.startswith("payout_prev_"))
async def payout_prev(callback: types.CallbackQuery, state: FSMContext, bot: Bot):
    """Переход к предыдущей выплате"""
    data = await state.get_data()
    payout_ids = data.get('payout_ids', [])
    current_index = data.get('current_index', 0)
    
    if not payout_ids:
        await callback.answer("Нет доступных выплат!", show_alert=True)
        return
    
    new_index = (current_index - 1) % len(payout_ids)
    await state.update_data(current_index=new_index)
    await show_payout_details(callback, payout_ids[new_index], new_index, len(payout_ids), bot)
    await callback.answer()

@admin_router.callback_query(F.data.startswith("payout_next_"))
async def payout_next(callback: types.CallbackQuery, state: FSMContext, bot: Bot):
    """Переход к следующей выплате"""
    data = await state.get_data()
    payout_ids = data.get('payout_ids', [])
    current_index = data.get('current_index', 0)
    
    if not payout_ids:
        await callback.answer("Нет доступных выплат!", show_alert=True)
        return
    
    new_index = (current_index + 1) % len(payout_ids)
    await state.update_data(current_index=new_index)
    await show_payout_details(callback, payout_ids[new_index], new_index, len(payout_ids), bot)
    await callback.answer()

@admin_router.callback_query(F.data.startswith("payout_approve_"))
async def payout_approve(callback: types.CallbackQuery, state: FSMContext, bot: Bot):
    """Одобрение выплаты"""
    payout_id = int(callback.data.split("_")[2])
    
    if db.update_referral_payout_status(payout_id, 'processing'):
        payout = db.get_referral_payout(payout_id)
        
        # Уведомляем реферера
        try:
            await bot.send_message(
                payout.referrer_id,
                f"✅ <b>Выплата одобрена!</b>\n\n"
                f"💰 Сумма: {payout.amount:,.2f}₽\n"
                f"💳 Метод: {payout.method}\n\n"
                f"⏳ Выплата будет произведена в течение 1-3 рабочих дней.",
                parse_mode="HTML"
            )
        except Exception as e:
            print(f"Error notifying referrer: {e}")
        
        await callback.answer("✅ Выплата одобрена! Реферер уведомлен.", show_alert=True)
        
        # Обновляем отображение
        data = await state.get_data()
        current_index = data.get('current_index', 0)
        total = len(data.get('payout_ids', []))
        await show_payout_details(callback, payout_id, current_index, total, bot)
    else:
        await callback.answer("❌ Ошибка одобрения выплаты!", show_alert=True)

@admin_router.callback_query(F.data.startswith("payout_reject_"))
async def payout_reject(callback: types.CallbackQuery, state: FSMContext, bot: Bot):
    """Отклонение выплаты"""
    payout_id = int(callback.data.split("_")[2])
    await state.set_state(AdminResponse.payout_notes)
    await state.update_data(payout_id=payout_id, payout_action='reject')
    
    await callback.message.answer(
        "❌ Укажите причину отклонения выплаты:",
        reply_markup=kb.back_to_admin_menu()
    )
    await callback.answer()

@admin_router.callback_query(F.data.startswith("payout_complete_"))
async def payout_complete(callback: types.CallbackQuery, state: FSMContext, bot: Bot):
    """Завершение выплаты"""
    payout_id = int(callback.data.split("_")[2])
    
    if db.complete_referral_payout(payout_id):
        payout = db.get_referral_payout(payout_id)
        
        # Уведомляем реферера
        try:
            await bot.send_message(
                payout.referrer_id,
                f"✅ <b>Выплата завершена!</b>\n\n"
                f"💰 Сумма: {payout.amount:,.2f}₽\n"
                f"💳 Метод: {payout.method}\n\n"
                f"💸 Средства переведены на ваши реквизиты.",
                parse_mode="HTML"
            )
        except Exception as e:
            print(f"Error notifying referrer: {e}")
        
        await callback.answer("✅ Выплата завершена! Реферер уведомлен.", show_alert=True)
        
        # Удаляем из списка и переходим к следующей
        data = await state.get_data()
        payout_ids = data.get('payout_ids', [])
        if payout_id in payout_ids:
            payout_ids.remove(payout_id)
        
        if not payout_ids:
            await admin_referral_payouts(callback, state, bot)
            return
        
        current_index = data.get('current_index', 0)
        if current_index >= len(payout_ids):
            current_index = len(payout_ids) - 1
        
        await state.update_data(payout_ids=payout_ids, current_index=current_index)
        await show_payout_details(callback, payout_ids[current_index], current_index, len(payout_ids), bot)
    else:
        await callback.answer("❌ Ошибка завершения выплаты!", show_alert=True)

@admin_router.message(AdminResponse.payout_notes)
async def process_payout_notes(message: types.Message, state: FSMContext, bot: Bot):
    """Обработка заметок для выплаты"""
    data = await state.get_data()
    payout_id = data['payout_id']
    action = data['payout_action']
    notes = message.text.strip()
    
    if action == 'reject':
        if db.update_referral_payout_status(payout_id, 'failed', notes):
            payout = db.get_referral_payout(payout_id)
            
            # Уведомляем реферера
            try:
                await bot.send_message(
                    payout.referrer_id,
                    f"❌ <b>Выплата отклонена</b>\n\n"
                    f"💰 Сумма: {payout.amount:,.2f}₽\n"
                    f"📝 Причина: {notes}\n\n"
                    f"Обратитесь к администратору для уточнения деталей.",
                    parse_mode="HTML"
                )
            except Exception as e:
                print(f"Error notifying referrer: {e}")
            
            await message.answer("✅ Выплата отклонена! Реферер уведомлен.")
        else:
            await message.answer("❌ Ошибка отклонения выплаты!")
    
    await state.clear()
    await bot.delete_message(message.chat.id, message.message_id)
    await callback.answer()