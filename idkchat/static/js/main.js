const exports = {};

function isLocalNetwork(hostname = window.location.hostname) {
    return (
        (['localhost', '127.0.0.1', '', '::1'].includes(hostname))
        || (hostname.startsWith('192.168.'))
        || (hostname.startsWith('10.'))
        || (hostname.endsWith('.local'))
    )
}

if(isLocalNetwork()) {
    // Local enviroment
    window.API_ENDPOINT = `http://${window.location.host}/api`;
    window.WS_ENDPOINT = `ws://${window.location.host}/ws`;
} else {
    // Production enviroment
    window.API_ENDPOINT = `https://${window.location.hostname}/api`;
    window.WS_ENDPOINT = `wss://${window.location.hostname}/ws`;
}
window.DEFAULT_AVATAR = "/static/img/no-avatar.png";

// Solution to not working DOMContentLoaded on Cloudflare when both HTML Minify and Rocker Loader are on.
// https://dev.to/hollowman6/solution-to-missing-domcontentloaded-event-when-enabling-both-html-auto-minify-and-rocket-loader-in-cloudflare-5ch8
let inCloudFlare = true;
window.addEventListener("DOMContentLoaded", function () {
    inCloudFlare = false;
});
if (document.readyState === "loading") {
    window.addEventListener("load", function () {
        if (inCloudFlare) window.dispatchEvent(new Event("DOMContentLoaded"));
    });
}

function avatarUrl(avatar) {
    if(!avatar) return DEFAULT_AVATAR;
    return avatar;
}

function sortedIndex(array, value, key) {
    if(key === undefined) key = (val) => val;
    let low = 0, high = array.length;

    while (low < high) {
        let mid = (low + high) >>> 1;
        if (key(array[mid]) < key(value)) low = mid + 1;
        else high = mid;
    }
    return low;
}

function formatErrorObj(obj) {
    let errors = "";
    if(typeof obj !== "object")
        return obj;

    if(Array.isArray(obj))
        return obj.join(", ")
    for (let errorField in obj) {
        let fieldErrors = formatErrorObj(obj[errorField]);
        errors += `<p>${errorField}: ${fieldErrors}</p>`
    }

    return errors;
}

function showAlert(errorsJson, container, alertType="danger") {
    let errors = formatErrorObj(errorsJson);

    container.innerHTML = `
    <div class="alert alert-${alertType} alert-dismissible fade show" role="alert">
      <h5 class="alert-heading">The following errors have occurred:</h5>
      ${errors}
      <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    </div>
    `;
}

function hideAlert(container) {
    container.innerHTML = "";
}

function validateInputs(...inputs) {
    let valid = true;
    for(let input of inputs) {
        if(!input.validity.valid) {
            input.reportValidity();
            valid = false;
        }
    }
    return valid;
}

function setCookie(name, value, expires_in_seconds) {
    let expires = "";
    if (expires_in_seconds) {
        let date = new Date();
        date.setTime(date.getTime() + (expires_in_seconds * 1000));
        expires = "; expires=" + date.toUTCString();
    }
    document.cookie = name + "=" + (value || "") + expires + "; path=/";
}

function getCookie(name) {
    for (let cookie of document.cookie.split(';')) {
        if(name !== cookie.split("=")[0]) continue;
        let value = cookie.split("=")[1];
        return value.replace(/^"(.*)"$/, '$1');
    }
    return null;
}

function removeCookie(name) {
    document.cookie = `${name}=; Path=/; Expires=Thu, 01 Jan 1970 00:00:01 GMT;`;
}

function logout() {
    removeCookie("token");
    localStorage.removeItem("token");
    localStorage.removeItem("KEY");
    localStorage.removeItem("encPrivKey");
    location.href = "/auth";
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
