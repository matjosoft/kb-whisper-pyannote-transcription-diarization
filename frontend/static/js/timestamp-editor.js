/**
 * TimestampEditor - Handles editing of segment timestamps
 *
 * Features:
 * - Edit start and end times with modal dialog
 * - Time validation (end > start, no negatives, no overlaps)
 * - MM:SS.ms format parsing and display
 * - Gap/overlap detection with adjacent segments
 * - Auto-calculate duration
 * - Visual warnings for timing issues
 */

class TimestampEditor {
    constructor(transcriptEditor) {
        this.editor = transcriptEditor;
        this.modalOverlay = null;
        this.currentSegmentId = null;
        this.startInput = null;
        this.endInput = null;
        this.errorDiv = null;
    }

    /**
     * Initialize timestamp editor (create modal)
     */
    init() {
        this.createTimestampModal();
    }

    /**
     * Show timestamp editor for a segment
     */
    show(segmentId) {
        const segment = this.editor.segments.find(s => s.id === segmentId);
        if (!segment) {
            console.error('Segment not found:', segmentId);
            return;
        }

        this.currentSegmentId = segmentId;

        // Set current values
        if (this.startInput) {
            this.startInput.value = this.formatTime(segment.start);
        }
        if (this.endInput) {
            this.endInput.value = this.formatTime(segment.end);
        }

        // Clear errors
        if (this.errorDiv) {
            this.errorDiv.innerHTML = '';
        }

        // Show modal
        if (this.modalOverlay) {
            this.modalOverlay.classList.add('show');
            // Focus on start input
            setTimeout(() => {
                if (this.startInput) {
                    this.startInput.focus();
                    this.startInput.select();
                }
            }, 100);
        }
    }

    /**
     * Hide timestamp editor
     */
    hide() {
        if (this.modalOverlay) {
            this.modalOverlay.classList.remove('show');
        }
        this.currentSegmentId = null;
        if (this.errorDiv) {
            this.errorDiv.innerHTML = '';
        }
    }

    /**
     * Save timestamp changes
     */
    save() {
        if (!this.currentSegmentId) return;

        const segment = this.editor.segments.find(s => s.id === this.currentSegmentId);
        if (!segment) return;

        // Parse times
        const startTime = this.parseTime(this.startInput.value);
        const endTime = this.parseTime(this.endInput.value);

        // Validate
        const errors = this.validate(this.currentSegmentId, startTime, endTime);
        if (errors.length > 0) {
            this.showErrors(errors);
            return;
        }

        // Update segment
        this.editor.updateSegment(this.currentSegmentId, {
            start: startTime,
            end: endTime,
            duration: endTime - startTime
        });

        // Update display
        this.updateSegmentDisplay(this.currentSegmentId);

        // Hide modal
        this.hide();

        // Show success notification
        if (window.Toast) {
            Toast.show('Timestamps updated', 'success');
        }

        console.log(`Updated timestamps for segment ${this.currentSegmentId}`);
    }

    /**
     * Validate timestamp changes
     */
    validate(segmentId, startTime, endTime) {
        const errors = [];

        // Check if times are valid numbers
        if (isNaN(startTime)) {
            errors.push('Invalid start time format');
        }
        if (isNaN(endTime)) {
            errors.push('Invalid end time format');
        }

        if (errors.length > 0) return errors;

        // Check for negative times
        if (startTime < 0) {
            errors.push('Start time cannot be negative');
        }
        if (endTime < 0) {
            errors.push('End time cannot be negative');
        }

        // Check end > start
        if (endTime <= startTime) {
            errors.push('End time must be after start time');
        }

        // Check for overlaps with adjacent segments
        const segmentIndex = this.editor.segments.findIndex(s => s.id === segmentId);
        if (segmentIndex === -1) return errors;

        // Check previous segment
        if (segmentIndex > 0) {
            const prevSegment = this.editor.segments[segmentIndex - 1];
            if (startTime < prevSegment.end) {
                errors.push(`Overlaps with previous segment (ends at ${this.formatTime(prevSegment.end)})`);
            }
        }

        // Check next segment
        if (segmentIndex < this.editor.segments.length - 1) {
            const nextSegment = this.editor.segments[segmentIndex + 1];
            if (endTime > nextSegment.start) {
                errors.push(`Overlaps with next segment (starts at ${this.formatTime(nextSegment.start)})`);
            }
        }

        return errors;
    }

