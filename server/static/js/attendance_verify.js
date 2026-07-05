/**
 * attendance_verify.js — flujo de confirmación de asistencia.
 *
 * Espera del template:
 *   window.VERIFY_CONFIG = {
 *       diasDisponibles: { 'Lunes': [{id, label, cupos, llena}, ...], ... },
 *       certId: '<id>',
 *       csrfToken: '<token>',
 *   }
 *
 * Endpoints:
 *   POST /api/v1/public/attendance/update-phone/
 *   POST /api/v1/public/attendance/confirm/
 *
 * IDs en template: #select-dia #select-horario #horario-wrapper
 *                  #btn-final-confirm #input-celular #phone-status-icon
 *                  #step-schedule #step-success #success-message
 */
(function () {
    'use strict';

    const CFG = window.VERIFY_CONFIG;
    if (!CFG) return;
    const diasDisponibles = CFG.diasDisponibles || {};
    const certId = CFG.certId || '';
    const csrfToken = CFG.csrfToken || '';

    // Poblar el select de días al cargar
    document.addEventListener('DOMContentLoaded', () => {
        const selectDia = document.getElementById('select-dia');
        if (!selectDia) return;
        selectDia.innerHTML = '<option value="">— Selecciona un día —</option>';
        Object.keys(diasDisponibles).forEach(dia => {
            const opt = document.createElement('option');
            opt.value = dia;
            opt.textContent = dia;
            selectDia.appendChild(opt);
        });
    });

    // ── Día → horarios dependientes ─────────────────────────────
    window.onDayChange = function () {
        const dia = document.getElementById('select-dia').value;
        const wrapper = document.getElementById('horario-wrapper');
        const selectHorario = document.getElementById('select-horario');
        const btn = document.getElementById('btn-final-confirm');

        if (!dia) {
            wrapper.classList.add('hidden');
            btn.disabled = true;
            return;
        }

        selectHorario.innerHTML = '<option value="">— Selecciona un horario —</option>';
        (diasDisponibles[dia] || []).forEach(slot => {
            const opt = document.createElement('option');
            opt.value = slot.id;
            if (slot.llena) {
                opt.textContent = `[AGOTADO] ${slot.label}`;
                opt.disabled = true;
            } else {
                opt.textContent = `${slot.label} (${slot.cupos} cupos disponibles)`;
            }
            selectHorario.appendChild(opt);
        });

        wrapper.classList.remove('hidden');
        btn.disabled = true;

        selectHorario.addEventListener('change', () => {
            btn.disabled = !selectHorario.value;
        });
    };

    // ── Auto-save del celular al perder foco ────────────────────
    window.savePhone = async function () {
        const input = document.getElementById('input-celular');
        const icon = document.getElementById('phone-status-icon');
        if (!certId || !input) return;

        icon.className = 'fa-solid fa-spinner fa-spin text-[#F58830] text-sm absolute right-2 pointer-events-none';
        const fd = new FormData();
        fd.append('cert_id', certId);
        fd.append('celular', input.value.trim());
        fd.append('csrfmiddlewaretoken', csrfToken);

        try {
            const res = await fetch('/api/v1/public/attendance/update-phone/', {
                method: 'POST',
                body: fd,
                headers: { 'X-Requested-With': 'XMLHttpRequest' },
            });
            icon.className = res.ok
                ? 'fa-solid fa-check text-emerald-500 text-sm absolute right-2 pointer-events-none'
                : 'fa-solid fa-triangle-exclamation text-red-500 text-sm absolute right-2 pointer-events-none';
        } catch (e) {
            icon.className = 'fa-solid fa-triangle-exclamation text-red-500 text-sm absolute right-2 pointer-events-none';
            console.error('Error guardando celular:', e);
        }

        setTimeout(() => {
            icon.className = 'fa-solid fa-pen text-gray-400 dark:text-gray-500 text-sm absolute right-2 pointer-events-none transition-all';
        }, 2000);
    };

    // ── Modal de compromiso (SweetAlert) + envío ────────────────
    window.triggerConfirmationPopup = function () {
        const sesionId = document.getElementById('select-horario').value;
        if (!sesionId) return;

        Swal.fire({
            title: '¡Compromiso de asistencia!',
            html: `
                <div class="text-left mt-2">
                    <p class="mb-4 text-gray-600 dark:text-gray-300">Al confirmar, te comprometes a asistir a la sesión seleccionada.</p>
                    <div class="p-4 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 rounded-lg">
                        <p class="text-amber-800 dark:text-amber-400 text-sm font-bold m-0"><i class="fa-solid fa-triangle-exclamation mr-2"></i>Si faltas, tu cuenta será bloqueada y no podrás recibir certificados.</p>
                    </div>
                    <p class="mt-4 text-gray-600 dark:text-gray-300 text-sm font-semibold text-center">Ese día, se tomará asistencia proyectando un código QR.</p>
                </div>`,
            icon: 'warning',
            iconColor: '#F58830',
            showCancelButton: true,
            confirmButtonColor: '#10B981',
            cancelButtonColor: '#EF4444',
            confirmButtonText: 'Sí, acepto el compromiso',
            cancelButtonText: 'Cancelar',
            background: document.documentElement.classList.contains('dark') ? '#1e293b' : '#fff',
            color: document.documentElement.classList.contains('dark') ? '#fff' : '#1e293b',
            customClass: {
                title: 'font-black text-2xl',
                confirmButton: 'font-bold px-6 py-3 rounded-xl shadow-lg swal-btn-confirm',
                cancelButton: 'font-bold px-6 py-3 rounded-xl swal-btn-cancel',
            },
        }).then(result => {
            if (result.isConfirmed) submitConfirmation();
        });
    };

    async function submitConfirmation() {
        const sesionId = document.getElementById('select-horario').value;
        if (!sesionId || !certId) return;

        const btn = document.getElementById('btn-final-confirm');
        btn.disabled = true;
        btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Procesando...';

        try {
            const fd = new FormData();
            fd.append('cert_id', certId);
            fd.append('sesion_id', sesionId);
            const res = await fetch('/api/v1/public/attendance/confirm/', {
                method: 'POST',
                headers: { 'X-CSRFToken': csrfToken },
                body: fd,
            });
            const data = await res.json();

            if (data.ok) {
                document.getElementById('step-schedule').classList.add('hidden');
                document.getElementById('step-success').classList.remove('hidden');
                document.getElementById('success-message').textContent = data.message;
            } else {
                resetButton(btn);
                if (typeof showToast === 'function') showToast(data.error || 'Error al confirmar.', 'error');
            }
        } catch (err) {
            resetButton(btn);
            if (typeof showToast === 'function') showToast('Error de conexión. Inténtalo de nuevo.', 'error');
        }
    }

    function resetButton(btn) {
        btn.disabled = false;
        btn.innerHTML = '<i class="fa-solid fa-lock"></i> Confirmar asistencia';
    }
})();
