// Modern theme management with smooth transitions
class ThemeManager {
    constructor() {
        this.themeToggle = document.getElementById('themeToggle');
        this.transitionDuration = 300;
        this.init();
    }

    init() {
        // Apply theme immediately to avoid flash of unstyled content
        this.applyTheme(this.getTheme());

        // Set up event listeners
        if (this.themeToggle) {
            this.themeToggle.addEventListener('click', () => this.toggleTheme());

            // Add keyboard accessibility
            this.themeToggle.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    this.toggleTheme();
                }
            });
        }
    }

    // Check for saved theme preference or default to dark mode
    getTheme() {
        return localStorage.getItem('crypto-analysis-theme') || 'dark';
    }

    // Apply the current theme with smooth transition
    applyTheme(theme) {
        // Add transition class for smooth color changes
        document.documentElement.classList.add('theme-transitioning');
        document.documentElement.setAttribute('data-theme', theme);

        if (this.themeToggle) {
            const icon = theme === 'dark' ? '☀️' : '🌙';
            const text = theme === 'dark' ? 'Light Mode' : 'Dark Mode';

            this.themeToggle.innerHTML = `<span class="theme-switch-icon" aria-hidden="true">${icon}</span><span>${text}</span>`;
            this.themeToggle.setAttribute('aria-label', `Switch to ${text}`);
        }

        // Remove transition class after animation completes
        setTimeout(() => {
            document.documentElement.classList.remove('theme-transitioning');
        }, this.transitionDuration);
    }

    // Toggle between light and dark themes with animation
    toggleTheme() {
        const currentTheme = this.getTheme();
        const newTheme = currentTheme === 'light' ? 'dark' : 'light';
        localStorage.setItem('crypto-analysis-theme', newTheme);
        this.applyTheme(newTheme);

        // Add ripple effect on toggle (optional visual feedback)
        this.addRippleEffect();
    }

    // Add visual feedback on theme toggle
    addRippleEffect() {
        if (!this.themeToggle) return;

        this.themeToggle.style.transform = 'scale(0.95)';
        setTimeout(() => {
            this.themeToggle.style.transform = '';
        }, 150);
    }
}

// Export for use in main script
window.ThemeManager = ThemeManager;