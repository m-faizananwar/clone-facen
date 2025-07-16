// --- Camera & Attendance Monitoring Only (for main page) ---
let video = document.getElementById('video');
let canvas = document.getElementById('canvas');
let ctx = canvas ? canvas.getContext('2d') : null;
let stream = null;
let isProcessing = false;
let realtimeInterval = null;
let realtimeMode = false;
let lastRecognized = {};
const COOLDOWN_SECONDS = 30;
let detectionInterval = null;
let stableRealFaceSince = null;
let lastRecognitionTrigger = 0;
const DETECTION_INTERVAL_MS = 100;
const RECOGNITION_STABLE_MS = 1000;
let detectionInFlight = false;
let latestDetectionFaces = [];

// DOM elements (main page only)
const startCameraBtn = document.getElementById('startCamera');
const recognizeFaceBtn = document.getElementById('recognizeFace');
const toggleRealtimeBtn = document.getElementById('toggleRealtime');
const recognitionStatus = document.getElementById('recognitionStatus');
const loadingIndicator = document.getElementById('loadingIndicator');
const lastRecognition = document.getElementById('lastRecognition');
const lastRecognitionText = document.getElementById('lastRecognitionText');
const attendanceStatus = document.getElementById('attendanceStatus');
const attendanceLog = document.getElementById('attendanceLog');
const detectionFeedback = document.getElementById('detectionFeedback');
const tabTodayBtn = document.getElementById('tab-today');
const tabPastBtn = document.getElementById('tab-past');
const attendanceTodayTab = document.getElementById('attendance-today');
const attendancePastTab = document.getElementById('attendance-past');
const pastAttendanceLog = document.getElementById('pastAttendanceLog');
const pastDatePicker = document.getElementById('pastDatePicker');
const loadPastAttendanceBtn = document.getElementById('loadPastAttendance');

// Tab switching (now 3 tabs)
const tabAllPastBtn = document.getElementById('tab-allpast');
const attendanceAllPastTab = document.getElementById('attendance-allpast');
const allPastAttendanceLog = document.getElementById('allPastAttendanceLog');

// --- Event listeners (main page only) ---
if (startCameraBtn) startCameraBtn.addEventListener('click', startCamera);
if (recognizeFaceBtn) recognizeFaceBtn.addEventListener('click', recognizeFace);
if (toggleRealtimeBtn) toggleRealtimeBtn.addEventListener('click', toggleRealtimeMode);
if (loadPastAttendanceBtn) loadPastAttendanceBtn.addEventListener('click', loadPastAttendance);
if (pastDatePicker) pastDatePicker.addEventListener('change', loadPastAttendance);

// Tab switching (now 3 tabs)
if (tabTodayBtn && tabPastBtn && tabAllPastBtn && attendanceTodayTab && attendancePastTab && attendanceAllPastTab) {
    tabTodayBtn.addEventListener('click', () => {
        tabTodayBtn.classList.add('active');
        tabPastBtn.classList.remove('active');
        tabAllPastBtn.classList.remove('active');
        attendanceTodayTab.classList.add('active');
        attendancePastTab.classList.remove('active');
        attendanceAllPastTab.classList.remove('active');
    });
    tabPastBtn.addEventListener('click', () => {
        tabPastBtn.classList.add('active');
        tabTodayBtn.classList.remove('active');
        tabAllPastBtn.classList.remove('active');
        attendancePastTab.classList.add('active');
        attendanceTodayTab.classList.remove('active');
        attendanceAllPastTab.classList.remove('active');
        loadPastAttendance();
    });
    tabAllPastBtn.addEventListener('click', () => {
        tabAllPastBtn.classList.add('active');
        tabTodayBtn.classList.remove('active');
        tabPastBtn.classList.remove('active');
        attendanceAllPastTab.classList.add('active');
        attendanceTodayTab.classList.remove('active');
        attendancePastTab.classList.remove('active');
        loadAllPastAttendance();
    });
}

