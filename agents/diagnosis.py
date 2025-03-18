from transformers import pipeline


class DiagnosisAgent:
    def __init__(self, agent_id: int):
        self.agent_id = agent_id
        self.llm_model = pipeline(
            "text-generation", model="mistralai/Mistral-7B")

    def analyze_symptoms(self, patient_data: dict):
        symptoms = patient_data.get("symptoms", "")
        prompt = f"Given the symptoms: {symptoms}, what possible conditions could the patient have?"
        response = self.llm_model(prompt, max_length=100)
        return response[0]['generated_text']
