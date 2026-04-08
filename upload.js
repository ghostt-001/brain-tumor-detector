const API = "http://127.0.0.1:5000";

let file;

/* LOAD USER */
async function loadUser(){
    const res = await fetch(API + "/check", { credentials: "include" });
    const data = await res.json();
    if(data.loggedIn){
        document.getElementById("welcomeText").innerText = "Welcome, " + data.user;
    }
}
loadUser();

/* PROFILE MENU */
const profile = document.getElementById("profile");
const menu = document.getElementById("menu");

profile.addEventListener("click", () => {
    menu.style.display = menu.style.display === "block" ? "none" : "block";
});

window.addEventListener("click", (e) => {
    if(!profile.contains(e.target)) menu.style.display = "none";
});

/* FILE */
fileInput.onchange = () => {
    file = fileInput.files[0];
    preview(URL.createObjectURL(file));
    // Hide any previous result or error when new image is selected
    document.getElementById("resultCard").classList.add("hidden");
    hideError();
};

/* PREVIEW */
function preview(src){
    document.getElementById("previewImg").src = src;
    document.getElementById("previewCard").classList.remove("hidden");
}

/* URL */
function loadFromURL(){
    preview(document.getElementById("imageUrl").value);
}

/* SHOW / HIDE ERROR BANNER */
function showError(msg){
    let banner = document.getElementById("errorBanner");
    if(!banner){
        banner = document.createElement("div");
        banner.id = "errorBanner";
        banner.style.cssText = `
            background: #ff4d4d;
            color: white;
            padding: 14px 20px;
            border-radius: 10px;
            margin: 16px 0;
            font-size: 15px;
            font-weight: 500;
            display: flex;
            align-items: center;
            gap: 10px;
        `;
        // Insert above the analyze button
        const analyzeBtn = document.querySelector("button[onclick='analyze()']") ||
                           document.querySelector(".analyze-btn") ||
                           document.getElementById("analyzeBtn");
        if(analyzeBtn) analyzeBtn.parentNode.insertBefore(banner, analyzeBtn);
        else document.body.appendChild(banner);
    }
    banner.innerHTML = `⚠️ ${msg}`;
    banner.style.display = "flex";
}

function hideError(){
    const banner = document.getElementById("errorBanner");
    if(banner) banner.style.display = "none";
}

/* ANALYZE */
async function analyze(){
    if(!file){
        showError("Please upload an image first.");
        return;
    }

    hideError();
    const popup = document.getElementById("loadingPopup");
    popup.classList.add("active");

    try {
        // ── STEP 1: Validate image with Claude AI ──
        const validateForm = new FormData();
        validateForm.append("file", file);

        popup.querySelector && (popup.querySelector("p") || {innerText: ""}).innerText;

        const validateRes = await fetch(API + "/validate", {
            method: "POST",
            body: validateForm
        });

        const validateData = await validateRes.json();

        if(!validateData.valid){
            popup.classList.remove("active");
            document.getElementById("resultCard").classList.add("hidden");
            showError(
                `Invalid image: ${validateData.reason} — Please upload a brain MRI scan only.`
            );
            return;
        }

        // ── STEP 2: Run model prediction ──
        const predictForm = new FormData();
        predictForm.append("file", file);

        const res = await fetch(API + "/predict", {
            method: "POST",
            body: predictForm
        });

        const data = await res.json();

        setTimeout(() => {
            popup.classList.remove("active");

            if(data.error){
                showError("Prediction error: " + data.error);
                return;
            }

            document.getElementById("resultCard").classList.remove("hidden");
            document.getElementById("resultTitle").innerText = data.result;
            document.getElementById("confidence").innerText = "Confidence: " + data.confidence + "%";

            // Show extra message if uncertain
            document.getElementById("details").innerText = data.message
                ? data.message
                : "Detected using AI model. Results are for reference only.";

            document.getElementById("progressFill").style.width = data.confidence + "%";

            // Color the result title based on outcome
            const titleEl = document.getElementById("resultTitle");
            if(data.result === "No Tumor"){
                titleEl.style.color = "#4caf50";
            } else if(data.result === "Uncertain"){
                titleEl.style.color = "#ff9800";
            } else {
                titleEl.style.color = "#ff4d4d";
            }

        }, 1500);

    } catch(err) {
        popup.classList.remove("active");
        showError("Something went wrong. Please try again.");
    }
}

/* LOGOUT */
async function logout(){
    await fetch(API + "/logout", { credentials: "include" });
    location.href = "/";
}

/* DOWNLOAD */
function downloadReport(){
    const result = document.getElementById("resultTitle").innerText;
    const confidence = document.getElementById("confidence").innerText;
    const details = document.getElementById("details").innerText;
    const text = `Brain Tumor Detection Report\n============================\nResult: ${result}\n${confidence}\n\n${details}\n\nGenerated on: ${new Date().toLocaleString()}`;
    const blob = new Blob([text], { type: "text/plain" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "brain_tumor_report.txt";
    a.click();
}
