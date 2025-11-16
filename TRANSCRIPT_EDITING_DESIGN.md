# Transcript Editing Feature - Design & Implementation Plan

## Executive Summary

This document outlines a comprehensive design for adding transcript editing capabilities to the whisper-pyannote transcription application. The feature will enable users to edit text, adjust timestamps, change speakers, and manage segments through an intuitive, visually appealing interface.

---

## 1. Feature Requirements

### Core Editing Capabilities
1. **Text Editing**
   - Add or remove text within segments
   - Real-time validation and auto-save
   - Visual feedback for unsaved changes

2. **Speaker Management**
   - Change speaker assignment for any segment
   - Create new speakers on-the-fly
   - Merge or rename speakers globally
   - Visual speaker color coding (maintain existing 6-color palette)

3. **Timestamp Adjustment**
   - Edit start/end times with validation
   - Visual timeline representation
   - Automatic gap/overlap detection
   - Snap-to-word alignment (optional)

4. **Segment Operations**
   - Split segments at cursor position
   - Merge consecutive segments
   - Delete segments
   - Reorder segments (if needed)

### UX Requirements
- **Simple & Intuitive:** Inline editing with minimal mode switching
- **Visually Appealing:** Consistent with existing dark mode design
- **Non-destructive:** Undo/redo support
- **Responsive:** Works on mobile and desktop

---

## 2. UI/UX Design

### 2.1 Visual Design Concept

#### Edit Mode Toggle
```
┌─────────────────────────────────────────────────┐
│ [View Mode] [Edit Mode ✓]    [Undo] [Redo]     │
└─────────────────────────────────────────────────┘
```

#### Segment Card in Edit Mode
```
┌─────────────────────────────────────────────────────────────┐
│ [Speaker: Speaker 1 ▼] [00:00.42] → [00:03.87] [⋮]        │
├─────────────────────────────────────────────────────────────┤
│ This is the transcribed text that can be edited inline.    │
│ [Cursor blinking here]                                      │
├─────────────────────────────────────────────────────────────┤
│ Duration: 3.45s • 8 words • Modified ⚠                     │
└─────────────────────────────────────────────────────────────┘

[⋮] Menu:
  ✂ Split at cursor
  🔗 Merge with next
  🗑 Delete segment
  ─────────────
  💾 Save changes
```

#### Timeline Visualization (Optional Enhancement)
```
┌──────────────────────────────────────────────────────────┐
│ Timeline:                                                 │
│ 0:00      0:30      1:00      1:30      2:00      2:30   │
│ ▓▓▓▓▓░░░░░▓▓▓▓▓▓▓░░▓▓▓▓░░░░░░▓▓▓▓▓▓▓▓▓░░░░▓▓▓░░░        │
│ S1   S2   S1      S2   S3      S1        S2   S3         │
└──────────────────────────────────────────────────────────┘
```

### 2.2 Interaction Patterns

#### Inline Text Editing
- **Click segment text** → Enter edit mode (contenteditable)
- **Type freely** → Changes tracked, auto-save indicator appears
- **Click outside or press Escape** → Save/discard prompt if modified

#### Speaker Change
- **Click speaker dropdown** → Shows existing + "Add new speaker..." option
- **Select speaker** → Immediate update with color change animation
- **Type new name** → Creates new speaker, assigns unique color

#### Timestamp Editing
- **Click timestamp** → Opens time picker modal/popover
- **Input format:** `MM:SS.ms` with validation
- **Visual feedback:** Shows gaps, overlaps, or warnings
- **Drag handles (advanced):** Drag segment edges on timeline

#### Segment Operations
- **Split:** Place cursor in text → Click "Split" → Creates two segments at cursor position with interpolated timestamp
- **Merge:** Click "Merge with next" → Combines current + next segment (same speaker preferred)
- **Delete:** Click delete → Confirmation → Remove segment

---

## 3. Technical Architecture

### 3.1 Data Model Extensions

#### Current Segment Structure
```javascript
{
    start: 0.42,
    end: 3.87,
    text: "Transcribed text",
    speaker: "Speaker 1",
    duration: 3.45
}
```

