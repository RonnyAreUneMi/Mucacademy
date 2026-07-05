/**
 * attendance_search.js — buscador en vivo de participantes para verificar asistencias.
 *
 * Endpoint: GET /api/v1/public/attendance/search/?q=...
 * IDs en el template: #searchInput #spinner #clearBtn #searchHint
 *                     #resultsDropdown #resultsList
 */
(function () {
    'use strict';

    const input = document.getElementById('searchInput');
    if (!input) return;

    const dropdown = document.getElementById('resultsDropdown');
    const resultsList = document.getElementById('resultsList');
    const spinner = document.getElementById('spinner');
    const clearBtn = document.getElementById('clearBtn');
    const hint = document.getElementById('searchHint');

    let debounceTimer = null;
    let currentQuery = '';

    function getInitials(nombres, apellidos) {
        return ((nombres || '').trim().charAt(0) + (apellidos || '').trim().charAt(0)).toUpperCase();
    }

    function highlightMatch(text, query) {
        if (!query || !text) return text || '';
        const tokens = query.toLowerCase().split(/\s+/);
        let out = text;
        tokens.forEach(token => {
            if (token.length < 2) return;
            const re = new RegExp(`(${token.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi');
            out = out.replace(re, '<mark class="bg-[#F58830]/25 text-inherit rounded-sm px-0.5">$1</mark>');
        });
        return out;
    }

    function renderResults(data, query) {
        const results = data.results;
        if (results.length === 0) {
            resultsList.innerHTML = `
                <div class="text-center py-8 px-4 text-gray-400 dark:text-gray-500">
                    <i class="fa-solid fa-user-slash text-3xl mb-2 block text-gray-300 dark:text-gray-600"></i>
                    <p class="text-sm">No se encontraron resultados para "<strong>${query}</strong>"</p>
                </div>`;
            dropdown.classList.remove('hidden');
            return;
        }

        let html = `<div class="px-3 py-2 text-[10px] font-bold uppercase tracking-wider text-gray-400 dark:text-gray-500 border-b border-gray-100 dark:border-blue-900/30">
            ${results.length} resultado${results.length > 1 ? 's' : ''}
        </div>`;

        results.forEach(p => {
            const fullName = `${p.nombres} ${p.apellidos}`;
            const initials = getInitials(p.nombres, p.apellidos);
            const metaParts = [];
            if (p.cedula) metaParts.push(`<i class="fa-solid fa-id-card text-[10px]"></i> ${highlightMatch(p.cedula, query)}`);
            metaParts.push(`<i class="fa-solid fa-envelope text-[10px]"></i> ${highlightMatch(p.email, query)}`);
            if (p.cursos_count) metaParts.push(`<i class="fa-solid fa-graduation-cap text-[10px]"></i> ${p.cursos_count}`);

            html += `
                <a href="/attendance/verify/?q=${encodeURIComponent(p.cedula || p.email)}"
                   class="flex items-center gap-3 px-4 py-3 hover:bg-[#F58830]/10 transition-colors group">
                    <div class="w-11 h-11 rounded-xl bg-gradient-to-br from-[#162054] to-blue-700 text-white flex items-center justify-center font-bold text-sm shrink-0">${initials}</div>
                    <div class="flex-1 min-w-0">
                        <div class="font-bold text-sm text-gray-800 dark:text-white truncate">${highlightMatch(fullName, query)}</div>
                        <div class="text-xs text-gray-500 dark:text-gray-400 truncate mt-0.5">${metaParts.join(' &nbsp;·&nbsp; ')}</div>
                    </div>
                    <i class="fa-solid fa-chevron-right text-gray-300 dark:text-gray-600 text-xs group-hover:text-[#F58830]"></i>
                </a>`;
        });

        resultsList.innerHTML = html;
        dropdown.classList.remove('hidden');
    }

    function doSearch(query) {
        if (query.length < 3) {
            dropdown.classList.add('hidden');
            hint.style.opacity = '1';
            spinner.classList.add('hidden');
            return;
        }
        hint.style.opacity = '0';
        spinner.classList.remove('hidden');

        fetch(`/api/v1/public/attendance/search/?q=${encodeURIComponent(query)}`)
            .then(r => r.json())
            .then(data => {
                spinner.classList.add('hidden');
                if (query === currentQuery) renderResults(data, query);
            })
            .catch(() => spinner.classList.add('hidden'));
    }

    input.addEventListener('input', () => {
        const val = input.value.trim();
        currentQuery = val;
        clearBtn.classList.toggle('hidden', val.length === 0);
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(() => doSearch(val), 300);
    });

    clearBtn.addEventListener('click', () => {
        input.value = '';
        currentQuery = '';
        dropdown.classList.add('hidden');
        clearBtn.classList.add('hidden');
        hint.style.opacity = '1';
        input.focus();
    });

    document.addEventListener('click', (e) => {
        if (!e.target.closest('.search-wrapper')) dropdown.classList.add('hidden');
    });

    input.addEventListener('focus', () => {
        if (currentQuery.length >= 3) doSearch(currentQuery);
    });

    input.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            const first = resultsList.querySelector('a');
            if (first) first.click();
        }
    });

    // Auto-search si vino con query
    if (input.value.trim().length >= 3) {
        currentQuery = input.value.trim();
        doSearch(currentQuery);
    }
})();
