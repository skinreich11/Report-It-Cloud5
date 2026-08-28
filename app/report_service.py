import base64
import json


class ReportGenerationError(RuntimeError):
    pass


REPORT_SCHEMA_KEYS = {
    "service_request_type",
    "service_code",
    "summary",
    "public_description",
    "priority",
    "open311_request",
    "open311_attributes",
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
Create a San Francisco Open311 street issue report from the submitted details and image.

Return only a JSON object with these fields:
- service_request_type: closest San Francisco Open311 category from this list: Pothole and street issues, Damaged public property, Tree maintenance, Parking and traffic sign repair, Illegal postings
- service_code: exact matching service_code from this map:
  - Pothole and street issues: input:Pothole & Street Issues
  - Damaged public property: PW:BSM:Damage Property
  - Tree maintenance: PW:BUF:Tree Maintenance
  - Parking and traffic sign repair: input:Parking & Traffic Sign Repair
  - Illegal postings: input:Illegal Postings
- summary: one concise sentence
- public_description: 2-4 sentences suitable for a public Open311 service request, no HTML, under 4000 characters
- priority: Low, Normal, High, or Urgent
- open311_request: object with service_code, address_string, phone, description, and media_url. Use null for media_url because the server will add it if a public URL is configured.
- open311_attributes: object containing required attributes for the selected service_code:
  - input:Pothole & Street Issues requires input.pothole.Nature_of_request. Use one of: Bike_Lane, construction_plate_shifted, Crosswalk, manhole_cover_off, pavement_defect, Street_Lane_Marker, utility_excavation, other
  - PW:BSM:Damage Property requires oform.pw_damaged_property.Nature_of_request. Use one of: benches_on_sidewalk, bike_rack, kiosk_public_toilet, news_rack, parking_meter, traffic_signal, transit_shelter_platform
  - PW:BUF:Tree Maintenance requires oform.pw_tree_maintenance.Request_type. Use one of: about_to_fall, fallen_tree, hanging_limb, damaged_vandalism, hitting_window_or_building, lifted_sidewalk_tree_roots, property_damage, backfill_tree_basin, blocking_sidewalk, blocking_signs, blocking_street_lights, blocking_traffic_signal, other
  - input:Parking & Traffic Sign Repair requires oform.mta_signs.Nature_of_request, oform.mta_signs.Request_type, and oform.mta_signs.Subtype. Use valid values from the SF Open311 service definition; use other when uncertain.
  - input:Illegal Postings has no required attributes.

Submitted details:
Description: {payload.description}
Location: {payload.location}
Contact phone: {payload.phone}

Do not invent a full address if the location is incomplete. If the issue category is uncertain, choose Pothole and street issues only when road damage is visible; otherwise choose Damaged public property and explain uncertainty in public_description.
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

    open311_request = report.get("open311_request")
    if not isinstance(open311_request, dict):
        raise ReportGenerationError("The report generator returned invalid Open311 request details")

    open311_attributes = report.get("open311_attributes")
    if not isinstance(open311_attributes, dict):
        raise ReportGenerationError("The report generator returned invalid Open311 attributes")

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