#### Enhanced Segment Structure
```javascript
{
    id: "seg_1234567890",           // NEW: Unique identifier
    start: 0.42,
    end: 3.87,
    text: "Transcribed text",
    speaker: "Speaker 1",
    duration: 3.45,

    // NEW: Edit tracking
    edited: false,                   // Has this segment been modified?
    editHistory: [],                 // Undo/redo stack (optional)

    // NEW: Word-level timing (if available from Whisper)
    words: [                         // For advanced timeline alignment
        { word: "Transcribed", start: 0.42, end: 0.89 },
        { word: "text", start: 0.92, end: 1.20 }
    ]
}
```

#### Speaker Management
```javascript
{
    speakers: {
        "Speaker 1": {
            displayName: "Speaker 1",
            color: "#3b82f6",         // Blue accent
            segmentCount: 12,
            totalDuration: 45.6
        },
        "Speaker 2": { ... }
    },
    nextSpeakerId: 3                  // For auto-generating new speaker names
}
```

### 3.2 State Management

#### Global State Object
```javascript
const transcriptState = {
    // Current data
    segments: [],                     // Array of segment objects
    speakers: {},                     // Speaker metadata

    // Edit tracking
    isEditMode: false,                // View vs Edit mode
    hasUnsavedChanges: false,         // Dirty flag

    // Undo/redo
    history: [],                      // Past states
    historyIndex: -1,                 // Current position in history
    maxHistorySize: 50,               // Limit memory usage

    // UI state
    activeSegmentId: null,            // Currently editing segment
    selectedSegments: []              // Multi-select (future)
}
```

#### State Management Functions
```javascript
// Core operations
function updateSegment(segmentId, changes) { ... }
function deleteSegment(segmentId) { ... }
function splitSegment(segmentId, position) { ... }
function mergeSegments(segmentId1, segmentId2) { ... }

// Speaker operations
function updateSpeaker(oldName, newName) { ... }
function createSpeaker(name) { ... }
function assignSpeaker(segmentId, speakerName) { ... }

// History management
function saveToHistory() { ... }
function undo() { ... }
function redo() { ... }
```

### 3.3 Component Architecture

#### New JavaScript Modules

**`transcript-editor.js`** (Main editing controller)
- Initialize edit mode
- Handle mode switching
- Coordinate UI updates
- Manage state changes

**`segment-editor.js`** (Individual segment editing)
- Inline text editing
- Speaker dropdown
- Timestamp editor
- Segment menu

**`speaker-manager.js`** (Speaker operations)
- Speaker creation/renaming
- Global speaker updates
- Color assignment
- Speaker statistics

**`timeline-view.js`** (Optional - Timeline visualization)
- Visual timeline rendering
- Drag-to-adjust timestamps
- Gap/overlap detection
- Playback synchronization

**`edit-history.js`** (Undo/redo system)
- State snapshot management
- History navigation
- Memory optimization

**`validation.js`** (Data validation)
- Timestamp validation (no negative, end > start)
- Gap/overlap detection
- Text sanitization
- Speaker name validation

### 3.4 CSS Design System

#### Color Palette (Extend existing dark mode)
```css
:root {
    /* Existing colors */
    --bg-primary: #0a0e1a;
    --surface-1: #1a1f35;
    --text-primary: #e5e7eb;

    /* NEW: Edit mode colors */
    --edit-active: #3b82f6;          /* Blue - active editing */
    --edit-modified: #f59e0b;        /* Amber - unsaved changes */
    --edit-error: #ef4444;           /* Red - validation error */
    --edit-success: #10b981;         /* Green - saved */

    /* NEW: Interactive states */
    --hover-overlay: rgba(59, 130, 246, 0.1);
    --focus-ring: 0 0 0 2px rgba(59, 130, 246, 0.5);
}
```

#### Component Styles
```css
.segment-card {
    /* Base card style (existing) */
}

.segment-card.edit-mode {
    border: 2px solid var(--surface-2);
    cursor: text;
}

.segment-card.editing {
    border-color: var(--edit-active);
    box-shadow: 0 0 0 4px rgba(59, 130, 246, 0.1);
}

.segment-card.modified {
    border-left: 4px solid var(--edit-modified);
}

.segment-text {
    /* Existing styles */
}

.segment-text[contenteditable="true"] {
    outline: none;
    padding: 8px;
    border-radius: 4px;
    background: rgba(255, 255, 255, 0.02);
}

.segment-text[contenteditable="true"]:focus {
    background: rgba(255, 255, 255, 0.05);
}
```

