// Modern Healthcare Dashboard JavaScript

// Global state
let currentView = 'dashboard';
let currentData = {
    patients: [],
    nurses: [],
    appointments: [],
    calls: []
};

// Configuration
const API_BASE = '';
const REFRESH_INTERVAL = 30000;
let charts = {};

// Initialize the application
document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
});

async function initializeApp() {
    try {
        showLoading(true);
        
        // Set up navigation
        setupNavigation();
        
        // Load initial data
        await loadAllData();
        
        // Setup real-time updates
        setupRealTimeUpdates();
        
        // Initialize charts
        setupCharts();
        
        // Show dashboard by default
        showView('dashboard');
        
        showLoading(false);
        showToast('System initialized successfully', 'success');
    } catch (error) {
        console.error('Initialization error:', error);
        showToast('Failed to initialize application', 'error');
        showLoading(false);
    }
}

// Navigation Management
function setupNavigation() {
    document.querySelectorAll('.nav-item').forEach(item => {
        if (!item.hasAttribute('target')) {
            item.addEventListener('click', (e) => {
                e.preventDefault();
                const view = item.getAttribute('data-view');
                if (view) {
                    showView(view);
                }
            });
        }
    });
}

function showView(viewName) {
    // Update active nav item
    document.querySelectorAll('.nav-item').forEach(item => {
        item.classList.remove('active');
        if (item.getAttribute('data-view') === viewName) {
            item.classList.add('active');
        }
    });
    
    // Hide all views
    document.querySelectorAll('.view').forEach(view => {
        view.style.display = 'none';
    });
    
    // Show selected view
    const targetView = document.getElementById(`${viewName}-view`);
    if (targetView) {
        targetView.style.display = 'block';
        currentView = viewName;
        
        // Update page title
        const titles = {
            'dashboard': 'Dashboard',
            'patients': 'Patient Management',
            'nurses': 'Nurse Management', 
            'appointments': 'Appointment Management',
            'calls': 'Call History',
            'analytics': 'Analytics & Reports'
        };
        document.getElementById('page-title').textContent = titles[viewName] || viewName;
        
        // Load view-specific data
        switch(viewName) {
            case 'patients':
                renderPatientsTable();
                break;
            case 'nurses':
                renderNursesTable();
                break;
            case 'appointments':
                renderAppointmentsView();
                break;
            case 'calls':
                renderCallsTable();
                break;
            case 'analytics':
                updateCharts();
                break;
        }
    }
}

// Data Loading Functions
async function loadAllData() {
    try {
        const [patientsRes, nursesRes, appointmentsRes, callsRes] = await Promise.all([
            fetchAPI('/patients/'),
            fetchAPI('/nurses/'),
            fetchAPI('/appointments/'),
            fetchAPI('/calls/')
        ]);
        
        currentData.patients = patientsRes || [];
        currentData.nurses = nursesRes || [];
        currentData.appointments = appointmentsRes || [];
        currentData.calls = callsRes || [];
        
        updateDashboardStats();
        updateDashboardCards();
        
    } catch (error) {
        console.error('Error loading data:', error);
        // Use fallback data for demo
        currentData = {
            patients: generateMockPatients(),
            nurses: generateMockNurses(),
            appointments: generateMockAppointments(),
            calls: generateMockCalls()
        };
        updateDashboardStats();
        updateDashboardCards();
    }
}

async function fetchAPI(endpoint, options = {}) {
    try {
        const response = await fetch(API_BASE + endpoint, {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            ...options
        });
        
        if (!response.ok) {
            throw new Error(`API Error: ${response.statusText}`);
        }
        
        return await response.json();
    } catch (error) {
        console.error('API Error:', error);
        throw error;
    }
}

// Dashboard Functions
function updateDashboardStats() {
    const today = new Date().toDateString();
    const todayAppointments = currentData.appointments.filter(apt => 
        new Date(apt.date).toDateString() === today
    );
    
    document.getElementById('patient-count').textContent = currentData.patients.length;
    document.getElementById('nurse-count').textContent = currentData.nurses.length;
    document.getElementById('appointment-count').textContent = todayAppointments.length;
    document.getElementById('call-count').textContent = currentData.calls.length;
}

