from fastapi import FastAPI, HTTPException, Request, Query, Depends, UploadFile, File
from database import Base, SessionLocal, engine, get_db
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import schemas, models, crud
from sqlalchemy.orm import Session
from auth import (
    get_current_user,
    authenticate_user,
    create_access_token,
    get_password_hash
)
from typing import List, Optional
from datetime import datetime, timedelta

app = FastAPI(title="VriddhaMitra", description="User-Patient Management System")
Base.metadata.create_all(engine)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Root endpoint
@app.get("/")
def read_root():
    return RedirectResponse(url="/static/index.html")

# Authentication endpoints
@app.post('/register_user', response_model=schemas.UserOut)
def register_user(user: schemas.RegisterUser, db: Session = Depends(get_db)):
    """Register a new user (physician/staff)"""
    if crud.check_user_exists(user.email, db):
        raise HTTPException(status_code=400, detail='User already exists')
    
    # Hash password
    hashed_password = get_password_hash(user.password)
    user_data = user.model_dump()
    user_data['password'] = hashed_password
    
    # Create user object
    new_user = schemas.RegisterUser(**user_data)
    created_user = crud.register_user(new_user, db)
    
    return created_user

@app.post('/register_patient')
def register_patient(
    patient: schemas.RegisterPatient,
    current_user: models.Users = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Register a new patient"""
    # Only physicians can register patients
    if current_user.role != 'physician':
        raise HTTPException(status_code=403, detail="Only physicians can register new patients")

    try:
        # Override physician_id to be the current user (owner)
        patient.physician_id = current_user.id
        
        # Check if patient exists
        if crud.check_patient_exists(patient.phone_number, db):
            raise HTTPException(status_code=400, detail='Patient with this phone number already exists')
        
        created_patient = crud.register_patient(patient, db)
        return created_patient
    
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        print(f"Error registering patient: {str(e)}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@app.post('/login')
def login(login_data: schemas.LoginRequest, db: Session = Depends(get_db)):
    """Login endpoint - returns JWT token"""
    user = authenticate_user(login_data.email, login_data.password, db)
    
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )
    
    # Create JWT token
    access_token = create_access_token(
        data={"sub": str(user.id), "email": user.email, "role": user.role}
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "role": user.role
        }
    }

# Patient Management
@app.get('/users/{user_id}/patients', response_model=List[schemas.PatientListItem])
def get_patients(
    user_id: int,
    current_user: models.Users = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all patients assigned to OR shared with a user"""
    if current_user.id != user_id:
        raise HTTPException(status_code=403, detail="Access forbidden")
    
    patients = crud.get_user_patients(user_id, db)
    return patients

@app.get('/users/{user_id}/patients/search', response_model=List[schemas.PatientListItem])
def search_patients(
    user_id: int,
    q: str = Query(...),
    current_user: models.Users = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Search patients by name or phone"""
    if current_user.id != user_id:
        raise HTTPException(status_code=403, detail="Access forbidden")
    
    patients = crud.search_patients(user_id, q, db)
    return patients

@app.get('/patients/{patient_id}', response_model=schemas.PatientDetail)
def get_patient(
    patient_id: int,
    current_user: models.Users = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get patient details (protected)"""
    # Get permission level
    permission = crud.check_access(patient_id, current_user.id, db)
    if not permission:
        raise HTTPException(status_code=403, detail="Access forbidden: You do not have permission to view this patient")
    
    patient = crud.get_patient_by_id(patient_id, db)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
        
    # Convert to schema manually to inject permission_level
    patient_data = schemas.PatientDetail.model_validate(patient)
    patient_data.permission_level = permission.value if hasattr(permission, 'value') else permission
    
    return patient_data

# Sharing Endpoints
@app.post('/patients/{patient_id}/share', response_model=schemas.SharedAccessResponse)
def share_patient(
    patient_id: int,
    share_data: schemas.SharedAccessCreate,
    current_user: models.Users = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Share a patient with another user"""
    # Only owner can share (or check logic)
    patient = crud.get_patient_by_id(patient_id, db)
    if not patient or patient.physician_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the patient owner can share this record")
    
    # Find target user
    target_user = crud.get_user_by_email(share_data.user_email, db)
    if not target_user:
        raise HTTPException(status_code=404, detail="User with this email not found")
        
    if target_user.id == current_user.id:
         raise HTTPException(status_code=400, detail="Cannot share with yourself")

    access = crud.grant_access(
        patient_id=patient_id,
        user_id=target_user.id,
        granted_by=current_user.id,
        permission=share_data.permission,
        db=db
    )
    
    # Populate response fields
    response = schemas.SharedAccessResponse.model_validate(access)
    response.user_name = target_user.name
    response.user_email = target_user.email
    return response

@app.delete('/patients/{patient_id}/share/{user_id}')
def revoke_sharing(
    patient_id: int,
    user_id: int,
    current_user: models.Users = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Revoke sharing access"""
    patient = crud.get_patient_by_id(patient_id, db)
    if not patient or patient.physician_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the patient owner can revoke access")
        
    crud.revoke_access(patient_id, user_id, db)
    return {"message": "Access revoked"}

@app.get('/patients/{patient_id}/access', response_model=List[schemas.SharedAccessResponse])
def get_sharing_list(
    patient_id: int,
    current_user: models.Users = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get list of users with shared access"""
    permission = crud.check_access(patient_id, current_user.id, db)
    if not permission: # Basic access check
        raise HTTPException(status_code=403, detail="Access forbidden")
        
    access_list = crud.get_patient_access_list(patient_id, db)
    
    # Populate extra fields
    response = []
    for access in access_list:
        resp = schemas.SharedAccessResponse.model_validate(access)
        resp.user_name = access.user.name
        resp.user_email = access.user.email
        response.append(resp)
        
    return response

# Reporting Endpoints
@app.get('/patients/{patient_id}/report')
def generate_report(
    patient_id: int,
    period: str = Query("week", enum=["week", "month", "all", "custom"]),
    start_date: Optional[str] = Query(None), # YYYY-MM-DD
    end_date: Optional[str] = Query(None),   # YYYY-MM-DD
    current_user: models.Users = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Generate a PDF summary report for a patient"""
    permission = crud.check_access(patient_id, current_user.id, db)
    if not permission:
        raise HTTPException(status_code=403, detail="Access forbidden")
        
    now = datetime.now()
    if period == "week":
        s_date = now - timedelta(weeks=1)
        e_date = now
    elif period == "month":
        s_date = now - timedelta(days=30)
        e_date = now
    elif period == "all":
        s_date = datetime.min
        e_date = now
    elif period == "custom":
        if not start_date or not end_date:
            raise HTTPException(status_code=400, detail="Start and End dates required for custom period")
        try:
            s_date = datetime.strptime(start_date, "%Y-%m-%d")
            e_date = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1) # inclusive
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    else:
        s_date = now - timedelta(weeks=1)
        e_date = now
        
    data = crud.get_patient_data_summary(patient_id, s_date, e_date, db)
    patient = crud.get_patient_by_id(patient_id, db)
    
    # Generate PDF using Platypus
    from reportlab.lib.pagesizes import letter
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from io import BytesIO
    from fastapi.responses import StreamingResponse
    import os
    import re
    
    # Register Hindi Font
    font_path = "static/fonts/NotoSansDevanagari-Regular.ttf"
    has_hindi_font = False
    if os.path.exists(font_path):
        pdfmetrics.registerFont(TTFont('Devanagari', font_path))
        has_hindi_font = True
        
    def format_text(text):
        """Wraps text in Hindi font tag if Devanagari chars detected"""
        if not text: return "-"
        if not has_hindi_font: return str(text)
        
        # Simple check for Devanagari block (U+0900 to U+097F)
        # If text contains any Devanagari char, we wrap the whole thing or split?
        # Safest for now: wrap the whole string in Devanagari font if it has Hindi.
        # But wait, NotoSansDevanagari might NOT have English.
        # So we should only wrap the HINDI parts.
        
        # Regex for Devanagari: [\u0900-\u097F]
        # We replace any sequence of Devanagari chars with <font face="Devanagari">\g<0></font>
        return re.sub(r'([\u0900-\u097F]+)', r'<font face="Devanagari">\1</font>', str(text))

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elements = []
    
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='HindiNormal', parent=styles['Normal'], fontName='Helvetica', leading=14))
    styles.add(ParagraphStyle(name='HindiSmall', parent=styles['Normal'], fontName='Helvetica', fontSize=9, leading=12))
    
    # Header
    elements.append(Paragraph(f"<b>Patient Summary Report</b>", styles['Heading1']))
    elements.append(Spacer(1, 12))
    
    # Patient Info Table
    header_data = [
        [Paragraph(f"<b>Patient Name:</b> {format_text(patient.name)}", styles['HindiNormal']),
         Paragraph(f"<b>Generated on:</b> {now.strftime('%d-%b-%Y %H:%M')}", styles['Normal'])],
        [Paragraph(f"<b>Period:</b> {s_date.strftime('%d-%b-%Y')} to {e_date.strftime('%d-%b-%Y')}", styles['Normal']),
         Paragraph(f"<b>Patient ID:</b> {patient.id}", styles['Normal'])]
    ]
    t = Table(header_data, colWidths=[300, 200])
    t.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 10),
    ]))
    elements.append(t)
    elements.append(Spacer(1, 20))
    
    # Vitals Section
    elements.append(Paragraph("<b>Vitals Summary</b>", styles['Heading2']))
    elements.append(Spacer(1, 10))
    
    if data['vitals']:
        vitals_data = [['Date', 'BP (mmHg)', 'Heart Rate', 'Temp (F)', 'SpO2 (%)']]
        for v in data['vitals'][:20]: # Limit for PDF
            v_date = v.created_at.strftime('%d-%b-%Y %H:%M')
            bp = f"{v.systolic_bp}/{v.diastolic_bp}" if v.systolic_bp else "-"
            vitals_data.append([
                v_date, 
                bp, 
                str(v.heart_rate or '-'), 
                str(v.temperature or '-'), 
                str(v.spo2 or '-')
            ])
            
        t_vitals = Table(vitals_data, colWidths=[120, 100, 80, 80, 80])
        t_vitals.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#f3f4f6')),
            ('TEXTCOLOR', (0,0), (-1,0), colors.black),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,0), 10),
            ('BOTTOMPADDING', (0,0), (-1,0), 12),
            ('BACKGROUND', (0,1), (-1,-1), colors.white),
            ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ]))
        elements.append(t_vitals)
    else:
        elements.append(Paragraph("No vitals recorded in this period.", styles['Normal']))
        
    elements.append(Spacer(1, 20))
    
    # Notes Section
    elements.append(Paragraph("<b>Clinical Notes</b>", styles['Heading2']))
    elements.append(Spacer(1, 10))
    
    if data['notes']:
        for n in data['notes']:
            n_date = n.created_at.strftime('%d-%b-%Y %H:%M')
            author_text = format_text(n.author.name)
            
            # Note Header
            elements.append(Paragraph(f"<b>Note by {author_text} on {n_date}</b>", styles['HindiNormal']))
            
            # content
            content_parts = []
            if n.assessment: content_parts.append(f"<b>Assessment:</b> {format_text(n.assessment)}")
            if n.plan: content_parts.append(f"<b>Plan:</b> {format_text(n.plan)}")
            if n.raw_notes: content_parts.append(f"<b>Raw:</b> {format_text(n.raw_notes)}")
            
            for part in content_parts:
                elements.append(Paragraph(part, styles['HindiSmall']))
                
            elements.append(Spacer(1, 15))
            elements.append(Paragraph("<hr/>", styles['Normal'])) # Does hr work? using a line instead
            # Drawing a line with Table or just spacer
            elements.append(Spacer(1, 5))
            
    else:
        elements.append(Paragraph("No notes recorded in this period.", styles['Normal']))

    doc.build(elements)
    buffer.seek(0)
    
    return StreamingResponse(
        buffer, 
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=report_{patient_id}_{period}.pdf"}
    )

