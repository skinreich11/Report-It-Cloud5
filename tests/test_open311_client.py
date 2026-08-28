from app.open311_client import (
    build_mock_submission_result,
    build_media_url,
    build_open311_request,
    choose_service,
)
from app.validation import ReportPayload


def test_choose_service_maps_common_street_issues_to_san_francisco_codes():
    assert choose_service("Broken street lamp")["service_code"] == "PW:BSM:Damage Property"
    assert choose_service("Pothole in the road")["service_code"] == "input:Pothole & Street Issues"
    assert choose_service("Fallen tree limb")["service_code"] == "PW:BUF:Tree Maintenance"


def test_build_open311_request_includes_required_fields_and_attributes():
    payload = ReportPayload(
        description="Large pothole in travel lane.",
        location="1 Dr Carlton B Goodlett Pl, San Francisco, CA",
        phone="415-555-0199",
    )
    report = {
        "service_request_type": "Pothole and street issues",
        "service_code": "input:Pothole & Street Issues",
        "public_description": "Large pothole in the travel lane.",
        "open311_attributes": {"input.pothole.Nature_of_request": "pavement_defect"},
    }

    request_data = build_open311_request(
        report=report,
        payload=payload,
        media_url="https://example.com/uploads/street.png",
    )

    assert request_data == {
        "service_code": "input:Pothole & Street Issues",
        "address_string": "1 Dr Carlton B Goodlett Pl, San Francisco, CA",
        "phone": "415-555-0199",
        "description": "Large pothole in the travel lane.",
        "media_url": "https://example.com/uploads/street.png",
        "attribute[input.pothole.Nature_of_request]": "pavement_defect",
    }


def test_build_open311_request_falls_back_to_valid_service_metadata():
    payload = ReportPayload(
        description="Broken lamp.",
        location="Market St and 5th St, San Francisco, CA",
        phone="415-555-0199",
    )
    report = {
        "service_request_type": "Street light",
        "service_code": "not-real",
        "public_description": "A street lamp is out.",
        "open311_attributes": {"bad": "value"},
    }

    request_data = build_open311_request(
        report=report,
        payload=payload,
    )

    assert request_data["service_code"] == "PW:BSM:Damage Property"
    assert request_data["attribute[oform.pw_damaged_property.Nature_of_request]"] == "traffic_signal"
    assert "bad" not in request_data


def test_build_media_url_requires_public_base_url():
    assert build_media_url(None, "street.png") is None
    assert build_media_url("https://example.com/app/", "street.png") == (
        "https://example.com/app/uploads/street.png"
    )


def test_build_mock_submission_result_returns_success_with_request_sample():
    request_data = {
        "service_code": "input:Pothole & Street Issues",
        "address_string": "1 Dr Carlton B Goodlett Pl, San Francisco, CA",
        "phone": "415-555-0199",
        "description": "Large pothole in the travel lane.",
        "media_url": "https://example.com/uploads/street.png",
        "attribute[input.pothole.Nature_of_request]": "pavement_defect",
    }

    result = build_mock_submission_result(
        request_data=request_data,
        provider_name="San Francisco 311",
        base_url="https://san-francisco2-dev.spotmobile.net/open311/v2",
    )

    assert result["status"] == "submitted"
    assert result["provider"] == "San Francisco 311"
    assert result["endpoint"] == "https://san-francisco2-dev.spotmobile.net/open311/v2/requests.json"
    assert result["request_sample"]["service_code"] == "input:Pothole & Street Issues"
    assert result["request_sample"]["attributes"] == {
        "input.pothole.Nature_of_request": "pavement_defect"
    }