function updateDashboardCards() {
    updateRecentAppointments();
    updateRecentCalls();
    updateNurseAvailability();
}

function updateRecentAppointments() {
    const container = document.getElementById('recent-appointments');
    const today = new Date();
    const todayAppointments = currentData.appointments
        .filter(apt => new Date(apt.date).toDateString() === today.toDateString())
        .sort((a, b) => new Date(a.date) - new Date(b.date))
        .slice(0, 5);
    
    if (todayAppointments.length === 0) {
        container.innerHTML = '<div class="text-center text-muted p-4">No appointments scheduled for today</div>';
        return;
    }
    
    const html = todayAppointments.map(apt => {
        const patient = currentData.patients.find(p => p.id === apt.patient_id);
        const nurse = currentData.nurses.find(n => n.id === apt.nurse_id);
        return `
            <div class="appointment-item p-3 border-bottom">
                <div class="d-flex justify-between align-center">
                    <div>
                        <strong>${patient?.name || 'Unknown Patient'}</strong>
                        <br>
                        <small class="text-muted">with ${nurse?.name || 'Unknown Nurse'}</small>
                    </div>
                    <div class="text-right">
                        <span class="badge bg-primary">${formatTime(apt.date)}</span>
                    </div>
                </div>
            </div>
        `;
    }).join('');
    
    container.innerHTML = html;
}

function updateRecentCalls() {
    const container = document.getElementById('recent-calls');
    const recentCalls = currentData.calls
        .sort((a, b) => new Date(b.created_at) - new Date(a.created_at))
        .slice(0, 5);
    
    if (recentCalls.length === 0) {
        container.innerHTML = '<div class="text-center text-muted p-4">No recent calls</div>';
        return;
    }
    
    const html = recentCalls.map(call => `
        <div class="call-item p-3 border-bottom">
            <div class="d-flex justify-between align-center">
                <div>
                    <strong>${call.patient_phone}</strong>
                    <br>
                    <small class="text-muted">${call.duration || 'N/A'} seconds</small>
                </div>
                <div class="text-right">
                    <span class="badge ${call.status === 'completed' ? 'bg-success' : 'bg-warning'}">
                        ${call.status}
                    </span>
                    <br>
                    <small class="text-muted">${formatDateTime(call.created_at)}</small>
                </div>
            </div>
        </div>
    `).join('');
    
    container.innerHTML = html;
}

function updateNurseAvailability() {
    const container = document.getElementById('nurse-availability');
    const availableNurses = currentData.nurses.filter(nurse => nurse.is_available !== false);
    
    if (availableNurses.length === 0) {
        container.innerHTML = '<div class="text-center text-muted p-4">No nurses available</div>';
        return;
    }
    
    const html = availableNurses.slice(0, 5).map(nurse => `
        <div class="nurse-item p-3 border-bottom">
            <div class="d-flex justify-between align-center">
                <div>
                    <strong>${nurse.name}</strong>
                    <br>
                    <small class="text-muted">${nurse.specialization}</small>
                </div>
                <div class="text-right">
                    <span class="status-indicator status-online"></span>
                    <span class="text-success">Available</span>
                </div>
            </div>
        </div>
    `).join('');
    
    container.innerHTML = html;
}

