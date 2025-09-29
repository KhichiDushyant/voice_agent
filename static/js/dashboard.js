// Modern Healthcare Dashboard JavaScript

// Global state
let currentView = 'dashboard';
let currentData = {
    patients: [],
    nurses: [],
    appointments: [],
    calls: []
};

// Get CSRF token from the page
function getCSRFToken() {
    const token = document.querySelector('[name=csrfmiddlewaretoken]');
    return token ? token.value : null;
}

// Configuration
const API_BASE = '';
const REFRESH_INTERVAL = 30000;
const CALLS_REFRESH_INTERVAL = 5000; // Refresh calls every 5 seconds for real-time updates
let charts = {};
let callsRefreshInterval;

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
            'nurse-schedule': 'Nurse Schedule & Availability',
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
            case 'nurse-schedule':
                renderNurseSchedule();
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
            fetchAPI('/api/patients/'),
            fetchAPI('/api/nurses/'),
            fetchAPI('/api/appointments/'),
            fetchAPI('/api/calls/')
        ]);
        
        currentData.patients = patientsRes.patients || patientsRes || [];
        currentData.nurses = nursesRes.nurses || nursesRes || [];
        currentData.appointments = appointmentsRes.appointments || appointmentsRes || [];
        currentData.calls = Array.isArray(callsRes) ? callsRes : (callsRes.calls || []);
        
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

// Load calls data separately for real-time updates
async function loadCallsData() {
    try {
        const callsRes = await fetchAPI('/api/calls/');
        currentData.calls = Array.isArray(callsRes) ? callsRes : (callsRes.calls || []);
        
        // Update calls display if currently viewing calls
        if (currentView === 'calls') {
            renderCallsTable();
        }
        
        // Update dashboard cards
        updateRecentCalls();
        updateDashboardStats();
        
    } catch (error) {
        console.error('Error loading calls data:', error);
    }
}