---

## 4. Implementation Plan

### Phase 1: Foundation (Days 1-2)
**Goal:** Set up edit mode infrastructure

- [ ] Create `transcript-editor.js` module
- [ ] Add edit mode toggle UI to HTML
- [ ] Implement state management structure
- [ ] Add unique IDs to existing segments
- [ ] Create basic undo/redo system
- [ ] Add dirty state tracking

**Deliverable:** Toggle between view and edit mode

### Phase 2: Text Editing (Days 3-4)
**Goal:** Enable inline text editing

- [ ] Create `segment-editor.js` module
- [ ] Implement contenteditable for segment text
- [ ] Add auto-save on blur
- [ ] Show modified indicator
- [ ] Validate text input
- [ ] Test undo/redo for text changes

**Deliverable:** Edit segment text inline

### Phase 3: Speaker Management (Days 5-6)
**Goal:** Complete speaker editing features

- [ ] Create `speaker-manager.js` module
- [ ] Add speaker dropdown to each segment
- [ ] Implement "Add new speaker" functionality
- [ ] Create speaker creation modal
- [ ] Add speaker color assignment
- [ ] Update speaker editor to sync with changes
- [ ] Test speaker switching and creation

**Deliverable:** Change speakers and create new ones

### Phase 4: Timestamp Editing (Days 7-8)
**Goal:** Enable timestamp adjustments

- [ ] Create timestamp editor component
- [ ] Add time input with MM:SS.ms format
- [ ] Implement validation (end > start, no negatives)
- [ ] Add gap/overlap detection
- [ ] Show warnings for timing issues
- [ ] Update duration automatically
- [ ] Test edge cases

**Deliverable:** Edit segment start/end times

### Phase 5: Segment Operations (Days 9-10)
**Goal:** Implement split, merge, delete

- [ ] Add segment menu UI (three-dot menu)
- [ ] Implement split at cursor position
- [ ] Implement merge with next segment
- [ ] Implement delete with confirmation
- [ ] Calculate interpolated timestamps for splits
- [ ] Update segment IDs after operations
- [ ] Test all operations with undo/redo

**Deliverable:** Full segment manipulation

### Phase 6: Visual Polish (Days 11-12)
**Goal:** Enhance UX and visual design

- [ ] Add smooth transitions and animations
- [ ] Implement loading states
- [ ] Add keyboard shortcuts (Ctrl+Z, Ctrl+Y, Delete)
- [ ] Create helpful tooltips
- [ ] Add segment statistics (word count, duration)
- [ ] Polish mobile responsiveness
- [ ] Add accessibility (ARIA labels, keyboard nav)

**Deliverable:** Professional, polished UI

### Phase 7: Export Integration (Day 13)
**Goal:** Update export formats with edits

- [ ] Update Word export to use edited segments
- [ ] Update TXT export to use edited segments
- [ ] Update JSON export to include edit metadata
- [ ] Add "Export edited transcript" label
- [ ] Test all export formats

**Deliverable:** Exports reflect edited content

### Phase 8: Testing & Refinement (Days 14-15)
**Goal:** Comprehensive testing and bug fixes

- [ ] Test all features end-to-end
- [ ] Test edge cases (empty segments, special chars)
- [ ] Performance testing (large transcripts)
- [ ] Cross-browser testing
- [ ] Mobile device testing
- [ ] Fix bugs and polish UX
- [ ] Create user documentation

**Deliverable:** Production-ready feature

### Optional Future Enhancements (Post-MVP)
- [ ] Visual timeline with drag-to-adjust
- [ ] Word-level timestamp alignment
- [ ] Multi-segment selection and bulk operations
- [ ] Search and replace across transcript
- [ ] Comment/annotation system
- [ ] Collaborative editing (multiple users)
- [ ] Backend persistence (save edits to database)
- [ ] AI-assisted speaker identification
- [ ] Export to subtitle formats (SRT, VTT)

---

## 5. Technical Implementation Details

### 5.1 Inline Text Editing

