const API = "http://127.0.0.1:5000";

function showRegister() {
    document.getElementById("login-form").classList.remove("active");
    document.getElementById("register-form").classList.add("active");
}

function showLogin() {
    document.getElementById("register-form").classList.remove("active");
    document.getElementById("login-form").classList.add("active");
}

/* REGISTER */
async function register() {
    const name = document.getElementById("name").value;
    const email = document.getElementById("email").value;
    const password = document.getElementById("password").value;

    const res = await fetch(API + "/register", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({name, email, password})
    });

    const data = await res.json();
    alert(data.message || data.error);
}

/* LOGIN */
async function handleLogin() {
    const email = document.getElementById("login-email").value;
    const password = document.getElementById("login-password").value;

    const res = await fetch(API + "/login", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({email, password}),
        credentials: "include"
    });

    const data = await res.json();

    if (res.ok) {
        alert("Login successful");
        window.location.href = "/";
    } else {
        alert(data.error);
    }
}