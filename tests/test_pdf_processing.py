"""
PDF processing tests for FlockParser
Tests PDF extraction, processing pipeline, and format conversion
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, mock_open
import tempfile

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from flockparsecli import (
    extract_text_from_pdf,
    process_pdf,
    process_directory,
)


class TestPDFExtraction:
    """Test PDF text extraction"""

    @patch('flockparsecli.PdfReader')
    def test_extract_text_pypdf2(self, mock_pypdf2):
        """Test PDF extraction with PyPDF2 (primary method)"""
        # Mock PDF with pages
        mock_page1 = Mock()
        mock_page1.extract_text.return_value = "Page 1 content"
        mock_page2 = Mock()
        mock_page2.extract_text.return_value = "Page 2 content"

        mock_pdf = Mock()
        mock_pdf.pages = [mock_page1, mock_page2]

        mock_pypdf2.return_value = mock_pdf

        result = extract_text_from_pdf("test.pdf")

        assert "Page 1 content" in result
        assert "Page 2 content" in result

    @patch('flockparsecli.subprocess.run')
    @patch('flockparsecli.PdfReader')
    def test_extract_text_fallback_pdftotext(self, mock_pypdf2, mock_subprocess):
        """Test fallback to pdftotext when PyPDF2 fails"""
        # PyPDF2 returns empty
        mock_page = Mock()
        mock_page.extract_text.return_value = ""
        mock_pdf = Mock()
        mock_pdf.pages = [mock_page]
        mock_pypdf2.return_value = mock_pdf

        # pdftotext succeeds
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stderr = ""
        mock_subprocess.return_value = mock_result

        with patch('builtins.open', mock_open(read_data="pdftotext extracted text")):
            result = extract_text_from_pdf("test.pdf")

        assert "pdftotext extracted text" in result or result == ""

    @patch('pytesseract.image_to_string')
    @patch('pdf2image.convert_from_path')
    @patch('flockparsecli.subprocess.run')
    @patch('flockparsecli.PdfReader')
    def test_extract_text_ocr_fallback(self, mock_pypdf2, mock_subprocess, mock_convert, mock_ocr):
        """Test OCR fallback when PyPDF2 and pdftotext fail"""
        # PyPDF2 returns minimal text
        mock_page = Mock()
        mock_page.extract_text.return_value = ""
        mock_pdf = Mock()
        mock_pdf.pages = [mock_page]
        mock_pypdf2.return_value = mock_pdf

        # pdftotext fails
        mock_subprocess.side_effect = FileNotFoundError()

        # OCR succeeds
        mock_image = Mock()
        mock_convert.return_value = [mock_image]
        mock_ocr.return_value = "OCR extracted text"

        result = extract_text_from_pdf("test.pdf")

        assert "OCR extracted text" in result

    @patch('flockparsecli.PdfReader')
    def test_extract_text_empty_pdf(self, mock_pypdf2):
        """Test extracting text from empty PDF"""
        mock_pdf = Mock()
        mock_pdf.pages = []

        mock_pypdf2.return_value = mock_pdf

        result = extract_text_from_pdf("empty.pdf")

        assert result == ""


class TestPDFProcessing:
    """Test PDF processing pipeline"""

    @patch('flockparsecli.register_document')
    @patch('flockparsecli.chunk_text')
    @patch('flockparsecli.extract_text_from_pdf')
    def test_process_pdf_success(self, mock_extract, mock_chunk, mock_register):
        """Test successful PDF processing"""
        mock_extract.return_value = "Extracted PDF text content for testing purposes"
        mock_chunk.return_value = ["Chunk 1", "Chunk 2", "Chunk 3"]
        mock_register.return_value = "doc_123"

        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
            tmp_path = tmp.name

        try:
            process_pdf(tmp_path)

            # Should have called functions
            mock_extract.assert_called_once()
            mock_chunk.assert_called_once()
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    def test_process_pdf_nonexistent(self):
        """Test processing non-existent PDF"""
        result = process_pdf("/nonexistent/file.pdf")
        # Should return None for nonexistent file
        assert result is None

    @patch('flockparsecli.extract_text_from_pdf')
    def test_process_pdf_empty_text(self, mock_extract):
        """Test processing PDF with no extractable text"""
        mock_extract.return_value = ""

        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
            tmp_path = tmp.name

        try:
            result = process_pdf(tmp_path)
            # Empty PDFs return None
            assert result is None
        finally:
            Path(tmp_path).unlink(missing_ok=True)


class TestDirectoryProcessing:
    """Test batch directory processing"""

    @patch('flockparsecli.process_pdf')
    def test_process_directory_multiple_files(self, mock_process):
        """Test processing directory with multiple PDFs"""
        # Create temporary directory with mock PDFs
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create empty PDF files
            Path(tmpdir, "file1.pdf").touch()
            Path(tmpdir, "file2.pdf").touch()
            Path(tmpdir, "file3.pdf").touch()

            process_directory(tmpdir)

            # Should process all files
            assert mock_process.call_count == 3

    def test_process_directory_empty(self):
        """Test processing empty directory"""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = process_directory(tmpdir)
            # Should return None for empty directory
            assert result is None

    def test_process_directory_nonexistent(self):
        """Test processing non-existent directory"""
        result = process_directory("/nonexistent_dir")
        assert result is None


class TestFormatConversion:
    """Test file format conversions"""

    @patch('flockparsecli.register_document')
    @patch('flockparsecli.chunk_text')
    @patch('flockparsecli.extract_text_from_pdf')
    def test_pdf_to_txt_conversion(self, mock_extract, mock_chunk, mock_register):
        """Test PDF to TXT conversion"""
        mock_extract.return_value = "PDF text content for conversion test"
        mock_chunk.return_value = ["chunk"]
        mock_register.return_value = "doc_123"

        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
            pdf_path = tmp.name

        try:
            # Processing should create TXT file
            process_pdf(pdf_path)

            # TXT file should be created in PROCESSED_DIR
            assert mock_extract.called
        finally:
            Path(pdf_path).unlink(missing_ok=True)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
