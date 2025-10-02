"""
Test script for Word export functionality.
Run this to verify Word export is working correctly.

Usage:
    python test_word_export.py
"""

from pathlib import Path
import sys


def test_import():
    """Test if python-docx can be imported"""
    print("Testing python-docx import...")
    try:
        import docx
        print("✓ python-docx imported successfully")
        return True
    except ImportError as e:
        print(f"✗ Failed to import python-docx: {e}")
        print("\nPlease install it:")
        print("  pip install python-docx")
        return False


def test_export_service():
    """Test if ExportService can be imported"""
    print("\nTesting ExportService import...")
    try:
        from backend.services.export_service import ExportService
        print("✓ ExportService imported successfully")
        return True
    except ImportError as e:
        print(f"✗ Failed to import ExportService: {e}")
        return False


def test_basic_export():
    """Test basic Word export functionality"""
    print("\nTesting basic Word export...")
    try:
        from backend.services.export_service import ExportService

        # Sample transcription data
        sample_data = {
            "segments": [
                {
                    "speaker": "Speaker 1",
                    "start": 0.0,
                    "end": 5.5,
                    "text": "Hello, this is a test transcription."
                },
                {
                    "speaker": "Speaker 2",
                    "start": 5.5,
                    "end": 10.0,
                    "text": "Yes, this is testing the Word export feature."
                },
                {
                    "speaker": "Speaker 1",
                    "start": 10.0,
                    "end": 15.0,
                    "text": "It seems to be working correctly."
                }
            ],
            "duration": 15.0,
            "num_speakers": 2,
            "language": "en",
            "full_text": "Test transcription"
        }

        # Create export service
        export_service = ExportService()

        # Test output path
        output_path = Path("test_export.docx")

        # Export
        result_path = export_service.export_to_word(
            transcription_data=sample_data,
            output_path=output_path
        )

        # Check if file was created
        if result_path.exists():
            file_size = result_path.stat().st_size
            print(f"✓ Word document created successfully")
            print(f"  Location: {result_path.absolute()}")
            print(f"  Size: {file_size} bytes")

            # Clean up
            cleanup = input("\nDelete test file? (y/n): ").lower()
            if cleanup == 'y':
                result_path.unlink()
                print("✓ Test file deleted")
            else:
                print(f"ℹ Test file kept: {result_path.absolute()}")

            return True
        else:
            print("✗ Word document was not created")
            return False

    except Exception as e:
        print(f"✗ Export test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_template_creation():
    """Test template creation"""
    print("\nTesting template creation...")
    try:
        from pathlib import Path
        import sys

        # Add backend to path if needed
        backend_path = Path(__file__).parent / "backend"
        if str(backend_path) not in sys.path:
            sys.path.insert(0, str(backend_path))

        from templates.create_default_template import create_default_template

        template_path = create_default_template()

        if template_path.exists():
            print(f"✓ Template created: {template_path}")
            return True
        else:
            print("✗ Template was not created")
            return False

    except Exception as e:
        print(f"✗ Template creation failed: {e}")
        return False


def test_directories():
    """Test if required directories exist"""
    print("\nTesting directory structure...")

    directories = [
        Path("backend/templates/word"),
        Path("backend/services"),
        Path("exports")
    ]

    all_exist = True
    for dir_path in directories:
        if dir_path.exists():
            print(f"✓ {dir_path} exists")
        else:
            print(f"✗ {dir_path} does not exist")
            all_exist = False

    return all_exist


def main():
    """Run all tests"""
    print("=" * 60)
    print("Word Export Feature - Test Suite")
    print("=" * 60)

    results = {
        "Import python-docx": test_import(),
        "Import ExportService": test_export_service(),
        "Directory structure": test_directories(),
        "Template creation": test_template_creation(),
        "Basic export": test_basic_export()
    }

    print("\n" + "=" * 60)
    print("Test Results Summary")
    print("=" * 60)

    all_passed = True
    for test_name, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{test_name}: {status}")
        if not result:
            all_passed = False

    print("=" * 60)

    if all_passed:
        print("\n🎉 All tests passed! Word export is ready to use.")
        print("\nNext steps:")
        print("1. Start the application: python run.py")
        print("2. Transcribe an audio file")
        print("3. Click 'Export to Word' to test in the application")
    else:
        print("\n⚠ Some tests failed. Please fix the issues above.")
        print("\nTroubleshooting:")
        print("1. Run: pip install -r requirements.txt")
        print("2. Run: python setup_word_export.py")
        print("3. Check that you're in the project root directory")

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
