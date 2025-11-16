/**
 * EditHistory - Manages undo/redo functionality for transcript editing
 *
 * Features:
 * - Stores state snapshots for undo/redo
 * - Limits history size to prevent memory issues
 * - Handles history navigation
 * - Integrates with TranscriptEditor
 */

class EditHistory {
    constructor(editor, maxSize = 50) {
        this.editor = editor;
        this.maxSize = maxSize;
        this.history = [];
        this.currentIndex = -1;

        // Set reference in editor
        this.editor.editHistory = this;
    }

    /**
     * Save current state to history
     */
    saveState() {
        // Remove any states after current index (when user made changes after undo)
        if (this.currentIndex < this.history.length - 1) {
            this.history = this.history.slice(0, this.currentIndex + 1);
        }

        // Get current state from editor
        const state = this.editor.getState();

        // Add to history
        this.history.push(state);

        // Limit history size
        if (this.history.length > this.maxSize) {
            this.history.shift();
        } else {
            this.currentIndex++;
        }

        // Update UI
        this.editor.updateUI();

        console.log(`State saved. History size: ${this.history.length}, Index: ${this.currentIndex}`);
    }

    /**
     * Undo to previous state
     */
    undo() {
        if (!this.canUndo()) {
            console.log('Cannot undo: at beginning of history');
            return;
        }

        this.currentIndex--;
        const state = this.history[this.currentIndex];
        this.editor.restoreState(state);

        console.log(`Undo performed. Index: ${this.currentIndex}`);

        // Show toast notification
        if (window.Toast) {
            Toast.show('Undo successful', 'info');
        }
    }

    /**
     * Redo to next state
     */
    redo() {
        if (!this.canRedo()) {
            console.log('Cannot redo: at end of history');
            return;
        }

        this.currentIndex++;
        const state = this.history[this.currentIndex];
        this.editor.restoreState(state);

        console.log(`Redo performed. Index: ${this.currentIndex}`);

        // Show toast notification
        if (window.Toast) {
            Toast.show('Redo successful', 'info');
        }
    }

    /**
     * Check if undo is possible
     */
    canUndo() {
        return this.currentIndex > 0;
    }

    /**
     * Check if redo is possible
     */
    canRedo() {
        return this.currentIndex < this.history.length - 1;
    }

    /**
     * Clear history
     */
    clear() {
        this.history = [];
        this.currentIndex = -1;
        this.editor.updateUI();
        console.log('History cleared');
    }

    /**
     * Get history info for debugging
     */
    getInfo() {
        return {
            size: this.history.length,
            currentIndex: this.currentIndex,
            canUndo: this.canUndo(),
            canRedo: this.canRedo()
        };
    }
}
