/**
 * Dashboard de cuenta — countdown del próximo evento + scroll automático
 * al día resaltado del calendario cuando viene de un correo `?day=YYYY-MM-DD`.
 *
 * Depende de:
 *   - components/countdown.js
 *   - components/event-modal.js (ya cargado por _base.html)
 */
(function() {
    'use strict';

    function initScrollToHighlight() {
        const highlighted = document.querySelector('.cal-day.is-highlight');
        if (!highlighted) return;
        setTimeout(() => {
            highlighted.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }, 300);
    }

    function init() {
        if (window.initCountdown) {
            window.initCountdown('#countdown');
        }
        initScrollToHighlight();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
