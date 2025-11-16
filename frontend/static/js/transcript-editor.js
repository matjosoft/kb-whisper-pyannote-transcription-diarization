/**
 * TranscriptEditor - Main controller for transcript editing functionality
 *
 * Manages:
 * - Edit mode state
 * - Transcript segments with unique IDs
 * - Speaker management
 * - Integration with edit history (undo/redo)
 * - Dirty state tracking
 */

class TranscriptEditor {
    constructor(app) {
        this.app = app; // Reference to main AudioScribeApp
        this.isEditMode = false;
        this.hasUnsavedChanges = false;
        this.activeSegmentId = null;
        this.editHistory = null; // Will be set by EditHistory instance

        // State
        this.segments = [];
        this.speakers = {};
        this.nextSegmentId = 1;
        this.nextSpeakerId = 1;

        this.initializeElements();
        this.setupEventListeners();
    }

    initializeElements() {
        // Edit mode controls (will be added to HTML)
        this.editModeToggle = document.getElementById('editModeToggle');
        this.undoBtn = document.getElementById('undoBtn');
        this.redoBtn = document.getElementById('redoBtn');
        this.editStats = document.getElementById('editStats');
        this.saveIndicator = document.getElementById('saveIndicator');
    }

    setupEventListeners() {
        // Edit mode toggle
        if (this.editModeToggle) {
            this.editModeToggle.addEventListener('change', () => this.toggleEditMode());
        }

        // Undo/redo buttons
        if (this.undoBtn) {
            this.undoBtn.addEventListener('click', () => this.undo());
        }
        if (this.redoBtn) {
            this.redoBtn.addEventListener('click', () => this.redo());
        }

        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => this.handleKeyboardShortcuts(e));

