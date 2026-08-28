import base64
import json


class ReportGenerationError(RuntimeError):
    pass


REPORT_SCHEMA_KEYS = {
    "service_request_type",
    "summary",
    "public_description",
    "priority",
    "recommended_311_details",
}


def build_data_url(mime_type, content):
    encoded = base64.b64encode(content).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"


def generate_report(*, client, payload, image_data_url, model):
    prompt = _build_prompt(payload)
    try:
        response = client.responses.create(
            model=model,
            input=[
                {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": prompt},
                        {
                            "type": "input_image",
                            "image_url": image_data_url,
                            "detail": "auto",
                        },
                    ],
                }
            ],
            max_output_tokens=900,
        )
    except Exception as error:
        raise ReportGenerationError("Could not generate the report") from error

    return _parse_report_text(getattr(response, "output_text", ""))


def _build_prompt(payload):
    return f"""
Create a DC 311-style street issue report draft from the submitted details and image.

Return only a JSON object with these fields:
- service_request_type: closest DC 311 category, such as Streetlight Repair, Roadway Repair, Sidewalk Repair, Tree Inspection, Traffic Signal Issue, Illegal Dumping, or Other
- summary: one concise sentence
- public_description: 2-4 sentences suitable for a public service request
- priority: Low, Normal, High, or Urgent
- recommended_311_details: object with location, contact_phone, observed_issue, visible_hazards, and image_notes

Submitted details:
Description: {payload.description}
Location: {payload.location}
Contact phone: {payload.phone}

Do not invent a full address if the location is incomplete. If the issue category is uncertain, use Other and explain the uncertainty in public_description.

TODO: Add a follow-up integration that can communicate with the DC 311 website and create the official request from this validated report data after user confirmation.
""".strip()


def _parse_report_text(output_text):
    if not output_text:
        raise ReportGenerationError("The report generator returned no text")

    try:
        report = json.loads(output_text)
    except json.JSONDecodeError:
        report = _parse_embedded_json(output_text)

    if not isinstance(report, dict):
        raise ReportGenerationError("The report generator returned an invalid report")

    missing_keys = REPORT_SCHEMA_KEYS - set(report)
    if missing_keys:
        raise ReportGenerationError("The report generator returned an incomplete report")

    details = report.get("recommended_311_details")
    if not isinstance(details, dict):
        raise ReportGenerationError("The report generator returned invalid 311 details")

    return report


def _parse_embedded_json(output_text):
    first_brace = output_text.find("{")
    if first_brace == -1:
        raise ReportGenerationError("The report generator returned non-JSON text")

    decoder = json.JSONDecoder()
    try:
        report, _ = decoder.raw_decode(output_text[first_brace:])
    except json.JSONDecodeError as error:
        raise ReportGenerationError("The report generator returned malformed JSON") from error

    return report
