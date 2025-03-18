// API endpoint
const API_BASE_URL = 'http://localhost:8001/api';

// DOM Elements
const loginSection = document.getElementById('loginSection');
const chatSection = document.getElementById('chatSection');
const chatMessages = document.getElementById('chatMessages');
const userInput = document.getElementById('userInput');
const sendButton = document.getElementById('sendButton');
const tcInput = document.getElementById('tcInput');
const loginButton = document.getElementById('loginButton');
const patientInfo = document.getElementById('patientInfo');
const logoutButton = document.getElementById('logoutButton');

// Chat state
let currentState = 'initial';
let selectedDepartment = null;
let selectedDate = null;
let currentTcNumber = null;
let currentPatient = null;
let selectedDoctor = null;
let inactivityTimer = null;
let currentAppointmentId = null;

// Event Listeners
document.addEventListener('DOMContentLoaded', () => {
    // Login with Enter key
    tcInput.addEventListener('keypress', async (e) => {
        if (e.key === 'Enter') {
            await login();
        }
    });

    // Send message with Enter key
    userInput.addEventListener('keypress', async (e) => {
        if (e.key === 'Enter') {
            await sendMessage();
        }
    });

    // Button click handlers
    loginButton.addEventListener('click', login);
    sendButton.addEventListener('click', sendMessage);
    logoutButton.addEventListener('click', logout);

    // Reset inactivity timer on user activity
    ['mousemove', 'keypress', 'click', 'scroll'].forEach(event => {
        document.addEventListener(event, resetInactivityTimer);
    });
});

// Reset inactivity timer
function resetInactivityTimer() {
    if (inactivityTimer) {
        clearTimeout(inactivityTimer);
    }
    if (currentPatient) {
        inactivityTimer = setTimeout(logout, 5 * 60 * 1000); // 5 minutes
    }
}

// Logout function
function logout() {
    currentPatient = null;
    selectedDepartment = null;
    selectedDoctor = null;
    chatMessages.innerHTML = '';
    loginSection.classList.remove('hidden');
    chatSection.classList.add('hidden');
    tcInput.value = '';
    userInput.value = '';
    if (inactivityTimer) {
        clearTimeout(inactivityTimer);
        inactivityTimer = null;
    }
}

// Display patient info
function displayPatientInfo(patient) {
    const details = document.createElement('div');
    details.innerHTML = `
        <p><strong>Past Conditions:</strong> ${patient.past_conditions.join(', ')}</p>
        <p><strong>Active Medications:</strong></p>
        <ul>
            ${patient.medications
                .filter(med => med.status === 'active')
                .map(med => `<li>${med.name} (${med.dosage}, ${med.frequency})</li>`)
                .join('')}
        </ul>
        <p><strong>Recent Appointments:</strong></p>
        <ul>
            ${patient.past_appointments
                .slice(-2)
                .map(apt => `<li>${apt.date}: ${apt.department} - ${apt.doctor}</li>`)
                .join('')}
        </ul>
    `;
    patientInfo.querySelector('#patientDetails').innerHTML = '';
    patientInfo.querySelector('#patientDetails').appendChild(details);
}

// Handle login
async function login() {
    const tcNumber = tcInput.value.trim();
    if (tcNumber.length !== 11) {
        alert('Please enter a valid 11-digit ID number.');
        return;
    }

    try {
        const response = await fetch(`${API_BASE_URL}/patient/${tcNumber}/history`);
        const data = await response.json();
        
        currentPatient = data;
        currentTcNumber = tcNumber;
        loginSection.classList.add('hidden');
        chatSection.classList.remove('hidden');
        
        // Clear previous messages and show welcome message
        chatMessages.innerHTML = '';
        addMessage(`Hello! I'm your virtual health assistant. Please describe your symptoms so I can help you.`);
        
        // Display patient info if they have any history
        if (currentPatient.past_appointments && currentPatient.past_appointments.length > 0) {
            displayPatientInfo(currentPatient);
        }
        
        // Start inactivity timer
        resetInactivityTimer();
        
    } catch (error) {
        console.error('Login error:', error);
        alert('An error occurred while logging in. Please try again.');
    }
}

