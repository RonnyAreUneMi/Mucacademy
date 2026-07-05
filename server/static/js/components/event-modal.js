/**
 * Event details modal — abre desde cualquier `<button data-ev-*="…">` con
 * `onclick="openEventModal(this)"`.
 *
 * Renderiza dinámicamente:
 *   - Título, descripción HTML, fecha, horario, plataforma/lugar
 *   - Pills de modalidad + status
 *   - Lista de ponentes (parsea JSON de data-ev-ponentes)
 *   - CTAs según permisos (Meet button si aplica, form de inscribir si aplica)
 *
 * Espera la marca HTML del modal en `_event_modal.html`.
 */
(function() {
    'use strict';

    // SVG oficial Google Meet (5 colores)
    const MEET_SVG = '<svg viewBox="0 0 87.5 72" width="18" height="15" style="display:inline-block;vertical-align:-3px;flex-shrink:0;" aria-hidden="true">' +
        '<path fill="#00832d" d="M49.5 36l8.53 9.75 11.47 7.33 2-17.02-2-16.64-11.69 6.44z"/>' +
        '<path fill="#0066da" d="M0 51.5V66c0 3.315 2.685 6 6 6h14.5l3-10.96-3-9.54-9.95-3z"/>' +
        '<path fill="#e94235" d="M20.5 0L0 20.5l10.55 3 9.95-3 2.95-9.41z"/>' +
        '<path fill="#2684fc" d="M0 20.5h20.5v31H0z"/>' +
        '<path fill="#00ac47" d="M82.6 8.68L69.5 19.42v33.66l13.16 10.79c1.97 1.54 4.85.135 4.85-2.37V11c0-2.535-2.945-3.925-4.91-2.32zM49.5 36v15.5h-29V72h43c3.315 0 6-2.685 6-6V53.08z"/>' +
        '<path fill="#ffba00" d="M63.5 0h-43v20.5h29V36l20-.04V6c0-3.315-2.685-6-6-6z"/>' +
        '</svg>';

    const STATUS_MAP = {
        asisti:    { icon: 'fa-circle-check', text: 'Asistí',    cls: 'text-emerald-600' },
        no_asisti: { icon: 'fa-circle-xmark', text: 'No asistí', cls: 'text-red-500' },
        inscrito:  { icon: 'fa-bookmark',     text: 'Inscrito',  cls: 'text-blue-500' },
    };

    function initials(name) {
        return (name || '').trim().split(/\s+/).slice(0, 2)
            .map(w => w[0] || '').join('').toUpperCase() || '?';
    }
    function escapeHtml(s) {
        return (s || '').replace(/[&<>"']/g, m =>
            ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[m])
        );
    }

    function init() {
        const modal = document.getElementById('evModal');
        if (!modal) return;

        const card     = modal.querySelector('.ev-modal-card');
        const titleEl  = document.getElementById('evModalTitle');
        const descBox  = document.getElementById('evModalDescBlock');
        const descEl   = document.getElementById('evModalDesc');
        const ponBox   = document.getElementById('evModalPonentesBlock');
        const ponList  = document.getElementById('evModalPonentes');
        const ponPlur  = document.getElementById('evModalPonentesPlural');
        const dateEl   = document.getElementById('evModalDate');
        const timeEl   = document.getElementById('evModalTime');
        const locRow   = document.getElementById('evModalLocationRow');
        const locLbl   = document.getElementById('evModalLocationLbl');
        const locVal   = document.getElementById('evModalLocation');
        const banner   = document.getElementById('evModalBanner');
        const heroFb   = document.getElementById('evModalHeroFallback');
        const statusP  = document.getElementById('evModalStatus');
        const modalP   = document.getElementById('evModalModality');
        const meetBtn  = document.getElementById('evModalMeetBtn');
        const inscForm = document.getElementById('evModalInscribirForm');

        function close() {
            modal.classList.add('hidden');
            modal.setAttribute('aria-hidden', 'true');
            document.body.style.overflow = '';
        }
        modal.querySelectorAll('[data-ev-close]').forEach(el => el.addEventListener('click', close));
        document.addEventListener('keydown', e => {
            if (e.key === 'Escape' && !modal.classList.contains('hidden')) close();
        });

        window.openEventModal = function(trigger) {
            const d = trigger.dataset;
            const isVirtual = d.evVirtual === '1';
            card.classList.toggle('is-virtual', isVirtual);

            titleEl.textContent = d.evTitle || '';

            // Descripción (CKEditor HTML del admin = trusted)
            if (d.evDesc && d.evDesc.trim()) {
                descEl.innerHTML = d.evDesc;
                descBox.classList.remove('hidden');
            } else {
                descBox.classList.add('hidden');
            }

            // Ponentes
            let ponentes = [];
            try { ponentes = JSON.parse(d.evPonentes || '[]'); } catch (e) { ponentes = []; }
            if (ponentes.length > 0) {
                ponPlur.style.display = ponentes.length === 1 ? 'none' : '';
                ponList.innerHTML = ponentes.map(p => {
                    const nombre = p.name || p.nombre || '';
                    const meta = [p.title || p.titulo, p.affiliation || p.afiliacion].filter(Boolean).join(' · ');
                    return '' +
                        '<div class="ev-modal-ponente">' +
                            '<div class="ev-modal-ponente-avatar">' + escapeHtml(initials(nombre)) + '</div>' +
                            '<div style="flex:1;min-width:0;">' +
                                '<p class="ev-modal-ponente-name">' + escapeHtml(nombre) + '</p>' +
                                (meta ? '<p class="ev-modal-ponente-meta">' + escapeHtml(meta) + '</p>' : '') +
                                (p.bio ? '<p class="ev-modal-ponente-bio">' + escapeHtml(p.bio) + '</p>' : '') +
                            '</div>' +
                        '</div>';
                }).join('');
                ponBox.classList.remove('hidden');
            } else {
                ponBox.classList.add('hidden');
            }

            // Fecha + horario
            dateEl.textContent = d.evDate || '';
            timeEl.textContent = (d.evTimeStart || '--:--') + ' – ' + (d.evTimeEnd || '--:--');

            // Lugar / plataforma
            if (isVirtual) {
                locLbl.innerHTML = '<span class="meet-key-icon">' + MEET_SVG + '</span> Plataforma';
                const platformLabel = d.evPlatform || 'Google Meet';
                if (d.evMeet) {
                    locVal.innerHTML = '<a href="' + d.evMeet + '" target="_blank" rel="noopener" style="display:inline-flex;align-items:center;gap:8px;">' +
                        MEET_SVG + '<span>' + platformLabel + '</span>' +
                        '<i class="fa-solid fa-arrow-up-right-from-square text-[10px]"></i></a>';
                } else {
                    locVal.innerHTML = '<span style="display:inline-flex;align-items:center;gap:8px;">' +
                        MEET_SVG + '<span>' + platformLabel + '</span></span>';
                }
                locRow.style.display = '';
            } else if (d.evPlace) {
                locLbl.innerHTML = '<i class="fa-solid fa-location-dot"></i> Lugar';
                locVal.textContent = d.evPlace;
                locRow.style.display = '';
            } else {
                locRow.style.display = 'none';
            }

            // Banner
            if (d.evBanner) {
                banner.src = d.evBanner;
                banner.classList.remove('hidden');
                heroFb.style.display = 'none';
            } else {
                banner.classList.add('hidden');
                banner.src = '';
                heroFb.style.display = '';
                heroFb.querySelector('i').className = isVirtual
                    ? 'fa-solid fa-video'
                    : 'fa-solid fa-calendar-check';
            }

            // Pills
            modalP.innerHTML = isVirtual
                ? '<i class="fa-solid fa-video"></i> Virtual'
                : '<i class="fa-solid fa-building"></i> Presencial';
            modalP.style.background = isVirtual
                ? 'rgba(59,130,246,0.85)'
                : 'rgba(245,136,48,0.85)';

            const status = d.evStatus;
            const s = STATUS_MAP[status];
            if (s) {
                statusP.classList.remove('hidden');
                statusP.innerHTML = '<i class="fa-solid ' + s.icon + ' text-[10px]"></i> ' + s.text;
                statusP.className = 'ev-modal-pill ev-modal-pill-status ' + s.cls;
            } else {
                statusP.classList.add('hidden');
            }

            // Botón Meet
            if (isVirtual && d.evMeet && (status === 'inscrito' || status === 'asisti')) {
                meetBtn.href = d.evMeet;
                meetBtn.classList.remove('hidden');
            } else {
                meetBtn.classList.add('hidden');
            }

            // Form de inscripción
            if (d.evCanInscribir === '1') {
                inscForm.action = d.evInscribirUrl || '';
                inscForm.classList.remove('hidden');
            } else {
                inscForm.classList.add('hidden');
            }

            modal.querySelector('.ev-modal-scroll').scrollTop = 0;
            modal.classList.remove('hidden');
            modal.setAttribute('aria-hidden', 'false');
            document.body.style.overflow = 'hidden';
        };
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
