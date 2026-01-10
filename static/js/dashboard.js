// Dashboard JavaScript with JWT Authentication

// Wait for DOM to be ready before checking auth
document.addEventListener('DOMContentLoaded', () => {
    const token = localStorage.getItem('access_token');
    const physicianId = localStorage.getItem('physician_id');
    const physicianName = localStorage.getItem('physician_name');

    console.log('Dashboard loaded. Token:', token ? 'Present' : 'Missing');
    console.log('Physician ID:', physicianId);

    // Check if logged in
    if (!token || !physicianId) {
        console.log('Not authenticated, redirecting to login');
        window.location.href = '/static/index.html';
        return;
    }

    // Set welcome message
    const welcomeElement = document.getElementById('welcomeText');
    if (welcomeElement) {
        welcomeElement.textContent = `Welcome back, ${physicianName}!`;
    }

    // Check user role for UI adjustments
    const userRole = localStorage.getItem('user_role');
    const isStaff = userRole && (userRole.toLowerCase() === 'staff' || userRole.toLowerCase() === 'nurse');

    if (isStaff) {
        const addBtn = document.getElementById('addPatientBtn');
        if (addBtn) addBtn.style.display = 'none'; // Or addBtn.remove()
    }

    // Load patients
    loadPatients();
});

const token = localStorage.getItem('access_token');
const physicianId = localStorage.getItem('physician_id');
const physicianName = localStorage.getItem('physician_name');

async function loadPatients() {
    try {
        const response = await fetch(`/users/${physicianId}/patients`, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });

        if (response.status === 401) {
            // Token expired or invalid
            localStorage.clear();
            window.location.href = '/static/index.html';
            return;
        }

        const patients = await response.json();
        displayPatients(patients);
    } catch (error) {
        console.error('Error loading patients:', error);
        document.getElementById('patientsList').innerHTML =
            '<p style="text-align: center; color: var(--error);">Error loading patients</p>';
    }
}

function displayPatients(patients) {
    const patientsList = document.getElementById('patientsList');

    // Safety check if API returns error object instead of array
    if (!Array.isArray(patients)) {
        console.error("Expected array of patients, got:", patients);
        patientsList.innerHTML = '<p style="text-align: center; color: var(--error);">Error retrieving patient list</p>';
        return;
    }

    const userRole = localStorage.getItem('user_role');
    const isStaff = userRole && (userRole.toLowerCase() === 'staff' || userRole.toLowerCase() === 'nurse');

    if (patients.length === 0) {
        if (isStaff) {
            patientsList.innerHTML =
                '<p style="text-align: center; color: var(--gray-500);">No patients assigned yet.</p>';
        } else {
            patientsList.innerHTML =
                '<p style="text-align: center; color: var(--gray-500);">No patients assigned yet. Add a new patient to get started!</p>';
        }
        return;
    }

    const currentUserId = parseInt(physicianId);

    patientsList.innerHTML = patients.map(patient => {
        const isShared = patient.physician_id !== currentUserId;
        // Simplified badge without emojis
        const sharedBadge = isShared
            ? '<span style="background: var(--accent); color: white; padding: 2px 6px; border-radius: 4px; font-size: 0.7rem; margin-left: 8px;">Shared</span>'
            : '';

        return `
        <div class="patient-item">
            <div class="patient-info">
                <h3>${patient.name} ${sharedBadge}</h3>
                <p>${patient.phone_number}</p>
                <p style="font-size: 0.75rem; color: var(--gray-500);">ID: ${patient.id}</p>
            </div>
            <button class="btn btn-primary" onclick="openPatientRecord(${patient.id})">
                Open Record
                <svg class="btn-icon" width="20" height="20" viewBox="0 0 20 20" fill="none">
                    <path d="M4 10h12m0 0l-4-4m4 4l-4 4" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
                </svg>
            </button>
        </div>
    `}).join('');
}

async function searchPatients() {
    const query = document.getElementById('searchInput').value.trim();

    if (!query) {
        loadPatients();
        return;
    }

    try {
        const response = await fetch(`/users/${physicianId}/patients/search?q=${encodeURIComponent(query)}`, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });

        if (response.status === 401) {
            localStorage.clear();
            window.location.href = '/static/index.html';
            return;
        }

        const patients = await response.json();
        displayPatients(patients);
    } catch (error) {
        console.error('Error searching patients:', error);
    }
}

function showAddPatientModal() {
    document.getElementById('addPatientModal').classList.add('active');
}

function closeAddPatientModal() {
    document.getElementById('addPatientModal').classList.remove('active');
    document.getElementById('addPatientForm').reset();
    document.getElementById('addPatientError').textContent = '';
}

document.getElementById('addPatientForm').addEventListener('submit', async (e) => {
    e.preventDefault();

    const errorDiv = document.getElementById('addPatientError');
    errorDiv.textContent = '';

    const patientData = {
        name: document.getElementById('patientName').value,
        phone_number: document.getElementById('patientPhone').value,
        membership_price: parseFloat(document.getElementById('membershipPrice').value),
        physician_id: parseInt(physicianId)
    };

    try {
        const response = await fetch('/register_patient', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify(patientData)
        });

        if (response.status === 401) {
            localStorage.clear();
            window.location.href = '/static/index.html';
            return;
        }

        if (response.ok) {
            closeAddPatientModal();
            loadPatients(); // Reload patient list
        } else {
            const error = await response.json();
            errorDiv.textContent = error.detail || 'Failed to add patient';
        }
    } catch (error) {
        errorDiv.textContent = 'An error occurred. Please try again.';
        console.error('Add patient error:', error);
    }
});

function openPatientRecord(patientId) {
    window.location.href = `/static/patient-record.html?id=${patientId}`;
}

// Allow search on Enter key
document.getElementById('searchInput').addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
        searchPatients();
    }
});

function logout() {
    localStorage.clear();
    window.location.href = '/static/index.html';
}