// Handle user input
async function sendMessage() {
    const message = userInput.value.trim();
    if (!message) return;

    // Add user message to chat
    addMessage(message, 'user');
    userInput.value = '';

    // Reset inactivity timer
    resetInactivityTimer();

    // Handle appointment states
    if (currentState === 'updating_appointment') {
        const appointmentId = parseInt(message);
        if (isNaN(appointmentId)) {
            addMessage("Please provide a valid Appointment ID number.");
            return;
        }
        currentAppointmentId = appointmentId;
        
        // Find the appointment in patient history
        const appointment = currentPatient.past_appointments.find(apt => apt.id === appointmentId);
        if (!appointment) {
            addMessage("Appointment not found. Please check the ID and try again.");
            return;
        }

        // Get available time slots for the department
        try {
            const response = await fetch(`${API_BASE_URL}/patient/recommend`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    tc_number: currentTcNumber,
                    department: appointment.department,
                    preferred_date: new Date().toISOString().split('T')[0]
                })
            });

            const doctorInfo = await response.json();
            
            if (doctorInfo.available_doctors.length === 0) {
                addMessage("I'm sorry, there are no available doctors at the moment. Please try again later.");
                return;
            }

            addMessage(`Please select a new time slot for your appointment with ${appointment.doctor}:`);
            
            const timeSlots = ['9:00', '10:00', '11:00', '14:00', '15:00', '16:00'];
            const doctorDiv = document.createElement('div');
            doctorDiv.className = 'doctor-slots';
            
            const availableSlots = timeSlots
                .filter(() => Math.random() > 0.5)
                .map(time => {
                    const today = new Date().toISOString().split('T')[0];
                    return `<button onclick="updateAppointmentTime('${today} ${time}')">${time}</button>`;
                })
                .join(' ');
            
            doctorDiv.innerHTML = `
                <p><strong>${appointment.doctor}</strong></p>
                <div class="time-slots">${availableSlots}</div>
            `;
            chatMessages.appendChild(doctorDiv);

        } catch (error) {
            console.error('Error fetching available times:', error);
            addMessage("I'm sorry, I couldn't fetch the available time slots. Please try again.");
        }
        return;
    }

    // Process regular input
    await processUserInput(message);
}

// Process user input
async function processUserInput(message) {
    // Reset department if user is describing new symptoms
    if (message.toLowerCase().includes('symptom')) {
        selectedDepartment = null;
    }

    if (!selectedDepartment) {
        try {
            const response = await fetch(`${API_BASE_URL}/patient/diagnose`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    tc_number: currentTcNumber,
                    symptoms: message,
                    severity: "moderate",
                    duration: "recent"
                })
            });

            const diagnosis = await response.json();
            
            // Display recommendations
            if (diagnosis.warnings && diagnosis.warnings.length > 0) {
                addMessage("⚠️ " + diagnosis.warnings.join('\n'));
            }
            
            if (diagnosis.initial_treatment && diagnosis.initial_treatment.length > 0) {
                addMessage("📋 Initial recommendations:\n" + diagnosis.initial_treatment.join('\n'));
            }

            // Show department options
            addMessage("Based on your symptoms, I recommend the following departments:");
            const deptButtons = diagnosis.recommended_departments
                .map(dept => `<button onclick="selectDepartment('${dept}')">${dept}</button>`)
                .join(' ');
            
            const deptDiv = document.createElement('div');
            deptDiv.className = 'department-buttons';
            deptDiv.innerHTML = deptButtons;
            chatMessages.appendChild(deptDiv);

        } catch (error) {
            console.error('Error processing symptoms:', error);
            addMessage("I'm sorry, I couldn't process your symptoms. Please try again.");
        }
        return;
    }

    // Handle appointment management commands
    if (message.toLowerCase().includes('show appointments') || message.toLowerCase().includes('view appointments')) {
        await showAppointments();
        return;
    }

    if (message.toLowerCase().includes('update appointment')) {
        addMessage("Which appointment would you like to update? Please provide the Appointment ID.");
        currentState = 'updating_appointment';
        return;
    }

    if (message.toLowerCase().includes('cancel appointment')) {
        addMessage("Which appointment would you like to cancel? Please provide the Appointment ID.");
        currentState = 'cancelling_appointment';
        return;
    }
}

