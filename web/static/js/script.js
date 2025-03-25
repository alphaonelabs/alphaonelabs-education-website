// Toggle functions for menus
function toggleLanguageDropdown() {
  document.getElementById("language-dropdown").classList.toggle("hidden");
}

function toggleUserDropdown() {
  document.getElementById("user-dropdown").classList.toggle("hidden");
}

function toggleMobileMenu() {
  const menu = document.getElementById("mobile-menu");
  menu.classList.toggle("hidden");
  document.body.classList.toggle("overflow-hidden");
}

// Document ready handler
document.addEventListener("DOMContentLoaded", function () {
  // Close dropdowns when clicking outside
  document.addEventListener("click", function (event) {
    const languageDropdown = document.getElementById("language-dropdown");
    const userDropdown = document.getElementById("user-dropdown");
    const menu = document.getElementById("mobile-menu");

    const languageButton = event.target.closest(
      '[onclick="toggleLanguageDropdown()"]'
    );
    const userButton = event.target.closest('[onclick="toggleUserDropdown()"]');
    const menuButton = event.target.closest('[onclick="toggleMobileMenu()"]');
    const menuContent = event.target.closest(".mobile-menu-content");

    if (
      languageDropdown &&
      !languageButton &&
      !languageDropdown.contains(event.target)
    ) {
      languageDropdown.classList.add("hidden");
    }

    if (userDropdown && !userButton && !userDropdown.contains(event.target)) {
      userDropdown.classList.add("hidden");
    }

    if (
      menu &&
      !menu.classList.contains("hidden") &&
      !menuButton &&
      !menuContent
    ) {
      toggleMobileMenu();
    }
  });
});