// Table Rendering Functions
function renderPatientsTable() {
    const container = document.getElementById('patients-table');
    
    if (currentData.patients.length === 0) {
        container.innerHTML = '<div class="text-center text-muted p-4">No patients found</div>';
        return;
    }
    
    const html = `
        <table>
            <thead>
                <tr>
                    <th>Name</th>
                    <th>Phone</th>
                    <th>Email</th>
                    <th>Medical Conditions</th>
                    <th>Assigned Nurse</th>
                    <th>Actions</th>
                </tr>
            </thead>
            <tbody>
                ${currentData.patients.map(patient => {
                    const assignedNurse = currentData.nurses.find(n => 
                        currentData.appointments.some(a => a.patient_id === patient.id && a.nurse_id === n.id)
                    );
                    return `
                        <tr>
                            <td><strong>${patient.name}</strong></td>
                            <td>${patient.phone}</td>
                            <td>${patient.email || 'N/A'}</td>
                            <td>${Array.isArray(patient.medical_conditions) ? patient.medical_conditions.join(', ') : patient.medical_conditions || 'None'}</td>
                            <td>${assignedNurse?.name || 'Unassigned'}</td>
                            <td>
                                <button class="btn btn-sm btn-outline" onclick="editPatient(${patient.id})">Edit</button>
                                <button class="btn btn-sm btn-primary" onclick="scheduleAppointmentForPatient(${patient.id})">Schedule</button>
                            </td>
                        </tr>
                    `;
                }).join('')}
            </tbody>
        </table>
    `;
    
    container.innerHTML = html;
    setupTableFilters('patient');
}

function renderNursesTable() {
    const container = document.getElementById('nurses-table');
    
    if (currentData.nurses.length === 0) {
        container.innerHTML = '<div class="text-center text-muted p-4">No nurses found</div>';
        return;
    }
    
    const html = `
        <table>
            <thead>
                <tr>
                    <th>Name</th>
                    <th>Specialization</th>
                    <th>Phone</th>
                    <th>Email</th>
                    <th>Status</th>
                    <th>Patients Assigned</th>
                    <th>Actions</th>
                </tr>
            </thead>
            <tbody>
                ${currentData.nurses.map(nurse => {
                    const assignedPatients = currentData.appointments.filter(a => a.nurse_id === nurse.id).length;
                    const isAvailable = nurse.is_available !== false;
                    return `
                        <tr>
                            <td><strong>${nurse.name}</strong></td>
                            <td>${nurse.specialization}</td>
                            <td>${nurse.phone || 'N/A'}</td>
                            <td>${nurse.email || 'N/A'}</td>
                            <td>
                                <span class="status-indicator ${isAvailable ? 'status-online' : 'status-offline'}"></span>
                                ${isAvailable ? 'Available' : 'Busy'}
                            </td>
                            <td>${assignedPatients}</td>
                            <td>
                                <button class="btn btn-sm btn-outline" onclick="editNurse(${nurse.id})">Edit</button>
                                <button class="btn btn-sm btn-secondary" onclick="viewNurseSchedule(${nurse.id})">Schedule</button>
                            </td>
                        </tr>
                    `;
                }).join('')}
            </tbody>
        </table>
    `;
    
    container.innerHTML = html;
    setupTableFilters('nurse');
}

function renderAppointmentsView() {
    renderAppointmentsCalendar();
    renderAppointmentsList();
}

function renderAppointmentsCalendar() {
    const container = document.getElementById('appointments-calendar');
    container.innerHTML = `
        <h4 class="mb-3">Calendar View</h4>
        <div class="calendar-placeholder p-4 text-center bg-secondary rounded">
            <i class="fas fa-calendar-alt fa-3x text-muted mb-3"></i>
            <p class="text-muted">Calendar integration would go here</p>
            <p class="small text-muted">Showing ${currentData.appointments.length} appointments</p>
        </div>
    `;
}

function renderAppointmentsList() {
    const container = document.getElementById('appointments-list');
    const upcomingAppointments = currentData.appointments
        .filter(apt => new Date(apt.date) >= new Date())
        .sort((a, b) => new Date(a.date) - new Date(b.date))
        .slice(0, 10);
    
    if (upcomingAppointments.length === 0) {
        container.innerHTML = '<div class="text-center text-muted p-4">No upcoming appointments</div>';
        return;
    }
    
    const html = `
        <h4 class="mb-3">Upcoming Appointments</h4>
        <div class="appointments-list">
            ${upcomingAppointments.map(apt => {
                const patient = currentData.patients.find(p => p.id === apt.patient_id);
                const nurse = currentData.nurses.find(n => n.id === apt.nurse_id);
                return `
                    <div class="appointment-card p-3 mb-3 border rounded">
                        <div class="d-flex justify-between align-center">
                            <div>
                                <strong>${patient?.name || 'Unknown Patient'}</strong>
                                <br>
                                <small class="text-muted">with ${nurse?.name || 'Unknown Nurse'}</small>
                            </div>
                            <div class="text-right">
                                <strong>${formatDateTime(apt.date)}</strong>
                                <br>
                                <button class="btn btn-sm btn-outline mt-1" onclick="editAppointment(${apt.id})">Edit</button>
                            </div>
                        </div>
                    </div>
                `;
            }).join('')}
        </div>
    `;
    
    container.innerHTML = html;
}

