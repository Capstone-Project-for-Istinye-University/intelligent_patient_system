from sqlalchemy import Column, Integer, String, DateTime, JSON, ForeignKey, Table, Boolean
from sqlalchemy.orm import relationship
from database.db_setup import Base
from datetime import datetime

# Hasta-İlaç ilişki tablosu
patient_medications = Table(
    'patient_medications',
    Base.metadata,
    Column('patient_id', Integer, ForeignKey('patients.id')),
    Column('medication_id', Integer, ForeignKey('medications.id'))
)


class Patient(Base):
    __tablename__ = "patients"

    id = Column(Integer, primary_key=True, index=True)
    tc_number = Column(String, unique=True, index=True)
    name = Column(String, index=True)
    email = Column(String, unique=True, index=True)
    phone = Column(String)
    date_of_birth = Column(DateTime)
    gender = Column(String)
    address = Column(String)
    emergency_contact = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow,
                        onupdate=datetime.utcnow)

    # İlişkiler
    appointments = relationship("Appointment", back_populates="patient")
    medical_history = relationship("MedicalHistory", back_populates="patient")
    medications = relationship(
        "Medication", secondary=patient_medications, back_populates="patients")


class Appointment(Base):
    __tablename__ = "appointments"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"))
    doctor_id = Column(Integer, ForeignKey("doctors.id"))
    department = Column(String)
    appointment_date = Column(DateTime)
    status = Column(String)  # scheduled, completed, cancelled
    symptoms = Column(JSON)
    diagnosis = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow,
                        onupdate=datetime.utcnow)

    # İlişkiler
    patient = relationship("Patient", back_populates="appointments")
    doctor = relationship("Doctor", back_populates="appointments")


class MedicalHistory(Base):
    __tablename__ = "medical_history"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"))
    condition = Column(String)
    diagnosis_date = Column(DateTime)
    treatment = Column(String)
    notes = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

    # İlişkiler
    patient = relationship("Patient", back_populates="medical_history")


class Medication(Base):
    __tablename__ = "medications"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    dosage = Column(String)
    frequency = Column(String)
    start_date = Column(DateTime)
    end_date = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # İlişkiler
    patients = relationship(
        "Patient", secondary=patient_medications, back_populates="medications")


class Doctor(Base):
    __tablename__ = "doctors"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    department = Column(String)
    specialization = Column(String)
    email = Column(String, unique=True)
    phone = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

    # İlişkiler
    appointments = relationship("Appointment", back_populates="doctor")
