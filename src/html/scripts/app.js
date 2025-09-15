// Main application script - coordinates all functionality
document.addEventListener('DOMContentLoaded', function () {
    // Initialize all managers
    const themeManager = new window.ThemeManager();
    const collapsibleManager = new window.CollapsibleManager();
    const backToTopManager = new window.BackToTopManager();

    // Add any additional initialization here
    console.log('Crypto Analysis Report initialized successfully');
});

// Legacy global functions for backward compatibility
function toggleTheme() {
    const themeManager = new window.ThemeManager();
    themeManager.toggleTheme();
}

function initializeCollapsibleSections() {
    const collapsibleManager = new window.CollapsibleManager();
    // Already initialized in DOMContentLoaded, but keeping for compatibility
}