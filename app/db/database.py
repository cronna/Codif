from typing import List, Optional, Dict, Any
from contextlib import contextmanager
from sqlalchemy.orm import Session as DBSession
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import func, case
import logging
import json

from app.db.models import (
    Session, ClientOrder, TeamApplication, ConsultationRequest,
    PortfolioProject, UserSession, ReferralUser, ReferralEarning, ReferralPayout, engine
)
from config import config

logger = logging.getLogger(__name__)

def _migrate_schema_if_needed():
    """Простая миграция: добавление отсутствующих колонок в SQLite."""
    try:
        if engine.dialect.name != 'sqlite':
            return
        with engine.connect() as conn:
            # Проверяем наличие столбцов video_url и bot_url в portfolio_projects
            res = conn.exec_driver_sql("PRAGMA table_info('portfolio_projects')").fetchall()
            existing_cols = {row[1] for row in res}  # row[1] = name

            if 'video_url' not in existing_cols:
                conn.exec_driver_sql("ALTER TABLE portfolio_projects ADD COLUMN video_url VARCHAR(500)")
            if 'bot_url' not in existing_cols:
                conn.exec_driver_sql("ALTER TABLE portfolio_projects ADD COLUMN bot_url VARCHAR(500)")
            
            # Проверяем наличие столбца order_type в client_orders
            res = conn.exec_driver_sql("PRAGMA table_info('client_orders')").fetchall()
            existing_cols = {row[1] for row in res}  # row[1] = name
            
            if 'order_type' not in existing_cols:
                conn.exec_driver_sql("ALTER TABLE client_orders ADD COLUMN order_type VARCHAR(20) DEFAULT 'bot'")
    except Exception as e:
        logger.error(f"Schema migration failed: {e}")

@contextmanager
def get_db_session():
    """Контекстный менеджер для работы с сессией БД"""
    session = Session()
    try:
        yield session
        session.commit()
    except SQLAlchemyError as e:
        session.rollback()
        logger.error(f"Database error: {e}")
        raise
    except Exception as e:
        session.rollback()
        logger.error(f"Unexpected error: {e}")
        raise
    finally:
        session.close()

class DatabaseOptimizer:
    """Класс для оптимизации работы с базой данных"""
    
    @staticmethod
    def bulk_update_status(model_class, ids: List[int], status: str, session: DBSession = None):
        """Массовое обновление статуса записей"""
        close_session = session is None
        if session is None:
            session = Session()
        
        try:
            session.query(model_class).filter(
                model_class.id.in_(ids)
            ).update({
                'status': status,
                'updated_at': func.now()
            }, synchronize_session=False)
            
            if close_session:
                session.commit()
            return True
        except Exception as e:
            if close_session:
                session.rollback()
            logger.error(f"Bulk update error: {e}")
            return False
        finally:
            if close_session:
                session.close()
    
    @staticmethod
    def get_user_stats_optimized(user_id: int):
        """Оптимизированное получение статистики пользователя"""
        try:
            with get_db_session() as session:
                # Получаем статистику заказов
                orders_stats = session.query(
                    func.count(ClientOrder.id).label('total_orders'),
                    func.count(case([(ClientOrder.status == 'completed', 1)])).label('completed_orders')
                ).filter(ClientOrder.user_id == user_id).first()
                
                # Получаем количество заявок в команду
                team_apps = session.query(func.count(TeamApplication.id)).filter(
                    TeamApplication.user_id == user_id
                ).scalar() or 0
                
                # Получаем количество консультаций
                consultations = session.query(func.count(ConsultationRequest.id)).filter(
                    ConsultationRequest.user_id == user_id
                ).scalar() or 0
                
                return {
                    'total_orders': orders_stats.total_orders or 0,
                    'completed_orders': orders_stats.completed_orders or 0,
                    'team_applications': team_apps,
                    'consultations': consultations
                }
        except Exception as e:
            logger.error(f"Error getting user stats: {e}")
            return {'total_orders': 0, 'completed_orders': 0, 'team_applications': 0, 'consultations': 0}

