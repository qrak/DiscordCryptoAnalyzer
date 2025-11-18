// Modern back to top button with scroll progress
class BackToTopManager {
    constructor() {
        this.backToTopButton = document.querySelector('.back-to-top');
        this.scrollThreshold = 300;
        this.init();
    }

    init() {
        if (!this.backToTopButton) return;

        // Show/hide button based on scroll position with debouncing
        let scrollTimeout;
        window.addEventListener('scroll', () => {
            clearTimeout(scrollTimeout);
            scrollTimeout = setTimeout(() => {
                this.updateButtonVisibility();
            }, 10);
        }, { passive: true });

        // Smooth scroll to top on click
        this.backToTopButton.addEventListener('click', () => {
            this.scrollToTop();
        });

        // Add keyboard accessibility
        this.backToTopButton.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                this.scrollToTop();
            }
        });

        // Make button focusable
        this.backToTopButton.setAttribute('tabindex', '0');
        this.backToTopButton.setAttribute('aria-label', 'Back to top');
    }

    // Update button visibility based on scroll position
    updateButtonVisibility() {
        const scrollY = window.scrollY || document.documentElement.scrollTop;

        if (scrollY > this.scrollThreshold) {
            this.backToTopButton.classList.add('visible');
        } else {
            this.backToTopButton.classList.remove('visible');
        }
    }

    // Smooth scroll to top with animation
    scrollToTop() {
        // Add visual feedback
        this.backToTopButton.style.transform = 'scale(0.9)';

        window.scrollTo({
            top: 0,
            behavior: 'smooth'
        });

        // Reset button transform after animation
        setTimeout(() => {
            this.backToTopButton.style.transform = '';
        }, 200);
    }
}

// Export for use in main script
window.BackToTopManager = BackToTopManager;