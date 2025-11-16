/**
 * SpeakerManager - Manages speaker operations for transcript editing
 *
 * Features:
 * - Create new speakers
 * - Assign speakers to segments
 * - Rename speakers globally
 * - Manage speaker colors
 * - Calculate speaker statistics
 */

class SpeakerManager {
    constructor(transcriptEditor) {
        this.editor = transcriptEditor;
        this.modalOverlay = null;
        this.currentSegmentId = null;
    }

    /**
     * Initialize speaker manager (create modal if needed)
     */
    init() {
        this.createNewSpeakerModal();
    }

    /**
     * Create speaker dropdown for a segment
     */
    createSpeakerDropdown(segment) {
        const dropdown = document.createElement('select');
        dropdown.className = 'speaker-dropdown';
        dropdown.dataset.segmentId = segment.id;

        // Get current speaker class for color coding
        const speakerClass = this.editor.app.getSpeakerClass(segment.speaker);
        dropdown.classList.add(speakerClass);

        // Add existing speakers
        Object.keys(this.editor.speakers).forEach(speakerId => {
            const option = document.createElement('option');
            option.value = speakerId;
            option.textContent = this.editor.app.speakerNames[speakerId] || speakerId;
            option.selected = segment.speaker === speakerId;
            dropdown.appendChild(option);
        });

        // Add "New speaker" option
        const newOption = document.createElement('option');
        newOption.value = '__new__';
        newOption.textContent = '+ Add new speaker...';
        dropdown.appendChild(newOption);

        // Handle change event
        dropdown.addEventListener('change', (e) => this.handleSpeakerChange(e, segment.id));

        return dropdown;
    }

    /**
     * Handle speaker change from dropdown
     */
    handleSpeakerChange(event, segmentId) {
        const selectedValue = event.target.value;

        if (selectedValue === '__new__') {
            // Show new speaker modal
            this.currentSegmentId = segmentId;
            this.showNewSpeakerModal();
            // Reset dropdown to current speaker
            const segment = this.editor.segments.find(s => s.id === segmentId);
            if (segment) {
                event.target.value = segment.speaker;
            }
        } else {
            // Assign existing speaker
            this.assignSpeaker(segmentId, selectedValue);
        }
    }

    /**
     * Assign a speaker to a segment
     */
    assignSpeaker(segmentId, speakerId) {
        const segment = this.editor.segments.find(s => s.id === segmentId);
        if (!segment) {
            console.error('Segment not found:', segmentId);
            return;
        }

        const oldSpeaker = segment.speaker;
        if (oldSpeaker === speakerId) {
            return; // No change
        }

        // Update segment
        this.editor.updateSegment(segmentId, {
            speaker: speakerId
        });

        // Update speaker statistics
        this.updateSpeakerStats();

        // Update the segment display
        this.updateSegmentSpeakerDisplay(segmentId, speakerId);

        // Update dropdown color
        const dropdown = document.querySelector(`select[data-segment-id="${segmentId}"]`);
        if (dropdown) {
            // Remove old speaker class
            const oldClass = this.editor.app.getSpeakerClass(oldSpeaker);
            dropdown.classList.remove(oldClass);

            // Add new speaker class
            const newClass = this.editor.app.getSpeakerClass(speakerId);
            dropdown.classList.add(newClass);
        }

        // Update segment div color
        const segmentDiv = document.querySelector(`.transcription-segment[data-segment-id="${segmentId}"]`);
        if (segmentDiv) {
            // Remove all speaker classes
            for (let i = 1; i <= 6; i++) {
                segmentDiv.classList.remove(`speaker-${i}`);
            }
            // Add new speaker class
            const newClass = this.editor.app.getSpeakerClass(speakerId);
            segmentDiv.classList.add(newClass);
        }

        // Show success notification
        if (window.Toast) {
            const speakerName = this.editor.app.speakerNames[speakerId] || speakerId;
            Toast.show(`Speaker changed to ${speakerName}`, 'success');
        }

        console.log(`Assigned speaker ${speakerId} to segment ${segmentId}`);
    }

