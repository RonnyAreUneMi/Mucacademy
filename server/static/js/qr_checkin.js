/**
 * qr_checkin.js — check-in de asistencia vía QR de la sesión.
 *
 * Espera del template:
 *   window.QR_CHECKIN_CONFIG = { codigoQR: '<codigo>', csrfToken: '<token>' };
 *
 * Endpoints:
 *   GET  /api/v1/public/checkin/<codigo>/session/
 *   GET  /api/v1/public/checkin/<codigo>/search/?q=...
 *   POST /api/v1/public/checkin/<codigo>/register/
 */
(function () {
    'use strict';

    const CFG = window.QR_CHECKIN_CONFIG;
    if (!CFG) return;
    const codigoQR = CFG.codigoQR;
    const csrfToken = CFG.csrfToken;

    function esc(s) {
        return String(s || '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
    }

    // Cargar info de la sesión
    (async function loadSesion() {
        try {
            const res = await fetch(`/api/v1/public/checkin/${codigoQR}/session/`);
            if (!res.ok) throw new Error('Sesión no encontrada');
            const s = await res.json();
            document.getElementById('sesion-label-text').textContent =
                `${s.dia_semana} — ${s.hora_inicio} – ${s.hora_fin}`;
        } catch (err) {
            document.getElementById('sesion-label-text').textContent = 'Sesión no disponible';
            console.error(err);
        }
    })();

    const searchInput = document.getElementById('searchInput');
    const resultsDropdown = document.getElementById('resultsDropdown');
    const spinner = document.getElementById('spinner');
    const clearBtn = document.getElementById('clearBtn');
    let debounceTimer;

    searchInput.addEventListener('input', function () {
        const val = this.value.trim();
        clearBtn.classList.toggle('hidden', val.length === 0);
        clearTimeout(debounceTimer);

        if (val.length < 3) {
            resultsDropdown.classList.add('hidden');
            document.getElementById('state-idle').classList.remove('hidden');
            return;
        }
        document.getElementById('state-idle').classList.add('hidden');
        spinner.classList.remove('hidden');
        debounceTimer = setTimeout(() => searchPeople(val), 300);
    });

    async function searchPeople(query) {
        try {
            const res = await fetch(`/api/v1/public/checkin/${codigoQR}/search/?q=${encodeURIComponent(query)}`);
            const data = await res.json();
            spinner.classList.add('hidden');

            if (data.results.length === 0) {
                resultsDropdown.innerHTML = `
                    <div class="p-6 text-center text-gray-400 dark:text-gray-500 text-sm">
                        <i class="fa-solid fa-user-xmark text-2xl mb-2 block opacity-50"></i>
                        No se encontraron resultados
                    </div>`;
            } else {
                resultsDropdown.innerHTML = `
                    <div class="px-4 py-2.5 text-[10px] font-bold text-gray-400 dark:text-gray-500 uppercase tracking-wider border-b border-gray-100 dark:border-blue-900/30">
                        ${data.results.length} resultado${data.results.length > 1 ? 's' : ''}
                    </div>
                    ${data.results.map(p => renderResultItem(p)).join('')}`;
            }
            resultsDropdown.classList.remove('hidden');
        } catch (err) {
            spinner.classList.add('hidden');
            console.error('Search error:', err);
        }
    }

    function renderResultItem(p) {
        const fullName = `${p.nombres} ${p.apellidos}`;
        let statusBadge;
        if (p.already_registered) {
            statusBadge = '<div class="text-[11px] font-bold text-emerald-600 dark:text-emerald-400 mt-0.5"><i class="fa-solid fa-check-circle mr-1"></i> Ya registrado</div>';
        } else if (!p.is_confirmed) {
            statusBadge = '<div class="text-[11px] font-bold text-red-500 dark:text-red-400 mt-0.5"><i class="fa-solid fa-calendar-xmark mr-1"></i> Sin reserva para esta sesión</div>';
        } else {
            statusBadge = '<div class="text-[11px] font-bold text-blue-500 dark:text-blue-400 mt-0.5"><i class="fa-solid fa-calendar-check mr-1"></i> Cupo confirmado</div>';
        }

        return `
            <button type="button" onclick="registerAttendance(${p.id}, '${esc(fullName)}', ${p.already_registered}, ${p.is_confirmed})"
                class="w-full flex items-center gap-3 px-4 py-3 hover:bg-[#F58830]/10 transition-colors text-left ${!p.is_confirmed ? 'opacity-75' : ''}">
                <div class="w-11 h-11 rounded-xl flex items-center justify-center font-black text-white text-sm shrink-0
                    ${p.is_confirmed ? 'bg-[#162054]' : 'bg-gray-400'}">
                    ${esc(p.nombres.charAt(0))}${esc(p.apellidos.charAt(0))}
                </div>
                <div class="flex-1 min-w-0">
                    <p class="font-bold text-gray-800 dark:text-white text-sm truncate">${esc(fullName)}</p>
                    <p class="text-xs text-gray-400 dark:text-gray-500 truncate">
                        ${p.cedula ? `<i class="fa-solid fa-id-card mr-0.5"></i>${esc(p.cedula)} · ` : ''}
                        <i class="fa-solid fa-envelope mr-0.5"></i>${esc(p.email)}
                    </p>
                    ${statusBadge}
                </div>
                <i class="fa-solid fa-chevron-right text-gray-300 dark:text-gray-600 text-xs"></i>
            </button>`;
    }

    window.registerAttendance = async function (certId, nombre, alreadyRegistered, isConfirmed) {
        if (alreadyRegistered) {
            return showSuccess(nombre, '¡Ya habías registrado tu asistencia!',
                new Date().toLocaleTimeString('es', { hour: '2-digit', minute: '2-digit' }));
        }
        if (!isConfirmed) {
            return showError(`Lo sentimos, ${nombre}. No tienes una reserva confirmada para esta sesión.`);
        }

        resultsDropdown.classList.add('hidden');
        spinner.classList.remove('hidden');

        try {
            const res = await fetch(`/api/v1/public/checkin/${codigoQR}/register/`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken },
                body: JSON.stringify({ cert_id: certId }),
            });
            const data = await res.json();
            spinner.classList.add('hidden');

            if (data.ok) {
                showSuccess(data.nombre, data.message,
                    data.hora || new Date().toLocaleTimeString('es', { hour: '2-digit', minute: '2-digit' }));
            } else {
                showError(data.error || 'Error al registrar.');
            }
        } catch (err) {
            spinner.classList.add('hidden');
            showError('Error de conexión. Inténtalo de nuevo.');
        }
    };

    function showSuccess(nombre, message, time) {
        document.getElementById('state-idle').classList.add('hidden');
        document.getElementById('state-error').classList.add('hidden');
        resultsDropdown.classList.add('hidden');
        document.getElementById('successTitle').textContent = `¡Bienvenido/a, ${nombre}!`;
        document.getElementById('successMessage').textContent = message;
        document.getElementById('successTime').textContent = time;
        document.getElementById('state-success').classList.remove('hidden');
    }

    function showError(message) {
        document.getElementById('state-idle').classList.add('hidden');
        document.getElementById('state-success').classList.add('hidden');
        resultsDropdown.classList.add('hidden');
        document.getElementById('errorMessage').textContent = message;
        document.getElementById('state-error').classList.remove('hidden');
    }

    window.clearSearch = function () {
        searchInput.value = '';
        clearBtn.classList.add('hidden');
        resultsDropdown.classList.add('hidden');
        document.getElementById('state-idle').classList.remove('hidden');
        searchInput.focus();
    };

    window.resetSearch = function () {
        window.clearSearch();
        document.getElementById('state-success').classList.add('hidden');
        document.getElementById('state-error').classList.add('hidden');
    };
})();
