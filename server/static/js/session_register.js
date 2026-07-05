/**
 * session_register.js — flujo de inscripción a evento (3 pasos: search → form/confirm → success).
 *
 * Espera del template:
 *   window.REGISTER_CONFIG = { sessionId: <int>, csrfToken: '<token>' };
 *
 * Endpoints:
 *   GET  /api/v1/public/sessions/{id}/search-participant/?q=...
 *   POST /api/v1/public/sessions/{id}/confirm-participant/
 *   POST /api/v1/public/sessions/{id}/register-participant/
 *
 * Steps (IDs en el template):
 *   #step-search       — buscar por cédula/email
 *   #step-new-form     — registro nuevo
 *   #step-success      — confirmación
 */
(function () {
    'use strict';

    const CFG = window.REGISTER_CONFIG;
    if (!CFG) { console.error('REGISTER_CONFIG no definida'); return; }
    const SESSION_ID = CFG.sessionId;
    const CSRF = CFG.csrfToken;

    let searchTimeout = null;

    // ── Step 1: búsqueda ────────────────────────────────────────
    const searchInput = document.getElementById('search-input');
    if (searchInput) {
        searchInput.addEventListener('input', function () {
            clearTimeout(searchTimeout);
            const q = this.value.trim();
            document.getElementById('result-found').classList.add('hidden');
            document.getElementById('result-not-found').classList.add('hidden');
            if (q.length < 3) return;

            document.getElementById('search-spinner').classList.remove('hidden');
            searchTimeout = setTimeout(() => doSearch(q), 400);
        });
    }

    function doSearch(q) {
        fetch(`/api/v1/public/sessions/${SESSION_ID}/search-participant/?q=${encodeURIComponent(q)}`)
            .then(r => r.json())
            .then(data => {
                document.getElementById('search-spinner').classList.add('hidden');
                const list = document.getElementById('search-results-list');
                list.innerHTML = '';
                list.classList.add('hidden');

                if (!data.found) {
                    document.getElementById('result-not-found').classList.remove('hidden');
                    return;
                }
                if (data.count > 1) {
                    list.classList.remove('hidden');
                    data.results.forEach(p => list.appendChild(renderSearchResult(p)));
                } else {
                    selectParticipant(data.participante, data.ya_confirmado);
                }
            })
            .catch(() => document.getElementById('search-spinner').classList.add('hidden'));
    }

    function renderSearchResult(p) {
        const item = document.createElement('div');
        item.className = 'flex items-center gap-3 p-3 bg-gray-50 dark:bg-[#0F163A]/30 hover:bg-[#F58830]/10 border border-gray-100 dark:border-blue-900/20 rounded-xl cursor-pointer transition-all group';
        item.innerHTML = `
            <div class="w-10 h-10 rounded-full bg-[#162054] text-white flex items-center justify-center font-bold text-xs shrink-0 group-hover:bg-[#F58830]">
                ${(p.nombres || '').charAt(0)}${(p.apellidos || '').charAt(0)}
            </div>
            <div class="flex-1 min-w-0">
                <p class="font-bold text-sm text-gray-800 dark:text-white truncate">${p.nombres} ${p.apellidos}</p>
                <p class="text-[0.7rem] text-gray-400 truncate">
                    ${p.cedula ? '<i class="fa-solid fa-id-card mr-1"></i>' + p.cedula : ''}
                    ${p.email ? ' · <i class="fa-solid fa-envelope mr-1"></i>' + p.email : ''}
                </p>
            </div>
            <i class="fa-solid fa-chevron-right text-gray-300 group-hover:text-[#F58830] text-xs"></i>
        `;
        item.onclick = () => selectParticipant(p);
        return item;
    }

    function selectParticipant(p, yaConfirmado = null) {
        document.getElementById('search-results-list').classList.add('hidden');
        document.getElementById('result-found').classList.remove('hidden');
        document.getElementById('result-not-found').classList.add('hidden');

        document.getElementById('found-nombre').textContent = `${p.nombres} ${p.apellidos}`;
        document.getElementById('found-cedula-p').textContent = p.cedula || '—';
        document.getElementById('found-email-p').textContent = p.email || '—';
        document.getElementById('found-cedula-input').value = p.cedula || '';
        document.getElementById('found-email-input').value = p.email || '';
        document.getElementById('found-celular').value = p.celular || '';
        document.getElementById('found-participante-id').value = p.id;
        document.getElementById('found-cursos').textContent = p.cursos && p.cursos.length > 0 ? p.cursos.join(', ') : 'Ninguno aún';

        const missing = p.missing_info || [];

        toggleField('found-cedula-p', 'found-cedula-input', !p.cedula);
        toggleField('found-email-p', 'found-email-input', !p.email);

        if (missing.includes('nombres') || missing.includes('apellidos')) {
            document.getElementById('found-names-extra').classList.remove('hidden');
            document.getElementById('found-nombres-input').value = p.nombres || '';
            document.getElementById('found-apellidos-input').value = p.apellidos || '';
            document.getElementById('found-nombre').classList.add('hidden');
        } else {
            document.getElementById('found-names-extra').classList.add('hidden');
            document.getElementById('found-nombre').classList.remove('hidden');
        }

        const hasMissing = missing.length > 0;
        document.getElementById('found-icon-success').classList.toggle('hidden', hasMissing);
        document.getElementById('found-icon-warning').classList.toggle('hidden', !hasMissing);
        document.getElementById('found-msg-success').classList.toggle('hidden', hasMissing);
        document.getElementById('found-msg-missing').classList.toggle('hidden', !hasMissing);

        const confirmed = yaConfirmado !== null ? yaConfirmado : p.ya_confirmado;
        document.getElementById('found-ya-confirmado').classList.toggle('hidden', !confirmed);
        document.getElementById('btn-confirm-existing').classList.toggle('hidden', confirmed);
    }

    // helper: toggle entre <p> de solo lectura e <input> editable
    function toggleField(textId, inputId, missing) {
        document.getElementById(textId).classList.toggle('hidden', missing);
        document.getElementById(inputId).classList.toggle('hidden', !missing);
    }

    window.confirmExisting = function () {
        const btn = document.getElementById('btn-confirm-existing');
        const participanteId = document.getElementById('found-participante-id').value;
        const celular = document.getElementById('found-celular').value.trim();
        const cedula = document.getElementById('found-cedula-input').value.trim();
        const email = document.getElementById('found-email-input').value.trim();
        const nombres = document.getElementById('found-nombres-input').value.trim();
        const apellidos = document.getElementById('found-apellidos-input').value.trim();

        // Validaciones contextuales
        const cedulaInputVisible = !document.getElementById('found-cedula-input').classList.contains('hidden');
        const emailInputVisible = !document.getElementById('found-email-input').classList.contains('hidden');
        const namesVisible = !document.getElementById('found-names-extra').classList.contains('hidden');

        if (cedulaInputVisible && !cedula) return showToast('Por favor ingresa tu cédula.', 'warning');
        if (emailInputVisible && !email)   return showToast('Por favor ingresa tu email.', 'warning');
        if (namesVisible && (!nombres || !apellidos)) return showToast('Por favor ingresa tus nombres y apellidos.', 'warning');

        btn.disabled = true;
        btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin mr-1"></i> Registrando...';

        const fd = new FormData();
        fd.append('participante_id', participanteId);
        fd.append('celular', celular);
        fd.append('cedula', cedula);
        fd.append('email', email);
        fd.append('nombres', nombres);
        fd.append('apellidos', apellidos);

        fetch(`/api/v1/public/sessions/${SESSION_ID}/confirm-participant/`, {
            method: 'POST',
            headers: { 'X-CSRFToken': CSRF },
            body: fd,
        })
            .then(r => r.json())
            .then(data => {
                if (data.ok) {
                    if (data.already) {
                        Swal.fire({ icon: 'info', title: 'Ya registrado', text: data.message, confirmButtonColor: '#F58830' });
                        resetConfirmBtn(btn);
                    } else {
                        showSuccess(data);
                    }
                } else {
                    Swal.fire({ icon: 'error', title: 'Error', text: data.error, confirmButtonColor: '#F58830' });
                    resetConfirmBtn(btn);
                }
            })
            .catch(() => resetConfirmBtn(btn));
    };

    function resetConfirmBtn(btn) {
        btn.disabled = false;
        btn.innerHTML = '<i class="fa-solid fa-check-double mr-1"></i> Usar estos datos y registrarme';
    }

    // ── Step 2: nuevo formulario ────────────────────────────────
    window.showNewForm = function () {
        document.getElementById('step-search').classList.add('hidden');
        document.getElementById('step-new-form').classList.remove('hidden');

        // Pre-llenar con lo que tipeó en el search
        const searchVal = document.getElementById('search-input').value.trim();
        if (searchVal.includes('@')) {
            document.getElementById('new-email').value = searchVal;
        } else if (/^\d+$/.test(searchVal)) {
            document.getElementById('new-cedula').value = searchVal;
        }
    };

    window.showSearch = function () {
        document.getElementById('step-new-form').classList.add('hidden');
        document.getElementById('step-search').classList.remove('hidden');
    };

    const newForm = document.getElementById('new-form');
    if (newForm) {
        newForm.addEventListener('submit', function (e) {
            e.preventDefault();
            const errorDiv = document.getElementById('new-form-error');
            errorDiv.classList.add('hidden');

            const cedula = document.getElementById('new-cedula').value.trim();
            const email = document.getElementById('new-email').value.trim();
            const nombres = document.getElementById('new-nombres').value.trim();
            const apellidos = document.getElementById('new-apellidos').value.trim();
            const celular = document.getElementById('new-celular').value.trim();

            if (!nombres || !apellidos) return showFormError(errorDiv, 'Nombres y apellidos son obligatorios.');
            if (!cedula && !email) return showFormError(errorDiv, 'Debe proporcionar al menos cédula o correo electrónico.');

            const btn = this.querySelector('button[type=submit]');
            btn.disabled = true;
            btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin mr-1"></i> Registrando...';

            const fd = new FormData();
            fd.append('cedula', cedula);
            fd.append('nombres', nombres);
            fd.append('apellidos', apellidos);
            fd.append('email', email);
            fd.append('celular', celular);

            fetch(`/api/v1/public/sessions/${SESSION_ID}/register-participant/`, {
                method: 'POST',
                headers: { 'X-CSRFToken': CSRF },
                body: fd,
            })
                .then(r => r.json())
                .then(data => {
                    if (data.ok) {
                        if (data.already) {
                            Swal.fire({ icon: 'info', title: 'Ya registrado', text: data.message, confirmButtonColor: '#F58830' });
                            resetSubmitBtn(btn);
                        } else {
                            showSuccess(data);
                        }
                    } else {
                        showFormError(errorDiv, data.error);
                        resetSubmitBtn(btn);
                    }
                })
                .catch(() => {
                    showFormError(errorDiv, 'Error de conexión. Intenta de nuevo.');
                    resetSubmitBtn(btn);
                });
        });
    }

    function showFormError(el, msg) {
        el.textContent = msg;
        el.classList.remove('hidden');
    }
    function resetSubmitBtn(btn) {
        btn.disabled = false;
        btn.innerHTML = '<i class="fa-solid fa-check mr-1"></i> Registrarme';
    }

    // ── Step 3: success ─────────────────────────────────────────
    function showSuccess(data) {
        document.getElementById('step-search').classList.add('hidden');
        document.getElementById('step-new-form').classList.add('hidden');
        document.getElementById('step-success').classList.remove('hidden');

        // Persistir inscripción en localStorage
        try {
            const stored = JSON.parse(localStorage.getItem('certifai_user') || '{}');
            stored.sessions = Array.isArray(stored.sessions) ? stored.sessions : [];
            const sid = parseInt(SESSION_ID);
            if (!stored.sessions.includes(sid)) stored.sessions.push(sid);
            const emailEl = document.querySelector('input[name="email"]');
            if (emailEl && emailEl.value) stored.email = emailEl.value.trim();
            localStorage.setItem('certifai_user', JSON.stringify(stored));
        } catch (e) { /* localStorage off — ignorar */ }

        document.getElementById('success-message').textContent = data.message;
        if (!data.sesion) return;

        document.getElementById('success-titulo').textContent = data.sesion.titulo;
        document.getElementById('success-fecha').textContent = data.sesion.fecha;
        document.getElementById('success-horario').textContent = data.sesion.horario;

        const esVirtual = data.sesion.modalidad === 'virtual';
        const lugarRow = document.getElementById('success-lugar-row');
        const plataformaRow = document.getElementById('success-plataforma-row');
        const virtualBlock = document.getElementById('success-virtual-link');

        if (esVirtual) {
            lugarRow.classList.add('hidden');
            plataformaRow.classList.remove('hidden');
            document.getElementById('success-plataforma').textContent = data.sesion.plataforma || 'Reunión virtual';

            if (data.sesion.enlace_virtual) {
                virtualBlock.classList.remove('hidden');
                document.getElementById('success-virtual-link-url').href = data.sesion.enlace_virtual;
                document.getElementById('success-virtual-link-text').textContent = data.sesion.enlace_virtual;
            }
            document.querySelectorAll('.success-tip-presencial').forEach(el => el.classList.add('hidden'));
            document.querySelectorAll('.success-tip-virtual').forEach(el => el.classList.remove('hidden'));
        } else {
            plataformaRow.classList.add('hidden');
            virtualBlock.classList.add('hidden');
            if (data.sesion.lugar) document.getElementById('success-lugar').textContent = data.sesion.lugar;
            else lugarRow.classList.add('hidden');
        }

        window.scrollTo({ top: 0, behavior: 'smooth' });
    }

    window.copyVirtualLink = function () {
        const url = document.getElementById('success-virtual-link-url').href;
        navigator.clipboard.writeText(url).then(() => {
            if (typeof showToast === 'function') showToast('Enlace copiado al portapapeles', 'success');
        }).catch(() => { });
    };
})();
