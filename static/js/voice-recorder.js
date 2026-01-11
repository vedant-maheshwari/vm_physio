// Voice Recorder with Sarvam API Integration
let mediaRecorder;
let audioChunks = [];
let isRecording = false;

// Make toggleRecording globally accessible
window.toggleRecording = async function () {
    const recordBtn = document.getElementById('recordBtn');
    const statusText = document.getElementById('recordingStatus');

    // Get fresh token each time
    const token = localStorage.getItem('access_token');

    if (!token) {
        statusText.textContent = 'Please login first';
        statusText.style.color = 'var(--error)';
        statusText.style.opacity = '1';
        return;
    }

    if (!isRecording) {
        // Start recording
        try {
            // Check for HTTPS (required on iOS)
            if (location.protocol !== 'https:' && location.hostname !== 'localhost' && location.hostname !== '127.0.0.1') {
                statusText.innerHTML = `
                    <strong style="color: var(--error);">⚠️ HTTPS Required</strong><br>
                    <small>Microphone requires secure connection (HTTPS) on mobile browsers.</small>
                `;
                statusText.style.opacity = '1';
                return;
            }

            // Check if getUserMedia is supported
            if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
                statusText.textContent = 'Microphone not supported in this browser';
                statusText.style.color = 'var(--error)';
                statusText.style.opacity = '1';
                return;
            }

            console.log('Requesting microphone access...');
            const stream = await navigator.mediaDevices.getUserMedia({
                audio: {
                    echoCancellation: true,
                    noiseSuppression: true,
                    autoGainControl: true
                }
            });

            console.log('✓ Microphone access granted');

            // Try different formats for better mobile support
            let options;
            if (MediaRecorder.isTypeSupported('audio/webm;codecs=opus')) {
                options = { mimeType: 'audio/webm;codecs=opus' };
            } else if (MediaRecorder.isTypeSupported('audio/webm')) {
                options = { mimeType: 'audio/webm' };
            } else if (MediaRecorder.isTypeSupported('audio/mp4')) {
                options = { mimeType: 'audio/mp4' };
            } else {
                console.warn('Using default audio format');
                options = {};
            }

            console.log('Using format:', options.mimeType || 'default');
            mediaRecorder = new MediaRecorder(stream, options);

            mediaRecorder.ondataavailable = (event) => {
                if (event.data && event.data.size > 0) {
                    audioChunks.push(event.data);
                    console.log(`Audio chunk received: ${event.data.size} bytes`);
                }
            };

            mediaRecorder.onstop = async () => {
                console.log('=== Recording Stopped ===');
                console.log(`Total chunks collected: ${audioChunks.length}`);

                if (audioChunks.length === 0) {
                    console.error('❌ No audio data collected');
                    statusText.textContent = 'Recording failed - no audio captured';
                    statusText.style.color = 'var(--error)';
                    statusText.style.opacity = '1';
                    stream.getTracks().forEach(track => track.stop());
                    return;
                }

                const audioBlob = new Blob(audioChunks, { type: options.mimeType || 'audio/webm' });
                console.log(`✓ Audio blob created: ${audioBlob.size} bytes, type: ${audioBlob.type}`);
                audioChunks = [];

                if (audioBlob.size === 0) {
                    console.error('❌ Audio blob is empty');
                    statusText.textContent = 'Recording failed - no audio data';
                    statusText.style.color = 'var(--error)';
                    statusText.style.opacity = '1';
                    stream.getTracks().forEach(track => track.stop());
                    return;
                }

                // Show processing status
                statusText.textContent = 'Processing audio...';
                statusText.style.color = 'var(--primary)';
                statusText.style.opacity = '1';

                // Transcribe audio using Sarvam API
                await transcribeAudio(audioBlob, token);

                // Stop all tracks
                stream.getTracks().forEach(track => {
                    console.log(`Stopping track: ${track.kind}`);
                    track.stop();
                });
            };

            // Request data every 100ms while recording
            mediaRecorder.start(100);
            isRecording = true;
            console.log('✓ Recording started');

            recordBtn.classList.add('recording');
            recordBtn.textContent = '⏹️  Stop';
            statusText.textContent = '🔴 Recording...';
            statusText.style.opacity = '1';
            statusText.style.color = 'var(--error)';

        } catch (error) {
            console.error('Error accessing microphone:', error);

            // Check if it's a permission error
            if (error.name === 'NotAllowedError' || error.name === 'PermissionDeniedError') {
                statusText.innerHTML = `
                    <strong>Microphone Access Blocked</strong><br>
                    <small style="font-size: 0.75rem;">
                    To fix: Tap the 🔒 or ⓘ in address bar → Site Settings → Microphone → Allow
                    </small>
                `;
            } else if (error.name === 'NotFoundError') {
                statusText.textContent = 'No microphone found on this device';
            } else {
                statusText.textContent = 'Microphone error. Please type notes manually.';
            }

            statusText.style.color = 'var(--error)';
            statusText.style.opacity = '1';

            // Keep the error visible longer for mobile users
            setTimeout(() => {
                statusText.style.opacity = '0.7';
            }, 10000);
        }
    } else {
        // Stop recording
        mediaRecorder.stop();
        isRecording = false;

        recordBtn.classList.remove('recording');
        recordBtn.textContent = '🎤';
        statusText.textContent = 'Processing... प्रोसेस हो रहा है...';
        statusText.style.color = 'var(--primary)';
    }
}

