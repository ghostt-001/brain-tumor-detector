const API = "http://127.0.0.1:5000";

/* NAVBAR */
const navbar = document.getElementById("navbar");

window.addEventListener("scroll", () => {
    if (window.scrollY > 50) {
        navbar.classList.add("scrolled");
    } else {
        navbar.classList.remove("scrolled");
    }
});

/* POPUP */
function openPopup() {
    document.getElementById("popup").style.display = "flex";
}

function closePopup() {
    document.getElementById("popup").style.display = "none";
}

/* CLICK OUTSIDE CLOSE */
window.addEventListener("click", (e) => {
    const popup = document.getElementById("popup");
    if (e.target === popup) {
        popup.style.display = "none";
    }
});

/* LOGIN CHECK */
async function handleUpload() {
    try {
        const res = await fetch(API + "/check", {
            credentials: "include"
        });

        const data = await res.json();

        if (data.loggedIn) {
            window.location.href = "upload.html";
        } else {
            openPopup();
        }

    } catch (err) {
        alert("Backend not running");
    }
}