// Handle department selection
async function selectDepartment(dept) {
    selectedDepartment = dept;
    addMessage(`You selected ${dept}. Let me check available doctors and their schedules.`);

    try {
        const response = await fetch(`${API_BASE_URL}/patient/recommend`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                tc_number: currentTcNumber,
                department: dept,
                preferred_date: new Date().toISOString().split('T')[0]
            })
        });

        const doctorInfo = await response.json();
        
        if (doctorInfo.available_doctors.length === 0) {
            addMessage("I'm sorry, there are no available doctors at the moment. Please try again later.");
            return;
        }

        addMessage("Here are the available doctors and their next available slots:");
        
        const timeSlots = ['9:00', '10:00', '11:00', '14:00', '15:00', '16:00'];
        doctorInfo.available_doctors.forEach((doctor, index) => {
            const availableSlots = timeSlots
                .filter(() => Math.random() > 0.5)
                .map(time => `<button onclick="bookAppointment(${index}, '${time}')">${time}</button>`)
                .join(' ');
            
            const doctorDiv = document.createElement('div');
            doctorDiv.className = 'doctor-slots';
            doctorDiv.innerHTML = `
                <p><strong>${doctor.name}</strong></p>
                <div class="time-slots">${availableSlots}</div>
            `;
            chatMessages.appendChild(doctorDiv);
        });

    } catch (error) {
        console.error('Doctor recommendation error:', error);
        addMessage("I'm sorry, I couldn't fetch the doctor information. Please try again.");
    }
}

// Handle appointment booking
async function bookAppointment(doctorId, time) {
    const date = new Date().toISOString().split('T')[0];
    
    try {
        const response = await fetch(`${API_BASE_URL}/appointment/create`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                tc_number: currentTcNumber,
                department: selectedDepartment,
                doctor_id: doctorId + 1,
                appointment_date: `${date} ${time}`
            })
        });

        if (!response.ok) {
            throw new Error('Appointment creation failed');
        }

        const result = await response.json();
        
        if (result.success) {
            // Update current patient data with new appointment
            currentPatient.past_appointments.push({
                id: result.appointment_id,
                department: result.department,
                date: result.appointment_date,
                doctor: result.doctor_name
            });
            
            addMessage(`✅ Your appointment has been successfully created:
                \nDoctor: ${result.doctor_name}
                \nDepartment: ${result.department}
                \nDate: ${result.appointment_date}
                \nAppointment ID: ${result.appointment_id}`);
            
            addMessage("Is there anything else I can help you with?");
            
            // Add clickable options
            addClickableOptions([
                { text: "I have other symptoms", message: "I have another symptom to discuss" },
                { text: "View my appointments", action: showAppointments },
                { text: "Update an appointment", message: "update appointment" },
                { text: "Cancel an appointment", message: "cancel appointment" }
            ]);
            
            // Update displayed patient info
            displayPatientInfo(currentPatient);
        } else {
            throw new Error('Appointment creation failed');
        }

    } catch (error) {
        console.error('Booking error:', error);
        addMessage("I'm sorry, I couldn't book the appointment. Please try again.");
    }
}

// Show patient appointments
async function showAppointments() {
    try {
        const response = await fetch(`${API_BASE_URL}/patient/${currentTcNumber}/appointments`);
        const data = await response.json();
        
        if (data.appointments.length === 0) {
            addMessage("You currently have no active appointments.");
            return;
        }

        addMessage("Your appointments:");
        const appointmentsList = data.appointments.map(apt => 
            `ID: ${apt.id}\nDoctor: ${apt.doctor}\nDepartment: ${apt.department}\nDate: ${apt.date}`
        ).join('\n\n');
        
        addMessage(appointmentsList);
        
        addMessage("What would you like to do with your appointments?");
        
        // Add clickable options
        addClickableOptions([
            { text: "Update an appointment", message: "update appointment" },
            { text: "Cancel an appointment", message: "cancel appointment" },
            { text: "Book a new appointment", message: "I have a new symptom to discuss" }
        ]);

    } catch (error) {
        console.error('Error fetching appointments:', error);
        addMessage("I'm sorry, I couldn't retrieve your appointments. Please try again.");
    }
}

