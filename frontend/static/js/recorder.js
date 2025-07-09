class AudioRecorder {
    constructor() {
        this.mediaRecorder = null;
        this.audioChunks = [];
        this.isRecording = false;
        this.startTime = null;
        this.timerInterval = null;
        this.stream = null;
    }

    async initialize() {
        try {
            // Request microphone access
            this.stream = await navigator.mediaDevices.getUserMedia({ 
                audio: {
                    echoCancellation: true,
                    noiseSuppression: true,
                    autoGainControl: true
                } 
            });
            
            // Create MediaRecorder
            this.mediaRecorder = new MediaRecorder(this.stream, {
                mimeType: this.getSupportedMimeType()
            });
            
            // Set up event handlers
            this.mediaRecorder.ondataavailable = (event) => {
                if (event.data.size > 0) {
                    this.audioChunks.push(event.data);
                }
            };
            
            this.mediaRecorder.onstop = () => {
                this.handleRecordingStop();
            };
            
            return true;
        } catch (error) {
            console.error('Failed to initialize audio recorder:', error);
            throw new Error('Microphone access denied or not available');
        }
    }

    getSupportedMimeType() {
        const types = [
            'audio/webm;codecs=opus',
            'audio/webm',
            'audio/mp4',
            'audio/ogg;codecs=opus'
        ];
        
        for (const type of types) {
            if (MediaRecorder.isTypeSupported(type)) {
                return type;
            }
        }
        
        return 'audio/webm'; // Fallback
    }

    async startRecording() {
        if (!this.mediaRecorder) {
            await this.initialize();
        }
        
        if (this.isRecording) {
            return;
        }
        
        try {
            this.audioChunks = [];
            this.startTime = Date.now();
            this.isRecording = true;
            
            this.mediaRecorder.start(1000); // Collect data every second
            this.startTimer();
            
            return true;
        } catch (error) {
            console.error('Failed to start recording:', error);
            this.isRecording = false;
            throw error;
        }
    }

    stopRecording() {
        if (!this.isRecording || !this.mediaRecorder) {
            return;
        }
        
        this.isRecording = false;
        this.mediaRecorder.stop();
        this.stopTimer();
    }

    startTimer() {
        this.timerInterval = setInterval(() => {
            if (this.startTime) {
                const elapsed = Date.now() - this.startTime;
                const seconds = Math.floor(elapsed / 1000);
                const minutes = Math.floor(seconds / 60);
                const remainingSeconds = seconds % 60;
                
                const timeString = `${minutes.toString().padStart(2, '0')}:${remainingSeconds.toString().padStart(2, '0')}`;
                
                // Update UI
                const recordingTime = document.getElementById('recordingTime');
                if (recordingTime) {
                    recordingTime.textContent = `Recording: ${timeString}`;
                }
            }
        }, 1000);
    }

    stopTimer() {
        if (this.timerInterval) {
            clearInterval(this.timerInterval);
            this.timerInterval = null;
        }
    }

    handleRecordingStop() {
        if (this.audioChunks.length === 0) {
            console.warn('No audio data recorded');
            return;
        }
        
        // Create blob from recorded chunks
        const mimeType = this.getSupportedMimeType();
        const audioBlob = new Blob(this.audioChunks, { type: mimeType });
        
        // Calculate duration
        const duration = this.startTime ? (Date.now() - this.startTime) / 1000 : 0;
        const minutes = Math.floor(duration / 60);
        const seconds = Math.floor(duration % 60);
        const durationString = `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
        
        // Update UI with recording info
        const recordingTime = document.getElementById('recordingTime');
        const recordingDetails = document.getElementById('recordingDetails');
        const recordingInfo = document.getElementById('recordingInfo');
        
        if (recordingTime) {
            recordingTime.textContent = `Last recording duration: ${durationString}`;
        }
        
        if (recordingDetails) {
            const sizeKB = (audioBlob.size / 1024).toFixed(2);
            recordingDetails.textContent = `Recorded: ${mimeType}, Size: ${sizeKB} KB`;
        }
        
        if (recordingInfo) {
            recordingInfo.classList.remove('hidden');
        }
        
        // Trigger custom event with the recorded audio
        const event = new CustomEvent('recordingComplete', {
            detail: {
                audioBlob: audioBlob,
                duration: duration,
                mimeType: mimeType,
                size: audioBlob.size
            }
        });
        
        document.dispatchEvent(event);
    }

    getRecordedAudio() {
        if (this.audioChunks.length === 0) {
            return null;
        }
        
        const mimeType = this.getSupportedMimeType();
        return new Blob(this.audioChunks, { type: mimeType });
    }

    cleanup() {
        this.stopRecording();
        
        if (this.stream) {
            this.stream.getTracks().forEach(track => track.stop());
            this.stream = null;
        }
        
        this.mediaRecorder = null;
        this.audioChunks = [];
    }

    isSupported() {
        return !!(navigator.mediaDevices && 
                 navigator.mediaDevices.getUserMedia && 
                 window.MediaRecorder);
    }
}

// Export for use in other scripts
window.AudioRecorder = AudioRecorder;