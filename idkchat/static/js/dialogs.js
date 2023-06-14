const dialogs = document.getElementById("dialogsContainer");
const dialog_title = document.getElementById("dialogTitle");
const messages = document.getElementById("messagesContainer");
const message_input = document.getElementById("messageInput");
const dUserName = document.getElementById("adddial_userName");
const selDialogContainer = document.getElementById("selDialogContainer");
const actualDialogContainer = document.getElementById("actualDialogContainer");
const newDialogModal = document.getElementById("newDialogModal");
const sidebar = document.getElementById("sidebar");
const crypt = new OpenCrypto();

t = localStorage.getItem("token");
if(!t || !t.split(".")[1]) location.href = "/auth";
t = atob(t.split(".")[1]);
t = JSON.parse(t);
if(!t["user_id"]) location.href = "/auth";
window.USER_ID = t["user_id"];
window.PUBKEY = t["pubKey"];
delete t;

window.DIALOGS = {};
window.MESSAGES = [];
window.MESSAGES_CACHE = {};
window.CURRENT_DIALOG = 0;
window._WS = null;


async function encryptMessage(text, chatKey) {
    let buffer = new TextEncoder().encode(text);
    return await crypt.encrypt(chatKey, buffer);
}

async function decryptMessage(message, chatKey) {
    let buffer = await crypt.decrypt(chatKey, message);
    return new TextDecoder("utf-8").decode(buffer);
}


function updateDialog(dialog_id) {
    // TODO: UPDATE DIALOG
    /*let dialog_obj = DIALOGS[dialog_id];
    let dialog = document.getElementById(`dialog-id-${dialog_id}`);
    if(!dialog || !dialog_obj) return;

    let username, avatar;
    for(let childNode of dialog.childNodes) {
        if(childNode.nodeName === "SPAN") {
            username = childNode;
        }
        if(childNode.nodeName === "IMG") {
            avatar = childNode;
        }
        if(username && avatar) break;
    }
    if(!username || !avatar) return;

    username.innerText = dialog_obj["user"]["username"];
    username.style.color = dialog_obj["new_messages"] ? "#ff0000" : "";

    avatar.src = avatarUrl(dialog_obj["user"]["id"], dialog_obj["user"]["avatar"]);
    ensureImageLoaded(avatar, DEFAULT_AVATAR);*/
}

async function addDialog(dialog) {
    let dialog_id = dialog["id"];
    let user = dialog["user"];

    if(!(dialog_id in MESSAGES_CACHE)) {
        MESSAGES_CACHE[dialog_id] = {"messages": [], "message_ids": []};
    }

    if(!(dialog_id in DIALOGS)) DIALOGS[dialog_id] = dialog;
    if(DIALOGS[dialog_id]["chatKey"] === undefined) {
        let privKey = await crypt.decryptPrivateKey(localStorage.getItem("encPrivKey"), localStorage.getItem("KEY"), { name: 'RSA-OAEP' });
        dialog["chatKey"] = await crypt.decryptKey(privKey, dialog["key"], {type: 'raw', name: 'AES-GCM', length: 256, usages: ['encrypt', 'decrypt', 'wrapKey', 'unwrapKey'], isExtractable: true});
    }
    if(dialog_id in DIALOGS || document.getElementById(`dialog-id-${dialog_id}`) !== null) {
        Object.assign(DIALOGS[dialog["id"]], dialog);
        updateDialog(dialog_id);
        return;
    }

    let dialog_el = document.createElement("li");
    dialogs.appendChild(dialog_el);
    dialog_el.outerHTML = `
    <li class="nav-item w-100" id="dialog-id-${dialog_id}">
      <a href="#" class="d-flex align-items-center text-white text-decoration-none nav-link" onclick="selectDialog(${dialog_id});">
        <img src="${avatarUrl(user["id"], user["avatar"])}" alt="User avatar" width="32" height="32" class="rounded-circle me-2">
        <p class="text-truncate" title="${user["username"]}"><b>${user["username"]}</b></p>
      </a>
    </li>
    `;
}

function clearMessages() {
    messages.innerHTML = "";
}

