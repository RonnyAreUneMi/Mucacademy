/**
 * verify_certificate.js — verifica un certificado por hash.
 *
 * Espera del template:
 *   window.VERIFY_CONFIG = { certHash: '<hash>' };
 *
 * Endpoint: GET /api/v1/public/verify/<hash>/
 *
 * IDs en template: #loading-state #state-found #state-not-found
 *                  #cert-nombre #cert-cedula(-row) #cert-curso
 *                  #cert-horas(-row) #cert-lote #cert-fecha(-row)
 *                  #cert-hash #bad-hash
 */
(function () {
    'use strict';

    const CFG = window.VERIFY_CONFIG;
    if (!CFG || !CFG.certHash) return;
    const HASH = CFG.certHash;

    function formatDate(iso) {
        if (!iso) return '';
        try {
            const d = new Date(iso);
            if (isNaN(d)) return iso;
            return d.toLocaleDateString('es-EC', { day: '2-digit', month: '2-digit', year: 'numeric' });
        } catch { return iso; }
    }

    async function verify() {
        try {
            const res = await fetch(`/api/v1/public/verify/${encodeURIComponent(HASH)}/`);
            document.getElementById('loading-state').classList.add('hidden');

            if (res.status === 404) return showNotFound();
            const data = await res.json();
            if (!data.found) return showNotFound();

            showFound(data);
        } catch (err) {
            console.error(err);
            document.getElementById('loading-state').classList.add('hidden');
            showNotFound();
        }
    }

    function showNotFound() {
        document.getElementById('state-not-found').classList.remove('hidden');
        document.getElementById('bad-hash').textContent = HASH;
    }

    function showFound(data) {
        const c = data.certificado || {};
        const lote = data.lote || {};

        document.getElementById('state-found').classList.remove('hidden');
        document.getElementById('cert-nombre').textContent = `${c.nombres || ''} ${c.apellidos || ''}`.trim();

        if (c.cedula) {
            document.getElementById('cert-cedula-row').classList.remove('hidden');
            document.getElementById('cert-cedula').textContent = c.cedula;
        }
        document.getElementById('cert-curso').textContent = c.curso || '';
        if (c.horas) {
            document.getElementById('cert-horas-row').classList.remove('hidden');
            document.getElementById('cert-horas').textContent = c.horas;
        }
        document.getElementById('cert-lote').textContent = lote.nombre || '';
        if (c.fecha_curso) {
            document.getElementById('cert-fecha-row').classList.remove('hidden');
            document.getElementById('cert-fecha').textContent = formatDate(c.fecha_curso);
        }
        document.getElementById('cert-hash').textContent = data.hash;
    }

    verify();
})();
