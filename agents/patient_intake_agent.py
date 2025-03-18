from sqlalchemy.orm import Session
from models.patient import Patient
from datetime import datetime
from typing import Dict, Optional


class PatientIntakeAgent:
    def __init__(self, db: Session):
        self.db = db

    async def process(self, patient_data: Dict) -> Patient:
        """
        Hasta verilerini işler ve veritabanına kaydeder.

        Args:
            patient_data (Dict): Hasta bilgileri

        Returns:
            Patient: Oluşturulan hasta nesnesi
        """
        try:
            # TC numarası kontrolü
            existing_patient = self.db.query(Patient).filter(
                Patient.tc_number == patient_data["tc_number"]
            ).first()

            if existing_patient:
                return existing_patient

            # Yeni hasta oluştur
            patient = Patient(
                tc_number=patient_data["tc_number"],
                name=patient_data["name"],
                email=patient_data["email"],
                phone=patient_data["phone"],
                date_of_birth=datetime.fromisoformat(
                    patient_data["date_of_birth"]),
                gender=patient_data["gender"],
                address=patient_data.get("address", ""),
                emergency_contact=patient_data.get("emergency_contact", {})
            )

            self.db.add(patient)
            self.db.commit()
            self.db.refresh(patient)

            return patient

        except Exception as e:
            self.db.rollback()
            raise Exception(f"Error processing patient data: {str(e)}")

    async def get_patient_history(self, tc_number: str) -> Dict:
        """
        Hasta geçmişini getirir.

        Args:
            tc_number (str): Hasta TC numarası

        Returns:
            Dict: Hasta geçmişi bilgileri
        """
        patient = self.db.query(Patient).filter(
            Patient.tc_number == tc_number
        ).first()

        if not patient:
            raise Exception("Patient not found")

        return {
            "patient_info": {
                "name": patient.name,
                "tc_number": patient.tc_number,
                "date_of_birth": patient.date_of_birth,
                "gender": patient.gender
            },
            "appointments": [
                {
                    "date": app.appointment_date,
                    "department": app.department,
                    "symptoms": app.symptoms,
                    "diagnosis": app.diagnosis
                }
                for app in patient.appointments
            ],
            "medical_history": [
                {
                    "condition": hist.condition,
                    "diagnosis_date": hist.diagnosis_date,
                    "treatment": hist.treatment,
                    "notes": hist.notes
                }
                for hist in patient.medical_history
            ],
            "medications": [
                {
                    "name": med.name,
                    "dosage": med.dosage,
                    "frequency": med.frequency,
                    "start_date": med.start_date,
                    "end_date": med.end_date,
                    "is_active": med.is_active
                }
                for med in patient.medications
            ]
        }
