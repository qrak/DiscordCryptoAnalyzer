// Collapsible sections functionality
class CollapsibleManager {
    constructor() {
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
                const isExpanded = content.classList.contains('expanded');

                if (isExpanded) {
                    content.classList.remove('expanded');
                    content.classList.add('collapsed');
                    icon.classList.remove('expanded');
                } else {
                    content.classList.remove('collapsed');
                    content.classList.add('expanded');
                    icon.classList.add('expanded');
                }
            });
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
                    const isExpanded = content.classList.contains('expanded');

                    if (isExpanded) {
                        content.classList.remove('expanded');
                        content.classList.add('collapsed');
                        icon.classList.remove('expanded');
                    } else {
                        content.classList.remove('collapsed');
                        content.classList.add('expanded');
                        icon.classList.add('expanded');
                    }
                });
            }
        });
    }
}

// Export for use in main script
window.CollapsibleManager = CollapsibleManager;