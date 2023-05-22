const avatar_img = document.getElementById("avatar-img");
const logout_btn = document.getElementById("logout-button");
const username_span = document.getElementById("username");
const avatar_remove_btn = document.getElementById("avatar-remove-button");

logout_btn.addEventListener("click", () => {
    localStorage.removeItem("token");
    location.href = "/auth.html";
});

avatar_img.addEventListener("click", () => {
    let input = document.createElement('input');
    input.type = 'file';

    input.onchange = (e) => {
        let file = e.target.files[0];
        if(!file.type.startsWith("image/"))
            return;
        if(file.size > 4 * 1024 * 1024)
            return;

        let reader = new FileReader();
        reader.readAsDataURL(file);
        reader.onload = async (ev) => {
            await uploadAvatar(reader.result);
        }
    }

    input.click();
});

avatar_remove_btn.addEventListener("click", async () => {
    await uploadAvatar(null);
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
        location.href = "/auth.html";
    }

    let profileData = await resp.json();
    avatar_img.src = profileData["avatar"] ? avatarUrl(profileData["id"], profileData["avatar"]) : DEFAULT_AVATAR;
}

async function fetchProfileData() {
    let resp = await fetch(`${window.API_ENDPOINT}/users/@me`, {
        headers: {
            "Authorization": localStorage.getItem("token")
        }
    });
    if(resp.status === 401) {
        localStorage.removeItem("token");
        location.href = "/auth.html";
    }

    let profileData = await resp.json();
    avatar_img.src = profileData["avatar"] ? avatarUrl(profileData["id"], profileData["avatar"]) : DEFAULT_AVATAR;
    username_span.innerText = profileData["username"];
}


if (document.readyState !== 'loading') {
    fetchProfileData().then();
} else {
    window.addEventListener("DOMContentLoaded", async () => {
        await fetchProfileData();
    }, false);
}