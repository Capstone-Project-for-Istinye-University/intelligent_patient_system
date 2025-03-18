from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Dict, Optional, List
import random

from database.db_setup import get_db, init_db
from models.patient import Patient, Doctor, Appointment
from agents.patient_intake import PatientIntakeAgent
from agents.diagnosis import DiagnosisAgent
from agents.recommendation import RecommendationAgent
from pydantic import BaseModel

app = FastAPI(title="Patient Referral Intelligent System")

# CORS settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Veritabanı başlatma


@app.on_event("startup")
def startup_event():
    init_db()

# Veri modelleri


class PatientHistory(BaseModel):
    tc_number: str
    past_conditions: List[str]
    medications: List[Dict[str, str]]
    past_appointments: List[Dict[str, str]]


class Symptoms(BaseModel):
    tc_number: str
    symptoms: str
    severity: str
    duration: str


class DepartmentRequest(BaseModel):
    tc_number: str
    department: str
    preferred_date: str


class AppointmentRequest(BaseModel):
    tc_number: str
    department: str
    doctor_id: int
    appointment_date: str


class AppointmentUpdateRequest(BaseModel):
    tc_number: str
    appointment_id: int
    new_date: str


class AppointmentCancelRequest(BaseModel):
    tc_number: str
    appointment_id: int


# Örnek hasta veritabanı (gerçek uygulamada bir veritabanında saklanacak)
# Example patient database (in a real application, this would be stored in a database)
PATIENT_DATABASE = {
    "12345678901": {
        "past_conditions": ["Migraine", "Hypertension"],
        "medications": [
            {"name": "Beloc", "status": "active",
                "dosage": "50mg", "frequency": "once daily"},
            {"name": "Majezik", "status": "past",
                "dosage": "100mg", "frequency": "when needed"}
        ],
        "past_appointments": [
            {"department": "Neurology", "date": "2024-01-15",
                "doctor": "Dr. Sarah Johnson", "diagnosis": "Migraine"},
            {"department": "Cardiology", "date": "2024-02-20",
                "doctor": "Dr. Michael Chen", "diagnosis": "Hypertension"}
        ]
    },
    "98765432109": {
        "past_conditions": ["Diabetes", "Asthma"],
        "medications": [
            {"name": "Ventolin", "status": "active",
                "dosage": "100mcg", "frequency": "as needed"},
            {"name": "Glucophage", "status": "active",
                "dosage": "1000mg", "frequency": "twice daily"}
        ],
        "past_appointments": [
            {"department": "Pulmonology", "date": "2024-02-01",
                "doctor": "Dr. Emily White", "diagnosis": "Asthma"},
            {"department": "Internal Medicine", "date": "2024-03-01",
                "doctor": "Dr. James Wilson", "diagnosis": "Diabetes Control"}
        ]
    }
}

# Departman ve doktor verileri
DEPARTMENTS = {
    "ENT": ["Dr. John Smith", "Dr. Emily Brown", "Dr. Michael Davis"],
    "Neurology": ["Dr. Sarah Johnson", "Dr. David Miller", "Dr. Lisa Anderson"],
    "Cardiology": ["Dr. Michael Chen", "Dr. Emma Wilson", "Dr. Robert Taylor"],
    "Ophthalmology": ["Dr. Rachel Green", "Dr. Thomas Moore", "Dr. Jennifer Lee"],
    "Internal Medicine": ["Dr. James Wilson", "Dr. Jessica Martinez", "Dr. William Turner"]
}

# Semptom-departman eşleştirmeleri ve ilk tedavi önerileri
SYMPTOM_MAPPING = {
    "headache": {
        "departments": ["Neurology", "ENT"],
        "initial_treatment": "Rest in a quiet, dark room. You may take over-the-counter pain medication. If pain is severe and persistent, please seek medical attention.",
        "severity_check": ["vision problems", "vomiting", "fever"]
    },
    "fever": {
        "departments": ["Internal Medicine"],
        "initial_treatment": "Stay hydrated and rest. Take fever reducer if temperature exceeds 101.3°F (38.5°C). Seek medical attention if fever persists for more than 3 days.",
        "severity_check": ["difficulty breathing", "confusion"]
    },
    "sore throat": {
        "departments": ["ENT"],
        "initial_treatment": "Gargle with warm salt water. Stay hydrated. You may use throat lozenges for temporary relief.",
        "severity_check": ["difficulty swallowing", "high fever"]
    },
    "stomach pain": {
        "departments": ["Internal Medicine"],
        "initial_treatment": "Eat bland foods. Avoid acidic and spicy foods. Consider taking antacids if needed.",
        "severity_check": ["severe abdominal pain", "vomiting", "diarrhea"]
    }
}

# Hasta kayıt endpoint'i


