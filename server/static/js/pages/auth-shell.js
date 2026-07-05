/**
 * Auth shell (login / register) — carrusel showcase con bg sincronizado
 * y mega watermark que cambian con cada slide.
 *
 * Depende de:
 *   - components/theme.js
 *   - components/carousel.js
 */
(function() {
    'use strict';

    function init() {
        if (!window.initCarousel) return;
        window.initCarousel({
            stage:    '#showcaseStage',
            slide:    '.showcase-slide',
            dot:      '.showcase-dot',
            extras:   '.showcase-bg, .showcase-mega',  // bgs y watermarks por slide
            interval: 6000,
            swipe:    false,
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