class DatabaseManager:
    """Менеджер для работы с базой данных"""
    
    @staticmethod
    def create_client_order(data: Dict[str, Any]) -> Optional[ClientOrder]:
        """Создание заявки на разработку"""
        try:
            with get_db_session() as session:
                order = ClientOrder(**data)
                session.add(order)
                session.flush()  # Получаем ID
                return order
        except Exception as e:
            logger.error(f"Error creating client order: {e}")
            return None

    @staticmethod
    def get_client_orders(status: Optional[str] = None, limit: int = 50) -> List[ClientOrder]:
        """Получение заявок на разработку"""
        try:
            with get_db_session() as session:
                query = session.query(ClientOrder).order_by(ClientOrder.created_at.desc())
                if status:
                    query = query.filter(ClientOrder.status == status)
                return query.limit(limit).all()
        except Exception as e:
            logger.error(f"Error getting client orders: {e}")
            return []

    @staticmethod
    def get_client_order(order_id: int) -> Optional[ClientOrder]:
        """Получение конкретной заявки"""
        try:
            with get_db_session() as session:
                return session.query(ClientOrder).filter(ClientOrder.id == order_id).first()
        except Exception as e:
            logger.error(f"Error getting client order {order_id}: {e}")
            return None

    @staticmethod
    def update_client_order_status(order_id: int, status: str) -> bool:
        """Обновление статуса заявки"""
        try:
            with get_db_session() as session:
                order = session.query(ClientOrder).filter(ClientOrder.id == order_id).first()
                if order:
                    order.status = status
                    return True
                return False
        except Exception as e:
            logger.error(f"Error updating client order status: {e}")
            return False

    @staticmethod
    def update_client_order(order_id: int, data: Dict[str, Any]) -> bool:
        """Обновление данных заявки"""
        try:
            with get_db_session() as session:
                order = session.query(ClientOrder).filter(ClientOrder.id == order_id).first()
                if order:
                    for key, value in data.items():
                        setattr(order, key, value)
                    return True
                return False
        except Exception as e:
            logger.error(f"Error updating client order: {e}")
            return False

    @staticmethod
    def set_order_final_price(order_id: int, final_price: float, admin_notes: str = None) -> bool:
        """Установка окончательной цены заказа администратором"""
        try:
            with get_db_session() as session:
                order = session.query(ClientOrder).filter(ClientOrder.id == order_id).first()
                if order:
                    order.final_price = final_price
                    order.status = 'accepted'
                    if admin_notes:
                        order.admin_notes = admin_notes
                    return True
                return False
        except Exception as e:
            logger.error(f"Error setting order final price: {e}")
            return False

    @staticmethod
    def confirm_order_payment(order_id: int) -> bool:
        """Подтверждение оплаты заказа и начисление реферальной комиссии"""
        try:
            with get_db_session() as session:
                order = session.query(ClientOrder).filter(ClientOrder.id == order_id).first()
                if not order or order.status != 'accepted':
                    return False
                
                # Обновляем статус заказа
                order.status = 'paid'
                
                # Проверяем, есть ли реферер у пользователя
                referral_user = session.query(ReferralUser).filter_by(user_id=order.user_id).first()
                if referral_user and referral_user.referred_by:
                    # Создаем начисление рефералу
                    if order.final_price:
                        commission_rate = 0.25  # 25%
                        earned_amount = order.final_price * commission_rate
                        
                        earning = ReferralEarning(
                            referrer_id=referral_user.referred_by,
                            referred_user_id=order.user_id,
                            order_id=order.id,
                            order_amount=order.final_price,
                            commission_rate=commission_rate,
                            earned_amount=earned_amount,
                            status='confirmed',
                            confirmed_at=func.now()
                        )
                        session.add(earning)
                        
                        # Обновляем баланс реферера
                        referrer = session.query(ReferralUser).filter_by(user_id=referral_user.referred_by).first()
                        if referrer:
                            referrer.total_earned += earned_amount
                            referrer.balance += earned_amount
                
                return True
        except Exception as e:
            logger.error(f"Error confirming order payment: {e}")
            return False

    @staticmethod
    def delete_client_order(order_id: int) -> bool:
        """Удаление заявки"""
        try:
            with get_db_session() as session:
                order = session.query(ClientOrder).filter(ClientOrder.id == order_id).first()
                if order:
                    session.delete(order)
                    return True
                return False
        except Exception as e:
            logger.error(f"Error deleting client order: {e}")
            return False

    # Team Application methods
    @staticmethod
    def create_team_application(data: Dict[str, Any]) -> Optional[TeamApplication]:
        """Создание заявки в команду"""
        try:
            with get_db_session() as session:
                application = TeamApplication(**data)
                session.add(application)
                session.flush()
                return application
        except Exception as e:
            logger.error(f"Error creating team application: {e}")
            return None

    @staticmethod
    def get_team_applications(status: Optional[str] = None, limit: int = 50) -> List[TeamApplication]:
        """Получение заявок в команду"""
        try:
            with get_db_session() as session:
                query = session.query(TeamApplication).order_by(TeamApplication.created_at.desc())
                if status:
                    query = query.filter(TeamApplication.status == status)
                return query.limit(limit).all()
        except Exception as e:
            logger.error(f"Error getting team applications: {e}")
            return []

    @staticmethod
    def get_team_application(app_id: int) -> Optional[TeamApplication]:
        """Получение конкретной заявки в команду"""
        try:
            with get_db_session() as session:
                return session.query(TeamApplication).filter(TeamApplication.id == app_id).first()
        except Exception as e:
            logger.error(f"Error getting team application {app_id}: {e}")
            return None

    @staticmethod
    def update_team_application_status(app_id: int, status: str) -> bool:
        """Обновление статуса заявки в команду"""
        try:
            with get_db_session() as session:
                app = session.query(TeamApplication).filter(TeamApplication.id == app_id).first()
                if app:
                    app.status = status
                    return True
                return False
        except Exception as e:
            logger.error(f"Error updating team application status: {e}")
            return False

    @staticmethod
    def delete_team_application(app_id: int) -> bool:
        """Удаление заявки в команду"""
        try:
            with get_db_session() as session:
                app = session.query(TeamApplication).filter(TeamApplication.id == app_id).first()
                if app:
                    session.delete(app)
                    return True
                return False
        except Exception as e:
            logger.error(f"Error deleting team application: {e}")
            return False

    # Consultation Request methods
    @staticmethod
    def create_consultation_request(data: Dict[str, Any]) -> Optional[ConsultationRequest]:
        """Создание запроса на консультацию"""
        try:
            with get_db_session() as session:
                request = ConsultationRequest(**data)
                session.add(request)
                session.flush()
                return request
        except Exception as e:
            logger.error(f"Error creating consultation request: {e}")
            return None

    @staticmethod
    def get_consultation_requests(status: Optional[str] = None, limit: int = 50) -> List[ConsultationRequest]:
        """Получение запросов на консультацию"""
        try:
            with get_db_session() as session:
                query = session.query(ConsultationRequest).order_by(ConsultationRequest.created_at.desc())
                if status:
                    query = query.filter(ConsultationRequest.status == status)
                return query.limit(limit).all()
        except Exception as e:
            logger.error(f"Error getting consultation requests: {e}")
            return []

    @staticmethod
    def get_consultation_request(req_id: int) -> Optional[ConsultationRequest]:
        """Получение конкретного запроса на консультацию"""
        try:
            with get_db_session() as session:
                return session.query(ConsultationRequest).filter(ConsultationRequest.id == req_id).first()
        except Exception as e:
            logger.error(f"Error getting consultation request {req_id}: {e}")
            return None

    @staticmethod
    def update_consultation_request(req_id: int, data: Dict[str, Any]) -> bool:
        """Обновление запроса на консультацию"""
        try:
            with get_db_session() as session:
                req = session.query(ConsultationRequest).filter(ConsultationRequest.id == req_id).first()
                if req:
                    for key, value in data.items():
                        setattr(req, key, value)
                    return True
                return False
        except Exception as e:
            logger.error(f"Error updating consultation request: {e}")
            return False

    @staticmethod
    def delete_consultation_request(req_id: int) -> bool:
        """Удаление запроса на консультацию"""
        try:
            with get_db_session() as session:
                req = session.query(ConsultationRequest).filter(ConsultationRequest.id == req_id).first()
                if req:
                    session.delete(req)
                    return True
                return False
        except Exception as e:
            logger.error(f"Error deleting consultation request: {e}")
            return False

    # Portfolio methods
    @staticmethod
    def create_portfolio_project(data: Dict[str, Any]) -> Optional[PortfolioProject]:
        """Создание проекта в портфолио"""
        try:
            _migrate_schema_if_needed()
            with get_db_session() as session:
                project = PortfolioProject(**data)
                session.add(project)
                session.flush()
                return project
        except Exception as e:
            logger.error(f"Error creating portfolio project: {e}")
            return None

    @staticmethod
    def get_portfolio_projects(limit: int = 50) -> List[PortfolioProject]:
        """Получение проектов портфолио"""
        try:
            with get_db_session() as session:
                return session.query(PortfolioProject).order_by(PortfolioProject.created_at.desc()).limit(limit).all()
        except Exception as e:
            logger.error(f"Error getting portfolio projects: {e}")
            return []

    @staticmethod
    def get_portfolio_project(project_id: int) -> Optional[PortfolioProject]:
        """Получение конкретного проекта"""
        try:
            with get_db_session() as session:
                return session.query(PortfolioProject).filter(PortfolioProject.id == project_id).first()
        except Exception as e:
            logger.error(f"Error getting portfolio project {project_id}: {e}")
            return None

    @staticmethod
    def update_portfolio_project(project_id: int, data: Dict[str, Any]) -> Optional[PortfolioProject]:
        """Обновление проекта в портфолио"""
        try:
            _migrate_schema_if_needed()
            with get_db_session() as session:
                project = session.query(PortfolioProject).filter(PortfolioProject.id == project_id).first()
                if project:
                    for key, value in data.items():
                        setattr(project, key, value)
                    return project
                return None
        except Exception as e:
            logger.error(f"Error updating portfolio project: {e}")
            return None

    @staticmethod
    def delete_portfolio_project(project_id: int) -> bool:
        """Удаление проекта из портфолио"""
        try:
            with get_db_session() as session:
                project = session.query(PortfolioProject).filter(PortfolioProject.id == project_id).first()
                if project:
                    session.delete(project)
                    return True
                return False
        except Exception as e:
            logger.error(f"Error deleting portfolio project: {e}")
            return False

    # User Session methods
    @staticmethod
    def save_user_session(user_id: int, state: str, data: Dict[str, Any]) -> bool:
        """Сохранение сессии пользователя"""
        try:
            with get_db_session() as session:
                user_session = session.query(UserSession).filter(UserSession.user_id == user_id).first()
                if user_session:
                    user_session.current_state = state
                    user_session.state_data = json.dumps(data)
                    user_session.last_activity = func.now()
                else:
                    user_session = UserSession(
                        user_id=user_id,
                        current_state=state,
                        state_data=json.dumps(data)
                    )
                    session.add(user_session)
                return True
        except Exception as e:
            logger.error(f"Error saving user session: {e}")
            return False

    @staticmethod
    def get_user_session(user_id: int) -> Optional[Dict[str, Any]]:
        """Получение сессии пользователя"""
        try:
            with get_db_session() as session:
                user_session = session.query(UserSession).filter(UserSession.user_id == user_id).first()
                if user_session:
                    return {
                        'state': user_session.current_state,
                        'data': json.loads(user_session.state_data) if user_session.state_data else {}
                    }
                return None
        except Exception as e:
            logger.error(f"Error getting user session: {e}")
            return None

    @staticmethod
    def delete_user_session(user_id: int) -> bool:
        """Удаление сессии пользователя"""
        try:
            with get_db_session() as session:
                user_session = session.query(UserSession).filter(UserSession.user_id == user_id).first()
                if user_session:
                    session.delete(user_session)
                    return True
                return False
        except Exception as e:
            logger.error(f"Error deleting user session: {e}")
            return False

    # Реферальная система
    def create_referral_user(self, user_id, username, referral_code, referred_by=None):
        """Создание реферального пользователя"""
        try:
            session = Session()
            
            # Проверяем, существует ли уже пользователь
            existing = session.query(ReferralUser).filter_by(user_id=user_id).first()
            if existing:
                return existing
            
            referral_user = ReferralUser(
                user_id=user_id,
                username=username,
                referral_code=referral_code,
                referred_by=referred_by
            )
            
            session.add(referral_user)
            session.commit()
            
            logger.info(f"Referral user created: {user_id}")
            return referral_user
            
        except Exception as e:
            logger.error(f"Error creating referral user: {e}")
            session.rollback()
            return None
        finally:
            session.close()

    def get_referral_user(self, user_id):
        """Получение реферального пользователя"""
        try:
            session = Session()
            return session.query(ReferralUser).filter_by(user_id=user_id).first()
        except Exception as e:
            logger.error(f"Error getting referral user: {e}")
            return None
        finally:
            session.close()

    def get_referral_user_by_code(self, referral_code):
        """Получение реферального пользователя по коду"""
        try:
            session = Session()
            return session.query(ReferralUser).filter_by(referral_code=referral_code).first()
        except Exception as e:
            logger.error(f"Error getting referral user by code: {e}")
            return None
        finally:
            session.close()

    def update_referral_user_payout_info(self, user_id, method, card_number=None, phone_number=None, full_name=None):
        """Обновление данных для выплат"""
        try:
            session = Session()
            referral_user = session.query(ReferralUser).filter_by(user_id=user_id).first()
            
            if referral_user:
                referral_user.payout_method = method
                referral_user.card_number = card_number
                referral_user.phone_number = phone_number
                referral_user.full_name = full_name
                
                session.commit()
                return True
            return False
            
        except Exception as e:
            logger.error(f"Error updating referral user payout info: {e}")
            session.rollback()
            return False
        finally:
            session.close()

    def create_referral_earning(self, referrer_id, referred_user_id, order_id, order_amount):
        """Создание начисления по реферальной программе"""
        try:
            session = Session()
            
            commission_rate = 0.25  # 25%
            earned_amount = order_amount * commission_rate
            
            earning = ReferralEarning(
                referrer_id=referrer_id,
                referred_user_id=referred_user_id,
                order_id=order_id,
                order_amount=order_amount,
                commission_rate=commission_rate,
                earned_amount=earned_amount
            )
            
            session.add(earning)
            session.commit()
            
            logger.info(f"Referral earning created: {referrer_id} earned {earned_amount}")
            return earning
            
        except Exception as e:
            logger.error(f"Error creating referral earning: {e}")
            session.rollback()
            return None
        finally:
            session.close()

    def confirm_referral_earning(self, earning_id):
        """Подтверждение оплаты заказа и начисление рефералу"""
        try:
            session = Session()
            
            earning = session.query(ReferralEarning).filter_by(id=earning_id).first()
            if not earning:
                return False
            
            earning.status = 'confirmed'
            earning.confirmed_at = func.now()
            
            # Обновляем баланс реферера
            referrer = session.query(ReferralUser).filter_by(user_id=earning.referrer_id).first()
            if referrer:
                referrer.total_earned += earning.earned_amount
                referrer.balance += earning.earned_amount
            
            session.commit()
            return True
            
        except Exception as e:
            logger.error(f"Error confirming referral earning: {e}")
            session.rollback()
            return False
        finally:
            session.close()

    def get_referral_earnings(self, referrer_id, status=None):
        """Получение начислений реферера"""
        try:
            session = Session()
            query = session.query(ReferralEarning).filter_by(referrer_id=referrer_id)
            
            if status:
                query = query.filter_by(status=status)
            
            return query.order_by(ReferralEarning.created_at.desc()).all()
            
        except Exception as e:
            logger.error(f"Error getting referral earnings: {e}")
            return []
        finally:
            session.close()

    def get_referral_stats(self, user_id):
        """Получение статистики реферера"""
        try:
            session = Session()
            
            referral_user = session.query(ReferralUser).filter_by(user_id=user_id).first()
            if not referral_user:
                return None
            
            # Подсчитываем количество рефералов
            referrals_count = session.query(ReferralUser).filter_by(referred_by=user_id).count()
            
            # Обновляем счетчик если нужно
            if referral_user.total_referrals != referrals_count:
                referral_user.total_referrals = referrals_count
                session.commit()
            
            return {
                'referral_code': referral_user.referral_code,
                'total_referrals': referrals_count,
                'total_earned': referral_user.total_earned,
                'balance': referral_user.balance,
                'total_paid': referral_user.total_paid,
                'payout_method': referral_user.payout_method,
                'card_number': referral_user.card_number,
                'phone_number': referral_user.phone_number,
                'full_name': referral_user.full_name
            }
            
        except Exception as e:
            logger.error(f"Error getting referral stats: {e}")
            return None
        finally:
            session.close()

    def create_referral_payout_request(self, referrer_id, amount, method, recipient_info):
        """Создание запроса на выплату"""
        try:
            session = Session()
            
            # Проверяем баланс
            referrer = session.query(ReferralUser).filter_by(user_id=referrer_id).first()
            if not referrer or referrer.balance < amount:
                return None
            
            payout = ReferralPayout(
                referrer_id=referrer_id,
                amount=amount,
                method=method,
                recipient_info=recipient_info
            )
            
            session.add(payout)
            session.commit()
            
            logger.info(f"Referral payout request created: {referrer_id} requested {amount}")
            return payout
            
        except Exception as e:
            logger.error(f"Error creating referral payout request: {e}")
            session.rollback()
            return None
        finally:
            session.close()

    def complete_referral_payout(self, payout_id, transaction_details=None):
        """Завершение выплаты рефералу"""
        try:
            session = Session()
            
            payout = session.query(ReferralPayout).filter_by(id=payout_id).first()
            if not payout:
                return False
            
            payout.status = 'completed'
            payout.completed_at = func.now()
            if transaction_details:
                payout.transaction_details = transaction_details
            
            # Обновляем баланс и статистику реферера
            referrer = session.query(ReferralUser).filter_by(user_id=payout.referrer_id).first()
            if referrer:
                referrer.balance -= payout.amount
                referrer.total_paid += payout.amount
            
            # Обновляем статус связанных начислений
            earnings_to_update = session.query(ReferralEarning).filter_by(
                referrer_id=payout.referrer_id,
                status='confirmed'
            ).limit(int(payout.amount / 0.25)).all()
            
            for earning in earnings_to_update:
                earning.status = 'paid'
                earning.paid_at = func.now()
            
            session.commit()
            return True
            
        except Exception as e:
            logger.error(f"Error completing referral payout: {e}")
            session.rollback()
            return False
        finally:
            session.close()

    def get_pending_payouts(self):
        """Получение ожидающих выплат для админки"""
        try:
            session = Session()
            return session.query(ReferralPayout).filter_by(status='requested').order_by(ReferralPayout.created_at.asc()).all()
        except Exception as e:
            logger.error(f"Error getting pending payouts: {e}")
            return []
        finally:
            session.close()

    def get_accepted_orders_for_payment(self):
        """Получение принятых заказов для подтверждения оплаты"""
        try:
            session = Session()
            return session.query(ClientOrder).filter_by(status='accepted').order_by(ClientOrder.created_at.asc()).all()
        except Exception as e:
            logger.error(f"Error getting accepted orders: {e}")
            return []
        finally:
            session.close()

    def get_referral_payout(self, payout_id):
        """Получение конкретной выплаты"""
        try:
            session = Session()
            return session.query(ReferralPayout).filter_by(id=payout_id).first()
        except Exception as e:
            logger.error(f"Error getting referral payout: {e}")
            return None
        finally:
            session.close()

    def update_referral_payout_status(self, payout_id, status, admin_notes=None):
        """Обновление статуса выплаты"""
        try:
            session = Session()
            payout = session.query(ReferralPayout).filter_by(id=payout_id).first()
            if payout:
                payout.status = status
                if admin_notes:
                    payout.admin_notes = admin_notes
                if status == 'processing':
                    payout.processed_at = func.now()
                elif status == 'completed':
                    payout.completed_at = func.now()
                session.commit()
                return True
            return False
        except Exception as e:
            logger.error(f"Error updating payout status: {e}")
            session.rollback()
            return False
        finally:
            session.close()

    def get_pending_referral_earnings(self):
        """Получение ожидающих подтверждения начислений"""
        try:
            session = Session()
            return session.query(ReferralEarning).filter_by(status='pending').order_by(ReferralEarning.created_at.asc()).all()
        except Exception as e:
            logger.error(f"Error getting pending referral earnings: {e}")
            return []
        finally:
            session.close()

    def get_pending_referral_payouts(self):
        """Get all pending referral payouts"""
        try:
            session = Session()
            return session.query(ReferralPayout).filter_by(status='pending').order_by(ReferralPayout.created_at.asc()).all()
        except Exception as e:
            logger.error(f"Error getting pending referral payouts: {e}")
            return []
        finally:
            session.close()

    def create_referral_payout(self, referrer_id: int, amount: float) -> int:
        """Create a new referral payout request"""
        try:
            session = Session()
            
            # Get referrer info
            referrer = session.query(ReferralUser).filter_by(user_id=referrer_id).first()
            if not referrer or referrer.balance < amount:
                return None
            
            # Create payout request
            payout = ReferralPayout(
                referrer_id=referrer_id,
                amount=amount,
                method=referrer.payout_method,
                details=referrer.payout_details,
                status='pending'
            )
            session.add(payout)
            
            # Deduct from balance
            referrer.balance -= amount
            
            session.commit()
            return payout.id
            
        except Exception as e:
            logger.error(f"Error creating referral payout: {e}")
            session.rollback()
            return None
        finally:
            session.close()