// --- Camera functions ---
async function startCamera() {
    try {
        stream = await navigator.mediaDevices.getUserMedia({ 
            video: { width: 640, height: 480 } 
        });
        if (video) video.srcObject = stream;
        if (startCameraBtn) {
            startCameraBtn.textContent = 'Camera Started';
            startCameraBtn.disabled = true;
        }
        if (recognizeFaceBtn) recognizeFaceBtn.disabled = false;
        if (toggleRealtimeBtn) toggleRealtimeBtn.disabled = false;
        // Set canvas size to match video
        if (video) {
            video.addEventListener('loadedmetadata', () => {
                if (canvas) {
                    canvas.width = video.videoWidth;
                    canvas.height = video.videoHeight;
                }
            });
        }
        // Start detection overlay
        if (!detectionInterval) {
            detectionInterval = setInterval(liveDetect, DETECTION_INTERVAL_MS);
            requestAnimationFrame(drawDetectionOverlay);
        }
    } catch (err) {
        console.error('Error accessing camera:', err);
        showStatus('Error accessing camera: ' + err.message, 'error');
    }
}

function captureFrame() {
    if (!video || !canvas || !ctx) return null;
    if (video.videoWidth === 0 || video.videoHeight === 0) return null;
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    ctx.drawImage(video, 0, 0);
    return canvas.toDataURL('image/jpeg', 0.8);
}

// --- Recognition ---
async function recognizeFace() {
    if (isProcessing) return;
    const imageData = captureFrame();
    if (!imageData) {
        showStatus('Please start camera first', 'error');
        return;
    }
    isProcessing = true;
    showLoading(true);
    if (recognizeFaceBtn) recognizeFaceBtn.disabled = true;
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
            showStatus(`✅ Recognized: ${result.employee} (Real face verified)`, 'success');
            if (lastRecognitionText) lastRecognitionText.textContent = `${result.employee} - ${new Date().toLocaleTimeString()} (Anti-spoofing: PASSED)`;
            if (lastRecognition) lastRecognition.style.display = 'block';
            markAttendance(result.employee);
        } else {
            showStatus(`❓ ${result.message} (Real face detected)`, 'error');
        }
    } catch (error) {
        showStatus('Recognition failed: ' + error.message, 'error');
    } finally {
        isProcessing = false;
        showLoading(false);
        if (recognizeFaceBtn) recognizeFaceBtn.disabled = false;
    }
}

// --- Attendance ---
async function markAttendance(employeeName) {
    try {
        const response = await fetch('/mark_attendance', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ employee: employeeName })
        });
        const result = await response.json();
        if (result.success) {
            showAttendanceStatus(result.message, 'success');
            loadAttendance();
        } else {
            showAttendanceStatus(result.message, 'error');
        }
    } catch (error) {
        showAttendanceStatus('Failed to mark attendance: ' + error.message, 'error');
    }
}

// --- Attendance Log ---
function badge(type) {
    const color = type === 'IN' ? '#22c55e' : '#4f8cff';
    return `<span class="badge badge-${type.toLowerCase()}" style="background:${color};color:#fff;padding:2px 10px;border-radius:12px;font-size:0.98em;">${type}</span>`;
}

async function loadAttendance() {
    if (!attendanceLog) return;
    try {
        const response = await fetch('/get_attendance');
        const attendance = await response.json();
        attendanceLog.innerHTML = '';
        const today = new Date().toISOString().split('T')[0];
        const todayAttendance = attendance.filter(record => record.date === today);
        if (todayAttendance.length === 0) {
            attendanceLog.innerHTML = '<div class="attendance-table-row empty">No attendance records for today</div>';
        } else {
            let rowIdx = 0;
            todayAttendance.forEach(record => {
                if (record.events && Array.isArray(record.events)) {
                    record.events.forEach(ev => {
                        const row = document.createElement('div');
                        row.className = 'attendance-table-row';
                        if (rowIdx % 2 === 1) row.classList.add('alt');
                        row.style.display = 'flex';
                        row.style.alignItems = 'center';
                        row.innerHTML = `
                            <div style='flex:2;'>${record.employee}</div>
                            <div style='flex:1;'>${badge(ev.type.toUpperCase())}</div>
                            <div style='flex:1;'>${ev.time}</div>
                        `;
                        attendanceLog.appendChild(row);
                        rowIdx++;
                    });
                } else if (record.time) {
                    const row = document.createElement('div');
                    row.className = 'attendance-table-row';
                    if (rowIdx % 2 === 1) row.classList.add('alt');
                    row.style.display = 'flex';
                    row.style.alignItems = 'center';
                    row.innerHTML = `
                        <div style='flex:2;'>${record.employee}</div>
                        <div style='flex:1;'>${badge('IN')}</div>
                        <div style='flex:1;'>${record.time}</div>
                    `;
                    attendanceLog.appendChild(row);
                    rowIdx++;
                }
            });
        }
    } catch (error) {
        attendanceLog.innerHTML = '<div class="attendance-table-row empty">Error loading attendance</div>';
    }
}