    /**
     * Update segment speaker display (name in header)
     */
    updateSegmentSpeakerDisplay(segmentId, speakerId) {
        const segmentDiv = document.querySelector(`.transcription-segment[data-segment-id="${segmentId}"]`);
        if (!segmentDiv) return;

        const speakerNameElement = segmentDiv.querySelector('.speaker-name');
        if (speakerNameElement) {
            speakerNameElement.textContent = this.editor.app.speakerNames[speakerId] || speakerId;
        }
    }

    /**
     * Create a new speaker
     */
    createSpeaker(speakerName) {
        if (!speakerName || speakerName.trim().length === 0) {
            if (window.Toast) {
                Toast.show('Speaker name cannot be empty', 'error');
            }
            return null;
        }

        // Generate new speaker ID
        const newSpeakerId = `Speaker ${this.editor.nextSpeakerId}`;
        this.editor.nextSpeakerId++;

        // Add to speakers
        this.editor.speakers[newSpeakerId] = {
            displayName: speakerName.trim(),
            color: this.editor.getSpeakerColor(newSpeakerId),
            segmentCount: 0,
            totalDuration: 0
        };

        // Add to app's speaker names
        this.editor.app.speakerNames[newSpeakerId] = speakerName.trim();

        // Update speaker editor (the original one in the UI)
        this.updateOriginalSpeakerEditor();

        console.log(`Created new speaker: ${newSpeakerId} (${speakerName})`);

        return newSpeakerId;
    }

    /**
     * Update the original speaker editor in the UI
     */
    updateOriginalSpeakerEditor() {
        if (this.editor.app.createSpeakerEditor) {
            this.editor.app.createSpeakerEditor(this.editor.app.speakerNames);
        }
    }

    /**
     * Rename a speaker globally
     */
    renameSpeaker(oldSpeakerId, newName) {
        if (!newName || newName.trim().length === 0) {
            if (window.Toast) {
                Toast.show('Speaker name cannot be empty', 'error');
            }
            return false;
        }

        // Update speaker names
        this.editor.app.speakerNames[oldSpeakerId] = newName.trim();
        if (this.editor.speakers[oldSpeakerId]) {
            this.editor.speakers[oldSpeakerId].displayName = newName.trim();
        }

        // Update all segment displays with this speaker
        this.editor.segments.forEach(segment => {
            if (segment.speaker === oldSpeakerId) {
                this.updateSegmentSpeakerDisplay(segment.id, oldSpeakerId);
            }
        });

        // Update dropdowns
        document.querySelectorAll('.speaker-dropdown').forEach(dropdown => {
            const option = dropdown.querySelector(`option[value="${oldSpeakerId}"]`);
            if (option) {
                option.textContent = newName.trim();
            }
        });

        if (window.Toast) {
            Toast.show(`Speaker renamed to "${newName}"`, 'success');
        }

        return true;
    }

    /**
     * Update speaker statistics
     */
    updateSpeakerStats() {
        // Reset all counts
        Object.keys(this.editor.speakers).forEach(speakerId => {
            this.editor.speakers[speakerId].segmentCount = 0;
            this.editor.speakers[speakerId].totalDuration = 0;
        });

        // Recalculate from segments
        this.editor.segments.forEach(segment => {
            if (this.editor.speakers[segment.speaker]) {
                this.editor.speakers[segment.speaker].segmentCount++;
                this.editor.speakers[segment.speaker].totalDuration += segment.duration;
            }
        });
    }

    /**
     * Show new speaker modal
     */
    showNewSpeakerModal() {
        if (!this.modalOverlay) {
            console.error('New speaker modal not found');
            return;
        }

        this.modalOverlay.classList.add('show');

        // Focus on input
        const input = this.modalOverlay.querySelector('#newSpeakerName');
        if (input) {
            input.value = '';
            setTimeout(() => input.focus(), 100);
        }
    }