# Миграция схемы при запуске
_migrate_schema_if_needed()

# Создаем экземпляр менеджера БД
db = DatabaseManager()

# Для обратной совместимости
def create_client_order(session, data):
    return db.create_client_order(data)

def get_client_orders(session, status=None):
    return db.get_client_orders(status)

def get_client_order(session, order_id):
    return db.get_client_order(order_id)

def update_client_order_status(session, order_id, status):
    return db.update_client_order_status(order_id, status)

def delete_client_order(session, order_id):
    return db.delete_client_order(order_id)

def create_team_application(session, data):
    return db.create_team_application(data)

def get_team_applications(session, status=None):
    return db.get_team_applications(status)

def get_team_application(session, app_id):
    return db.get_team_application(app_id)

def update_team_application_status(session, app_id, status):
    return db.update_team_application_status(app_id, status)

def delete_team_application(session, app_id):
    return db.delete_team_application(app_id)

def create_consultation_request(session, data):
    return db.create_consultation_request(data)

def get_consultation_requests(session, status=None):
    return db.get_consultation_requests(status)

def get_consultation_request(session, req_id):
    return db.get_consultation_request(req_id)

def update_consultation_request_status(session, req_id, status):
    return db.update_consultation_request(req_id, {'status': status})

def delete_consultation_request(session, req_id):
    return db.delete_consultation_request(req_id)

def create_portfolio_project(session, data):
    return db.create_portfolio_project(data)

def get_portfolio_projects(session):
    return db.get_portfolio_projects()

def get_portfolio_project(session, project_id):
    return db.get_portfolio_project(project_id)

def update_portfolio_project(session, project_id, data):
    return db.update_portfolio_project(project_id, data)

def delete_portfolio_project(session, project_id):
    return db.delete_portfolio_project(project_id)