// Update appointment with selected time
async function updateAppointmentTime(newDate) {
    try {
        const response = await fetch(`${API_BASE_URL}/appointment/update`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                tc_number: currentTcNumber,
                appointment_id: currentAppointmentId,
                new_date: newDate
            })
        });

        if (!response.ok) {
            throw new Error('Appointment update failed');
        }

        const result = await response.json();
        
        if (result.success) {
            // Update the appointment in currentPatient data
            const appointment = currentPatient.past_appointments.find(apt => apt.id === currentAppointmentId);
            if (appointment) {
                appointment.date = newDate;
            }
            
            addMessage("✅ Your appointment has been successfully updated!");
            await showAppointments();
            
            // Reset state
            currentState = null;
            currentAppointmentId = null;
        } else {
            throw new Error('Appointment update failed');
        }
        
    } catch (error) {
        console.error('Error updating appointment:', error);
        addMessage("I'm sorry, I couldn't update the appointment. Please try again.");
    }
}

// Cancel appointment
async function cancelAppointment(appointmentId) {
    try {
        const response = await fetch(`${API_BASE_URL}/appointment/cancel`, {
            method: 'DELETE',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                tc_number: currentTcNumber,
                appointment_id: appointmentId
            })
        });

        if (!response.ok) {
            throw new Error('Appointment cancellation failed');
        }

        const result = await response.json();
        addMessage("✅ Your appointment has been successfully cancelled!");
        await showAppointments();
        
    } catch (error) {
        console.error('Error cancelling appointment:', error);
        addMessage("I'm sorry, I couldn't cancel the appointment. Please try again.");
    }
}

// Add message to chat
function addMessage(message, sender = 'bot') {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${sender}`;
    messageDiv.textContent = message;
    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// DOM Elements
document.addEventListener('DOMContentLoaded', function() {
    const appointmentForm = document.getElementById('appointmentForm');
    const bookButtons = document.querySelectorAll('.primary-btn');
    const navLinks = document.querySelectorAll('nav a');
    
    // Form Submission
    if (appointmentForm) {
        appointmentForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            // Get form data
            const formData = new FormData(appointmentForm);
            const appointmentData = {};
            
            for (let [key, value] of formData.entries()) {
                appointmentData[key] = value;
            }
            
            // Simulate API call
            simulateAppointmentBooking(appointmentData);
        });
    }
    
    // Book Appointment Button Click
    bookButtons.forEach(button => {
        if (button.textContent.includes('Book Appointment')) {
            button.addEventListener('click', function() {
                const appointmentSection = document.querySelector('.appointment-form');
                if (appointmentSection) {
                    appointmentSection.scrollIntoView({ behavior: 'smooth' });
                }
            });
        }
    });
    
    // Navigation Active State
    navLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            
            // Remove active class from all links
            navLinks.forEach(navLink => {
                navLink.classList.remove('active');
            });
            
            // Add active class to clicked link
            this.classList.add('active');
            
            // If it's a real link, navigate to the page
            // For demo purposes, we're just showing the active state
        });
    });
    
    // Initialize the intelligent referral system
    initializeReferralSystem();
});

// Simulate appointment booking
function simulateAppointmentBooking(data) {
    // Show loading state
    const submitButton = document.querySelector('form .primary-btn');
    const originalText = submitButton.textContent;
    submitButton.textContent = 'Processing...';
    submitButton.disabled = true;
    
    // Simulate API delay
    setTimeout(() => {
        // Analyze appointment data with "AI"
        const response = analyzeAppointmentRequest(data);
        
        // Show success message
        showNotification(response.message, 'success');
        
        // Reset form
        document.getElementById('appointmentForm').reset();
        
        // Reset button
        submitButton.textContent = originalText;
        submitButton.disabled = false;
    }, 1500);
}

// Analyze appointment request (simulated AI logic)
function analyzeAppointmentRequest(data) {
    // This would be where the actual AI logic would go
    // For demo purposes, we're just returning a success message
    
    const doctorName = getRecommendedDoctor(data.department);
    const appointmentDate = new Date(data.date);
    const formattedDate = appointmentDate.toLocaleDateString('en-US', {
        weekday: 'long',
        year: 'numeric',
        month: 'long',
        day: 'numeric'
    });
    
    return {
        success: true,
        message: `Appointment request received! Based on your symptoms, we've matched you with Dr. ${doctorName}. Your appointment is scheduled for ${formattedDate} at ${data.time}. You will receive a confirmation email shortly.`,
        recommendedDoctor: doctorName,
        priority: getPriorityLevel(data.symptoms)
    };
}

