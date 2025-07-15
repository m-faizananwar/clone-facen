let video = document.getElementById('video');
let canvas = document.getElementById('canvas');
let ctx = canvas.getContext('2d');
let stream = null;
let capturedImage = null;
let isProcessing = false;
let realtimeInterval = null;
let realtimeMode = false;
let lastRecognized = {};
const COOLDOWN_SECONDS = 30;
let detectionInterval = null;
let lastDetection = { faces: [], timestamp: 0 };
let stableRealFaceSince = null;
let lastRecognitionTrigger = 0;
const DETECTION_INTERVAL_MS = 200;
const RECOGNITION_STABLE_MS = 1000;

// DOM elements
const startCameraBtn = document.getElementById('startCamera');
const recognizeFaceBtn = document.getElementById('recognizeFace');
const captureForEmployeeBtn = document.getElementById('captureForEmployee');
const addEmployeeBtn = document.getElementById('addEmployee');
const employeeNameInput = document.getElementById('employeeName');
const recognitionStatus = document.getElementById('recognitionStatus');
const loadingIndicator = document.getElementById('loadingIndicator');
const lastRecognition = document.getElementById('lastRecognition');
const lastRecognitionText = document.getElementById('lastRecognitionText');
const attendanceStatus = document.getElementById('attendanceStatus');
const addEmployeeStatus = document.getElementById('addEmployeeStatus');
const employeeList = document.getElementById('employeeList');
const attendanceLog = document.getElementById('attendanceLog');
const toggleRealtimeBtn = document.getElementById('toggleRealtime');
const realtimeStatus = document.getElementById('realtimeStatus');
const detectionFeedback = document.getElementById('detectionFeedback');

// Event listeners
startCameraBtn.addEventListener('click', startCamera);
recognizeFaceBtn.addEventListener('click', recognizeFace);
captureForEmployeeBtn.addEventListener('click', captureForEmployee);
addEmployeeBtn.addEventListener('click', addEmployee);
toggleRealtimeBtn.addEventListener('click', toggleRealtimeMode);

// Start camera
async function startCamera() {
    try {
        stream = await navigator.mediaDevices.getUserMedia({ 
            video: { width: 640, height: 480 } 
        });
        video.srcObject = stream;
        startCameraBtn.textContent = 'Camera Started';
        startCameraBtn.disabled = true;
        recognizeFaceBtn.disabled = false;
        captureForEmployeeBtn.disabled = false;
        toggleRealtimeBtn.disabled = false;
        // Set canvas size to match video
        video.addEventListener('loadedmetadata', () => {
            canvas.width = video.videoWidth;
            canvas.height = video.videoHeight;
        });
        // Start detection overlay
        if (!detectionInterval) {
            detectionInterval = setInterval(liveDetect, DETECTION_INTERVAL_MS);
        }
    } catch (err) {
        console.error('Error accessing camera:', err);
        showStatus('Error accessing camera: ' + err.message, 'error');
    }
}

// Capture current frame
function captureFrame() {
    if (video.videoWidth === 0 || video.videoHeight === 0) {
        return null;
    }
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    ctx.drawImage(video, 0, 0);
    return canvas.toDataURL('image/jpeg', 0.8);
}

// Recognize face
async function recognizeFace() {
    if (isProcessing) return;
    const imageData = captureFrame();
    if (!imageData) {
        showStatus('Please start camera first', 'error');
        return;
    }
    isProcessing = true;
    showLoading(true);
    recognizeFaceBtn.disabled = true;
    try {
        const response = await fetch('/recognize', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ image: imageData })
        });
        const result = await response.json();
        // Check for antispoofing detection first
        if (result.spoofing_detected) {
            showStatus(`🚫 ${result.message}`, 'error');
            return;
        }
        if (result.success) {
            showStatus(`✅ Recognized: ${result.employee} (Real face verified)`, 'success');
            lastRecognitionText.textContent = `${result.employee} - ${new Date().toLocaleTimeString()} (Anti-spoofing: PASSED)`;
            lastRecognition.style.display = 'block';
            // Automatically mark attendance
            markAttendance(result.employee);
        } else {
            // Face not recognized but antispoofing passed
            showStatus(`❓ ${result.message} (Real face detected)`, 'error');
        }
    } catch (error) {
        showStatus('Recognition failed: ' + error.message, 'error');
    } finally {
        isProcessing = false;
        showLoading(false);
        recognizeFaceBtn.disabled = false;
    }
}

