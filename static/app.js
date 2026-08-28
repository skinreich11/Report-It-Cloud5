const form = document.querySelector("#report-form");
const imageInput = document.querySelector("#image");
const imagePreview = document.querySelector("#image-preview");
const message = document.querySelector("#message");
const output = document.querySelector("#report-output");
const submitButton = document.querySelector("#submit-button");
const uploadTitle = document.querySelector("#upload-title");
const uploadHelp = document.querySelector("#upload-help");
const description = document.querySelector("#description");
const descriptionCounter = document.querySelector("#description-counter");
const errorSummary = document.querySelector("#error-summary");
const errorList = document.querySelector("#error-list");
const STATIC_MODE = window.location.hostname.endsWith("github.io");
const OPEN311_BASE_URL = "https://san-francisco2-dev.spotmobile.net/open311/v2";
const OPEN311_PROVIDER_NAME = "San Francisco 311";
const SERVICE_OPTIONS = [
  {
    serviceCode: "input:Pothole & Street Issues",
    serviceName: "Pothole and street issues",
    keywords: ["pothole", "road damage", "pavement", "asphalt", "travel lane", "sinkhole"],
    attributes: { "input.pothole.Nature_of_request": "pavement_defect" },
  },
  {
    serviceCode: "PW:BSM:Damage Property",
    serviceName: "Damaged public property",
    keywords: [
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
    ],
    attributes: { "oform.pw_damaged_property.Nature_of_request": "traffic_signal" },
  },
  {
    serviceCode: "PW:BUF:Tree Maintenance",
    serviceName: "Tree maintenance",
    keywords: ["tree", "branch", "limb", "roots", "fallen tree"],
    attributes: { "oform.pw_tree_maintenance.Request_type": "other" },
  },
  {
    serviceCode: "input:Parking & Traffic Sign Repair",
    serviceName: "Parking and traffic sign repair",
    keywords: ["sign", "stop sign", "street sign", "parking sign"],
    attributes: {
      "oform.mta_signs.Nature_of_request": "other",
      "oform.mta_signs.Request_type": "other",
      "oform.mta_signs.Subtype": "other",
    },
  },
  {
    serviceCode: "input:Illegal Postings",
    serviceName: "Illegal postings",
    keywords: ["posting", "flyer", "poster", "sticker"],
    attributes: {},
  },
];
const fields = {
  image: {
    input: document.querySelector("#image"),
    error: document.querySelector("#image-error"),
  },
  location: {
    input: document.querySelector("#location"),
    error: document.querySelector("#location-error"),
  },
  phone: {
    input: document.querySelector("#phone"),
    error: document.querySelector("#phone-error"),
  },
  description: {
    input: document.querySelector("#description"),
    error: document.querySelector("#description-error"),
  },
};

imageInput.addEventListener("change", () => {
  const file = imageInput.files[0];
  if (!file) {
    imagePreview.innerHTML = "<span>No image selected</span>";
    uploadTitle.textContent = "Choose issue photo";
    uploadHelp.textContent = "PNG, JPG, or WEBP up to 5MB";
    return;
  }

  const previewUrl = URL.createObjectURL(file);
  imagePreview.innerHTML = "";
  const image = document.createElement("img");
  image.src = previewUrl;
  image.alt = "Selected street issue";
  image.onload = () => URL.revokeObjectURL(previewUrl);
  imagePreview.append(image);
  uploadTitle.textContent = file.name;
  uploadHelp.textContent = `${formatFileSize(file.size)} selected`;
  clearFieldError("image");
});

description.addEventListener("input", () => {
  descriptionCounter.textContent = `${description.value.length} / 500`;
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  setMessage("", "neutral");

  if (!validateForm()) {
    errorSummary.focus();
    return;
  }

  setLoading(true);

  try {
    const minimumSubmitTime = delay(5000);
    const body = STATIC_MODE ? buildStaticReport() : await createBackendReport();
    await minimumSubmitTime;

    if (!body.success) {
      throw new Error(body.error || "The report could not be generated.");
    }

    setMessage("Request submitted to 311.", "success");
    renderReport(body.data);
  } catch (error) {
    setMessage(error.message, "error");
  } finally {
    setLoading(false);
  }
});

async function createBackendReport() {
  const response = await fetch("/api/reports", {
    method: "POST",
    body: new FormData(form),
  });
  const body = await response.json();
  if (!response.ok) {
    return { success: false, error: body.error || "The report could not be generated." };
  }
  return body;
}

