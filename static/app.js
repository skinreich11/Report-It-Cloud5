const form = document.querySelector("#report-form");
const imageInput = document.querySelector("#image");
const imagePreview = document.querySelector("#image-preview");
const message = document.querySelector("#message");
const output = document.querySelector("#report-output");
const submitButton = document.querySelector("#submit-button");

imageInput.addEventListener("change", () => {
  const file = imageInput.files[0];
  if (!file) {
    imagePreview.innerHTML = "<span>No image selected</span>";
    return;
  }

  const previewUrl = URL.createObjectURL(file);
  imagePreview.innerHTML = "";
  const image = document.createElement("img");
  image.src = previewUrl;
  image.alt = "Selected street issue";
  image.onload = () => URL.revokeObjectURL(previewUrl);
  imagePreview.append(image);
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  setMessage("", "neutral");
  setLoading(true);

  try {
    const response = await fetch("/api/reports", {
      method: "POST",
      body: new FormData(form),
    });
    const body = await response.json();

    if (!response.ok || !body.success) {
      throw new Error(body.error || "The report could not be generated.");
    }

    renderReport(body.data);
    setMessage("Report draft generated.", "success");
  } catch (error) {
    setMessage(error.message, "error");
  } finally {
    setLoading(false);
  }
});

function setLoading(isLoading) {
  submitButton.disabled = isLoading;
  submitButton.textContent = isLoading ? "Generating..." : "Generate report";
}

function setMessage(text, type) {
  message.hidden = !text;
  message.textContent = text;
  message.className = `message message--${type}`;
}

function renderReport({ submission, report }) {
  output.className = "report-output";
  output.innerHTML = "";

  output.append(
    fieldBlock("Request ID", submission.id),
    fieldBlock("Service request type", report.service_request_type),
    fieldBlock("Priority", report.priority),
    fieldBlock("Summary", report.summary),
    fieldBlock("Public description", report.public_description),
    detailList(report.recommended_311_details),
  );
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

function detailList(details) {
  const wrapper = document.createElement("section");
  wrapper.className = "report-field";

  const title = document.createElement("h3");
  title.textContent = "311 details";

  const list = document.createElement("dl");
  Object.entries(details || {}).forEach(([key, value]) => {
    const term = document.createElement("dt");
    term.textContent = labelize(key);

    const description = document.createElement("dd");
    description.textContent = Array.isArray(value) ? value.join(", ") : value || "Not provided";

    list.append(term, description);
  });

  wrapper.append(title, list);
  return wrapper;
}

function labelize(value) {
  return value
    .replaceAll("_", " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}
