# services/file_text_extractor.py
import logging

logger = logging.getLogger(__name__)

ALLOWED_IMAGE_TYPES = ['image/png', 'image/jpeg', 'image/webp']
ALLOWED_FILE_TYPES = ['application/pdf', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'text/plain']
MAX_IMAGES_PER_TEST_PAGE = 10
MAX_IMAGE_SIZE_BYTES = 5 * 1024 * 1024
MAX_FILE_SIZE_BYTES = 2 * 1024 * 1024


def extract_text_from_file(file_bytes: bytes, content_type: str, filename: str = "") -> str:
    """Extract text content from uploaded file."""
    try:
        if content_type == "text/plain" or filename.endswith('.txt'):
            return file_bytes.decode('utf-8')
        if content_type == "application/pdf" or filename.endswith('.pdf'):
            return _extract_from_pdf(file_bytes)
        if content_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document" or filename.endswith('.docx'):
            return _extract_from_docx(file_bytes)
        return ""
    except Exception as e:
        logger.error(f"Failed to extract text: {e}")
        return ""


def _extract_from_pdf(file_bytes: bytes) -> str:
    try:
        import PyPDF2
        from io import BytesIO
        reader = PyPDF2.PdfReader(BytesIO(file_bytes))
        return "\n\n".join([page.extract_text() or "" for page in reader.pages])
    except:
        return ""


def _extract_from_docx(file_bytes: bytes) -> str:
    try:
        import docx
        from io import BytesIO
        doc = docx.Document(BytesIO(file_bytes))
        return "\n\n".join([p.text for p in doc.paragraphs if p.text.strip()])
    except:
        return ""


def validate_image_upload(content_type: str, file_size: int) -> tuple:
    if content_type not in ALLOWED_IMAGE_TYPES:
        return False, "Invalid image type. Allowed: PNG, JPEG, WebP"
    if file_size > MAX_IMAGE_SIZE_BYTES:
        return False, "Image too large. Max size: 5MB"
    return True, None


def validate_file_upload(content_type: str, file_size: int, filename: str) -> tuple:
    is_valid_type = content_type in ALLOWED_FILE_TYPES
    is_valid_ext = filename.lower().endswith(('.pdf', '.docx', '.txt'))
    if not (is_valid_type or is_valid_ext):
        return False, "Invalid file type. Allowed: PDF, DOCX, TXT"
    if file_size > MAX_FILE_SIZE_BYTES:
        return False, "File too large. Max size: 2MB"
    return True, None