async function loadPastAttendance() {
    if (!pastAttendanceLog) return;
    try {
        const response = await fetch('/get_attendance');
        const attendance = await response.json();
        let filtered = attendance;
        const selectedDate = pastDatePicker && pastDatePicker.value;
        if (selectedDate) {
            filtered = attendance.filter(record => record.date === selectedDate);
        }
        if (filtered.length === 0) {
            pastAttendanceLog.innerHTML = '<div class="attendance-table-row empty">No attendance records found.</div>';
        } else {
            let rowIdx = 0;
            filtered.forEach(record => {
                if (record.events && Array.isArray(record.events)) {
                    record.events.forEach(ev => {
                        const row = document.createElement('div');
                        row.className = 'attendance-table-row';
                        if (rowIdx % 2 === 1) row.classList.add('alt');
                        row.style.display = 'flex';
                        row.style.alignItems = 'center';
                        row.innerHTML = `
                            <div style='flex:2;'>${record.employee}</div>
                            <div style='flex:1;'>${badge(ev.type.toUpperCase())}</div>
                            <div style='flex:1;'>${ev.time}</div>
                        `;
                        pastAttendanceLog.appendChild(row);
                        rowIdx++;
                    });
                } else if (record.time) {
                    const row = document.createElement('div');
                    row.className = 'attendance-table-row';
                    if (rowIdx % 2 === 1) row.classList.add('alt');
                    row.style.display = 'flex';
                    row.style.alignItems = 'center';
                    row.innerHTML = `
                        <div style='flex:2;'>${record.employee}</div>
                        <div style='flex:1;'>${badge('IN')}</div>
                        <div style='flex:1;'>${record.time}</div>
                    `;
                    pastAttendanceLog.appendChild(row);
                    rowIdx++;
                }
            });
        }
    } catch (error) {
        pastAttendanceLog.innerHTML = '<div class="attendance-table-row empty">Error loading past attendance</div>';
    }
}

async function loadAllPastAttendance() {
    if (!allPastAttendanceLog) return;
    try {
        const response = await fetch('/get_attendance');
        const attendance = await response.json();
        if (attendance.length === 0) {
            allPastAttendanceLog.innerHTML = '<div class="attendance-table-row empty">No attendance records found.</div>';
        } else {
            let rowIdx = 0;
            attendance.forEach(record => {
                if (record.events && Array.isArray(record.events)) {
                    record.events.forEach(ev => {
                        const row = document.createElement('div');
                        row.className = 'attendance-table-row';
                        if (rowIdx % 2 === 1) row.classList.add('alt');
                        row.style.display = 'flex';
                        row.style.alignItems = 'center';
                        row.innerHTML = `
                            <div style='flex:2;'>${record.employee}</div>
                            <div style='flex:1;'>${badge(ev.type.toUpperCase())}</div>
                            <div style='flex:1;'>${ev.time} <span style='color:#888;font-size:0.95em;'>(${record.date})</span></div>
                        `;
                        allPastAttendanceLog.appendChild(row);
                        rowIdx++;
                    });
                } else if (record.time) {
                    const row = document.createElement('div');
                    row.className = 'attendance-table-row';
                    if (rowIdx % 2 === 1) row.classList.add('alt');
                    row.style.display = 'flex';
                    row.style.alignItems = 'center';
                    row.innerHTML = `
                        <div style='flex:2;'>${record.employee}</div>
                        <div style='flex:1;'>${badge('IN')}</div>
                        <div style='flex:1;'>${record.time} <span style='color:#888;font-size:0.95em;'>(${record.date})</span></div>
                    `;
                    allPastAttendanceLog.appendChild(row);
                    rowIdx++;
                }
            });
        }
    } catch (error) {
        allPastAttendanceLog.innerHTML = '<div class="attendance-table-row empty">Error loading all past attendance</div>';
    }
}

