from aiogram.fsm.state import State, StatesGroup

class ClientOrder(StatesGroup):
    order_type = State()
    project_name = State()
    functionality = State()
    deadlines = State()
    budget = State()
    confirm = State()

class JoinTeam(StatesGroup):
    full_name = State()
    age = State()
    experience = State()
    stack = State()
    about = State()
    motivation = State()
    role = State()

class Portfolio(StatesGroup):
    viewing = State()
    details = State()

class Consultation(StatesGroup):
    question = State()

class AdminMenu(StatesGroup):
    main = State()
    client_orders = State()
    team_applications = State()
    portfolio_manage = State()
    consultations = State()
    referral_payouts = State()
    payment_confirmations = State()

class PortfolioManage(StatesGroup):
    add_title = State()
    add_description = State()
    add_details = State()
    add_cost = State()
    add_technologies = State()
    add_duration = State()
    add_video = State()
    add_bot_url = State()
    edit_project = State()
    edit_field = State()
    delete_confirm = State()

class AdminResponse(StatesGroup):
    client_order = State()
    team_application = State()
    consultation = State()
    set_final_price = State()
    payout_notes = State()

class ReferralSystem(StatesGroup):
    main = State()
    wallet_method = State()
    enter_wallet = State()
    setup_wallet = State()

class OrderManagement(StatesGroup):
    set_price = State()
    add_notes = State()
    confirm_payment = State()