# Protected notes endpoints
@app.post('/users/{user_id}/notes')
def create_note(
    user_id: int,
    note: schemas.NoteCreate,
    current_user: models.Users = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new clinical note"""
    if current_user.id != user_id:
        raise HTTPException(status_code=403, detail="Access forbidden")
    
    # Check permissions (EDIT required)
    permission = crud.check_access(note.patient_id, user_id, db)
    if permission != models.PermissionLevel.EDIT:
        raise HTTPException(status_code=403, detail="You do not have permission to add notes (Edit access required)")
    
    created_note = crud.create_note(user_id, note, db)
    return {
        "id": created_note.id,
        "message": "Note created successfully"
    }

@app.get('/patients/{patient_id}/notes')
def get_notes(
    patient_id: int,
    current_user: models.Users = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all notes for a patient"""
    permission = crud.check_access(patient_id, current_user.id, db)
    if not permission:
        raise HTTPException(status_code=403, detail="Access forbidden")
    
    notes = crud.get_patient_notes(patient_id, db)
    
    # Format response
    formatted_notes = []
    for note in notes:
        formatted_notes.append({
            "id": note.id,
            "physician_id": note.physician_id, # author
            "physician_name": note.author.name,
            "patient_id": note.patient_id,
            "chief_complaint": note.chief_complaint,
            "subjective": note.subjective,
            "objective": note.objective,
            "assessment": note.assessment,
            "plan": note.plan,
            "raw_notes": note.raw_notes,
            "created_at": note.created_at.isoformat()
        })
    
    return formatted_notes

# Protected vitals endpoints
@app.post('/users/{user_id}/vitals')
def create_vitals(
    user_id: int,
    vitals: schemas.VitalsCreate,
    current_user: models.Users = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Log new vitals reading"""
    if current_user.id != user_id:
        raise HTTPException(status_code=403, detail="Access forbidden")
        
    permission = crud.check_access(vitals.patient_id, user_id, db)
    if permission != models.PermissionLevel.EDIT:
        raise HTTPException(status_code=403, detail="Edit access required")
    
    created_vitals = crud.create_vitals(user_id, vitals, db)
    return {
        "id": created_vitals.id,
        "message": "Vitals logged successfully"
    }

@app.get('/patients/{patient_id}/vitals', response_model=List[schemas.VitalsResponse])
def get_vitals(
    patient_id: int,
    current_user: models.Users = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all vitals for a patient"""
    permission = crud.check_access(patient_id, current_user.id, db)
    if not permission:
        raise HTTPException(status_code=403, detail="Access forbidden")
    
    vitals = crud.get_patient_vitals(patient_id, db)
    return vitals

# Voice transcription endpoint
@app.post('/transcribe')
async def transcribe_audio(
    file: UploadFile = File(...),
    current_user: models.Users = Depends(get_current_user)
):
    """Transcribe audio using Sarvam AI API"""
    import requests
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    sarvam_api_key = os.getenv("SARVAM_API_KEY")
    sarvam_api_url = "https://api.sarvam.ai/speech-to-text"
    
    if not sarvam_api_key:
        raise HTTPException(status_code=500, detail="Sarvam API key not configured")
    
    try:
        audio_content = await file.read()
        headers = {"api-subscription-key": sarvam_api_key}
        files = {"file": ("audio.wav", audio_content, "audio/wav")}
        data = {"model": "saarika:v2.5", "language_code": "hi-IN", "with_diarization": "false"}
        
        response = requests.post(sarvam_api_url, headers=headers, files=files, data=data, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            return {"text": result.get("transcript", ""), "status": "success", "language": result.get("language_code", "hi-IN")}
        else:
            return {"text": "", "status": "error", "error": f"Sarvam API error: {response.status_code}", "detail": response.text}
            
    except Exception as e:
        print(f"Transcription failed: {str(e)}")
        return {"text": "", "status": "error", "error": str(e)}

# AI Consultation Analysis endpoint
@app.post('/analyze-consultation', response_model=schemas.SOAPResponse)
async def analyze_consultation(
    data: schemas.ConsultationAnalysis,
    current_user: models.Users = Depends(get_current_user)
):
    """Generate SOAP notes from transcript using OpenAI"""
    from openai import OpenAI
    import os
    import json
    from dotenv import load_dotenv
    
    load_dotenv()
    openai_api_key = os.getenv("OPENAI_API_KEY")
    
    if not openai_api_key:
        raise HTTPException(status_code=500, detail="OpenAI API key not configured")
    
    try:
        client = OpenAI(api_key=openai_api_key)
        system_prompt = """You are a medical AI assistant. Analyze consultation transcript and generate SOAP notes and summary."""
        user_prompt = f"""Transcript: {data.transcript}\nContext: {data.patient_context}\nJSON Format: {{"soap_note": {{"subjective": "...", "objective": "...", "assessment": "...", "plan": "..."}}, "patient_summary": "..."}}"""

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
            response_format={"type": "json_object"},
            temperature=0.3
        )
        
        result = json.loads(response.choices[0].message.content)
        soap_data = result.get("soap_note", {})
        return schemas.SOAPResponse(
            soap_note=schemas.SOAPNote(
                subjective=soap_data.get("subjective", "Not documented"),
                objective=soap_data.get("objective", "Not documented"),
                assessment=soap_data.get("assessment", "Not documented"),
                plan=soap_data.get("plan", "Not documented")
            ),
            patient_summary=result.get("patient_summary", "Consultation completed.")
        )
        
    except Exception as e:
        print(f"OpenAI analysis failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to analyze consultation: {str(e)}")