// Mark attendance
async function markAttendance(employeeName) {
    try {
        const response = await fetch('/mark_attendance', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ employee: employeeName })
        });
        const result = await response.json();
        if (result.success) {
            showAttendanceStatus(result.message, 'success');
            loadAttendance(); // Refresh attendance log
        } else {
            showAttendanceStatus(result.message, 'error');
        }
    } catch (error) {
        showAttendanceStatus('Failed to mark attendance: ' + error.message, 'error');
    }
}

// Capture for new employee
function captureForEmployee() {
    const imageData = captureFrame();
    if (!imageData) {
        showStatus('Please start camera first', 'error');
        return;
    }
    capturedImage = imageData;
    addEmployeeBtn.disabled = false;
    addEmployeeBtn.textContent = 'Add Employee (Image Captured)';
    showAddEmployeeStatus('📸 Image captured! Enter name and click Add Employee. (Antispoofing will be verified)', 'success');
}

// Add new employee
async function addEmployee() {
    const name = employeeNameInput.value.trim();
    if (!name) {
        showAddEmployeeStatus('Please enter employee name', 'error');
        return;
    }
    if (!capturedImage) {
        showAddEmployeeStatus('Please capture image first', 'error');
        return;
    }
    try {
        const response = await fetch('/add_employee', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                name: name,
                image: capturedImage
            })
        });
        const result = await response.json();
        if (result.success) {
            showAddEmployeeStatus(`✅ ${result.message}`, 'success');
            employeeNameInput.value = '';
            capturedImage = null;
            addEmployeeBtn.disabled = true;
            addEmployeeBtn.textContent = 'Add Employee (Capture First)';
            loadEmployees(); // Refresh employee list
        } else {
            // Check if it's an antispoofing error
            if (result.message.includes('Spoofing detected') || result.message.includes('spoofing')) {
                showAddEmployeeStatus(`🚫 ${result.message}`, 'error');
            } else {
                showAddEmployeeStatus(`❌ ${result.message}`, 'error');
            }
        }
    } catch (error) {
        showAddEmployeeStatus('Failed to add employee: ' + error.message, 'error');
    }
}

// Load employees
async function loadEmployees() {
    try {
        const response = await fetch('/get_employees');
        const employees = await response.json();
        employeeList.innerHTML = '';
        if (Object.keys(employees).length === 0) {
            employeeList.innerHTML = '<div class="employee-item">No employees registered</div>';
        } else {
            for (const [name, info] of Object.entries(employees)) {
                const item = document.createElement('div');
                item.className = 'employee-item';
                item.textContent = `${name} (ID: ${info.id})`;
                employeeList.appendChild(item);
            }
        }
    } catch (error) {
        employeeList.innerHTML = '<div class="employee-item">Error loading employees</div>';
    }
}

// Load attendance
async function loadAttendance() {
    try {
        const response = await fetch('/get_attendance');
        const attendance = await response.json();
        attendanceLog.innerHTML = '';
        // Filter today's attendance
        const today = new Date().toISOString().split('T')[0];
        const todayAttendance = attendance.filter(record => record.date === today);
        if (todayAttendance.length === 0) {
            attendanceLog.innerHTML = '<div class="attendance-item">No attendance records for today</div>';
        } else {
            todayAttendance.forEach(record => {
                const item = document.createElement('div');
                item.className = 'attendance-item';
                let html = `<strong>${record.employee}</strong><ul style='margin:0 0 0 20px;padding:0;'>`;
                if (record.events && Array.isArray(record.events)) {
                    record.events.forEach(ev => {
                        html += `<li>${ev.type.toUpperCase()} at ${ev.time}</li>`;
                    });
                } else if (record.time) {
                    // legacy record
                    html += `<li>IN at ${record.time}</li>`;
                }
                html += '</ul>';
                item.innerHTML = html;
                attendanceLog.appendChild(item);
            });
        }
    } catch (error) {
        attendanceLog.innerHTML = '<div class="attendance-item">Error loading attendance</div>';
    }
}

// Utility functions
function showStatus(message, type) {
    recognitionStatus.textContent = message;
    recognitionStatus.className = `status-box status-${type}`;
    recognitionStatus.style.display = 'block';
    setTimeout(() => {
        recognitionStatus.style.display = 'none';
    }, 5000);
}

function showAttendanceStatus(message, type) {
    attendanceStatus.textContent = message;
    attendanceStatus.className = `status-box status-${type}`;
    attendanceStatus.style.display = 'block';
    setTimeout(() => {
        attendanceStatus.style.display = 'none';
    }, 5000);
}

function showAddEmployeeStatus(message, type) {
    addEmployeeStatus.innerHTML = `<div class="status-box status-${type}">${message}</div>`;
    setTimeout(() => {
        addEmployeeStatus.innerHTML = '';
    }, 5000);
}

