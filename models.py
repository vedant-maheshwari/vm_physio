from sqlalchemy.orm import mapped_column, relationship, Mapped
from database import Base
from sqlalchemy import String, ForeignKey, DateTime, Text, Integer, Float, Enum
from typing import List
from datetime import datetime
import enum

class PermissionLevel(str, enum.Enum):
    VIEW = "VIEW"
    EDIT = "EDIT"

class Users(Base):
    __tablename__ = 'users'

    id : Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name : Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    email : Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    hashed_password : Mapped[str] = mapped_column(String(100), nullable=False)
    role : Mapped[str] = mapped_column(String(20), default='physician')

    # Relationships
    owned_patients : Mapped[List["Patients"]] = relationship(
        back_populates = 'owner',
        cascade = "all, delete-orphan",
        foreign_keys = "Patients.physician_id"
    )

    notes : Mapped[List['Notes']] = relationship(
        back_populates = 'author'
    )

    vitals : Mapped[List['Vitals']] = relationship(
        back_populates = 'author'
    )
    
    # Shared access received
    shared_patients : Mapped[List['SharedAccess']] = relationship(
        back_populates='user',
        foreign_keys='SharedAccess.user_id'
    )

class Patients(Base):
    __tablename__ = 'patients'

    id : Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name : Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    phone_number : Mapped[str] = mapped_column(String(15), nullable=False, index=True)
    membership_price : Mapped[float] = mapped_column(Float, nullable=False)
    
    # This remains "physician_id" for legacy compatibility or we can rename to owner_id
    # Keeping physician_id to minimize refactor, but pointing to users.id
    physician_id : Mapped[int] = mapped_column(ForeignKey('users.id', ondelete="CASCADE"))

    owner : Mapped["Users"] = relationship(
        back_populates = 'owned_patients',
        foreign_keys=[physician_id]
    )
    
    notes : Mapped[List["Notes"]] = relationship(
        back_populates="patient"
    )
    
    vitals : Mapped[List["Vitals"]] = relationship(
        back_populates="patient"
    )
    
    shared_with : Mapped[List['SharedAccess']] = relationship(
        back_populates='patient',
        cascade="all, delete-orphan"
    )

class SharedAccess(Base):
    __tablename__ = 'shared_access'
    
    id : Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    patient_id : Mapped[int] = mapped_column(ForeignKey('patients.id', ondelete="CASCADE"))
    user_id : Mapped[int] = mapped_column(ForeignKey('users.id', ondelete="CASCADE")) # User who received access
    granted_by : Mapped[int] = mapped_column(ForeignKey('users.id')) # User who granted access
    
    permission : Mapped[PermissionLevel] = mapped_column(Enum(PermissionLevel), default=PermissionLevel.VIEW)
    created_at : Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Relationships
    patient : Mapped['Patients'] = relationship(back_populates='shared_with')
    user : Mapped['Users'] = relationship(foreign_keys=[user_id], back_populates='shared_patients')
    granter : Mapped['Users'] = relationship(foreign_keys=[granted_by])

class Notes(Base):
    __tablename__ = 'notes'

    id : Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    physician_id : Mapped[int] = mapped_column(ForeignKey('users.id', ondelete="CASCADE")) # The author
    patient_id : Mapped[int] = mapped_column(ForeignKey('patients.id', ondelete="CASCADE"))
    
    # SOAP Format Fields
    chief_complaint : Mapped[str] = mapped_column(String(500), nullable=True)  # CC
    subjective : Mapped[str] = mapped_column(Text, nullable=True)  # S
    objective : Mapped[str] = mapped_column(Text, nullable=True)  # O
    assessment : Mapped[str] = mapped_column(Text, nullable=True)  # A
    plan : Mapped[str] = mapped_column(Text, nullable=True)  # P
    
    # Raw transcription from voice
    raw_notes : Mapped[str] = mapped_column(Text, nullable=True)
    
    # Timestamp
    created_at : Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    author : Mapped['Users'] = relationship(
        back_populates = 'notes'
    )
    patient : Mapped['Patients'] = relationship(
        back_populates = 'notes'
    )

class Vitals(Base):
    __tablename__ = 'vitals'

    id : Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    physician_id : Mapped[int] = mapped_column(ForeignKey('users.id', ondelete="CASCADE")) # The author
    patient_id : Mapped[int] = mapped_column(ForeignKey('patients.id', ondelete="CASCADE"))
    
    # Vital Signs
    systolic_bp : Mapped[int] = mapped_column(Integer, nullable=True)  # Systolic Blood Pressure
    diastolic_bp : Mapped[int] = mapped_column(Integer, nullable=True)  # Diastolic Blood Pressure
    heart_rate : Mapped[int] = mapped_column(Integer, nullable=True)  # Heart Rate (bpm)
    temperature : Mapped[float] = mapped_column(Float, nullable=True)  # Temperature (Fahrenheit)
    spo2 : Mapped[int] = mapped_column(Integer, nullable=True)  # Oxygen Saturation (%)
    
    # Timestamp
    created_at : Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    author : Mapped['Users'] = relationship(
        back_populates = 'vitals'
    )
    patient : Mapped['Patients'] = relationship(
        back_populates = 'vitals'
    )