async function addMessage(dialog_id, message) {
    let message_id = message["id"];
    if(!MESSAGES_CACHE[dialog_id]["message_ids"].includes(message_id)) {
        MESSAGES_CACHE[dialog_id]["message_ids"].push(message_id);
        MESSAGES_CACHE[dialog_id]["messages"].push(message);
    }
    if(window.CURRENT_DIALOG !== dialog_id)
        return;
    if(document.getElementById(`message-id-${message_id}`))
        return;

    let dialog = DIALOGS[dialog_id];
    message["text"] = "text" in message ? message["text"] : await decryptMessage(message["content"], dialog["chatKey"]);

    let idx = sortedIndex(MESSAGES, message_id);
    MESSAGES.splice(idx, 0, message_id);

    let message_el = document.createElement("li");
    let insertLast = idx === MESSAGES.length-1;
    let before = MESSAGES[idx+1];
    before = document.getElementById(`message-id-${before}`);
    if(insertLast || !before)
        messages.appendChild(message_el);
    else {
        messages.insertBefore(message_el, before);
    }

    let date = new Date(message["created_at"]*1000);
    message_el.outerHTML = `
    <li class="message ${message["author"] === USER_ID ? "my-message" : ""}" id="message-id-${message_id}">
      <div>
        <span class="message-time">[${padDate(date.getDate())}.${padDate(date.getMonth())}.${date.getFullYear()} ${padDate(date.getHours())}:${padDate(date.getMinutes())}]</span>
        <span class="message-text">${message["text"]}</span>
      </div>
    </li>
    `;

    if(insertLast)
        messages.scrollTo(0, messages.scrollHeight);
}

function padDate(d) {
    return ("0"+d).slice(-2)
}

async function sendMessage() {
    message_input.value = message_input.value.trim();
    if(!validateInputs(message_input)) return;
    let text = message_input.value.trim();
    if(!text)
        return;

    let dialog_id = window.CURRENT_DIALOG;
    let dialog = DIALOGS[dialog_id];
    let content = await encryptMessage(text, dialog["chatKey"])

    let resp = await fetch(`${window.API_ENDPOINT}/chat/dialogs/${dialog_id}/messages`, {
        method: "POST",
        headers: {
            "Authorization": localStorage.getItem("token"),
            "Content-Type": "application/json"
        },
        body: JSON.stringify({"content": content})
    });
    if(resp.status === 401) {
        localStorage.removeItem("token");
        location.href = "/auth";
    }

    if(resp.status >= 400 && resp.status < 405) {
        let jsonResp = await resp.json();
        alert(jsonResp.message);
        return;
    }

    message_input.value = "";
}

message_input.addEventListener("keyup", ({key}) => {
    if(key === "Enter") {
        sendMessage().then();
    }
});

async function fetchDialogs() {
    let resp = await fetch(`${window.API_ENDPOINT}/chat/dialogs`, {
        headers: {
            "Authorization": localStorage.getItem("token")
        }
    });
    if(resp.status === 401) {
        localStorage.removeItem("token");
        location.href = "/auth";
    }

    for(let dialog of await resp.json()) {
        await addDialog(dialog);
        Object.assign(DIALOGS[dialog["id"]], dialog);
    }
}

async function fetchMessages(dialog_id) {
    let resp = await fetch(`${window.API_ENDPOINT}/chat/dialogs/${dialog_id}/messages`, {
        headers: {
            "Authorization": localStorage.getItem("token")
        }
    });
    if(resp.status === 401) {
        localStorage.removeItem("token");
        location.href = "/auth";
    }

    for(let message of await resp.json()) {
        await addMessage(dialog_id, message);
    }
}

async function selectDialog(dialog_id) {
    if(!(dialog_id in DIALOGS)) return;

    let dialog_to_sel = document.getElementById(`dialog-id-${dialog_id}`);
    if(!dialog_to_sel) return;

    for(let active_el of document.getElementsByClassName("active")) {
        active_el.classList.remove("active");
    }
    dialog_to_sel.getElementsByTagName("a")[0].classList.add("active");
    dialog_title.innerText = DIALOGS[dialog_id]["user"]["username"];

    selDialogContainer.classList.add("d-none")
    selDialogContainer.classList.remove("d-flex");
    actualDialogContainer.classList.add("d-flex")
    actualDialogContainer.classList.remove("d-none");

    window.MESSAGES = [];
    clearMessages();

    window.CURRENT_DIALOG = dialog_id;
    for(let message of MESSAGES_CACHE[dialog_id]["messages"]) {
        await addMessage(dialog_id, message);
    }
    hideSidebar();
    fetchMessages(dialog_id).then();

    if(DIALOGS[dialog_id]["new_messages"]) {
        window._WS.send(JSON.stringify({
            "op": 2,
            "d": {
                "dialog_id": window.CURRENT_DIALOG,
                "message_id": -1
            }
        }));
    }
}

