// Function to set a cookie
function setCookie(name, value, days) {
    let expires = "";
    if (days) {
        const date = new Date();
        date.setTime(date.getTime() + (days * 24 * 60 * 60 * 1000)); // Convert days to milliseconds
        expires = "; expires=" + date.toUTCString();
    }
    document.cookie = name + "=" + (value || "") + expires + "; path=/";
}

// Function to get a cookie by name
function getCookie(name) {
    const nameEQ = name + "=";
    const cookies = document.cookie.split(';');
    for (let i = 0; i < cookies.length; i++) {
        let cookie = cookies[i];
        while (cookie.charAt(0) == ' ') cookie = cookie.substring(1, cookie.length);
        if (cookie.indexOf(nameEQ) == 0) return cookie.substring(nameEQ.length, cookie.length);
    }
    return null;
}

// Function to set aria-modal attribute
function setAriaModal(modalId, state) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.setAttribute('aria-modal', state);
    }
}

// Check if "already_visited" cookie exists
if (!getCookie("already_visited")) {
    // If the cookie doesn't exist, set it with a 30-day expiration and keep modal open
    setCookie("already_visited", "true", 30);
    console.log("First visit: Cookie created, modal stays open");
} else {
    // If the cookie exists, set aria-modal to false to close modal
    setAriaModal('yourModalId', 'false');
    console.log("Cookie exists: Modal closed (aria-modal set to false)");
}