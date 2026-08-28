import pytest

from app.validation import ValidationError, validate_report_payload, validate_upload


PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"0" * 32


def test_validate_report_payload_trims_and_accepts_valid_fields():
    payload = validate_report_payload(
        {
            "description": "  Broken street lamp flickering near the bus stop. ",
            "location": "  1350 Pennsylvania Ave NW ",
            "phone": " (202) 555-0142 ",
        }
    )

    assert payload.description == "Broken street lamp flickering near the bus stop."
    assert payload.location == "1350 Pennsylvania Ave NW"
    assert payload.phone == "(202) 555-0142"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("description", ""),
        ("description", "x" * 501),
        ("location", ""),
        ("location", "x" * 201),
        ("phone", "not-a-phone"),
    ],
)
def test_validate_report_payload_rejects_invalid_input(field, value):
    data = {
        "description": "Pothole in travel lane",
        "location": "14th St NW and U St NW",
        "phone": "202-555-0199",
    }
    data[field] = value

    with pytest.raises(ValidationError):
        validate_report_payload(data)


def test_validate_upload_accepts_small_png():
    result = validate_upload("street.png", "image/png", PNG_BYTES)

    assert result.extension == ".png"
    assert result.mime_type == "image/png"


@pytest.mark.parametrize(
    ("filename", "mime_type", "content"),
    [
        ("street.txt", "text/plain", b"hello"),
        ("street.png", "image/png", b"not really an image"),
        ("street.jpg", "image/jpeg", b"\xff\xd8\xff" + b"0" * (5 * 1024 * 1024 + 1)),
    ],
)
def test_validate_upload_rejects_unsafe_files(filename, mime_type, content):
    with pytest.raises(ValidationError):
        validate_upload(filename, mime_type, content)
