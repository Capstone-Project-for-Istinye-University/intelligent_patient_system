from typing import Dict, Any, List
from models.patient import Patient
from database.db_setup import get_db


class RecommendationAgent:
    def __init__(self):
        self.db = get_db()
        self.doctors = {
            "cardiology": [
                {"name": "Dr. Emma Wilson", "experience": 15, "rating": 4.8},
                {"name": "Dr. James Smith", "experience": 12, "rating": 4.6}
            ],
            "neurology": [
                {"name": "Dr. Michael Chen", "experience": 18, "rating": 4.9},
                {"name": "Dr. Sarah Johnson", "experience": 14, "rating": 4.7}
            ],
            "orthopedics": [
                {"name": "Dr. Robert Brown", "experience": 16, "rating": 4.8},
                {"name": "Dr. Lisa Anderson", "experience": 13, "rating": 4.5}
            ],
            "pediatrics": [
                {"name": "Dr. David Kim", "experience": 17, "rating": 4.9},
                {"name": "Dr. Maria Garcia", "experience": 15, "rating": 4.7}
            ],
            "dermatology": [
                {"name": "Dr. Thomas Lee", "experience": 14, "rating": 4.6},
                {"name": "Dr. Jennifer White", "experience": 12, "rating": 4.5}
            ],
            "ophthalmology": [
                {"name": "Dr. William Taylor", "experience": 16, "rating": 4.8},
                {"name": "Dr. Emily Davis", "experience": 13, "rating": 4.6}
            ]
        }

    async def get_recommendation(self, patient_id: str) -> Dict[str, Any]:
        """
        Hasta için en uygun doktoru önerir.

        Args:
            patient_id (str): Hasta ID

        Returns:
            Dict[str, Any]: Doktor önerisi ve detayları
        """
        try:
            # Hasta tanısını al
            diagnosis = await self._get_diagnosis(patient_id)
            if not diagnosis:
                raise ValueError("Hasta tanısı bulunamadı")

            # Önerilen departmanları al
            recommended_departments = diagnosis.get(
                "recommended_departments", [])
            if not recommended_departments:
                raise ValueError("Önerilen departman bulunamadı")

            # Her departman için doktor önerilerini al
            recommendations = []
            for dept in recommended_departments:
                doctors = self._get_doctors_for_department(dept)
                recommendations.extend(doctors)

            # Doktorları skorla ve sırala
            sorted_recommendations = self._score_and_sort_doctors(
                recommendations, diagnosis)

            return {
                "patient_id": patient_id,
                "priority": diagnosis.get("priority", "medium"),
                # En iyi 3 doktoru döndür
                "recommended_doctors": sorted_recommendations[:3],
                "departments": recommended_departments
            }

        except Exception as e:
            raise ValueError(f"Doktor önerisi oluşturulamadı: {str(e)}")

    async def _get_diagnosis(self, patient_id: str) -> Dict[str, Any]:
        """Hasta tanısını veritabanından alır."""
        return await self.db.diagnoses.find_one(
            {"patient_id": patient_id},
            sort=[("timestamp", -1)]  # En son tanıyı al
        )

    def _get_doctors_for_department(self, department: str) -> List[Dict[str, Any]]:
        """Belirli bir departman için doktorları döndürür."""
        return self.doctors.get(department, [])

    def _score_and_sort_doctors(self, doctors: List[Dict[str, Any]], diagnosis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Doktorları deneyim, puan ve önceliğe göre skorlar ve sıralar.
        """
        priority_multiplier = {
            "high": 1.5,
            "medium": 1.2,
            "low": 1.0
        }

        for doctor in doctors:
            # Temel skor hesaplama
            base_score = (doctor["experience"] * 0.4) + \
                (doctor["rating"] * 0.6)

            # Öncelik çarpanını uygula
            priority = diagnosis.get("priority", "medium")
            multiplier = priority_multiplier.get(priority, 1.0)

            # Final skoru hesapla
            doctor["score"] = base_score * multiplier

        # Skora göre sırala
        return sorted(doctors, key=lambda x: x["score"], reverse=True)

    async def _save_recommendation(self, patient_id: str, recommendation: Dict[str, Any]) -> None:
        """Doktor önerisini veritabanına kaydeder."""
        await self.db.recommendations.insert_one({
            "patient_id": patient_id,
            "recommendation": recommendation,
            "timestamp": datetime.utcnow()
        })
