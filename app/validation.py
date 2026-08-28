import re
from dataclasses import dataclass
from pathlib import Path


MAX_UPLOAD_BYTES = 5 * 1024 * 1024
ALLOWED_IMAGE_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
}
PHONE_PATTERN = re.compile(r"^[0-9+().\-\s]{7,24}$")


class ValidationError(ValueError):
    pass


@dataclass(frozen=True)
class ReportPayload:
    description: str
    location: str
    phone: str


@dataclass(frozen=True)
class UploadValidation:
    extension: str
    mime_type: str


def validate_report_payload(form_data):
    description = _trimmed(form_data.get("description", ""))
    location = _trimmed(form_data.get("location", ""))
    phone = _trimmed(form_data.get("phone", ""))

    if not description:
        raise ValidationError("Description is required")
    if len(description) > 500:
        raise ValidationError("Description must be 500 characters or fewer")
    if not location:
        raise ValidationError("Location is required")
    if len(location) > 200:
        raise ValidationError("Location must be 200 characters or fewer")
    if not PHONE_PATTERN.match(phone) or not 10 <= _digit_count(phone) <= 15:
        raise ValidationError("Phone number must be a valid contact number")

    return ReportPayload(description=description, location=location, phone=phone)


def validate_upload(filename, mime_type, content, *, max_bytes=MAX_UPLOAD_BYTES):
    extension = Path(filename).suffix.lower()
    expected_mime_type = ALLOWED_IMAGE_TYPES.get(extension)

    if expected_mime_type is None:
        raise ValidationError("Image must be a JPG, PNG, or WEBP file")
    if mime_type != expected_mime_type:
        raise ValidationError("Image content type does not match the file extension")
    if not content:
        raise ValidationError("Image upload is empty")
    if len(content) > max_bytes:
        raise ValidationError("Image must be 5MB or smaller")
    if not _content_matches_image_type(extension, content):
        raise ValidationError("Image file content is invalid")

    return UploadValidation(extension=extension, mime_type=expected_mime_type)


def _trimmed(value):
    return str(value).strip()


def _digit_count(value):
    return len([character for character in value if character.isdigit()])


def _content_matches_image_type(extension, content):
    if extension == ".png":
        return content.startswith(b"\x89PNG\r\n\x1a\n")
    if extension in {".jpg", ".jpeg"}:
        return content.startswith(b"\xff\xd8\xff")
    if extension == ".webp":
        return len(content) >= 12 and content[:4] == b"RIFF" and content[8:12] == b"WEBP"
    return False
