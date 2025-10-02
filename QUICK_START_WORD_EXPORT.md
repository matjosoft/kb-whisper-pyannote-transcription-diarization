# Quick Start - Word Export Feature

## 🎯 What's New?

You can now export your transcriptions to professionally formatted Microsoft Word documents (.docx) in addition to JSON!

## 🚀 Quick Setup (3 steps)

### Step 1: Install Dependencies

```bash
pip install python-docx
```

Or update all dependencies:

```bash
pip install -r requirements.txt
```

### Step 2: Initialize Word Export

```bash
python setup_word_export.py
```

This will:
- Check if python-docx is installed
- Create necessary directories
- Generate the default Word template

### Step 3: Test (Optional)

```bash
python test_word_export.py
```

This will verify everything is working correctly.

## 📝 How to Use

1. **Start the application:**
   ```bash
   python run.py
   ```

2. **Transcribe audio** (record or upload)

3. **Click "Export to Word"** to download a .docx file

4. **Or click "Export JSON"** for JSON format (same as before)

## 📄 What You Get

Your Word document will include:

```
┌─────────────────────────────────────────┐
│     TRANSCRIPTION REPORT                │
├─────────────────────────────────────────┤
│                                         │
│  Metadata:                             │
│  • Export Date: 2025-10-01 14:30:25   │
│  • Duration: 120.50 seconds            │
│  • Number of Speakers: 3               │
│  • Language: EN                        │
│  • Total Segments: 45                  │
│                                         │
│  Transcription:                        │
│                                         │
│  Speaker 1 [00:00 - 00:05]            │
│      Hello, this is the beginning...   │
│                                         │
│  Speaker 2 [00:05 - 00:12]            │
│      Yes, I agree with that...         │
│                                         │
│  Speaker 1 [00:12 - 00:18]            │
│      Let me add to that point...       │
│                                         │
└─────────────────────────────────────────┘
```

## 🎨 Custom Templates (Optional)

Want to customize the document format?

1. **Create a Word template** with placeholders like `{{title}}`, `{{date}}`, etc.
2. **Save it** in `backend/templates/word/`
3. **See full guide:** [WORD_EXPORT_GUIDE.md](WORD_EXPORT_GUIDE.md)

### Available Placeholders:

- `{{title}}` - Document title
- `{{date}}` - Export date/time
- `{{duration}}` - Audio duration
- `{{num_speakers}}` - Number of speakers
- `{{language}}` - Detected language
- `{{total_segments}}` - Total segments
- `{{TRANSCRIPTION}}` - Where segments go (required!)

## 🔧 Troubleshooting

### "Module not found: docx"

```bash
pip install python-docx
```

### "Failed to export to Word"

1. Run the setup script:
   ```bash
   python setup_word_export.py
   ```

2. Run the test script:
   ```bash
   python test_word_export.py
   ```

3. Check backend console for error messages

### Buttons not showing

Clear your browser cache and reload the page (Ctrl+F5)

## 📚 More Information

- **Detailed Guide:** [WORD_EXPORT_GUIDE.md](WORD_EXPORT_GUIDE.md)
- **Template Examples:** [backend/templates/TEMPLATE_EXAMPLES.md](backend/templates/TEMPLATE_EXAMPLES.md)
- **Implementation Details:** [WORD_EXPORT_IMPLEMENTATION.md](WORD_EXPORT_IMPLEMENTATION.md)

## ✅ That's It!

You're ready to export beautiful Word documents from your transcriptions!

**Questions?** Check the documentation files above or the main [README.md](README.md).

---

*Happy transcribing! 📝*
