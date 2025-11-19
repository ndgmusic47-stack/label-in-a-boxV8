"""
Unit tests for UserRepository authentication operations
"""
import pytest
from crud.user import UserRepository
from auth_utils import hash_password, verify_password


@pytest.mark.asyncio
async def test_create_and_get_user(test_db):
    """
    Test creating a new user and retrieving it by email.
    
    This test verifies:
    - User creation via UserRepository.create_user
    - User retrieval via UserRepository.get_user_by_email
    - Email matching and user object existence
    """
    # Create UserRepository instance
    user_repo = UserRepository(test_db)
    
    # Create a new user
    test_email = "test@example.com"
    test_password = "test_password_123"
    hashed_pwd = hash_password(test_password)
    
    user_data = {
        "email": test_email,
        "hashed_password": hashed_pwd,
        "is_active": True,
        "is_paid_user": False
    }
    
    created_user = await user_repo.create_user(user_data)
    
    # Verify user was created with correct attributes
    assert created_user is not None
    assert created_user.email == test_email.lower()  # Email should be lowercased
    assert created_user.hashed_password == hashed_pwd
    assert created_user.is_active is True
    assert created_user.is_paid_user is False
    
    # Commit to ensure user is persisted
    await test_db.commit()
    
    # Retrieve the user by email
    retrieved_user = await user_repo.get_user_by_email(test_email)
    
    # Verify user was retrieved correctly
    assert retrieved_user is not None
    assert retrieved_user.email == test_email.lower()
    assert retrieved_user.id == created_user.id  # Same user


@pytest.mark.asyncio
async def test_login_verification(test_db):
    """
    Test password verification for login.
    
    This test verifies:
    - User creation with a known password
    - Password hashing and storage
    - Password verification using verify_password
    """
    # Create UserRepository instance
    user_repo = UserRepository(test_db)
    
    # Create a user with a known password
    test_email = "login_test@example.com"
    test_password = "secure_password_456"
    hashed_pwd = hash_password(test_password)
    
    user_data = {
        "email": test_email,
        "hashed_password": hashed_pwd,
        "is_active": True
    }
    
    created_user = await user_repo.create_user(user_data)
    await test_db.commit()
    
    # Retrieve the user from the database
    retrieved_user = await user_repo.get_user_by_email(test_email)
    
    # Verify user exists
    assert retrieved_user is not None
    assert retrieved_user.email == test_email.lower()
    
    # Verify password using verify_password function
    assert verify_password(test_password, retrieved_user.hashed_password) is True
    
    # Verify that wrong password fails
    assert verify_password("wrong_password", retrieved_user.hashed_password) is False

