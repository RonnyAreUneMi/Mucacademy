/**
 * search.js — búsqueda pública de certificados (resultados en grid).
 *
 * Espera del template:
 *   window.SEARCH_CONFIG = { homeUrl: '/' };
 *
 * Endpoints:
 *   GET /api/v1/public/certificates/?q=...
 *   POST /api/v1/public/certificates/{hash}/download/
 *   GET  /api/v1/public/certificates/bulk-download/?q=...
 */
(function () {
    'use strict';

    const CFG = window.SEARCH_CONFIG || { homeUrl: '/' };

    const FACULTY_COLORS = {
        FACI:     { bar: '#0071CE', bg: 'rgba(0, 113, 206, 0.12)', text: '#0071CE' },
        FACS:     { bar: '#10B981', bg: 'rgba(16, 185, 129, 0.12)', text: '#10B981' },
        FACE:     { bar: '#EC4899', bg: 'rgba(236, 72, 153, 0.12)', text: '#EC4899' },
        FACSECYD: { bar: '#8B5CF6', bg: 'rgba(139, 92, 246, 0.12)', text: '#8B5CF6' },
        POSGRADO: { bar: '#FF9100', bg: 'rgba(255, 145, 0, 0.12)', text: '#FF9100' },
    };

    const DOWNLOAD_URL_BASE = '/api/v1/public/certificates';
    const ZIP_URL_BASE = '/api/v1/public/certificates/bulk-download/';

    function esc(s) {
        if (s == null) return '';
        return String(s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
    }

    function formatDate(iso) {
        if (!iso) return '';
        try {
            const d = new Date(iso);
            if (isNaN(d)) return iso;
            return d.toLocaleDateString('es-EC', { day: '2-digit', month: 'short', year: 'numeric' });
        } catch { return iso; }
    }

    function renderCertCard(cert) {
        const fac = (cert.lote_facultad || '').toUpperCase();
        const colors = FACULTY_COLORS[fac] || { bar: '#F58830', bg: 'rgba(245, 136, 48, 0.12)', text: '#F58830' };
        const facDisplay = cert.lote_facultad_display || 'General';
        const fecha = formatDate(cert.fecha_curso || cert.created_at);
        const hashShort = (cert.hash_verificacion || '').slice(0, 6);

        return `
        <div class="bg-white dark:bg-[#162054] rounded-2xl border border-gray-200 dark:border-white/10 overflow-hidden flex flex-col transition-all hover:-translate-y-1 hover:shadow-2xl hover:border-[#F58830]">
            <div class="h-1.5 w-full" style="background: ${colors.bar}"></div>
            <div class="p-5 flex-1 flex flex-col">
                <div class="flex items-start justify-between gap-3 mb-4">
                    <span class="text-[10px] font-bold px-2.5 py-1 rounded-md uppercase tracking-wider" style="background: ${colors.bg}; color: ${colors.text}">
                        ${esc(facDisplay)}
                    </span>
                    <span class="text-[10px] text-gray-400 font-mono">#${esc(hashShort)}</span>
                </div>

                <h3 class="font-extrabold text-gray-900 dark:text-white text-base leading-snug line-clamp-2 mb-4" title="${esc(cert.lote_nombre || cert.curso)}">
                    ${esc(cert.lote_nombre || cert.curso)}
                </h3>

                <div class="space-y-2 mb-5 flex-1">
                    <div class="flex items-center text-xs text-gray-600 dark:text-gray-400">
                        <i class="fa-solid fa-user w-4 text-center text-[#F58830] mr-2"></i>
                        <span class="font-medium truncate">${esc(cert.nombres)} ${esc(cert.apellidos)}</span>
                    </div>
                    <div class="flex items-center text-xs text-gray-600 dark:text-gray-400">
                        <i class="fa-regular fa-calendar w-4 text-center text-[#F58830] mr-2"></i>
                        <span>${esc(fecha)}</span>
                    </div>
                    ${cert.horas ? `
                    <div class="flex items-center text-xs text-gray-600 dark:text-gray-400">
                        <i class="fa-regular fa-clock w-4 text-center text-[#F58830] mr-2"></i>
                        <span>${cert.horas} horas académicas</span>
                    </div>` : ''}
                </div>

                <a href="${DOWNLOAD_URL_BASE}/${esc(cert.hash_verificacion)}/download/" target="_blank"
                    class="w-full bg-[#162054] hover:bg-[#0d1740] dark:bg-[#F58830] dark:hover:bg-[#e07820] text-white text-xs font-bold py-3 px-4 rounded-xl text-center transition-colors flex items-center justify-center gap-2 uppercase tracking-wider shadow-md">
                    <i class="fa-solid fa-download"></i> Descargar PDF
                </a>
            </div>
        </div>`;
    }

    async function runSearch() {
        const params = new URLSearchParams(window.location.search);
        const query = (params.get('q') || '').trim();

        // Back link preserva query
        if (query) {
            const back = document.getElementById('back-link');
            if (back) back.href = `${CFG.homeUrl}?q=${encodeURIComponent(query)}`;
        }

        const loading = document.getElementById('loading-state');
        const header = document.getElementById('results-header');
        const grid = document.getElementById('results-grid');
        const empty = document.getElementById('empty-state');
        const err = document.getElementById('error-state');

        if (!query) {
            loading.classList.add('hidden');
            empty.classList.remove('hidden');
            document.getElementById('empty-query').textContent = '(consulta vacía)';
            return;
        }

        try {
            const res = await fetch(`/api/v1/public/certificates/?q=${encodeURIComponent(query)}`);
            const data = await res.json();
            loading.classList.add('hidden');

            const results = data.results || [];
            const total = data.count || results.length;

            if (total === 0) {
                empty.classList.remove('hidden');
                document.getElementById('empty-query').textContent = `"${query}"`;
                return;
            }

            // Header
            header.classList.remove('hidden');
            const first = results[0];
            const nombre = `${first.nombres} ${first.apellidos}`.trim();
            document.getElementById('results-title').innerHTML =
                `Hola,<br><span class="text-[#F58830]">${esc(nombre)}</span>`;
            document.getElementById('results-summary').innerHTML =
                `Encontramos <span class="inline-flex items-center justify-center min-w-[2rem] h-7 px-2 rounded-lg bg-[#F58830]/15 text-[#F58830] font-extrabold mx-1">${total}</span> certificado${total > 1 ? 's' : ''} asociado${total > 1 ? 's' : ''} a tu búsqueda.`;

            if (total > 1) {
                document.getElementById('zip-action').classList.remove('hidden');
                document.getElementById('zip-link').href = `${ZIP_URL_BASE}?q=${encodeURIComponent(query)}`;
            }

            grid.classList.remove('hidden');
            grid.innerHTML = results.map(renderCertCard).join('');
        } catch (e) {
            console.error(e);
            loading.classList.add('hidden');
            err.classList.remove('hidden');
        }
    }

    runSearch();
})();
