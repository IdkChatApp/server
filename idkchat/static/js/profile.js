const avatarImage = document.getElementById("avatarImage");
const profileAlertContainer = document.getElementById("profileAlertContainer");
const navUserAvatar = document.getElementById("navUserAvatar");

function fileToB64(file) {
    return new Promise((resolve) => {
        let reader = new FileReader();
        reader.readAsDataURL(file);
        reader.onload = async (ev) => {
            resolve(reader.result);
        }
    });
}

function loadImage(url) {
    return new Promise((resolve) => {
        const image = new Image();
        image.onload = () => {
            resolve(image);
        }
        image.src = url;
    });
}

function fileInput() {
    return new Promise((resolve, reject) => {
        let input = document.createElement('input');
        input.type = 'file';

        input.onchange = (e) => {
            let file = e.target.files[0];
            if(!file.type.startsWith("image/")) {
                showAlert(`Invalid file (not image).`, profileAlertContainer);
                reject();
            }
            if(file.size > 4 * 1024 * 1024) {
                showAlert(`The file size should not exceed 4 mb.`, profileAlertContainer);
                reject();
            }
            resolve(file);
        }

        input.click();
    });
}

function setUserAvatar(avatar) {
    avatarImage.src = avatar;
    navUserAvatar.src = avatar;
}

avatarImage.addEventListener("click", async () => {
    let file = await fileInput();
    let b64 = await fileToB64(file);
    let image = await loadImage(b64);
    if(image.width > 1024 || image.height > 1024) {
        return showAlert(`The file resolution should not exceed 1024x1024 pixels.`, profileAlertContainer);
    }

    await uploadAvatar(b64);
});

async function uploadAvatar(avatar_b64) {
    if(!avatar_b64 && avatar_b64 !== null) return;
    let resp = await fetch(`${window.API_ENDPOINT}/users/@me`, {
        method: "PATCH",
        headers: {
            "Authorization": localStorage.getItem("token"),
            "Content-Type": "application/json"
        },
        body: JSON.stringify({"avatar": avatar_b64})
    });
    if(resp.status === 401) {
        localStorage.removeItem("token");
        location.href = "/auth";
    }
    if(resp.status >= 400 && resp.status < 499) {
        let jsonResp = await resp.json();
        return showAlert(jsonResp, profileAlertContainer);
    }
    if(resp.status > 499) {
        return showAlert(`Unknown response (status code ${resp.status})! Please try again later.`, profileAlertContainer);
    }

    let profileData = await resp.json();
    setUserAvatar(avatarUrl(profileData["avatar"]));
}

async function fetchProfileData() {
    let resp = await fetch(`${window.API_ENDPOINT}/users/@me`, {
        headers: {
            "Authorization": localStorage.getItem("token")
        }
    });
    if(resp.status === 401) {
        localStorage.removeItem("token");
        location.href = "/auth";
    }
    if(resp.status >= 400 && resp.status < 499) {
        let jsonResp = await resp.json();
        return showAlert(jsonResp, profileAlertContainer);
    }
    if(resp.status > 499) {
        return showAlert(`Unknown response (status code ${resp.status})! Please try again later.`, profileAlertContainer);
    }

    let profileData = await resp.json();
    setUserAvatar(avatarUrl(profileData["avatar"]));
}


if (document.readyState !== 'loading') {
    fetchProfileData().then();
} else {
    window.addEventListener("DOMContentLoaded", async () => {
        await fetchProfileData();
    }, false);
}