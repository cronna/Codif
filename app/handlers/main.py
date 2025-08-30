import logging
from typing import Optional, Dict, Any
from aiogram import types, F, Router, Bot
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from config import config
# from app.handlers.admin import AdminHandler  # Временно отключено
# from app.handlers.consultation import ConsultationHandler  # Временно отключено
# from app.handlers.portfolio import PortfolioHandler  # Временно отключено
from app.handlers.referral import ReferralHandler
from app.db.database import db
from app.keyboards import kb
from app.fsm import ClientOrder, JoinTeam, Portfolio, Consultation, ReferralSystem
from app.utils.message_manager import MessageManager
from app.utils.notification_manager import NotificationManager
from app.utils.error_handler import error_handler, ErrorHandler
from app.utils.ui_components import UIComponents
from app.utils.cache_manager import DataValidator, cache
from app.utils.performance_monitor import monitor_performance, performance_monitor

main_router = Router()

# Настройка логирования
logger = logging.getLogger(__name__)

# Менеджеры
message_manager = MessageManager()
notification_manager = NotificationManager()

class MainHandler:
    """Основной обработчик для главных функций бота"""
    
    @staticmethod
    async def start_command(message: types.Message, state: FSMContext) -> None:
        """Обработчик команды /start"""
        try:
            user_id = message.from_user.id
            
            # Очищаем состояние
            await state.clear()
            
            # Удаляем сессию из БД если она есть
            db.delete_user_session(user_id)
            
            # Проверяем реферальную ссылку
            if message.text and len(message.text.split()) > 1:
                start_param = message.text.split()[1]
                if start_param.startswith('ref_'):
                    referral_code = start_param[4:]  # Убираем 'ref_'
                    success = await ReferralHandler.process_referral_start(
                        user_id, referral_code, message.from_user.username
                    )
                    if success:
                        await message.answer(
                            f"{config.EMOJI['gift']} <b>Добро пожаловать!</b>\n\n"
                            f"Вы перешли по реферальной ссылке. Теперь при оформлении заказа "
                            f"ваш реферер получит бонус!\n\n"
                            f"{config.EMOJI['info']} <i>Это никак не влияет на стоимость ваших заказов</i>",
                            parse_mode="HTML"
                        )
            
            # Отправляем приветственное сообщение
            sent = await message.answer(
                config.MESSAGES["welcome"],
                reply_markup=kb.main_menu(user_id, user_id in config.ADMIN_IDS),
                parse_mode="HTML"
            )
            
            # Сохраняем ID главного сообщения
            message_manager.set_main_message(user_id, sent.message_id)
            
            logger.info(f"User {user_id} started the bot")
            
        except Exception as e:
            logger.error(f"Error in start command: {e}")
            await message.answer(config.MESSAGES["error_occurred"])

    @staticmethod
    async def back_to_main(callback: types.CallbackQuery, state: FSMContext, bot: Bot) -> None:
        """Возврат в главное меню"""
        try:
            user_id = callback.from_user.id
            await state.clear()
            
            # Очищаем сессию
            db.delete_user_session(user_id)
            
            # Если текущее сообщение медиа (например, из портфолио) — отправляем НОВОЕ текстовое сообщение
            content_type = getattr(callback.message, "content_type", "")
            is_media = content_type and content_type != "text"

            if is_media:
                sent = await bot.send_message(
                    user_id,
                    config.MESSAGES["welcome"],
                    reply_markup=kb.main_menu(user_id, user_id in config.ADMIN_IDS),
                    parse_mode="HTML"
                )
                message_manager.set_main_message(user_id, sent.message_id)
                # Пытаемся удалить предыдущее медиа, чтобы не засорять чат
                try:
                    await bot.delete_message(user_id, callback.message.message_id)
                except Exception:
                    pass
                
                # Чистим сохраненный id сообщения об успехе
                success_msg_id = message_manager.get_success_message(user_id)
                if success_msg_id and success_msg_id != sent.message_id:
                    try:
                        await bot.delete_message(user_id, success_msg_id)
                    except Exception:
                        pass
                message_manager.clear_success_message(user_id)
                await callback.answer()
                return

            # Иначе пробуем отредактировать текущее сообщение
            edited = await message_manager.edit_main_message(
                user_id,
                config.MESSAGES["welcome"],
                callback.message.message_id,
                kb.main_menu(user_id, user_id in config.ADMIN_IDS),
                bot
            )
            
            # Если не удалось — пробуем отредактировать ранее сохраненное "главное" сообщение
            if not edited:
                main_msg_id = message_manager.get_main_message(user_id)
                if main_msg_id:
                    edited = await message_manager.edit_main_message(
                        user_id,
                        config.MESSAGES["welcome"],
                        main_msg_id,
                        kb.main_menu(user_id, user_id in config.ADMIN_IDS),
                        bot
                    )
            
            # Если всё ещё не удалось — отправляем новое сообщение и сохраняем как главное
            if not edited:
                sent = await bot.send_message(
                    user_id,
                    config.MESSAGES["welcome"],
                    reply_markup=kb.main_menu(user_id, user_id in config.ADMIN_IDS),
                    parse_mode="HTML"
                )
                message_manager.set_main_message(user_id, sent.message_id)
            else:
                # Сохраняем текущее сообщение как главное
                message_manager.set_main_message(user_id, callback.message.message_id)
            
            # Чистим сохраненный id сообщения об успехе. Если оно и было — оно уже преобразовано/закрыто.
            success_msg_id = message_manager.get_success_message(user_id)
            if success_msg_id:
                # Если это не то же самое сообщение, попробуем его удалить
                if success_msg_id != callback.message.message_id:
                    try:
                        await bot.delete_message(user_id, success_msg_id)
                    except Exception as e:
                        logger.warning(f"Could not delete old success message: {e}")
                message_manager.clear_success_message(user_id)
            
            await callback.answer()
            
        except Exception as e:
            logger.error(f"Error in back_to_main: {e}")
            await callback.answer(config.MESSAGES["error_occurred"], show_alert=True)

    @staticmethod
    async def cancel_questionnaire(callback: types.CallbackQuery, state: FSMContext, bot: Bot) -> None:
        """Отмена текущей анкеты"""
        try:
            user_id = callback.from_user.id
            await state.clear()
            
            # Очищаем сессию
            db.delete_user_session(user_id)
            
            # Редактируем главное сообщение
            await message_manager.edit_main_message(
                user_id,
                f"{config.MESSAGES['cancelled']}\n\n{config.MESSAGES['welcome']}",
                callback.message.message_id,
                kb.main_menu(user_id, user_id in config.ADMIN_IDS),
                bot
            )
            
            await callback.answer()
            
        except Exception as e:
            logger.error(f"Error in cancel_questionnaire: {e}")
            await callback.answer(config.MESSAGES["error_occurred"], show_alert=True)

