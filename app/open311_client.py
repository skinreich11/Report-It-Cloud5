from dataclasses import dataclass
from urllib.parse import urljoin


@dataclass(frozen=True)
class ServiceOption:
    service_code: str
    service_name: str
    keywords: tuple[str, ...]
    attributes: dict[str, str]


SAN_FRANCISCO_SERVICES = (
    ServiceOption(
        service_code="input:Pothole & Street Issues",
        service_name="Pothole and street issues",
        keywords=("pothole", "road damage", "pavement", "asphalt", "travel lane", "sinkhole"),
        attributes={"input.pothole.Nature_of_request": "pavement_defect"},
    ),
    ServiceOption(
        service_code="PW:BSM:Damage Property",
        service_name="Damaged public property",
        keywords=(
            "lamp",
            "light",
            "streetlight",
            "traffic signal",
            "signal",
            "bench",
            "bike rack",
            "shelter",
            "public property",
            "broken fixture",
        ),
        attributes={"oform.pw_damaged_property.Nature_of_request": "traffic_signal"},
    ),
    ServiceOption(
        service_code="PW:BUF:Tree Maintenance",
        service_name="Tree maintenance",
        keywords=("tree", "branch", "limb", "roots", "fallen tree"),
        attributes={"oform.pw_tree_maintenance.Request_type": "other"},
    ),
    ServiceOption(
        service_code="input:Parking & Traffic Sign Repair",
        service_name="Parking and traffic sign repair",
        keywords=("sign", "stop sign", "street sign", "parking sign"),
        attributes={
            "oform.mta_signs.Nature_of_request": "other",
            "oform.mta_signs.Request_type": "other",
            "oform.mta_signs.Subtype": "other",
        },
    ),
    ServiceOption(
        service_code="input:Illegal Postings",
        service_name="Illegal postings",
        keywords=("posting", "flyer", "poster", "sticker"),
        attributes={},
    ),
)
DEFAULT_SERVICE = SAN_FRANCISCO_SERVICES[0]


def choose_service(issue_text):
    normalized = str(issue_text or "").lower()
    for service in SAN_FRANCISCO_SERVICES:
        if any(keyword in normalized for keyword in service.keywords):
            return _service_dict(service)
    return _service_dict(DEFAULT_SERVICE)


def build_open311_request(*, report, payload, media_url=None):
    selected = _service_for_report(report)
    attributes = _valid_attributes(
        selected=selected,
        generated_attributes=report.get("open311_attributes"),
    )
    request_data = {
        "service_code": selected.service_code,
        "address_string": payload.location,
        "phone": payload.phone,
        "description": _request_description(report, payload),
    }
    if media_url:
        request_data = {**request_data, "media_url": media_url}

    return {
        **request_data,
        **{f"attribute[{key}]": value for key, value in attributes.items()},
    }


def build_media_url(public_base_url, filename):
    if not public_base_url:
        return None
    base_url = str(public_base_url).rstrip("/") + "/"
    return urljoin(base_url, f"uploads/{filename}")


def build_mock_submission_result(*, request_data, provider_name, base_url):
    endpoint = f"{str(base_url).rstrip('/')}/requests.json"
    return {
        "status": "submitted",
        "provider": provider_name,
        "endpoint": endpoint,
        "service_notice": "Submission marked successful after local Open311 payload preparation.",
        "request_sample": _request_sample(request_data),
    }


def _service_for_report(report):
    service_code = str(report.get("service_code") or "").strip()
    for service in SAN_FRANCISCO_SERVICES:
        if service.service_code == service_code:
            return service
    issue_text = " ".join(
        [
            str(report.get("service_request_type") or ""),
            str(report.get("summary") or ""),
            str(report.get("public_description") or ""),
        ]
    )
    selected = choose_service(issue_text)
    return ServiceOption(
        service_code=selected["service_code"],
        service_name=selected["service_name"],
        keywords=tuple(selected["keywords"]),
        attributes=dict(selected["attributes"]),
    )


def _valid_attributes(*, selected, generated_attributes):
    if not isinstance(generated_attributes, dict):
        return selected.attributes

    valid_attributes = {
        key: str(generated_attributes.get(key) or fallback)
        for key, fallback in selected.attributes.items()
    }
    return valid_attributes


def _request_description(report, payload):
    description = str(report.get("public_description") or payload.description).strip()
    return description[:4000]


def _service_dict(service):
    return {
        "service_code": service.service_code,
        "service_name": service.service_name,
        "keywords": service.keywords,
        "attributes": service.attributes,
    }


def _request_sample(request_data):
    return {
        "service_code": request_data.get("service_code"),
        "address_string": request_data.get("address_string"),
        "phone": request_data.get("phone"),
        "description": request_data.get("description"),
        "media_url": request_data.get("media_url"),
        "attributes": {
            key.removeprefix("attribute[").removesuffix("]"): value
            for key, value in request_data.items()
            if key.startswith("attribute[")
        },
    }
