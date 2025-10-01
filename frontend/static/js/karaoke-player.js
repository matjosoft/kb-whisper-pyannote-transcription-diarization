class KaraokePlayer {
    constructor() {
        this.audio = null;
        this.isPlaying = false;
        this.currentTime = 0;
        this.duration = 0;
        this.segments = [];
        this.currentSegmentIndex = -1;
        this.isVisible = false;
        this.isDragging = false;
        this.totalDuration = 0;
        
        this.initializeElements();
        this.setupEventListeners();
    }

    initializeElements() {
        // Main elements
        this.karaokePlayer = document.getElementById('karaokePlayer');
        this.karaokeContent = document.getElementById('karaokeContent');
        this.karaokeToggleBtn = document.getElementById('karaokeToggleBtn');
        
        // Audio controls
        this.playPauseBtn = document.getElementById('playPauseBtn');
        this.currentTimeDisplay = document.getElementById('currentTime');
        this.totalTimeDisplay = document.getElementById('totalTime');
        this.progressBar = document.getElementById('progressBar');
        this.progressFill = document.getElementById('progressFill');
        this.progressHandle = document.getElementById('progressHandle');
        this.volumeSlider = document.getElementById('volumeSlider');
        
        // Display elements
        this.speakerLanes = document.getElementById('speakerLanes');
        this.currentSpeaker = document.getElementById('currentSpeaker');
        this.currentText = document.getElementById('currentText');
    }

    setupEventListeners() {
        // Toggle karaoke view
        this.karaokeToggleBtn.addEventListener('click', () => this.toggleKaraokeView());
        
        // Audio controls
        this.playPauseBtn.addEventListener('click', () => this.togglePlayPause());
        this.volumeSlider.addEventListener('input', (e) => this.setVolume(e.target.value));
        
        // Progress bar interactions
        this.progressBar.addEventListener('click', (e) => this.seekToPosition(e));
        this.progressHandle.addEventListener('mousedown', (e) => this.startDragging(e));
        document.addEventListener('mousemove', (e) => this.handleDragging(e));
        document.addEventListener('mouseup', () => this.stopDragging());
        
        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => this.handleKeyboard(e));
    }

    toggleKaraokeView() {
        this.isVisible = !this.isVisible;
        
        if (this.isVisible) {
            this.karaokeContent.classList.remove('hidden');
            this.karaokeToggleBtn.innerHTML = '<span>🎵</span> Hide Karaoke View';
        } else {
            this.karaokeContent.classList.add('hidden');
            this.karaokeToggleBtn.innerHTML = '<span>🎵</span> Show Karaoke View';
            this.pause();
        }
    }

    async loadAudio(audioFile, segments) {
        try {
            // Create audio element
            if (this.audio) {
                this.audio.pause();
                this.audio = null;
            }
            
            this.audio = new Audio();
            this.segments = segments || [];
            
            // Set up audio event listeners
            this.audio.addEventListener('loadedmetadata', () => {
                this.duration = this.audio.duration;
                this.totalDuration = this.duration;
                this.totalTimeDisplay.textContent = this.formatTime(this.duration);
                this.createSpeakerLanes();
            });
            
            this.audio.addEventListener('timeupdate', () => {
                if (!this.isDragging) {
                    this.updateProgress();
                    this.updateCurrentSegment();
                }
            });
            
            this.audio.addEventListener('ended', () => {
                this.isPlaying = false;
                this.updatePlayPauseButton();
                this.currentTime = 0;
                this.updateProgress();
            });
            
            this.audio.addEventListener('error', (e) => {
                console.error('Audio loading error:', e);
                alert('Failed to load audio file');
            });
            
            // Load the audio file
            if (audioFile instanceof File) {
                const audioUrl = URL.createObjectURL(audioFile);
                this.audio.src = audioUrl;
            } else if (typeof audioFile === 'string') {
                this.audio.src = audioFile;
            }
            
            // Set initial volume
            this.audio.volume = this.volumeSlider.value / 100;
            
        } catch (error) {
            console.error('Error loading audio:', error);
            alert('Failed to load audio: ' + error.message);
        }
    }

    createSpeakerLanes() {
        if (!this.segments || this.segments.length === 0) {
            this.speakerLanes.innerHTML = '<p style="text-align: center; opacity: 0.7;">No transcription data available</p>';
            return;
        }

        // Get unique speakers
        const speakers = [...new Set(this.segments.map(seg => seg.speaker))];

        this.speakerLanes.innerHTML = '';

        speakers.forEach((speaker, index) => {
            const laneDiv = document.createElement('div');
            laneDiv.className = `speaker-lane speaker-lane-${(index % 5) + 1}`;

            // Speaker label (truncate to 8 characters)
            const labelDiv = document.createElement('div');
            labelDiv.className = 'speaker-label';
            const truncatedName = speaker.length > 8 ? speaker.substring(0, 8) + '...' : speaker;
            labelDiv.textContent = truncatedName;
            labelDiv.title = speaker; // Show full name on hover
            
            // Timeline
            const timelineDiv = document.createElement('div');
            timelineDiv.className = 'lane-timeline';
            
            // Add segments for this speaker
            const speakerSegments = this.segments.filter(seg => seg.speaker === speaker);
            speakerSegments.forEach((segment, segIndex) => {
                const segmentDiv = document.createElement('div');
                segmentDiv.className = 'text-segment';
                segmentDiv.textContent = segment.text;
                segmentDiv.title = `${this.formatTime(segment.start)} - ${this.formatTime(segment.end)}: ${segment.text}`;
                
                // Calculate position and width based on time
                const startPercent = (segment.start / this.totalDuration) * 100;
                const widthPercent = ((segment.end - segment.start) / this.totalDuration) * 100;
                
                segmentDiv.style.left = `${startPercent}%`;
                segmentDiv.style.width = `${widthPercent}%`;
                
                // Add click handler to seek to segment
                segmentDiv.addEventListener('click', () => {
                    this.seekToTime(segment.start);
                });
                
                timelineDiv.appendChild(segmentDiv);
            });
            
            laneDiv.appendChild(labelDiv);
            laneDiv.appendChild(timelineDiv);
            this.speakerLanes.appendChild(laneDiv);
        });
    }

    updateProgress() {
        if (!this.audio) return;
        
        this.currentTime = this.audio.currentTime;
        this.currentTimeDisplay.textContent = this.formatTime(this.currentTime);
        
        if (this.duration > 0) {
            const progressPercent = (this.currentTime / this.duration) * 100;
            this.progressFill.style.width = `${progressPercent}%`;
            this.progressHandle.style.left = `${progressPercent}%`;
        }
    }

    updateCurrentSegment() {
        if (!this.segments || this.segments.length === 0) return;
        
        // Find current segment
        const currentSegment = this.segments.find(segment => 
            this.currentTime >= segment.start && this.currentTime <= segment.end
        );
        
        if (currentSegment) {
            const segmentIndex = this.segments.indexOf(currentSegment);
            
            if (segmentIndex !== this.currentSegmentIndex) {
                this.currentSegmentIndex = segmentIndex;
                
                // Update current text display
                this.currentSpeaker.textContent = currentSegment.speaker;
                this.currentSpeaker.className = `current-speaker ${this.getSpeakerClass(currentSegment.speaker)}`;
                this.currentText.textContent = currentSegment.text;
                
                // Highlight active segment in lanes
                this.highlightActiveSegment(currentSegment);
            }
        } else {
            // No current segment
            if (this.currentSegmentIndex !== -1) {
                this.currentSegmentIndex = -1;
                this.currentSpeaker.textContent = 'Speaker';
                this.currentSpeaker.className = 'current-speaker';
                this.currentText.textContent = 'Audio text will appear here as it plays...';
                this.clearActiveSegments();
            }
        }
    }

    highlightActiveSegment(activeSegment) {
        // Remove previous highlights
        this.clearActiveSegments();
        
        // Find and highlight the active segment
        const textSegments = this.speakerLanes.querySelectorAll('.text-segment');
        textSegments.forEach(segmentEl => {
            const segmentText = segmentEl.textContent;
            if (segmentText === activeSegment.text && 
                segmentEl.closest('.speaker-lane').querySelector('.speaker-label').textContent === activeSegment.speaker) {
                segmentEl.classList.add('active');
            }
        });
    }

    clearActiveSegments() {
        const activeSegments = this.speakerLanes.querySelectorAll('.text-segment.active');
        activeSegments.forEach(segment => segment.classList.remove('active'));
    }

    getSpeakerClass(speaker) {
        const speakerNumber = speaker.match(/\d+/);
        return speakerNumber ? `speaker-${speakerNumber[0]}` : 'speaker-1';
    }

    togglePlayPause() {
        if (!this.audio) {
            alert('No audio loaded');
            return;
        }
        
        if (this.isPlaying) {
            this.pause();
        } else {
            this.play();
        }
    }

    play() {
        if (!this.audio) return;
        
        this.audio.play().then(() => {
            this.isPlaying = true;
            this.updatePlayPauseButton();
        }).catch(error => {
            console.error('Play error:', error);
            alert('Failed to play audio');
        });
    }

    pause() {
        if (!this.audio) return;
        
        this.audio.pause();
        this.isPlaying = false;
        this.updatePlayPauseButton();
    }

    updatePlayPauseButton() {
        const icon = this.playPauseBtn.querySelector('.play-icon');
        if (this.isPlaying) {
            icon.textContent = '⏸️';
        } else {
            icon.textContent = '▶️';
        }
    }

    setVolume(value) {
        if (!this.audio) return;
        
        this.audio.volume = value / 100;
    }

    seekToPosition(event) {
        if (!this.audio || this.isDragging) return;
        
        const rect = this.progressBar.getBoundingClientRect();
        const clickX = event.clientX - rect.left;
        const progressPercent = clickX / rect.width;
        const seekTime = progressPercent * this.duration;
        
        this.seekToTime(seekTime);
    }

    seekToTime(time) {
        if (!this.audio) return;
        
        this.audio.currentTime = Math.max(0, Math.min(time, this.duration));
        this.updateProgress();
    }

    startDragging(event) {
        event.preventDefault();
        this.isDragging = true;
        this.progressHandle.style.cursor = 'grabbing';
    }

    handleDragging(event) {
        if (!this.isDragging || !this.audio) return;
        
        const rect = this.progressBar.getBoundingClientRect();
        const dragX = event.clientX - rect.left;
        const progressPercent = Math.max(0, Math.min(1, dragX / rect.width));
        const seekTime = progressPercent * this.duration;
        
        // Update visual progress
        this.progressFill.style.width = `${progressPercent * 100}%`;
        this.progressHandle.style.left = `${progressPercent * 100}%`;
        this.currentTimeDisplay.textContent = this.formatTime(seekTime);
    }

    stopDragging() {
        if (!this.isDragging) return;
        
        this.isDragging = false;
        this.progressHandle.style.cursor = 'pointer';
        
        // Seek to the dragged position
        if (this.audio) {
            const progressPercent = parseFloat(this.progressFill.style.width) / 100;
            const seekTime = progressPercent * this.duration;
            this.seekToTime(seekTime);
        }
    }

    handleKeyboard(event) {
        if (!this.isVisible || !this.audio) return;
        
        // Only handle if not typing in an input field
        if (event.target.tagName === 'INPUT' || event.target.tagName === 'TEXTAREA') return;
        
        switch (event.code) {
            case 'Space':
                event.preventDefault();
                this.togglePlayPause();
                break;
            case 'ArrowLeft':
                event.preventDefault();
                this.seekToTime(this.currentTime - 5); // Skip back 5 seconds
                break;
            case 'ArrowRight':
                event.preventDefault();
                this.seekToTime(this.currentTime + 5); // Skip forward 5 seconds
                break;
            case 'ArrowUp':
                event.preventDefault();
                const currentVolume = parseInt(this.volumeSlider.value);
                this.volumeSlider.value = Math.min(100, currentVolume + 10);
                this.setVolume(this.volumeSlider.value);
                break;
            case 'ArrowDown':
                event.preventDefault();
                const currentVol = parseInt(this.volumeSlider.value);
                this.volumeSlider.value = Math.max(0, currentVol - 10);
                this.setVolume(this.volumeSlider.value);
                break;
        }
    }

    formatTime(seconds) {
        if (isNaN(seconds)) return '00:00';
        
        const minutes = Math.floor(seconds / 60);
        const remainingSeconds = Math.floor(seconds % 60);
        return `${minutes.toString().padStart(2, '0')}:${remainingSeconds.toString().padStart(2, '0')}`;
    }

    // Public method to load transcription results
    loadTranscriptionResults(results, audioFile = null) {
        if (!results || !results.segments) {
            console.warn('No transcription results provided');
            return;
        }
        
        this.segments = results.segments;
        
        if (audioFile) {
            this.loadAudio(audioFile, this.segments);
        } else {
            // If no audio file provided, just create the lanes with the segments
            // Estimate duration from the last segment
            if (this.segments.length > 0) {
                this.totalDuration = Math.max(...this.segments.map(s => s.end));
                this.duration = this.totalDuration;
                this.totalTimeDisplay.textContent = this.formatTime(this.duration);
                this.createSpeakerLanes();
            }
        }
    }

    // Public method to update speaker names
    updateSpeakerNames(speakerNames) {
        if (!this.segments || this.segments.length === 0) {
            return;
        }

        // Store original speaker IDs on first call to preserve mapping
        if (!this.originalSpeakerIds) {
            this.originalSpeakerIds = {};
            this.segments.forEach(segment => {
                if (!this.originalSpeakerIds[segment.speaker]) {
                    this.originalSpeakerIds[segment.speaker] = segment.speaker;
                }
            });
        }

        // Update segments with new speaker names using the stored original IDs
        this.segments = this.segments.map(segment => {
            // Use the stored originalSpeakerId if it exists, otherwise look it up
            const originalId = segment.originalSpeakerId || this.originalSpeakerIds[segment.speaker] || segment.speaker;
            const newSpeakerName = speakerNames[originalId] || segment.speaker;
            return {
                ...segment,
                speaker: newSpeakerName,
                originalSpeakerId: originalId
            };
        });

        // Recreate speaker lanes with updated names
        this.createSpeakerLanes();

        // Update current display if there's an active segment
        if (this.currentSegmentIndex >= 0 && this.currentSegmentIndex < this.segments.length) {
            const currentSegment = this.segments[this.currentSegmentIndex];
            this.currentSpeaker.textContent = currentSegment.speaker;
            this.currentSpeaker.className = `current-speaker ${this.getSpeakerClass(currentSegment.speaker)}`;
        }
    }

    // Clean up resources
    destroy() {
        if (this.audio) {
            this.audio.pause();
            this.audio = null;
        }
        
        this.segments = [];
        this.currentSegmentIndex = -1;
        this.isPlaying = false;
    }
}

// Export for use in other scripts
window.KaraokePlayer = KaraokePlayer;