async function newDialog() {
    dUserName.value = dUserName.value.trim();
    if(!validateInputs(dUserName)) return;
    let username = dUserName.value.trim();
    if(!username) return;

    let resp = await fetch(`${window.API_ENDPOINT}/users/get-by-name`, {
        method: "POST",
        headers: {
            "Authorization": localStorage.getItem("token"),
            "Content-Type": "application/json"
        },
        body: JSON.stringify({"username": username})
    });
    if(resp.status === 401) {
        localStorage.removeItem("token");
        location.href = "/auth";
    }
    let jsonResp = await resp.json();
    if(resp.status >= 400 && resp.status < 405) {
        alert(jsonResp.message);
        return;
    }
    let OTHER_ID = jsonResp["id"];
    let otherPubKey = await crypt.pemPublicToCrypto(jsonResp["pubKey"], { name: 'RSA-OAEP' });

    let key = await crypt.getSharedKey();
    let myKey = await crypt.encryptKey(PUBKEY, key);
    let otherKey = await crypt.encryptKey(otherPubKey, key);

    let data = {"username": username, "keys": {}}
    data["keys"][USER_ID] = myKey;
    data["keys"][OTHER_ID] = otherKey;
    resp = await fetch(`${window.API_ENDPOINT}/chat/dialogs`, {
        method: "POST",
        headers: {
            "Authorization": localStorage.getItem("token"),
            "Content-Type": "application/json"
        },
        body: JSON.stringify(data)
    });
    if(resp.status === 401) {
        localStorage.removeItem("token");
        location.href = "/auth";
    }

    jsonResp = await resp.json();

    if(resp.status >= 400 && resp.status < 405) {
        alert(JSON.stringify(jsonResp));
        return;
    }

    await addDialog(jsonResp);
    await selectDialog(jsonResp["id"]);

    let modal = bootstrap.Modal.getInstance(newDialogModal);
    modal.hide();
    dUserName.value = "";
}

async function _ws_handle_new_message(data) {
    let dialog = data["dialog"];
    await addDialog(dialog);

    let message = data["message"];
    await addMessage(dialog["id"], message);

    if(message["author"] !== USER_ID && window.CURRENT_DIALOG === dialog["id"]) {
        window._WS.send(JSON.stringify({
            "op": 2,
            "d": {
                "dialog_id": dialog["id"],
                "message_id": message["id"]
            }
        }));
    }
}

function _ws_handle_dialog_update(data) {
    let dialog_id = data["id"];
    Object.assign(DIALOGS[dialog_id], data);
    updateDialog(dialog_id);
}

window.WS_HANDLERS = {
    1: _ws_handle_new_message,
    3: _ws_handle_dialog_update
}

function initWs() {
    let ws = window._WS = new WebSocket(window.WS_ENDPOINT);

    ws.addEventListener("open", (event) => {
        ws.send(JSON.stringify({
            "op": 0,
            "d": {
                "token": localStorage.getItem("token")
            }
        }));
    });

    ws.addEventListener("message", (event) => {
        const data = JSON.parse(event.data);
        if(data["op"] in WS_HANDLERS) {
            WS_HANDLERS[data["op"]](data["d"])
        }
    });

    ws.addEventListener("close", (event) => {
        if(event.code === 4001) {
            localStorage.removeItem("token");
            location.href = "/auth";
            return;
        }
        setTimeout(() => {
            fetchDialogs().then();
            initWs();
        }, 1000);
    });
}

async function initPubKey() {
    window.PUBKEY = await crypt.pemPublicToCrypto(window.PUBKEY, { name: 'RSA-OAEP' });
}

if (document.readyState !== 'loading') {
    initPubKey().then(() => {
        fetchDialogs().then(() => {
            initWs();
        });
    })
} else {
    window.addEventListener("DOMContentLoaded",  async () => {
        await initPubKey();
        await fetchDialogs();
        initWs();
    }, false);
}

function hideSidebar() {
    if(sidebar.classList.contains("d-flex")) {
        sidebar.classList.add("d-none");
        sidebar.classList.remove("d-flex");
    }
}

function showSidebar() {
    if(sidebar.classList.contains("d-none")) {
        sidebar.classList.add("d-flex");
        sidebar.classList.remove("d-none");
    }
}