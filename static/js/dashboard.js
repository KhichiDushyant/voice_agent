// Dashboard JavaScript for Carematix AI Voice Assistant

// Load dashboard statistics
async function loadStats() {
    try {
        const [patientsRes, nursesRes, appointmentsRes, callsRes] = await Promise.all([
            fetch('/patients/'),
            fetch('/nurses/'),
            fetch('/appointments/'),
            fetch('/calls/')
        ]);
        
        const patients = await patientsRes.json();
        const nurses = await nursesRes.json();
        const appointments = await appointmentsRes.json();
        const calls = await callsRes.json();
        
        document.getElementById('patient-count').textContent = patients.length;
        document.getElementById('nurse-count').textContent = nurses.length;
        document.getElementById('appointment-count').textContent = appointments.length;
        document.getElementById('call-count').textContent = calls.length;
    } catch (error) {
        console.error('Error loading stats:', error);
    }
}

// Action functions
function makeTestCall() {
    const phoneNumber = prompt('Enter phone number to call (e.g., +1234567890):');
    if (phoneNumber) {
        fetch('/make-call/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ phone_number: phoneNumber })
        })
        .then(response => response.json())
        .then(data => {
            if (data.message) {
                alert('Call initiated: ' + data.message);
            } else {
                alert('Error: ' + (data.error || 'Unknown error'));
            }
        })
        .catch(error => {
            alert('Error making call: ' + error.message);
        });
    }
}

function viewCallHistory() {
    window.open('/calls/', '_blank');
}

function viewPatients() {
    window.open('/admin/carematix_app/patient/', '_blank');
}

function addPatient() {
    const name = prompt('Enter patient name:');
    const phone = prompt('Enter patient phone:');
    if (name && phone) {
        fetch('/patients/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ 
                name: name, 
                phone: phone,
                email: '',
                medical_conditions: []
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                alert('Patient added successfully!');
                loadStats();
            } else {
                alert('Error: ' + (data.error || 'Unknown error'));
            }
        })
        .catch(error => {
            alert('Error adding patient: ' + error.message);
        });
    }
}

function viewNurses() {
    window.open('/admin/carematix_app/nurse/', '_blank');
}

function addNurse() {
    const name = prompt('Enter nurse name:');
    const specialization = prompt('Enter specialization:');
    if (name && specialization) {
        fetch('/nurses/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ 
                name: name, 
                specialization: specialization,
                phone: '',
                email: '',
                license_number: ''
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                alert('Nurse added successfully!');
                loadStats();
            } else {
                alert('Error: ' + (data.error || 'Unknown error'));
            }
        })
        .catch(error => {
            alert('Error adding nurse: ' + error.message);
        });
    }
}

function viewAppointments() {
    window.open('/admin/carematix_app/appointment/', '_blank');
}

function scheduleAppointment() {
    window.open('/admin/carematix_app/appointment/add/', '_blank');
}

// Load stats on page load
document.addEventListener('DOMContentLoaded', function() {
    loadStats();
    
    // Refresh stats every 30 seconds
    setInterval(loadStats, 30000);
});
