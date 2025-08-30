import os
import json
from dotenv import load_dotenv

# Загружаем переменные окружения из .env файла
load_dotenv()

class Config:
    """Конфигурация бота"""
    
    # Основные настройки
    BOT_TOKEN = os.getenv("BOT_TOKEN", "8076800755:AAETbYbCio_e1cM_lErJmovtVyTPzpxbNJw")
    CHANNEL_LINK = os.getenv("CHANNEL_LINK", "https://t.me/codifofficial")
    
    # Администраторы (ID через запятую)
    ADMIN_IDS = [
        int(admin_id.strip()) 
        for admin_id in os.getenv("ADMIN_IDS", "5534526646").split(",")
        if admin_id.strip().isdigit()
    ]
    
    # Настройки базы данных
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///bot.db")
    
    # Настройки логирования
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # Настройки интерфейса
    MAX_MESSAGE_LENGTH = 4096
    MAX_BUTTONS_PER_ROW = 2
    
    # Эмодзи для интерфейса
    EMOJI = {
        "bot": "🤖",
        "team": "👥", 
        "portfolio": "🎨",
        "consultation": "💬",
        "admin": "👑",
        "back": "◀️",
        "next": "▶️",
        "success": "✅",
        "error": "❌",
        "warning": "⚠️",
        "info": "ℹ️",
        "edit": "✏️",
        "delete": "🗑️",
        "add": "➕",
        "contact": "📞",
        "channel": "📢",
        "star": "⭐",
        "fire": "🔥",
        "rocket": "🚀",
        "gem": "💎",
        "crown": "👑",
        "lightning": "⚡",
        "sparkles": "✨",
        "target": "🎯",
        "magic": "🪄",
        "gift": "🎁",
        "money": "💰",
        "chart": "📊",
        "wallet": "💳",
        "history": "📋",
        "link": "🔗",
        "request": "💸",
        "refresh": "🔄",
        "card": "💳",
        "phone": "📱",
        "user": "👤",
        "calendar": "📅",
        "document": "📄",
        "handshake": "🤝",
        "pencil": "✏️",
        "crystal": "🔮",
        "trophy": "🏆",
        "medal": "🥇",
        "shield": "🛡️",
        "key": "🔑",
        "lock": "🔒",
        "home": "🏠",
        "arrow_up": "⬆️",
        "arrow_down": "⬇️",
        "check": "✔️",
        "robot": "🤖"
    }
    
    # Сообщения интерфейса
    MESSAGES = {
        # Реферальная система
        "referral_welcome": f"{EMOJI['gift']} <b>Реферальная программа Codif</b>\n\n{EMOJI['money']} Приводите клиентов и получайте <b>25% с каждого заказа!</b>\n\n{EMOJI['info']} Как это работает:\n• Делитесь своей реферальной ссылкой\n• Клиент заказывает бота через вашу ссылку\n• После оплаты вам начисляется 25%\n• Запрашиваете выплату когда удобно",
        
        "referral_stats": f"{EMOJI['chart']} <b>Ваша статистика</b>\n\n{EMOJI['user']} Приведено рефералов: {{total_referrals}}\n{EMOJI['money']} Всего заработано: {{total_earned}}₽\n{EMOJI['wallet']} Доступно к выводу: {{balance}}₽\n{EMOJI['success']} Уже выплачено: {{total_paid}}₽",
        
        "referral_link_message": f"{EMOJI['link']} <b>Ваша реферальная ссылка:</b>\n\n<code>{{referral_link}}</code>\n\n{EMOJI['info']} Отправьте эту ссылку друзьям и знакомым. Когда они закажут бота через неё, вы получите 25% от суммы заказа!",
        
        "referral_payout_requested": f"{EMOJI['success']} <b>Запрос на выплату отправлен!</b>\n\n{EMOJI['money']} Сумма: {{amount}}₽\n{EMOJI['info']} Мы обработаем ваш запрос в течение 1-2 рабочих дней и переведём деньги на указанные реквизиты.",
        
        "referral_setup_wallet": f"{EMOJI['wallet']} <b>Настройка выплат</b>\n\n{EMOJI['info']} Выберите удобный способ получения выплат:\n\n{EMOJI['card']} <b>Банковская карта</b> - переводы через СБП\n{EMOJI['phone']} <b>ЮMoney</b> - на номер телефона\n{EMOJI['phone']} <b>QIWI</b> - на номер телефона",
        
        "referral_enter_card": f"{EMOJI['card']} <b>Банковская карта</b>\n\n{EMOJI['pencil']} Введите номер карты для переводов через СБП:\n\n{EMOJI['info']} Формат: 1234 5678 9012 3456",
        
        "referral_enter_phone": f"{EMOJI['phone']} <b>Номер телефона</b>\n\n{EMOJI['pencil']} Введите номер телефона для переводов:\n\n{EMOJI['info']} Формат: +7 900 123 45 67",
        
        "referral_enter_name": f"{EMOJI['user']} <b>ФИО для переводов</b>\n\n{EMOJI['pencil']} Введите ваше полное имя как в паспорте:\n\n{EMOJI['info']} Например: Иванов Иван Иванович",
        
        "referral_wallet_saved": f"{EMOJI['success']} <b>Реквизиты сохранены!</b>\n\n{EMOJI['info']} Теперь вы можете запрашивать выплаты. Мы будем переводить деньги на указанные реквизиты.",
        
        "referral_insufficient_balance": f"{EMOJI['error']} <b>Недостаточно средств</b>\n\n{EMOJI['info']} Ваш баланс: {{balance}}₽\nМинимальная сумма для вывода: 500₽",
        
        "referral_earning_confirmed": f"{EMOJI['success']} <b>Начисление подтверждено!</b>\n\n{EMOJI['money']} Сумма: {{amount}}₽\n{EMOJI['user']} За заказ от: @{{username}}\n\n{EMOJI['info']} Средства добавлены на ваш баланс и доступны для вывода.",
        "welcome": (
        f"{EMOJI['sparkles']} <b>Добро пожаловать в Codif Bot!</b> {EMOJI['sparkles']}\n\n"
        f"{EMOJI['rocket']} <i>Мы создаем инновационные телеграм боты и современные веб-приложения</i>\n\n"
        f"{EMOJI['gem']} <b>Выберите интересующий раздел:</b>"
    ),
        "order_success": "🎉 <b>Заявка успешно отправлена!</b>\n\n✨ Наши специалисты свяжутся с вами в течение 24 часов\n\n💼 <i>Спасибо за доверие к Codif!</i>",
        "application_success": "🌟 <b>Заявка в команду принята!</b>\n\n🔍 Мы тщательно рассмотрим вашу кандидатуру\n\n📞 <i>Ожидайте обратную связь в ближайшие дни</i>",
        "consultation_success": "💬 <b>Запрос на консультацию получен!</b>\n\n🎯 Наш эксперт подготовит детальный ответ\n\n⚡ <i>Обычно отвечаем в течение нескольких часов</i>",
        "no_portfolio": "🎨 <b>Портфолио временно недоступно</b>\n\n🔄 <i>Мы обновляем наши проекты</i>\n\n📅 Загляните чуть позже!",
        "access_denied": "🔒 <b>Доступ ограничен</b>\n\n👤 <i>У вас нет прав для этой функции</i>",
        "error_occurred": "⚠️ <b>Что-то пошло не так</b>\n\n🔄 <i>Попробуйте повторить операцию</i>\n\n📞 Если проблема повторяется - свяжитесь с поддержкой",
        "cancelled": "❌ <b>Операция отменена</b>\n\n🔙 <i>Возвращаемся к предыдущему шагу</i>",
        "back_to_main": "🏠 <b>Возвращаемся в главное меню</b>\n\n✨ <i>Готовы к новым задачам!</i>",
        "calendar": "📅",
        "document": "📄",
        "handshake": "🤝",
        "pencil": "✏️",
        "crystal": "🔮",
        "trophy": "🏆",
        "medal": "🥇",
        "shield": "🛡️",
        "key": "🔑",
        "lock": "🔒",
        "home": "🏠",
        "arrow_up": "⬆️",
        "arrow_down": "⬇️",
        "check": "✔️",
        "cross": "✖️",
        "heart": "❤️",
        "thumbs_up": "👍",
        "handshake": "🤝",
        "money": "💰",
        "time": "⏰",
        "calendar": "📅",
        "document": "📄",
        "bulb": "💡",
        "chart": "📊",
        "tools": "🛠️",
        "computer": "💻",
        "phone": "📱",
        "robot": "🤖",
        "email": "📧",
        "message": "💌",
        "bell": "🔔",
        "megaphone": "📣",
        "loudspeaker": "📢",
        "microphone": "🎤",
        "camera": "📷",
        "video": "🎥",
        "play": "▶️",
        "pause": "⏸️",
        "stop": "⏹️",
        "record": "⏺️",
        "fast_forward": "⏩",
        "rewind": "⏪",
        "repeat": "🔁",
        "shuffle": "🔀",
        "volume_up": "🔊",
        "volume_down": "🔉",
        "mute": "🔇",
        "battery": "🔋",
        "plug": "🔌",
        "signal": "📶",
        "wifi": "📶",
        "bluetooth": "📶",
        "location": "📍",
        "map": "🗺️",
        "compass": "🧭",
        "globe": "🌍",
        "satellite": "🛰️",
        "airplane": "✈️",
        "car": "🚗",
        "train": "🚆",
        "ship": "🚢",
        "bicycle": "🚴",
        "walking": "🚶",
        "running": "🏃",
        "dancing": "💃",
        "music": "🎵",
        "note": "🎶",
        "headphones": "🎧",
        "radio": "📻",
        "tv": "📺",
        "movie": "🎬",
        "game": "🎮",
        "dice": "🎲",
        "puzzle": "🧩",
        "art": "🎨",
        "brush": "🖌️",
        "palette": "🎨",
        "frame": "🖼️",
        "book": "📚",
        "newspaper": "📰",
        "magazine": "📖",
        "scroll": "📜",
        "page": "📃",
        "clipboard": "📋",
        "pushpin": "📌",
        "paperclip": "📎",
        "ruler": "📏",
        "triangular_ruler": "📐",
        "scissors": "✂️",
        "pen": "🖊️",
        "pencil": "✏️",
        "crayon": "🖍️",
        "paintbrush": "🖌️",
        "magnifying_glass": "🔍",
        "microscope": "🔬",
        "telescope": "🔭",
        "crystal_ball": "🔮",
        "joystick": "🕹️",
        "slot_machine": "🎰",
        "bowling": "🎳",
        "pool": "🎱",
        "yo_yo": "🪀",
        "kite": "🪁",
        "magic_wand": "🪄"
    }
    
    # Тексты сообщений
    MESSAGES = {
        "welcome": (
        f"{EMOJI['sparkles']} <b>Добро пожаловать в Codif Bot!</b> {EMOJI['sparkles']}\n\n"
        f"{EMOJI['rocket']} <i>Мы создаем инновационные телеграм боты и современные веб-приложения</i>\n\n"
        f"{EMOJI['gem']} <b>Выберите интересующий раздел:</b>"
    ),
        "order_success": "🎉 <b>Заявка успешно отправлена!</b>\n\n✨ Наши специалисты свяжутся с вами в течение 24 часов\n\n💼 <i>Спасибо за доверие к Codif!</i>",
        "application_success": "🌟 <b>Заявка в команду принята!</b>\n\n🔍 Мы тщательно рассмотрим вашу кандидатуру\n\n📞 <i>Ожидайте обратную связь в ближайшие дни</i>",
        "consultation_success": "💬 <b>Запрос на консультацию получен!</b>\n\n🎯 Наш эксперт подготовит детальный ответ\n\n⚡ <i>Обычно отвечаем в течение нескольких часов</i>",
        "no_portfolio": "🎨 <b>Портфолио временно недоступно</b>\n\n🔄 <i>Мы обновляем наши проекты</i>\n\n📅 Загляните чуть позже!",
        "access_denied": "🔒 <b>Доступ ограничен</b>\n\n👤 <i>У вас нет прав для этой функции</i>",
        "error_occurred": "⚠️ <b>Что-то пошло не так</b>\n\n🔄 <i>Попробуйте повторить операцию</i>\n\n📞 Если проблема повторяется - свяжитесь с поддержкой",
        "cancelled": "❌ <b>Операция отменена</b>\n\n🔙 <i>Возвращаемся к предыдущему шагу</i>",
        "back_to_main": "🏠 <b>Возвращаемся в главное меню</b>\n\n✨ <i>Готовы к новым задачам!</i>"
    }

    # Кастомные (premium) эмодзи: маппинг символа -> custom_emoji_id
    # Можно задать переменной окружения CUSTOM_EMOJI_MAP (JSON), например:
    # {"🎨": "5432967052265780841", "💬": "5432967052540209738"}
    try:
        EMOJI_CUSTOM = json.loads(os.getenv("CUSTOM_EMOJI_MAP", "{}"))
        if not isinstance(EMOJI_CUSTOM, dict):
            EMOJI_CUSTOM = {}
    except Exception:
        EMOJI_CUSTOM = {}

# Создаем экземпляр конфигурации
config = Config()

# Для обратной совместимости
BOT_TOKEN = config.BOT_TOKEN
CHANNEL_LINK = config.CHANNEL_LINK
ADMIN_IDS = config.ADMIN_IDS