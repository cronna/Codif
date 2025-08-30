import random
import string
from aiogram import types, Bot
from aiogram.fsm.context import FSMContext
from aiogram import F

from app.db.database import db
from app.fsm import ReferralSystem
from app.keyboards import referral_main_menu_keyboard, referral_wallet_methods_keyboard, referral_earnings_actions_keyboard, back_button
from app.utils.message_manager import message_manager
from app.utils.notification_manager import notification_manager
from config import config
import logging

logger = logging.getLogger(__name__)

class ReferralHandler:
    """Обработчик реферальной системы"""
    
    @staticmethod
    def generate_referral_code(user_id: int) -> str:
        """Генерация уникального реферального кода"""
        # Используем часть user_id и случайные символы
        random_part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
        return f"REF{user_id % 10000}{random_part}"
    
    @staticmethod
    async def start_referral_system(callback: types.CallbackQuery, state: FSMContext) -> None:
        """Главное меню реферальной системы"""
        try:
            user_id = callback.from_user.id
            await state.set_state(ReferralSystem.main)
            
            # Получаем или создаем реферального пользователя
            referral_user = db.get_referral_user(user_id)
            if not referral_user:
                # Создаем нового реферального пользователя
                referral_code = ReferralHandler.generate_referral_code(user_id)
                referral_user = db.create_referral_user(
                    user_id=user_id,
                    username=callback.from_user.username,
                    referral_code=referral_code
                )
            
            await message_manager.edit_main_message(
                user_id,
                text=config.MESSAGES["referral_welcome"],
                message_id=callback.message.message_id,
                reply_markup=referral_main_menu_keyboard(),
                bot=callback.bot,
            )
            
        except Exception as e:
            logger.error(f"Error starting referral system: {e}")
            await callback.answer("Произошла ошибка", show_alert=True)

    @staticmethod
    async def show_referral_stats(callback: types.CallbackQuery, state: FSMContext) -> None:
        """Показать статистику реферера"""
        try:
            user_id = callback.from_user.id
            stats = db.get_referral_stats(user_id)
            
            if not stats:
                await message_manager.edit_main_message(
                    user_id,
                    text=config.MESSAGES["referral_no_stats"],
                    message_id=callback.message.message_id,
                    reply_markup=referral_main_menu_keyboard(),
                    bot=callback.bot,
                )
                return
            
            # Формируем текст статистики
            stats_text = (
                f"{config.MESSAGES['referral_stats']}\n\n"
                f"{config.EMOJI['referral']} <b>Приведено пользователей:</b> {stats['total_referrals']}\n"
                f"{config.EMOJI['earnings']} <b>Всего заработано:</b> {stats['total_earned']:.2f}₽\n"
                f"{config.EMOJI['balance']} <b>Доступно к выводу:</b> {stats['balance']:.2f}₽\n"
                f"{config.EMOJI['paid']} <b>Выплачено:</b> {stats['total_paid']:.2f}₽\n\n"
                f"{config.EMOJI['link']} <b>Ваш реферальный код:</b> <code>{stats['referral_code']}</code>\n\n"
                f"{config.EMOJI['info']} <i>Поделитесь своей ссылкой с друзьями!</i>"
            )
            
            await message_manager.edit_main_message(
                user_id,
                text=stats_text,
                message_id=callback.message.message_id,
                reply_markup=referral_main_menu_keyboard(),
                bot=callback.bot,
            )
            
        except Exception as e:
            logger.error(f"Error showing referral stats: {e}")
            await callback.answer("Произошла ошибка", show_alert=True)

    @staticmethod
    async def show_referral_link(callback: types.CallbackQuery, state: FSMContext) -> None:
        """Показать реферальную ссылку"""
        try:
            user_id = callback.from_user.id
            stats = db.get_referral_stats(user_id)
            
            if not stats:
                await callback.answer("Ошибка получения данных", show_alert=True)
                return
            
            bot_username = (await callback.bot.get_me()).username
            referral_link = f"https://t.me/{bot_username}?start=ref_{stats['referral_code']}"
            
            link_text = (
                f"{config.MESSAGES['referral_link_generated']}\n\n"
                f"{config.EMOJI['link']} <b>Ваша ссылка:</b>\n"
                f"<code>{referral_link}</code>\n\n"
                f"{config.EMOJI['money']} За каждый оплаченный заказ по этой ссылке вы получите <b>25%</b> от суммы заказа!"
            )
            
            await message_manager.edit_main_message(
                user_id,
                text=link_text,
                message_id=callback.message.message_id,
                reply_markup=referral_main_menu_keyboard(),
                bot=callback.bot,
            )
            
        except Exception as e:
            logger.error(f"Error showing referral link: {e}")
            await callback.answer("Произошла ошибка", show_alert=True)

    @staticmethod
    async def setup_wallet_start(callback: types.CallbackQuery, state: FSMContext) -> None:
        """Начало настройки кошелька для выплат"""
        try:
            user_id = callback.from_user.id
            await state.set_state(ReferralSystem.wallet_method)
            
            await message_manager.edit_main_message(
                user_id,
                text=config.MESSAGES["setup_wallet_prompt"],
                message_id=callback.message.message_id,
                reply_markup=referral_wallet_methods_keyboard(),
                bot=callback.bot,
            )
            
        except Exception as e:
            logger.error(f"Error starting wallet setup: {e}")
            await callback.answer("Произошла ошибка", show_alert=True)

    @staticmethod
    async def select_wallet_method(callback: types.CallbackQuery, state: FSMContext) -> None:
        """Выбор метода выплат"""
        try:
            user_id = callback.from_user.id
            method = callback.data.split("_")[-1]  # card или sbp
            
            await state.update_data(payout_method=method)
            await state.set_state(ReferralSystem.enter_wallet)
            
            if method == "card":
                prompt = config.MESSAGES["enter_card_number"]
            else:  # sbp
                prompt = config.MESSAGES["enter_phone_number"]
            
            await message_manager.edit_main_message(
                user_id,
                text=prompt,
                message_id=callback.message.message_id,
                reply_markup=back_button(),
                bot=callback.bot,
            )
            
        except Exception as e:
            logger.error(f"Error selecting wallet method: {e}")
            await callback.answer("Произошла ошибка", show_alert=True)

    @staticmethod
    async def process_wallet_info(message: types.Message, state: FSMContext) -> None:
        """Обработка данных кошелька"""
        try:
            user_id = message.from_user.id
            data = await state.get_data()
            method = data.get("payout_method")
            
            if method == "card":
                # Валидация номера карты (упрощенная)
                card_number = message.text.replace(" ", "").replace("-", "")
                if not card_number.isdigit() or len(card_number) != 16:
                    await message.answer("❌ Неверный формат номера карты. Попробуйте еще раз.")
                    return
                
                # Маскируем номер карты для безопасности
                masked_card = f"{card_number[:4]} **** **** {card_number[-4:]}"
                await state.update_data(card_number=masked_card)
                
            else:  # sbp
                # Валидация номера телефона (упрощенная)
                phone = message.text.replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
                if not phone.startswith("+7") or len(phone) != 12:
                    await message.answer("❌ Неверный формат номера телефона. Попробуйте еще раз.")
                    return
                
                await state.update_data(phone_number=phone)
            
            # Запрашиваем ФИО
            await state.set_state(ReferralSystem.setup_wallet)
            await message.answer(
                config.MESSAGES["enter_full_name"],
                reply_markup=back_button(),
                parse_mode="HTML"
            )
            
        except Exception as e:
            logger.error(f"Error processing wallet info: {e}")
            await message.answer("Произошла ошибка. Попробуйте еще раз.")

    @staticmethod
    async def process_full_name(message: types.Message, state: FSMContext) -> None:
        """Обработка ФИО и сохранение данных"""
        try:
            user_id = message.from_user.id
            data = await state.get_data()
            full_name = message.text.strip()
            
            # Простая валидация ФИО
            if len(full_name.split()) < 2:
                await message.answer("❌ Введите полное ФИО (Фамилия Имя Отчество)")
                return
            
            # Сохраняем данные в базу
            success = db.update_referral_user_payout_info(
                user_id=user_id,
                method=data.get("payout_method"),
                card_number=data.get("card_number"),
                phone_number=data.get("phone_number"),
                full_name=full_name
            )
            
            if success:
                await message.answer(
                    config.MESSAGES["wallet_setup_success"],
                    reply_markup=referral_main_menu_keyboard(),
                    parse_mode="HTML"
                )
                await state.set_state(ReferralSystem.main)
            else:
                await message.answer("❌ Ошибка сохранения данных. Попробуйте еще раз.")
            
        except Exception as e:
            logger.error(f"Error processing full name: {e}")
            await message.answer("Произошла ошибка. Попробуйте еще раз.")

    @staticmethod
    async def show_earnings(callback: types.CallbackQuery, state: FSMContext) -> None:
        """Показать историю начислений"""
        try:
            user_id = callback.from_user.id
            earnings = db.get_referral_earnings(user_id)
            
            if not earnings:
                await message_manager.edit_main_message(
                    user_id,
                    text=config.MESSAGES["no_earnings"],
                    message_id=callback.message.message_id,
                    reply_markup=referral_main_menu_keyboard(),
                    bot=callback.bot,
                )
                return
            
            # Формируем список начислений
            earnings_text = f"{config.EMOJI['history']} <b>История начислений</b>\n\n"
            
            for earning in earnings[:10]:  # Показываем последние 10
                status_emoji = {
                    'pending': config.EMOJI['pending'],
                    'confirmed': config.EMOJI['confirmed'],
                    'paid': config.EMOJI['paid']
                }.get(earning.status, '❓')
                
                earnings_text += (
                    f"{status_emoji} <b>{earning.earned_amount:.2f}₽</b> "
                    f"({earning.created_at.strftime('%d.%m.%Y')})\n"
                    f"   Заказ #{earning.order_id} - {earning.order_amount:.2f}₽\n\n"
                )
            
            if len(earnings) > 10:
                earnings_text += f"<i>... и еще {len(earnings) - 10} начислений</i>\n\n"
            
            # Добавляем статусы
            earnings_text += (
                f"{config.EMOJI['pending']} Ожидает оплаты\n"
                f"{config.EMOJI['confirmed']} Оплачен\n"
                f"{config.EMOJI['paid']} Выплачен"
            )
            
            await message_manager.edit_main_message(
                user_id,
                text=earnings_text,
                message_id=callback.message.message_id,
                reply_markup=referral_earnings_actions_keyboard(),
                bot=callback.bot,
            )
            
        except Exception as e:
            logger.error(f"Error showing earnings: {e}")
            await callback.answer("Произошла ошибка", show_alert=True)

    @staticmethod
    async def request_payout(callback: types.CallbackQuery, state: FSMContext) -> None:
        """Запрос выплаты"""
        try:
            user_id = callback.from_user.id
            stats = db.get_referral_stats(user_id)
            
            if not stats or stats['balance'] < 500:  # Минимальная сумма 500₽
                await callback.answer(
                    config.MESSAGES["insufficient_balance"],
                    show_alert=True
                )
                return
            
            # Проверяем настройки выплат
            if not stats['full_name'] or (not stats['card_number'] and not stats['phone_number']):
                await callback.answer(
                    "❌ Сначала настройте данные для выплат",
                    show_alert=True
                )
                return
            
            # Формируем информацию о получателе
            if stats['payout_method'] == 'card':
                recipient_info = f"Карта: {stats['card_number']}, {stats['full_name']}"
            else:
                recipient_info = f"СБП: {stats['phone_number']}, {stats['full_name']}"
            
            # Создаем запрос на выплату
            payout = db.create_referral_payout_request(
                referrer_id=user_id,
                amount=stats['balance'],
                method=stats['payout_method'],
                recipient_info=recipient_info
            )
            
            if payout:
                # Уведомляем админов
                await notification_manager.notify_admins(
                    f"💸 <b>Новый запрос на выплату реферальных!</b>\n\n"
                    f"👤 Пользователь: @{callback.from_user.username}\n"
                    f"🆔 ID: {user_id}\n"
                    f"💰 Сумма: {stats['balance']:.2f}₽\n"
                    f"💳 Метод: {stats['payout_method']}\n"
                    f"📝 Реквизиты: {recipient_info}",
                    callback.bot
                )
                
                await callback.answer(
                    config.MESSAGES["payout_request_success"],
                    show_alert=True
                )
            else:
                await callback.answer("❌ Ошибка создания запроса", show_alert=True)
            
        except Exception as e:
            logger.error(f"Error requesting payout: {e}")
            await callback.answer("Произошла ошибка", show_alert=True)

    @staticmethod
    async def process_referral_start(user_id: int, referral_code: str, username: str = None) -> bool:
        """Обработка перехода по реферальной ссылке"""
        try:
            # Находим реферера по коду
            referrer = db.get_referral_user_by_code(referral_code)
            if not referrer:
                return False
            
            # Проверяем, что пользователь не пытается стать рефералом самого себя
            if referrer.user_id == user_id:
                return False
            
            # Проверяем, не является ли пользователь уже чьим-то рефералом
            existing_referral = db.get_referral_user(user_id)
            if existing_referral and existing_referral.referred_by:
                return False  # Уже чей-то реферал
            
            # Создаем или обновляем реферального пользователя
            if existing_referral:
                # Обновляем существующего пользователя
                existing_referral.referred_by = referrer.user_id
            else:
                # Создаем нового реферального пользователя
                new_code = ReferralHandler.generate_referral_code(user_id)
                db.create_referral_user(
                    user_id=user_id,
                    username=username,
                    referral_code=new_code,
                    referred_by=referrer.user_id
                )
            
            logger.info(f"User {user_id} became referral of {referrer.user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error processing referral start: {e}")
            return False
