// Patient Record JavaScript with JWT Authentication
const urlParams = new URLSearchParams(window.location.search);
const patientId = urlParams.get('id');
const token = localStorage.getItem('access_token');
const physicianId = localStorage.getItem('physician_id'); // Actually User ID now

if (!patientId || !physicianId || !token) {
    window.location.href = '/static/dashboard.html';
}

let vitalsChart = null;

// Load patient data
window.addEventListener('DOMContentLoaded', () => {
    loadPatientInfo();
    loadNotes();
    loadVitals();
});

async function loadPatientInfo() {
    try {
        const response = await fetch(`/patients/${patientId}`, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });

        if (response.status === 401) {
            localStorage.clear();
            window.location.href = '/static/index.html';
            return;
        }

        const patient = await response.json();

        document.getElementById('patientName').textContent = patient.name;
        document.getElementById('patientId').textContent = `ID: ${patient.id}`;

        // Populate Overview
        document.getElementById('overviewPhone').textContent = patient.phone_number || '-';
        document.getElementById('overviewPrice').textContent = patient.membership_price ? `₹${patient.membership_price}` : '-';

        // Permission Logic
        // Permission Logic
        const userRole = localStorage.getItem('user_role');
        const isStaff = userRole && (userRole.toLowerCase() === 'staff' || userRole.toLowerCase() === 'nurse');

        // Hide "Share" if Staff
        // User requested to keep it for Physicians (even if shared/non-owner, though backend might block)
        if (isStaff) {
            const shareBtn = document.getElementById('shareBtn');
            if (shareBtn) shareBtn.style.display = 'none';
        }

        if (patient.permission_level === 'VIEW') {
            const addNoteBtn = document.getElementById('addNoteBtn');
            const addVitalsBtn = document.getElementById('addVitalsBtn');
            if (addNoteBtn) addNoteBtn.style.display = 'none';
            if (addVitalsBtn) addVitalsBtn.style.display = 'none';
        }

    } catch (error) {
        console.error('Error loading patient info:', error);
    }
}

async function loadNotes() {
    try {
        const response = await fetch(`/patients/${patientId}/notes`, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });

        if (response.status === 401) {
            localStorage.clear();
            window.location.href = '/static/index.html';
            return;
        }

        const notes = await response.json();

        displayNotes(notes);
    } catch (error) {
        console.error('Error loading notes:', error);
        document.getElementById('timelineContainer').innerHTML =
            '<p style="text-align: center; color: var(--error);">Error loading notes</p>';
    }
}

function displayNotes(notes) {
    const container = document.getElementById('timelineContainer');

    if (notes.length === 0) {
        container.innerHTML =
            '<p style="text-align: center; color: var(--gray-500);">No clinical notes yet. Add the first note!</p>';
        return;
    }

    container.innerHTML = notes.map(note => {
        // Force UTC interpretation by appending Z if missing
        const timeString = note.created_at.endsWith('Z') ? note.created_at : note.created_at + 'Z';
        const date = new Date(timeString);
        const formattedDate = date.toLocaleDateString('en-IN', {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
            timeZone: 'Asia/Kolkata'
        });
        const formattedTime = date.toLocaleTimeString('en-IN', {
            hour: '2-digit',
            minute: '2-digit',
            timeZone: 'Asia/Kolkata'
        });

        // Use raw_notes if available, otherwise use SOAP fields (backwards compatible)
        const noteText = note.raw_notes ||
            [note.subjective, note.objective, note.assessment, note.plan]
                .filter(Boolean).join('\n\n') ||
            'No notes recorded';

        return `
            <div class="timeline-item">
                <div class="timeline-dot"></div>
                <div class="note-card">
                    <div class="note-header">
                        <div style="display: flex; justify-content: space-between; align-items: start;">
                            <div>
                                <strong style="font-size: 1rem;">Clinical Note</strong>
                                <p class="note-meta">${formattedDate}, ${formattedTime} • Dr. ${note.physician_name}</p>
                            </div>
                        </div>
                    </div>
                    <div class="soap-content">
                        <div class="soap-text" style="white-space: pre-wrap;">${noteText}</div>
                    </div>
                </div>
            </div>
        `;
    }).join('');
}

async function loadVitals() {
    try {
        const response = await fetch(`/patients/${patientId}/vitals`, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });

        if (response.status === 401) {
            localStorage.clear();
            window.location.href = '/static/index.html';
            return;
        }

        const vitals = await response.json();

        displayVitalsTable(vitals);
        displayVitalsChart(vitals);
    } catch (error) {
        console.error('Error loading vitals:', error);
    }
}

