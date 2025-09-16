// Main application script - coordinates all functionality
document.addEventListener('DOMContentLoaded', function () {
    // Initialize all managers
    const themeManager = new window.ThemeManager();
    const collapsibleManager = new window.CollapsibleManager();
    const backToTopManager = new window.BackToTopManager();

    // Add any additional initialization here
    console.log('Crypto Analysis Report initialized successfully');
});