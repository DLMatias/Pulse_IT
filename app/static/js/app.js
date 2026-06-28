const body = document.body;

document.querySelectorAll("[data-nav-open]").forEach((button) => {
    button.addEventListener("click", () => body.classList.add("nav-open"));
});

document.querySelectorAll("[data-nav-close]").forEach((button) => {
    button.addEventListener("click", () => body.classList.remove("nav-open"));
});

document.addEventListener("keydown", (event) => {
    const activeElement = document.activeElement;
    const isTyping = ["INPUT", "TEXTAREA", "SELECT"].includes(activeElement?.tagName);

    if (event.key === "Escape") {
        body.classList.remove("nav-open");
    }

    if (!isTyping && event.key.toLowerCase() === "a") {
        window.location.href = "/assets";
    }

    if (!isTyping && event.key.toLowerCase() === "t") {
        window.location.href = "/tickets";
    }
});
