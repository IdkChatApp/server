const auth_title = document.getElementById("auth-form-title");
const auth_title2 = document.getElementById("auth-form-title2");
const login_input = document.getElementById("login");
const password_input = document.getElementById("password");
const password2_input = document.getElementById("password2");
const password2_div = document.getElementById("password2-div");
const btn_login = document.getElementById("btn_login");
const btn_register = document.getElementById("btn_register");

function toggleMode() {
    let login = auth_title.innerText.trim() === "Login";
    auth_title.innerText = login ? "Register" : "Login";
    auth_title2.innerText = login ? "or Login (click here)" : "or Register (click here)";
    password2_div.style.display = login ? "" : "none";
    btn_register.style.display = login ? "" : "none";
    btn_login.style.display = login ? "none" : "";
}

async function _processAuthResponse(resp) {
    let jsonResp = await resp.json();

    if(resp.status > 400 && resp.status < 405) {
        alert(jsonResp.message);
        return;
    }

    if(resp.status !== 200) {
        alert("Unknown error occured! Please try again later.");
        return;
    }

    localStorage.setItem("token", jsonResp["token"]);
    location.href = "/dialogs.html";
}

async function login() {
    let login = login_input.value.trim();
    let password = password_input.value.trim();

    let resp = await fetch(`${window.API_ENDPOINT}/auth/login`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({"login": login, "password": password})
    });

    await _processAuthResponse(resp);
}

async function register() {
    let login = login_input.value.trim();
    let password = password_input.value.trim();
    let password2 = password2_input.value.trim();

    if(password !== password2) {
        alert("Passwords do not match!");
        return;
    }

    let resp = await fetch(`${window.API_ENDPOINT}/auth/register`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({"login": login, "password": password})
    });

    await _processAuthResponse(resp);
}

if (document.readyState !== 'loading') {
    if(localStorage.getItem("token"))
        location.href = "/dialogs.html";
} else {
    window.addEventListener("DOMContentLoaded", async () => {
        if(localStorage.getItem("token"))
            location.href = "/dialogs.html";
    }, false);
}