// --- Utility functions ---
function showStatus(message, type) {
    if (!recognitionStatus) return;
    recognitionStatus.textContent = message;
    recognitionStatus.className = `status-box status-${type}`;
    recognitionStatus.style.display = 'block';
    setTimeout(() => {
        recognitionStatus.style.display = 'none';
    }, 5000);
}
function showAttendanceStatus(message, type) {
    if (!attendanceStatus) return;
    attendanceStatus.textContent = message;
    attendanceStatus.className = `status-box status-${type}`;
    attendanceStatus.style.display = 'block';
    setTimeout(() => {
        attendanceStatus.style.display = 'none';
    }, 5000);
}
function showLoading(show) {
    if (!loadingIndicator) return;
    loadingIndicator.style.display = show ? 'block' : 'none';
}

function drawDetectionOverlay() {
    if (!canvas || !ctx) return;
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    let feedback = '';
    if (!latestDetectionFaces || latestDetectionFaces.length === 0) {
        feedback = 'No face detected';
        if (detectionFeedback) detectionFeedback.style.color = '#888';
    } else {
        latestDetectionFaces.forEach(face => {
            let color = '#FFD600';
            if (face.is_real === true) color = '#28a745';
            else if (face.is_real === false) color = '#dc3545';
            ctx.lineWidth = 3;
            ctx.strokeStyle = color;
            ctx.beginPath();
            ctx.rect(face.x, face.y, face.w, face.h);
            ctx.stroke();
            ctx.font = '16px Arial';
            ctx.fillStyle = color;
            let label = face.is_real === true ? 'Real Face' : (face.is_real === false ? 'Spoofing' : 'Unknown');
            ctx.fillText(label, face.x, face.y - 8);
            feedback = label;
        });
    }
    if (detectionFeedback) detectionFeedback.textContent = feedback;
    requestAnimationFrame(drawDetectionOverlay);
}

async function liveDetect() {
    if (!video || !canvas || !ctx) return;
    if (video.videoWidth === 0 || video.videoHeight === 0) return;
    if (isProcessing) return;
    if (detectionInFlight) return;
    detectionInFlight = true;
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
            latestDetectionFaces = result.faces;
            // Check for stable real face
            const realFace = result.faces.find(f => f.is_real === true);
            const now = Date.now();
            if (realFace) {
                if (!stableRealFaceSince) stableRealFaceSince = now;
                if (now - stableRealFaceSince > RECOGNITION_STABLE_MS && now - lastRecognitionTrigger > RECOGNITION_STABLE_MS) {
                    lastRecognitionTrigger = now;
                    stableRealFaceSince = null;
                    recognizeFace();
                }
            } else {
                stableRealFaceSince = null;
            }
        } else {
            latestDetectionFaces = [];
        }
    } catch (e) {
        latestDetectionFaces = [];
    } finally {
        detectionInFlight = false;
    }
}

// --- Real-time attendance mode ---
function toggleRealtimeMode() {
    if (!realtimeMode) {
        realtimeMode = true;
        if (toggleRealtimeBtn) toggleRealtimeBtn.textContent = 'Stop Real-Time Attendance';
        if (recognizeFaceBtn) recognizeFaceBtn.disabled = true;
        realtimeInterval = setInterval(realtimeRecognize, 2000);
    } else {
        realtimeMode = false;
        if (toggleRealtimeBtn) toggleRealtimeBtn.textContent = 'Start Real-Time Attendance';
        if (recognizeFaceBtn) recognizeFaceBtn.disabled = false;
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
                if (lastRecognitionText) lastRecognitionText.textContent = `${emp} - ${new Date().toLocaleTimeString()} (Anti-spoofing: PASSED)`;
                if (lastRecognition) lastRecognition.style.display = 'block';
                await markAttendance(emp);
            }
        } else {
            showStatus(`❓ ${result.message} (Real face detected)`, 'error');
        }
    } catch (error) {
        showStatus('Recognition failed: ' + error.message, 'error');
    } finally {
        isProcessing = false;
        showLoading(false);
    }
}

// --- Initialize page ---
document.addEventListener('DOMContentLoaded', () => {
    loadAttendance();
    setInterval(loadAttendance, 30000);
    if (attendancePastTab && attendancePastTab.classList.contains('active')) {
        loadPastAttendance();
    }
    if (attendanceAllPastTab && attendanceAllPastTab.classList.contains('active')) {
        loadAllPastAttendance();
    }
});