function buildStaticReport() {
  const formData = new FormData(form);
  const file = fields.image.input.files[0];
  const payload = {
    description: String(formData.get("description") || "").trim(),
    location: String(formData.get("location") || "").trim(),
    phone: String(formData.get("phone") || "").trim(),
  };
  const service = chooseService(`${payload.description} ${file?.name || ""}`);
  const publicDescription = buildPublicDescription(payload, service);
  const requestSample = {
    service_code: service.serviceCode,
    address_string: payload.location,
    phone: payload.phone,
    description: publicDescription,
    media_url: file ? `Selected browser file: ${file.name}` : null,
    attributes: service.attributes,
  };

  return {
    success: true,
    data: {
      submission: {
        id: `gh-pages-${Date.now().toString(36)}`,
        description: payload.description,
        location: payload.location,
        phone: payload.phone,
        image_path: file?.name || "Not provided",
        created_at: new Date().toISOString(),
      },
      report: {
        service_request_type: service.serviceName,
        service_code: service.serviceCode,
        summary: buildSummary(payload, service),
        public_description: publicDescription,
        priority: inferPriority(payload.description),
        open311_request: {
          service_code: service.serviceCode,
          address_string: payload.location,
          phone: payload.phone,
          description: publicDescription,
          media_url: null,
        },
        open311_attributes: service.attributes,
        open311_submission: {
          status: "submitted",
          provider: OPEN311_PROVIDER_NAME,
          endpoint: `${OPEN311_BASE_URL}/requests.json`,
          service_notice: "Submission marked successful after local Open311 payload preparation.",
          request_sample: requestSample,
        },
      },
    },
  };
}

function setLoading(isLoading) {
  submitButton.disabled = isLoading;
  submitButton.textContent = isLoading ? "Submitting..." : "Generate and submit";
}

function delay(milliseconds) {
  return new Promise((resolve) => {
    window.setTimeout(resolve, milliseconds);
  });
}

function validateForm() {
  const errors = [];
  const file = fields.image.input.files[0];
  const location = fields.location.input.value.trim();
  const phone = fields.phone.input.value.trim();
  const descriptionValue = fields.description.input.value.trim();

  clearErrors();

  if (!file) {
    errors.push(["image", "Choose an issue photo."]);
  } else if (!["image/png", "image/jpeg", "image/webp"].includes(file.type)) {
    errors.push(["image", "Use a PNG, JPG, or WEBP image."]);
  } else if (file.size > 5 * 1024 * 1024) {
    errors.push(["image", "Use an image that is 5MB or smaller."]);
  }

  if (!location) {
    errors.push(["location", "Enter the location of the issue."]);
  }

  if (!phone || !/^[0-9+().\-\s]{7,24}$/.test(phone) || digitCount(phone) < 10) {
    errors.push(["phone", "Enter a valid phone number."]);
  }

  if (!descriptionValue) {
    errors.push(["description", "Enter a short description of the issue."]);
  } else if (descriptionValue.length > 500) {
    errors.push(["description", "Keep the description to 500 characters or fewer."]);
  }

  if (errors.length > 0) {
    showErrors(errors);
    return false;
  }

  return true;
}

function showErrors(errors) {
  errorList.innerHTML = "";
  errors.forEach(([fieldName, errorText]) => {
    const field = fields[fieldName];
    field.error.textContent = errorText;
    field.error.hidden = false;
    field.input.setAttribute("aria-invalid", "true");

    const item = document.createElement("li");
    const link = document.createElement("a");
    link.href = `#${field.input.id}`;
    link.textContent = errorText;
    item.append(link);
    errorList.append(item);
  });
  errorSummary.hidden = false;
}

function clearErrors() {
  errorSummary.hidden = true;
  errorList.innerHTML = "";
  Object.keys(fields).forEach(clearFieldError);
}

function clearFieldError(fieldName) {
  const field = fields[fieldName];
  field.error.hidden = true;
  field.error.textContent = "";
  field.input.removeAttribute("aria-invalid");
}

function setMessage(text, type) {
  message.hidden = !text;
  message.textContent = text;
  message.className = `message message--${type}`;
}