class OrderHandler:
    """Обработчик заказов ботов"""
    
    @staticmethod
    async def start_order(callback: types.CallbackQuery, state: FSMContext) -> None:
        """Начало выбора типа заказа"""
        try:
            user_id = callback.from_user.id
            await state.set_state(ClientOrder.order_type)
            
            # Сохраняем сессию
            db.save_user_session(user_id, "order_selection", {"step": "order_type"})
            
            # Надежное редактирование главного сообщения (учет медиа)
            await message_manager.edit_main_message(
                user_id,
                text=f"{config.EMOJI['rocket']} <b>Выбор типа проекта</b>\n\n{config.EMOJI['gem']} <b>Что вы хотите заказать?</b>\n\n{config.EMOJI['robot']} <b>Телеграм бот</b> - классический бот с командами и функциями\n\n{config.EMOJI['phone']} <b>Мини-приложение</b> - современное веб-приложение внутри Telegram\n\n{config.EMOJI['info']} <i>Выберите подходящий вариант для вашего проекта</i>",
                message_id=callback.message.message_id,
                reply_markup=kb.order_type_selection(),
                bot=callback.bot,
            )
            
            message_manager.set_last_question(user_id, callback.message.message_id)
            await callback.answer()
            
        except Exception as e:
            logger.error(f"Error starting order: {e}")
            await callback.answer(config.MESSAGES["error_occurred"], show_alert=True)

    @staticmethod
    async def select_order_type(callback: types.CallbackQuery, state: FSMContext) -> None:
        """Обработка выбора типа заказа"""
        try:
            user_id = callback.from_user.id
            order_type = "bot" if callback.data == "order_type_bot" else "miniapp"
            
            await state.update_data(order_type=order_type)
            await state.set_state(ClientOrder.project_name)
            
            # Обновляем сессию
            db.save_user_session(user_id, "order_bot", {"step": "project_name", "order_type": order_type})
            
            # Определяем тип проекта для отображения
            project_type = "бота" if order_type == "bot" else "мини-приложения"
            project_emoji = config.EMOJI['robot'] if order_type == "bot" else config.EMOJI['phone']
            
            # Надежное редактирование главного сообщения
            await message_manager.edit_main_message(
                user_id,
                text=f"{project_emoji} <b>Заказ разработки {project_type}</b>\n\n{config.EMOJI['pencil']} <i>Шаг 1 из 4</i>\n\n{config.EMOJI['bulb']} <b>Введите название вашего проекта:</b>\n\n{config.EMOJI['info']} <i>Например: \"Интернет-магазин одежды\" или \"Система бронирования\"</i>",
                message_id=callback.message.message_id,
                reply_markup=kb.back_button(),
                bot=callback.bot,
            )
            
            message_manager.set_last_question(user_id, callback.message.message_id)
            await callback.answer()
            
        except Exception as e:
            logger.error(f"Error selecting order type: {e}")
            await callback.answer(config.MESSAGES["error_occurred"], show_alert=True)

    @staticmethod
    @error_handler("handle_project_name")
    @monitor_performance("handle_project_name")
    async def handle_project_name(message: types.Message, state: FSMContext) -> None:
        """Обработка названия проекта с валидацией"""
        try:
            user_id = message.from_user.id
            project_name = message.text.strip()
            
            # Валидация с помощью нового валидатора
            is_valid, validated_name = DataValidator.validate_user_input(
                project_name, max_length=200, min_length=3
            )
            
            if not is_valid:
                await message.answer(
                    f"{config.EMOJI['warning']} {validated_name}\n\nПопробуйте еще раз:",
                    reply_markup=kb.back_button()
                )
                return
            
            # Получаем тип заказа из состояния
            data = await state.get_data()
            order_type = data.get('order_type', 'bot')
            
            # Определяем текст в зависимости от типа
            if order_type == 'bot':
                project_type = "бота"
                project_emoji = config.EMOJI['robot']
                functionality_text = (
                    f"{config.EMOJI['check']} Какие функции должен выполнять бот?\n"
                    f"{config.EMOJI['check']} Какие команды нужны пользователям?\n"
                    f"{config.EMOJI['check']} Нужны ли интеграции с внешними сервисами?\n"
                    f"{config.EMOJI['check']} Особые требования к функционалу?"
                )
            else:
                project_type = "мини-приложения"
                project_emoji = config.EMOJI['phone']
                functionality_text = (
                    f"{config.EMOJI['check']} Какие страницы и разделы нужны?\n"
                    f"{config.EMOJI['check']} Какой функционал должен быть в приложении?\n"
                    f"{config.EMOJI['check']} Нужна ли авторизация и личные данные?\n"
                    f"{config.EMOJI['check']} Интеграции с API и внешними сервисами?"
                )
            
            sent = await message.answer(
                f"{project_emoji} <b>Функционал {project_type}</b>\n\n{config.EMOJI['pencil']} <i>Шаг 2 из 4</i>\n\n{config.EMOJI['tools']} <b>Опишите желаемый функционал:</b>\n\n"
                f"{functionality_text}\n\n"
                f"{config.EMOJI['bulb']} <i>Чем подробнее описание, тем точнее будет оценка!</i>",
                reply_markup=kb.back_button(),
                parse_mode="HTML"
            )
            
            message_manager.set_last_question(user_id, sent.message_id)
            
        except Exception as e:
            logger.error(f"Error processing project name: {e}")
            await message.answer(config.MESSAGES["error_occurred"])

    @staticmethod
    async def process_functionality(message: types.Message, state: FSMContext) -> None:
        """Обработка функционала"""
        try:
            user_id = message.from_user.id
            await state.update_data(functionality=message.text)
            await state.set_state(ClientOrder.deadlines)
            
            # Обновляем сессию
            db.save_user_session(user_id, "order_bot", {"step": "deadlines"})
            
            sent = await message.answer(
                f"{config.EMOJI['calendar']} <b>Сроки разработки</b>\n\n{config.EMOJI['pencil']} <i>Шаг 3 из 4</i>\n\n{config.EMOJI['time']} <b>Укажите желаемые сроки:</b>\n\n"
                f"{config.EMOJI['target']} Когда нужен готовый проект?\n"
                f"{config.EMOJI['chart']} Есть ли промежуточные этапы?\n"
                f"{config.EMOJI['lightning']} Насколько срочен проект?\n\n"
                f"{config.EMOJI['info']} <i>Обычно разработка занимает от 1 до 4 недель</i>",
                reply_markup=kb.back_button(),
                parse_mode="HTML"
            )
            
            message_manager.set_last_question(user_id, sent.message_id)
            
        except Exception as e:
            logger.error(f"Error processing functionality: {e}")
            await message.answer(config.MESSAGES["error_occurred"])

    @staticmethod
    async def process_deadlines(message: types.Message, state: FSMContext) -> None:
        """Обработка сроков"""
        try:
            user_id = message.from_user.id
            await state.update_data(deadlines=message.text)
            await state.set_state(ClientOrder.budget)
            
            # Обновляем сессию
            db.save_user_session(user_id, "order_bot", {"step": "budget"})
            
            sent = await message.answer(
                f"{config.EMOJI['money']} <b>Бюджет проекта</b>\n\n{config.EMOJI['pencil']} <i>Шаг 4 из 4</i>\n\n{config.EMOJI['gem']} <b>Укажите ваш бюджет:</b>\n\n"
                f"{config.EMOJI['chart']} Общая стоимость проекта\n"
                f"{config.EMOJI['handshake']} Возможность поэтапной оплаты\n"
                f"{config.EMOJI['tools']} Дополнительные расходы (хостинг, домены)\n\n"
                f"{config.EMOJI['bulb']} <i>Стоимость ботов обычно от 15,000₽ до 100,000₽</i>",
                reply_markup=kb.back_button(),
                parse_mode="HTML"
            )
            
            message_manager.set_last_question(user_id, sent.message_id)
            
        except Exception as e:
            logger.error(f"Error processing deadlines: {e}")
            await message.answer(config.MESSAGES["error_occurred"])

    @staticmethod
    async def process_budget(message: types.Message, state: FSMContext, bot: Bot) -> None:
        """Обработка бюджета и сохранение заявки"""
        try:
            user_id = message.from_user.id
            await state.update_data(budget=message.text)
            data = await state.get_data()
            
            # Сохраняем анкету в БД
            app_data = {
                "user_id": user_id,
                "username": message.from_user.username,
                "order_type": data.get("order_type", "bot"),
                "project_name": data["project_name"],
                "functionality": data["functionality"],
                "deadlines": data["deadlines"],
                "budget": data["budget"]
            }
            
            order = db.create_client_order(app_data)
            
            if order:
                # Определяем тип проекта для уведомления
                order_type_text = "бота" if data.get("order_type", "bot") == "bot" else "мини-приложения"
                
                # Уведомляем админов
                await notification_manager.notify_admins(
                    f"📋 <b>Новая заявка на разработку {order_type_text}!</b>\n\n"
                    f"👤 Пользователь: @{message.from_user.username}\n"
                    f"🆔 ID: {user_id}\n"
                    f"📝 Проект: {data['project_name']}\n"
                    f"💰 Бюджет: {data['budget']}",
                    bot
                )
                
                # Отправляем сообщение об успехе
                success_msg = await bot.send_message(
                    user_id,
                    f"{config.MESSAGES['order_success']}\n\n"
                    f"{config.EMOJI['document']} <b>Детали заявки:</b>\n\n"
                    f"{config.EMOJI['rocket']} <b>Проект:</b> {data['project_name']}\n"
                    f"{config.EMOJI['money']} <b>Бюджет:</b> {data['budget']}\n"
                    f"{config.EMOJI['calendar']} <b>Сроки:</b> {data['deadlines']}\n\n"
                    f"{config.EMOJI['phone']} <i>Мы свяжемся с вами в ближайшее время!</i>",
                    reply_markup=kb.success_action(),
                    parse_mode="HTML"
                )
                
                message_manager.set_success_message(user_id, success_msg.message_id)
                
                # Проверяем, является ли пользователь рефералом и создаем начисление
                referral_user = db.get_referral_user(user_id)
                if referral_user and referral_user.referred_by:
                    # Извлекаем сумму из строки бюджета (упрощенно)
                    try:
                        budget_str = data['budget'].replace('₽', '').replace(' ', '').replace(',', '')
                        # Ищем числа в строке
                        import re
                        numbers = re.findall(r'\d+', budget_str)
                        if numbers:
                            order_amount = float(numbers[-1])  # Берем последнее число
                            
                            # Создаем начисление рефералу
                            earning = db.create_referral_earning(
                                referrer_id=referral_user.referred_by,
                                referred_user_id=user_id,
                                order_id=order.id,
                                order_amount=order_amount
                            )
                            
                            if earning:
                                # Уведомляем реферера о начислении
                                try:
                                    await bot.send_message(
                                        referral_user.referred_by,
                                        f"{config.EMOJI['money']} <b>Новое начисление!</b>\n\n"
                                        f"Ваш реферал @{message.from_user.username} оформил заказ.\n"
                                        f"Начислено: {earning.earned_amount:.2f}₽\n\n"
                                        f"{config.EMOJI['pending']} Статус: Ожидает оплаты\n"
                                        f"{config.EMOJI['info']} После подтверждения оплаты средства будут доступны к выводу",
                                        parse_mode="HTML"
                                    )
                                except Exception as e:
                                    logger.error(f"Error notifying referrer: {e}")
                    except Exception as e:
                        logger.error(f"Error processing referral earning: {e}")
            
            # Очищаем состояние и сессию
            await state.clear()
            db.delete_user_session(user_id)
            
            logger.info(f"Order created successfully for user {user_id}")
        except Exception as e:
            logger.error(f"Error processing budget: {e}")
            await message.answer(config.MESSAGES["error_occurred"])

