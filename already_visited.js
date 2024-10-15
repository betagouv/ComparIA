document.getElementById("fr-modal-welcome-close").blur()

const cookieExists = document.cookie.includes('comparia_already_visited');
// Check if "already_visited" cookie exists
if (!cookieExists) {
    document.cookie = 'name=comparia_already_visited; SameSite=None; Secure;'
    console.log("First visit: Cookie created, modal stays open");
} else {
    const modal = document.getElementById("fr-modal-welcome");
    dsfr(modal).modal.conceal();
    console.log("Cookie exists: Modal closed");
}