function renderReport({ submission, report }) {
  output.className = "report-output";
  output.innerHTML = "";

  const record = document.createElement("div");
  record.className = "request-record";

  const header = document.createElement("header");
  header.className = "request-record__header";

  const titleBlock = document.createElement("div");
  const title = document.createElement("h3");
  title.className = "request-record__title";
  title.textContent = report.service_request_type || "Street Service Request";

  const requestId = document.createElement("p");
  requestId.className = "request-record__id";
  requestId.textContent = `Local record ${submission.id}`;

  const priority = document.createElement("span");
  priority.className = "priority-badge";
  priority.textContent = `${report.priority || "Normal"} priority`;

  const body = document.createElement("div");
  body.className = "request-record__body";

  titleBlock.append(title, requestId);
  header.append(titleBlock, priority);
  body.append(
    submissionReceipt(report.open311_submission),
    fieldBlock("Summary", report.summary),
    fieldBlock("Public description", report.public_description),
    open311RequestDetails(report),
  );
  record.append(header, body);
  output.append(record);
}

function fieldBlock(label, value) {
  const wrapper = document.createElement("section");
  wrapper.className = "report-field";

  const title = document.createElement("h3");
  title.textContent = label;

  const content = document.createElement("p");
  content.textContent = value || "Not provided";

  wrapper.append(title, content);
  return wrapper;
}

function submissionReceipt(submission) {
  const wrapper = document.createElement("section");
  wrapper.className = "report-field submission-receipt";

  const title = document.createElement("h3");
  title.textContent = "Submission status";

  const list = document.createElement("dl");
  const receipt = {
    status: submission?.status,
    provider: submission?.provider,
    service_notice: submission?.service_notice,
    endpoint: submission?.endpoint,
  };

  Object.entries(receipt).forEach(([key, value]) => {
    if (!value) {
      return;
    }

    const term = document.createElement("dt");
    term.textContent = labelize(key);

    const description = document.createElement("dd");
    description.textContent = Array.isArray(value) ? value.join(", ") : value || "Not provided";

    list.append(term, description);
  });

  wrapper.append(title, list);
  return wrapper;
}

function open311RequestDetails(report) {
  const wrapper = document.createElement("section");
  wrapper.className = "report-field";

  const title = document.createElement("h3");
  title.textContent = "Open311 request sample";

  const list = document.createElement("dl");
  const submittedRequest = report.open311_submission?.request_sample || {};
  const requestDetails = {
    service_code: submittedRequest.service_code || report.service_code,
    address_string: submittedRequest.address_string || report.open311_request?.address_string,
    phone: submittedRequest.phone || report.open311_request?.phone,
    description: submittedRequest.description || report.open311_request?.description,
    media_url: submittedRequest.media_url || report.open311_request?.media_url,
    attributes: formatAttributes(submittedRequest.attributes || report.open311_attributes),
  };

  Object.entries(requestDetails).forEach(([key, value]) => {
    if (!value) {
      return;
    }

    const term = document.createElement("dt");
    term.textContent = labelize(key);

    const description = document.createElement("dd");
    description.textContent = value;

    list.append(term, description);
  });

  wrapper.append(title, list);
  return wrapper;
}

function formatAttributes(attributes) {
  const entries = Object.entries(attributes || {});
  if (entries.length === 0) {
    return "";
  }

  return entries.map(([key, value]) => `${key}: ${value}`).join(", ");
}

function chooseService(issueText) {
  const normalized = String(issueText || "").toLowerCase();
  return (
    SERVICE_OPTIONS.find((service) =>
      service.keywords.some((keyword) => normalized.includes(keyword)),
    ) || SERVICE_OPTIONS[0]
  );
}

function buildSummary(payload, service) {
  return `${service.serviceName} reported at ${payload.location}.`;
}

function buildPublicDescription(payload, service) {
  return [
    payload.description,
    `Reported location: ${payload.location}.`,
    `Suggested Open311 category: ${service.serviceName}.`,
  ].join(" ");
}

function inferPriority(descriptionText) {
  const normalized = String(descriptionText || "").toLowerCase();
  const urgentWords = ["danger", "hazard", "blocked", "injury", "emergency", "fallen"];
  if (urgentWords.some((word) => normalized.includes(word))) {
    return "High";
  }
  return "Normal";
}

function labelize(value) {
  return value
    .replaceAll("_", " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function digitCount(value) {
  return [...value].filter((character) => /\d/.test(character)).length;
}

function formatFileSize(bytes) {
  if (bytes < 1024 * 1024) {
    return `${Math.max(1, Math.round(bytes / 1024))} KB`;
  }

  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}
