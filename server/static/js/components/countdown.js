/**
 * Countdown reutilizable.
 *
 * Espera en el DOM un contenedor con `data-target="<ISO datetime>"` y dentro
 * 4 elementos con `data-cd="d|h|m|s"`.
 *
 * Uso: <div id="countdown" data-target="2026-04-30T16:00:00">…</div>
 *      <script src="components/countdown.js"></script>
 *      <script>initCountdown('#countdown');</script>
 */
(function() {
    'use strict';

    function pad(n) { return String(Math.max(0, n)).padStart(2, '0'); }

    function initCountdown(selector) {
        const root = (typeof selector === 'string')
            ? document.querySelector(selector)
            : selector;
        if (!root || !root.dataset.target) return null;
        const target = new Date(root.dataset.target).getTime();
        const cells = {
            d: root.querySelector('[data-cd="d"]'),
            h: root.querySelector('[data-cd="h"]'),
            m: root.querySelector('[data-cd="m"]'),
            s: root.querySelector('[data-cd="s"]'),
        };
        function tick() {
            const diff = Math.max(0, target - Date.now());
            const d = Math.floor(diff / 86400000);
            const h = Math.floor((diff % 86400000) / 3600000);
            const m = Math.floor((diff % 3600000) / 60000);
            const s = Math.floor((diff % 60000) / 1000);
            if (cells.d) cells.d.textContent = pad(d);
            if (cells.h) cells.h.textContent = pad(h);
            if (cells.m) cells.m.textContent = pad(m);
            if (cells.s) cells.s.textContent = pad(s);
        }
        tick();
        const id = setInterval(tick, 1000);
        return { stop: () => clearInterval(id) };
    }

    window.initCountdown = initCountdown;
})();