```javascript
class SegmentTextEditor {
    constructor(segmentId, initialText) {
        this.segmentId = segmentId;
        this.initialText = initialText;
        this.currentText = initialText;
        this.element = null;
    }

    enable() {
        this.element.contentEditable = true;
        this.element.addEventListener('blur', () => this.onBlur());
        this.element.addEventListener('input', () => this.onInput());
        this.element.addEventListener('keydown', (e) => this.onKeyDown(e));
    }

    disable() {
        this.element.contentEditable = false;
        // Remove listeners
    }

    onInput() {
        this.currentText = this.element.textContent;
        if (this.currentText !== this.initialText) {
            this.markAsModified();
        }
    }

    onBlur() {
        if (this.hasChanges()) {
            this.save();
        }
    }

    save() {
        const segment = transcriptState.segments.find(s => s.id === this.segmentId);
        if (segment) {
            saveToHistory(); // Before making changes
            segment.text = this.currentText;
            segment.edited = true;
            this.initialText = this.currentText;
            this.clearModifiedFlag();
            transcriptState.hasUnsavedChanges = true;
        }
    }
}
```

### 5.2 Speaker Dropdown

```javascript
function createSpeakerDropdown(segment) {
    const dropdown = document.createElement('select');
    dropdown.className = 'speaker-dropdown';

    // Add existing speakers
    Object.keys(transcriptState.speakers).forEach(speakerName => {
        const option = document.createElement('option');
        option.value = speakerName;
        option.textContent = speakerName;
        option.selected = segment.speaker === speakerName;
        dropdown.appendChild(option);
    });

    // Add "New speaker" option
    const newOption = document.createElement('option');
    newOption.value = '__new__';
    newOption.textContent = '+ Add new speaker...';
    dropdown.appendChild(newOption);

    dropdown.addEventListener('change', (e) => {
        if (e.target.value === '__new__') {
            showNewSpeakerModal(segment.id);
        } else {
            assignSpeaker(segment.id, e.target.value);
        }
    });

    return dropdown;
}

function assignSpeaker(segmentId, speakerName) {
    saveToHistory();
    const segment = transcriptState.segments.find(s => s.id === segmentId);
    segment.speaker = speakerName;
    segment.edited = true;
    updateSegmentDisplay(segmentId);
    transcriptState.hasUnsavedChanges = true;
}
```

### 5.3 Timestamp Editor

```javascript
class TimestampEditor {
    constructor(segmentId) {
        this.segmentId = segmentId;
        this.segment = transcriptState.segments.find(s => s.id === segmentId);
    }

    show() {
        const modal = this.createModal();
        document.body.appendChild(modal);
        this.attachValidation();
    }

    createModal() {
        return `
            <div class="modal">
                <div class="modal-content">
                    <h3>Edit Timestamps</h3>
                    <label>
                        Start Time:
                        <input type="text" id="start-time"
                               value="${this.formatTime(this.segment.start)}"
                               placeholder="MM:SS.ms" />
                    </label>
                    <label>
                        End Time:
                        <input type="text" id="end-time"
                               value="${this.formatTime(this.segment.end)}"
                               placeholder="MM:SS.ms" />
                    </label>
                    <div id="validation-messages"></div>
                    <button onclick="this.save()">Save</button>
                    <button onclick="this.cancel()">Cancel</button>
                </div>
            </div>
        `;
    }

    validate(start, end) {
        const errors = [];

        if (start < 0) errors.push("Start time cannot be negative");
        if (end < 0) errors.push("End time cannot be negative");
        if (end <= start) errors.push("End time must be after start time");

        // Check for overlaps with adjacent segments
        const prevSegment = this.getPreviousSegment();
        const nextSegment = this.getNextSegment();

        if (prevSegment && start < prevSegment.end) {
            errors.push(`Overlaps with previous segment (ends at ${this.formatTime(prevSegment.end)})`);
        }

        if (nextSegment && end > nextSegment.start) {
            errors.push(`Overlaps with next segment (starts at ${this.formatTime(nextSegment.start)})`);
        }

        return errors;
    }

    save() {
        const start = this.parseTime(document.getElementById('start-time').value);
        const end = this.parseTime(document.getElementById('end-time').value);

        const errors = this.validate(start, end);
        if (errors.length > 0) {
            this.showErrors(errors);
            return;
        }

        saveToHistory();
        this.segment.start = start;
        this.segment.end = end;
        this.segment.duration = end - start;
        this.segment.edited = true;
        updateSegmentDisplay(this.segmentId);
        this.close();
    }

    formatTime(seconds) {
        const mins = Math.floor(seconds / 60);
        const secs = (seconds % 60).toFixed(2);
        return `${mins.toString().padStart(2, '0')}:${secs.padStart(5, '0')}`;
    }

    parseTime(timeString) {
        const [mins, secs] = timeString.split(':').map(parseFloat);
        return mins * 60 + secs;
    }
}
```

