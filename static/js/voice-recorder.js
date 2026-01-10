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
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });

            // Use webm format which is widely supported
            const options = { mimeType: 'audio/webm' };
            mediaRecorder = new MediaRecorder(stream, options);

            mediaRecorder.ondataavailable = (event) => {
                if (event.data && event.data.size > 0) {
                    audioChunks.push(event.data);
                    console.log(`Audio chunk received: ${event.data.size} bytes`);
                }
            };

            mediaRecorder.onstop = async () => {
                console.log(`Recording stopped. Total chunks: ${audioChunks.length}`);
                const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
                console.log(`Final blob size: ${audioBlob.size} bytes`);
                audioChunks = [];

                // Transcribe audio using Sarvam API
                await transcribeAudio(audioBlob, token);

                // Stop all tracks
                stream.getTracks().forEach(track => track.stop());
            };

            // Request data every 100ms while recording
            mediaRecorder.start(100);
            isRecording = true;

            recordBtn.classList.add('recording');
            recordBtn.textContent = '⏹️';
            statusText.textContent = 'Recording... रिकॉर्डिंग हो रही है...';
            statusText.style.opacity = '1';
            statusText.style.color = 'var(--error)';

        } catch (error) {
            console.error('Error accessing microphone:', error);
            statusText.textContent = 'Microphone access denied • माइक्रोफ़ोन एक्सेस अस्वीकृत';
            statusText.style.color = 'var(--error)';
            statusText.style.opacity = '1';
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
        // Create FormData to send audio file
        const formData = new FormData();
        formData.append('file', audioBlob, 'recording.webm');

        statusText.textContent = 'Transcribing with Sarvam AI... ट्रांसक्रिप्शन हो रहा है...';

        // Transcribe with Sarvam API
        const response = await fetch('/transcribe', {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`
            },
            body: formData
        });

        if (response.status === 401) {
            localStorage.clear();
            window.location.href = '/static/index.html';
            return;
        }

        if (response.ok) {
            const data = await response.json();

            if (data.status === 'success' && data.text) {
                // Successfully transcribed - populate notes field
                console.log('✅ Transcription:', data.text);

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
                console.error('Transcription error:', data);
                statusText.textContent = 'Transcription failed. Please type manually.';
                statusText.style.color = 'var(--error)';
                setTimeout(() => {
                    statusText.style.opacity = '0';
                }, 3000);
            }
        } else {
            throw new Error('Transcription request failed');
        }
    } catch (error) {
        console.error('Transcription error:', error);
        statusText.textContent = 'Error processing audio. Please type manually.';
        statusText.style.color = 'var(--error)';
        setTimeout(() => {
            statusText.style.opacity = '0';
        }, 3000);
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
