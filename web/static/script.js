let thumbs = [];
let cropper;

function showTab(index) {
    document.querySelectorAll(".tab-content").forEach((el, i) => {
        el.style.display = i === index ? "block" : "none";
    });
    document.querySelectorAll(".tabs button").forEach((btn, i) => {
        btn.classList.toggle("active", i === index);
    });
}

function updateCheckboxState() {
    for (let i = 0; i < 3; i++) {
        const faceBox = document.getElementById(`face-${i}`);
        const useCheckbox = document.getElementById(`use-${i}`);
        const hasImage = faceBox.querySelector("img") !== null;
        useCheckbox.disabled = !hasImage;
        useCheckbox.checked = hasImage
    }
}

function loadImage() {
    const file = document.getElementById("image-input").files[0];
    if (file) {
        const img = document.getElementById("crop-image");
        img.src = URL.createObjectURL(file);
        img.style.display = "block";
        if (cropper) cropper.destroy();

        cropper = new Cropper(img, {
            aspectRatio: 215 / 265,
            viewMode: 1,
            autoCropArea: 0.8,
            movable: true,
            zoomable: true,
        });

        document.querySelectorAll(".copy-btn").forEach(btn => btn.disabled = false);

        document.getElementById("copy-0").onclick = () => copyToFace(0);
        document.getElementById("copy-1").onclick = () => copyToFace(1);
        document.getElementById("copy-2").onclick = () => copyToFace(2);
    } else {
        document.querySelectorAll(".copy-btn").forEach(btn => btn.disabled = true);
    }
    updateCheckboxState();
}

function copyToFace(index) {
    if (cropper) {
        const canvas = cropper.getCroppedCanvas({width: 215, height: 265});
        const imgEl = document.createElement("img");
        imgEl.src = canvas.toDataURL();
        const faceBox = document.getElementById(`face-${index}`);
        faceBox.innerHTML = "";
        faceBox.appendChild(imgEl);

        cropper.destroy();
        const img = document.getElementById("crop-image");
        img.src = "";
        img.style.display = "none";
        document.querySelectorAll(".copy-btn").forEach(btn => btn.disabled = true);

        updateCheckboxState();
    }
}

async function executeRecaptcha() {
    const recaptchaResponse = window.grecaptcha ? grecaptcha.getResponse() : '';
    if (!window.__CF$cv$params && !recaptchaResponse) {
        Swal.fire({
            title: "CAPTCHA Required",
            text: "Please complete the CAPTCHA to proceed.",
            icon: "warning",
            confirmButtonText: "OK"
        });
        return null;
    }
    return recaptchaResponse
}

async function submitFaces() {
    const recaptchaResponse = window.grecaptcha ? grecaptcha.getResponse() : '';
    if (!window.__CF$cv$params && !recaptchaResponse) {
        Swal.fire({
            title: "CAPTCHA Required",
            text: "Please complete the CAPTCHA to proceed.",
            icon: "warning",
            confirmButtonText: "OK"
        });
        return;
    }

    const images = Array.from(document.querySelectorAll(".face-box img"))
        .map((img, index) => ({
            src: img.src,
            use: document.getElementById(`use-${index}`).checked
        }))
        .filter(item => item.use)
        .map(item => item.src);

    const eventId = document.getElementById("event-select").value;
    const bib = document.getElementById("bib-number").value.trim();
    if (!eventId) return Swal.fire("Missing Event", "Please select an event.", "warning");
    if (!/^\d{1,6}$/.test(bib) && images.length === 0) return Swal.fire("Invalid Input", "Please enter a valid bib number or select at least one face.", "warning");
    if (!/^\d{1,6}$/.test(bib)) {
        const result = await Swal.fire({title: "No Bib", text: "Send only image search?", showCancelButton: true});
        if (!result.isConfirmed) return;
    }
    if (images.length === 0) {
        const {value: action} = await Swal.fire({
            title: "No faces selected",
            html: "Press <b>Continue</b> to search photos<br>Press <b>Add</b> to add or use face image",
            icon: "warning",
            showCancelButton: true,
            confirmButtonText: "Continue",
            cancelButtonText: "Add",
            reverseButtons: true,
            focusConfirm: false,
            customClass: {
                confirmButton: "swal2-confirm",
                cancelButton: "swal2-cancel"
            }
        });
        if (action === undefined || action === "Add") {
            return;
        }
    }

    const payload = {
        event_id: parseInt(eventId),
        bib_number: bib,
        images: images,
        recaptcha_token: recaptchaResponse
    };
    const loadingIndicator = document.getElementById('loading-indicator');
    loadingIndicator.style.display = 'flex';
    const response = await fetch(`/mphoto/api/search/`, {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify(payload)
    });
    const data = await response.json();
    loadingIndicator.style.display = 'none';
    if (data.error) {
        await Swal.fire({
            title: "Error",
            text: data.error,
            icon: "error",
            confirmButtonText: "OK"
        });
        return;
    }
    thumbs = data;
    document.getElementById("tab1").disabled = false;
    showTab(1);
    displayThumbs();
    document.getElementById("submit-faces").disabled = true;
    setTimeout(() => document.getElementById("submit-faces").disabled = false, 5000);
    grecaptcha.reset();
}

function createDownloadLink(dl, name) {
    const p = document.createElement('p');
    const link = document.createElement('a');
    link.href = dl;
    link.classList.add('btn', 'btn-primary', 'btn-sm', 'mt-2')
    const span = document.createElement('span');
    span.textContent = ' ' + name;
    const icon = document.createElement('i');
    icon.classList.add('fa-solid', 'fa-download');
    link.appendChild(icon)
    link.appendChild(span)
    p.appendChild(link)
    return p;
}

function displayThumbs() {
    const grid = document.getElementById("thumbs-grid");
    const totalPhotos = document.getElementById("total-photos");

    grid.innerHTML = "";

    if (thumbs.length === 0) {
        totalPhotos.textContent = "No photos found for the bib and face uploaded.";
    } else {
        totalPhotos.textContent = `Total photos found: ${thumbs.length}`;
        thumbs.forEach(p => {
            const div = document.createElement("div");
            div.style.position = "relative";
            div.classList.add('text-center')
            const img = document.createElement("img");
            img.src = `${p['thumb_link']}`;
            img.style.width = '300px'
            const download = createDownloadLink(p['download_link'], p['name'])
            div.appendChild(img);
            div.appendChild(download);
            grid.appendChild(div);
        });
    }
}

window.onload = () => {
    updateCheckboxState();
};

document.addEventListener("DOMContentLoaded", () => {
    $('#event-select').select2({
        placeholder: 'Select Event...',
        allowClear: true,
        minimumInputLength: 0, // Allow search with any input
        width: '100%', // Match Bootstrap form-control width
        theme: 'bootstrap-5' // Align with Bootstrap 5 styling
    });
});