class TeamHandler:
    """Обработчик заявок в команду"""
    
    @staticmethod
    async def start_join_team(callback: types.CallbackQuery, state: FSMContext) -> None:
        """Начало заполнения анкеты для вступления в команду"""
        try:
            user_id = callback.from_user.id
            await state.set_state(JoinTeam.full_name)
            
            # Сохраняем сессию
            db.save_user_session(user_id, "join_team", {"step": "full_name"})
            
            # Надежное редактирование главного сообщения (учет медиа)
            await message_manager.edit_main_message(
                user_id,
                text=f"{config.EMOJI['handshake']} <b>Присоединение к команде Codif</b>\n\n{config.EMOJI['pencil']} <i>Шаг 1 из 6</i>\n\n{config.EMOJI['star']} <b>Введите ваше имя и фамилию:</b>\n\n{config.EMOJI['info']} <i>Например: Иван Петров</i>",
                message_id=callback.message.message_id,
                reply_markup=kb.back_button(),
                bot=callback.bot,
            )
            
            message_manager.set_last_question(user_id, callback.message.message_id)
            await callback.answer()
            
        except Exception as e:
            logger.error(f"Error starting join team: {e}")
            await callback.answer(config.MESSAGES["error_occurred"], show_alert=True)

    @staticmethod
    async def process_full_name(message: types.Message, state: FSMContext) -> None:
        """Обработка ФИО"""
        try:
            user_id = message.from_user.id
            await state.update_data(full_name=message.text)
            await state.set_state(JoinTeam.age)
            
            # Обновляем сессию
            db.save_user_session(user_id, "join_team", {"step": "age"})
            
            sent = await message.answer(
                f"{config.EMOJI['calendar']} <b>Возраст</b>\n\n{config.EMOJI['pencil']} <i>Шаг 2 из 6</i>\n\n{config.EMOJI['time']} <b>Введите ваш возраст:</b>\n\n{config.EMOJI['info']} <i>Укажите полных лет</i>",
                reply_markup=kb.back_button(),
                parse_mode="HTML"
            )
            
            message_manager.set_last_question(user_id, sent.message_id)
            
        except Exception as e:
            logger.error(f"Error processing full name: {e}")
            await message.answer(config.MESSAGES["error_occurred"])

    @staticmethod
    async def process_age(message: types.Message, state: FSMContext) -> None:
        """Обработка возраста"""
        try:
            user_id = message.from_user.id
            await state.update_data(age=message.text)
            await state.set_state(JoinTeam.experience)
            
            # Обновляем сессию
            db.save_user_session(user_id, "join_team", {"step": "experience"})
            
            sent = await message.answer(
                f"{config.EMOJI['trophy']} <b>Опыт работы</b>\n\n{config.EMOJI['pencil']} <i>Шаг 3 из 6</i>\n\n{config.EMOJI['chart']} <b>Расскажите о вашем опыте:</b>\n\n"
                f"{config.EMOJI['check']} Сколько лет в разработке?\n"
                f"{config.EMOJI['check']} Какие проекты реализовали?\n"
                f"{config.EMOJI['check']} Опыт работы в команде?\n"
                f"{config.EMOJI['check']} Участие в крупных проектах?\n\n"
                f"{config.EMOJI['bulb']} <i>Чем подробнее, тем лучше мы поймем ваш уровень!</i>",
                reply_markup=kb.back_button(),
                parse_mode="HTML"
            )
            
            message_manager.set_last_question(user_id, sent.message_id)
            
        except Exception as e:
            logger.error(f"Error processing age: {e}")
            await message.answer(config.MESSAGES["error_occurred"])

    @staticmethod
    async def process_experience(message: types.Message, state: FSMContext) -> None:
        """Обработка опыта работы"""
        try:
            user_id = message.from_user.id
            await state.update_data(experience=message.text)
            await state.set_state(JoinTeam.stack)
            
            # Обновляем сессию
            db.save_user_session(user_id, "join_team", {"step": "stack"})
            
            sent = await message.answer(
                f"{config.EMOJI['computer']} <b>Технологический стек</b>\n\n{config.EMOJI['pencil']} <i>Шаг 4 из 6</i>\n\n{config.EMOJI['tools']} <b>Перечислите ваши технологии:</b>\n\n"
                f"{config.EMOJI['gear']} Языки программирования\n"
                f"{config.EMOJI['wrench']} Фреймворки и библиотеки\n"
                f"{config.EMOJI['hammer']} Инструменты разработки\n"
                f"{config.EMOJI['folder']} Базы данных\n"
                f"{config.EMOJI['cloud']} Облачные платформы\n\n"
                f"{config.EMOJI['info']} <i>Укажите уровень владения каждой технологией</i>",
                reply_markup=kb.back_button(),
                parse_mode="HTML"
            )
            
            message_manager.set_last_question(user_id, sent.message_id)
            
        except Exception as e:
            logger.error(f"Error processing experience: {e}")
            await message.answer(config.MESSAGES["error_occurred"])

    @staticmethod
    async def process_stack(message: types.Message, state: FSMContext) -> None:
        """Обработка стека технологий"""
        try:
            user_id = message.from_user.id
            await state.update_data(stack=message.text)
            await state.set_state(JoinTeam.about)
            
            # Обновляем сессию
            db.save_user_session(user_id, "join_team", {"step": "about"})
            
            sent = await message.answer(
                f"{config.EMOJI['heart']} <b>О себе</b>\n\n{config.EMOJI['pencil']} <i>Шаг 5 из 6</i>\n\n{config.EMOJI['sparkles']} <b>Расскажите о себе:</b>\n\n"
                f"{config.EMOJI['star']} Ваши сильные стороны\n"
                f"{config.EMOJI['target']} Интересы в разработке\n"
                f"{config.EMOJI['rocket']} Цели и амбиции\n"
                f"{config.EMOJI['gem']} Что вас мотивирует?\n\n"
                f"{config.EMOJI['bulb']} <i>Помогите нам узнать вас лучше!</i>",
                reply_markup=kb.back_button(),
                parse_mode="HTML"
            )
            
            message_manager.set_last_question(user_id, sent.message_id)
            
        except Exception as e:
            logger.error(f"Error processing stack: {e}")
            await message.answer(config.MESSAGES["error_occurred"])

    @staticmethod
    async def process_about(message: types.Message, state: FSMContext) -> None:
        """Обработка информации о себе"""
        try:
            user_id = message.from_user.id
            await state.update_data(about=message.text)
            await state.set_state(JoinTeam.motivation)
            
            # Обновляем сессию
            db.save_user_session(user_id, "join_team", {"step": "motivation"})
            
            sent = await message.answer(
                f"{config.EMOJI['fire']} <b>Мотивация</b>\n\n{config.EMOJI['pencil']} <i>Шаг 6 из 6</i>\n\n{config.EMOJI['lightning']} <b>Почему именно Codif?</b>\n\n"
                f"{config.EMOJI['heart']} Что вас привлекает в нашей команде?\n"
                f"{config.EMOJI['crystal']} Какие возможности видите для себя?\n"
                f"{config.EMOJI['trophy']} Ваши ожидания от работы?\n"
                f"{config.EMOJI['handshake']} Как планируете развиваться с нами?\n\n"
                f"{config.EMOJI['sparkles']} <i>Последний шаг - расскажите о своих планах!</i>",
                reply_markup=kb.back_button(),
                parse_mode="HTML"
            )
            
            message_manager.set_last_question(user_id, sent.message_id)
            
        except Exception as e:
            logger.error(f"Error processing about: {e}")
            await message.answer(config.MESSAGES["error_occurred"])

    @staticmethod
    async def process_motivation(message: types.Message, state: FSMContext) -> None:
        """Обработка мотивации"""
        try:
            user_id = message.from_user.id
            await state.update_data(motivation=message.text)
            await state.set_state(JoinTeam.role)
            
            # Обновляем сессию
            db.save_user_session(user_id, "join_team", {"step": "role"})
            
            sent = await message.answer(
                f"{config.EMOJI['gear']} <b>Специализация</b>\n\n{config.EMOJI['pencil']} <i>Финальный шаг</i>\n\n{config.EMOJI['target']} <b>Выберите направление:</b>\n\n"
                f"{config.EMOJI['computer']} Frontend/Backend разработка\n"
                f"{config.EMOJI['phone']} Мобильная разработка\n"
                f"{config.EMOJI['cloud']} DevOps/Системная администрация\n"
                f"{config.EMOJI['art']} UI/UX дизайн\n"
                f"{config.EMOJI['shield']} Тестирование и QA\n"
                f"{config.EMOJI['rocket']} Product Management\n"
                f"{config.EMOJI['bulb']} Другое направление\n\n"
                f"{config.EMOJI['info']} <i>Можете указать несколько направлений</i>",
                reply_markup=kb.back_button(),
                parse_mode="HTML"
            )
            
            message_manager.set_last_question(user_id, sent.message_id)
            
        except Exception as e:
            logger.error(f"Error processing motivation: {e}")
            await message.answer(config.MESSAGES["error_occurred"])

    @staticmethod
    async def process_role(message: types.Message, state: FSMContext, bot: Bot) -> None:
        """Обработка роли и сохранение анкеты"""
        try:
            user_id = message.from_user.id
            await state.update_data(role=message.text)
            data = await state.get_data()
            
            # Сохраняем анкету в БД
            app_data = {
                "user_id": user_id,
                "username": message.from_user.username,
                "full_name": data["full_name"],
                "age": data["age"],
                "experience": data["experience"],
                "stack": data["stack"],
                "about": data["about"],
                "motivation": data["motivation"],
                "role": data["role"]
            }
            
            application = db.create_team_application(app_data)
            
            if application:
                # Уведомляем админов
                await notification_manager.notify_admins(
                    f"👥 <b>Новая заявка в команду!</b>\n\n"
                    f"👤 Пользователь: @{message.from_user.username}\n"
                    f"🆔 ID: {user_id}\n"
                    f"📝 Имя: {data['full_name']}\n"
                    f"🎭 Роль: {data['role']}\n"
                    f"💼 Опыт: {data['experience'][:50]}...",
                    bot
                )
                
                # Отправляем сообщение об успехе
                success_msg = await bot.send_message(
                    user_id,
                    f"{config.MESSAGES['application_success']}\n\n"
                    f"📋 <b>Детали заявки:</b>\n"
                    f"• Имя: {data['full_name']}\n"
                    f"• Роль: {data['role']}\n"
                    f"• Опыт: {data['experience'][:50]}...",
                    reply_markup=kb.success_action(),
                    parse_mode="HTML"
                )
                
                message_manager.set_success_message(user_id, success_msg.message_id)
                
                # Очищаем состояние и сессию
                await state.clear()
                db.delete_user_session(user_id)
                
                logger.info(f"Team application created successfully for user {user_id}")
            else:
                await message.answer(config.MESSAGES["error_occurred"])
                
        except Exception as e:
            logger.error(f"Error processing role: {e}")
            await message.answer(config.MESSAGES["error_occurred"])