        // Warn before leaving with unsaved changes
        window.addEventListener('beforeunload', (e) => {
            if (this.hasUnsavedChanges) {
                e.preventDefault();
                e.returnValue = 'You have unsaved changes. Are you sure you want to leave?';
                return e.returnValue;
            }
        });
    }

    /**
     * Load transcript results and prepare for editing
     */
    loadTranscript(results) {
        // Convert segments to editable format with unique IDs
        this.segments = results.segments.map((segment, index) => ({
            id: this.generateSegmentId(),
            start: segment.start,
            end: segment.end,
            text: segment.text,
            speaker: segment.speaker,
            duration: segment.duration || (segment.end - segment.start),
            edited: false,
            words: segment.words || [] // Word-level timing if available
        }));

        // Store speakers
        this.speakers = {};
        Object.keys(results.speakers).forEach(speakerId => {
            this.speakers[speakerId] = {
                displayName: results.speakers[speakerId],
                color: this.getSpeakerColor(speakerId),
                segmentCount: this.segments.filter(s => s.speaker === speakerId).length,
                totalDuration: this.calculateSpeakerDuration(speakerId)
            };
        });

        // Update next speaker ID based on existing speakers
        const speakerNumbers = Object.keys(this.speakers)
            .map(id => parseInt(id.match(/\d+/)?.[0] || 0))
            .filter(n => !isNaN(n));
        this.nextSpeakerId = speakerNumbers.length > 0 ? Math.max(...speakerNumbers) + 1 : 1;

        // Clear unsaved changes flag
        this.hasUnsavedChanges = false;
        this.updateUI();

        // Save initial state to history
        if (this.editHistory) {
            this.editHistory.saveState();
        }
    }

    /**
     * Toggle between view and edit mode
     */
    toggleEditMode() {
        this.isEditMode = !this.isEditMode;

        if (this.isEditMode) {
            this.enterEditMode();
        } else {
            this.exitEditMode();
        }

        this.updateUI();
    }

    enterEditMode() {
        console.log('Entering edit mode');

        // Add edit-mode class to transcription display
        const transcriptionDisplay = document.getElementById('transcriptionDisplay');
        if (transcriptionDisplay) {
            transcriptionDisplay.classList.add('edit-mode');
        }

        // Re-render segments with edit controls
        this.renderSegments();

        // Show edit controls
        this.showEditControls();
    }

    exitEditMode() {
        console.log('Exiting edit mode');

        // Check for unsaved changes
        if (this.hasUnsavedChanges) {
            const confirm = window.confirm('You have unsaved changes. Do you want to discard them?');
            if (!confirm) {
                // Revert toggle
                if (this.editModeToggle) {
                    this.editModeToggle.checked = true;
                }
                this.isEditMode = true;
                return;
            }
        }

        // Remove edit-mode class
        const transcriptionDisplay = document.getElementById('transcriptionDisplay');
        if (transcriptionDisplay) {
            transcriptionDisplay.classList.remove('edit-mode');
        }

        // Re-render segments without edit controls (use app's display method)
        this.app.displayTranscription(this.getSegmentsForDisplay());

        // Hide edit controls
        this.hideEditControls();
    }

    /**
     * Render segments in edit mode with controls
     */
    renderSegments() {
        const transcriptionDisplay = document.getElementById('transcriptionDisplay');
        if (!transcriptionDisplay) return;

        transcriptionDisplay.innerHTML = '';

        this.segments.forEach((segment, index) => {
            const segmentElement = this.createEditableSegment(segment, index);
            transcriptionDisplay.appendChild(segmentElement);
        });
    }

    /**
     * Create an editable segment element
     */
    createEditableSegment(segment, index) {
        const segmentDiv = document.createElement('div');
        segmentDiv.className = `transcription-segment ${this.app.getSpeakerClass(segment.speaker)} edit-mode`;
        segmentDiv.dataset.segmentId = segment.id;

        if (segment.edited) {
            segmentDiv.classList.add('modified');
        }

        // Header with speaker and timestamp
        const header = document.createElement('div');
        header.className = 'segment-header';

        // Speaker name (editable in future phase)
        const speakerName = document.createElement('span');
        speakerName.className = 'speaker-name';
        speakerName.textContent = this.app.speakerNames[segment.speaker] || segment.speaker;

        // Timestamp
        const timeStamp = document.createElement('span');
        timeStamp.className = 'segment-time';
        timeStamp.textContent = `[${this.app.formatTime(segment.start)} - ${this.app.formatTime(segment.end)}]`;

        header.appendChild(speakerName);
        header.appendChild(timeStamp);

        // Text (will be made editable in Phase 2)
        const text = document.createElement('div');
        text.className = 'segment-text';
        text.textContent = segment.text;
        text.dataset.segmentId = segment.id;

        // Footer with metadata
        const footer = document.createElement('div');
        footer.className = 'segment-footer';

        const wordCount = segment.text.split(/\s+/).filter(w => w.length > 0).length;
        footer.innerHTML = `
            <span>Duration: ${segment.duration.toFixed(2)}s</span>
            <span>•</span>
            <span>${wordCount} words</span>
            ${segment.edited ? '<span class="badge badge-warning">⚠ Modified</span>' : ''}
        `;

        segmentDiv.appendChild(header);
        segmentDiv.appendChild(text);
        segmentDiv.appendChild(footer);

        return segmentDiv;
    }

    /**
     * Get segments in format compatible with app.displayTranscription()
     */
    getSegmentsForDisplay() {
        return this.segments.map(seg => ({
            start: seg.start,
            end: seg.end,
            text: seg.text,
            speaker: seg.speaker,
            duration: seg.duration
        }));
    }

    /**
     * Update a segment
     */
    updateSegment(segmentId, changes) {
        const segment = this.segments.find(s => s.id === segmentId);
        if (!segment) return;

        // Save to history before making changes
        if (this.editHistory) {
            this.editHistory.saveState();
        }

        // Apply changes
        Object.assign(segment, changes);
        segment.edited = true;

        // Mark as unsaved
        this.hasUnsavedChanges = true;
        this.updateUI();
    }

    /**
     * Undo last change
     */
    undo() {
        if (this.editHistory) {
            this.editHistory.undo();
        }
    }

    /**
     * Redo last undone change
     */
    redo() {
        if (this.editHistory) {
            this.editHistory.redo();
        }
    }

    /**
     * Restore state from history
     */
    restoreState(state) {
        this.segments = JSON.parse(JSON.stringify(state.segments));
        this.speakers = JSON.parse(JSON.stringify(state.speakers));

        if (this.isEditMode) {
            this.renderSegments();
        } else {
            this.app.displayTranscription(this.getSegmentsForDisplay());
        }

        this.updateUI();
    }

    /**
     * Get current state for history
     */
    getState() {
        return {
            segments: JSON.parse(JSON.stringify(this.segments)),
            speakers: JSON.parse(JSON.stringify(this.speakers))
        };
    }

    /**
     * Update UI elements
     */
    updateUI() {
        // Update stats
        if (this.editStats) {
            const modifiedCount = this.segments.filter(s => s.edited).length;
            const stats = `${this.segments.length} segments • ${Object.keys(this.speakers).length} speakers`;
            const modifiedText = modifiedCount > 0 ? ` • ${modifiedCount} modified` : '';
            this.editStats.textContent = stats + modifiedText;
        }

        // Update save indicator
        if (this.saveIndicator) {
            if (this.hasUnsavedChanges) {
                this.saveIndicator.textContent = '⚠ Unsaved changes';
                this.saveIndicator.className = 'save-indicator unsaved';
            } else {
                this.saveIndicator.textContent = '✓ All changes saved';
                this.saveIndicator.className = 'save-indicator saved';
            }
        }

        // Update undo/redo buttons
        if (this.editHistory) {
            if (this.undoBtn) {
                this.undoBtn.disabled = !this.editHistory.canUndo();
            }
            if (this.redoBtn) {
                this.redoBtn.disabled = !this.editHistory.canRedo();
            }
        }

        // Update edit mode toggle
        if (this.editModeToggle) {
            this.editModeToggle.checked = this.isEditMode;
        }
    }

    /**
     * Show edit controls
     */
    showEditControls() {
        const editControls = document.getElementById('editControls');
        if (editControls) {
            editControls.classList.remove('hidden');
        }
    }

    /**
     * Hide edit controls
     */
    hideEditControls() {
        const editControls = document.getElementById('editControls');
        if (editControls) {
            editControls.classList.add('hidden');
        }
    }

    /**
     * Handle keyboard shortcuts
     */
    handleKeyboardShortcuts(e) {
        if (!this.isEditMode) return;

        // Ctrl/Cmd + Z = Undo
        if ((e.ctrlKey || e.metaKey) && e.key === 'z' && !e.shiftKey) {
            e.preventDefault();
            this.undo();
        }

        // Ctrl/Cmd + Shift + Z or Ctrl/Cmd + Y = Redo
        if ((e.ctrlKey || e.metaKey) && (e.key === 'y' || (e.key === 'z' && e.shiftKey))) {
            e.preventDefault();
            this.redo();
        }

        // Ctrl/Cmd + S = Save (mark as saved)
        if ((e.ctrlKey || e.metaKey) && e.key === 's') {
            e.preventDefault();
            this.markAsSaved();
        }
    }

    /**
     * Mark changes as saved
     */
    markAsSaved() {
        this.hasUnsavedChanges = false;
        this.updateUI();

        // Show toast notification
        if (window.Toast) {
            Toast.show('Changes saved', 'success');
        }
    }

    /**
     * Generate unique segment ID
     */
    generateSegmentId() {
        return `seg_${Date.now()}_${this.nextSegmentId++}`;
    }

    /**
     * Get speaker color from class
     */
    getSpeakerColor(speakerId) {
        const speakerClass = this.app.getSpeakerClass(speakerId);
        const speakerNum = speakerClass.match(/\d+/)?.[0] || '1';

        const colors = {
            '1': '#3b82f6', // Blue
            '2': '#10b981', // Green
            '3': '#f59e0b', // Orange
            '4': '#ec4899', // Pink
            '5': '#8b5cf6', // Purple
            '6': '#06b6d4'  // Cyan
        };

        return colors[speakerNum] || colors['1'];
    }

    /**
     * Calculate total duration for a speaker
     */
    calculateSpeakerDuration(speakerId) {
        return this.segments
            .filter(s => s.speaker === speakerId)
            .reduce((total, s) => total + s.duration, 0);
    }

    /**
     * Get current results in original format for export
     */
    getResults() {
        return {
            segments: this.getSegmentsForDisplay(),
            speakers: Object.keys(this.speakers).reduce((acc, key) => {
                acc[key] = this.speakers[key].displayName;
                return acc;
            }, {}),
            num_speakers: Object.keys(this.speakers).length,
            language: this.app.currentResults?.language || 'unknown',
            duration: this.segments.length > 0
                ? this.segments[this.segments.length - 1].end
                : 0,
            full_text: this.segments.map(s => s.text).join(' ')
        };
    }
}
