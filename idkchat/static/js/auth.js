const authTitle = document.getElementById("authTitle");
const authAlertContainer = document.getElementById("authAlertContainer");
const loginForm = document.getElementById("loginForm");
const signupForm = document.getElementById("signupForm");
const lLoginInput = document.getElementById("login_loginInput");
const lPasswordInput = document.getElementById("login_passwordInput");
const sLoginInput = document.getElementById("signup_loginInput");
const sPasswordInput = document.getElementById("signup_passwordInput");
const sPasswordRepeatInput = document.getElementById("signup_passwordRepeatInput");

const FORMS = {
    "login": loginForm,
    "sign up": signupForm,
}

function showForm(form) {
    for(let f in FORMS) {
        if(f === form) {
            FORMS[f].classList.remove("d-none");
            FORMS[f].classList.add("d-flex");
            continue;
        }
        FORMS[f].classList.remove("d-flex");
        FORMS[f].classList.add("d-none");
    }
    authTitle.innerText = form.charAt(0).toUpperCase() + form.slice(1);
}

async function login() {
    lLoginInput.value = lLoginInput.value.trim();
    lPasswordInput.value = lPasswordInput.value.trim();
    if(!validateInputs(lLoginInput, lPasswordInput)) return;

    let login = lLoginInput.value.trim();
    let password = lPasswordInput.value.trim();

    let srp = new SrpClient(login, password, "sha-256", 2048);
    await srp.preCalculateK();

    let resp = await fetch(`${window.API_ENDPOINT}/auth/login-start`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({"login": login})
    });
    let jsonResp = await resp.json();

    if(resp.status >= 400 && resp.status < 499) {
        return showAlert(jsonResp, authAlertContainer);
    }
    if(resp.status > 499) {
        return showAlert(`Unknown response (status code ${resp.status})! Please try again later.`, authAlertContainer);
    }

    let salt = new SrpBigInteger(jsonResp["salt"]);
    let B = new SrpBigInteger(jsonResp["B"]);
    let ticket = jsonResp["ticket"];
    srp.setSalt(salt);
    srp.setB(B);
    let A = await srp.genA();
    let M = await srp.processChallenge();

    let key = await hashPassword(salt, password);

    resp = await fetch(`${window.API_ENDPOINT}/auth/login`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({"A": A.toStringHex(), "M": M.toStringHex(), "ticket": ticket})
    });
    jsonResp = await resp.json();
    if(resp.status >= 400 && resp.status < 499) {
        return showAlert(jsonResp, authAlertContainer);
    }
    if(resp.status > 499) {
        return showAlert(`Unknown response (status code ${resp.status})! Please try again later.`, authAlertContainer);
    }

    if(!srp.verify_HAMK(new SrpBigInteger(jsonResp["H_AMK"]))) {
        return showAlert(`Unknown response (status code ${resp.status})! Please try again later.`, authAlertContainer);
    }
    let privKey = jsonResp["privKey"];
    const crypt = new OpenCrypto();
    try {
        await crypt.decryptPrivateKey(privKey, key, {name: 'RSA-OAEP'});
    } catch {
        return showAlert("Can't decrypt private key!", authAlertContainer);
    }

    if(resp.status === 200) {
        localStorage.setItem("KEY", key);
        localStorage.setItem("encPrivKey", privKey);
    }

    setCookie("token", jsonResp["token"], 86400*2);
    localStorage.setItem("token", jsonResp["token"]);
    location.href = "/dialogs";
}

async function signup() {
    sLoginInput.value = sLoginInput.value.trim();
    sPasswordInput.value = sPasswordInput.value.trim();
    sPasswordRepeatInput.value = sPasswordRepeatInput.value.trim();
    if(!validateInputs(sLoginInput, sPasswordInput, sPasswordRepeatInput)) return;

    let login = sLoginInput.value.trim();
    let password = sPasswordInput.value.trim();
    let password2 = sPasswordRepeatInput.value.trim();

    if(password !== password2) {
        showAlert("Passwords do not match!", authAlertContainer);
        return;
    }

    let srp = new SrpClient(login, password, "sha-256", 2048);
    await srp.preCalculateK();
    let salt = srp.genSalt();
    let vkey = await srp.genV();

    let key = await hashPassword(salt, password);
    const crypt = new OpenCrypto();
    let keyPair = await crypt.getRSAKeyPair(2048, "SHA-512", "RSA-OAEP", ['encrypt', 'decrypt', 'wrapKey', 'unwrapKey'], true);
    let privKey = await crypt.encryptPrivateKey(keyPair.privateKey, key);
    let pubKey = await crypt.cryptoPublicToPem(keyPair.publicKey);

    let resp = await fetch(`${window.API_ENDPOINT}/auth/register`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({"login": login, "salt": salt.toStringHex(), "verifier": vkey.toStringHex(), "privKey": privKey, "pubKey": pubKey})
    });
    let jsonResp = await resp.json();

    if(resp.status >= 400 && resp.status < 499) {
        return showAlert(jsonResp, authAlertContainer);
    }
    if(resp.status > 499) {
        return showAlert(`Unknown response (status code ${resp.status})! Please try again later.`, authAlertContainer);
    }

    setCookie("token", jsonResp["token"], 86400*2);
    localStorage.setItem("KEY", key);
    localStorage.setItem("encPrivKey", privKey);
    localStorage.setItem("token", jsonResp["token"]);
    location.href = "/dialogs";
}

if (document.readyState !== 'loading') {
    if(localStorage.getItem("token"))
        location.href = "/dialogs";
} else {
    window.addEventListener("DOMContentLoaded", async () => {
        if(localStorage.getItem("token"))
            location.href = "/dialogs";
    }, false);
}