    /**
     * Show validation errors
     */
    showErrors(errors) {
        if (!this.errorDiv) return;

        this.errorDiv.innerHTML = errors.map(error =>
            `<div class="validation-error">${error}</div>`
        ).join('');
    }

    /**
     * Parse time string (MM:SS.ms or SS.ms) to seconds
     */
    parseTime(timeString) {
        if (!timeString || typeof timeString !== 'string') return NaN;

        timeString = timeString.trim();

        // Check for MM:SS.ms format
        const mmssPattern = /^(\d+):(\d+(?:\.\d+)?)$/;
        const mmssMatch = timeString.match(mmssPattern);

        if (mmssMatch) {
            const minutes = parseInt(mmssMatch[1], 10);
            const seconds = parseFloat(mmssMatch[2]);
            return minutes * 60 + seconds;
        }

        // Check for SS.ms format
        const ssPattern = /^(\d+(?:\.\d+)?)$/;
        const ssMatch = timeString.match(ssPattern);

        if (ssMatch) {
            return parseFloat(ssMatch[1]);
        }

        return NaN;
    }

    /**
     * Format seconds to MM:SS.ms string
     */
    formatTime(seconds) {
        if (typeof seconds !== 'number' || isNaN(seconds)) return '00:00.00';

        const mins = Math.floor(seconds / 60);
        const secs = seconds % 60;

        // Format: MM:SS.ms (2 decimal places)
        const minsStr = mins.toString().padStart(2, '0');
        const secsStr = secs.toFixed(2).padStart(5, '0');

        return `${minsStr}:${secsStr}`;
    }

    /**
     * Update segment display with new timestamps
     */
    updateSegmentDisplay(segmentId) {
        const segment = this.editor.segments.find(s => s.id === segmentId);
        if (!segment) return;

        const segmentDiv = document.querySelector(`.transcription-segment[data-segment-id="${segmentId}"]`);
        if (!segmentDiv) return;

        // Update timestamp display
        const timeStamp = segmentDiv.querySelector('.segment-time');
        if (timeStamp) {
            timeStamp.textContent = `[${this.formatTime(segment.start)} - ${this.formatTime(segment.end)}]`;
        }

        // Update footer (duration)
        const footer = segmentDiv.querySelector('.segment-footer');
        if (footer) {
            const wordCount = segment.text.split(/\s+/).filter(w => w.length > 0).length;
            const modifiedBadge = segment.edited
                ? '<span class="badge badge-warning">⚠ Modified</span>'
                : '';

            footer.innerHTML = `
                <span>Duration: ${segment.duration.toFixed(2)}s</span>
                <span>•</span>
                <span>${wordCount} words</span>
                ${modifiedBadge}
            `;
        }
    }

    /**
     * Check for gaps between segments
     */
    checkForGaps(segmentId) {
        const segmentIndex = this.editor.segments.findIndex(s => s.id === segmentId);
        if (segmentIndex === -1) return [];

        const warnings = [];
        const segment = this.editor.segments[segmentIndex];

        // Check gap with previous segment
        if (segmentIndex > 0) {
            const prevSegment = this.editor.segments[segmentIndex - 1];
            const gap = segment.start - prevSegment.end;
            if (gap > 1.0) { // Gap > 1 second
                warnings.push(`${gap.toFixed(2)}s gap before this segment`);
            }
        }

        // Check gap with next segment
        if (segmentIndex < this.editor.segments.length - 1) {
            const nextSegment = this.editor.segments[segmentIndex + 1];
            const gap = nextSegment.start - segment.end;
            if (gap > 1.0) { // Gap > 1 second
                warnings.push(`${gap.toFixed(2)}s gap after this segment`);
            }
        }

        return warnings;
    }