@app.post("/api/patient/register")
async def register_patient(patient_data: Dict, db: Session = Depends(get_db)):
    try:
        patient_intake = PatientIntakeAgent(db)
        patient = await patient_intake.process(patient_data)
        return {"message": "Patient registered successfully", "patient_id": patient.id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# Hasta geçmişi endpoint'i


@app.get("/api/patient/{tc_number}/history")
async def get_patient_history(tc_number: str):
    # Create a new patient record if not exists
    if tc_number not in PATIENT_DATABASE:
        PATIENT_DATABASE[tc_number] = {
            "past_conditions": [],
            "medications": [],
            "past_appointments": []
        }
    return PATIENT_DATABASE[tc_number]

# Tanı endpoint'i


@app.post("/api/patient/diagnose")
async def diagnose_patient(symptoms: Symptoms):
    # Create patient record if not exists
    if symptoms.tc_number not in PATIENT_DATABASE:
        PATIENT_DATABASE[symptoms.tc_number] = {
            "past_conditions": [],
            "medications": [],
            "past_appointments": []
        }

    patient_history = PATIENT_DATABASE[symptoms.tc_number]
    symptoms_lower = symptoms.symptoms.lower()

    # Recommendations and treatment suggestions
    recommendations = {
        "departments": set(),
        "initial_treatment": [],
        "warnings": [],
        "patient_specific_notes": []
    }

    # Analyze symptoms
    for symptom, info in SYMPTOM_MAPPING.items():
        if symptom in symptoms_lower:
            recommendations["departments"].update(info["departments"])
            recommendations["initial_treatment"].append(
                info["initial_treatment"])

            # Severity check
            for severity in info["severity_check"]:
                if severity in symptoms_lower:
                    recommendations["warnings"].append(
                        f"The combination of '{symptom}' with '{severity}' may be serious. Please seek medical attention promptly."
                    )

    # Patient history specific recommendations
    if patient_history:
        active_meds = [med for med in patient_history["medications"]
                       if med["status"] == "active"]
        if active_meds:
            recommendations["patient_specific_notes"].append(
                "Please inform the doctor about your current medications: " +
                ", ".join(
                    [f"{med['name']} ({med['dosage']})" for med in active_meds])
            )

        if patient_history["past_conditions"]:
            recommendations["patient_specific_notes"].append(
                "Please inform the doctor about your chronic conditions: " +
                ", ".join(patient_history["past_conditions"])
            )

    # If no department recommendations found
    if not recommendations["departments"]:
        recommendations["departments"] = set(DEPARTMENTS.keys())
        recommendations["warnings"].append(
            "No specific match found for your symptoms. Please select the most appropriate department."
        )

    return {
        "recommended_departments": list(recommendations["departments"]),
        "initial_treatment": recommendations["initial_treatment"],
        "warnings": recommendations["warnings"],
        "patient_specific_notes": recommendations["patient_specific_notes"]
    }

# Doktor önerisi endpoint'i


@app.post("/api/patient/recommend")
async def recommend_doctor(request: DepartmentRequest):
    if request.department not in DEPARTMENTS:
        raise HTTPException(status_code=400, detail="Invalid department")

    # Create patient record if not exists
    if request.tc_number not in PATIENT_DATABASE:
        PATIENT_DATABASE[request.tc_number] = {
            "past_conditions": [],
            "medications": [],
            "past_appointments": []
        }

    patient_history = PATIENT_DATABASE[request.tc_number]
    available_doctors = []

    for doctor in DEPARTMENTS[request.department]:
        if random.random() > 0.5:  # 50% chance doctor is available
            doctor_info = {
                "name": doctor,
                "specialization": request.department
            }

            # If patient has visited this doctor before, note it
            past_visits = [
                apt for apt in patient_history["past_appointments"]
                if apt["doctor"] == doctor
            ]
            if past_visits:
                doctor_info["past_visit"] = past_visits[-1]

            available_doctors.append(doctor_info)

    return {
        "available_doctors": available_doctors
    }

# Randevu oluşturma endpoint'i


@app.post("/api/appointment/create")
async def create_appointment(request: AppointmentRequest):
    if request.tc_number not in PATIENT_DATABASE:
        PATIENT_DATABASE[request.tc_number] = {
            "past_conditions": [],
            "medications": [],
            "past_appointments": []
        }

    patient = PATIENT_DATABASE[request.tc_number]

    # Generate a unique appointment ID
    appointment_id = len(patient["past_appointments"]) + 1

    # Get doctor name
    doctor_name = f"Dr. {DEPARTMENTS[request.department][request.doctor_id - 1]}"

    # Create new appointment
    new_appointment = {
        "id": appointment_id,
        "department": request.department,
        "date": request.appointment_date,
        "doctor": doctor_name
    }

    patient["past_appointments"].append(new_appointment)

    return {
        "success": True,
        "appointment_id": appointment_id,
        "department": request.department,
        "appointment_date": request.appointment_date,
        "doctor_name": doctor_name
    }

# Randevu listesi endpoint'i


@app.get("/api/patient/{tc_number}/appointments")
async def get_patient_appointments(tc_number: str):
    if tc_number not in PATIENT_DATABASE:
        raise HTTPException(status_code=404, detail="Patient not found")

    return {
        "appointments": PATIENT_DATABASE[tc_number]["past_appointments"]
    }

# Randevu güncelleme endpoint'i


@app.put("/api/appointment/update")
async def update_appointment(request: AppointmentUpdateRequest):
    if request.tc_number not in PATIENT_DATABASE:
        raise HTTPException(status_code=404, detail="Patient not found")

    patient = PATIENT_DATABASE[request.tc_number]
    appointments = patient["past_appointments"]

    for appointment in appointments:
        if appointment["id"] == request.appointment_id:
            appointment["date"] = request.new_date
            return {"success": True, "message": "Appointment updated successfully"}

    raise HTTPException(status_code=404, detail="Appointment not found")

# Randevu iptal endpoint'i


@app.delete("/api/appointment/cancel")
async def cancel_appointment(request: AppointmentCancelRequest):
    if request.tc_number not in PATIENT_DATABASE:
        raise HTTPException(status_code=404, detail="Patient not found")

    patient = PATIENT_DATABASE[request.tc_number]
    appointments = patient["past_appointments"]

    for i, appointment in enumerate(appointments):
        if appointment.get("id") == request.appointment_id:
            del appointments[i]
            return {"success": True, "message": "Appointment cancelled successfully"}

    raise HTTPException(status_code=404, detail="Appointment not found")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
