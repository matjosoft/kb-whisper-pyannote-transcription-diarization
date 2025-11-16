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

        // Editing state
        this.editMode = false;
        this.editedSegments = new Set();
        this.draggingBoundary = null;
        this.draggingSegment = null;
        this.editingSegment = null;

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

        // Edit mode elements
        this.editModeBtn = document.getElementById('editModeBtn');
        this.saveEditsBtn = document.getElementById('saveEditsBtn');
        this.editModeHelp = document.getElementById('editModeHelp');
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

        // Edit mode controls
        if (this.editModeBtn) {
            this.editModeBtn.addEventListener('click', () => this.toggleEditMode());
        }
        if (this.saveEditsBtn) {
            this.saveEditsBtn.addEventListener('click', () => this.saveEdits());
        }

        // Global mouse handlers for boundary dragging
        document.addEventListener('mousemove', (e) => this.handleBoundaryDrag(e));
        document.addEventListener('mouseup', () => this.stopBoundaryDrag());

        // Global mouse handlers for segment dragging
        document.addEventListener('mousemove', (e) => this.handleSegmentDrag(e));
        document.addEventListener('mouseup', () => this.stopSegmentDrag());
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
                // Find the global index of this segment
                const globalSegmentIndex = this.segments.indexOf(segment);

                const segmentDiv = document.createElement('div');
                segmentDiv.className = 'text-segment';
                if (this.editedSegments.has(globalSegmentIndex)) {
                    segmentDiv.classList.add('edited');
                }
                segmentDiv.textContent = segment.text;
                segmentDiv.title = `${this.formatTime(segment.start)} - ${this.formatTime(segment.end)}: ${segment.text}`;

                // Calculate position and width based on time
                const startPercent = (segment.start / this.totalDuration) * 100;
                const widthPercent = ((segment.end - segment.start) / this.totalDuration) * 100;

                segmentDiv.style.left = `${startPercent}%`;
                segmentDiv.style.width = `${widthPercent}%`;

                if (this.editMode) {
                    // Add editing capabilities
                    segmentDiv.classList.add('editable');

                    // Add boundary handles for resizing
                    const leftHandle = document.createElement('div');
                    leftHandle.className = 'boundary-handle left-handle';
                    leftHandle.title = 'Drag to adjust start time';
                    leftHandle.addEventListener('mousedown', (e) => {
                        this.startBoundaryDrag(e, globalSegmentIndex, 'start', segmentDiv);
                    });

                    const rightHandle = document.createElement('div');
                    rightHandle.className = 'boundary-handle right-handle';
                    rightHandle.title = 'Drag to adjust end time';
                    rightHandle.addEventListener('mousedown', (e) => {
                        this.startBoundaryDrag(e, globalSegmentIndex, 'end', segmentDiv);
                    });

                    segmentDiv.appendChild(leftHandle);
                    segmentDiv.appendChild(rightHandle);

                    // Double-click to edit text
                    segmentDiv.addEventListener('dblclick', (e) => {
                        e.stopPropagation();
                        this.startTextEdit(segmentDiv, segment, globalSegmentIndex);
                    });

                    // Click and drag to move between speakers
                    segmentDiv.addEventListener('mousedown', (e) => {
                        if (!e.target.classList.contains('boundary-handle')) {
                            this.startSegmentDrag(e, segment, globalSegmentIndex, segmentDiv);
                        }
                    });

                    // Single click still seeks in edit mode
                    segmentDiv.addEventListener('click', (e) => {
                        if (!this.draggingSegment && !this.editingSegment) {
                            this.seekToTime(segment.start);
                        }
                    });
                } else {
                    // Normal mode: click to seek
                    segmentDiv.addEventListener('click', () => {
                        this.seekToTime(segment.start);
                    });
                }

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

    // Edit mode methods
    toggleEditMode() {
        this.editMode = !this.editMode;

        if (this.editMode) {
            this.editModeBtn.innerHTML = '<span>✏️</span> Exit Edit Mode';
            this.editModeBtn.classList.add('active');
            this.saveEditsBtn.classList.remove('hidden');
            if (this.editModeHelp) {
                this.editModeHelp.classList.remove('hidden');
            }
            if (this.isPlaying) {
                this.pause();
            }
        } else {
            this.editModeBtn.innerHTML = '<span>✏️</span> Edit Transcript';
            this.editModeBtn.classList.remove('active');
            this.saveEditsBtn.classList.add('hidden');
            if (this.editModeHelp) {
                this.editModeHelp.classList.add('hidden');
            }
        }

        // Recreate speaker lanes with edit mode
        this.createSpeakerLanes();
    }

    saveEdits() {
        if (this.editedSegments.size === 0) {
            window.toast.info('No Changes', 'No edits have been made to save');
            return;
        }

        const editedCount = this.editedSegments.size;

        // Dispatch event to notify main app of changes
        const event = new CustomEvent('transcriptEdited', {
            detail: {
                segments: this.segments,
                editedCount: editedCount
            }
        });
        document.dispatchEvent(event);

        // Clear edited segments tracking
        this.editedSegments.clear();

        // Update visual feedback
        const editedMarkers = this.speakerLanes.querySelectorAll('.text-segment.edited');
        editedMarkers.forEach(marker => marker.classList.remove('edited'));
    }

    startTextEdit(segmentElement, segmentData, segmentIndex) {
        if (!this.editMode) return;

        this.editingSegment = { element: segmentElement, data: segmentData, index: segmentIndex };

        // Create input element
        const input = document.createElement('input');
        input.type = 'text';
        input.value = segmentData.text;
        input.className = 'segment-text-editor';
        input.style.width = '100%';
        input.style.height = '100%';
        input.style.border = 'none';
        input.style.background = 'rgba(255, 255, 255, 0.95)';
        input.style.color = '#000';
        input.style.padding = '0 8px';
        input.style.fontSize = 'inherit';
        input.style.fontWeight = 'inherit';

        // Save on Enter or blur
        const saveEdit = () => {
            const newText = input.value.trim();
            if (newText && newText !== segmentData.text) {
                segmentData.text = newText;
                this.segments[segmentIndex].text = newText;
                this.editedSegments.add(segmentIndex);
                segmentElement.classList.add('edited');
            }
            segmentElement.textContent = segmentData.text;
            this.editingSegment = null;
        };

        input.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                saveEdit();
            } else if (e.key === 'Escape') {
                segmentElement.textContent = segmentData.text;
                this.editingSegment = null;
            }
        });

        input.addEventListener('blur', saveEdit);

        // Replace text with input
        segmentElement.textContent = '';
        segmentElement.appendChild(input);
        input.focus();
        input.select();
    }

    startBoundaryDrag(e, segmentIndex, boundary, segmentElement) {
        if (!this.editMode) return;

        e.stopPropagation();
        this.draggingBoundary = {
            segmentIndex,
            boundary, // 'start' or 'end'
            element: segmentElement,
            initialX: e.clientX
        };

        segmentElement.classList.add('dragging-boundary');
    }

    handleBoundaryDrag(e) {
        if (!this.draggingBoundary) return;

        const { segmentIndex, boundary, element } = this.draggingBoundary;
        const segment = this.segments[segmentIndex];

        const timelineRect = element.parentElement.getBoundingClientRect();
        const relativeX = e.clientX - timelineRect.left;
        const newTime = (relativeX / timelineRect.width) * this.totalDuration;

        // Constrain to valid range
        if (boundary === 'start') {
            // Find previous segment end time
            const prevSegment = segmentIndex > 0 ? this.segments[segmentIndex - 1] : null;
            const minTime = prevSegment ? prevSegment.end : 0;
            const maxTime = segment.end - 0.1; // Minimum 0.1s duration

            segment.start = Math.max(minTime, Math.min(newTime, maxTime));
        } else {
            // Find next segment start time
            const nextSegment = segmentIndex < this.segments.length - 1 ? this.segments[segmentIndex + 1] : null;
            const maxTime = nextSegment ? nextSegment.start : this.totalDuration;
            const minTime = segment.start + 0.1; // Minimum 0.1s duration

            segment.end = Math.min(maxTime, Math.max(newTime, minTime));
        }

        // Update segment duration
        segment.duration = segment.end - segment.start;

        // Update visual position
        const startPercent = (segment.start / this.totalDuration) * 100;
        const widthPercent = ((segment.end - segment.start) / this.totalDuration) * 100;

        element.style.left = `${startPercent}%`;
        element.style.width = `${widthPercent}%`;

        // Update tooltip
        element.title = `${this.formatTime(segment.start)} - ${this.formatTime(segment.end)}: ${segment.text}`;

        this.editedSegments.add(segmentIndex);
        element.classList.add('edited');
    }

    stopBoundaryDrag() {
        if (!this.draggingBoundary) return;

        this.draggingBoundary.element.classList.remove('dragging-boundary');
        this.draggingBoundary = null;
    }

    startSegmentDrag(e, segmentData, segmentIndex, segmentElement) {
        if (!this.editMode) return;
        if (e.target.classList.contains('boundary-handle')) return; // Don't drag if clicking boundary handle

        e.stopPropagation();
        this.draggingSegment = {
            data: segmentData,
            index: segmentIndex,
            element: segmentElement,
            initialY: e.clientY,
            originalSpeaker: segmentData.speaker
        };

        segmentElement.classList.add('dragging');
    }

    handleSegmentDrag(e) {
        if (!this.draggingSegment) return;

        const { element, data, index } = this.draggingSegment;

        // Find which speaker lane we're over
        const speakerLanes = Array.from(this.speakerLanes.querySelectorAll('.speaker-lane'));
        const targetLane = speakerLanes.find(lane => {
            const rect = lane.getBoundingClientRect();
            return e.clientY >= rect.top && e.clientY <= rect.bottom;
        });

        if (targetLane) {
            const newSpeaker = targetLane.querySelector('.speaker-label').textContent.replace('...', '');

            // Find full speaker name
            const speakers = [...new Set(this.segments.map(seg => seg.speaker))];
            const fullSpeakerName = speakers.find(s => s.startsWith(newSpeaker) || newSpeaker.startsWith(s)) || newSpeaker;

            // Visual feedback
            speakerLanes.forEach(lane => lane.classList.remove('drop-target'));
            if (fullSpeakerName !== data.speaker) {
                targetLane.classList.add('drop-target');
            }
        }
    }

    stopSegmentDrag() {
        if (!this.draggingSegment) return;

        const { data, index, element } = this.draggingSegment;

        // Find which speaker lane we dropped on
        const speakerLanes = Array.from(this.speakerLanes.querySelectorAll('.speaker-lane'));
        speakerLanes.forEach(lane => lane.classList.remove('drop-target'));

        const targetLane = speakerLanes.find(lane => {
            const rect = lane.getBoundingClientRect();
            return this.draggingSegment.initialY >= rect.top && this.draggingSegment.initialY <= rect.bottom;
        });

        if (targetLane) {
            const newSpeakerLabel = targetLane.querySelector('.speaker-label').textContent;
            const newSpeaker = newSpeakerLabel.endsWith('...') ? newSpeakerLabel.slice(0, -3) : newSpeakerLabel;

            // Find full speaker name
            const speakers = [...new Set(this.segments.map(seg => seg.speaker))];
            const fullSpeakerName = speakers.find(s => s.startsWith(newSpeaker)) || newSpeaker;

            if (fullSpeakerName && fullSpeakerName !== data.speaker) {
                // Update speaker
                data.speaker = fullSpeakerName;
                this.segments[index].speaker = fullSpeakerName;
                this.editedSegments.add(index);

                // Recreate lanes to show new speaker assignment
                this.createSpeakerLanes();
            }
        }

        element.classList.remove('dragging');
        this.draggingSegment = null;
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
        this.editedSegments.clear();
    }
}

// Export for use in other scripts
window.KaraokePlayer = KaraokePlayer;
