from typing import Dict, List
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from models.patient import Doctor, Appointment, Patient
import numpy as np


class RecommendationAgent:
    def __init__(self, db: Session):
        self.db = db

    async def get_recommendation(self, patient_id: int, department: str, preferred_date: datetime = None) -> Dict:
        """
        Hasta için doktor ve randevu önerileri oluşturur.

        Args:
            patient_id (int): Hasta ID
            department (str): Seçilen departman
            preferred_date (datetime, optional): Tercih edilen tarih

        Returns:
            Dict: Öneriler ve doktor bilgileri
        """
        try:
            # Departmandaki doktorları getir
            doctors = self.db.query(Doctor).filter(
                Doctor.department == department
            ).all()

            if not doctors:
                raise Exception(
                    f"No doctors found in department: {department}")

            # Her doktor için müsait randevuları kontrol et
            doctor_availability = []
            for doctor in doctors:
                availability = await self._check_doctor_availability(
                    doctor.id,
                    preferred_date
                )
                if availability:
                    doctor_availability.append({
                        "doctor": {
                            "id": doctor.id,
                            "name": doctor.name,
                            "specialization": doctor.specialization,
                            "experience": self._calculate_experience(doctor.created_at)
                        },
                        "available_slots": availability
                    })

            # Doktorları deneyim ve müsaitlik durumuna göre sırala
            doctor_availability.sort(
                key=lambda x: (
                    len(x["available_slots"]),
                    x["doctor"]["experience"]
                ),
                reverse=True
            )

            return {
                "department": department,
                "doctors": doctor_availability,
                "recommendations": self._generate_recommendations(patient_id, department)
            }

        except Exception as e:
            raise Exception(f"Error generating recommendations: {str(e)}")

    async def _check_doctor_availability(self, doctor_id: int, preferred_date: datetime = None) -> List[datetime]:
        """Doktorun müsait randevu saatlerini kontrol eder."""
        # Varsayılan olarak bugünden itibaren 7 günlük randevuları kontrol et
        if not preferred_date:
            preferred_date = datetime.now()

        end_date = preferred_date + timedelta(days=7)

        # Mevcut randevuları al
        existing_appointments = self.db.query(Appointment).filter(
            Appointment.doctor_id == doctor_id,
            Appointment.appointment_date >= preferred_date,
            Appointment.appointment_date <= end_date,
            Appointment.status == "scheduled"
        ).all()

        # Müsait saatleri hesapla
        available_slots = []
        current_date = preferred_date

        while current_date <= end_date:
            # Her gün için 09:00-17:00 arası randevu saatleri
            for hour in range(9, 17):
                slot = current_date.replace(
                    hour=hour, minute=0, second=0, microsecond=0)

                # Eğer slot müsaitse ekle
                if not any(
                    app.appointment_date == slot
                    for app in existing_appointments
                ):
                    available_slots.append(slot)

            current_date += timedelta(days=1)

        return available_slots

    def _calculate_experience(self, created_at: datetime) -> int:
        """Doktorun deneyim süresini hesaplar (yıl olarak)."""
        return (datetime.now() - created_at).days // 365

    def _generate_recommendations(self, patient_id: int, department: str) -> Dict:
        """Hasta için özel öneriler oluşturur."""
        # Hasta geçmişini al
        patient = self.db.query(Patient).filter(
            Patient.id == patient_id).first()
        if not patient:
            return {}

        recommendations = {
            "medical_notes": [],
            "preparation_notes": [],
            "follow_up_notes": []
        }

        # Geçmiş randevuları analiz et
        past_appointments = [
            app for app in patient.appointments
            if app.department == department
        ]

        if past_appointments:
            # Geçmiş tanıları kontrol et
            for app in past_appointments:
                if app.diagnosis:
                    recommendations["medical_notes"].append(
                        f"Previous diagnosis: {app.diagnosis}"
                    )

        # Aktif ilaçları kontrol et
        active_medications = [
            med for med in patient.medications
            if med.is_active
        ]

        if active_medications:
            recommendations["preparation_notes"].append(
                "Please bring your current medications with you"
            )

        # Departmana özel öneriler
        if department == "cardiology":
            recommendations["preparation_notes"].extend([
                "Avoid heavy meals before the appointment",
                "Bring your blood pressure readings if available"
            ])
        elif department == "neurology":
            recommendations["preparation_notes"].extend([
                "Note down any recent episodes or symptoms",
                "Bring any previous MRI/CT scan results"
            ])

        return recommendations
