// Modern collapsible sections with smooth animations
class CollapsibleManager {
    constructor() {
        this.animationDuration = 400;
        this.init();
    }

    init() {
        this.initializeDiscordSummary();
        this.initializeMainContentSections();
    }

    // Initialize Discord summary (collapsed by default)
    initializeDiscordSummary() {
        const discordSummary = document.querySelector('.discord-summary');
        if (!discordSummary) return;

        const header = discordSummary.querySelector('.discord-summary-header');
        const content = discordSummary.querySelector('.discord-summary-content');
        const icon = discordSummary.querySelector('.collapse-icon');

        if (header && content && icon) {
            // Start collapsed
            content.classList.add('collapsed');
            icon.classList.remove('expanded');

            header.addEventListener('click', () => {
                this.toggleSection(content, icon);
            });

            // Add keyboard accessibility
            header.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    this.toggleSection(content, icon);
                }
            });

            // Make header focusable
            header.setAttribute('tabindex', '0');
            header.setAttribute('role', 'button');
            header.setAttribute('aria-expanded', 'false');
        }
    }

    // Initialize main content sections (expanded by default)
    initializeMainContentSections() {
        const collapsibleSections = document.querySelectorAll('.collapsible-section');

        collapsibleSections.forEach(section => {
            const header = section.querySelector('.collapsible-header');
            const content = section.querySelector('.collapsible-content');
            const icon = section.querySelector('.collapse-icon');

            if (header && content && icon) {
                // Start expanded for main content
                content.classList.add('expanded');
                icon.classList.add('expanded');

                header.addEventListener('click', () => {
                    this.toggleSection(content, icon, header);
                });

                // Add keyboard accessibility
                header.addEventListener('keydown', (e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                        e.preventDefault();
                        this.toggleSection(content, icon, header);
                    }
                });

                // Make header focusable
                header.setAttribute('tabindex', '0');
                header.setAttribute('role', 'button');
                header.setAttribute('aria-expanded', 'true');
            }
        });
    }

    // Toggle section with smooth animation
    toggleSection(content, icon, header = null) {
        const isExpanded = content.classList.contains('expanded');

        if (isExpanded) {
            // Collapse
            content.style.maxHeight = content.scrollHeight + 'px';
            requestAnimationFrame(() => {
                content.classList.remove('expanded');
                content.classList.add('collapsed');
                icon.classList.remove('expanded');
                if (header) header.setAttribute('aria-expanded', 'false');
            });
        } else {
            // Expand
            content.classList.remove('collapsed');
            content.classList.add('expanded');
            icon.classList.add('expanded');
            if (header) header.setAttribute('aria-expanded', 'true');

            // Set max-height for smooth transition
            content.style.maxHeight = content.scrollHeight + 'px';

            // Remove max-height after transition completes
            setTimeout(() => {
                if (content.classList.contains('expanded')) {
                    content.style.maxHeight = 'none';
                }
            }, this.animationDuration);
        }
    }
}

// Export for use in main script
window.CollapsibleManager = CollapsibleManager;