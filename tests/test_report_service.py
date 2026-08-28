import json
from types import SimpleNamespace

import pytest

from app.report_service import ReportGenerationError
from app.report_service import build_data_url, generate_report
from app.validation import ReportPayload


class FakeResponses:
    def __init__(self):
        self.kwargs = None

    def create(self, **kwargs):
        self.kwargs = kwargs
        return SimpleNamespace(
            output_text=json.dumps(
                {
                    "service_request_type": "Streetlight Repair",
                    "summary": "Broken street lamp near a bus stop.",
                    "public_description": "A street lamp appears broken and needs inspection.",
                    "priority": "Normal",
                    "recommended_311_details": {
                        "location": "1350 Pennsylvania Ave NW",
                        "contact_phone": "202-555-0142",
                    },
                }
            )
        )


class FakeOpenAIClient:
    def __init__(self):
        self.responses = FakeResponses()


def test_build_data_url_uses_image_mime_type_and_base64_content():
    data_url = build_data_url("image/png", b"\x89PNG\r\n\x1a\n")

    assert data_url.startswith("data:image/png;base64,")
    assert data_url.endswith("iVBORw0KGgo=")


def test_generate_report_calls_responses_api_with_text_image_and_phone():
    client = FakeOpenAIClient()
    payload = ReportPayload(
        description="Broken street lamp flickering near the bus stop.",
        location="1350 Pennsylvania Ave NW",
        phone="202-555-0142",
    )

    report = generate_report(
        client=client,
        payload=payload,
        image_data_url="data:image/png;base64,abc123",
        model="gpt-5.6",
    )

    request = client.responses.kwargs
    content = request["input"][0]["content"]
    prompt_text = content[0]["text"]

    assert request["model"] == "gpt-5.6"
    assert content[1]["type"] == "input_image"
    assert content[1]["image_url"] == "data:image/png;base64,abc123"
    assert "Broken street lamp" in prompt_text
    assert "1350 Pennsylvania Ave NW" in prompt_text
    assert "202-555-0142" in prompt_text
    assert report["service_request_type"] == "Streetlight Repair"


def test_generate_report_parses_embedded_json_response():
    client = FakeOpenAIClient()
    client.responses.create = lambda **_: SimpleNamespace(
        output_text='Report:\n{"service_request_type":"Other","summary":"Issue noted.","public_description":"Issue requires review.","priority":"Low","recommended_311_details":{}}'
    )
    payload = ReportPayload(
        description="Unknown street issue.",
        location="15th St NW",
        phone="202-555-0142",
    )

    report = generate_report(
        client=client,
        payload=payload,
        image_data_url="data:image/png;base64,abc123",
        model="gpt-5.6",
    )

    assert report["service_request_type"] == "Other"


@pytest.mark.parametrize(
    "output_text",
    [
        "",
        "not json",
        '{"summary":"Missing required fields"}',
        '["not", "an", "object"]',
        '{"service_request_type":"Other","summary":"Issue","public_description":"Desc","priority":"Low","recommended_311_details":[]}',
    ],
)
def test_generate_report_rejects_invalid_model_output(output_text):
    client = FakeOpenAIClient()
    client.responses.create = lambda **_: SimpleNamespace(output_text=output_text)
    payload = ReportPayload(
        description="Unknown street issue.",
        location="15th St NW",
        phone="202-555-0142",
    )

    with pytest.raises(ReportGenerationError):
        generate_report(
            client=client,
            payload=payload,
            image_data_url="data:image/png;base64,abc123",
            model="gpt-5.6",
        )


def test_generate_report_wraps_openai_errors():
    client = FakeOpenAIClient()

    def fail(**_kwargs):
        raise RuntimeError("network detail")

    client.responses.create = fail
    payload = ReportPayload(
        description="Unknown street issue.",
        location="15th St NW",
        phone="202-555-0142",
    )

    with pytest.raises(ReportGenerationError, match="Could not generate"):
        generate_report(
            client=client,
            payload=payload,
            image_data_url="data:image/png;base64,abc123",
            model="gpt-5.6",
        )
