from transformers import pipeline
from typing import Dict, List
import torch
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


class DiagnosisAgent:
    def __init__(self):
        # Semptom-departman eşleştirme sözlüğü
        self.department_keywords = {
            "cardiology": ["chest pain", "heart", "blood pressure", "palpitations", "shortness of breath"],
            "neurology": ["headache", "dizziness", "seizure", "memory", "numbness", "tremor"],
            "orthopedics": ["joint pain", "fracture", "back pain", "muscle", "bone", "sprain"],
            "pediatrics": ["fever", "cough", "child", "growth", "development", "vaccination"],
            "dermatology": ["rash", "skin", "acne", "allergy", "itching", "dermatitis"],
            "ophthalmology": ["eye", "vision", "glasses", "retina", "cataract", "glaucoma"],
            "ent": ["ear", "nose", "throat", "sinus", "hearing", "taste"],
            "psychiatry": ["anxiety", "depression", "stress", "sleep", "mood", "behavior"],
            "gastroenterology": ["stomach", "digestion", "nausea", "vomiting", "diarrhea", "constipation"],
            "endocrinology": ["diabetes", "thyroid", "hormone", "metabolism", "weight", "growth"]
        }

        # LLM modelini yükle
        self.classifier = pipeline(
            "text-classification",
            model="microsoft/BiomedNLP-PubMedBERT-base-uncased-abstract",
            device=0 if torch.cuda.is_available() else -1
        )

        # TF-IDF vektörizasyonu için
        self.vectorizer = TfidfVectorizer()
        self.department_vectors = None
        self._initialize_vectors()

    def _initialize_vectors(self):
        """Departman anahtar kelimelerini vektörize eder."""
        all_keywords = []
        for keywords in self.department_keywords.values():
            all_keywords.extend(keywords)

        # TF-IDF vektörizasyonu
        self.department_vectors = self.vectorizer.fit_transform(all_keywords)

    async def analyze(self, symptoms: Dict, patient_history: Dict = None) -> Dict:
        """
        Semptomları analiz eder ve olası departmanları belirler.

        Args:
            symptoms (Dict): Hasta semptomları
            patient_history (Dict, optional): Hasta geçmişi

        Returns:
            Dict: Analiz sonuçları
        """
        try:
            # Semptomları birleştir
            all_symptoms = " ".join(symptoms.get(
                "primary", [])) + " " + " ".join(symptoms.get("secondary", []))

            # Semptom vektörünü oluştur
            symptom_vector = self.vectorizer.transform([all_symptoms])

            # Her departman için benzerlik skoru hesapla
            department_scores = {}
            for dept, keywords in self.department_keywords.items():
                dept_vector = self.vectorizer.transform([" ".join(keywords)])
                similarity = cosine_similarity(
                    symptom_vector, dept_vector)[0][0]
                department_scores[dept] = similarity

            # En yüksek skorlu departmanları seç
            recommended_departments = sorted(
                department_scores.items(),
                key=lambda x: x[1],
                reverse=True
            )[:3]

            # Hasta geçmişi varsa, önerileri güncelle
            if patient_history:
                recommended_departments = self._adjust_recommendations(
                    recommended_departments,
                    patient_history
                )

            # Öncelik seviyesini belirle
            priority = self._determine_priority(symptoms)

            return {
                "recommended_departments": [
                    {
                        "department": dept,
                        "confidence": float(score),
                        "reason": self._generate_reason(dept, symptoms)
                    }
                    for dept, score in recommended_departments
                ],
                "priority": priority,
                "symptoms_analysis": {
                    "primary": symptoms.get("primary", []),
                    "secondary": symptoms.get("secondary", []),
                    "duration": symptoms.get("duration", ""),
                    "severity": symptoms.get("severity", "moderate")
                }
            }

        except Exception as e:
            raise Exception(f"Error analyzing symptoms: {str(e)}")

    def _determine_priority(self, symptoms: Dict) -> str:
        """Semptomlara göre öncelik seviyesini belirler."""
        urgent_keywords = ["severe", "emergency",
                           "acute", "critical", "pain", "bleeding"]
        severity = symptoms.get("severity", "moderate").lower()

        if severity == "severe" or any(keyword in str(symptoms).lower() for keyword in urgent_keywords):
            return "high"
        elif severity == "moderate":
            return "medium"
        else:
            return "low"

    def _adjust_recommendations(self, recommendations: List, history: Dict) -> List:
        """Hasta geçmişine göre önerileri günceller."""
        # Geçmiş randevuları analiz et
        past_departments = [app["department"]
                            for app in history.get("appointments", [])]

        # Geçmiş departmanlara göre skorları ayarla
        adjusted_recommendations = []
        for dept, score in recommendations:
            if dept in past_departments:
                # Geçmiş departmanlara bonus puan ver
                score *= 1.2
            adjusted_recommendations.append((dept, score))

        return sorted(adjusted_recommendations, key=lambda x: x[1], reverse=True)

    def _generate_reason(self, department: str, symptoms: Dict) -> str:
        """Departman önerisi için neden oluşturur."""
        primary_symptoms = symptoms.get("primary", [])
        secondary_symptoms = symptoms.get("secondary", [])

        # Departmana özgü anahtar kelimeleri bul
        dept_keywords = self.department_keywords.get(department, [])
        matching_symptoms = []

        for symptom in primary_symptoms + secondary_symptoms:
            if any(keyword in symptom.lower() for keyword in dept_keywords):
                matching_symptoms.append(symptom)

        if matching_symptoms:
            return f"Based on symptoms: {', '.join(matching_symptoms)}"
        else:
            return f"Based on general assessment and department expertise"
