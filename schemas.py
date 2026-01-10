from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional

class RegisterUser(BaseModel):
    name : str
    email : EmailStr
    password : str
    role : str = 'physician'

    class Config:
        from_attributes = True

class SharedAccessCreate(BaseModel):
    user_email : EmailStr
    permission : str = 'VIEW' # VIEW or EDIT

class SharedAccessResponse(BaseModel):
    id : int
    patient_id : int
    user_id : int
    granted_by : int
    permission : str
    created_at : datetime
    user_name : Optional[str] = None
    user_email : Optional[str] = None

    class Config:
        from_attributes = True

class RegisterPatient(BaseModel):
    name : str
    phone_number : str
    membership_price : float
    physician_id : int

    class Config:
        from_attributes = True

class UserOut(BaseModel):
    id : int
    name : str
    email : EmailStr
    role : str

    class Config:
        from_attributes = True

class LoginRequest(BaseModel):
    email : EmailStr
    password : str

class NoteCreate(BaseModel):
    patient_id : int
    chief_complaint : Optional[str] = None
    subjective : Optional[str] = None
    objective : Optional[str] = None
    assessment : Optional[str] = None
    plan : Optional[str] = None
    raw_notes : Optional[str] = None

class NoteResponse(BaseModel):
    id : int
    physician_id : int
    patient_id : int
    chief_complaint : Optional[str]
    subjective : Optional[str]
    objective : Optional[str]
    assessment : Optional[str]
    plan : Optional[str]
    raw_notes : Optional[str]
    created_at : datetime
    physician_name : str

    class Config:
        from_attributes = True

class VitalsCreate(BaseModel):
    patient_id : int
    systolic_bp : Optional[int] = None
    diastolic_bp : Optional[int] = None
    heart_rate : Optional[int] = None
    temperature : Optional[float] = None
    spo2 : Optional[int] = None

class VitalsResponse(BaseModel):
    id : int
    physician_id : int
    patient_id : int
    systolic_bp : Optional[int]
    diastolic_bp : Optional[int]
    heart_rate : Optional[int]
    temperature : Optional[float]
    spo2 : Optional[int]
    created_at : datetime

    class Config:
        from_attributes = True

# AI Consultation Analysis Schemas
class ConsultationAnalysis(BaseModel):
    transcript: str
    patient_context: Optional[str] = None

    class Config:
        from_attributes = True

class SOAPNote(BaseModel):
    subjective: str
    objective: str
    assessment: str
    plan: str

    class Config:
        from_attributes = True

class SOAPResponse(BaseModel):
    soap_note: SOAPNote
    patient_summary: str

    class Config:
        from_attributes = True

class PatientListItem(BaseModel):
    id : int
    name : str
    phone_number : str
    physician_id : int

    class Config:
        from_attributes = True

class PatientDetail(BaseModel):
    id : int
    name : str
    phone_number : str
    membership_price : float
    physician_id : int
    permission_level : str = "VIEW" # OWNER, EDIT, VIEW

    class Config:
        from_attributes = True
