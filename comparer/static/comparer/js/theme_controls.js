/**
 * Theme Controls Module
 * Handles dark/light mode toggling and persistence
 */

document.addEventListener('DOMContentLoaded', function() {
    const themeSwitch = document.getElementById('theme-switch');
    const htmlElement = document.documentElement;
    
    // Check for saved theme preference or use default
    const savedTheme = localStorage.getItem('theme') || 'light';
    
    // Apply the saved theme
    applyTheme(savedTheme);
    
    // Set the toggle switch to match the current theme
    themeSwitch.checked = savedTheme === 'dark';
    
    // Add event listener for theme toggle
    themeSwitch.addEventListener('change', function() {
        const newTheme = this.checked ? 'dark' : 'light';
        applyTheme(newTheme);
        localStorage.setItem('theme', newTheme);
    });
    
    /**
     * Apply the specified theme to the document
     * @param {string} theme - The theme to apply ('light' or 'dark')
     */
    function applyTheme(theme) {
        htmlElement.setAttribute('data-theme', theme);
        
        // Update meta theme-color for mobile browsers
        const metaThemeColor = document.querySelector('meta[name="theme-color"]');
        if (metaThemeColor) {
            metaThemeColor.setAttribute('content', theme === 'dark' ? '#1a1a1a' : '#ffffff');
        }
    }
    
    // Handle system preference changes
    const prefersDarkScheme = window.matchMedia('(prefers-color-scheme: dark)');
    
    prefersDarkScheme.addEventListener('change', function(e) {
        // Only auto-switch if user hasn't manually set a preference
        if (!localStorage.getItem('theme')) {
            const newTheme = e.matches ? 'dark' : 'light';
            applyTheme(newTheme);
            themeSwitch.checked = e.matches;
        }
    });
});