class ConsultationHandler:
    """Обработчик консультаций"""
    
    @staticmethod
    async def start_consultation(callback: types.CallbackQuery, state: FSMContext) -> None:
        """Начало консультации"""
        try:
            user_id = callback.from_user.id
            await state.set_state(Consultation.question)
            
            # Сохраняем сессию
            db.save_user_session(user_id, "consultation", {"step": "question"})

            # Надежное редактирование главного сообщения (учитывает медиа)
            await message_manager.edit_main_message(
                user_id,
                text="💬 <b>Консультация</b>\n\nОпишите ваш вопрос подробно:",
                message_id=callback.message.message_id,
                reply_markup=kb.back_button(),
                bot=callback.bot,
            )

            # Сохраняем id сообщения с вопросом (id не меняется при редактировании)
            message_manager.set_last_question(user_id, callback.message.message_id)
            await callback.answer()
            
        except Exception as e:
            logger.error(f"Error starting consultation: {e}")
            await callback.answer(config.MESSAGES["error_occurred"], show_alert=True)

    @staticmethod
    async def process_question(message: types.Message, state: FSMContext, bot: Bot) -> None:
        """Обработка вопроса и сохранение запроса"""
        try:
            user_id = message.from_user.id
            question = message.text
            
            # Сохраняем запрос в БД
            req_data = {
                "user_id": user_id,
                "username": message.from_user.username,
                "question": question
            }
            
            request = db.create_consultation_request(req_data)
            
            if request:
                # Уведомляем админов
                await notification_manager.notify_admins(
                    f"💬 <b>Новый запрос на консультацию!</b>\n\n"
                    f"👤 Пользователь: @{message.from_user.username}\n"
                    f"🆔 ID: {user_id}\n"
                    f"❓ Вопрос: {question[:100]}...",
                    bot
                )
                
                # Отправляем сообщение об успехе
                success_msg = await bot.send_message(
                    user_id,
                    f"{config.MESSAGES['consultation_success']}\n\n"
                    f"📝 <b>Ваш вопрос:</b>\n{question[:200]}...",
                    reply_markup=kb.success_action(),
                    parse_mode="HTML"
                )
                
                message_manager.set_success_message(user_id, success_msg.message_id)
                
                # Очищаем состояние и сессию
                await state.clear()
                db.delete_user_session(user_id)
                
                logger.info(f"Consultation request created successfully for user {user_id}")
            else:
                await message.answer(config.MESSAGES["error_occurred"])
                
        except Exception as e:
            logger.error(f"Error processing question: {e}")
            await message.answer(config.MESSAGES["error_occurred"])

