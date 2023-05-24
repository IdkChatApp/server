const auth_title = document.getElementById("auth-form-title");
const login_input = document.getElementById("login");
const password_input = document.getElementById("password");
const password2_input = document.getElementById("password2");
const password2_div = document.getElementById("password2-div");
const btn_login = document.getElementById("btn_login");
const btn_register = document.getElementById("btn_register");

function toggleMode() {
    let login = auth_title.innerText.trim() === "Login";
    auth_title.innerText = login ? "Register" : "Login";
    password2_div.style.display = login ? "" : "none";
    btn_register.style.display = login ? "" : "none";
    btn_login.style.display = login ? "none" : "";
}

async function _processAuthResponse(resp, json, final_response=true) {
    let jsonResp = json ? json : await resp.json();

    if(resp.status > 400 && resp.status < 405) {
        alert(jsonResp.message);
        return;
    }

    if(resp.status !== 200) {
        alert("Unknown error occured! Please try again later.");
        return;
    }

    if(!final_response) return jsonResp;

    localStorage.setItem("token", jsonResp["token"]);
    location.href = "/dialogs";
    return jsonResp;
}

async function hashPassword(salt, password) {
    let h = concatUint8Arrays(salt.toUint8Array(), new TextEncoder().encode(password));
    for(let i = 0; i < 64; i++) {
        const hashBuffer = await window.crypto.subtle.digest("SHA-384", h);
        h = new Uint8Array(hashBuffer);
    }
    const hashArray = Array.from(new Uint8Array(h));
    return hashArray.map((b) => b.toString(16).padStart(2, "0")).join("");
}

async function login() {
    let login = login_input.value.trim();
    let password = password_input.value.trim();

    let srp = new SrpClient(login, password, "sha-256", 2048);
    await srp.preCalculateK();

    let resp = await fetch(`${window.API_ENDPOINT}/auth/login-start`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({"login": login})
    });
    let jsonResp = await _processAuthResponse(resp, undefined, false);
    if(!jsonResp)
        return;
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
    if(!srp.verify_HAMK(new SrpBigInteger(jsonResp["H_AMK"]))) {
        console.log(srp.H_AMK)
        alert("Unknown error occured! Please try again.??");
        return;
    }
    let privKey = jsonResp["privKey"];
    const crypt = new OpenCrypto();
    try {
        await crypt.decryptPrivateKey(privKey, key, {name: 'RSA-OAEP'});
    } catch {
        alert("Can't decrypt private key!.");
        return;
    }

    if(resp.status === 200) {
        localStorage.setItem("KEY", key);
        localStorage.setItem("encPrivKey", privKey);
    }

    await _processAuthResponse(resp, jsonResp);
}

async function register() {
    let login = login_input.value.trim();
    let password = password_input.value.trim();
    let password2 = password2_input.value.trim();

    if(password !== password2) {
        alert("Passwords do not match!");
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
    if(resp.status === 200) {
        localStorage.setItem("KEY", key);
        localStorage.setItem("encPrivKey", privKey);
    }

    await _processAuthResponse(resp);
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