async function transcribeAudio(audioBlob, token) {
    const statusText = document.getElementById('recordingStatus');

    try {
        console.log('=== Starting Transcription ===');
        console.log(`Blob size: ${audioBlob.size} bytes, type: ${audioBlob.type}`);

        // Create FormData to send audio file
        const formData = new FormData();
        formData.append('file', audioBlob, 'recording.webm');

        statusText.textContent = '📡 Sending to Sarvam AI...';
        statusText.style.color = 'var(--primary)';

        // Transcribe with Sarvam API
        const response = await fetch('/transcribe', {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`
            },
            body: formData
        });

        console.log(`Transcription response status: ${response.status}`);

        if (response.status === 401) {
            console.error('❌ Unauthorized - token expired');
            localStorage.clear();
            window.location.href = '/static/index.html';
            return;
        }

        if (response.ok) {
            const data = await response.json();
            console.log('Transcription response:', data);

            if (data.status === 'success' && data.text) {
                // Successfully transcribed - populate notes field
                console.log('✅ Transcription successful:', data.text);

                const notesField = document.getElementById('notes');
                if (notesField) {
                    notesField.value = data.text;

                    // Visual indicator
                    notesField.style.borderColor = 'var(--success)';
                    notesField.style.backgroundColor = '#f0fdf4';
                    setTimeout(() => {
                        notesField.style.borderColor = '';
                        notesField.style.backgroundColor = '';
                    }, 2000);
                }

                statusText.textContent = `✓ Transcribed successfully!`;
                statusText.style.color = 'var(--success)';

                setTimeout(() => {
                    statusText.style.opacity = '0';
                }, 3000);
            } else {
                // Error from Sarvam API
                console.error('❌ Transcription error from API:', data);
                statusText.innerHTML = `
                    <strong style="color: var(--error);">Transcription Failed</strong><br>
                    <small>${data.error || 'Please try again or type manually'}</small>
                `;
                statusText.style.opacity = '1';
                setTimeout(() => {
                    statusText.style.opacity = '0.7';
                }, 5000);
            }
        } else {
            const errorText = await response.text();
            console.error('❌ Transcription request failed:', errorText);
            throw new Error(`Server error: ${response.status}`);
        }
    } catch (error) {
        console.error('❌ Transcription error:', error);
        statusText.innerHTML = `
            <strong style="color: var(--error);">Error Processing Audio</strong><br>
            <small>Check console for details. Try typing manually.</small>
        `;
        statusText.style.opacity = '1';
        setTimeout(() => {
            statusText.style.opacity = '0.7';
        }, 5000);
    }
}

function populateSOAPFields(soapData) {
    // Populate SOAP fields with AI-generated content
    const fields = {
        'subjective': soapData.soap_note.subjective,
        'objective': soapData.soap_note.objective,
        'assessment': soapData.soap_note.assessment,
        'plan': soapData.soap_note.plan
    };

    for (const [fieldId, value] of Object.entries(fields)) {
        const field = document.getElementById(fieldId);
        if (field && value && value !== 'Not documented') {
            field.value = value;

            // Add visual indicator that field was auto-filled
            field.style.borderColor = 'var(--success)';
            field.style.backgroundColor = '#f0fdf4';
            setTimeout(() => {
                field.style.borderColor = '';
                field.style.backgroundColor = '';
            }, 2000);
        }
    }

    console.log('✅ SOAP fields populated');
}

console.log('Voice recorder loaded successfully');
