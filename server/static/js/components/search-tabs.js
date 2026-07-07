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

    // ── Autocomplete de certificados (dropdown de coincidencias) ──────────
    function initCertAutocomplete() {
        const input = document.getElementById('qCerts');
        const box = document.getElementById('certSuggest');
        const form = document.getElementById('searchCerts');
        if (!input || !box || !form) return;

        let timer = null, items = [], active = -1;

        function esc(s) {
            const d = document.createElement('div');
            d.textContent = s == null ? '' : String(s);
            return d.innerHTML;
        }
        // Usamos style.display (no clases) para evitar conflictos con utilidades CSS.
        function hide() { box.style.display = 'none'; box.innerHTML = ''; active = -1; }
        function isOpen() { return box.style.display === 'block'; }
        function render(names) {
            items = names;
            if (!names.length) { hide(); return; }
            box.innerHTML = names.map((n, i) =>
                `<button type="button" role="option" data-i="${i}" class="cert-suggest-item">
                    <i class="fa-solid fa-user-graduate" aria-hidden="true"></i>
                    <span class="truncate">${esc(n)}</span>
                 </button>`).join('');
            box.classList.remove('hidden');
            box.style.display = 'block';
        }
        function choose(i) {
            if (i < 0 || i >= items.length) return;
            input.value = items[i];
            hide();
            form.submit();
        }

        // Privacidad: si es cédula (solo dígitos) se busca SOLO con los 10 dígitos
        // completos (evita filtrar info por coincidencias parciales de cédula).
        // Por nombre, basta con 2+ caracteres.
        function queryReady(q) {
            if (/^\d+$/.test(q)) return q.length === 10;
            return q.replace(/\s+/g, '').length >= 2;
        }

        async function fetchSuggest(q) {
            try {
                const r = await fetch(`/api/v1/public/certificates/autocomplete/?q=${encodeURIComponent(q)}`);
                const d = await r.json();
                render((d.results || []).map(x => x.name).filter(Boolean).slice(0, 8));
            } catch { hide(); }
        }

        input.addEventListener('input', () => {
            const q = input.value.trim();
            clearTimeout(timer);
            if (!queryReady(q)) { hide(); return; }
            timer = setTimeout(() => fetchSuggest(q), 160);
        });
        box.addEventListener('mousedown', (e) => {
            const btn = e.target.closest('[data-i]');
            if (btn) { e.preventDefault(); choose(+btn.dataset.i); }
        });
        input.addEventListener('keydown', (e) => {
            if (!isOpen()) return;
            const opts = Array.from(box.querySelectorAll('[data-i]'));
            if (e.key === 'ArrowDown') { e.preventDefault(); active = Math.min(active + 1, opts.length - 1); }
            else if (e.key === 'ArrowUp') { e.preventDefault(); active = Math.max(active - 1, 0); }
            else if (e.key === 'Enter' && active >= 0) { e.preventDefault(); choose(active); return; }
            else if (e.key === 'Escape') { hide(); return; }
            else return;
            opts.forEach((o, i) => o.classList.toggle('is-active', i === active));
            if (opts[active]) opts[active].scrollIntoView({ block: 'nearest' });
        });
        document.addEventListener('click', (e) => { if (!form.contains(e.target)) hide(); });
    }

    function init() { initSearchTabs(); initCertAutocomplete(); }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