// Get recommended doctor based on department (simulated)
function getRecommendedDoctor(department) {
    const doctors = {
        'cardiology': 'Emma Wilson',
        'neurology': 'James Thompson',
        'orthopedics': 'Sarah Miller',
        'pediatrics': 'Robert Johnson',
        'dermatology': 'Lisa Chen',
        'ophthalmology': 'David Kim'
    };
    
    return doctors[department] || 'John Smith';
}

// Get priority level based on symptoms (simulated AI analysis)
function getPriorityLevel(symptoms) {
    // This would be where the actual symptom analysis would happen
    // For demo purposes, we're just checking for keywords
    
    const urgentKeywords = ['severe', 'pain', 'emergency', 'acute', 'critical'];
    const symptomText = symptoms.toLowerCase();
    
    for (const keyword of urgentKeywords) {
        if (symptomText.includes(keyword)) {
            return 'high';
        }
    }
    
    return 'normal';
}

// Show notification
function showNotification(message, type = 'info') {
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.innerHTML = `
        <div class="notification-content">
            <p>${message}</p>
        </div>
        <button class="notification-close">&times;</button>
    `;
    
    // Add to DOM
    document.body.appendChild(notification);
    
    // Add styles
    notification.style.position = 'fixed';
    notification.style.bottom = '20px';
    notification.style.right = '20px';
    notification.style.maxWidth = '400px';
    notification.style.backgroundColor = type === 'success' ? '#34a853' : '#1a73e8';
    notification.style.color = 'white';
    notification.style.padding = '15px 20px';
    notification.style.borderRadius = '8px';
    notification.style.boxShadow = '0 4px 12px rgba(0, 0, 0, 0.15)';
    notification.style.zIndex = '1000';
    notification.style.display = 'flex';
    notification.style.justifyContent = 'space-between';
    notification.style.alignItems = 'center';
    
    // Close button styles
    const closeButton = notification.querySelector('.notification-close');
    closeButton.style.background = 'none';
    closeButton.style.border = 'none';
    closeButton.style.color = 'white';
    closeButton.style.fontSize = '20px';
    closeButton.style.cursor = 'pointer';
    closeButton.style.marginLeft = '10px';
    
    // Add close functionality
    closeButton.addEventListener('click', function() {
        document.body.removeChild(notification);
    });
    
    // Auto remove after 5 seconds
    setTimeout(() => {
        if (document.body.contains(notification)) {
            document.body.removeChild(notification);
        }
    }, 5000);
}

// Initialize the intelligent referral system
function initializeReferralSystem() {
    console.log('Patient Referral Intelligent System initialized');
    // This would be where the actual system initialization would happen
    // For demo purposes, we're just logging a message
}

// Add some additional features for the demo
function addDemoFeatures() {
    // Simulate real-time doctor availability
    setInterval(() => {
        const departments = ['cardiology', 'neurology', 'orthopedics', 'pediatrics', 'dermatology', 'ophthalmology'];
        const randomDept = departments[Math.floor(Math.random() * departments.length)];
        const doctorName = getRecommendedDoctor(randomDept);
        const waitTime = Math.floor(Math.random() * 30) + 5;
        
        console.log(`Current wait time for Dr. ${doctorName} (${randomDept}): ${waitTime} minutes`);
    }, 10000); // Update every 10 seconds
}

// Call demo features in non-production environment
if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
    addDemoFeatures();
}

// Add clickable options to chat
function addClickableOptions(options) {
    const optionsDiv = document.createElement('div');
    optionsDiv.className = 'chat-options';
    
    options.forEach(option => {
        const button = document.createElement('button');
        button.className = 'option-button';
        button.textContent = option.text;
        button.onclick = async () => {
            addMessage(option.message || option.text, 'user');
            if (option.action) {
                await option.action();
            } else {
                await processUserInput(option.message || option.text);
            }
        };
        optionsDiv.appendChild(button);
    });
    
    chatMessages.appendChild(optionsDiv);
}

// Add CSS for new buttons
const style = document.createElement('style');
style.textContent = `
    .chat-options {
        display: flex;
        flex-direction: column;
        gap: 8px;
        margin: 10px 0;
    }
    
    .option-button {
        background-color: #007bff;
        color: white;
        border: none;
        border-radius: 20px;
        padding: 8px 16px;
        cursor: pointer;
        transition: background-color 0.3s;
        text-align: left;
    }
    
    .option-button:hover {
        background-color: #0056b3;
    }
`;
document.head.appendChild(style); 