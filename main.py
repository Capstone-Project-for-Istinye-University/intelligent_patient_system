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


# Departman ve doktor verileri
DEPARTMENTS = {
    "ENT": ["Dr. John Smith", "Dr. Emily Brown", "Dr. Michael Davis", "Dr. Laura Williams"],
    "Neurology": ["Dr. Sarah Johnson", "Dr. David Miller", "Dr. Lisa Anderson", "Dr. Richard Lee"],
    "Cardiology": ["Dr. Michael Chen", "Dr. Emma Wilson", "Dr. Robert Taylor", "Dr. Catherine Brooks"],
    "Ophthalmology": ["Dr. Rachel Green", "Dr. Thomas Moore", "Dr. Jennifer Lee", "Dr. Daniel Clark"],
    "Internal Medicine": ["Dr. James Wilson", "Dr. Jessica Martinez", "Dr. William Turner", "Dr. Sophia Adams"],
    "Orthopedics": ["Dr. Mark Robinson", "Dr. Julia Scott", "Dr. Robert Johnson", "Dr. Elizabeth Chen"],
    "Dermatology": ["Dr. Alice Kim", "Dr. Steven Park", "Dr. Michelle Wong", "Dr. Kevin Garcia"],
    "Gastroenterology": ["Dr. Thomas Lewis", "Dr. Patricia White", "Dr. Charles Martin", "Dr. Nancy Rodriguez"],
    "Psychiatry": ["Dr. Helen Carter", "Dr. George Baker", "Dr. Susan Evans", "Dr. Brian Thompson"],
    "Pediatrics": ["Dr. Anna Moore", "Dr. Paul Roberts", "Dr. Maria Lopez", "Dr. John Wilson"]
}

# Semptom-departman eşleştirmeleri ve ilk tedavi önerileri
SYMPTOM_MAPPING = {
    "headache": {
        "departments": ["Neurology", "ENT"],
        "initial_treatment": "Rest in a quiet, dark room. You may take over-the-counter pain medication. If pain is severe and persistent, please seek medical attention.",
        "severity_check": ["vision problems", "vomiting", "fever", "stiff neck", "confusion"]
    },
    "migraine": {
        "departments": ["Neurology"],
        "initial_treatment": "Rest in a dark, quiet room. Apply cold compresses to your forehead. Consider taking prescribed migraine medication if available.",
        "severity_check": ["vision loss", "numbness", "difficulty speaking"]
    },
    "fever": {
        "departments": ["Internal Medicine"],
        "initial_treatment": "Stay hydrated and rest. Take fever reducer if temperature exceeds 101.3°F (38.5°C). Seek medical attention if fever persists for more than 3 days.",
        "severity_check": ["difficulty breathing", "confusion", "rash", "severe pain"]
    },
    "sore throat": {
        "departments": ["ENT"],
        "initial_treatment": "Gargle with warm salt water. Stay hydrated. You may use throat lozenges for temporary relief.",
        "severity_check": ["difficulty swallowing", "high fever", "rash", "swollen lymph nodes"]
    },
    "stomach pain": {
        "departments": ["Internal Medicine", "Gastroenterology"],
        "initial_treatment": "Eat bland foods. Avoid acidic and spicy foods. Consider taking antacids if needed.",
        "severity_check": ["severe abdominal pain", "vomiting", "diarrhea", "blood in stool", "fever"]
    },
    "back pain": {
        "departments": ["Orthopedics", "Neurology"],
        "initial_treatment": "Rest and apply ice for the first 48-72 hours, then switch to heat. Take over-the-counter pain relievers as directed.",
        "severity_check": ["inability to move", "numbness", "loss of bladder control", "fever", "leg weakness"]
    },
    "joint pain": {
        "departments": ["Orthopedics", "Internal Medicine"],
        "initial_treatment": "Rest the affected joint. Apply ice to reduce swelling. Consider over-the-counter anti-inflammatory medication.",
        "severity_check": ["severe swelling", "redness", "inability to move joint", "fever"]
    },
    "skin rash": {
        "departments": ["Dermatology"],
        "initial_treatment": "Avoid scratching. Apply cold compresses and consider calamine lotion or hydrocortisone cream for itching.",
        "severity_check": ["difficulty breathing", "swelling of face or tongue", "fever", "spreading rapidly"]
    },
    "eye pain": {
        "departments": ["Ophthalmology"],
        "initial_treatment": "Rest your eyes. Avoid bright lights. Do not rub your eyes. Use artificial tears if they feel dry.",
        "severity_check": ["vision changes", "severe pain", "light sensitivity", "discharge"]
    },
    "chest pain": {
        "departments": ["Cardiology", "Internal Medicine"],
        "initial_treatment": "If experiencing severe chest pain, especially with shortness of breath, sweating, or nausea, call emergency services immediately.",
        "severity_check": ["shortness of breath", "radiating pain to arm or jaw", "sweating", "nausea", "irregular heartbeat"]
    },
    "cough": {
        "departments": ["Internal Medicine", "ENT"],
        "initial_treatment": "Stay hydrated. Use cough drops or honey for temporary relief. Avoid irritants like smoke.",
        "severity_check": ["difficulty breathing", "coughing up blood", "chest pain", "high fever"]
    },
    "dizziness": {
        "departments": ["Neurology", "ENT", "Cardiology"],
        "initial_treatment": "Sit or lie down immediately. Move slowly when changing positions. Stay hydrated.",
        "severity_check": ["severe headache", "difficulty speaking", "vision changes", "numbness", "fainting"]
    },
    "breathing difficulty": {
        "departments": ["Cardiology", "Internal Medicine"],
        "initial_treatment": "For severe breathing difficulty, seek emergency care immediately. Sit upright and try to stay calm.",
        "severity_check": ["blue lips or face", "chest pain", "inability to speak in full sentences", "confusion"]
    },
    "anxiety": {
        "departments": ["Psychiatry", "Internal Medicine"],
        "initial_treatment": "Practice deep breathing exercises. Focus on your breath and try to stay in the present moment.",
        "severity_check": ["chest pain", "thoughts of harming yourself", "panic attacks", "inability to function"]
    },
    "depression": {
        "departments": ["Psychiatry"],
        "initial_treatment": "Reach out to a trusted friend or family member. Maintain a regular routine and consider physical activity.",
        "severity_check": ["thoughts of suicide", "inability to function", "severe withdrawal", "significant changes in eating or sleeping"]
    },
    "fatigue": {
        "departments": ["Internal Medicine"],
        "initial_treatment": "Ensure you're getting adequate sleep. Maintain a balanced diet and stay hydrated. Consider light exercise.",
        "severity_check": ["extreme weakness", "fever", "unexplained weight loss", "shortness of breath"]
    },
    "nausea": {
        "departments": ["Gastroenterology", "Internal Medicine"],
        "initial_treatment": "Eat small, bland meals. Stay hydrated with small sips of clear liquids. Avoid strong odors.",
        "severity_check": ["severe vomiting", "inability to keep fluids down", "abdominal pain", "dizziness"]
    },
    "ear pain": {
        "departments": ["ENT"],
        "initial_treatment": "Apply a warm compress to the affected ear. Take over-the-counter pain relievers as directed.",
        "severity_check": ["severe pain", "discharge from ear", "hearing loss", "fever", "dizziness"]
    },
    "insomnia": {
        "departments": ["Psychiatry", "Neurology"],
        "initial_treatment": "Establish a regular sleep schedule. Avoid caffeine and screens before bedtime. Create a comfortable sleep environment.",
        "severity_check": ["extreme fatigue", "mood changes", "inability to function during the day", "chronic condition"]
    }
}

