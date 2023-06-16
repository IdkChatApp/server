const settingsAlertContainer = document.getElementById("settingsAlertContainer");
const cOldPassword = document.getElementById("changepass_oldPassword");
const cNewPassword = document.getElementById("changepass_newPassword");
const cNewPasswordRepeat = document.getElementById("changepass_newPasswordRepeat");
const crypt = new OpenCrypto();

async function changePassword(login) {
    hideAlert(settingsAlertContainer);
    cOldPassword.value = cOldPassword.value.trim();
    cNewPassword.value = cNewPassword.value.trim();
    cNewPasswordRepeat.value = cNewPasswordRepeat.value.trim();
    if(!validateInputs(cOldPassword, cNewPassword, cNewPasswordRepeat)) return;
    if(cNewPassword.value !== cNewPasswordRepeat.value)
        return showAlert("Passwords do not match!", settingsAlertContainer);
    if(cNewPassword.value === cOldPassword.value) {
        return showAlert("The new password must not be the same as the old one!", settingsAlertContainer);
    }

    let oldPassword = cOldPassword.value.trim();
    let newPassword = cNewPassword.value.trim();

    let oldSrp = new SrpClient(login, oldPassword, "sha-256", 2048);
    await oldSrp.preCalculateK();

    let resp = await fetch(`${window.API_ENDPOINT}/users/@me/password`, {
        method: "GET",
        headers: {
            "Authorization": localStorage.getItem("token"),
        }
    });
    let jsonResp = await resp.json();
    if(resp.status >= 400 && resp.status < 499) return showAlert(jsonResp, settingsAlertContainer);
    if(resp.status > 499) return showAlert(`Unknown response (status code ${resp.status})! Please try again later.`, settingsAlertContainer);
    oldSrp.setSalt(new SrpBigInteger(jsonResp["salt"]));
    oldSrp.setB(new SrpBigInteger(jsonResp["B"]));
    let A = await oldSrp.genA();
    let M = await oldSrp.processChallenge();

    let newSrp = new SrpClient(login, newPassword, "sha-256", 2048);
    await newSrp.preCalculateK();
    let salt = newSrp.genSalt();
    let vkey = await newSrp.genV();

    let key = await hashPassword(salt, newPassword);
    let newPk = await crypt.decryptPrivateKey(localStorage.getItem("encPrivKey"), localStorage.getItem("KEY"), { name: 'RSA-OAEP' });
    newPk = await crypt.encryptPrivateKey(newPk, key);

    resp = await fetch(`${window.API_ENDPOINT}/users/@me/password`, {
        method: "POST",
        headers: {
            "Authorization": localStorage.getItem("token"),
            "Content-Type": "application/json"
        },
        body: JSON.stringify({"A": A.toStringHex(), "M": M.toStringHex(), "ticket": jsonResp["ticket"],
        "new_salt": salt.toStringHex(), "new_verifier": vkey.toStringHex(), "new_privkey": newPk})
    });
    if(resp.status >= 400 && resp.status < 499) return showAlert(await resp.json(), settingsAlertContainer);
    if(resp.status > 499) return showAlert(`Unknown response (status code ${resp.status})! Please try again later.`, settingsAlertContainer);

    localStorage.setItem("KEY", key);
    localStorage.setItem("encPrivKey", newPk);

    return showAlert(`Password changed successfully!`, settingsAlertContainer, "success");
}
