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
    window.API_ENDPOINT = "https://127.0.0.1:8000/api/v1";
    window.WS_ENDPOINT = "wss://127.0.0.1:8000/ws";
} else {
    // Production enviroment
    window.API_ENDPOINT = "https://idkchat-api.pepega.ml/api/v1";
    window.WS_ENDPOINT = "wss://idkchat-api.pepega.ml/ws";
}
window.CDN = "https://link.storjshare.io/s/jwadfbzk4qjnfgqwp52yzhryzata/idkchat";
window.AVATAR_QUERY = "wrap=0"
window.DEFAULT_AVATAR = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNMafj/HwAGFwLkTJBHPQAAAABJRU5ErkJggg==";

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

function avatarUrl(user_id, avatar_hash) {
    let ext = avatar_hash.startsWith("a_") ? "gif" : "png";
    return `${CDN}/avatars/${user_id}/${avatar_hash}.${ext}?${window.AVATAR_QUERY}`;
}