function displayVitalsTable(vitals) {
    const tbody = document.getElementById('vitalsTableBody');

    if (vitals.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" style="text-align: center; color: var(--gray-500);">No vitals logged yet</td></tr>';
        return;
    }

    tbody.innerHTML = vitals.map(v => {
        const timeString = v.created_at.endsWith('Z') ? v.created_at : v.created_at + 'Z';
        const date = new Date(timeString);
        const formattedDate = date.toLocaleDateString('en-IN', {
            month: 'short',
            day: 'numeric',
            year: 'numeric',
            timeZone: 'Asia/Kolkata'
        });

        return `
            <tr>
                <td>${formattedDate}</td>
                <td>${v.systolic_bp && v.diastolic_bp ? `${v.systolic_bp}/${v.diastolic_bp}` : '-'}</td>
                <td>${v.heart_rate || '-'}</td>
                <td>${v.temperature || '-'}</td>
                <td>${v.spo2 || '-'}</td>
            </tr>
        `;
    }).join('');
}

function displayVitalsChart(vitals) {
    const ctx = document.getElementById('vitalsChart').getContext('2d');

    if (vitalsChart) {
        vitalsChart.destroy();
    }

    if (vitals.length === 0) {
        return;
    }

    // Reverse to show chronological order
    const reversedVitals = [...vitals].reverse();

    const labels = reversedVitals.map(v => {
        const timeString = v.created_at.endsWith('Z') ? v.created_at : v.created_at + 'Z';
        const date = new Date(timeString);
        return date.toLocaleDateString('en-IN', { month: 'short', day: 'numeric', timeZone: 'Asia/Kolkata' });
    });

    vitalsChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Sys BP',
                    data: reversedVitals.map(v => v.systolic_bp),
                    borderColor: '#EF4444',
                    backgroundColor: 'rgba(239, 68, 68, 0.1)',
                    tension: 0.4
                },
                {
                    label: 'Dia BP',
                    data: reversedVitals.map(v => v.diastolic_bp),
                    borderColor: '#F472B6',
                    backgroundColor: 'rgba(244, 114, 182, 0.1)',
                    tension: 0.4
                },
                {
                    label: 'Heart Rate',
                    data: reversedVitals.map(v => v.heart_rate),
                    borderColor: '#4F7FFF',
                    backgroundColor: 'rgba(79, 127, 255, 0.1)',
                    tension: 0.4
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: {
                    display: true,
                    position: 'top'
                }
            },
            scales: {
                y: {
                    beginAtZero: false
                }
            }
        }
    });
}

// Tab switching
function switchTab(tabName) {
    // Remove active class from all tabs and content
    document.querySelectorAll('.nav-tab').forEach(tab => tab.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));

    // Add active class to selected tab
    event.target.classList.add('active');

    // Show selected content
    document.getElementById(tabName + 'Tab').classList.add('active');
}

// Modal functions
function showAddNoteModal() {
    document.getElementById('addNoteModal').classList.add('active');
}

function closeAddNoteModal() {
    document.getElementById('addNoteModal').classList.remove('active');
    document.getElementById('addNoteForm').reset();
    document.getElementById('addNoteError').textContent = '';
}

function showAddVitalsModal() {
    document.getElementById('addVitalsModal').classList.add('active');
}

function closeAddVitalsModal() {
    document.getElementById('addVitalsModal').classList.remove('active');
    document.getElementById('addVitalsForm').reset();
    document.getElementById('addVitalsError').textContent = '';
}

// Share Modal
async function showShareModal() {
    document.getElementById('shareModal').classList.add('active');
    await loadSharedList();
}

function closeShareModal() {
    document.getElementById('shareModal').classList.remove('active');
    document.getElementById('shareForm').reset();
    document.getElementById('shareError').textContent = '';
}

async function loadSharedList() {
    try {
        const response = await fetch(`/patients/${patientId}/access`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });

        if (response.ok) {
            const list = await response.json();
            const listContainer = document.getElementById('sharedList');

            if (list.length === 0) {
                listContainer.innerHTML = '<p style="font-size: 0.875rem; color: var(--gray-500); text-align: center;">Not shared with anyone</p>';
                return;
            }

            listContainer.innerHTML = list.map(item => `
                <div style="display: flex; justify-content: space-between; align-items: center; padding: 0.5rem; background: white; margin-bottom: 0.5rem; border-radius: 4px;">
                    <div>
                        <p style="font-weight: 500; font-size: 0.875rem;">${item.user_name || item.user_email}</p>
                        <p style="font-size: 0.75rem; color: var(--gray-500);">${item.permission}</p>
                    </div>
                    ${item.granted_by == physicianId ? `
                    <button onclick="revokeAccess(${item.user_id})" style="color: red; border: none; background: none; cursor: pointer; font-size: 0.875rem;">
                        Revoke
                    </button>` : ''}
                </div>
            `).join('');
        }
    } catch (e) {
        console.error("Error loading share list", e);
    }
}

