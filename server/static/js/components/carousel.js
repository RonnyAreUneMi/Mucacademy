/**
 * Carousel genérico — fade entre slides + autoplay + dots + flechas + swipe touch.
 *
 * Uso:
 *   initCarousel({
 *       stage:    '#heroSwiper',     // contenedor padre
 *       slide:    '.hero-slide',     // selector de cada slide (toggle .is-active)
 *       dot:      '.hero-dot',       // selector dots opcionales
 *       arrow:    '.hero-arrow',     // selector flechas opcionales (data-dir="-1|1")
 *       extras:   '.hero-mega',      // (opcional) selector de elementos paralelos a sincronizar
 *                                    //  con la misma is-active según el index
 *       interval: 6000,              // ms autoplay (0 = sin autoplay)
 *       swipe:    true,              // activa swipe touch
 *   });
 */
(function() {
    'use strict';

    function initCarousel(opts) {
        const root = typeof opts.stage === 'string'
            ? document.querySelector(opts.stage)
            : opts.stage;
        if (!root) return null;

        const slides  = Array.from(root.querySelectorAll(opts.slide));
        const dots    = opts.dot   ? Array.from(document.querySelectorAll(opts.dot))   : [];
        const arrows  = opts.arrow ? Array.from(root.querySelectorAll(opts.arrow))     : [];
        const extras  = opts.extras ? Array.from(document.querySelectorAll(opts.extras)) : [];
        const total   = slides.length;
        const interval = (typeof opts.interval === 'number') ? opts.interval : 6000;
        const swipe   = opts.swipe !== false;

        if (total <= 1) return null;

        let current = 0;
        let timer = null;

        function setActive(elements, idx) {
            elements.forEach((el, i) => el.classList.toggle('is-active', i === idx));
        }
        function go(i) {
            current = (i + total) % total;
            setActive(slides, current);
            if (dots.length)   setActive(dots, current);
            if (extras.length) setActive(extras, current);
        }
        function tick()  { go(current + 1); }
        function start() { stop(); if (interval > 0) timer = setInterval(tick, interval); }
        function stop()  { if (timer) clearInterval(timer); timer = null; }

        dots.forEach((d, i) => d.addEventListener('click', () => {
            const target = (typeof d.dataset.go !== 'undefined') ? parseInt(d.dataset.go, 10) : i;
            go(target); start();
        }));

        arrows.forEach(a => a.addEventListener('click', () => {
            const dir = parseInt(a.dataset.dir || '1', 10);
            go(current + dir); start();
        }));

        root.addEventListener('mouseenter', stop);
        root.addEventListener('mouseleave', start);

        if (swipe) {
            let startX = null;
            root.addEventListener('touchstart', e => {
                startX = e.touches[0].clientX; stop();
            }, { passive: true });
            root.addEventListener('touchend', e => {
                if (startX === null) return;
                const dx = e.changedTouches[0].clientX - startX;
                if (Math.abs(dx) > 40) go(current + (dx < 0 ? 1 : -1));
                startX = null; start();
            });
        }

        start();

        return {
            go,
            destroy: () => {
                stop();
                root.removeEventListener('mouseenter', stop);
                root.removeEventListener('mouseleave', start);
            },
        };
    }

    window.initCarousel = initCarousel;
})();
