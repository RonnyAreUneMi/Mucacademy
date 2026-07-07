/**
 * eventos_list.js — lista pública de eventos.
 *
 * Espera que el template haya seteado:
 *   window.EVENTOS_CONFIG = { registerUrlBase: '/sesion/0/registro/' };
 *
 * Endpoints consumidos:
 *   GET /api/v1/public/sessions/upcoming/
 *   GET /api/v1/public/sessions/past/
 *
 * IDs en el DOM (definidos en el template + partials):
 *   #loading-state · #upcoming-section · #upcoming-grid · #empty-upcoming
 *   #past-section · #past-grid · #empty-all
 *   #eventModal y todos sus #modal-* (ver _partials/_event_modal.html)
 *   #imageLightbox · #lightbox-img
 */
(function () {
    'use strict';

    const CONFIG = window.EVENTOS_CONFIG || { registerUrlBase: '/sesion/0/registro/' };

    // ── Helpers ─────────────────────────────────────────────────
    function esc(s) {
        if (s == null) return '';
        return String(s).replace(/[&<>"']/g, c => ({
            '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
        }[c]));
    }
    function formatDate(iso) {
        if (!iso) return '';
        const [y, m, d] = iso.split('-');
        return `${d}/${m}/${y}`;
    }
    function formatTime(t) { return t ? t.substring(0, 5) : ''; }

    // ── Estado de inscripción (localStorage) ────────────────────
    function getRegisteredSessionIds() {
        try {
            const raw = JSON.parse(localStorage.getItem('certifai_user') || '{}');
            return Array.isArray(raw.sessions) ? raw.sessions.map(Number) : [];
        } catch (e) { return []; }
    }
    function isUserRegistered(sesionId) {
        return getRegisteredSessionIds().includes(parseInt(sesionId));
    }

    // ── Ventana de tiempo: 1h antes hasta el fin ────────────────
    function isMeetingJoinable(fecha, horaInicio, horaFin) {
        if (!fecha || !horaInicio || !horaFin) return false;
        const start = new Date(`${fecha}T${horaInicio}`);
        const end = new Date(`${fecha}T${horaFin}`);
        if (isNaN(start) || isNaN(end)) return false;
        if (end < start) end.setDate(end.getDate() + 1);
        const now = new Date();
        const earliest = new Date(start.getTime() - 60 * 60 * 1000);
        return now >= earliest && now <= end;
    }

    // ── Badge para card header ──────────────────────────────────
    function badgeStatus(isPast, esVirtual, onGradient) {
        const bg = onGradient ? 'bg-white/20'
            : (isPast ? 'bg-gray-700/90' : (esVirtual ? 'bg-blue-500/90' : 'bg-[#F58830]/90'));
        const cls = `inline-flex items-center gap-1 px-3 py-1 rounded-full text-xs font-bold ${bg} text-white backdrop-blur-sm`;
        if (isPast) return `<span class="${cls}"><i class="fa-solid fa-flag-checkered text-[10px]"></i> Finalizado</span>`;
        if (esVirtual) return `<span class="${cls}"><i class="fa-solid fa-video text-[10px]"></i> Virtual</span>`;
        return `<span class="${cls}"><i class="fa-solid fa-building text-[10px]"></i> Presencial</span>`;
    }

    // ── Render de UNA card ──────────────────────────────────────
    function renderCard(s, isPast) {
        const esVirtual = s.modalidad === 'virtual';
        const titulo = s.title || s.day_of_week;
        const fechaFmt = formatDate(s.date);
        const horaIni = formatTime(s.start_time);
        const horaFin = formatTime(s.end_time);

        // Imagen / gradiente fallback
        let imageBlock;
        if (s.imagen_banner_url) {
            const grayCls = isPast ? 'grayscale group-hover:grayscale-0' : 'group-hover:scale-105';
            imageBlock = `
                <div class="relative w-full sm:w-56 h-48 sm:h-auto sm:min-h-[280px] flex-shrink-0 overflow-hidden bg-gray-100 dark:bg-[#0F163A]">
                    <img src="${esc(s.imagen_banner_url)}" alt="${esc(titulo)}" class="w-full h-full object-cover ${grayCls} transition-all duration-500">
                    <div class="absolute inset-0 bg-gradient-to-t from-black/40 via-transparent to-transparent"></div>
                    <div class="absolute top-3 left-3">${badgeStatus(isPast, esVirtual, false)}</div>
                </div>`;
        } else {
            const gradCls = isPast
                ? 'bg-gradient-to-br from-gray-500 to-gray-700'
                : esVirtual
                    ? 'bg-gradient-to-br from-blue-500 via-blue-600 to-blue-800'
                    : 'bg-gradient-to-br from-[#F58830] via-[#E8721C] to-[#D97520]';
            const icon = isPast ? 'fa-flag-checkered' : esVirtual ? 'fa-video' : 'fa-calendar-check';
            imageBlock = `
                <div class="relative w-full sm:w-56 h-48 sm:h-auto sm:min-h-[280px] flex-shrink-0 ${gradCls} flex items-center justify-center overflow-hidden">
                    <div class="absolute inset-0 opacity-15" style="background-image: radial-gradient(circle at 1px 1px, white 1px, transparent 0); background-size: 18px 18px;"></div>
                    <i class="fa-solid ${icon} text-white/50 text-7xl relative drop-shadow-lg"></i>
                    <div class="absolute top-3 left-3">${badgeStatus(isPast, esVirtual, true)}</div>
                </div>`;
        }

        // Ponentes inline
        const ponentes = Array.isArray(s.ponentes) ? s.ponentes : [];
        let ponentesText = '';
        if (ponentes.length === 1) {
            const p = ponentes[0];
            const pt = p.title || p.titulo;
            ponentesText = (pt ? pt + ' ' : '') + (p.name || p.nombre || '');
        } else if (ponentes.length > 1) {
            ponentesText = `${ponentes.length} ponentes`;
        }

        // Info grid
        const accentCls = isPast ? 'text-gray-400 dark:text-gray-500' : 'text-[#F58830]';
        const infoItem = (icon, label, value) => `
            <div class="flex items-start gap-2 min-w-0">
                <i class="fa-solid ${icon} ${accentCls} w-4 mt-1"></i>
                <div class="flex-1 min-w-0">
                    <p class="text-[10px] font-bold uppercase tracking-wider text-gray-400 dark:text-gray-500">${esc(label)}</p>
                    <p class="text-sm font-semibold text-gray-800 dark:text-gray-100 truncate">${esc(value)}</p>
                </div>
            </div>`;

        const ubicacionItem = esVirtual
            ? infoItem('fa-video', 'Modalidad', s.plataforma_display || 'Reunión virtual')
            : (s.lugar ? infoItem('fa-location-dot', 'Lugar', s.lugar) : '');

        const ponentesItem = ponentesText
            ? infoItem('fa-microphone-lines', ponentes.length === 1 ? 'Ponente' : 'Ponentes', ponentesText)
            : '';

        const infoGrid = `
            <div class="grid grid-cols-2 gap-x-4 gap-y-3">
                ${infoItem('fa-calendar-day', 'Fecha', s.day_of_week + ' ' + fechaFmt)}
                ${infoItem('fa-clock', 'Horario', horaIni + ' – ' + horaFin)}
                ${ubicacionItem}
                ${ponentesItem}
            </div>`;

        // Cupos
        let cuposHtml = '';
        if (!isPast) {
            if (s.capacity === 0) {
                cuposHtml = `<div class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-emerald-50 dark:bg-emerald-900/20 border border-emerald-200 dark:border-emerald-800/40 text-xs text-emerald-700 dark:text-emerald-400 font-bold"><i class="fa-solid fa-infinity"></i> Cupos ilimitados</div>`;
            } else if (!s.esta_llena) {
                const pct = Math.min(100, (s.confirmados_count / s.capacity) * 100);
                cuposHtml = `<div class="space-y-1.5">
                    <div class="flex justify-between items-center text-xs">
                        <span class="text-gray-700 dark:text-gray-300 font-bold">${s.cupos_disponibles} cupos disponibles</span>
                        <span class="text-gray-400 font-mono">${s.confirmados_count}/${s.capacity}</span>
                    </div>
                    <div class="w-full bg-gray-100 dark:bg-[#0F163A]/50 rounded-full h-2 overflow-hidden">
                        <div class="h-full bg-gradient-to-r from-[#F58830] to-[#D97520] rounded-full transition-all" style="width: ${pct}%"></div>
                    </div>
                </div>`;
            } else {
                cuposHtml = `<div class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800/40 text-xs text-red-700 dark:text-red-400 font-bold"><i class="fa-solid fa-ban"></i> Cupos agotados</div>`;
            }
        } else {
            cuposHtml = `<div class="text-xs text-gray-500 dark:text-gray-400"><i class="fa-solid fa-users mr-1"></i> ${s.confirmados_count} inscritos</div>`;
        }

        const descPreview = (s.descripcion || '').replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim();
        const descripcion = (descPreview && !isPast)
            ? `<p class="text-sm text-gray-500 dark:text-gray-400 line-clamp-2 mb-4">${esc(descPreview)}</p>`
            : '';

        // Botón principal
        const registerUrl = CONFIG.registerUrlBase.replace('/0/', '/' + s.id + '/');
        const lleno = !isPast && s.capacity > 0 && s.esta_llena;
        const canShowMeetButton = (
            esVirtual && s.enlace_virtual && !isPast &&
            isUserRegistered(s.id) && isMeetingJoinable(s.date, s.start_time, s.end_time)
        );

        let primaryAction = '';
        if (isPast) {
            primaryAction = `<button disabled class="flex-1 inline-flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-gray-100 dark:bg-gray-800 text-gray-500 dark:text-gray-400 font-bold text-sm cursor-not-allowed"><i class="fa-solid fa-flag-checkered"></i> Finalizado</button>`;
        } else if (lleno) {
            primaryAction = `<button disabled class="flex-1 inline-flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-gray-200 dark:bg-gray-700 text-gray-500 dark:text-gray-400 font-bold text-sm cursor-not-allowed"><i class="fa-solid fa-lock"></i> Sin cupos</button>`;
        } else if (canShowMeetButton) {
            primaryAction = `<a href="${esc(s.enlace_virtual)}" target="_blank" rel="noopener" onclick="event.stopPropagation()"
                class="flex-1 inline-flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-white hover:bg-gray-50 border-2 border-emerald-400 text-gray-800 font-bold text-sm transition-all shadow-sm hover:shadow-md hover:-translate-y-0.5">
                <svg class="w-5 h-5 flex-shrink-0" viewBox="0 0 87 72" aria-hidden="true">
                    <path fill="#00832d" d="M49.5 36l8.53 9.75 11.47 7.33 2-17.02-2-16.64-11.69 6.44z"/>
                    <path fill="#0066da" d="M0 51.5v15c0 3.04 2.46 5.5 5.5 5.5h15l3.1-11.32-3.1-9.68-10.09-3.1z"/>
                    <path fill="#e94235" d="M20.5 0L0 20.5l10.41 3.1 10.09-3.1 3.05-9.56z"/>
                    <path fill="#2684fc" d="M20.5 20.5H0v31h20.5z"/>
                    <path fill="#00ac47" d="M82.6 8.16L69.5 18.92v34.16l13.16 10.81C84.63 65.42 87 64 87 61.57V10.32c0-2.46-2.48-3.86-4.4-2.16zM49.5 36v15.5H20.5V72h43.5c3.04 0 5.5-2.46 5.5-5.5V53.08z"/>
                    <path fill="#ffba00" d="M64 0H20.5v20.5h29V36l20-.04V5.5C69.5 2.46 67.04 0 64 0z"/>
                </svg>
                <span>Ingresar a la reunión</span>
            </a>`;
        } else {
            primaryAction = `<a href="${esc(registerUrl)}" onclick="event.stopPropagation()"
                class="flex-1 inline-flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-[#F58830] hover:bg-[#D97520] text-white font-bold text-sm transition-all shadow-md hover:shadow-lg hover:-translate-y-0.5">
                <i class="fa-solid fa-user-plus"></i> Inscribirme
            </a>`;
        }

        const pastOpacity = isPast ? 'opacity-80 hover:opacity-100' : '';

        const dataAttrs = `
            data-sesion-id="${s.id}"
            data-titulo="${esc(titulo)}"
            data-descripcion="${esc(s.descripcion || '')}"
            data-dia-semana="${esc(s.day_of_week)}"
            data-fecha-iso="${esc(s.date)}"
            data-fecha-format="${fechaFmt}"
            data-hora-inicio="${horaIni}"
            data-hora-fin="${horaFin}"
            data-modalidad="${esc(s.modalidad)}"
            data-plataforma="${esc(s.plataforma_display || '')}"
            data-enlace-virtual="${esc(s.enlace_virtual || '')}"
            data-lugar="${esc(s.lugar || '')}"
            data-capacidad="${s.capacity}"
            data-confirmados="${s.confirmados_count}"
            data-is-past="${isPast ? 1 : 0}"
            data-ponentes='${esc(JSON.stringify(ponentes))}'
            ${s.imagen_banner_url ? `data-banner="${esc(s.imagen_banner_url)}"` : ''}`;

        return `<div role="button" tabindex="0"
            class="flex flex-col sm:flex-row bg-white dark:bg-[#162054] rounded-2xl shadow-lg border border-gray-100 dark:border-blue-900/30 overflow-hidden hover:shadow-2xl hover:-translate-y-1 transition-all duration-300 group cursor-pointer ${pastOpacity}"
            onclick="openEventModal(this)"
            onkeydown="if(event.key==='Enter'||event.key===' '){event.preventDefault();openEventModal(this);}"
            ${dataAttrs}>
            ${imageBlock}
            <div class="flex-1 flex flex-col p-5 sm:p-6 min-w-0">
                <h3 class="font-black text-xl text-gray-900 dark:text-white mb-1 line-clamp-2 group-hover:text-[#F58830] transition-colors">${esc(titulo)}</h3>
                ${descripcion}
                <div class="mb-4">${infoGrid}</div>
                <div class="mt-auto pt-3 border-t border-gray-100 dark:border-blue-900/30 space-y-3">
                    ${cuposHtml}
                    <div class="flex items-center gap-2">
                        ${primaryAction}
                        <button type="button" onclick="event.stopPropagation(); openEventModal(this.closest('[data-sesion-id]'))" class="px-4 py-2.5 rounded-xl border-2 border-gray-200 dark:border-blue-900/40 text-gray-600 dark:text-gray-300 hover:border-[#F58830] hover:text-[#F58830] font-bold text-sm transition-all" title="Ver detalles">
                            <i class="fa-solid fa-circle-info"></i>
                        </button>
                    </div>
                </div>
            </div>
        </div>`;
    }

    // ── Carga inicial ───────────────────────────────────────────
    async function loadEvents() {
        const loadingEl = document.getElementById('loading-state');
        try {
            const [upRes, pastRes] = await Promise.all([
                fetch('/api/v1/public/sessions/upcoming/'),
                fetch('/api/v1/public/sessions/past/'),
            ]);
            const upData = await upRes.json();
            const pastData = await pastRes.json();

            const upcoming = upData.results || upData;
            const past = Array.isArray(pastData) ? pastData : (pastData.results || []);

            loadingEl.classList.add('hidden');

            if (upcoming.length > 0) {
                document.getElementById('upcoming-section').classList.remove('hidden');
                document.getElementById('upcoming-grid').innerHTML = upcoming.map(s => renderCard(s, false)).join('');
            } else {
                document.getElementById('empty-upcoming').classList.remove('hidden');
            }

            if (past.length > 0) {
                document.getElementById('past-section').classList.remove('hidden');
                document.getElementById('past-grid').innerHTML = past.map(s => renderCard(s, true)).join('');
            }

            if (upcoming.length === 0 && past.length === 0) {
                document.getElementById('empty-all').classList.remove('hidden');
            }
        } catch (err) {
            console.error('Error cargando eventos:', err);
            loadingEl.innerHTML = `<p class="text-red-500">Error al cargar eventos. <a href="" class="underline">Reintentar</a></p>`;
        }
    }

    // ── Modal de detalles ───────────────────────────────────────
    window.openEventModal = function (btn) {
        const d = btn.dataset;
        const modal = document.getElementById('eventModal');

        const img = document.getElementById('modal-img');
        const imgBg = document.getElementById('modal-img-bg');
        const grad = document.getElementById('modal-gradient');
        const gradIcon = document.getElementById('modal-gradient-icon');
        if (d.banner) {
            img.src = d.banner; imgBg.src = d.banner;
            img.classList.remove('hidden'); imgBg.classList.remove('hidden');
            grad.classList.add('hidden'); grad.classList.remove('flex');
        } else {
            img.classList.add('hidden'); imgBg.classList.add('hidden');
            img.src = ''; imgBg.src = '';
            grad.classList.remove('hidden'); grad.classList.add('flex');
            const isVirtual = d.modalidad === 'virtual';
            grad.className = 'flex w-full h-full min-h-[240px] md:min-h-[450px] items-center justify-center bg-gradient-to-br ' +
                (isVirtual ? 'from-blue-500 to-blue-700' : 'from-[#F58830] to-[#D97520]');
            gradIcon.className = 'fa-solid ' + (isVirtual ? 'fa-video' : 'fa-calendar-check') + ' text-white/50 text-8xl';
        }

        const statusBadge = document.getElementById('modal-status-badge');
        statusBadge.innerHTML = d.isPast === '1'
            ? '<span class="inline-flex items-center gap-1 px-3 py-1.5 rounded-full text-xs font-bold bg-gray-800/90 text-white backdrop-blur-sm"><i class="fa-solid fa-flag-checkered"></i> Evento finalizado</span>'
            : '<span class="inline-flex items-center gap-1 px-3 py-1.5 rounded-full text-xs font-bold bg-green-500/90 text-white backdrop-blur-sm"><i class="fa-solid fa-circle-check"></i> Próximo</span>';

        const badges = [];
        if (d.modalidad === 'virtual') {
            badges.push('<span class="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-bold bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400"><i class="fa-solid fa-video"></i> Virtual</span>');
        } else {
            badges.push('<span class="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-bold bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400"><i class="fa-solid fa-building"></i> Presencial</span>');
        }
        document.getElementById('modal-badges').innerHTML = badges.join('');

        document.getElementById('modal-title').textContent = d.titulo;
        const descEl = document.getElementById('modal-description');
        const descWrap = document.getElementById('modal-description-wrap');
        if (d.descripcion) {
            descEl.innerHTML = d.descripcion;
            descWrap.classList.remove('hidden');
        } else {
            descWrap.classList.add('hidden');
        }
        document.getElementById('modal-fecha').textContent = d.diaSemana + ' ' + d.fechaFormat;
        document.getElementById('modal-horario').textContent = d.horaInicio + ' – ' + d.horaFin;

        const ubicRow = document.getElementById('modal-ubicacion-row');
        const ubicLabel = document.getElementById('modal-ubicacion-label');
        const ubicText = document.getElementById('modal-ubicacion');
        const ubicIconWrap = document.getElementById('modal-ubicacion-icon-wrap');
        const ubicIcon = document.getElementById('modal-ubicacion-icon');
        const enlace = document.getElementById('modal-enlace');

        if (d.modalidad === 'virtual') {
            ubicRow.classList.remove('hidden');
            ubicLabel.textContent = 'Modalidad virtual';
            ubicText.textContent = d.plataforma || 'Reunión virtual';
            ubicIconWrap.className = 'w-9 h-9 rounded-lg bg-blue-500/15 text-blue-500 flex items-center justify-center shrink-0';
            ubicIcon.className = 'fa-solid fa-video text-sm';
            const canJoin = d.enlaceVirtual && d.isPast !== '1' &&
                isUserRegistered(parseInt(d.sesionId)) &&
                isMeetingJoinable(d.fechaIso, d.horaInicio, d.horaFin);
            if (canJoin) {
                enlace.href = d.enlaceVirtual;
                enlace.classList.remove('hidden'); enlace.classList.add('flex');
            } else {
                enlace.classList.add('hidden'); enlace.classList.remove('flex');
            }
        } else if (d.lugar) {
            ubicRow.classList.remove('hidden');
            ubicLabel.textContent = 'Lugar';
            ubicText.textContent = d.lugar;
            ubicIconWrap.className = 'w-9 h-9 rounded-lg bg-[#F58830]/15 text-[#F58830] flex items-center justify-center shrink-0';
            ubicIcon.className = 'fa-solid fa-location-dot text-sm';
            enlace.classList.add('hidden'); enlace.classList.remove('flex');
        } else {
            ubicRow.classList.add('hidden');
        }

        // Ponentes
        const ponentesSection = document.getElementById('modal-ponentes-section');
        const ponentesLabel = document.getElementById('modal-ponentes-label');
        const ponentesList = document.getElementById('modal-ponentes-list');
        let ponentesData = [];
        try { ponentesData = JSON.parse(d.ponentes || '[]'); } catch (e) { ponentesData = []; }
        if (ponentesData.length > 0) {
            ponentesLabel.textContent = ponentesData.length === 1 ? 'Ponente' : `${ponentesData.length} ponentes`;
            ponentesList.innerHTML = ponentesData.map(p => {
                const name = (p.titulo ? p.titulo + ' ' : '') + p.nombre;
                const afi = p.afiliacion ? `<p class="text-xs text-gray-500 dark:text-gray-400">${esc(p.afiliacion)}</p>` : '';
                const bio = p.bio ? `<p class="text-xs text-gray-600 dark:text-gray-300 mt-1 leading-relaxed">${esc(p.bio)}</p>` : '';
                const initial = (p.nombre || '?').trim().charAt(0).toUpperCase();
                return `<div class="flex items-start gap-3 p-3 rounded-xl bg-gray-50 dark:bg-[#0F163A]/50 border border-gray-100 dark:border-blue-900/30">
                    <div class="w-10 h-10 rounded-full bg-gradient-to-br from-[#F58830] to-[#D97520] text-white font-black flex items-center justify-center shrink-0">${esc(initial)}</div>
                    <div class="flex-1 min-w-0">
                        <p class="font-bold text-gray-800 dark:text-white text-sm">${esc(name)}</p>
                        ${afi}${bio}
                    </div>
                </div>`;
            }).join('');
            ponentesSection.classList.remove('hidden');
        } else {
            ponentesSection.classList.add('hidden');
        }

        // Cupos
        const cap = parseInt(d.capacidad);
        const confirmados = parseInt(d.confirmados);
        const capBar = document.getElementById('modal-cap-bar');
        const capFill = document.getElementById('modal-cap-fill');
        const capText = document.getElementById('modal-cap-text');
        const cuposText = document.getElementById('modal-cupos');
        if (cap === 0) {
            cuposText.innerHTML = '<i class="fa-solid fa-infinity mr-1 text-green-500"></i> Ilimitados · ' + confirmados + ' inscritos';
            capBar.classList.add('hidden');
        } else {
            const disponibles = Math.max(0, cap - confirmados);
            cuposText.textContent = confirmados + ' / ' + cap + ' (' + disponibles + ' disponibles)';
            capBar.classList.remove('hidden');
            const pct = Math.min(100, (confirmados / cap) * 100);
            capFill.style.width = pct + '%';
            capFill.className = 'h-full rounded-full transition-all ' + (disponibles === 0 ? 'bg-red-500' : 'bg-[#F58830]');
            capText.textContent = disponibles === 0 ? 'Sin cupos disponibles' : disponibles + ' cupos disponibles';
        }

        // CTA principal
        const cta = document.getElementById('modal-cta');
        if (d.isPast === '1') {
            cta.innerHTML = '<div class="w-full bg-gray-100 dark:bg-gray-800 text-gray-500 dark:text-gray-400 font-bold py-3 rounded-xl text-center text-sm"><i class="fa-solid fa-flag-checkered mr-1"></i> Este evento ya finalizó</div>';
        } else if (cap > 0 && confirmados >= cap) {
            cta.innerHTML = '<button disabled class="w-full bg-gray-200 dark:bg-gray-700 text-gray-400 dark:text-gray-500 font-bold py-3 rounded-xl cursor-not-allowed text-sm"><i class="fa-solid fa-lock mr-1"></i> Cupos agotados</button>';
        } else {
            const url = CONFIG.registerUrlBase.replace('/0/', '/' + d.sesionId + '/');
            cta.innerHTML = '<a href="' + url + '" class="block w-full bg-[#F58830] hover:bg-[#D97520] text-white font-bold py-3.5 rounded-xl transition-all text-center text-sm"><i class="fa-solid fa-user-plus mr-1"></i> Inscribirme en este evento</a>';
        }

        modal.classList.remove('hidden');
        modal.classList.add('flex');
        document.body.style.overflow = 'hidden';
    };

    window.closeEventModal = function (event) {
        if (event && event.target.id !== 'eventModal') return;
        const m = document.getElementById('eventModal');
        m.classList.add('hidden');
        m.classList.remove('flex');
        document.body.style.overflow = '';
    };

    window.zoomModalImage = function () {
        const src = document.getElementById('modal-img').src;
        if (!src) return;
        document.getElementById('lightbox-img').src = src;
        const lb = document.getElementById('imageLightbox');
        lb.classList.remove('hidden'); lb.classList.add('flex');
    };

    window.closeImageLightbox = function (event) {
        if (event && event.target.id !== 'imageLightbox') return;
        const lb = document.getElementById('imageLightbox');
        lb.classList.add('hidden'); lb.classList.remove('flex');
        document.getElementById('lightbox-img').src = '';
    };

    // ── ESC cierra modales ──────────────────────────────────────
    document.addEventListener('keydown', function (e) {
        if (e.key !== 'Escape') return;
        if (!document.getElementById('imageLightbox').classList.contains('hidden')) {
            window.closeImageLightbox();
        } else {
            window.closeEventModal();
        }
    });

    // Auto-arranque
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', loadEvents);
    } else {
        loadEvents();
    }
})();
