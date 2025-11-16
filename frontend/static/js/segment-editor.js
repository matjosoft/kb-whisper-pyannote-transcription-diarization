/**
 * SegmentEditor - Handles editing of individual transcript segments
 *
 * Features:
 * - Inline text editing with contenteditable
 * - Auto-save on blur
 * - Real-time word count
 * - Modified state tracking
 * - Text validation
 */

class SegmentEditor {
    constructor(segmentId, transcriptEditor) {
        this.segmentId = segmentId;
        this.editor = transcriptEditor;
        this.element = null;
        this.textElement = null;
        this.footerElement = null;
        this.initialText = '';
        this.currentText = '';
        this.isEditing = false;
        this.saveTimeout = null;
    }

    /**
     * Initialize the segment editor
     */
    init(element) {
        this.element = element;
        this.textElement = element.querySelector('.segment-text');
        this.footerElement = element.querySelector('.segment-footer');

        if (!this.textElement) {
            console.error('Text element not found for segment', this.segmentId);
            return;
        }

        // Get initial text
        const segment = this.getSegment();
        if (segment) {
            this.initialText = segment.text;
            this.currentText = segment.text;
        }

        this.attachEventListeners();
    }

    /**
     * Attach event listeners for text editing
     */
    attachEventListeners() {
        // Make text editable
        this.textElement.contentEditable = 'true';
        this.textElement.setAttribute('spellcheck', 'true');

        // Focus event - start editing
        this.textElement.addEventListener('focus', () => this.onFocus());

        // Blur event - save changes
        this.textElement.addEventListener('blur', () => this.onBlur());

        // Input event - track changes
        this.textElement.addEventListener('input', () => this.onInput());

        // Keydown event - handle special keys
        this.textElement.addEventListener('keydown', (e) => this.onKeyDown(e));

        // Paste event - clean pasted text
        this.textElement.addEventListener('paste', (e) => this.onPaste(e));
    }

    /**
     * Handle focus event
     */
    onFocus() {
        this.isEditing = true;
        this.element.classList.add('editing');
        this.editor.activeSegmentId = this.segmentId;

        // Store initial text for comparison
        this.initialText = this.textElement.textContent;

        console.log(`Editing segment ${this.segmentId}`);
    }

    /**
     * Handle blur event - save changes
     */
    onBlur() {
        this.isEditing = false;
        this.element.classList.remove('editing');
        this.editor.activeSegmentId = null;

        // Clear any pending save timeout
        if (this.saveTimeout) {
            clearTimeout(this.saveTimeout);
        }

        // Save if text changed
        if (this.hasChanges()) {
            this.save();
        }
    }

    /**
     * Handle input event - track changes in real-time
     */
    onInput() {
        this.currentText = this.textElement.textContent;

        // Update word count in real-time
        this.updateWordCount();

        // Mark as modified if changed
        if (this.hasChanges()) {
            this.markAsModified();
        } else {
            this.clearModifiedFlag();
        }

        // Debounced auto-save (500ms after last keystroke)
        if (this.saveTimeout) {
            clearTimeout(this.saveTimeout);
        }

        this.saveTimeout = setTimeout(() => {
            if (this.hasChanges() && this.isEditing) {
                console.log('Auto-saving after 500ms of inactivity...');
                // Note: We don't actually save here to avoid interrupting editing
                // Actual save happens on blur
            }
        }, 500);
    }

    /**
     * Handle keydown event
     */
    onKeyDown(e) {
        // Enter key - add newline (allow multi-line text)
        if (e.key === 'Enter' && !e.shiftKey) {
            // Allow default behavior (newline)
            return;
        }

        // Escape key - cancel editing (restore original text)
        if (e.key === 'Escape') {
            e.preventDefault();
            this.cancel();
        }

        // Ctrl+S - manual save
        if ((e.ctrlKey || e.metaKey) && e.key === 's') {
            e.preventDefault();
            this.save();
            this.textElement.blur(); // Exit editing mode
        }

        // Prevent undo/redo from bubbling (let edit history handle it)
        if ((e.ctrlKey || e.metaKey) && (e.key === 'z' || e.key === 'y')) {
            // Let browser's native undo/redo work within the text field
            // But we'll use our history for cross-segment changes
            return;
        }
    }

