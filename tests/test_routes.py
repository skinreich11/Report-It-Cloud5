import io

import pytest

from app import create_app
from app.openai_client import ServiceConfigError
from app.report_service import ReportGenerationError


PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"0" * 32


class FakeReportGenerator:
    def __init__(self):
        self.calls = []

    def __call__(self, *, payload, image_data_url):
        self.calls.append((payload, image_data_url))
        return {
            "service_request_type": "Roadway Repair",
            "service_code": "input:Pothole & Street Issues",
            "summary": "Pothole at an intersection.",
            "public_description": "A pothole is visible in the roadway.",
            "priority": "Normal",
            "open311_request": {
                "service_code": "input:Pothole & Street Issues",
                "address_string": payload.location,
                "phone": payload.phone,
                "description": "A pothole is visible in the roadway.",
                "media_url": None,
            },
            "open311_attributes": {"input.pothole.Nature_of_request": "pavement_defect"},
        }


@pytest.fixture()
def client(tmp_path):
    generator = FakeReportGenerator()
    app = create_app(
        {
            "TESTING": True,
            "DATABASE_PATH": tmp_path / "report_it.sqlite3",
            "UPLOAD_FOLDER": tmp_path / "uploads",
            "REPORT_GENERATOR": generator,
            "PUBLIC_BASE_URL": "https://example.com",
            "RATE_LIMIT_MAX": 100,
        }
    )
    app.report_generator = generator
    return app.test_client(), generator


def test_create_report_accepts_multipart_input_and_persists_report(client):
    http, generator = client

    response = http.post(
        "/api/reports",
        data={
            "description": "Pothole opening in the bike lane.",
            "location": "14th St NW and U St NW",
            "phone": "202-555-0199",
            "image": (io.BytesIO(PNG_BYTES), "street.png"),
        },
        content_type="multipart/form-data",
    )

    body = response.get_json()

    assert response.status_code == 201
    assert body["success"] is True
    assert body["data"]["report"]["service_request_type"] == "Roadway Repair"
    assert "dc_311_submission_steps" not in body["data"]["report"]
    assert body["data"]["report"]["open311_submission"]["status"] == "submitted"
    assert "token" not in body["data"]["report"]["open311_submission"]
    assert body["data"]["submission"]["location"] == "14th St NW and U St NW"
    assert len(generator.calls) == 1
    request_sample = body["data"]["report"]["open311_submission"]["request_sample"]
    assert request_sample["service_code"] == "input:Pothole & Street Issues"
    assert request_sample["address_string"] == "14th St NW and U St NW"
    assert request_sample["phone"] == "202-555-0199"
    assert request_sample["media_url"].startswith("https://example.com/uploads/street-")
    assert request_sample["attributes"] == {
        "input.pothole.Nature_of_request": "pavement_defect"
    }

    fetch_response = http.get(f"/api/reports/{body['data']['submission']['id']}")
    fetch_body = fetch_response.get_json()

    assert fetch_response.status_code == 200
    assert fetch_body["data"]["report"]["summary"] == "Pothole at an intersection."
    assert fetch_body["data"]["report"]["open311_submission"]["provider"] == "San Francisco 311"


def test_create_report_rejects_invalid_upload(client):
    http, _ = client

    response = http.post(
        "/api/reports",
        data={
            "description": "Pothole opening in the bike lane.",
            "location": "14th St NW and U St NW",
            "phone": "202-555-0199",
            "image": (io.BytesIO(b"not image content"), "street.txt"),
        },
        content_type="multipart/form-data",
    )

    body = response.get_json()

    assert response.status_code == 400
    assert body["success"] is False
    assert "image" in body["error"].lower()


def test_create_report_requires_image(client):
    http, _ = client

    response = http.post(
        "/api/reports",
        data={
            "description": "Pothole opening in the bike lane.",
            "location": "14th St NW and U St NW",
            "phone": "202-555-0199",
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 400
    assert response.get_json()["success"] is False


def test_create_report_blocks_cross_origin_requests(client):
    http, _ = client

    response = http.post(
        "/api/reports",
        data={
            "description": "Pothole opening in the bike lane.",
            "location": "14th St NW and U St NW",
            "phone": "202-555-0199",
            "image": (io.BytesIO(PNG_BYTES), "street.png"),
        },
        content_type="multipart/form-data",
        headers={"Origin": "https://example.com"},
    )

    assert response.status_code == 403


def test_create_report_handles_generator_configuration_errors(tmp_path):
    def fail_generator(**_kwargs):
        raise ServiceConfigError("missing key")

    app = create_app(
        {
            "TESTING": True,
            "DATABASE_PATH": tmp_path / "report_it.sqlite3",
            "UPLOAD_FOLDER": tmp_path / "uploads",
            "REPORT_GENERATOR": fail_generator,
            "RATE_LIMIT_MAX": 100,
        }
    )

    response = app.test_client().post(
        "/api/reports",
        data={
            "description": "Pothole opening in the bike lane.",
            "location": "14th St NW and U St NW",
            "phone": "202-555-0199",
            "image": (io.BytesIO(PNG_BYTES), "street.png"),
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 503


def test_create_report_handles_generation_errors(tmp_path):
    def fail_generator(**_kwargs):
        raise ReportGenerationError("model failed")

    app = create_app(
        {
            "TESTING": True,
            "DATABASE_PATH": tmp_path / "report_it.sqlite3",
            "UPLOAD_FOLDER": tmp_path / "uploads",
            "REPORT_GENERATOR": fail_generator,
            "RATE_LIMIT_MAX": 100,
        }
    )

    response = app.test_client().post(
        "/api/reports",
        data={
            "description": "Pothole opening in the bike lane.",
            "location": "14th St NW and U St NW",
            "phone": "202-555-0199",
            "image": (io.BytesIO(PNG_BYTES), "street.png"),
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 502


def test_get_report_returns_404_for_missing_id(client):
    http, _ = client

    response = http.get("/api/reports/not-found")

    assert response.status_code == 404