async function revokeAccess(userId) {
    if (!confirm("Are you sure you want to revoke access for this user?")) return;

    try {
        const response = await fetch(`/patients/${patientId}/share/${userId}`, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${token}` }
        });

        if (response.ok) {
            loadSharedList();
        } else {
            alert("Failed to revoke access");
        }
    } catch (e) {
        console.error(e);
    }
}

// Report Modal
function showReportModal() {
    document.getElementById('reportModal').classList.add('active');
}

function closeReportModal() {
    document.getElementById('reportModal').classList.remove('active');
}

// Add note form submission
document.getElementById('addNoteForm').addEventListener('submit', async (e) => {
    e.preventDefault();

    const errorDiv = document.getElementById('addNoteError');
    errorDiv.textContent = '';

    const notesField = document.getElementById('notes');
    if (!notesField) {
        errorDiv.textContent = 'Notes field not found. Please refresh the page.';
        return;
    }

    const noteData = {
        patient_id: parseInt(patientId),
        raw_notes: notesField.value
    };

    try {
        // Updated endpoint to users
        const response = await fetch(`/users/${physicianId}/notes`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify(noteData)
        });

        if (response.status === 401) {
            localStorage.clear();
            window.location.href = '/static/index.html';
            return;
        }

        if (response.ok) {
            closeAddNoteModal();
            loadNotes(); // Reload notes
        } else {
            const error = await response.json();
            errorDiv.textContent = error.detail || 'Failed to add note';
        }
    } catch (error) {
        errorDiv.textContent = 'An error occurred. Please try again.';
        console.error('Add note error:', error);
    }
});

// Add vitals form submission
document.getElementById('addVitalsForm').addEventListener('submit', async (e) => {
    e.preventDefault();

    const errorDiv = document.getElementById('addVitalsError');
    errorDiv.textContent = '';

    const vitalsData = {
        patient_id: parseInt(patientId),
        systolic_bp: parseInt(document.getElementById('systolicBP').value) || null,
        diastolic_bp: parseInt(document.getElementById('diastolicBP').value) || null,
        heart_rate: parseInt(document.getElementById('heartRate').value) || null,
        temperature: parseFloat(document.getElementById('temperature').value) || null,
        spo2: parseInt(document.getElementById('spo2').value) || null
    };

    try {
        // Updated endpoint to users
        const response = await fetch(`/users/${physicianId}/vitals`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify(vitalsData)
        });

        if (response.status === 401) {
            localStorage.clear();
            window.location.href = '/static/index.html';
            return;
        }

        if (response.ok) {
            closeAddVitalsModal();
            loadVitals(); // Reload vitals
        } else {
            const error = await response.json();
            errorDiv.textContent = error.detail || 'Failed to log vitals';
        }
    } catch (error) {
        errorDiv.textContent = 'An error occurred. Please try again.';
        console.error('Add vitals error:', error);
    }
});

// Share Form Submit
document.getElementById('shareForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const errorDiv = document.getElementById('shareError');
    errorDiv.textContent = '';

    const email = document.getElementById('shareEmail').value;
    const permission = document.getElementById('sharePermission').value;

    try {
        const response = await fetch(`/patients/${patientId}/share`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({
                user_email: email,
                permission: permission
            })
        });

        if (response.ok) {
            loadSharedList(); // Refresh list
            document.getElementById('shareEmail').value = '';
        } else {
            const error = await response.json();
            errorDiv.textContent = error.detail || 'Failed to share';
        }
    } catch (e) {
        errorDiv.textContent = "Error sharing patient";
    }
});

// Report Form Submit
document.getElementById('reportForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const errorDiv = document.getElementById('reportError');
    errorDiv.textContent = '';

    const period = document.getElementById('reportPeriod').value;
    let queryParams = `?period=${period}`;

    if (period === 'custom') {
        const startDate = document.getElementById('startDate').value;
        const endDate = document.getElementById('endDate').value;

        if (!startDate || !endDate) {
            errorDiv.textContent = 'Please select both start and end dates';
            return;
        }
        queryParams += `&start_date=${startDate}&end_date=${endDate}`;
    }

    try {
        const response = await fetch(`/patients/${patientId}/report${queryParams}`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });

        if (response.ok) {
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `report_${patientId}_${period}.pdf`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);
            closeReportModal();
        } else {
            const err = await response.json();
            errorDiv.textContent = err.detail || "Failed to generate report";
        }
    } catch (e) {
        errorDiv.textContent = "Error generating report";
        console.error(e);
    }
});

function toggleCustomDates() {
    const period = document.getElementById('reportPeriod').value;
    const customFields = document.getElementById('customDateFields');
    if (period === 'custom') {
        customFields.style.display = 'grid';
    } else {
        customFields.style.display = 'none';
    }
}

function goBack() {
    window.location.href = '/static/dashboard.html';
}
