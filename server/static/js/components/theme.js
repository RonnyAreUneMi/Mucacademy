/**
 * Theme toggle reutilizable.
 *
 * Espera en el DOM:
 *   - Un botón con onclick="toggleTheme()" (o evento click manual)
 *   - Un <i id="themeIcon"> (o "theme-icon") con clase `fa-moon` ó `fa-sun`
 *
 * Persiste la preferencia en localStorage.theme = 'light' | 'dark'.
 * Tailwind config usa darkMode: 'class', así que mira la clase del <html>.
 *
 * No sobrescribe `className` completo — sólo intercambia fa-moon ↔ fa-sun
 * para preservar tamaños/colores Tailwind del template.
 */
(function() {
    'use strict';

    function getIcon() {
        return document.getElementById('themeIcon') || document.getElementById('theme-icon');
    }

    function applyIcon() {
        const icon = getIcon();
        if (!icon) return;
        const isDark = document.documentElement.classList.contains('dark');
        if (isDark) {
            icon.classList.add('fa-moon');
            icon.classList.remove('fa-sun');
        } else {
            icon.classList.add('fa-sun');
            icon.classList.remove('fa-moon');
        }
    }

    window.toggleTheme = function() {
        const root = document.documentElement;
        if (root.classList.contains('dark')) {
            root.classList.remove('dark');
            root.classList.add('light');
            localStorage.theme = 'light';
        } else {
            root.classList.remove('light');
            root.classList.add('dark');
            localStorage.theme = 'dark';
        }
        applyIcon();
    };

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', applyIcon);
    } else {
        applyIcon();
    }
})();
