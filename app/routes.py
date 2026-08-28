import uuid
from pathlib import Path

from flask import Blueprint, current_app, jsonify, request
from werkzeug.utils import secure_filename

from app.database import get_report, insert_report
from app.openai_client import ServiceConfigError, create_openai_client
from app.report_service import ReportGenerationError, build_data_url, generate_report
from app.security import InMemoryRateLimiter, request_origin_is_allowed
from app.validation import ValidationError, validate_report_payload, validate_upload


api = Blueprint("api", __name__)
rate_limiter = InMemoryRateLimiter()


@api.post("/api/reports")
def create_report():
    if not request_origin_is_allowed(request):
        return _error("Request origin is not allowed", 403)

    if not rate_limiter.allow(
        request.remote_addr or "unknown",
        max_requests=current_app.config["RATE_LIMIT_MAX"],
        window_seconds=current_app.config["RATE_LIMIT_WINDOW_SECONDS"],
    ):
        return _error("Too many report requests. Please try again later.", 429)

    try:
        payload = validate_report_payload(request.form)
        image_file = request.files.get("image")
        if image_file is None:
            raise ValidationError("An image upload is required")

        image_content = image_file.read()
        upload = validate_upload(
            image_file.filename or "",
            image_file.mimetype or "",
            image_content,
            max_bytes=current_app.config["MAX_UPLOAD_BYTES"],
        )
        image_data_url = build_data_url(upload.mime_type, image_content)
        report = _generate_report(payload=payload, image_data_url=image_data_url)
        image_path = _save_upload(image_file.filename or "street", upload.extension, image_content)
        submission = insert_report(payload=payload, image_path=image_path, report=report)
        # TODO: Add a user-confirmed DC 311 website submission flow from this validated data.
    except ValidationError as error:
        return _error(str(error), 400)
    except ServiceConfigError:
        return _error("Report generation is not configured on this server", 503)
    except ReportGenerationError:
        return _error("The report could not be generated. Please try again.", 502)

    return jsonify({"success": True, "data": {"submission": submission, "report": report}}), 201


@api.get("/api/reports/<report_id>")
def show_report(report_id):
    report = get_report(report_id)
    if report is None:
        return _error("Report not found", 404)

    return jsonify({"success": True, "data": report})


def _generate_report(*, payload, image_data_url):
    custom_generator = current_app.config.get("REPORT_GENERATOR")
    if custom_generator is not None:
        return custom_generator(payload=payload, image_data_url=image_data_url)

    client = create_openai_client()
    return generate_report(
        client=client,
        payload=payload,
        image_data_url=image_data_url,
        model=current_app.config["OPENAI_MODEL"],
    )


def _save_upload(original_filename, extension, content):
    safe_stem = Path(secure_filename(original_filename)).stem or "street"
    filename = f"{safe_stem}-{uuid.uuid4().hex}{extension}"
    image_path = Path(current_app.config["UPLOAD_FOLDER"]) / filename
    image_path.write_bytes(content)
    return image_path


def _error(message, status_code):
    return jsonify({"success": False, "error": message}), status_code
