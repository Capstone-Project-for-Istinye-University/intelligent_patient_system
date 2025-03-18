from models.patient import Patient


class PatientIntakeAgent:
    def __init__(self, agent_id: int):
        self.agent_id = agent_id
        self.patient_data = {}

    def collect_data(self, patient: Patient):
        self.patient_data = {
            "id": patient.id,
            "name": patient.name,
            "age": patient.age,
            "symptoms": patient.symptoms,
            "medical_history": patient.medical_history
        }
        return self.patient_data