class PortfolioHandler:
    """Обработчик портфолио"""
    
    @staticmethod
    async def start_portfolio(callback: types.CallbackQuery, state: FSMContext, bot: Bot) -> None:
        """Начало просмотра портфолио"""
        try:
            user_id = callback.from_user.id
            await state.set_state(Portfolio.viewing)
            
            # Получаем проекты из БД
            projects = db.get_portfolio_projects()
            
            if projects:
                await PortfolioHandler.show_project(user_id, 0, len(projects), bot)
            else:
                await callback.answer(config.MESSAGES["no_portfolio"], show_alert=True)
                
            await callback.answer()
            
        except Exception as e:
            logger.error(f"Error starting portfolio: {e}")
            await callback.answer(config.MESSAGES["error_occurred"], show_alert=True)

    @staticmethod
    async def show_project(user_id: int, project_index: int, total: int, bot: Bot) -> None:
        """Отображение проекта портфолио"""
        try:
            projects = db.get_portfolio_projects()
            if not projects or project_index >= len(projects):
                return
                
            project = projects[project_index]
            
            # Красивое форматирование карточки проекта
            try:
                cost_str = f"{int(project.cost):,}".replace(",", " ")
            except Exception:
                cost_str = str(getattr(project, "cost", "—"))

            parts = [
                f"📌 <b>{project.title}</b>",
                "────────────",
                f"📝 <i>{project.description}</i>",
            ]

            if getattr(project, "duration", None):
                parts.append(f"⏱️ <b>Длительность разработки:</b> {project.duration}")

            parts.extend([
                f"💰 <b>Стоимость:</b> {cost_str} ₽",
                "────────────",
                f"📊 Проект {project_index + 1} из {total}",
            ])

            text = "\n".join(parts)
            
            markup = kb.portfolio_navigation(
                project_index,
                total,
                bot_url=getattr(project, 'bot_url', None)
            )

            # Поддержка premium эмодзи через entities
            emoji_entities = MessageManager.build_custom_emoji_entities(text, config.EMOJI_CUSTOM)

            # Показываем видео если есть, иначе текст
            if getattr(project, 'video_url', None):
                shown = await message_manager.show_main_video(
                    user_id,
                    caption=text,
                    video_url=project.video_url,
                    reply_markup=markup,
                    bot=bot,
                    caption_entities=emoji_entities if emoji_entities else None,
                )
                if not shown:
                    await message_manager.edit_main_message(
                        user_id,
                        text,
                        reply_markup=markup,
                        bot=bot,
                        entities=emoji_entities if emoji_entities else None,
                    )
            else:
                await message_manager.edit_main_message(
                    user_id,
                    text,
                    reply_markup=markup,
                    bot=bot,
                    entities=emoji_entities if emoji_entities else None,
                )
            
        except Exception as e:
            logger.error(f"Error showing project: {e}")

    @staticmethod
    async def portfolio_prev(callback: types.CallbackQuery, bot: Bot) -> None:
        """Переход к предыдущему проекту"""
        try:
            current_index = int(callback.data.split("_")[2])
            projects = db.get_portfolio_projects()
            
            if projects:
                new_index = (current_index - 1) % len(projects)
                await PortfolioHandler.show_project(callback.from_user.id, new_index, len(projects), bot)
                
            await callback.answer()
            
        except Exception as e:
            logger.error(f"Error in portfolio_prev: {e}")
            await callback.answer(config.MESSAGES["error_occurred"], show_alert=True)

    @staticmethod
    async def portfolio_next(callback: types.CallbackQuery, bot: Bot) -> None:
        """Переход к следующему проекту"""
        try:
            current_index = int(callback.data.split("_")[2])
            projects = db.get_portfolio_projects()
            
            if projects:
                new_index = (current_index + 1) % len(projects)
                await PortfolioHandler.show_project(callback.from_user.id, new_index, len(projects), bot)
                
            await callback.answer()
            
        except Exception as e:
            logger.error(f"Error in portfolio_next: {e}")
            await callback.answer(config.MESSAGES["error_occurred"], show_alert=True)

    @staticmethod
    async def portfolio_details(callback: types.CallbackQuery, state: FSMContext, bot: Bot) -> None:
        """Просмотр деталей проекта"""
        try:
            project_index = int(callback.data.split("_")[2])
            projects = db.get_portfolio_projects()
            
            if projects and project_index < len(projects):
                project = projects[project_index]
                await state.set_state(Portfolio.details)
                await state.update_data(current_index=project_index)
                
                try:
                    cost_str = f"{int(project.cost):,}".replace(",", " ")
                except Exception:
                    cost_str = str(getattr(project, "cost", "—"))

                parts = [
                    f"📌 <b>{project.title}</b>",
                    "────────────",
                    f"📋 <b>Описание:</b>\n{project.details}",
                ]
                if getattr(project, "duration", None):
                    parts.append(f"⏱️ <b>Длительность разработки:</b> {project.duration}")
                parts.extend([
                    f"💰 <b>Стоимость:</b> {cost_str} ₽",
                    "────────────",
                    f"📊 Проект {project_index + 1} из {len(projects)}",
                ])
                text = "\n".join(parts)

                # entities для premium эмодзи
                emoji_entities = MessageManager.build_custom_emoji_entities(text, config.EMOJI_CUSTOM)
                
                markup = kb.portfolio_navigation(
                    project_index,
                    len(projects),
                    show_details=True,
                    bot_url=getattr(project, 'bot_url', None),
                )
                if getattr(project, 'video_url', None):
                    shown = await message_manager.show_main_video(
                        callback.from_user.id,
                        caption=text,
                        video_url=project.video_url,
                        reply_markup=markup,
                        bot=bot,
                        caption_entities=emoji_entities if emoji_entities else None,
                    )
                    if not shown:
                        await message_manager.edit_main_message(
                            callback.from_user.id,
                            text,
                            reply_markup=markup,
                            bot=bot,
                            entities=emoji_entities if emoji_entities else None,
                        )
                else:
                    await message_manager.edit_main_message(
                        callback.from_user.id,
                        text,
                        reply_markup=markup,
                        bot=bot,
                        entities=emoji_entities if emoji_entities else None,
                    )
                
            await callback.answer()
            
        except Exception as e:
            logger.error(f"Error in portfolio_details: {e}")
            await callback.answer(config.MESSAGES["error_occurred"], show_alert=True)

    @staticmethod
    async def portfolio_back(callback: types.CallbackQuery, state: FSMContext, bot: Bot) -> None:
        """Возврат к списку проектов"""
        try:
            project_index = int(callback.data.split("_")[2])
            await state.set_state(Portfolio.viewing)
            
            projects = db.get_portfolio_projects()
            if projects:
                await PortfolioHandler.show_project(callback.from_user.id, project_index, len(projects), bot)
                
            await callback.answer()
            
        except Exception as e:
            logger.error(f"Error in portfolio_back: {e}")
            await callback.answer(config.MESSAGES["error_occurred"], show_alert=True)