function renderCallsTable() {
    const container = document.getElementById('calls-table');
    
    if (currentData.calls.length === 0) {
        container.innerHTML = '<div class="text-center text-muted p-4">No calls found</div>';
        return;
    }
    
    const html = `
        <table>
            <thead>
                <tr>
                    <th>Date/Time</th>
                    <th>Patient Phone</th>
                    <th>Duration</th>
                    <th>Status</th>
                    <th>Nurse</th>
                    <th>Actions</th>
                </tr>
            </thead>
            <tbody>
                ${currentData.calls.map(call => {
                    const nurse = currentData.nurses.find(n => n.id === call.nurse_id);
                    return `
                        <tr>
                            <td>${formatDateTime(call.created_at)}</td>
                            <td>${call.patient_phone}</td>
                            <td>${call.duration || 'N/A'} sec</td>
                            <td>
                                <span class="badge ${call.status === 'completed' ? 'bg-success' : call.status === 'failed' ? 'bg-danger' : 'bg-warning'}">
                                    ${call.status}
                                </span>
                            </td>
                            <td>${nurse?.name || 'N/A'}</td>
                            <td>
                                <button class="btn btn-sm btn-outline" onclick="viewCallTranscript(${call.id})">Transcript</button>
                            </td>
                        </tr>
                    `;
                }).join('')}
            </tbody>
        </table>
    `;
    
    container.innerHTML = html;
    setupTableFilters('calls');
}

// Modal Functions
function showModal(title, content) {
    document.getElementById('modal-title').textContent = title;
    document.getElementById('modal-body').innerHTML = content;
    document.getElementById('modal-overlay').style.display = 'flex';
}

function closeModal() {
    document.getElementById('modal-overlay').style.display = 'none';
}

function showAddPatientModal() {
    const content = `
        <form onsubmit="handleAddPatient(event)">
            <div class="form-group">
                <label class="form-label">Patient Name</label>
                <input type="text" class="form-input" name="name" required>
            </div>
            <div class="form-group">
                <label class="form-label">Phone Number</label>
                <input type="tel" class="form-input" name="phone" required>
            </div>
            <div class="form-group">
                <label class="form-label">Email</label>
                <input type="email" class="form-input" name="email">
            </div>
            <div class="form-group">
                <label class="form-label">Medical Conditions</label>
                <textarea class="form-textarea" name="medical_conditions" placeholder="Enter medical conditions, separated by commas"></textarea>
            </div>
            <div class="d-flex justify-between">
                <button type="button" class="btn btn-outline" onclick="closeModal()">Cancel</button>
                <button type="submit" class="btn btn-primary">Add Patient</button>
            </div>
        </form>
    `;
    showModal('Add New Patient', content);
}

function showAddNurseModal() {
    const content = `
        <form onsubmit="handleAddNurse(event)">
            <div class="form-group">
                <label class="form-label">Nurse Name</label>
                <input type="text" class="form-input" name="name" required>
            </div>
            <div class="form-group">
                <label class="form-label">Specialization</label>
                <input type="text" class="form-input" name="specialization" required>
            </div>
            <div class="form-group">
                <label class="form-label">Phone Number</label>
                <input type="tel" class="form-input" name="phone">
            </div>
            <div class="form-group">
                <label class="form-label">Email</label>
                <input type="email" class="form-input" name="email">
            </div>
            <div class="form-group">
                <label class="form-label">License Number</label>
                <input type="text" class="form-input" name="license_number">
            </div>
            <div class="d-flex justify-between">
                <button type="button" class="btn btn-outline" onclick="closeModal()">Cancel</button>
                <button type="submit" class="btn btn-primary">Add Nurse</button>
            </div>
        </form>
    `;
    showModal('Add New Nurse', content);
}

