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
window.USERS = {};
window.MESSAGES = [];
window.CURRENT_DIALOG = 0;
window._WS = null;


class User {
    constructor(id, username, avatar, pubKey) {
        this.id = id;
        this.username = username;
        this.avatar = avatar;
        this._pubKey = pubKey;
        this.pubKey = null;
    }

    update(obj) {
        this.username = obj["username"];
        this.avatar = obj["avatar"];
    }

    async encryptKey(key) {
        if(this.pubKey === null)
            this.pubKey = await crypt.pemPublicToCrypto(this._pubKey, { name: 'RSA-OAEP' });

        return await crypt.encryptKey(this.pubKey, key);
    }

    static new(obj) {
        if(obj instanceof User) return obj;
        if(!(obj["id"] in USERS))
            USERS[obj["id"]] = new this(obj["id"], obj["username"] || obj["login"], obj["avatar"], obj["pubKey"]);
        return USERS[obj["id"]];
    }
}

class Dialog {
    constructor(id, key, user, new_messages) {
        this.id = id;
        this._key = key;
        this.user = user;
        this.new_messages = new_messages;
        this.associatedObj = null;
        this.key = null;
        this.messages = {};

        if(!(user.id in USERS)) USERS[user.id] = user;
    }

    async _decryptKey() {
        let privKey = await crypt.decryptPrivateKey(localStorage.getItem("encPrivKey"), localStorage.getItem("KEY"), { name: 'RSA-OAEP' });
        this.key = await crypt.decryptKey(privKey, this._key, {type: 'raw', name: 'AES-GCM', length: 256, usages: ['encrypt', 'decrypt', 'wrapKey', 'unwrapKey'], isExtractable: true});
    }

    async encrypt(text) {
        if(this.key === null) await this._decryptKey();
        let buffer = new TextEncoder().encode(text);
        return await crypt.encrypt(this.key, buffer);
    }

    async decrypt(message) {
        if(this.key === null) await this._decryptKey();
        let buffer = await crypt.decrypt(this.key, message);
        return new TextDecoder("utf-8").decode(buffer);
    }

    update(obj) {
        this.new_messages = obj["new_messages"];
        this.user.update(obj["user"]);
    }

    static new(obj) {
        if(obj instanceof Dialog) return obj;
        if(!(obj["id"] in DIALOGS))
            DIALOGS[obj["id"]] = new this(obj["id"], obj["key"], User.new(obj["user"]), obj["new_messages"]);
        return DIALOGS[obj["id"]];
    }
}

class Message {
    constructor(id, author_id, content, created_at, dialog) {
        this.id = id;
        this.author_id = author_id;
        this.content = content;
        this.created_at = created_at;
        this.dialog = dialog;
        this._text = null;
        this._date = null
        this._author = null;
    }

    get text() {
        let that = this;
        return (async () => {
            if(that._text === null) {
                that._text = await that.dialog.decrypt(that.content);
            }
            return that._text;
        })();
    }

    get date() {
        if(this._date === null) {
            let _padDate = (num) => ("0" + num).slice(-2);
            let date = new Date(this.created_at * 1000);
            this._date = `${_padDate(date.getDate())}.${_padDate(date.getMonth())}.${date.getFullYear()} ${_padDate(date.getHours())}:${_padDate(date.getMinutes())}`;
        }
        return this._date;
    }

    get author() {
        if(this._author === null) {
            if(!(this.author_id in USERS)) return null;
            this._author = USERS[this.author_id];
        }
        return this._author;
    }

    static new(obj, dialog) {
        if(obj instanceof Message) return obj;
        dialog = Dialog.new(dialog);
        if(!(obj["id"] in dialog.messages))
            dialog.messages[obj["id"]] = new this(obj["id"], obj["author"], obj["content"], obj["created_at"], dialog);
        return dialog.messages[obj["id"]];
    }
}

async function addDialog(dialog) {
    let dialog_id = dialog["id"];
    let user = dialog["user"];

    if(!(dialog_id in DIALOGS)) DIALOGS[dialog_id] = Dialog.new(dialog);
    DIALOGS[dialog_id].update(dialog);

    let dialog_el = document.getElementById(`dialog-id-${dialog_id}`);
    if(dialog_el === null) {
        dialog_el = document.createElement("li");
        dialogs.appendChild(dialog_el);
        dialog_el.outerHTML = `
        <li class="nav-item w-100" id="dialog-id-${dialog_id}">
          <a href="#" class="d-flex align-items-center text-white text-decoration-none nav-link" onclick="selectDialog(${dialog_id});">
            <img src="${avatarUrl(user["avatar"])}" alt="User avatar" width="32" height="32" class="rounded-circle me-2">
            <p class="text-truncate" title="${user["username"]}"><b>${user["username"]}</b></p>
          </a>
        </li>
        `;
    }
    DIALOGS[dialog_id].associatedObj = dialog_el;
}

function clearMessages() {
    messages.innerHTML = "";
}

async function addMessage(dialog_id, message) {
    let message_id = message["id"];
    let dialog = DIALOGS[dialog_id];
    if(!(message_id in dialog.messages))
        dialog.messages[message_id] = Message.new(message, dialog);
    message = dialog.messages[message_id];

    if(window.CURRENT_DIALOG !== dialog_id)
        return;
    if(document.getElementById(`message-id-${message_id}`))
        return;

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

    message_el.outerHTML = `
    <li class="message ${message.author_id === USER_ID ? "my-message" : ""}" id="message-id-${message_id}">
      <div>
        <span class="message-time">[${message.date}]</span>
        <span class="message-text">${await message.text}</span>
      </div>
    </li>
    `;

    if(insertLast)
        messages.scrollTo(0, messages.scrollHeight);
}

async function sendMessage() {
    message_input.value = message_input.value.trim();
    if(!validateInputs(message_input)) return;
    let text = message_input.value.trim();
    if(!text)
        return;

    let dialog_id = window.CURRENT_DIALOG;
    let dialog = DIALOGS[dialog_id];
    let content = await dialog.encrypt(text);

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

message_input.addEventListener("keyup", async ({key}) => {
    if(key === "Enter") {
        await sendMessage();
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
    let dialog = DIALOGS[dialog_id];

    let dialog_to_sel = document.getElementById(`dialog-id-${dialog_id}`);
    if(!dialog_to_sel) return;

    for(let active_el of document.getElementsByClassName("active")) {
        active_el.classList.remove("active");
    }
    dialog_to_sel.getElementsByTagName("a")[0].classList.add("active");
    dialog_title.innerText = DIALOGS[dialog_id].user.username;

    selDialogContainer.classList.add("d-none")
    selDialogContainer.classList.remove("d-flex");
    actualDialogContainer.classList.add("d-flex")
    actualDialogContainer.classList.remove("d-none");

    window.MESSAGES = [];
    clearMessages();

    window.CURRENT_DIALOG = dialog_id;
    for(let message_id in dialog.messages) {
        await addMessage(dialog_id, dialog.messages[message_id]);
    }
    hideSidebar();
    await fetchMessages(dialog_id);

    if(DIALOGS[dialog_id].new_messages) {
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
    let other_user = User.new(jsonResp);
    USERS[other_user.id] = other_user;

    let key = await crypt.getSharedKey();
    let myKey = await crypt.encryptKey(PUBKEY, key);
    let otherKey = await other_user.encryptKey(key);

    let data = {"username": username, "keys": {}}
    data["keys"][USER_ID] = myKey;
    data["keys"][other_user.id] = otherKey;
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
    addDialog(data).then();
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