# Регистрация обработчиков
@main_router.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await MainHandler.start_command(message, state)

@main_router.callback_query(F.data == "back_to_main")
async def back_to_main(callback: types.CallbackQuery, state: FSMContext, bot: Bot):
    await MainHandler.back_to_main(callback, state, bot)

@main_router.callback_query(F.data == "cancel_questionnaire")
async def cancel_questionnaire(callback: types.CallbackQuery, state: FSMContext, bot: Bot):
    await MainHandler.cancel_questionnaire(callback, state, bot)

# Заказы
@main_router.callback_query(F.data == "order_bot")
async def start_order_bot(callback: types.CallbackQuery, state: FSMContext):
    await OrderHandler.start_order(callback, state)

@main_router.callback_query(F.data.startswith("order_type_"))
async def select_order_type(callback: types.CallbackQuery, state: FSMContext):
    await OrderHandler.select_order_type(callback, state)

@main_router.message(ClientOrder.project_name)
async def process_project_name(message: types.Message, state: FSMContext):
    await OrderHandler.process_project_name(message, state)

@main_router.message(ClientOrder.functionality)
async def process_functionality(message: types.Message, state: FSMContext):
    await OrderHandler.process_functionality(message, state)

@main_router.message(ClientOrder.deadlines)
async def process_deadlines(message: types.Message, state: FSMContext):
    await OrderHandler.process_deadlines(message, state)