function showScheduleModal() {
    const patientsOptions = currentData.patients.map(p => 
        `<option value="${p.id}">${p.name}</option>`
    ).join('');
    
    const nursesOptions = currentData.nurses.map(n => 
        `<option value="${n.id}">${n.name} - ${n.specialization}</option>`
    ).join('');
    
    const content = `
        <form onsubmit="handleScheduleAppointment(event)">
            <div class="form-group">
                <label class="form-label">Patient</label>
                <select class="form-select" name="patient_id" required>
                    <option value="">Select Patient</option>
                    ${patientsOptions}
                </select>
            </div>
            <div class="form-group">
                <label class="form-label">Nurse</label>
                <select class="form-select" name="nurse_id" required>
                    <option value="">Select Nurse</option>
                    ${nursesOptions}
                </select>
            </div>
            <div class="form-group">
                <label class="form-label">Date & Time</label>
                <input type="datetime-local" class="form-input" name="date" required>
            </div>
            <div class="form-group">
                <label class="form-label">Notes</label>
                <textarea class="form-textarea" name="notes" placeholder="Optional appointment notes"></textarea>
            </div>
            <div class="d-flex justify-between">
                <button type="button" class="btn btn-outline" onclick="closeModal()">Cancel</button>
                <button type="submit" class="btn btn-primary">Schedule Appointment</button>
            </div>
        </form>
    `;
    showModal('Schedule New Appointment', content);
}

// Form Handlers
async function handleAddPatient(event) {
    event.preventDefault();
    const formData = new FormData(event.target);
    const patientData = {
        name: formData.get('name'),
        phone: formData.get('phone'),
        email: formData.get('email'),
        medical_conditions: formData.get('medical_conditions').split(',').map(c => c.trim()).filter(c => c)
    };
    
    try {
        showLoading(true);
        // In a real app, this would be an API call
        const newId = Math.max(...currentData.patients.map(p => p.id), 0) + 1;
        currentData.patients.push({...patientData, id: newId});
        
        closeModal();
        showToast('Patient added successfully', 'success');
        updateDashboardStats();
        if (currentView === 'patients') {
            renderPatientsTable();
        }
        showLoading(false);
    } catch (error) {
        showToast('Failed to add patient', 'error');
        showLoading(false);
    }
}

async function handleAddNurse(event) {
    event.preventDefault();
    const formData = new FormData(event.target);
    const nurseData = {
        name: formData.get('name'),
        specialization: formData.get('specialization'),
        phone: formData.get('phone'),
        email: formData.get('email'),
        license_number: formData.get('license_number'),
        is_available: true
    };
    
    try {
        showLoading(true);
        const newId = Math.max(...currentData.nurses.map(n => n.id), 0) + 1;
        currentData.nurses.push({...nurseData, id: newId});
        
        closeModal();
        showToast('Nurse added successfully', 'success');
        updateDashboardStats();
        if (currentView === 'nurses') {
            renderNursesTable();
        }
        showLoading(false);
    } catch (error) {
        showToast('Failed to add nurse', 'error');
        showLoading(false);
    }
}

async function handleScheduleAppointment(event) {
    event.preventDefault();
    const formData = new FormData(event.target);
    const appointmentData = {
        patient_id: parseInt(formData.get('patient_id')),
        nurse_id: parseInt(formData.get('nurse_id')),
        date: formData.get('date'),
        notes: formData.get('notes'),
        status: 'scheduled'
    };
    
    try {
        showLoading(true);
        const newId = Math.max(...currentData.appointments.map(a => a.id), 0) + 1;
        currentData.appointments.push({...appointmentData, id: newId});
        
        closeModal();
        showToast('Appointment scheduled successfully', 'success');
        updateDashboardStats();
        updateDashboardCards();
        if (currentView === 'appointments') {
            renderAppointmentsView();
        }
        showLoading(false);
    } catch (error) {
        showToast('Failed to schedule appointment', 'error');
        showLoading(false);
    }
}

// Quick Action Functions
function quickScheduleAppointment() {
    showScheduleModal();
}