### 5.4 Segment Split Operation

```javascript
function splitSegment(segmentId, cursorPosition) {
    saveToHistory();

    const segment = transcriptState.segments.find(s => s.id === segmentId);
    const text = segment.text;

    // Find split point (cursor position in text)
    const beforeText = text.substring(0, cursorPosition).trim();
    const afterText = text.substring(cursorPosition).trim();

    if (!beforeText || !afterText) {
        alert("Cannot split: Both segments must contain text");
        return;
    }

    // Calculate interpolated timestamp
    const ratio = cursorPosition / text.length;
    const splitTime = segment.start + (segment.duration * ratio);

    // Update first segment
    segment.text = beforeText;
    segment.end = splitTime;
    segment.duration = splitTime - segment.start;
    segment.edited = true;

    // Create second segment
    const newSegment = {
        id: generateSegmentId(),
        start: splitTime,
        end: segment.end,
        text: afterText,
        speaker: segment.speaker,
        duration: segment.end - splitTime,
        edited: true
    };

    // Insert after current segment
    const index = transcriptState.segments.indexOf(segment);
    transcriptState.segments.splice(index + 1, 0, newSegment);

    // Refresh display
    displayTranscription();
    transcriptState.hasUnsavedChanges = true;
}
```

### 5.5 Undo/Redo System

```javascript
const historyManager = {
    history: [],
    currentIndex: -1,
    maxSize: 50,

    saveState() {
        // Remove any states after current index (if we undid and then made new changes)
        this.history = this.history.slice(0, this.currentIndex + 1);

        // Deep clone current state
        const state = JSON.parse(JSON.stringify({
            segments: transcriptState.segments,
            speakers: transcriptState.speakers
        }));

        this.history.push(state);

        // Limit history size
        if (this.history.length > this.maxSize) {
            this.history.shift();
        } else {
            this.currentIndex++;
        }

        this.updateUI();
    },

    undo() {
        if (this.currentIndex > 0) {
            this.currentIndex--;
            this.restoreState(this.history[this.currentIndex]);
            this.updateUI();
        }
    },

    redo() {
        if (this.currentIndex < this.history.length - 1) {
            this.currentIndex++;
            this.restoreState(this.history[this.currentIndex]);
            this.updateUI();
        }
    },

    restoreState(state) {
        transcriptState.segments = JSON.parse(JSON.stringify(state.segments));
        transcriptState.speakers = JSON.parse(JSON.stringify(state.speakers));
        displayTranscription();
    },

    updateUI() {
        document.getElementById('undo-btn').disabled = this.currentIndex <= 0;
        document.getElementById('redo-btn').disabled = this.currentIndex >= this.history.length - 1;
    },

    clear() {
        this.history = [];
        this.currentIndex = -1;
        this.updateUI();
    }
};
```

---

## 6. User Experience Flow

### Typical Editing Session

1. **User loads transcript**
   - Transcription completes
   - Display shows in view mode (read-only)
   - "Edit Mode" button visible in header

2. **User clicks "Edit Mode"**
   - UI transitions to edit mode
   - Segment cards show edit controls
   - Undo/redo buttons appear
   - Tooltip: "Click any text to edit"

3. **User edits a segment**
   - Clicks on text → cursor appears
   - Types changes
   - Orange indicator shows "modified"
   - Clicks outside → auto-saves
   - Green checkmark briefly appears

4. **User changes speaker**
   - Clicks speaker dropdown
   - Selects different speaker
   - Card color animates to new speaker color
   - Modified indicator appears