# Daha fazla örnek hasta verileri
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
                "doctor": "Dr. Sarah Johnson", "diagnosis": "Migraine", "id": 1},
            {"department": "Cardiology", "date": "2024-02-20",
                "doctor": "Dr. Michael Chen", "diagnosis": "Hypertension", "id": 2}
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
                "doctor": "Dr. Emily White", "diagnosis": "Asthma", "id": 1},
            {"department": "Internal Medicine", "date": "2024-03-01",
                "doctor": "Dr. James Wilson", "diagnosis": "Diabetes Control", "id": 2}
        ]
    },
    "11122233344": {
        "past_conditions": ["Arthritis", "Hypercholesterolemia"],
        "medications": [
            {"name": "Ibuprofen", "status": "active",
                "dosage": "600mg", "frequency": "twice daily"},
            {"name": "Lipitor", "status": "active",
                "dosage": "20mg", "frequency": "once daily"}
        ],
        "past_appointments": [
            {"department": "Orthopedics", "date": "2024-01-10",
                "doctor": "Dr. Mark Robinson", "diagnosis": "Rheumatoid Arthritis", "id": 1},
            {"department": "Cardiology", "date": "2024-02-15",
                "doctor": "Dr. Emma Wilson", "diagnosis": "Hypercholesterolemia", "id": 2}
        ]
    },
    "22233344455": {
        "past_conditions": ["Depression", "Insomnia"],
        "medications": [
            {"name": "Fluoxetine", "status": "active",
                "dosage": "20mg", "frequency": "once daily"},
            {"name": "Ambien", "status": "active",
                "dosage": "10mg", "frequency": "as needed before sleep"}
        ],
        "past_appointments": [
            {"department": "Psychiatry", "date": "2024-02-05",
                "doctor": "Dr. Helen Carter", "diagnosis": "Major Depressive Disorder", "id": 1},
            {"department": "Neurology", "date": "2024-03-10",
                "doctor": "Dr. Lisa Anderson", "diagnosis": "Chronic Insomnia", "id": 2}
        ]
    },
    "33344455566": {
        "past_conditions": ["Eczema", "Allergic Rhinitis"],
        "medications": [
            {"name": "Hydrocortisone Cream", "status": "active",
                "dosage": "1%", "frequency": "twice daily"},
            {"name": "Cetirizine", "status": "active",
                "dosage": "10mg", "frequency": "once daily"}
        ],
        "past_appointments": [
            {"department": "Dermatology", "date": "2024-01-20",
                "doctor": "Dr. Alice Kim", "diagnosis": "Atopic Dermatitis", "id": 1},
            {"department": "ENT", "date": "2024-02-25",
                "doctor": "Dr. John Smith", "diagnosis": "Seasonal Allergies", "id": 2}
        ]
    }
}

# Hasta kayıt endpoint'i


@app.post("/api/patient/register")
async def register_patient(patient_data: Dict, db: Session = Depends(get_db)):
    try:
        tc_number = patient_data.get("tc_number")
        
        if not tc_number or len(tc_number) != 11:
            raise HTTPException(status_code=400, detail="Invalid TC number")
            
        # Create or update patient record
        if tc_number not in PATIENT_DATABASE:
            PATIENT_DATABASE[tc_number] = {
                "past_conditions": [],
                "medications": [],
                "past_appointments": []
            }
            
        # In a real app, we would use the database here
        # patient_intake = PatientIntakeAgent(db)
        # patient = await patient_intake.process(patient_data)
        
        return {"message": "Patient registered successfully", "tc_number": tc_number}
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