    /**
     * Handle paste event - clean pasted content
     */
    onPaste(e) {
        e.preventDefault();

        // Get plain text from clipboard
        const text = e.clipboardData.getData('text/plain');

        // Insert as plain text (no formatting)
        document.execCommand('insertText', false, text);
    }

    /**
     * Check if text has changed
     */
    hasChanges() {
        return this.currentText !== this.initialText;
    }

    /**
     * Save changes to segment
     */
    save() {
        if (!this.hasChanges()) {
            console.log('No changes to save');
            return;
        }

        // Sanitize text
        const sanitizedText = this.sanitizeText(this.currentText);

        if (!sanitizedText || sanitizedText.trim().length === 0) {
            if (window.Toast) {
                Toast.show('Segment text cannot be empty', 'error');
            }
            // Restore original text
            this.textElement.textContent = this.initialText;
            this.currentText = this.initialText;
            return;
        }

        // Update segment in editor
        this.editor.updateSegment(this.segmentId, {
            text: sanitizedText
        });

        // Update initial text
        this.initialText = sanitizedText;
        this.currentText = sanitizedText;

        // Update display
        this.textElement.textContent = sanitizedText;
        this.updateWordCount();
        this.markAsModified();

        // Show save notification
        if (window.Toast) {
            Toast.show('Changes saved', 'success');
        }

        console.log(`Saved segment ${this.segmentId}`);
    }

    /**
     * Cancel editing - restore original text
     */
    cancel() {
        this.textElement.textContent = this.initialText;
        this.currentText = this.initialText;
        this.clearModifiedFlag();
        this.textElement.blur();

        if (window.Toast) {
            Toast.show('Changes cancelled', 'info');
        }
    }

    /**
     * Sanitize text (remove extra whitespace, etc.)
     */
    sanitizeText(text) {
        return text
            .trim()
            .replace(/\s+/g, ' ') // Replace multiple spaces with single space
            .replace(/\n{3,}/g, '\n\n'); // Max 2 consecutive newlines
    }

    /**
     * Mark segment as modified
     */
    markAsModified() {
        if (!this.element.classList.contains('modified')) {
            this.element.classList.add('modified');
            this.updateFooter();
        }
    }

    /**
     * Clear modified flag
     */
    clearModifiedFlag() {
        this.element.classList.remove('modified');
        this.updateFooter();
    }

    /**
     * Update word count in footer
     */
    updateWordCount() {
        if (!this.footerElement) return;

        const segment = this.getSegment();
        if (!segment) return;

        const wordCount = this.currentText.split(/\s+/).filter(w => w.length > 0).length;
        const duration = segment.duration.toFixed(2);
        const modifiedBadge = segment.edited
            ? '<span class="badge badge-warning">⚠ Modified</span>'
            : '';

        this.footerElement.innerHTML = `
            <span>Duration: ${duration}s</span>
            <span>•</span>
            <span>${wordCount} words</span>
            ${modifiedBadge}
        `;
    }

    /**
     * Update footer display
     */
    updateFooter() {
        const segment = this.getSegment();
        if (!segment || !this.footerElement) return;

        const wordCount = this.currentText.split(/\s+/).filter(w => w.length > 0).length;
        const duration = segment.duration.toFixed(2);
        const modifiedBadge = segment.edited
            ? '<span class="badge badge-warning">⚠ Modified</span>'
            : '';

        this.footerElement.innerHTML = `
            <span>Duration: ${duration}s</span>
            <span>•</span>
            <span>${wordCount} words</span>
            ${modifiedBadge}
        `;
    }

    /**
     * Get segment data
     */
    getSegment() {
        return this.editor.segments.find(s => s.id === this.segmentId);
    }

    /**
     * Disable editing
     */
    disable() {
        if (this.textElement) {
            this.textElement.contentEditable = 'false';
            this.element.classList.remove('editing');
        }
    }

    /**
     * Enable editing
     */
    enable() {
        if (this.textElement) {
            this.textElement.contentEditable = 'true';
        }
    }

    /**
     * Update text programmatically (e.g., from undo/redo)
     */
    updateText(newText) {
        this.textElement.textContent = newText;
        this.initialText = newText;
        this.currentText = newText;
        this.updateWordCount();
    }

    /**
     * Destroy the editor
     */
    destroy() {
        if (this.saveTimeout) {
            clearTimeout(this.saveTimeout);
        }
        this.disable();
    }
}
