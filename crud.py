from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, desc
from datetime import datetime
import models, schemas
from typing import List, Optional

def register_user(user : schemas.RegisterUser, db : Session):
    new_user = models.Users(
        name = user.name,
        email = user.email,
        hashed_password = user.password,
        role = user.role
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

def register_patient(patient : schemas.RegisterPatient, db : Session):
    user = models.Patients(
        name = patient.name,
        phone_number = patient.phone_number,
        membership_price = patient.membership_price,
        physician_id = patient.physician_id # This represents the owner
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

def check_user_exists(email, db : Session):
    if db.query(models.Users).filter(models.Users.email == email).first():
        return True
    else: return False

def get_user_by_email(email: str, db: Session):
    return db.query(models.Users).filter(models.Users.email == email).first()

def check_patient_exists(phone_number, db : Session):
    if db.query(models.Patients).filter(models.Patients.phone_number == phone_number).first():
        return True
    else: return False

def login_user(email : str, password : str, db : Session):
    user = db.query(models.Users).filter(models.Users.email == email).first()
    if user and user.hashed_password == password:
        return user
    return None

# Patient Management
def get_user_patients(user_id : int, db : Session) -> List[models.Patients]:
    """Get all patients assigned to OR shared with a user"""
    # Owned patients
    owned = db.query(models.Patients).filter(
        models.Patients.physician_id == user_id
    ).all()
    
    # Shared patients
    shared_records = db.query(models.SharedAccess).filter(
        models.SharedAccess.user_id == user_id
    ).options(joinedload(models.SharedAccess.patient)).all()
    
    shared_patients = [record.patient for record in shared_records]
    
    # Combine and deduplicate (though they shouldn't overlap if logic is correct)
    all_patients = list({p.id: p for p in (owned + shared_patients)}.values())
    return all_patients

def search_patients(user_id : int, query : str, db : Session) -> List[models.Patients]:
    """Search patients by name or phone number (owned or shared)"""
    # This is a bit more complex with sharing. simpler to get all and filter in python if list is small,
    # or write a complex query. For MVP, fetch all associated and filter.
    all_patients = get_user_patients(user_id, db)
    
    query = query.lower()
    return [
        p for p in all_patients 
        if query in p.name.lower() or query in p.phone_number.lower()
    ]

def get_patient_by_id(patient_id : int, db : Session) -> Optional[models.Patients]:
    """Get patient by ID"""
    return db.query(models.Patients).filter(models.Patients.id == patient_id).first()

# Sharing Management
def grant_access(patient_id: int, user_id: int, granted_by: int, permission: str, db: Session):
    """Grant access to a patient for a user"""
    # Check if access already exists
    existing = db.query(models.SharedAccess).filter(
        models.SharedAccess.patient_id == patient_id,
        models.SharedAccess.user_id == user_id
    ).first()
    
    if existing:
        existing.permission = permission # Update permission
        db.commit()
        db.refresh(existing)
        return existing
        
    access = models.SharedAccess(
        patient_id=patient_id,
        user_id=user_id,
        granted_by=granted_by,
        permission=permission
    )
    db.add(access)
    db.commit()
    db.refresh(access)
    return access

def revoke_access(patient_id: int, user_id: int, db: Session):
    """Revoke access"""
    db.query(models.SharedAccess).filter(
        models.SharedAccess.patient_id == patient_id,
        models.SharedAccess.user_id == user_id
    ).delete()
    db.commit()

def get_patient_access_list(patient_id: int, db: Session):
    """Get list of users who have access to this patient"""
    return db.query(models.SharedAccess).filter(
        models.SharedAccess.patient_id == patient_id
    ).options(joinedload(models.SharedAccess.user)).all()

def check_access(patient_id: int, user_id: int, db: Session):
    """Check if user has access to patient. Returns permission level or None."""
    # Check ownership
    patient = get_patient_by_id(patient_id, db)
    if patient and patient.physician_id == user_id:
        return models.PermissionLevel.EDIT # Owner has full access
        
    # Check shared access
    access = db.query(models.SharedAccess).filter(
        models.SharedAccess.patient_id == patient_id,
        models.SharedAccess.user_id == user_id
    ).first()
    
    if access:
        return access.permission
        
    return None

# Notes Management
def create_note(user_id : int, note_data : schemas.NoteCreate, db : Session):
    """Create a new clinical note"""
    note = models.Notes(
        physician_id = user_id, # author
        patient_id = note_data.patient_id,
        chief_complaint = note_data.chief_complaint,
        subjective = note_data.subjective,
        objective = note_data.objective,
        assessment = note_data.assessment,
        plan = note_data.plan,
        raw_notes = note_data.raw_notes
    )
    db.add(note)
    db.commit()
    db.refresh(note)
    return note

def get_patient_notes(patient_id : int, db : Session):
    """Get all notes for a patient, ordered by most recent first"""
    # Update to load 'author' (which was 'physicians')
    return db.query(models.Notes).options(
        joinedload(models.Notes.author)
    ).filter(
        models.Notes.patient_id == patient_id
    ).order_by(desc(models.Notes.created_at)).all()

# Vitals Management
def create_vitals(user_id : int, vitals_data : schemas.VitalsCreate, db : Session):
    """Log new vitals reading"""
    vitals = models.Vitals(
        physician_id = user_id, # author
        patient_id = vitals_data.patient_id,
        systolic_bp = vitals_data.systolic_bp,
        diastolic_bp = vitals_data.diastolic_bp,
        heart_rate = vitals_data.heart_rate,
        temperature = vitals_data.temperature,
        spo2 = vitals_data.spo2
    )
    db.add(vitals)
    db.commit()
    db.refresh(vitals)
    return vitals

def get_patient_vitals(patient_id : int, db : Session):
    """Get all vitals for a patient, ordered by most recent first"""
    return db.query(models.Vitals).filter(
        models.Vitals.patient_id == patient_id
    ).order_by(desc(models.Vitals.created_at)).all()

# Reporting
def get_patient_data_summary(patient_id: int, start_date: datetime, end_date: datetime, db: Session):
    """Get aggregated data for report"""
    notes = db.query(models.Notes).filter(
        models.Notes.patient_id == patient_id,
        models.Notes.created_at >= start_date,
        models.Notes.created_at <= end_date
    ).all()
    
    vitals = db.query(models.Vitals).filter(
        models.Vitals.patient_id == patient_id,
        models.Vitals.created_at >= start_date,
        models.Vitals.created_at <= end_date
    ).all()
    
    return {"notes": notes, "vitals": vitals}