@main_router.message(ClientOrder.budget)
async def process_budget(message: types.Message, state: FSMContext, bot: Bot):
    await OrderHandler.process_budget(message, state, bot)

# Команда
@main_router.callback_query(F.data == "join_team")
async def start_join_team(callback: types.CallbackQuery, state: FSMContext):
    await TeamHandler.start_join_team(callback, state)

@main_router.message(JoinTeam.full_name)
async def process_full_name(message: types.Message, state: FSMContext):
    await TeamHandler.process_full_name(message, state)

@main_router.message(JoinTeam.age)
async def process_age(message: types.Message, state: FSMContext):
    await TeamHandler.process_age(message, state)

@main_router.message(JoinTeam.experience)
async def process_experience(message: types.Message, state: FSMContext):
    await TeamHandler.process_experience(message, state)

@main_router.message(JoinTeam.stack)
async def process_stack(message: types.Message, state: FSMContext):
    await TeamHandler.process_stack(message, state)

@main_router.message(JoinTeam.about)
async def process_about(message: types.Message, state: FSMContext):
    await TeamHandler.process_about(message, state)

@main_router.message(JoinTeam.motivation)
async def process_motivation(message: types.Message, state: FSMContext):
    await TeamHandler.process_motivation(message, state)

@main_router.message(JoinTeam.role)
async def process_role(message: types.Message, state: FSMContext, bot: Bot):
    await TeamHandler.process_role(message, state, bot)