5. **User adjusts timestamp**
   - Clicks on timestamp
   - Modal opens with time inputs
   - Enters new times
   - Validation shows any errors
   - Clicks "Save" → timestamps update

6. **User splits a segment**
   - Places cursor mid-text
   - Clicks three-dot menu → "Split at cursor"
   - Segment splits into two cards
   - Timestamps interpolated automatically

7. **User makes mistake**
   - Clicks "Undo" button (or Ctrl+Z)
   - Previous state restored
   - Can click "Redo" if needed

8. **User exports**
   - Clicks "Export to Word"
   - Edited transcript downloads
   - All changes included in export

---

## 7. Accessibility Considerations

- **Keyboard Navigation:**
  - Tab through segments
  - Enter to edit
  - Escape to cancel
  - Ctrl+Z / Ctrl+Y for undo/redo

- **Screen Readers:**
  - ARIA labels on all controls
  - Announce state changes ("Segment modified", "Saved")
  - Describe speaker colors for visually impaired

- **Visual:**
  - High contrast indicators
  - Multiple visual cues (color + icon + text)
  - Focus states clearly visible

---

## 8. Performance Considerations

### Large Transcripts (1000+ segments)

1. **Virtual Scrolling:**
   - Only render visible segments
   - Lazy load as user scrolls
   - Recycle DOM elements

2. **Debounced Auto-save:**
   - Don't save on every keystroke
   - Wait 500ms after typing stops

3. **Optimized State Updates:**
   - Only re-render changed segments
   - Use segment IDs for efficient lookups
   - Avoid full transcript re-renders

4. **Memory Management:**
   - Limit undo history size (50 states)
   - Clear old states periodically
   - Compress history snapshots

---

## 9. Testing Strategy

### Unit Tests
- Timestamp validation logic
- Text sanitization
- Speaker management functions
- Undo/redo state management

### Integration Tests
- Edit → Save → Export flow
- Split/merge operations
- Multi-segment speaker changes
- Undo/redo with various operations

### E2E Tests
- Complete editing session
- Export edited transcript
- Mobile editing workflow

### Manual Testing Checklist
- [ ] Edit text in segment
- [ ] Change speaker (existing)
- [ ] Create new speaker
- [ ] Edit start time
- [ ] Edit end time
- [ ] Split segment
- [ ] Merge segments
- [ ] Delete segment
- [ ] Undo changes
- [ ] Redo changes
- [ ] Export to Word/TXT
- [ ] Test on mobile
- [ ] Test with screen reader

---

## 10. Success Metrics

- **Functional:** All CRUD operations work correctly
- **UX:** Users can complete common edits in < 30 seconds
- **Performance:** No lag when editing transcripts up to 1000 segments
- **Quality:** Zero data loss, all changes preserved correctly
- **Accessibility:** WCAG 2.1 AA compliance

---

## 11. File Structure (New Files)

```
frontend/
├── static/
│   ├── js/
│   │   ├── app.js                    # [MODIFIED] Add edit mode integration
│   │   ├── transcript-editor.js      # [NEW] Main edit controller
│   │   ├── segment-editor.js         # [NEW] Segment editing logic
│   │   ├── speaker-manager.js        # [NEW] Speaker operations
│   │   ├── edit-history.js           # [NEW] Undo/redo system
│   │   ├── validation.js             # [NEW] Input validation
│   │   └── timeline-view.js          # [NEW, OPTIONAL] Visual timeline
│   └── css/
│       ├── style.css                 # [MODIFIED] Add edit mode styles
│       └── editor.css                # [NEW] Edit-specific styles
└── index.html                        # [MODIFIED] Add edit UI elements

backend/
├── services/
│   └── export_service.py             # [MODIFIED] Use edited segments
└── app.py                            # [NO CHANGES NEEDED]
```

---

## Conclusion

This design provides a comprehensive, user-friendly transcript editing system that:
- ✅ Enables all requested editing features
- ✅ Maintains visual consistency with existing UI
- ✅ Follows best practices for UX and accessibility
- ✅ Scales to large transcripts
- ✅ Integrates seamlessly with existing codebase
- ✅ Provides room for future enhancements

**Estimated Development Time:** 12-15 days for full MVP implementation

**Next Steps:** Review this design, provide feedback, and proceed with Phase 1 implementation.
