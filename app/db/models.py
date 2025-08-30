from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Index, Float, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.sql import func
from config import config

Base = declarative_base()

class ClientOrder(Base):
    """Модель заявки на разработку бота или мини-приложения"""
    __tablename__ = 'client_orders'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False, index=True)
    username = Column(String(100))
    order_type = Column(String(20), default='bot', nullable=False)  # bot, miniapp
    project_name = Column(String(200), nullable=False)
    functionality = Column(Text, nullable=False)
    deadlines = Column(String(100), nullable=False)
    budget = Column(String(100), nullable=False)
    status = Column(String(20), default='new', index=True)  # new, accepted, rejected, completed, paid
    final_price = Column(Float)  # Окончательная цена, установленная администратором
    admin_notes = Column(Text)  # Заметки администратора
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Индексы для оптимизации запросов
    __table_args__ = (
        Index('idx_client_orders_user_status', 'user_id', 'status'),
        Index('idx_client_orders_created', 'created_at'),
    )

class TeamApplication(Base):
    """Модель заявки в команду"""
    __tablename__ = 'team_applications'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False, index=True)
    username = Column(String(100))
    full_name = Column(String(200), nullable=False)
    age = Column(String(10), nullable=False)
    experience = Column(String(500), nullable=False)
    stack = Column(Text, nullable=False)
    about = Column(Text, nullable=False)
    motivation = Column(Text, nullable=False)
    role = Column(String(200), nullable=False)
    status = Column(String(20), default='new', index=True)  # new, accepted, rejected
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    __table_args__ = (
        Index('idx_team_applications_user_status', 'user_id', 'status'),
        Index('idx_team_applications_created', 'created_at'),
    )

class ConsultationRequest(Base):
    """Модель запроса на консультацию"""
    __tablename__ = 'consultation_requests'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False, index=True)
    username = Column(String(100))
    question = Column(Text, nullable=False)
    answer = Column(Text)  # Ответ администратора
    status = Column(String(20), default='new', index=True)  # new, answered, completed
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    __table_args__ = (
        Index('idx_consultation_requests_user_status', 'user_id', 'status'),
        Index('idx_consultation_requests_created', 'created_at'),
    )

class PortfolioProject(Base):
    """Модель проекта в портфолио"""
    __tablename__ = 'portfolio_projects'
    
    id = Column(Integer, primary_key=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    details = Column(Text, nullable=False)
    cost = Column(String(100), nullable=False)
    image_url = Column(String(500))  # Устаревшее поле (совместимость)
    video_url = Column(String(500))  # Ссылка на видео проекта
    bot_url = Column(String(500))    # Ссылка на бота проекта (опционально)
    technologies = Column(String(500))  # Используемые технологии
    duration = Column(String(100))  # Длительность разработки
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    __table_args__ = (
        Index('idx_portfolio_projects_created', 'created_at'),
    )

class UserSession(Base):
    """Модель для хранения сессий пользователей"""
    __tablename__ = 'user_sessions'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False, unique=True, index=True)
    current_state = Column(String(100))
    state_data = Column(Text)  # JSON данные состояния
    last_activity = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (
        Index('idx_user_sessions_activity', 'last_activity'),
    )

class ReferralUser(Base):
    """Модель реферального пользователя"""
    __tablename__ = 'referral_users'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False, unique=True, index=True)
    username = Column(String(100))
    referral_code = Column(String(20), nullable=False, unique=True, index=True)
    referred_by = Column(Integer, ForeignKey('referral_users.user_id'), nullable=True, index=True)
    
    # Настройки выплат (ручные переводы)
    payout_method = Column(String(20), default='card')  # card, sbp, manual
    card_number = Column(String(20))  # Номер карты (маскированный)
    phone_number = Column(String(15))  # Для СБП
    full_name = Column(String(200))  # ФИО для переводов
    
    # Статистика
    total_referrals = Column(Integer, default=0)
    total_earned = Column(Float, default=0.0)
    total_paid = Column(Float, default=0.0)
    balance = Column(Float, default=0.0)
    
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Связи
    earnings = relationship("ReferralEarning", back_populates="referrer")
    payouts = relationship("ReferralPayout", back_populates="referrer")
    
    __table_args__ = (
        Index('idx_referral_users_code', 'referral_code'),
        Index('idx_referral_users_referred_by', 'referred_by'),
    )

class ReferralEarning(Base):
    """Модель начислений по реферальной программе"""
    __tablename__ = 'referral_earnings'
    
    id = Column(Integer, primary_key=True)
    referrer_id = Column(Integer, ForeignKey('referral_users.user_id'), nullable=False, index=True)
    referred_user_id = Column(Integer, nullable=False, index=True)
    order_id = Column(Integer, ForeignKey('client_orders.id'), nullable=False, index=True)
    
    # Финансовые данные
    order_amount = Column(Float, nullable=False)  # Сумма заказа
    commission_rate = Column(Float, default=0.25)  # 25%
    earned_amount = Column(Float, nullable=False)  # Начисленная сумма
    
    # Статусы: pending (ожидает оплаты), confirmed (оплачен), paid (выплачен)
    status = Column(String(20), default='pending')
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    confirmed_at = Column(DateTime(timezone=True))  # Когда подтверждена оплата
    paid_at = Column(DateTime(timezone=True))  # Когда выплачено рефералу
    
    # Связи
    referrer = relationship("ReferralUser", back_populates="earnings")
    order = relationship("ClientOrder")
    
    __table_args__ = (
        Index('idx_referral_earnings_referrer_status', 'referrer_id', 'status'),
        Index('idx_referral_earnings_created', 'created_at'),
    )

class ReferralPayout(Base):
    """Модель выплат рефералам"""
    __tablename__ = 'referral_payouts'
    
    id = Column(Integer, primary_key=True)
    referrer_id = Column(Integer, ForeignKey('referral_users.user_id'), nullable=False, index=True)
    
    # Данные выплаты
    amount = Column(Float, nullable=False)
    method = Column(String(20), nullable=False)  # card, sbp, manual
    recipient_info = Column(String(200))  # Реквизиты получателя
    
    # Статус и детали
    status = Column(String(20), default='requested')  # requested, processing, completed, failed
    admin_notes = Column(Text)  # Заметки администратора
    transaction_details = Column(Text)  # Детали перевода
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    processed_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    
    # Связи
    referrer = relationship("ReferralUser", back_populates="payouts")
    
    __table_args__ = (
        Index('idx_referral_payouts_referrer_status', 'referrer_id', 'status'),
        Index('idx_referral_payouts_created', 'created_at'),
    )

# Инициализация базы данных
engine = create_engine(config.DATABASE_URL, echo=False)
Base.metadata.create_all(engine)
# Важно: не истекать атрибуты после commit, чтобы можно было безопасно
# возвращать ORM объекты из короткоживущих сессий без DetachedInstanceError
Session = sessionmaker(bind=engine, expire_on_commit=False)