# Консультации
@main_router.callback_query(F.data == "consultation")
async def start_consultation(callback: types.CallbackQuery, state: FSMContext):
    await ConsultationHandler.start_consultation(callback, state)

@main_router.message(Consultation.question)
async def process_question(message: types.Message, state: FSMContext, bot: Bot):
    await ConsultationHandler.process_question(message, state, bot)

# Портфолио
@main_router.callback_query(F.data == "portfolio")
async def start_portfolio(callback: types.CallbackQuery, state: FSMContext, bot: Bot):
    await PortfolioHandler.start_portfolio(callback, state, bot)

@main_router.callback_query(F.data.startswith("portfolio_prev_"))
async def portfolio_prev(callback: types.CallbackQuery, bot: Bot):
    await PortfolioHandler.portfolio_prev(callback, bot)

@main_router.callback_query(F.data.startswith("portfolio_next_"))
async def portfolio_next(callback: types.CallbackQuery, bot: Bot):
    await PortfolioHandler.portfolio_next(callback, bot)

@main_router.callback_query(F.data.startswith("portfolio_details_"))
async def portfolio_details(callback: types.CallbackQuery, state: FSMContext, bot: Bot):
    await PortfolioHandler.portfolio_details(callback, state, bot)

@main_router.callback_query(F.data.startswith("portfolio_back_"))
async def portfolio_back(callback: types.CallbackQuery, state: FSMContext, bot: Bot):
    await PortfolioHandler.portfolio_back(callback, state, bot)

# Реферальная система
@main_router.callback_query(F.data == "referral_system")
async def start_referral_system(callback: types.CallbackQuery, state: FSMContext):
    await ReferralHandler.start_referral_system(callback, state)

@main_router.callback_query(F.data == "referral_stats")
async def show_referral_stats(callback: types.CallbackQuery, state: FSMContext):
    await ReferralHandler.show_referral_stats(callback, state)

@main_router.callback_query(F.data == "referral_link")
async def show_referral_link(callback: types.CallbackQuery, state: FSMContext):
    await ReferralHandler.show_referral_link(callback, state)

@main_router.callback_query(F.data == "referral_setup_wallet")
async def setup_wallet_start(callback: types.CallbackQuery, state: FSMContext):
    await ReferralHandler.setup_wallet_start(callback, state)

@main_router.callback_query(F.data.startswith("wallet_method_"))
async def select_wallet_method(callback: types.CallbackQuery, state: FSMContext):
    await ReferralHandler.select_wallet_method(callback, state)

@main_router.message(ReferralSystem.enter_wallet)
async def process_wallet_info(message: types.Message, state: FSMContext):
    await ReferralHandler.process_wallet_info(message, state)

@main_router.message(ReferralSystem.setup_wallet)
async def process_full_name(message: types.Message, state: FSMContext):
    await ReferralHandler.process_full_name(message, state)

@main_router.callback_query(F.data == "referral_earnings")
async def show_earnings(callback: types.CallbackQuery, state: FSMContext):
    await ReferralHandler.show_earnings(callback, state)

@main_router.callback_query(F.data == "request_payout")
async def request_payout(callback: types.CallbackQuery, state: FSMContext):
    await ReferralHandler.request_payout(callback, state)

# Неактивная метка прогресса, чтобы Telegram не показывал вечную загрузку
@main_router.callback_query(F.data == "portfolio_progress")
async def portfolio_progress(callback: types.CallbackQuery):
    await callback.answer()