/**
 * Landing page — orquesta los componentes que necesita el home.
 *
 * Depende de (cargar antes):
 *   - components/theme.js
 *   - components/carousel.js
 *   - components/search-tabs.js
 */
(function() {
    'use strict';

    function initSmoothScroll() {
        document.querySelectorAll('a[href^="#"]').forEach(a => {
            a.addEventListener('click', e => {
                const target = document.querySelector(a.getAttribute('href'));
                if (target) {
                    e.preventDefault();
                    target.scrollIntoView({ behavior: 'smooth', block: 'start' });
                }
            });
        });
    }

    function initRevealOnScroll() {
        const els = document.querySelectorAll('.reveal');
        if (!els.length || !('IntersectionObserver' in window)) return;
        const io = new IntersectionObserver(entries => {
            entries.forEach(e => {
                if (e.isIntersecting) {
                    e.target.classList.add('in');
                    io.unobserve(e.target);
                }
            });
        }, { rootMargin: '0px 0px -10% 0px', threshold: 0.05 });
        els.forEach(el => io.observe(el));
    }

    function init() {
        // Hero swiper (si existe)
        if (window.initCarousel) {
            window.initCarousel({
                stage:    '#heroSwiper',
                slide:    '.hero-slide',
                dot:      '.hero-dot',
                arrow:    '.hero-arrow',
                interval: 5500,
                swipe:    true,
            });
        }

        initSmoothScroll();
        initRevealOnScroll();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
