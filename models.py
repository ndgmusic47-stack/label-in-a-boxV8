from sqlalchemy import Column, Integer, String, Boolean
from sqlalchemy.orm import relationship
from database import Base


class User(Base):
    """
    User model for storing user account information.
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    is_paid_user = Column(Boolean, default=False, nullable=False)
    trial_start_date = Column(String, nullable=True)
    
    # Relationship placeholder for future one-to-many linking (User to Project)
    # projects = relationship("Project", back_populates="owner")