function quickAddPatient() {
    showAddPatientModal();
}

async function makeTestCall() {
    const phoneNumber = prompt('Enter phone number to call (e.g., +1234567890):');
    if (!phoneNumber) return;
    
    try {
        showLoading(true);
        showToast('Initiating test call...', 'info');
        
        // Simulate API call
        await new Promise(resolve => setTimeout(resolve, 2000));
        
        // Add mock call to data
        const newCall = {
            id: Math.max(...currentData.calls.map(c => c.id), 0) + 1,
            patient_phone: phoneNumber,
            status: 'completed',
            duration: Math.floor(Math.random() * 120) + 30,
            created_at: new Date().toISOString(),
            nurse_id: currentData.nurses[0]?.id
        };
        
        currentData.calls.unshift(newCall);
        updateDashboardStats();
        updateDashboardCards();
        
        showToast('Test call completed successfully', 'success');
        showLoading(false);
        
    } catch (error) {
        showToast('Failed to make test call', 'error');
        showLoading(false);
    }
}

function viewAnalytics() {
    showView('analytics');
}

// Utility Functions
function showLoading(show) {
    document.getElementById('loading-overlay').style.display = show ? 'flex' : 'none';
}

function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = `
        <div class="d-flex justify-between align-center">
            <span>${message}</span>
            <button onclick="this.parentElement.parentElement.remove()" class="btn btn-sm" style="padding: 0; margin-left: 1rem;">&times;</button>
        </div>
    `;
    
    document.getElementById('toast-container').appendChild(toast);
    
    setTimeout(() => {
        if (toast.parentElement) {
            toast.remove();
        }
    }, 5000);
}

function formatDateTime(dateString) {
    if (!dateString) return 'N/A';
    const date = new Date(dateString);
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
}

function formatTime(dateString) {
    if (!dateString) return 'N/A';
    const date = new Date(dateString);
    return date.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
}

function setupTableFilters(type) {
    const searchInput = document.getElementById(`${type}-search`);
    const filterSelect = document.getElementById(`${type}-filter`);
    
    if (searchInput) {
        searchInput.addEventListener('input', () => filterTable(type));
    }
    
    if (filterSelect) {
        filterSelect.addEventListener('change', () => filterTable(type));
    }
}

function filterTable(type) {
    // Basic filtering logic - would be enhanced in a real application
    const searchValue = document.getElementById(`${type}-search`)?.value.toLowerCase() || '';
    const filterValue = document.getElementById(`${type}-filter`)?.value || '';
    
    // Re-render the table with filters applied
    switch(type) {
        case 'patient':
            renderPatientsTable();
            break;
        case 'nurse':
            renderNursesTable();
            break;
        case 'calls':
            renderCallsTable();
            break;
    }
}