async function fetchAPI(endpoint, options = {}) {
    try {
        const csrfToken = getCSRFToken();
        const headers = {
                'Content-Type': 'application/json',
                ...options.headers
        };
        
        // Add CSRF token for POST, PUT, DELETE requests
        if (options.method && ['POST', 'PUT', 'DELETE', 'PATCH'].includes(options.method.toUpperCase()) && csrfToken) {
            headers['X-CSRFToken'] = csrfToken;
        }
        
        const response = await fetch(API_BASE + endpoint, {
            headers,
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
        .sort((a, b) => new Date(b.start_time) - new Date(a.start_time))
        .slice(0, 5);
    
    if (recentCalls.length === 0) {
        container.innerHTML = '<div class="text-center text-muted p-4">No recent calls</div>';
        return;
    }
    
    const html = recentCalls.map(call => `
        <div class="call-item p-3 border-bottom">
            <div class="d-flex justify-between align-center">
                <div>
                    <strong>${call.patient_name || call.patient_phone}</strong>
                    <br>
                    <small class="text-muted">${call.call_duration ? call.call_duration + ' seconds' : 'N/A'}</small>
                </div>
                <div class="text-right">
                    <span class="badge ${call.call_status === 'completed' ? 'bg-success' : call.call_status === 'failed' ? 'bg-danger' : 'bg-warning'}">
                        ${call.call_status}
                    </span>
                    <br>
                    <small class="text-muted">${formatDateTime(call.start_time)}</small>
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
                    const assignedNurse = patient.assigned_nurse;
                    return `
                        <tr>
                            <td><strong>${patient.name}</strong></td>
                            <td>${patient.phone}</td>
                            <td>${patient.email || 'N/A'}</td>
                            <td>${Array.isArray(patient.medical_conditions) ? patient.medical_conditions.join(', ') : patient.medical_conditions || 'None'}</td>
                            <td>${assignedNurse ? `${assignedNurse.name} (${assignedNurse.specialization})` : 'Unassigned'}</td>
                            <td>
                                <button class="btn btn-sm btn-outline" onclick="editPatient(${patient.id})">Edit</button>
                                <button class="btn btn-sm btn-secondary" onclick="showAssignNurseModal(${patient.id})">Assign Nurse</button>
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
                    const assignedPatients = nurse.patient_assignments_count || 0;
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

// Global variables for call center
let autoRefreshEnabled = false;
let autoRefreshInterval = null;

function renderCallsTable() {
    updateCallStats();
    renderLiveCallFeed();
    renderCallHistoryTable();
}

function updateCallStats() {
    const totalCalls = currentData.calls.length;
    const completedCalls = currentData.calls.filter(call => call.call_status === 'completed').length;
    const failedCalls = currentData.calls.filter(call => call.call_status === 'failed').length;
    
    // Calculate average duration
    const completedCallsWithDuration = currentData.calls.filter(call => 
        call.call_status === 'completed' && call.call_duration
    );
    const avgDuration = completedCallsWithDuration.length > 0 
        ? Math.round(completedCallsWithDuration.reduce((sum, call) => sum + call.call_duration, 0) / completedCallsWithDuration.length)
        : 0;
    
    // Update stats display
    document.getElementById('total-calls').textContent = totalCalls;
    document.getElementById('completed-calls').textContent = completedCalls;
    document.getElementById('failed-calls').textContent = failedCalls;
    document.getElementById('avg-duration').textContent = avgDuration > 0 ? `${Math.floor(avgDuration / 60)}:${(avgDuration % 60).toString().padStart(2, '0')}` : 'N/A';
}

function renderLiveCallFeed() {
    const container = document.getElementById('live-calls-container');
    
    // Get recent calls (last 5)
    const recentCalls = currentData.calls
        .sort((a, b) => new Date(b.start_time) - new Date(a.start_time))
        .slice(0, 5);
    
    if (recentCalls.length === 0) {
        container.innerHTML = '<div class="text-center text-muted p-4">No recent calls</div>';
        return;
    }
    
    const html = recentCalls.map(call => {
        const statusClass = call.call_status === 'completed' ? 'active' : 
                           call.call_status === 'failed' ? 'ended' : 'ringing';
        const duration = call.call_duration ? formatDuration(call.call_duration) : 'N/A';
        const timeAgo = getTimeAgo(call.start_time);
        
        return `
            <div class="live-call-item">
                <div class="call-status-indicator ${statusClass}"></div>
                <div class="call-info">
                    <div class="call-patient">${call.patient_name || 'Unknown Patient'}</div>
                    <div class="call-details">
                        <span>${call.patient_phone}</span>
                        <span class="call-duration">${duration}</span>
                        <span>${timeAgo}</span>
                    </div>
                </div>
            </div>
        `;
    }).join('');
    
    container.innerHTML = html;
}

function renderCallHistoryTable() {
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
                    <th>Patient</th>
                    <th>Phone</th>
                    <th>Duration</th>
                    <th>Status</th>
                    <th>Direction</th>
                    <th>Actions</th>
                </tr>
            </thead>
            <tbody>
                ${currentData.calls.map(call => {
                    return `
                        <tr>
                            <td>${formatDateTime(call.start_time)}</td>
                            <td>${call.patient_name || 'Unknown'}</td>
                            <td>${call.patient_phone}</td>
                            <td>${call.call_duration ? formatDuration(call.call_duration) : 'N/A'}</td>
                            <td>
                                <span class="call-status-badge ${call.call_status}">
                                    ${call.call_status}
                                </span>
                            </td>
                            <td>
                                <span class="call-direction-badge ${call.call_direction}">
                                    ${call.call_direction}
                                </span>
                            </td>
                            <td>
                                <div class="call-actions">
                                    <button class="call-action-btn" onclick="viewCallTranscript(${call.id})">
                                        <i class="fas fa-file-text"></i> Transcript
                                    </button>
                                    <button class="call-action-btn" onclick="viewCallDetails(${call.id})">
                                        <i class="fas fa-info-circle"></i> Details
                                    </button>
                                </div>
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

function formatDuration(seconds) {
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
}

function getTimeAgo(dateString) {
    const now = new Date();
    const callTime = new Date(dateString);
    const diffInSeconds = Math.floor((now - callTime) / 1000);
    
    if (diffInSeconds < 60) return `${diffInSeconds}s ago`;
    if (diffInSeconds < 3600) return `${Math.floor(diffInSeconds / 60)}m ago`;
    if (diffInSeconds < 86400) return `${Math.floor(diffInSeconds / 3600)}h ago`;
    return `${Math.floor(diffInSeconds / 86400)}d ago`;
}

function toggleAutoRefresh() {
    autoRefreshEnabled = !autoRefreshEnabled;
    const button = document.getElementById('auto-refresh-text');
    
    if (autoRefreshEnabled) {
        button.textContent = 'Stop Auto Refresh';
        autoRefreshInterval = setInterval(async () => {
            await loadCallsData();
            renderCallsTable();
        }, 5000); // Refresh every 5 seconds
    } else {
        button.textContent = 'Auto Refresh';
        if (autoRefreshInterval) {
            clearInterval(autoRefreshInterval);
            autoRefreshInterval = null;
        }
    }
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
    const patientsOptions = currentData.patients.map(p => 
        `<option value="${p.id}" data-phone="${p.phone}">${p.name} - ${p.phone}</option>`
    ).join('');
    
    const content = `
        <form onsubmit="handleMakeTestCall(event)">
            <div class="form-group">
                <label class="form-label">Select Patient</label>
                <select class="form-select" name="patient_id" required>
                    <option value="">Choose a patient to call</option>
                    ${patientsOptions}
                </select>
            </div>
            <div class="form-group">
                <input type="text" class="form-input" name="search_patient" placeholder="Or search by name/phone..." onkeyup="filterPatients(this)">
            </div>
            <div class="d-flex justify-between">
                <button type="button" class="btn btn-outline" onclick="closeModal()">Cancel</button>
                <button type="submit" class="btn btn-primary">Make Call</button>
            </div>
        </form>
    `;
    showModal('Make Call', content);
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
    // Refresh all data every 30 seconds
    setInterval(async () => {
        try {
            await loadAllData();
            updateNotificationCount();
        } catch (error) {
            console.error('Real-time update failed:', error);
        }
    }, REFRESH_INTERVAL);
    
    // Refresh calls data more frequently (every 5 seconds) for real-time updates
    callsRefreshInterval = setInterval(async () => {
        try {
            await loadCallsData();
        } catch (error) {
            console.error('Calls refresh failed:', error);
        }
    }, CALLS_REFRESH_INTERVAL);
}

// View call details in a modal
async function viewCallDetails(callId) {
    try {
        showLoading(true);
        const response = await fetchAPI(`/calls/${callId}/details/`);
        
        if (!response || !response.call) {
            throw new Error('Call details not found');
        }
        
        const call = response.call || {};
        const transcript = response.transcript || {};
        const conversation = response.conversation || [];
        
        const content = `
            <div class="call-details">
                <div class="row">
                    <div class="col-md-6">
                        <h5>Call Information</h5>
                        <p><strong>Call ID:</strong> ${call.call_sid || 'N/A'}</p>
                        <p><strong>Patient:</strong> ${call.patient_name || 'Unknown'}</p>
                        <p><strong>Phone:</strong> ${call.patient_phone || 'N/A'}</p>
                        <p><strong>Direction:</strong> ${call.call_direction || 'N/A'}</p>
                        <p><strong>Status:</strong> <span class="badge ${call.call_status === 'completed' ? 'bg-success' : call.call_status === 'failed' ? 'bg-danger' : 'bg-warning'}">${call.call_status || 'Unknown'}</span></p>
                        <p><strong>Duration:</strong> ${call.call_duration ? call.call_duration + ' seconds' : 'N/A'}</p>
                        <p><strong>Start Time:</strong> ${call.start_time ? formatDateTime(call.start_time) : 'N/A'}</p>
                        ${call.end_time ? `<p><strong>End Time:</strong> ${formatDateTime(call.end_time)}</p>` : ''}
                    </div>
                    <div class="col-md-6">
                        <h5>Appointment Information</h5>
                        ${call.appointment_scheduled ? `
                            <p><strong>Nurse:</strong> ${call.nurse_name || 'N/A'}</p>
                            <p><strong>Specialization:</strong> ${call.nurse_specialization || 'N/A'}</p>
                            <p><strong>Appointment Scheduled:</strong> <span class="badge bg-success">Yes</span></p>
                        ` : '<p><span class="badge bg-warning">No appointment scheduled</span></p>'}
                    </div>
                </div>
                
                ${transcript ? `
                    <div class="transcript-section mt-4">
                        <h5>Call Transcript</h5>
                        <div class="transcript-content" style="max-height: 300px; overflow-y: auto; border: 1px solid #ddd; padding: 15px; border-radius: 5px;">
                            ${transcript.full_transcript ? `
                                <div class="full-transcript">
                                    <h6>Full Conversation</h6>
                                    <p>${transcript.full_transcript.replace(/\\n/g, '<br>')}</p>
                                </div>
                            ` : ''}
                            
                            ${transcript.appointment_summary ? `
                                <div class="appointment-summary mt-3">
                                    <h6>Appointment Summary</h6>
                                    <p>${transcript.appointment_summary}</p>
                                </div>
                            ` : ''}
                            
                            ${transcript.scheduling_outcome ? `
                                <div class="scheduling-outcome mt-3">
                                    <h6>Scheduling Outcome</h6>
                                    <span class="badge bg-info">${transcript.scheduling_outcome}</span>
                                </div>
                            ` : ''}
                        </div>
                    </div>
                ` : '<p class="mt-4"><em>No transcript available for this call.</em></p>'}
                
                ${conversation.length > 0 ? `
                    <div class="conversation-section mt-4">
                        <h5>Conversation Log</h5>
                        <div class="conversation-log" style="max-height: 200px; overflow-y: auto; border: 1px solid #ddd; padding: 10px; border-radius: 5px;">
                            ${conversation.map(msg => `
                                <div class="conversation-item mb-2">
                                    <strong>${msg.speaker}:</strong> ${msg.message}
                                    <small class="text-muted">(${formatDateTime(msg.timestamp)})</small>
                                </div>
                            `).join('')}
                        </div>
                    </div>
                ` : ''}
            </div>
        `;
        
        showModal('Call Details', content);
        
    } catch (error) {
        console.error('Error loading call details:', error);
        showToast('Failed to load call details', 'error');
    } finally {
        showLoading(false);
    }
}

// View call transcript in a modal
async function viewCallTranscript(callId) {
    try {
        showLoading(true);
        const response = await fetchAPI(`/calls/${callId}/transcript/`);
        
        if (!response || !response.transcript) {
            throw new Error('Call transcript not found');
        }
        
        const transcript = response.transcript || {};
        
        const content = `
            <div class="transcript-viewer">
                <div class="transcript-header mb-3">
                    <p><strong>Call ID:</strong> ${callId}</p>
                    <p><strong>Generated:</strong> ${transcript.created_at ? formatDateTime(transcript.created_at) : 'N/A'}</p>
                </div>
                
                ${transcript.full_transcript ? `
                    <div class="full-transcript mb-4">
                        <h5>Complete Transcript</h5>
                        <div class="transcript-content" style="max-height: 400px; overflow-y: auto; border: 1px solid #ddd; padding: 15px; border-radius: 5px; background: #f8f9fa;">
                            ${transcript.full_transcript.replace(/\\n/g, '<br>')}
                        </div>
                    </div>
                ` : ''}
                
                <div class="row">
                    ${transcript.patient_transcript ? `
                        <div class="col-md-6">
                            <h6>Patient Transcript</h6>
                            <div class="transcript-section" style="max-height: 200px; overflow-y: auto; border: 1px solid #ddd; padding: 10px; border-radius: 5px;">
                                ${transcript.patient_transcript.replace(/\\n/g, '<br>')}
                            </div>
                        </div>
                    ` : ''}
                    
                    ${transcript.assistant_transcript ? `
                        <div class="col-md-6">
                            <h6>Assistant Transcript</h6>
                            <div class="transcript-section" style="max-height: 200px; overflow-y: auto; border: 1px solid #ddd; padding: 10px; border-radius: 5px;">
                                ${transcript.assistant_transcript.replace(/\\n/g, '<br>')}
                            </div>
                        </div>
                    ` : ''}
                </div>
                
                ${transcript.appointment_summary ? `
                    <div class="appointment-summary mt-4">
                        <h5>Appointment Summary</h5>
                        <div class="summary-content" style="border: 1px solid #ddd; padding: 15px; border-radius: 5px; background: #f0f8ff;">
                            ${transcript.appointment_summary}
                        </div>
                    </div>
                ` : ''}
                
                ${transcript.scheduling_outcome ? `
                    <div class="scheduling-outcome mt-3">
                        <h5>Scheduling Outcome</h5>
                        <span class="badge badge-lg ${transcript.scheduling_outcome === 'scheduled' ? 'bg-success' : 'bg-warning'}">${transcript.scheduling_outcome}</span>
                    </div>
                ` : ''}
            </div>
        `;
        
        showModal('Call Transcript', content);
        
    } catch (error) {
        console.error('Error loading call transcript:', error);
        showToast('Failed to load call transcript', 'error');
    } finally {
        showLoading(false);
    }
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

// CRUD Operations
async function handleAddPatient(event) {
    event.preventDefault();
    showLoading(true);
    
    try {
        const formData = new FormData(event.target);
        const data = {
            name: formData.get('name'),
            phone: formData.get('phone'),
            email: formData.get('email'),
            medical_conditions: formData.get('medical_conditions').split(',').map(c => c.trim()).filter(c => c)
        };
        
        const result = await fetchAPI('/api/patients/', {
            method: 'POST',
            body: JSON.stringify(data)
        });
        
        if (result.success) {
            closeModal();
            await loadAllData();
            renderPatientsTable();
            showToast('Patient added successfully', 'success');
        }
    } catch (error) {
        console.error('Error adding patient:', error);
        showToast('Failed to add patient', 'error');
    } finally {
        showLoading(false);
    }
}

async function handleAddNurse(event) {
    event.preventDefault();
    showLoading(true);
    
    try {
        const formData = new FormData(event.target);
        const data = {
            name: formData.get('name'),
            specialization: formData.get('specialization'),
            phone: formData.get('phone'),
            email: formData.get('email'),
            license_number: formData.get('license_number')
        };
        
        const result = await fetchAPI('/api/nurses/', {
            method: 'POST',
            body: JSON.stringify(data)
        });
        
        if (result.success) {
            closeModal();
            await loadAllData();
            renderNursesTable();
            showToast('Nurse added successfully', 'success');
        }
    } catch (error) {
        console.error('Error adding nurse:', error);
        showToast('Failed to add nurse', 'error');
    } finally {
        showLoading(false);
    }
}

async function handleScheduleAppointment(event) {
    event.preventDefault();
    showLoading(true);
    
    try {
        const formData = new FormData(event.target);
        const datetime = formData.get('date');
        const dateTime = new Date(datetime);
        
        const data = {
            patient_id: formData.get('patient_id'),
            nurse_id: formData.get('nurse_id'),
            appointment_date: dateTime.toISOString().split('T')[0],
            appointment_time: dateTime.toTimeString().split(' ')[0].substring(0, 5),
            duration_minutes: formData.get('duration') || 30,
            appointment_type: formData.get('type') || 'consultation',
            notes: formData.get('notes')
        };
        
        const result = await fetchAPI('/api/appointments/', {
            method: 'POST',
            body: JSON.stringify(data)
        });
        
        if (result.success) {
            closeModal();
            
            // Reload all data to get the latest appointments
            await loadAllData();
            
            // Refresh the appointments view
            renderAppointmentsView();
            
            // Also refresh the nurse schedule view if it's currently visible
            const nurseScheduleView = document.getElementById('nurse-schedule-view');
            if (nurseScheduleView && nurseScheduleView.style.display !== 'none') {
                await loadNurseScheduleData();
                renderScheduleGrid();
                updateAvailabilitySummary();
            }
            
            showToast('Appointment scheduled successfully', 'success');
        } else if (result.error && result.suggested_available_times) {
            // Show error with suggested times
            const suggestedTimes = result.suggested_available_times.join(', ');
            showToast(`Nurse not available at requested time. Available times: ${suggestedTimes}`, 'warning');
            
            // Pre-populate the form with the first available time
            const firstAvailableTime = result.suggested_available_times[0];
            if (firstAvailableTime) {
                const dateInput = document.querySelector('input[name="date"]');
                if (dateInput) {
                    const currentDate = new Date(dateInput.value);
                    const [hours, minutes] = firstAvailableTime.split(':');
                    currentDate.setHours(parseInt(hours), parseInt(minutes), 0, 0);
                    dateInput.value = currentDate.toISOString().slice(0, 16);
                }
            }
        }
    } catch (error) {
        console.error('Error scheduling appointment:', error);
        showToast('Failed to schedule appointment', 'error');
    } finally {
        showLoading(false);
    }
}

function editPatient(id) {
    const patient = currentData.patients.find(p => p.id === id);
    if (!patient) return;
    
    const content = `
        <form onsubmit="handleUpdatePatient(event, ${id})">
            <div class="form-group">
                <label class="form-label">Patient Name</label>
                <input type="text" class="form-input" name="name" value="${patient.name}" required>
            </div>
            <div class="form-group">
                <label class="form-label">Phone Number</label>
                <input type="tel" class="form-input" name="phone" value="${patient.phone}" required>
            </div>
            <div class="form-group">
                <label class="form-label">Email</label>
                <input type="email" class="form-input" name="email" value="${patient.email || ''}">
            </div>
            <div class="form-group">
                <label class="form-label">Medical Conditions</label>
                <textarea class="form-textarea" name="medical_conditions">${Array.isArray(patient.medical_conditions) ? patient.medical_conditions.join(', ') : patient.medical_conditions || ''}</textarea>
            </div>
            <div class="d-flex justify-between">
                <button type="button" class="btn btn-outline" onclick="closeModal()">Cancel</button>
                <button type="submit" class="btn btn-primary">Update Patient</button>
            </div>
        </form>
    `;
    showModal('Edit Patient', content);
}

function editNurse(id) {
    const nurse = currentData.nurses.find(n => n.id === id);
    if (!nurse) return;
    
    const content = `
        <form onsubmit="handleUpdateNurse(event, ${id})">
            <div class="form-group">
                <label class="form-label">Nurse Name</label>
                <input type="text" class="form-input" name="name" value="${nurse.name}" required>
            </div>
            <div class="form-group">
                <label class="form-label">Specialization</label>
                <input type="text" class="form-input" name="specialization" value="${nurse.specialization}" required>
            </div>
            <div class="form-group">
                <label class="form-label">Phone Number</label>
                <input type="tel" class="form-input" name="phone" value="${nurse.phone || ''}">
            </div>
            <div class="form-group">
                <label class="form-label">Email</label>
                <input type="email" class="form-input" name="email" value="${nurse.email || ''}">
            </div>
            <div class="form-group">
                <label class="form-label">License Number</label>
                <input type="text" class="form-input" name="license_number" value="${nurse.license_number || ''}">
            </div>
            <div class="d-flex justify-between">
                <button type="button" class="btn btn-outline" onclick="closeModal()">Cancel</button>
                <button type="submit" class="btn btn-primary">Update Nurse</button>
            </div>
        </form>
    `;
    showModal('Edit Nurse', content);
}

async function handleUpdatePatient(event, patientId) {
    event.preventDefault();
    showLoading(true);
    
    try {
        const formData = new FormData(event.target);
        const data = {
            name: formData.get('name'),
            phone: formData.get('phone'),
            email: formData.get('email'),
            medical_conditions: formData.get('medical_conditions').split(',').map(c => c.trim()).filter(c => c)
        };
        
        const result = await fetchAPI(`/api/patients/${patientId}/`, {
            method: 'PUT',
            body: JSON.stringify(data)
        });
        
        if (result.success) {
            closeModal();
            await loadAllData();
            renderPatientsTable();
            showToast('Patient updated successfully', 'success');
        }
    } catch (error) {
        console.error('Error updating patient:', error);
        showToast('Failed to update patient', 'error');
    } finally {
        showLoading(false);
    }
}

async function handleUpdateNurse(event, nurseId) {
    event.preventDefault();
    showLoading(true);
    
    try {
        const formData = new FormData(event.target);
        const data = {
            name: formData.get('name'),
            specialization: formData.get('specialization'),
            phone: formData.get('phone'),
            email: formData.get('email'),
            license_number: formData.get('license_number')
        };
        
        const result = await fetchAPI(`/api/nurses/${nurseId}/`, {
            method: 'PUT',
            body: JSON.stringify(data)
        });
        
        if (result.success) {
            closeModal();
            await loadAllData();
            renderNursesTable();
            showToast('Nurse updated successfully', 'success');
        }
    } catch (error) {
        console.error('Error updating nurse:', error);
        showToast('Failed to update nurse', 'error');
    } finally {
        showLoading(false);
    }
}

function editAppointment(id) {
    const appointment = currentData.appointments.find(a => a.id === id);
    if (!appointment) return;
    
    const datetime = appointment.appointment_date + 'T' + appointment.appointment_time;
    
    const content = `
        <form onsubmit="handleUpdateAppointment(event, ${id})">
            <div class="form-group">
                <label class="form-label">Date & Time</label>
                <input type="datetime-local" class="form-input" name="datetime" value="${datetime}" required>
            </div>
            <div class="form-group">
                <label class="form-label">Duration (minutes)</label>
                <input type="number" class="form-input" name="duration" value="${appointment.duration_minutes}" required>
            </div>
            <div class="form-group">
                <label class="form-label">Status</label>
                <select class="form-select" name="status">
                    <option value="scheduled" ${appointment.status === 'scheduled' ? 'selected' : ''}>Scheduled</option>
                    <option value="confirmed" ${appointment.status === 'confirmed' ? 'selected' : ''}>Confirmed</option>
                    <option value="completed" ${appointment.status === 'completed' ? 'selected' : ''}>Completed</option>
                    <option value="cancelled" ${appointment.status === 'cancelled' ? 'selected' : ''}>Cancelled</option>
                </select>
            </div>
            <div class="form-group">
                <label class="form-label">Notes</label>
                <textarea class="form-textarea" name="notes">${appointment.notes || ''}</textarea>
            </div>
            <div class="d-flex justify-between">
                <button type="button" class="btn btn-outline" onclick="closeModal()">Cancel</button>
                <button type="submit" class="btn btn-primary">Update Appointment</button>
            </div>
        </form>
    `;
    showModal('Edit Appointment', content);
}

async function handleUpdateAppointment(event, appointmentId) {
    event.preventDefault();
    showLoading(true);
    
    try {
        const formData = new FormData(event.target);
        const datetime = new Date(formData.get('datetime'));
        
        const data = {
            appointment_date: datetime.toISOString().split('T')[0],
            appointment_time: datetime.toTimeString().split(' ')[0].substring(0, 5),
            duration_minutes: formData.get('duration'),
            status: formData.get('status'),
            notes: formData.get('notes')
        };
        
        const result = await fetchAPI(`/api/appointments/${appointmentId}/`, {
            method: 'PUT',
            body: JSON.stringify(data)
        });
        
        if (result.success) {
            closeModal();
            await loadAllData();
            renderAppointmentsView();
            showToast('Appointment updated successfully', 'success');
        }
    } catch (error) {
        console.error('Error updating appointment:', error);
        showToast('Failed to update appointment', 'error');
    } finally {
        showLoading(false);
    }
}

// Nurse-Patient Assignment
function showAssignNurseModal(patientId) {
    const patient = currentData.patients.find(p => p.id === patientId);
    if (!patient) return;
    
    const nursesOptions = currentData.nurses.map(n => 
        `<option value="${n.id}">${n.name} - ${n.specialization}</option>`
    ).join('');
    
    const content = `
        <form onsubmit="handleAssignNurse(event, ${patientId})">
            <div class="form-group">
                <label class="form-label">Patient: ${patient.name}</label>
            </div>
            <div class="form-group">
                <label class="form-label">Select Nurse</label>
                <select class="form-select" name="nurse_id" required>
                    <option value="">Choose a nurse</option>
                    ${nursesOptions}
                </select>
            </div>
            <div class="form-group">
                <label class="form-label">Primary Assignment</label>
                <input type="checkbox" name="is_primary" checked> Make this the primary assignment
            </div>
            <div class="form-group">
                <label class="form-label">Notes</label>
                <textarea class="form-textarea" name="notes"></textarea>
            </div>
            <div class="d-flex justify-between">
                <button type="button" class="btn btn-outline" onclick="closeModal()">Cancel</button>
                <button type="submit" class="btn btn-primary">Assign Nurse</button>
            </div>
        </form>
    `;
    showModal('Assign Nurse to Patient', content);
}

async function handleAssignNurse(event, patientId) {
    event.preventDefault();
    showLoading(true);
    
    try {
        const formData = new FormData(event.target);
        const data = {
            patient_id: patientId,
            nurse_id: formData.get('nurse_id'),
            is_primary: formData.get('is_primary') === 'on',
            notes: formData.get('notes')
        };
        
        const result = await fetchAPI('/api/assign-nurse/', {
            method: 'POST',
            body: JSON.stringify(data)
        });
        
        if (result.success) {
            closeModal();
            await loadAllData();
            renderPatientsTable();
            showToast('Nurse assigned successfully', 'success');
        }
    } catch (error) {
        console.error('Error assigning nurse:', error);
        showToast('Failed to assign nurse', 'error');
    } finally {
        showLoading(false);
    }
}

// Make Test Call

function filterPatients(input) {
    const select = input.closest('form').querySelector('select[name="patient_id"]');
    const searchTerm = input.value.toLowerCase();
    
    Array.from(select.options).forEach(option => {
        if (option.value) {
            const text = option.textContent.toLowerCase();
            option.style.display = text.includes(searchTerm) ? '' : 'none';
        }
    });
}

async function handleMakeTestCall(event) {
    event.preventDefault();
    showLoading(true);
    
    try {
        const formData = new FormData(event.target);
        const patientId = formData.get('patient_id');
        
        if (!patientId) {
            showToast('Please select a patient', 'error');
            return;
        }
        
        const result = await fetchAPI('/api/make-test-call/', {
            method: 'POST',
            body: JSON.stringify({ patient_id: patientId })
        });
        
        if (result.success) {
            closeModal();
            showToast(`Call initiated to ${result.patient_context.name}. OpenAI has context of patient and assigned nurse: ${result.nurse_context.name} (${result.nurse_context.specialization})`, 'success');
            
            // Refresh calls data to show the new call
            setTimeout(async () => {
                await loadCallsData();
                if (currentView === 'calls') {
                    renderCallsTable();
                }
            }, 1000);
        }
    } catch (error) {
        console.error('Error making test call:', error);
        showToast('Failed to make test call', 'error');
    } finally {
        showLoading(false);
    }
}

function quickScheduleAppointment() { showScheduleModal(); }
function quickAddPatient() { showAddPatientModal(); }
function scheduleAppointmentForPatient(id) { 
    const modal = showScheduleModal();
    // Pre-select the patient
    setTimeout(() => {
        const select = document.querySelector('select[name="patient_id"]');
        if (select) select.value = id;
    }, 100);
}
function viewAnalytics() { showView('analytics'); }
// Nurse Schedule Functions
let currentWeekStart = new Date();
currentWeekStart.setDate(currentWeekStart.getDate() - currentWeekStart.getDay() + 1); // Start from Monday

async function renderNurseSchedule() {
    // Ensure currentWeekStart is properly initialized
    initializeCurrentWeek();
    updateWeekDisplay();
    populateNurseFilter();
    
    // Always load fresh data from database
    await loadAllData(); // Load latest appointments
    await loadNurseScheduleData(); // Load nurse availability
    
    renderScheduleGrid();
    updateAvailabilitySummary();
    
    // Also update summary when data changes
    setTimeout(() => {
        updateAvailabilitySummary();
    }, 100);
}

function initializeCurrentWeek() {
    // Set currentWeekStart to the Monday of September 29, 2025 week
    // This ensures we're showing the correct week with the appointment data
    currentWeekStart = new Date(2025, 8, 29); // September 29, 2025 (month is 0-indexed)
    currentWeekStart.setHours(0, 0, 0, 0); // Reset time to start of day
    
}

async function loadNurseScheduleData() {
    try {
        // Use local date formatting to avoid timezone issues
        const weekStart = currentWeekStart.getFullYear() + '-' + 
            String(currentWeekStart.getMonth() + 1).padStart(2, '0') + '-' + 
            String(currentWeekStart.getDate()).padStart(2, '0');
        const response = await fetchAPI(`/nurses/schedules/?week_start=${weekStart}`);
        
        if (response && response.nurses) {
            currentData.nurseSchedules = response.nurses;
        } else {
            currentData.nurseSchedules = [];
        }
    } catch (error) {
        console.error('Error loading nurse schedule data:', error);
        // Fall back to mock data
        currentData.nurseSchedules = [];
    }
}

function updateWeekDisplay() {
    const weekEnd = new Date(currentWeekStart);
    weekEnd.setDate(weekEnd.getDate() + 6);
    
    const options = { month: 'short', day: 'numeric', year: 'numeric' };
    const weekText = `Week of ${currentWeekStart.toLocaleDateString('en-US', options)}`;
    document.getElementById('current-week').textContent = weekText;
}

function populateNurseFilter() {
    const select = document.getElementById('nurse-filter-select');
    const currentValue = select.value;
    
    select.innerHTML = '<option value="">All Nurses</option>';
    
    currentData.nurses.forEach(nurse => {
        const option = document.createElement('option');
        option.value = nurse.id;
        option.textContent = `${nurse.name} - ${nurse.specialization}`;
        select.appendChild(option);
    });
    
    select.value = currentValue;
}

function renderScheduleGrid() {
    const scheduleBody = document.getElementById('schedule-body');
    scheduleBody.innerHTML = '';
    
    // Generate time slots (6 AM to 10 PM)
    const timeSlots = [];
    for (let hour = 6; hour <= 22; hour++) {
        timeSlots.push({
            hour: hour,
            display: hour === 12 ? '12:00 PM' : 
                   hour > 12 ? `${hour - 12}:00 PM` : 
                   `${hour}:00 AM`
        });
    }
    
    timeSlots.forEach(timeSlot => {
        // Time column
        const timeCell = document.createElement('div');
        timeCell.className = 'time-cell';
        timeCell.textContent = timeSlot.display;
        scheduleBody.appendChild(timeCell);
        
        // Day columns
        for (let day = 0; day < 7; day++) {
            const dayCell = document.createElement('div');
            dayCell.className = 'day-cell';
            dayCell.dataset.day = day;
            dayCell.dataset.hour = timeSlot.hour;
            
            // Add availability blocks for this time slot
            addAvailabilityBlocks(dayCell, day, timeSlot.hour);
            
            scheduleBody.appendChild(dayCell);
        }
    });
}

function addAvailabilityBlocks(dayCell, day, hour) {
    const selectedNurseId = document.getElementById('nurse-filter-select').value;
    const nursesToShow = selectedNurseId ? 
        currentData.nurses.filter(n => n.id == selectedNurseId) : 
        currentData.nurses;
    
    nursesToShow.forEach(nurse => {
        const availability = getNurseAvailability(nurse.id, day, hour);
        // Always create a block, even if nurse is not available
        const block = createAvailabilityBlock(nurse, availability, day, hour);
        dayCell.appendChild(block);
    });
}

function getNurseAvailability(nurseId, day, hour) {
    // Always use database data - check appointments first
    const appointment = getNurseAppointment(nurseId, day, hour);
    if (appointment) {
        console.log(`Nurse ${nurseId} has appointment at day ${day}, hour ${hour}:`, appointment);
        return {
            type: 'busy',
            startTime: null,
            endTime: null,
            appointment: appointment
        };
    }
    
    // Check if nurse has regular availability for this day and time
    const nurse = currentData.nurses.find(n => n.id === nurseId);
    if (!nurse) {
        return {
            type: 'unavailable',
            startTime: null,
            endTime: null
        };
    }
    
    const dayNames = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];
    const dayName = dayNames[day];
    
    // ALWAYS use database data - no fallback to defaults
    if (currentData.nurseSchedules && currentData.nurseSchedules.length > 0) {
        const nurseSchedule = currentData.nurseSchedules.find(n => n.id === nurseId);
        
        if (nurseSchedule) {
            // Check regular availability from database
            const regularAvailability = nurseSchedule.availability.find(av => 
                av.day_of_week === dayName && !av.is_override
            );
            
            if (regularAvailability && regularAvailability.is_available) {
                const startHour = parseInt(regularAvailability.start_time.split(':')[0]);
                const endHour = parseInt(regularAvailability.end_time.split(':')[0]);
                
                if (hour >= startHour && hour < endHour) {
                    return {
                        type: 'available',
                        startTime: startHour,
                        endTime: endHour
                    };
                }
            }
            
            // Check for overrides from database
            const targetDate = new Date(currentWeekStart);
            targetDate.setDate(targetDate.getDate() + day);
            const dateStr = targetDate.toISOString().split('T')[0];
            
            const override = nurseSchedule.availability.find(av => 
                av.is_override && av.date === dateStr
            );
            
            if (override) {
                if (override.is_available && override.start_time && override.end_time) {
                    const startHour = parseInt(override.start_time.split(':')[0]);
                    const endHour = parseInt(override.end_time.split(':')[0]);
                    
                    if (hour >= startHour && hour < endHour) {
                        return {
                            type: 'available',
                            startTime: startHour,
                            endTime: endHour
                        };
                    }
                }
                return {
                    type: 'unavailable',
                    startTime: null,
                    endTime: null
                };
            }
            
            // If no availability data found in database, nurse is unavailable
            return {
                type: 'unavailable',
                startTime: null,
                endTime: null
            };
        }
    }
    
    // If no nurse schedule data loaded from database, nurse is unavailable
    return {
        type: 'unavailable',
        startTime: null,
        endTime: null
    };
}

function getMockNurseAvailability(nurseId, day, hour) {
    const nurse = currentData.nurses.find(n => n.id === nurseId);
    if (!nurse) return null;
    
    const dayNames = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];
    const dayName = dayNames[day];
    
    // Mock availability patterns
    const availabilityPatterns = {
        1: { // Alice Wilson - General Care
            'Monday': { start: 8, end: 17 },
            'Tuesday': { start: 8, end: 17 },
            'Wednesday': { start: 8, end: 17 },
            'Thursday': { start: 8, end: 17 },
            'Friday': { start: 8, end: 15 },
            'Saturday': { start: 9, end: 13 },
            'Sunday': null
        },
        2: { // Michael Chen - Cardiology
            'Monday': { start: 7, end: 16 },
            'Tuesday': { start: 7, end: 16 },
            'Wednesday': { start: 7, end: 16 },
            'Thursday': { start: 7, end: 16 },
            'Friday': { start: 7, end: 14 },
            'Saturday': null,
            'Sunday': null
        },
        3: { // Lisa Rodriguez - Pediatrics
            'Monday': { start: 9, end: 18 },
            'Tuesday': { start: 9, end: 18 },
            'Wednesday': { start: 9, end: 18 },
            'Thursday': { start: 9, end: 18 },
            'Friday': { start: 9, end: 16 },
            'Saturday': { start: 10, end: 14 },
            'Sunday': null
        },
        4: { // James Thompson - Geriatrics
            'Monday': { start: 8, end: 16 },
            'Tuesday': { start: 8, end: 16 },
            'Wednesday': { start: 8, end: 16 },
            'Thursday': { start: 8, end: 16 },
            'Friday': { start: 8, end: 15 },
            'Saturday': null,
            'Sunday': null
        },
        5: { // Maria Garcia - Mental Health
            'Monday': { start: 10, end: 19 },
            'Tuesday': { start: 10, end: 19 },
            'Wednesday': { start: 10, end: 19 },
            'Thursday': { start: 10, end: 19 },
            'Friday': { start: 10, end: 17 },
            'Saturday': { start: 11, end: 15 },
            'Sunday': null
        }
    };
    
    const pattern = availabilityPatterns[nurseId];
    if (!pattern || !pattern[dayName]) return null;
    
    const daySchedule = pattern[dayName];
    if (hour >= daySchedule.start && hour < daySchedule.end) {
        // Check for appointments during this time
        const hasAppointment = hasNurseAppointment(nurseId, day, hour);
        return {
            type: hasAppointment ? 'busy' : 'available',
            startTime: daySchedule.start,
            endTime: daySchedule.end
        };
    }
    
    return {
        type: 'unavailable',
        startTime: null,
        endTime: null
    };
}

function getNurseAppointment(nurseId, day, hour) {
    // Check appointments from nurse schedule data (database)
    if (currentData.nurseSchedules && currentData.nurseSchedules.length > 0) {
        const nurseSchedule = currentData.nurseSchedules.find(n => n.id === nurseId);
        if (nurseSchedule && nurseSchedule.appointments) {
            const targetDate = new Date(currentWeekStart);
            targetDate.setDate(targetDate.getDate() + day);
            // Use local date formatting to avoid timezone issues
            const targetDateString = targetDate.getFullYear() + '-' + 
                String(targetDate.getMonth() + 1).padStart(2, '0') + '-' + 
                String(targetDate.getDate()).padStart(2, '0');
            
            
            
            const appointment = nurseSchedule.appointments.find(apt => {
                return apt.date === targetDateString && 
                       apt.time && 
                       parseInt(apt.time.split(':')[0]) === hour;
            });
            
            if (appointment) {
                console.log(`Found appointment:`, appointment);
            }
            
            return appointment || null;
        }
    }
    
    // Fallback to general appointments list if nurse schedule data not available
    const targetDate = new Date(currentWeekStart);
    targetDate.setDate(targetDate.getDate() + day);
    const targetDateString = targetDate.toISOString().split('T')[0]; // YYYY-MM-DD format
    
    const nurse = currentData.nurses.find(n => n.id === nurseId);
    if (!nurse) {
        return null;
    }
    
    const appointment = currentData.appointments.find(apt => {
        return apt.nurse_name === nurse.name && 
               apt.appointment_date === targetDateString && 
               apt.appointment_time && 
               parseInt(apt.appointment_time.split(':')[0]) === hour;
    });
    
    return appointment || null;
}

function hasNurseAppointment(nurseId, day, hour) {
    // Check real appointments data
    const targetDate = new Date(currentWeekStart);
    targetDate.setDate(targetDate.getDate() + day);
    const targetDateString = targetDate.toISOString().split('T')[0]; // YYYY-MM-DD format
    
    const nurse = currentData.nurses.find(n => n.id === nurseId);
    if (!nurse) {
        return false;
    }
    
    const matchingAppointments = currentData.appointments.filter(apt => {
        return apt.nurse_name === nurse.name && 
               apt.appointment_date === targetDateString && 
               apt.appointment_time && 
               parseInt(apt.appointment_time.split(':')[0]) === hour;
    });
    
    return matchingAppointments.length > 0;
}

function createAvailabilityBlock(nurse, availability, day, hour) {
    const block = document.createElement('div');
    
    // Handle case where availability is null (shouldn't happen now, but safety check)
    if (!availability) {
        availability = { type: 'unavailable' };
    }
    
    block.className = `nurse-availability-block availability-${availability.type}`;
    
    // Set content based on availability type
    if (availability.type === 'busy' && availability.appointment) {
        // Show patient name for busy slots
        const patientName = availability.appointment.patient_name || 'Patient';
        block.textContent = patientName.split(' ')[0]; // First name only
    } else {
        // Show nurse name for available/unavailable slots
        block.textContent = nurse.name.split(' ')[0]; // First name only
    }
    
    // Format time for tooltip
    const timeString = hour === 12 ? '12:00 PM' : 
                     hour > 12 ? `${hour - 12}:00 PM` : 
                     `${hour}:00 AM`;
    
    let statusText, tooltipText;
    if (availability.type === 'busy' && availability.appointment) {
        statusText = 'Busy';
        const patientName = availability.appointment.patient_name || 'Patient';
        tooltipText = `${nurse.name} - ${nurse.specialization}\nPatient: ${patientName}\n${statusText} at ${timeString}`;
    } else {
        statusText = availability.type === 'available' ? 'Available' : 'Unavailable';
        tooltipText = `${nurse.name} - ${nurse.specialization}\n${statusText} at ${timeString}`;
    }
    
    block.title = tooltipText;
    
    // Add click handler for more details
    if (availability.type === 'busy') {
        // For busy blocks, show appointment details
        block.addEventListener('click', () => showAppointmentDetails(nurse, day, hour));
    } else {
        // For available/unavailable blocks, show nurse availability details
        block.addEventListener('click', () => showNurseAvailabilityDetails(nurse, availability, day, hour));
    }
    
    return block;
}

function showNurseAvailabilityDetails(nurse, availability, day, hour) {
    const dayNames = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];
    const dayName = dayNames[day];
    
    // Format time properly
    const timeString = hour === 12 ? '12:00 PM' : 
                     hour > 12 ? `${hour - 12}:00 PM` : 
                     `${hour}:00 AM`;
    
    const statusText = availability.type === 'available' ? 'Available' : 
                      availability.type === 'busy' ? 'Busy' : 
                      'Unavailable';
    
    const statusClass = availability.type === 'available' ? 'bg-success' : 
                       availability.type === 'busy' ? 'bg-danger' : 
                       'bg-secondary';
    
    const content = `
        <div class="nurse-details">
            <h4>${nurse.name}</h4>
            <p><strong>Specialization:</strong> ${nurse.specialization}</p>
            <p><strong>Day:</strong> ${dayName}</p>
            <p><strong>Time:</strong> ${timeString}</p>
            <p><strong>Status:</strong> <span class="badge ${statusClass}">${statusText}</span></p>
            <p><strong>Phone:</strong> ${nurse.phone || 'N/A'}</p>
            <p><strong>Email:</strong> ${nurse.email || 'N/A'}</p>
            <div class="mt-3">
                ${availability.type === 'available' ? 
                    `<button class="btn btn-primary btn-sm" onclick="scheduleAppointmentWithNurse(${nurse.id}, ${day}, ${hour})">
                        Schedule Appointment
                    </button>` : 
                    `<button class="btn btn-secondary btn-sm" disabled>
                        Not Available
                    </button>`
                }
            </div>
        </div>
    `;
    
    showModal('Nurse Availability Details', content);
}

function showAppointmentDetails(nurse, day, hour) {
    const dayNames = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];
    const dayName = dayNames[day];
    
    // Find the appointment for this nurse, day, and hour
    const targetDate = new Date(currentWeekStart);
    targetDate.setDate(targetDate.getDate() + day);
    // Use local date formatting to avoid timezone issues
    const targetDateString = targetDate.getFullYear() + '-' + 
        String(targetDate.getMonth() + 1).padStart(2, '0') + '-' + 
        String(targetDate.getDate()).padStart(2, '0');
    
    const appointment = currentData.appointments.find(apt => {
        return apt.nurse_name === nurse.name && 
               apt.appointment_date === targetDateString && 
               apt.appointment_time && 
               parseInt(apt.appointment_time.split(':')[0]) === hour;
    });
    
    if (!appointment) {
        showToast('Appointment details not found', 'error');
        return;
    }
    
    // Format time properly
    const timeString = hour === 12 ? '12:00 PM' : 
                     hour > 12 ? `${hour - 12}:00 PM` : 
                     `${hour}:00 AM`;
    
    const content = `
        <div class="appointment-details">
            <h4><i class="fas fa-calendar-check"></i> Appointment Details</h4>
            <div class="appointment-info">
                <div class="info-row">
                    <strong>Patient:</strong> ${appointment.patient_name}
                </div>
                <div class="info-row">
                    <strong>Phone:</strong> ${appointment.patient_phone}
                </div>
                <div class="info-row">
                    <strong>Nurse:</strong> ${appointment.nurse_name} (${appointment.nurse_specialization})
                </div>
                <div class="info-row">
                    <strong>Date:</strong> ${dayName}, ${targetDate.toLocaleDateString()}
                </div>
                <div class="info-row">
                    <strong>Time:</strong> ${timeString}
                </div>
                <div class="info-row">
                    <strong>Duration:</strong> ${appointment.duration_minutes} minutes
                </div>
                <div class="info-row">
                    <strong>Type:</strong> ${appointment.appointment_type}
                </div>
                <div class="info-row">
                    <strong>Status:</strong> <span class="badge bg-primary">${appointment.status}</span>
                </div>
                ${appointment.notes ? `
                <div class="info-row">
                    <strong>Notes:</strong> ${appointment.notes}
                </div>
                ` : ''}
                <div class="info-row">
                    <strong>Created:</strong> ${new Date(appointment.created_at).toLocaleString()}
                </div>
            </div>
            <div class="mt-3">
                <button class="btn btn-primary btn-sm" onclick="editAppointment(${appointment.id})">
                    <i class="fas fa-edit"></i> Edit Appointment
                </button>
                <button class="btn btn-danger btn-sm ms-2" onclick="deleteAppointment(${appointment.id})">
                    <i class="fas fa-trash"></i> Delete
                </button>
            </div>
        </div>
    `;
    
    showModal('Appointment Details', content);
}

function editAppointment(appointmentId) {
    // TODO: Implement edit appointment functionality
    showToast('Edit appointment functionality coming soon', 'info');
    closeModal();
}

function deleteAppointment(appointmentId) {
    // TODO: Implement delete appointment functionality
    if (confirm('Are you sure you want to delete this appointment?')) {
        showToast('Delete appointment functionality coming soon', 'info');
        closeModal();
    }
}

function scheduleAppointmentWithNurse(nurseId, day, hour) {
    const nurse = currentData.nurses.find(n => n.id === nurseId);
    const dayNames = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];
    const dayName = dayNames[day];
    
    // Pre-populate the schedule modal with nurse and time
    showScheduleModal();
    
    setTimeout(() => {
        const nurseSelect = document.querySelector('select[name="nurse_id"]');
        const dateInput = document.querySelector('input[name="date"]');
        
        if (nurseSelect) nurseSelect.value = nurseId;
        
        if (dateInput) {
            // Use the current week start (which is already set to Monday)
            const targetDate = new Date(currentWeekStart);
            targetDate.setDate(currentWeekStart.getDate() + day);
            targetDate.setHours(hour, 0, 0, 0);
            
            // Format for datetime-local input (YYYY-MM-DDTHH:MM)
            const year = targetDate.getFullYear();
            const month = String(targetDate.getMonth() + 1).padStart(2, '0');
            const dayOfMonth = String(targetDate.getDate()).padStart(2, '0');
            const hours = String(hour).padStart(2, '0');
            const minutes = '00';
            
            dateInput.value = `${year}-${month}-${dayOfMonth}T${hours}:${minutes}`;
        }
    }, 100);
}

async function previousWeek() {
    currentWeekStart.setDate(currentWeekStart.getDate() - 7);
    updateWeekDisplay();
    await loadAllData(); // Load latest appointments
    await loadNurseScheduleData(); // Load nurse availability
    renderScheduleGrid();
    updateAvailabilitySummary();
}

async function nextWeek() {
    currentWeekStart.setDate(currentWeekStart.getDate() + 7);
    updateWeekDisplay();
    await loadAllData(); // Load latest appointments
    await loadNurseScheduleData(); // Load nurse availability
    renderScheduleGrid();
    updateAvailabilitySummary();
}

function filterNurseSchedule() {
    renderScheduleGrid();
}

function updateAvailabilitySummary() {
    // Use nurseSchedules data if available, otherwise fall back to nurses
    const nursesData = currentData.nurseSchedules && currentData.nurseSchedules.length > 0 
        ? currentData.nurseSchedules 
        : currentData.nurses;
    
    const totalNurses = nursesData.length;
    
    // For now, let's show a simplified summary based on the current week view
    // Count available and busy slots for the current week instead of just "today"
    let totalSlots = 0;
    let availableSlots = 0;
    let busySlots = 0;
    
    // Count slots for the current week (Monday to Sunday, 9 AM to 5 PM)
    for (let day = 0; day < 7; day++) {
        for (let hour = 9; hour <= 17; hour++) {
            nursesData.forEach(nurse => {
                totalSlots++;
                const availability = getNurseAvailability(nurse.id, day, hour);
                if (availability) {
                    if (availability.type === 'available') {
                        availableSlots++;
                    } else if (availability.type === 'busy') {
                        busySlots++;
                    }
                }
            });
        }
    }
    
    const coveragePercentage = totalSlots > 0 ? Math.round((availableSlots / totalSlots) * 100) : 0;
    
    // Update the summary display
    const totalNursesEl = document.getElementById('total-nurses');
    const availableTodayEl = document.getElementById('available-today');
    const busyTodayEl = document.getElementById('busy-today');
    const coveragePercentageEl = document.getElementById('coverage-percentage');
    
    if (totalNursesEl) totalNursesEl.textContent = totalNurses;
    if (availableTodayEl) availableTodayEl.textContent = availableSlots;
    if (busyTodayEl) busyTodayEl.textContent = busySlots;
    if (coveragePercentageEl) coveragePercentageEl.textContent = coveragePercentage + '%';
    
    console.log(`Availability Summary: Total Nurses=${totalNurses}, Available Slots=${availableSlots}, Busy Slots=${busySlots}, Coverage=${coveragePercentage}%`);
}

function showAddAvailabilityModal() {
    const nursesOptions = currentData.nurses.map(n => 
        `<option value="${n.id}">${n.name} - ${n.specialization}</option>`
    ).join('');
    
    const content = `
        <form onsubmit="handleAddAvailability(event)">
            <div class="form-group">
                <label class="form-label">Nurse</label>
                <select class="form-select" name="nurse_id" required>
                    <option value="">Select Nurse</option>
                    ${nursesOptions}
                </select>
            </div>
            <div class="form-group">
                <label class="form-label">Day of Week</label>
                <select class="form-select" name="day_of_week" required>
                    <option value="">Select Day</option>
                    <option value="Monday">Monday</option>
                    <option value="Tuesday">Tuesday</option>
                    <option value="Wednesday">Wednesday</option>
                    <option value="Thursday">Thursday</option>
                    <option value="Friday">Friday</option>
                    <option value="Saturday">Saturday</option>
                    <option value="Sunday">Sunday</option>
                </select>
            </div>
            <div class="form-group">
                <label class="form-label">Start Time</label>
                <input type="time" class="form-input" name="start_time" required>
            </div>
            <div class="form-group">
                <label class="form-label">End Time</label>
                <input type="time" class="form-input" name="end_time" required>
            </div>
            <div class="form-group">
                <label class="form-label">Available</label>
                <input type="checkbox" name="is_available" checked> Mark as available
            </div>
            <div class="d-flex justify-between">
                <button type="button" class="btn btn-outline" onclick="closeModal()">Cancel</button>
                <button type="submit" class="btn btn-primary">Add Availability</button>
            </div>
        </form>
    `;
    showModal('Add Nurse Availability', content);
}

async function handleAddAvailability(event) {
    event.preventDefault();
    showLoading(true);
    
    try {
        const formData = new FormData(event.target);
        const data = {
            nurse_id: formData.get('nurse_id'),
            day_of_week: formData.get('day_of_week'),
            start_time: formData.get('start_time'),
            end_time: formData.get('end_time'),
            is_available: formData.get('is_available') === 'on'
        };
        
        // In a real app, this would be an API call
        showToast('Availability added successfully', 'success');
        closeModal();
        
        // Refresh the schedule
        renderScheduleGrid();
        updateAvailabilitySummary();
        
    } catch (error) {
        console.error('Error adding availability:', error);
        showToast('Failed to add availability', 'error');
    } finally {
        showLoading(false);
    }
}

function viewNurseSchedule(id) { 
    showView('nurse-schedule');
    // Filter to specific nurse if ID provided
    if (id) {
        setTimeout(() => {
            document.getElementById('nurse-filter-select').value = id;
            filterNurseSchedule();
        }, 100);
    }
}