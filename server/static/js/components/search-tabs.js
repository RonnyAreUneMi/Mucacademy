/**
 * Tabs ARIA con navegación por teclado para el buscador del hero.
 * Sincroniza tabs con sus paneles `<form>` y maneja focus + atributos a11y.
 *
 * Espera:
 *   - Contenedor con id="searchBar" y .search-tab[role="tab"][data-tab]
 *   - Forms con id que coincida con el aria-controls del tab
 */
(function() {
    'use strict';

    function initSearchTabs() {
        const bar = document.getElementById('searchBar');
        if (!bar) return;
        const tabs = Array.from(bar.querySelectorAll('.search-tab'));
        if (tabs.length < 2) return;

        const formE = document.getElementById('searchEventos');
        const formC = document.getElementById('searchCerts');
        if (!formE || !formC) return;

        function activate(target, focusInput = true) {
            tabs.forEach(t => {
                const active = (t === target);
                t.classList.toggle('is-active', active);
                t.setAttribute('aria-selected', active ? 'true' : 'false');
                t.setAttribute('tabindex', active ? '0' : '-1');
            });
            const isCerts = target.dataset.tab === 'certificados';
            formE.classList.toggle('hidden', isCerts);
            formC.classList.toggle('hidden', !isCerts);
            formE.toggleAttribute('hidden', isCerts);
            formC.toggleAttribute('hidden', !isCerts);
            if (focusInput) {
                const input = (isCerts ? formC : formE).querySelector('input');
                if (input) input.focus();
            }
        }

        tabs.forEach((t, i) => {
            t.addEventListener('click', () => activate(t));
            t.addEventListener('keydown', (e) => {
                if (e.key === 'ArrowRight' || e.key === 'ArrowLeft') {
                    e.preventDefault();
                    const dir = e.key === 'ArrowRight' ? 1 : -1;
                    const next = tabs[(i + dir + tabs.length) % tabs.length];
                    activate(next); next.focus();
                } else if (e.key === 'Home') {
                    e.preventDefault(); activate(tabs[0]); tabs[0].focus();
                } else if (e.key === 'End') {
                    e.preventDefault();
                    const last = tabs[tabs.length - 1];
                    activate(last); last.focus();
                }
            });
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initSearchTabs);
    } else {
        initSearchTabs();
    }
})();