// Chart Setup and Updates
function setupCharts() {
    if (typeof Chart === 'undefined') {
        console.log('Chart.js not loaded, skipping chart initialization');
        return;
    }
    
    // Initialize charts when analytics view is shown
    const appointmentsCtx = document.getElementById('appointments-chart');
    const callsCtx = document.getElementById('calls-chart');
    const patientsCtx = document.getElementById('patients-chart');
    const nursesCtx = document.getElementById('nurses-chart');
    
    if (appointmentsCtx) {
        charts.appointments = new Chart(appointmentsCtx, {
            type: 'line',
            data: {
                labels: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
                datasets: [{
                    label: 'Appointments',
                    data: [12, 19, 8, 15, 22, 8, 5],
                    borderColor: '#2563eb',
                    backgroundColor: 'rgba(37, 99, 235, 0.1)'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false
            }
        });
    }
    
    if (callsCtx) {
        charts.calls = new Chart(callsCtx, {
            type: 'doughnut',
            data: {
                labels: ['Successful', 'Failed', 'In Progress'],
                datasets: [{
                    data: [85, 10, 5],
                    backgroundColor: ['#10b981', '#ef4444', '#f59e0b']
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false
            }
        });
    }
}

function updateCharts() {
    // Update chart data based on current data
    // This would be implemented based on actual data analysis needs
}

// Real-time Updates
function setupRealTimeUpdates() {
    // Refresh data every 30 seconds
    setInterval(async () => {
        try {
            await loadAllData();
            updateNotificationCount();
        } catch (error) {
            console.error('Real-time update failed:', error);
        }
    }, REFRESH_INTERVAL);
}

function updateNotificationCount() {
    // Calculate notifications (new appointments, urgent calls, etc.)
    const notifications = 0; // Calculate based on new data
    document.getElementById('notification-count').textContent = notifications;
}

// Mock Data Generators (for demo purposes)
function generateMockPatients() {
    return [
        { id: 1, name: 'John Smith', phone: '+1234567890', email: 'john@example.com', medical_conditions: ['Diabetes', 'Hypertension'] },
        { id: 2, name: 'Sarah Johnson', phone: '+1234567891', email: 'sarah@example.com', medical_conditions: ['Asthma', 'Allergies'] },
        { id: 3, name: 'Robert Brown', phone: '+1234567892', email: 'robert@example.com', medical_conditions: ['Heart Disease', 'Arthritis'] },
        { id: 4, name: 'Emily Davis', phone: '+1234567893', email: 'emily@example.com', medical_conditions: ['Anxiety', 'Depression'] }
    ];
}

function generateMockNurses() {
    return [
        { id: 1, name: 'Dr. Alice Wilson', specialization: 'General Care', phone: '+1234567900', email: 'alice@carematix.com', is_available: true },
        { id: 2, name: 'Dr. Michael Chen', specialization: 'Cardiology', phone: '+1234567901', email: 'michael@carematix.com', is_available: true },
        { id: 3, name: 'Dr. Lisa Rodriguez', specialization: 'Pediatrics', phone: '+1234567902', email: 'lisa@carematix.com', is_available: true },
        { id: 4, name: 'Dr. James Thompson', specialization: 'Geriatrics', phone: '+1234567903', email: 'james@carematix.com', is_available: false },
        { id: 5, name: 'Dr. Maria Garcia', specialization: 'Mental Health', phone: '+1234567904', email: 'maria@carematix.com', is_available: true }
    ];
}

function generateMockAppointments() {
    const today = new Date();
    const tomorrow = new Date(today);
    tomorrow.setDate(tomorrow.getDate() + 1);
    
    return [
        { id: 1, patient_id: 1, nurse_id: 1, date: today.toISOString(), status: 'scheduled', notes: 'Regular checkup' },
        { id: 2, patient_id: 2, nurse_id: 3, date: tomorrow.toISOString(), status: 'scheduled', notes: 'Follow-up visit' },
        { id: 3, patient_id: 3, nurse_id: 2, date: new Date(today.getTime() + 2*24*60*60*1000).toISOString(), status: 'scheduled', notes: 'Cardiology consultation' },
        { id: 4, patient_id: 4, nurse_id: 5, date: new Date(today.getTime() + 3*24*60*60*1000).toISOString(), status: 'scheduled', notes: 'Mental health session' }
    ];
}

function generateMockCalls() {
    return [
        { id: 1, patient_phone: '+1234567890', status: 'completed', duration: 120, created_at: new Date().toISOString(), nurse_id: 1 },
        { id: 2, patient_phone: '+1234567891', status: 'completed', duration: 95, created_at: new Date(Date.now() - 3600000).toISOString(), nurse_id: 3 },
        { id: 3, patient_phone: '+1234567892', status: 'failed', duration: null, created_at: new Date(Date.now() - 7200000).toISOString(), nurse_id: 2 }
    ];
}

// Edit Functions (stubs for future implementation)
function editPatient(id) { showToast('Edit patient functionality coming soon', 'info'); }
function editNurse(id) { showToast('Edit nurse functionality coming soon', 'info'); }
function editAppointment(id) { showToast('Edit appointment functionality coming soon', 'info'); }
function scheduleAppointmentForPatient(id) { showScheduleModal(); }
function viewNurseSchedule(id) { showToast('Nurse schedule view coming soon', 'info'); }
function viewCallTranscript(id) { showToast('Call transcript view coming soon', 'info'); }