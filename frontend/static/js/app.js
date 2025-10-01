class AudioScribeApp {
    constructor() {
        this.recorder = null;
        this.currentResults = null;
        this.speakerNames = {};
        this.isProcessing = false;
        this.karaokePlayer = null;
        this.currentAudioFile = null;
        
        this.initializeElements();
        this.setupEventListeners();
        this.initializeRecorder();
        this.initializeKaraokePlayer();
    }

    initializeElements() {
        // Recording elements
        this.recordBtn = document.getElementById('recordBtn');
        this.recordingStatus = document.getElementById('recordingStatus');
        this.recordingInfo = document.getElementById('recordingInfo');
        
        // Upload elements
        this.uploadArea = document.getElementById('uploadArea');
        this.fileInput = document.getElementById('fileInput');
        
        // Processing elements
        this.processingSection = document.getElementById('processingSection');
        this.processingText = document.getElementById('processingText');
        
        // Results elements
        this.resultsSection = document.getElementById('resultsSection');
        this.speakerEditor = document.getElementById('speakerEditor');
        this.speakerInputs = document.getElementById('speakerInputs');
        this.transcriptionDisplay = document.getElementById('transcriptionDisplay');
        this.exportBtn = document.getElementById('exportBtn');
        this.clearBtn = document.getElementById('clearBtn');
    }

    setupEventListeners() {
        // Recording button
        this.recordBtn.addEventListener('click', () => this.toggleRecording());
        
        // File upload
        this.uploadArea.addEventListener('click', () => this.fileInput.click());
        this.uploadArea.addEventListener('dragover', (e) => this.handleDragOver(e));
        this.uploadArea.addEventListener('dragleave', (e) => this.handleDragLeave(e));
        this.uploadArea.addEventListener('drop', (e) => this.handleDrop(e));
        this.fileInput.addEventListener('change', (e) => this.handleFileSelect(e));
        
        // Recording completion
        document.addEventListener('recordingComplete', (e) => this.handleRecordingComplete(e));
        
        // Action buttons
        this.exportBtn.addEventListener('click', () => this.exportResults());
        this.clearBtn.addEventListener('click', () => this.clearResults());
    }

    async initializeRecorder() {
        try {
            if (!AudioRecorder || !new AudioRecorder().isSupported()) {
                this.recordBtn.disabled = true;
                this.recordBtn.textContent = 'Recording not supported';
                return;
            }
            
            this.recorder = new AudioRecorder();
        } catch (error) {
            console.error('Failed to initialize recorder:', error);
            this.recordBtn.disabled = true;
            this.recordBtn.textContent = 'Recording unavailable';
        }
    }

    initializeKaraokePlayer() {
        try {
            if (typeof KaraokePlayer !== 'undefined') {
                this.karaokePlayer = new KaraokePlayer();
            } else {
                console.warn('KaraokePlayer not available');
            }
        } catch (error) {
            console.error('Failed to initialize karaoke player:', error);
        }
    }

    async toggleRecording() {
        if (!this.recorder) {
            alert('Recording is not available');
            return;
        }

        try {
            if (this.recorder.isRecording) {
                this.stopRecording();
            } else {
                await this.startRecording();
            }
        } catch (error) {
            console.error('Recording error:', error);
            alert('Recording failed: ' + error.message);
        }
    }

    async startRecording() {
        await this.recorder.startRecording();
        
        this.recordBtn.innerHTML = '<span class="record-icon">⏹️</span> Stop Recording';
        this.recordBtn.classList.add('recording');
        this.recordingStatus.classList.remove('hidden');
        this.recordingInfo.classList.add('hidden');
    }

    stopRecording() {
        this.recorder.stopRecording();
        
        this.recordBtn.innerHTML = '<span class="record-icon">🎙️</span> Start Recording';
        this.recordBtn.classList.remove('recording');
        this.recordingStatus.classList.add('hidden');
    }

    handleRecordingComplete(event) {
        const { audioBlob } = event.detail;
        // Store the audio blob for karaoke player
        this.currentAudioFile = audioBlob;
        this.processAudio(audioBlob, 'recording');
    }

    handleDragOver(e) {
        e.preventDefault();
        this.uploadArea.classList.add('dragover');
    }

    handleDragLeave(e) {
        e.preventDefault();
        this.uploadArea.classList.remove('dragover');
    }

    handleDrop(e) {
        e.preventDefault();
        this.uploadArea.classList.remove('dragover');
        
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            this.handleFile(files[0]);
        }
    }

    handleFileSelect(e) {
        const files = e.target.files;
        if (files.length > 0) {
            this.handleFile(files[0]);
        }
    }

    handleFile(file) {
        // Validate file type
        if (!file.type.startsWith('audio/')) {
            alert('Please select an audio file');
            return;
        }
        
        // Validate file size (100MB limit)
        const maxSize = 800 * 1024 * 1024;
        if (file.size > maxSize) {
            alert('File size must be less than 800MB');
            return;
        }
        
        // Store the audio file for karaoke player
        this.currentAudioFile = file;
        this.processAudio(file, 'upload');
    }

    async processAudio(audioData, source) {
        if (this.isProcessing) {
            alert('Already processing audio. Please wait...');
            return;
        }

        this.isProcessing = true;
        this.showProcessing('Uploading audio...');
        
        try {
            let fileId;
            
            if (source === 'recording') {
                fileId = await this.saveRecording(audioData);
            } else {
                fileId = await this.uploadFile(audioData);
            }
            
            this.showProcessing('Transcribing and analyzing speakers...');
            const results = await this.transcribeAudio(fileId);
            
            // Only hide processing after successful completion
            this.hideProcessing();
            this.displayResults(results);
            
        } catch (error) {
            console.error('Processing error:', error);
            this.hideProcessing(); // Hide processing on error
            alert('Processing failed: ' + error.message);
        } finally {
            this.isProcessing = false;
        }
    }

    async saveRecording(audioBlob) {
        const formData = new FormData();
        formData.append('audio', audioBlob, 'recording.webm');
        
        const response = await fetch('/api/save-recording', {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            throw new Error('Failed to save recording');
        }
        
        const result = await response.json();
        return result.file_id;
    }

    async uploadFile(file) {
        const formData = new FormData();
        formData.append('file', file);
        
        const response = await fetch('/api/upload', {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            throw new Error('Failed to upload file');
        }
        
        const result = await response.json();
        return result.file_id;
    }

    async transcribeAudio(fileId) {
        console.log('Starting transcription...');
        
        // Initialize progress visualization immediately
        console.log('Initializing chunk progress...');
        this.initializeChunkProgress();
        
        // Always use streaming endpoint - it handles both streaming and fallback internally
        return await this.transcribeWithStreaming(fileId);
    }
    
    async transcribeWithStreaming(fileId) {
        return new Promise((resolve, reject) => {
            console.log('Attempting streaming transcription...');
            const eventSource = new EventSource(`/api/transcribe-stream/${fileId}`);
            let finalResult = null;
            let hasReceivedData = false;
            
            eventSource.onmessage = (event) => {
                try {
                    hasReceivedData = true;
                    const data = JSON.parse(event.data);
                    console.log('Received streaming data:', data);
                    
                    if (data.error) {
                        eventSource.close();
                        reject(new Error(data.error));
                        return;
                    }
                    
                    // Update progress based on status
                    this.updateTranscriptionProgress(data);
                    
                    if (data.status === 'completed' && data.result) {
                        finalResult = data.result;
                        eventSource.close();
                        resolve(finalResult);
                    } else if (data.status === 'error') {
                        eventSource.close();
                        reject(new Error(data.message || 'Transcription failed'));
                    }
                } catch (error) {
                    console.error('Error parsing SSE data:', error);
                    eventSource.close();
                    reject(error);
                }
            };
            
            eventSource.onerror = (error) => {
                console.error('EventSource error:', error);
                eventSource.close();
                if (!hasReceivedData) {
                    reject(new Error('Streaming connection failed'));
                } else if (!finalResult) {
                    reject(new Error('Connection to transcription service failed'));
                }
            };
            
            // Shorter timeout for streaming to allow fallback
            setTimeout(() => {
                if (!hasReceivedData) {
                    console.log('Streaming timeout, will fallback');
                    eventSource.close();
                    reject(new Error('Streaming timeout'));
                }
            }, 5000); // 5 second timeout for initial connection
        });
    }
    
    
    
    initializeChunkProgress() {
        console.log('initializeChunkProgress called');
        const chunkProgressContainer = document.getElementById('chunkProgressContainer');
        const chunksVisualization = document.getElementById('chunksVisualization');
        const overallProgressFill = document.getElementById('overallProgressFill');
        const overallProgressPercentage = document.getElementById('overallProgressPercentage');
        const progressStats = document.getElementById('progressStats');
        const progressTime = document.getElementById('progressTime');
        const currentChunkText = document.getElementById('currentChunkText');
        
        console.log('Processing section element:', this.processingSection);
        console.log('Chunk progress container element:', chunkProgressContainer);
        
        // Make sure processing section is visible
        if (this.processingSection) {
            console.log('Removing hidden class from processing section');
            this.processingSection.classList.remove('hidden');
            console.log('Processing section classes after removal:', this.processingSection.className);
        } else {
            console.error('Processing section element not found!');
        }
        
        // Reset and show progress elements
        if (chunkProgressContainer) {
            console.log('Removing hidden class from chunk progress container');
            chunkProgressContainer.classList.remove('hidden');
            console.log('Chunk progress container classes after removal:', chunkProgressContainer.className);
        } else {
            console.error('Chunk progress container element not found!');
        }
        
        if (chunksVisualization) {
            chunksVisualization.innerHTML = '';
        }
        if (overallProgressFill) {
            overallProgressFill.style.width = '0%';
        }
        if (overallProgressPercentage) {
            overallProgressPercentage.textContent = '0%';
        }
        if (progressStats) {
            progressStats.textContent = '0 / 0 chunks processed';
        }
        if (progressTime) {
            progressTime.textContent = 'Duration: 0.0s';
        }
        if (currentChunkText) {
            currentChunkText.textContent = 'Preparing...';
        }
        
        console.log('initializeChunkProgress completed');
    }
    
    updateTranscriptionProgress(data) {
        console.log('Updating transcription progress:', data);
        
        const progressStats = document.getElementById('progressStats');
        const progressTime = document.getElementById('progressTime');
        const currentChunkText = document.getElementById('currentChunkText');
        const overallProgressFill = document.getElementById('overallProgressFill');
        const overallProgressPercentage = document.getElementById('overallProgressPercentage');
        const chunksVisualization = document.getElementById('chunksVisualization');
        
        console.log('Progress elements found:', {
            progressStats: !!progressStats,
            progressTime: !!progressTime,
            currentChunkText: !!currentChunkText,
            overallProgressFill: !!overallProgressFill,
            overallProgressPercentage: !!overallProgressPercentage,
            chunksVisualization: !!chunksVisualization
        });
        
        // Update current status message
        if (currentChunkText) {
            currentChunkText.textContent = data.message || 'Processing...';
        }
        
        switch (data.status) {
            case 'starting':
                if (currentChunkText) {
                    currentChunkText.textContent = data.message;
                }
                break;
                
            case 'transcribing':
                if (data.total_chunks && data.duration) {
                    if (progressStats) {
                        progressStats.textContent = `0 / ${data.total_chunks} chunks processed`;
                    }
                    if (progressTime) {
                        progressTime.textContent = `Duration: ${data.duration.toFixed(1)}s`;
                    }
                    
                    // Create chunk blocks
                    this.createChunkBlocks(data.total_chunks);
                }
                break;
                
            case 'processing_chunk':
                if (data.chunk_index !== undefined && data.total_chunks) {
                    const completedChunks = data.chunk_index;
                    const totalChunks = data.total_chunks;
                    const progressPercent = Math.round((completedChunks / totalChunks) * 100);
                    
                    if (progressStats) {
                        progressStats.textContent = `${completedChunks} / ${totalChunks} chunks processed`;
                    }
                    if (overallProgressFill) {
                        overallProgressFill.style.width = `${progressPercent}%`;
                    }
                    if (overallProgressPercentage) {
                        overallProgressPercentage.textContent = `${progressPercent}%`;
                    }
                    
                    // Update chunk visualization
                    this.updateChunkBlock(data.chunk_index, 'processing');
                    
                    // Mark previous chunks as completed
                    for (let i = 0; i < data.chunk_index; i++) {
                        this.updateChunkBlock(i, 'completed');
                    }
                }
                break;
                
            case 'finalizing_transcription':
            case 'diarizing':
            case 'merging':
                // Mark all chunks as completed during final processing
                const allChunks = chunksVisualization.querySelectorAll('.chunk-block');
                allChunks.forEach(chunk => {
                    chunk.className = 'chunk-block completed';
                });
                overallProgressFill.style.width = '90%';
                overallProgressPercentage.textContent = '90%';
                break;
                
            case 'completed':
                overallProgressFill.style.width = '100%';
                overallProgressPercentage.textContent = '100%';
                currentChunkText.textContent = 'Transcription completed successfully!';
                
                // Mark all chunks as completed
                const completedChunks = chunksVisualization.querySelectorAll('.chunk-block');
                completedChunks.forEach(chunk => {
                    chunk.className = 'chunk-block completed';
                });
                break;
                
            case 'error':
                currentChunkText.textContent = data.message || 'An error occurred';
                
                // Mark current chunk as error
                if (data.chunk_index !== undefined) {
                    this.updateChunkBlock(data.chunk_index, 'error');
                }
                break;
        }
    }
    
    createChunkBlocks(totalChunks) {
        const chunksVisualization = document.getElementById('chunksVisualization');
        chunksVisualization.innerHTML = '';
        
        for (let i = 0; i < totalChunks; i++) {
            const chunkBlock = document.createElement('div');
            chunkBlock.className = 'chunk-block pending';
            chunkBlock.textContent = i + 1;
            chunkBlock.id = `chunk-${i}`;
            chunkBlock.title = `Chunk ${i + 1}`;
            chunksVisualization.appendChild(chunkBlock);
        }
    }
    
    updateChunkBlock(chunkIndex, status) {
        const chunkBlock = document.getElementById(`chunk-${chunkIndex}`);
        if (chunkBlock) {
            chunkBlock.className = `chunk-block ${status}`;
        }
    }

    showProcessing(message) {
        this.processingText.textContent = message;
        this.processingSection.classList.remove('hidden');
        this.resultsSection.classList.add('hidden');
        
        // Don't hide chunk progress initially - let initializeChunkProgress handle visibility
        // The chunk progress will be shown when transcription starts
    }

    hideProcessing() {
        this.processingSection.classList.add('hidden');
        
        // Also hide chunk progress
        const chunkProgressContainer = document.getElementById('chunkProgressContainer');
        if (chunkProgressContainer) {
            chunkProgressContainer.classList.add('hidden');
        }
    }

    displayResults(results) {
        this.currentResults = results;
        this.speakerNames = { ...results.speakers };
        
        this.createSpeakerEditor(results.speakers);
        this.displayTranscription(results.segments);
        
        // Load results into karaoke player
        if (this.karaokePlayer && this.currentResults) {
            this.karaokePlayer.loadTranscriptionResults(this.currentResults, this.currentAudioFile);
        }
        
        this.resultsSection.classList.remove('hidden');
    }

    createSpeakerEditor(speakers) {
        this.speakerInputs.innerHTML = '';
        
        Object.keys(speakers).forEach(speakerId => {
            const inputGroup = document.createElement('div');
            inputGroup.className = 'speaker-input-group';
            
            const label = document.createElement('label');
            label.textContent = speakerId + ':';
            
            const input = document.createElement('input');
            input.type = 'text';
            input.value = speakers[speakerId];
            input.placeholder = `Enter name for ${speakerId}`;
            input.addEventListener('input', (e) => {
                this.speakerNames[speakerId] = e.target.value || speakerId;
                this.updateTranscriptionDisplay();
            });
            
            inputGroup.appendChild(label);
            inputGroup.appendChild(input);
            this.speakerInputs.appendChild(inputGroup);
        });
    }

    displayTranscription(segments) {
        this.transcriptionDisplay.innerHTML = '';
        
        segments.forEach((segment, index) => {
            const segmentDiv = document.createElement('div');
            segmentDiv.className = `transcription-segment ${this.getSpeakerClass(segment.speaker)}`;
            
            const header = document.createElement('div');
            header.className = 'segment-header';
            
            const speakerName = document.createElement('span');
            speakerName.className = 'speaker-name';
            speakerName.textContent = this.speakerNames[segment.speaker] || segment.speaker;
            
            const timeStamp = document.createElement('span');
            timeStamp.className = 'segment-time';
            timeStamp.textContent = `[${this.formatTime(segment.start)} - ${this.formatTime(segment.end)}]`;
            
            header.appendChild(speakerName);
            header.appendChild(timeStamp);
            
            const text = document.createElement('div');
            text.className = 'segment-text';
            text.textContent = segment.text;
            
            segmentDiv.appendChild(header);
            segmentDiv.appendChild(text);
            this.transcriptionDisplay.appendChild(segmentDiv);
        });
    }

    updateTranscriptionDisplay() {
        const speakerNameElements = this.transcriptionDisplay.querySelectorAll('.speaker-name');
        speakerNameElements.forEach(element => {
            const segment = element.closest('.transcription-segment');
            const speakerId = Object.keys(this.speakerNames).find(id =>
                segment.classList.contains(this.getSpeakerClass(id))
            );
            if (speakerId) {
                element.textContent = this.speakerNames[speakerId] || speakerId;
            }
        });

        // Update karaoke player with new speaker names
        if (this.karaokePlayer) {
            this.karaokePlayer.updateSpeakerNames(this.speakerNames);
        }
    }

    getSpeakerClass(speaker) {
        const speakerNumber = speaker.match(/\d+/);
        return speakerNumber ? `speaker-${speakerNumber[0]}` : 'speaker-1';
    }

    formatTime(seconds) {
        const minutes = Math.floor(seconds / 60);
        const remainingSeconds = Math.floor(seconds % 60);
        return `${minutes.toString().padStart(2, '0')}:${remainingSeconds.toString().padStart(2, '0')}.${Math.floor((seconds % 1) * 1000).toString().padStart(3, '0')}`;
    }

    exportResults() {
        if (!this.currentResults) {
            alert('No results to export');
            return;
        }
        
        const exportData = {
            ...this.currentResults,
            speakers: this.speakerNames,
            segments: this.currentResults.segments.map(segment => ({
                ...segment,
                speaker: this.speakerNames[segment.speaker] || segment.speaker
            }))
        };
        
        const dataStr = JSON.stringify(exportData, null, 2);
        const dataBlob = new Blob([dataStr], { type: 'application/json' });
        
        const link = document.createElement('a');
        link.href = URL.createObjectURL(dataBlob);
        link.download = `transcription_${new Date().toISOString().slice(0, 19).replace(/:/g, '-')}.json`;
        link.click();
        
        URL.revokeObjectURL(link.href);
    }

    clearResults() {
        this.currentResults = null;
        this.speakerNames = {};
        this.currentAudioFile = null;
        this.resultsSection.classList.add('hidden');
        this.recordingInfo.classList.add('hidden');
        this.fileInput.value = '';
        
        // Clean up karaoke player
        if (this.karaokePlayer) {
            this.karaokePlayer.destroy();
        }
    }
}

// Initialize the app when the page loads
document.addEventListener('DOMContentLoaded', () => {
    new AudioScribeApp();
});
