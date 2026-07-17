/* Hero de partículas · CertifAI — adaptación vanilla (sin librerías).
   Se ancla a #hero-fx: campo ambiental + partículas que ciclan entre
   glifos de certificado/educación, el logo del tigre y el texto "CertifAI"
   (también al pasar el cursor). Paleta naranja→púrpura, sensible al tema. */
(function () {
    'use strict';
    var doc = document;
    var hero = doc.getElementById('hero-fx');
    if (!hero || !doc.createElement('canvas').getContext) return;

    var reduce = window.matchMedia &&
        window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    var canvas = doc.createElement('canvas');
    canvas.setAttribute('aria-hidden', 'true');
    canvas.style.cssText = 'position:absolute;inset:0;pointer-events:none;z-index:0;';
    hero.insertBefore(canvas, hero.firstChild);

    var ctx = canvas.getContext('2d');
    var dpr = Math.min(window.devicePixelRatio || 1, 2);
    var W = 0, H = 0;
    var ambient = [];
    var shapeP = [];
    var shapeIsLogo = false;
    var mouse = { x: -9999, y: -9999, on: false };
    var HERO_TEXT = (hero.getAttribute('data-hero-text') || 'CertifAI').trim();
    var LOGO_URL = hero.getAttribute('data-logo') || '';
    var textPts = null;
    var hoverText = false;
    var REPEL = 82, MAXPUSH = 15;

    var isDark = doc.documentElement.classList.contains('dark');
    new MutationObserver(function () {
        isDark = doc.documentElement.classList.contains('dark');
    }).observe(doc.documentElement, { attributes: true, attributeFilter: ['class'] });

    // Gradiente naranja #F58830 → púrpura #A855F7 en función de t (0..1).
    function rgbAt(t) {
        return [
            Math.round(245 - 77 * t),
            Math.round(136 - 51 * t),
            Math.round(48 + 199 * t)
        ];
    }
    // Color final según tema: claro → más oscuro/saturado y opaco; oscuro → más claro/suave.
    function colorFor(t, alpha) {
        var c = rgbAt(t);
        if (isDark) {
            return 'rgba(' + Math.min(255, c[0] + 26) + ',' + Math.min(255, c[1] + 26) +
                ',' + Math.min(255, c[2] + 20) + ',' + (alpha != null ? alpha : 0.85) + ')';
        }
        return 'rgba(' + Math.round(c[0] * 0.82) + ',' + Math.round(c[1] * 0.72) +
            ',' + Math.round(c[2] * 0.86) + ',' + (alpha != null ? alpha : 0.95) + ')';
    }
    function styleFor(p, base) {
        if (p.rgb) {
            var a = isDark ? 0.95 : 0.9;
            return 'rgba(' + p.rgb[0] + ',' + p.rgb[1] + ',' + p.rgb[2] + ',' + a + ')';
        }
        return colorFor(p.t, base);
    }

    var GLYPHS = ['', '', '', '', '', ''];
    var glyphIndex = 0, SWITCH_MS = 4800, lastSwitch = 0;

    var off = doc.createElement('canvas');
    var octx = off.getContext('2d');
    var SAMPLE = 240;
    off.width = SAMPLE; off.height = SAMPLE;

    function glyphPoints(glyph) {
        octx.clearRect(0, 0, SAMPLE, SAMPLE);
        octx.fillStyle = '#fff';
        octx.textAlign = 'center';
        octx.textBaseline = 'middle';
        octx.font = '900 180px "Font Awesome 6 Free"';
        octx.fillText(glyph, SAMPLE / 2, SAMPLE / 2);
        var data;
        try { data = octx.getImageData(0, 0, SAMPLE, SAMPLE).data; }
        catch (e) { return []; }
        var pts = [], step = 5;
        for (var y = 0; y < SAMPLE; y += step) {
            for (var x = 0; x < SAMPLE; x += step) {
                if (data[(y * SAMPLE + x) * 4 + 3] > 130) pts.push([x, y]);
            }
        }
        return pts;
    }

    var logoPts = null;

    function buildTargets(pts) {
        if (!pts || pts.length < 24) return false;
        var isLogo = pts[0].length > 2;
        shapeIsLogo = isLogo;
        var size = Math.min(H * 0.82, W * 0.5);
        var scale = size / SAMPLE;
        var cx = W * (W < 760 ? 0.5 : 0.74);
        var cy = H * (W < 760 ? 0.68 : 0.5);
        var target = isLogo
            ? Math.min(pts.length, W < 760 ? 900 : 1500)
            : Math.min(pts.length, W < 760 ? 200 : 420);
        var stride = pts.length / target;
        while (shapeP.length < target) {
            shapeP.push({ x: Math.random() * W, y: Math.random() * H, tx: 0, ty: 0 });
        }
        shapeP.length = target;
        for (var i = 0; i < target; i++) {
            var pt = pts[Math.floor(i * stride)];
            shapeP[i].tx = cx + (pt[0] - SAMPLE / 2) * scale;
            shapeP[i].ty = cy + (pt[1] - SAMPLE / 2) * scale;
            if (pt.length > 2) { shapeP[i].rgb = [pt[2], pt[3], pt[4]]; shapeP[i].t = 0; }
            else { shapeP[i].rgb = null; shapeP[i].t = pt[0] / SAMPLE; }
        }
        return true;
    }

    // Rotación: glifos de certificado/educación → logo del tigre → texto "CertifAI".
    function totalShapes() { return GLYPHS.length + (logoPts ? 1 : 0) + 1; }

    function applyShapeAt(idx) {
        if (idx < GLYPHS.length) return buildTargets(glyphPoints(GLYPHS[idx]));
        if (logoPts && idx === GLYPHS.length) return buildTargets(logoPts);
        return applyText();
    }

    function loadLogo(url) {
        if (!url) return;
        var img = new Image();
        img.onload = function () {
            octx.clearRect(0, 0, SAMPLE, SAMPLE);
            var r = Math.min(SAMPLE / img.width, SAMPLE / img.height) * 0.92;
            var w = img.width * r, h = img.height * r;
            octx.drawImage(img, (SAMPLE - w) / 2, (SAMPLE - h) / 2, w, h);
            var data;
            try { data = octx.getImageData(0, 0, SAMPLE, SAMPLE).data; }
            catch (e) { return; }
            var pts = [], step = 3;
            for (var y = 0; y < SAMPLE; y += step) {
                for (var x = 0; x < SAMPLE; x += step) {
                    var k = (y * SAMPLE + x) * 4;
                    if (data[k + 3] > 130) {
                        pts.push([x, y, data[k], data[k + 1], data[k + 2]]);
                    }
                }
            }
            if (pts.length >= 40) {
                logoPts = pts;
                if (!reduce) {
                    glyphIndex = GLYPHS.length;
                    applyShapeAt(glyphIndex);
                    lastSwitch = 0;
                }
            }
        };
        img.src = url;
    }

    function buildAmbient() {
        var count = Math.max(40, Math.min(Math.round(W / 12), 130));
        ambient = [];
        for (var i = 0; i < count; i++) {
            ambient.push({
                x: Math.random() * W, y: Math.random() * H,
                vx: (Math.random() - 0.5) * 0.26,
                vy: (Math.random() - 0.5) * 0.26,
                t: Math.random(), rgb: null
            });
        }
    }

    function sizeHero() {
        W = hero.clientWidth; H = hero.clientHeight;
        canvas.width = W * dpr; canvas.height = H * dpr;
        canvas.style.width = W + 'px'; canvas.style.height = H + 'px';
        ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
        buildAmbient();
        applyShapeAt(glyphIndex);
    }

    function repel(px, py) {
        if (!mouse.on || hoverText) return [px, py];
        var dx = px - mouse.x, dy = py - mouse.y;
        var d = Math.sqrt(dx * dx + dy * dy);
        if (d < REPEL && d > 0.001) {
            var push = (1 - d / REPEL) * MAXPUSH;
            return [px + (dx / d) * push, py + (dy / d) * push];
        }
        return [px, py];
    }

    var TXT_W = 760, TXT_H = 200;
    function buildTextPts() {
        var toff = doc.createElement('canvas'); toff.width = TXT_W; toff.height = TXT_H;
        var tctx = toff.getContext('2d');
        tctx.fillStyle = '#fff';
        tctx.textAlign = 'center';
        tctx.textBaseline = 'middle';
        var fs = 150;
        tctx.font = '800 ' + fs + 'px Outfit, Arial, sans-serif';
        while (tctx.measureText(HERO_TEXT).width > TXT_W * 0.95 && fs > 12) {
            fs -= 4; tctx.font = '800 ' + fs + 'px Outfit, Arial, sans-serif';
        }
        tctx.fillText(HERO_TEXT, TXT_W / 2, TXT_H / 2);
        var d;
        try { d = tctx.getImageData(0, 0, TXT_W, TXT_H).data; }
        catch (e) { return; }
        var pts = [], step = 4;
        for (var y = 0; y < TXT_H; y += step) {
            for (var x = 0; x < TXT_W; x += step) {
                if (d[(y * TXT_W + x) * 4 + 3] > 130) pts.push([x / TXT_W, y / TXT_H]);
            }
        }
        if (pts.length >= 40) textPts = pts;
    }

    function applyText() {
        if (!textPts) buildTextPts();
        if (!textPts) return false;
        shapeIsLogo = true;
        var aspect = TXT_W / TXT_H;
        var tW = W < 760 ? W * 0.86 : W * 0.52;
        var tH = tW / aspect;
        var cx = W * (W < 760 ? 0.5 : 0.70);
        var cy = H * (W < 760 ? 0.68 : 0.5);
        var target = Math.min(textPts.length, W < 760 ? 360 : 720);
        var stride = textPts.length / target;
        while (shapeP.length < target) {
            shapeP.push({ x: Math.random() * W, y: Math.random() * H, tx: 0, ty: 0 });
        }
        shapeP.length = target;
        for (var i = 0; i < target; i++) {
            var pt = textPts[Math.floor(i * stride)];
            shapeP[i].tx = cx + (pt[0] - 0.5) * tW;
            shapeP[i].ty = cy + (pt[1] - 0.5) * tH;
            shapeP[i].rgb = null;
            shapeP[i].t = pt[0];
        }
        return true;
    }

    function frame(ts) {
        if (mouse.on) {
            if (!hoverText) hoverText = applyText();
        } else {
            if (hoverText) { hoverText = false; applyShapeAt(glyphIndex); lastSwitch = ts; }
            if (!lastSwitch) lastSwitch = ts;
            if (ts - lastSwitch > SWITCH_MS) {
                glyphIndex = (glyphIndex + 1) % totalShapes();
                lastSwitch = applyShapeAt(glyphIndex) ? ts : (ts - SWITCH_MS + 500);
            }
        }
        ctx.clearRect(0, 0, W, H);

        for (var i = 0; i < ambient.length; i++) {
            var a = ambient[i];
            a.x += a.vx; a.y += a.vy;
            if (a.x < 0) a.x = W; else if (a.x > W) a.x = 0;
            if (a.y < 0) a.y = H; else if (a.y > H) a.y = 0;
            var r = repel(a.x, a.y);
            ctx.fillStyle = colorFor(a.t, isDark ? 0.55 : 0.6);
            ctx.beginPath(); ctx.arc(r[0], r[1], 1.7, 0, 6.2832); ctx.fill();
        }

        for (var j = 0; j < shapeP.length; j++) {
            var p = shapeP[j];
            p.x += (p.tx - p.x) * 0.085;
            p.y += (p.ty - p.y) * 0.085;
            var rr = repel(p.x, p.y);
            ctx.fillStyle = styleFor(p, 0.95);
            if (shapeIsLogo) {
                ctx.fillRect(rr[0], rr[1], 1.8, 1.8);
            } else {
                ctx.beginPath(); ctx.arc(rr[0], rr[1], 2.6, 0, 6.2832); ctx.fill();
            }
        }

        raf = requestAnimationFrame(frame);
    }

    function drawStatic() {
        ctx.clearRect(0, 0, W, H);
        for (var i = 0; i < ambient.length; i++) {
            ctx.fillStyle = colorFor(ambient[i].t, isDark ? 0.55 : 0.6);
            ctx.beginPath(); ctx.arc(ambient[i].x, ambient[i].y, 1.7, 0, 6.2832); ctx.fill();
        }
        for (var j = 0; j < shapeP.length; j++) {
            ctx.fillStyle = styleFor(shapeP[j], 0.95);
            if (shapeIsLogo) { ctx.fillRect(shapeP[j].tx, shapeP[j].ty, 1.8, 1.8); }
            else { ctx.beginPath(); ctx.arc(shapeP[j].tx, shapeP[j].ty, 2.6, 0, 6.2832); ctx.fill(); }
        }
    }

    hero.addEventListener('mousemove', function (e) {
        var rect = hero.getBoundingClientRect();
        mouse.x = e.clientX - rect.left;
        mouse.y = e.clientY - rect.top;
        mouse.on = true;
    });
    hero.addEventListener('mouseleave', function () {
        mouse.on = false; mouse.x = mouse.y = -9999;
    });

    loadLogo(LOGO_URL);

    var raf = null;
    function start() {
        sizeHero();
        if (reduce) drawStatic();
        else raf = requestAnimationFrame(frame);
    }

    if (doc.fonts && doc.fonts.load) {
        var started = false;
        var go = function () { if (started) return; started = true; start(); };
        doc.fonts.load('900 40px "Font Awesome 6 Free"').then(go).catch(go);
        setTimeout(go, 1200);
    } else {
        start();
    }

    var rsTimer;
    window.addEventListener('resize', function () {
        clearTimeout(rsTimer);
        rsTimer = setTimeout(function () {
            sizeHero();
            if (reduce) drawStatic();
        }, 200);
    }, { passive: true });
})();
