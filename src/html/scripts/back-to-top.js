// Back to top button functionality
class BackToTopManager {
    constructor() {
        this.backToTopButton = document.querySelector('.back-to-top');
        this.init();
    }

    init() {
        if (!this.backToTopButton) return;

        // Show/hide button based on scroll position
        window.addEventListener('scroll', () => {
            if (window.scrollY > 300) {
                this.backToTopButton.classList.add('visible');
            } else {
                this.backToTopButton.classList.remove('visible');
            }
        });

        // Smooth scroll to top on click
        this.backToTopButton.addEventListener('click', () => {
            window.scrollTo({
                top: 0,
                behavior: 'smooth'
            });
        });
    }
}

// Export for use in main script
window.BackToTopManager = BackToTopManager;