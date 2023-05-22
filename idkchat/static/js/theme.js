function setTheme(theme_name) {
    localStorage.setItem('theme', theme_name);
    document.body.className = `theme-${theme_name}`;
}

function toggleTheme() {
    if (localStorage.getItem('theme') === 'light') {
        setTheme('dark');
    } else {
        setTheme('light');
    }
}

const _updateTheme = () => {
    if (localStorage.getItem('theme') === 'light') {
        setTheme('light');
    } else {
        setTheme('dark');
    }
};

function initTheme() {
    _updateTheme();
    let toggleBtn = document.createElement("a");
    toggleBtn.classList.add("toggle-theme-btn");
    toggleBtn.onclick = toggleTheme;

    let btn_content = document.createElement("span");
    btn_content.innerText = "T";

    toggleBtn.appendChild(btn_content);
    document.body.appendChild(toggleBtn);
}

if (document.readyState !== 'loading') {
    initTheme();
} else {
    window.addEventListener("DOMContentLoaded", () => {
        initTheme();
    }, false);
}

window.addEventListener("storage", (ev) => {
    if(ev.key === "theme")
        _updateTheme();
});