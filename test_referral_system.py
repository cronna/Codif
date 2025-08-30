#!/usr/bin/env python3
"""
Test script for referral system functionality
Tests database methods, admin handlers, and integration
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.db.database import DatabaseManager
from app.db.models import *
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import tempfile

def test_database_methods():
    """Test all new database methods for referral system"""
    print("🧪 Testing database methods...")
    
    # Create temporary database for testing
    temp_db = tempfile.mktemp(suffix='.db')
    engine = create_engine(f'sqlite:///{temp_db}')
    Base.metadata.create_all(engine)
    
    # Initialize database manager with proper session
    db = DatabaseManager()
    original_engine = db.engine
    original_session = db.session
    
    db.engine = engine
    Session = sessionmaker(bind=engine)
    session = Session()
    db.session = session
    
    try:
        # Test 1: Create test users and referral user
        print("  ✓ Creating test users...")
        
        # Create referrer
        referrer = ReferralUser(
            user_id=12345,
            referral_code="TEST123",
            payout_method="card",
            payout_details="1234567890123456",
            full_name="Test Referrer"
        )
        db.session.add(referrer)
        
        # Create referred user
        referred = ReferralUser(
            user_id=67890,
            referral_code="TEST456",
            referred_by=12345
        )
        db.session.add(referred)
        
        # Create test order
        order = ClientOrder(
            user_id=67890,
            project_name="Test Project",
            project_description="Test Description",
            budget="50000",
            contact_info="test@example.com",
            status="new"
        )
        db.session.add(order)
        db.session.commit()
        
        order_id = order.id
        
        # Test 2: Set final price
        print("  ✓ Testing set_order_final_price...")
        result = db.set_order_final_price(order_id, 40000.0, "Test admin notes")
        assert result == True, "Failed to set final price"
        
        updated_order = db.get_client_order(order_id)
        assert updated_order.final_price == 40000.0, "Final price not set correctly"
        assert updated_order.status == "accepted", "Order status not updated"
        assert updated_order.admin_notes == "Test admin notes", "Admin notes not saved"
        
        # Test 3: Get accepted orders for payment
        print("  ✓ Testing get_accepted_orders_for_payment...")
        accepted_orders = db.get_accepted_orders_for_payment()
        assert len(accepted_orders) == 1, "Should have 1 accepted order"
        assert accepted_orders[0].id == order_id, "Wrong order returned"
        
        # Test 4: Confirm payment and create referral earning
        print("  ✓ Testing confirm_order_payment...")
        result = db.confirm_order_payment(order_id)
        assert result == True, "Failed to confirm payment"
        
        # Check order status updated
        paid_order = db.get_client_order(order_id)
        assert paid_order.status == "paid", "Order status not updated to paid"
        
        # Check referral earning created
        earnings = db.session.query(ReferralEarning).filter_by(order_id=order_id).all()
        assert len(earnings) == 1, "Referral earning not created"
        
        earning = earnings[0]
        assert earning.referrer_id == 12345, "Wrong referrer ID"
        assert earning.referred_user_id == 67890, "Wrong referred user ID"
        assert earning.order_amount == 40000.0, "Wrong order amount"
        assert earning.commission_rate == 0.25, "Wrong commission rate"
        assert earning.earned_amount == 10000.0, "Wrong earned amount"
        assert earning.status == "confirmed", "Earning not confirmed"
        
        # Check referrer balance updated
        updated_referrer = db.get_referral_user(12345)
        assert updated_referrer.balance == 10000.0, "Referrer balance not updated"
        assert updated_referrer.total_earned == 10000.0, "Referrer total earned not updated"
        
        # Test 5: Create payout request
        print("  ✓ Testing create_referral_payout...")
        payout_id = db.create_referral_payout(12345, 5000.0)
        assert payout_id is not None, "Failed to create payout request"
        
        payout = db.get_referral_payout(payout_id)
        assert payout.amount == 5000.0, "Wrong payout amount"
        assert payout.status == "pending", "Wrong payout status"
        
        # Check balance deducted
        updated_referrer = db.get_referral_user(12345)
        assert updated_referrer.balance == 5000.0, "Balance not deducted"
        
        # Test 6: Get pending payouts
        print("  ✓ Testing get_pending_referral_payouts...")
        pending_payouts = db.get_pending_referral_payouts()
        assert len(pending_payouts) == 1, "Should have 1 pending payout"
        assert pending_payouts[0].id == payout_id, "Wrong payout returned"
        
        # Test 7: Update payout status
        print("  ✓ Testing update_referral_payout_status...")
        result = db.update_referral_payout_status(payout_id, "processing")
        assert result == True, "Failed to update payout status"
        
        updated_payout = db.get_referral_payout(payout_id)
        assert updated_payout.status == "processing", "Payout status not updated"
        
        # Test 8: Complete payout
        result = db.update_referral_payout_status(payout_id, "completed", "Payment sent via bank transfer")
        assert result == True, "Failed to complete payout"
        
        completed_payout = db.get_referral_payout(payout_id)
        assert completed_payout.status == "completed", "Payout not completed"
        assert completed_payout.admin_notes == "Payment sent via bank transfer", "Admin notes not saved"
        
        print("✅ All database tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Database test failed: {e}")
        return False
    finally:
        db.session.close()
        os.unlink(temp_db)

def test_config_messages():
    """Test that all required config messages exist"""
    print("🧪 Testing config messages...")
    
    try:
        from config import config
        
        required_messages = [
            "admin_order_accepted",
            "admin_payment_confirmed", 
            "admin_no_accepted_orders",
            "admin_no_pending_payouts",
            "admin_payout_approved",
            "admin_payout_rejected",
            "admin_payout_completed",
            "client_order_accepted",
            "client_payment_confirmed",
            "referrer_commission_earned",
            "referrer_payout_approved",
            "referrer_payout_rejected",
            "referrer_payout_completed"
        ]
        
        for message_key in required_messages:
            assert message_key in config.MESSAGES, f"Missing message: {message_key}"
            assert len(config.MESSAGES[message_key]) > 0, f"Empty message: {message_key}"
        
        print("✅ All config messages exist!")
        return True
        
    except Exception as e:
        print(f"❌ Config test failed: {e}")
        return False

def test_imports():
    """Test that all modules import correctly"""
    print("🧪 Testing imports...")
    
    try:
        # Test core imports
        from app.db.database import DatabaseManager
        from app.db.models import ClientOrder, ReferralUser, ReferralEarning, ReferralPayout
        from app.fsm import OrderManagement, AdminMenu, AdminResponse
        from app.keyboards import admin_main_menu, admin_referral_payouts_keyboard, admin_payment_confirmations_keyboard
        from config import config
        
        print("✅ All imports successful!")
        return True
        
    except Exception as e:
        print(f"❌ Import test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 Starting referral system tests...\n")
    
    tests = [
        ("Imports", test_imports),
        ("Config Messages", test_config_messages),
        ("Database Methods", test_database_methods)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n📋 Running {test_name} test...")
        if test_func():
            passed += 1
        print()
    
    print("=" * 50)
    print(f"🎯 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Referral system is ready!")
        return True
    else:
        print("❌ Some tests failed. Please check the issues above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