    /**
     * Create timestamp modal HTML
     */
    createTimestampModal() {
        // Check if modal already exists
        let existing = document.getElementById('timestampModal');
        if (existing) {
            this.modalOverlay = existing;
            this.attachModalEventListeners();
            return;
        }

        // Create modal overlay
        this.modalOverlay = document.createElement('div');
        this.modalOverlay.id = 'timestampModal';
        this.modalOverlay.className = 'modal-overlay';

        this.modalOverlay.innerHTML = `
            <div class="modal">
                <h3>Edit Timestamps</h3>
                <div class="form-group">
                    <label for="startTimeInput">Start Time (MM:SS.ms or SS.ms)</label>
                    <input type="text" id="startTimeInput" placeholder="00:00.00" autocomplete="off">
                </div>
                <div class="form-group">
                    <label for="endTimeInput">End Time (MM:SS.ms or SS.ms)</label>
                    <input type="text" id="endTimeInput" placeholder="00:03.50" autocomplete="off">
                </div>
                <div id="timestampErrors"></div>
                <div class="modal-actions">
                    <button id="saveTimestampBtn" class="action-btn btn-primary">Save</button>
                    <button id="cancelTimestampBtn" class="action-btn">Cancel</button>
                </div>
            </div>
        `;

        document.body.appendChild(this.modalOverlay);
        this.attachModalEventListeners();
    }

    /**
     * Attach event listeners to modal
     */
    attachModalEventListeners() {
        if (!this.modalOverlay) return;

        this.startInput = this.modalOverlay.querySelector('#startTimeInput');
        this.endInput = this.modalOverlay.querySelector('#endTimeInput');
        this.errorDiv = this.modalOverlay.querySelector('#timestampErrors');

        const saveBtn = this.modalOverlay.querySelector('#saveTimestampBtn');
        const cancelBtn = this.modalOverlay.querySelector('#cancelTimestampBtn');

        if (saveBtn) {
            saveBtn.addEventListener('click', () => this.save());
        }

        if (cancelBtn) {
            cancelBtn.addEventListener('click', () => this.hide());
        }

        // Keyboard shortcuts
        if (this.startInput) {
            this.startInput.addEventListener('keydown', (e) => {
                if (e.key === 'Enter') {
                    e.preventDefault();
                    if (this.endInput) {
                        this.endInput.focus();
                        this.endInput.select();
                    }
                } else if (e.key === 'Escape') {
                    this.hide();
                }
            });
        }

        if (this.endInput) {
            this.endInput.addEventListener('keydown', (e) => {
                if (e.key === 'Enter') {
                    e.preventDefault();
                    this.save();
                } else if (e.key === 'Escape') {
                    this.hide();
                }
            });
        }

        // Close on overlay click
        this.modalOverlay.addEventListener('click', (e) => {
            if (e.target === this.modalOverlay) {
                this.hide();
            }
        });

        // Live validation feedback
        if (this.startInput && this.endInput) {
            const validateLive = () => {
                const startTime = this.parseTime(this.startInput.value);
                const endTime = this.parseTime(this.endInput.value);

                if (!isNaN(startTime) && !isNaN(endTime)) {
                    const duration = endTime - startTime;
                    if (duration > 0) {
                        // Show calculated duration
                        if (this.errorDiv) {
                            this.errorDiv.innerHTML = `<div style="color: var(--color-text-secondary); font-size: 13px;">Duration: ${duration.toFixed(2)}s</div>`;
                        }
                    }
                }
            };

            this.startInput.addEventListener('input', validateLive);
            this.endInput.addEventListener('input', validateLive);
        }
    }

    /**
     * Destroy the timestamp editor
     */
    destroy() {
        if (this.modalOverlay && this.modalOverlay.parentNode) {
            this.modalOverlay.parentNode.removeChild(this.modalOverlay);
        }
        this.modalOverlay = null;
        this.currentSegmentId = null;
        this.startInput = null;
        this.endInput = null;
        this.errorDiv = null;
    }
}