    /**
     * Hide new speaker modal
     */
    hideNewSpeakerModal() {
        if (this.modalOverlay) {
            this.modalOverlay.classList.remove('show');
        }
        this.currentSegmentId = null;
    }

    /**
     * Create new speaker modal HTML
     */
    createNewSpeakerModal() {
        // Check if modal already exists
        let existing = document.getElementById('newSpeakerModal');
        if (existing) {
            this.modalOverlay = existing;
            this.attachModalEventListeners();
            return;
        }

        // Create modal overlay
        this.modalOverlay = document.createElement('div');
        this.modalOverlay.id = 'newSpeakerModal';
        this.modalOverlay.className = 'modal-overlay';

        this.modalOverlay.innerHTML = `
            <div class="modal">
                <h3>Create New Speaker</h3>
                <div class="form-group">
                    <label for="newSpeakerName">Speaker Name</label>
                    <input type="text" id="newSpeakerName" placeholder="e.g., John Doe" autocomplete="off">
                    <div class="validation-error" id="speakerNameError"></div>
                </div>
                <div class="modal-actions">
                    <button id="createSpeakerBtn" class="action-btn btn-primary">Create</button>
                    <button id="cancelSpeakerBtn" class="action-btn">Cancel</button>
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

        const createBtn = this.modalOverlay.querySelector('#createSpeakerBtn');
        const cancelBtn = this.modalOverlay.querySelector('#cancelSpeakerBtn');
        const input = this.modalOverlay.querySelector('#newSpeakerName');

        if (createBtn) {
            createBtn.addEventListener('click', () => this.handleCreateSpeaker());
        }

        if (cancelBtn) {
            cancelBtn.addEventListener('click', () => this.hideNewSpeakerModal());
        }

        if (input) {
            // Submit on Enter key
            input.addEventListener('keydown', (e) => {
                if (e.key === 'Enter') {
                    e.preventDefault();
                    this.handleCreateSpeaker();
                } else if (e.key === 'Escape') {
                    this.hideNewSpeakerModal();
                }
            });
        }

        // Close on overlay click
        this.modalOverlay.addEventListener('click', (e) => {
            if (e.target === this.modalOverlay) {
                this.hideNewSpeakerModal();
            }
        });
    }

    /**
     * Handle create speaker button click
     */
    handleCreateSpeaker() {
        const input = this.modalOverlay.querySelector('#newSpeakerName');
        const errorDiv = this.modalOverlay.querySelector('#speakerNameError');

        if (!input) return;

        const speakerName = input.value.trim();

        // Validate
        if (!speakerName) {
            if (errorDiv) {
                errorDiv.textContent = 'Speaker name is required';
            }
            return;
        }

        // Clear error
        if (errorDiv) {
            errorDiv.textContent = '';
        }

        // Create new speaker
        const newSpeakerId = this.createSpeaker(speakerName);

        if (newSpeakerId) {
            // If we have a current segment, assign the new speaker to it
            if (this.currentSegmentId) {
                this.assignSpeaker(this.currentSegmentId, newSpeakerId);
            }

            // Re-render to show new speaker in all dropdowns
            this.editor.renderSegments();

            // Hide modal
            this.hideNewSpeakerModal();

            // Show success
            if (window.Toast) {
                Toast.show(`Speaker "${speakerName}" created`, 'success');
            }
        }
    }

    /**
     * Get all available speakers for dropdown
     */
    getAvailableSpeakers() {
        return Object.keys(this.editor.speakers).map(speakerId => ({
            id: speakerId,
            name: this.editor.app.speakerNames[speakerId] || speakerId,
            color: this.editor.speakers[speakerId].color,
            segmentCount: this.editor.speakers[speakerId].segmentCount,
            duration: this.editor.speakers[speakerId].totalDuration
        }));
    }

    /**
     * Destroy the speaker manager
     */
    destroy() {
        if (this.modalOverlay && this.modalOverlay.parentNode) {
            this.modalOverlay.parentNode.removeChild(this.modalOverlay);
        }
        this.modalOverlay = null;
        this.currentSegmentId = null;
    }
}