function showLoading(show) {
    loadingIndicator.style.display = show ? 'block' : 'none';
}

function drawDetections(faces) {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    let feedback = '';
    if (!faces || faces.length === 0) {
        feedback = 'No face detected';
        detectionFeedback.style.color = '#888';
    } else {
        faces.forEach(face => {
            let color = '#FFD600'; // yellow for unknown
            if (face.is_real === true) color = '#28a745'; // green
            else if (face.is_real === false) color = '#dc3545'; // red
            ctx.lineWidth = 3;
            ctx.strokeStyle = color;
            ctx.beginPath();
            ctx.rect(face.x, face.y, face.w, face.h);
            ctx.stroke();
            // Draw label
            ctx.font = '16px Arial';
            ctx.fillStyle = color;
            let label = face.is_real === true ? 'Real Face' : (face.is_real === false ? 'Spoofing' : 'Unknown');
            ctx.fillText(label, face.x, face.y - 8);
            feedback = label;
        });
    }
    detectionFeedback.textContent = feedback;
}

async function liveDetect() {
    if (video.videoWidth === 0 || video.videoHeight === 0) return;
    // Only send detection if not processing recognition
    if (isProcessing) return;
    // Get frame
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    ctx.drawImage(video, 0, 0);
    const imageData = canvas.toDataURL('image/jpeg', 0.7);
    try {
        const response = await fetch('/detect', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ image: imageData })
        });
        const result = await response.json();
        if (result.success) {
            drawDetections(result.faces);
            // Check for stable real face
            const realFace = result.faces.find(f => f.is_real === true);
            const now = Date.now();
            if (realFace) {
                if (!stableRealFaceSince) stableRealFaceSince = now;
                // Only trigger recognition if stable for RECOGNITION_STABLE_MS and not recently triggered
                if (now - stableRealFaceSince > RECOGNITION_STABLE_MS && now - lastRecognitionTrigger > RECOGNITION_STABLE_MS) {
                    lastRecognitionTrigger = now;
                    stableRealFaceSince = null;
                    // Trigger recognition (simulate click)
                    recognizeFace();
                }
            } else {
                stableRealFaceSince = null;
            }
        } else {
            drawDetections([]);
        }
    } catch (e) {
        drawDetections([]);
    }
}

// Real-time attendance mode
function toggleRealtimeMode() {
    if (!realtimeMode) {
        // Start real-time mode
        realtimeMode = true;
        toggleRealtimeBtn.textContent = 'Stop Real-Time Attendance';
        realtimeStatus.style.display = 'inline';
        recognizeFaceBtn.disabled = true;
        captureForEmployeeBtn.disabled = true;
        addEmployeeBtn.disabled = true;
        realtimeInterval = setInterval(realtimeRecognize, 2000);
    } else {
        // Stop real-time mode
        realtimeMode = false;
        toggleRealtimeBtn.textContent = 'Start Real-Time Attendance';
        realtimeStatus.style.display = 'none';
        recognizeFaceBtn.disabled = false;
        captureForEmployeeBtn.disabled = false;
        addEmployeeBtn.disabled = !capturedImage;
        clearInterval(realtimeInterval);
    }
}

async function realtimeRecognize() {
    if (isProcessing || !realtimeMode) return;
    const imageData = captureFrame();
    if (!imageData) return;
    isProcessing = true;
    showLoading(true);
    try {
        const response = await fetch('/recognize', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ image: imageData })
        });
        const result = await response.json();
        if (result.spoofing_detected) {
            showStatus(`🚫 ${result.message}`, 'error');
            return;
        }
        if (result.success) {
            const now = Date.now();
            const emp = result.employee;
            if (!lastRecognized[emp] || (now - lastRecognized[emp]) > COOLDOWN_SECONDS * 1000) {
                lastRecognized[emp] = now;
                showStatus(`✅ Recognized: ${emp} (Real face verified)`, 'success');
                lastRecognitionText.textContent = `${emp} - ${new Date().toLocaleTimeString()} (Anti-spoofing: PASSED)`;
                lastRecognition.style.display = 'block';
                await markAttendance(emp);
            } else {
                // Cooldown active, skip
            }
        } else {
            // Face not recognized but antispoofing passed
            showStatus(`❓ ${result.message} (Real face detected)`, 'error');
        }
    } catch (error) {
        showStatus('Recognition failed: ' + error.message, 'error');
    } finally {
        isProcessing = false;
        showLoading(false);
    }
}

// Initialize page
document.addEventListener('DOMContentLoaded', () => {
    loadEmployees();
    loadAttendance();
    // Refresh attendance every 30 seconds
    setInterval(loadAttendance, 30000);
});
