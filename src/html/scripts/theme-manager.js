// Theme management functionality
class ThemeManager {
    constructor() {
        this.themeToggle = document.getElementById('themeToggle');
        this.init();
    }

    init() {
        // Apply theme immediately to avoid flash of unstyled content
        this.applyTheme(this.getTheme());

        // Set up event listeners
        if (this.themeToggle) {
            this.themeToggle.addEventListener('click', () => this.toggleTheme());
        }
    }

    // Check for saved theme preference or default to dark mode
    getTheme() {
        return localStorage.getItem('crypto-analysis-theme') || 'dark';
    }

    // Apply the current theme
    applyTheme(theme) {
        document.documentElement.setAttribute('data-theme', theme);

        if (this.themeToggle) {
            if (theme === 'dark') {
                this.themeToggle.innerHTML = '<span class="theme-switch-icon" aria-hidden="true">☀️</span><span>Light Mode</span>';
            } else {
                this.themeToggle.innerHTML = '<span class="theme-switch-icon" aria-hidden="true">🌙</span><span>Dark Mode</span>';
            }
        }
    }

    // Toggle between light and dark themes
    toggleTheme() {
        const currentTheme = this.getTheme();
        const newTheme = currentTheme === 'light' ? 'dark' : 'light';
        localStorage.setItem('crypto-analysis-theme', newTheme);
        this.applyTheme(newTheme);
    }
}

// Export for use in main script
window.ThemeManager = ThemeManager;