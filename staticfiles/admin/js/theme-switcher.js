(function() {
    'use strict';
    
    // Get saved theme from localStorage or default to dark
    function getTheme() {
        return localStorage.getItem('admin-theme') || 'dark';
    }
    
    // Save theme to localStorage
    function saveTheme(theme) {
        localStorage.setItem('admin-theme', theme);
    }
    
    // Apply theme to document
    function applyTheme(theme) {
        if (theme === 'light') {
            document.documentElement.setAttribute('data-theme', 'light');
        } else {
            document.documentElement.removeAttribute('data-theme');
        }
    }
    
    // Initialize theme on page load
    function initTheme() {
        const savedTheme = getTheme();
        applyTheme(savedTheme);
    }
    
    // Watch for theme changes in UserSettings form
    function watchThemeSelector() {
        // Check if we're on the UserSettings change form
        const themeSelect = document.querySelector('select#id_theme');
        if (themeSelect) {
            // Apply theme immediately when changed
            themeSelect.addEventListener('change', function() {
                const newTheme = this.value;
                saveTheme(newTheme);
                applyTheme(newTheme);
            });
            
            // Set initial value from localStorage
            const savedTheme = getTheme();
            if (themeSelect.value !== savedTheme) {
                themeSelect.value = savedTheme;
            }
        }
    }
    
    // Initialize everything when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', function() {
            initTheme();
            watchThemeSelector();
        });
    } else {
        initTheme();
        watchThemeSelector();
    }
})();