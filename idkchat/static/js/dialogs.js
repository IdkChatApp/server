const dialogs = document.getElementById("dialogsContainer");
const dialog_title = document.getElementById("dialogTitle");
const messages = document.getElementById("messagesContainer");
const message_input = document.getElementById("messageInput");
const dUserName = document.getElementById("adddial_userName");
const selDialogContainer = document.getElementById("selDialogContainer");
const actualDialogContainer = document.getElementById("actualDialogContainer");
const newDialogModal = document.getElementById("newDialogModal");
const sidebar = document.getElementById("sidebar");
const content = document.getElementById("content");
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

    async update(obj) {
        this.username = obj["username"] || this.username;
        this.avatar = obj["avatar"] || this.avatar;
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
    constructor(id, key, user, unread_count) {
        this.id = id;
        this._key = key;
        this.user = user;
        this.unread_count = unread_count;
        this.associatedObj = null;
        this.key = null;
        this.messages = {};
        this._last_message = null;

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

    async addMessage(message) {
        if(!(message instanceof Message)) message = Message.new(message);
        if(message.id in this.messages) return;

        this.messages[message.id] = message;
        if(this._last_message === null || message.created_at > this._last_message.created_at) {
            this._last_message = message;
            await this.update({});
        }
    }

    async update(obj) {
        this._last_message = Message.new(obj["last_message"], this) || this._last_message;
        this.unread_count = typeof(obj["unread_count"]) === "number" ? obj["unread_count"] : this.unread_count;
        await this.user.update(obj["user"]);

        if(this.associatedObj === null) return;
        let av = this.associatedObj.getElementsByClassName("user-avatar");
        let lg = this.associatedObj.getElementsByClassName("user-login");
        let uc = this.associatedObj.getElementsByClassName("unread-count");
        let mp = this.associatedObj.getElementsByClassName("message-text-preview");

        if(av) av[0].src = avatarUrl(this.user.avatar);
        if(lg) lg[0].innerHTML = `<b>${this.user.username}</b>`;
        if(uc) {
            uc = uc[0];
            if(this.unread_count > 0 && uc.classList.contains("d-none")) uc.classList.remove("d-none");
            if(this.unread_count <= 0 && !uc.classList.contains("d-none")) uc.classList.add("d-none");

            uc.innerText = this.unread_count > 99 ? "99+" : this.unread_count.toString();
        }
        if(mp && this._last_message !== null) {
            mp = mp[0];
            mp.innerText = (this._last_message.author_id === USER_ID ? "You: " : "") + await this._last_message.text;
        }
    }

    static new(obj) {
        if(obj instanceof Dialog) return obj;
        if(!(obj["id"] in DIALOGS))
            DIALOGS[obj["id"]] = new this(obj["id"], obj["key"], User.new(obj["user"]), obj["unread_count"]);
        DIALOGS[obj["id"]]._last_message = Message.new(obj["last_message"]);
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
            if(that._text === null)
                that._text = await that.dialog.decrypt(that.content);
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
        if(!obj || ! dialog) return;
        if(obj instanceof Message) return obj;
        dialog = Dialog.new(dialog);
        if(!(obj["id"] in dialog.messages))
            dialog.messages[obj["id"]] = new this(obj["id"], obj["author"], obj["content"], obj["created_at"], dialog);
        return dialog.messages[obj["id"]];
    }
}

async function addDialog(dialog) {
    let dialog_id = dialog["id"], _dialog = dialog;
    if(!(dialog_id in DIALOGS)) DIALOGS[dialog_id] = Dialog.new(dialog);
    dialog = DIALOGS[dialog_id];
    let user = dialog.user;

    let dialog_el = document.getElementById(`dialog-id-${dialog_id}`);
    if(dialog_el === null) {
        dialog_el = document.createElement("li");
        dialogs.appendChild(dialog_el);

        let unread_badge = `
        <span class="badge rounded-pill bg-danger unread-count${dialog.unread_count > 0 ? " d-none" : ""}">
          ${dialog.unread_count > 99 ? "99+": dialog.unread_count}
        </span>
        `;

        let message_preview = `
        <p class="m-0 text-truncate message-text-preview">
          ${dialog._last_message !== null && dialog._last_message.author_id === USER_ID ? "You: " : ""}
          ${dialog._last_message !== null ? dialog._last_message.text : dialog._last_message}
        </p>
        `;

        dialog_el.outerHTML = `
        <li class="nav-item w-100" id="dialog-id-${dialog_id}">
          <a href="#" class="d-flex align-items-center text-white text-decoration-none nav-link" onclick="selectDialog(${dialog_id});">
            <div class="avatar-container">
              <img src="${avatarUrl(user.avatar)}" alt="User avatar" width="32" height="32" class="rounded-circle me-2 user-avatar">
              ${unread_badge}
            </div>
            <div class="w-100 text-truncate">
              <p class="text-truncate m-0 user-login" title="${user.username}"><b>${user.username}</b></p>
              ${message_preview}
            </div>
          </a>
        </li>
        `;
    }
    DIALOGS[dialog_id].associatedObj = dialog_el;
    await DIALOGS[dialog_id].update(_dialog);
}

function clearMessages() {
    messages.innerHTML = "";
}

function escapeHtml(str) {
    return str.replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;').replaceAll('"', '&quot;').replaceAll("'", '&#039;');
}

async function addMessage(dialog_id, message) {
    let message_id = message["id"];
    let dialog = DIALOGS[dialog_id];
    if(!(message_id in dialog.messages))
        await dialog.addMessage(Message.new(message, dialog));
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
        <span class="message-text">${escapeHtml(await message.text)}</span>
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
    messages.scrollTo(0, messages.scrollHeight);

    if(DIALOGS[dialog_id].unread_count > 0) {
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
    if(content.classList.contains("d-none")) {
        content.classList.remove("d-none");
    }
}

function showSidebar() {
    if(sidebar.classList.contains("d-none")) {
        sidebar.classList.add("d-flex");
        sidebar.classList.remove("d-none");
    }
    if(!content.classList.contains("d-none")) {
        content.classList.add("d-none");
    }
}