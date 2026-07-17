/* Partículas · CertifAI — motor vanilla (sin librerías).
   Dos modos:
   - full  (#hero-fx): campo ambiental + partículas que ciclan entre glifos de
     certificado/educación, el logo del tigre y el texto "CertifAI" (también al
     pasar el cursor).
   - ambient (.fx-header): solo el campo de puntos a la deriva con repulsión
     suave del cursor, sin figura grande (nunca tapa el título).
   Paleta naranja→púrpura, sensible al tema. Un único requestAnimationFrame
   compartido; los hosts fuera de viewport se pausan (IntersectionObserver). */
(function () {
    'use strict';
    var doc = document;
    if (!doc.createElement('canvas').getContext) return;

    var hosts = doc.querySelectorAll('#hero-fx, .fx-header');
    if (!hosts.length) return;

    var scriptTag = doc.querySelector('script[data-tiger]');
    var TIGER_URL = scriptTag ? scriptTag.getAttribute('data-tiger') : '';

    var reduce = window.matchMedia &&
        window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    var dpr = Math.min(window.devicePixelRatio || 1, 2);

    var isDark = doc.documentElement.classList.contains('dark');
    new MutationObserver(function () {
        isDark = doc.documentElement.classList.contains('dark');
    }).observe(doc.documentElement, { attributes: true, attributeFilter: ['class'] });

    function rgbAt(t) {
        return [
            Math.round(245 - 77 * t),
            Math.round(136 - 51 * t),
            Math.round(48 + 199 * t)
        ];
    }
    function colorFor(t, alpha) {
        var c = rgbAt(t);
        if (isDark) {
            return 'rgba(' + Math.min(255, c[0] + 26) + ',' + Math.min(255, c[1] + 26) +
                ',' + Math.min(255, c[2] + 20) + ',' + (alpha != null ? alpha : 0.85) + ')';
        }
        return 'rgba(' + Math.round(c[0] * 0.82) + ',' + Math.round(c[1] * 0.72) +
            ',' + Math.round(c[2] * 0.86) + ',' + (alpha != null ? alpha : 0.95) + ')';
    }
    function rgbThemed(t) {
        var c = rgbAt(t);
        return isDark
            ? [Math.min(255, c[0] + 26), Math.min(255, c[1] + 26), Math.min(255, c[2] + 20)]
            : [Math.round(c[0] * 0.82), Math.round(c[1] * 0.72), Math.round(c[2] * 0.86)];
    }

    // ─────────────────────────── instancia por host ───────────────────────────
    function Instance(host, mode) {
        this.host = host;
        this.ambientOnly = (mode === 'ambient');
        this.visible = true;
        this.W = 0; this.H = 0;
        this.ambient = [];
        this.shapeP = [];
        this.shapeIsLogo = false;
        this.mouse = { x: -9999, y: -9999, on: false };
        this.HERO_TEXT = (host.getAttribute('data-hero-text') || 'CertifAI').trim();
        this.LOGO_URL = host.getAttribute('data-logo') || (this.ambientOnly ? TIGER_URL : '');
        this.textPts = null;
        this.logoPts = null;
        this.hoverText = false;
        this.glyphIndex = 0;
        this.lastSwitch = 0;
        this.REPEL = 82; this.MAXPUSH = 15;
        this.active = false;   // hover en headers ambient
        this.morph = 0;        // 0 = texto CertifAI, 1 = tigre

        this.GLYPHS = ['', '', '', '', '', ''];
        this.SWITCH_MS = 4800;
        this.SAMPLE = 240;
        this.TXT_W = 760; this.TXT_H = 200;

        var canvas = doc.createElement('canvas');
        canvas.setAttribute('aria-hidden', 'true');
        canvas.style.cssText = 'position:absolute;inset:0;pointer-events:none;z-index:0;';
        host.insertBefore(canvas, host.firstChild);
        this.canvas = canvas;
        this.ctx = canvas.getContext('2d');

        this.off = doc.createElement('canvas');
        this.off.width = this.SAMPLE; this.off.height = this.SAMPLE;
        this.octx = this.off.getContext('2d');

        var self = this;
        if (this.ambientOnly) {
            host.addEventListener('mouseenter', function () { self.active = true; self.cleared = false; });
            host.addEventListener('mouseleave', function () { self.active = false; });
        } else {
            host.addEventListener('mousemove', function (e) {
                var rect = host.getBoundingClientRect();
                self.mouse.x = e.clientX - rect.left;
                self.mouse.y = e.clientY - rect.top;
                self.mouse.on = true;
            });
            host.addEventListener('mouseleave', function () {
                self.mouse.on = false; self.mouse.x = self.mouse.y = -9999;
            });
        }
    }

    Instance.prototype.styleFor = function (p, base) {
        if (p.rgb) {
            var a = isDark ? 0.95 : 0.9;
            return 'rgba(' + p.rgb[0] + ',' + p.rgb[1] + ',' + p.rgb[2] + ',' + a + ')';
        }
        return colorFor(p.t, base);
    };

    Instance.prototype.glyphPoints = function (glyph) {
        var S = this.SAMPLE, octx = this.octx;
        octx.clearRect(0, 0, S, S);
        octx.fillStyle = '#fff';
        octx.textAlign = 'center';
        octx.textBaseline = 'middle';
        octx.font = '900 180px "Font Awesome 6 Free"';
        octx.fillText(glyph, S / 2, S / 2);
        var data;
        try { data = octx.getImageData(0, 0, S, S).data; }
        catch (e) { return []; }
        var pts = [], step = 5;
        for (var y = 0; y < S; y += step) {
            for (var x = 0; x < S; x += step) {
                if (data[(y * S + x) * 4 + 3] > 130) pts.push([x, y]);
            }
        }
        return pts;
    };

    Instance.prototype.buildTargets = function (pts) {
        if (!pts || pts.length < 24) return false;
        var W = this.W, H = this.H, S = this.SAMPLE;
        var isLogo = pts[0].length > 2;
        this.shapeIsLogo = isLogo;
        var size = Math.min(H * 0.82, W * 0.5);
        var scale = size / S;
        var cx = W * (W < 760 ? 0.5 : 0.74);
        var cy = H * (W < 760 ? 0.68 : 0.5);
        var target = isLogo
            ? Math.min(pts.length, W < 760 ? 900 : 1500)
            : Math.min(pts.length, W < 760 ? 200 : 420);
        var stride = pts.length / target;
        while (this.shapeP.length < target) {
            this.shapeP.push({ x: Math.random() * W, y: Math.random() * H, tx: 0, ty: 0 });
        }
        this.shapeP.length = target;
        for (var i = 0; i < target; i++) {
            var pt = pts[Math.floor(i * stride)];
            this.shapeP[i].tx = cx + (pt[0] - S / 2) * scale;
            this.shapeP[i].ty = cy + (pt[1] - S / 2) * scale;
            if (pt.length > 2) { this.shapeP[i].rgb = [pt[2], pt[3], pt[4]]; this.shapeP[i].t = 0; }
            else { this.shapeP[i].rgb = null; this.shapeP[i].t = pt[0] / S; }
        }
        return true;
    };

    Instance.prototype.totalShapes = function () {
        return this.GLYPHS.length + (this.logoPts ? 1 : 0) + 1;
    };

    Instance.prototype.applyShapeAt = function (idx) {
        if (idx < this.GLYPHS.length) return this.buildTargets(this.glyphPoints(this.GLYPHS[idx]));
        if (this.logoPts && idx === this.GLYPHS.length) return this.buildTargets(this.logoPts);
        return this.applyText();
    };

    Instance.prototype.loadLogo = function (url) {
        if (!url) return;
        var self = this, S = this.SAMPLE, octx = this.octx;
        var img = new Image();
        img.onload = function () {
            octx.clearRect(0, 0, S, S);
            var r = Math.min(S / img.width, S / img.height) * 0.92;
            var w = img.width * r, h = img.height * r;
            octx.drawImage(img, (S - w) / 2, (S - h) / 2, w, h);
            var data;
            try { data = octx.getImageData(0, 0, S, S).data; }
            catch (e) { return; }
            var pts = [], step = 3;
            for (var y = 0; y < S; y += step) {
                for (var x = 0; x < S; x += step) {
                    var k = (y * S + x) * 4;
                    if (data[k + 3] > 130) pts.push([x, y, data[k], data[k + 1], data[k + 2]]);
                }
            }
            if (pts.length >= 40) {
                self.logoPts = pts;
                if (self.ambientOnly) {
                    self.buildAmbientTargets();
                } else if (!reduce) {
                    self.glyphIndex = self.GLYPHS.length;
                    self.applyShapeAt(self.glyphIndex);
                    self.lastSwitch = 0;
                }
            }
        };
        img.src = url;
    };

    // Header: los puntos forman "CertifAI" (idle) y el tigre (hover); cada punto
    // tiene su destino de texto (tX,tY) y de tigre (gX,gY) y se interpola entre
    // ambos. Ambas figuras van en la zona derecha del header (fuera del título).
    Instance.prototype.buildAmbientTargets = function () {
        if (!this.textPts) this.buildTextPts();
        if (!this.textPts) return;
        var W = this.W, H = this.H, S = this.SAMPLE;
        var count = W < 760 ? 320 : 560;
        var cx = W * (W < 760 ? 0.5 : 0.62), cy = H * 0.5;
        var aspect = this.TXT_W / this.TXT_H;
        var tW = Math.min(W * 0.42, H * 0.7 * aspect), tH = tW / aspect;
        var gSize = Math.min(H * 1.0, W * 0.38), gScale = gSize / S;
        var strideT = this.textPts.length / count;
        var lp = this.logoPts, strideG = lp ? lp.length / count : 0;
        this.shapeP.length = 0;
        for (var i = 0; i < count; i++) {
            var tp = this.textPts[Math.floor(i * strideT) % this.textPts.length];
            var tX = cx + (tp[0] - 0.5) * tW, tY = cy + (tp[1] - 0.5) * tH;
            var gX = tX, gY = tY, grgb = null;
            if (lp) {
                var gp = lp[Math.floor(i * strideG) % lp.length];
                gX = cx + (gp[0] - S / 2) * gScale;
                gY = cy + (gp[1] - S / 2) * gScale;
                grgb = [gp[2], gp[3], gp[4]];
            }
            this.shapeP.push({ tX: tX, tY: tY, gX: gX, gY: gY, tcol: tp[0], grgb: grgb });
        }
    };

    Instance.prototype.buildAmbient = function () {
        var W = this.W, count;
        if (this.ambientOnly) count = Math.max(12, Math.min(Math.round(W / 22), 60));
        else count = Math.max(40, Math.min(Math.round(W / 12), 130));
        this.ambient = [];
        for (var i = 0; i < count; i++) {
            this.ambient.push({
                x: Math.random() * W, y: Math.random() * this.H,
                vx: (Math.random() - 0.5) * 0.26,
                vy: (Math.random() - 0.5) * 0.26,
                t: Math.random(), rgb: null
            });
        }
    };

    Instance.prototype.size = function () {
        this.W = this.host.clientWidth; this.H = this.host.clientHeight;
        this.canvas.width = this.W * dpr; this.canvas.height = this.H * dpr;
        this.canvas.style.width = this.W + 'px'; this.canvas.style.height = this.H + 'px';
        this.ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
        if (this.ambientOnly) {
            this.buildAmbientTargets();
        } else {
            this.buildAmbient();
            this.applyShapeAt(this.glyphIndex);
        }
    };

    Instance.prototype.repel = function (px, py) {
        if (!this.mouse.on || this.hoverText) return [px, py];
        var dx = px - this.mouse.x, dy = py - this.mouse.y;
        var d = Math.sqrt(dx * dx + dy * dy);
        if (d < this.REPEL && d > 0.001) {
            var push = (1 - d / this.REPEL) * this.MAXPUSH;
            return [px + (dx / d) * push, py + (dy / d) * push];
        }
        return [px, py];
    };

    Instance.prototype.buildTextPts = function () {
        var TXT_W = this.TXT_W, TXT_H = this.TXT_H;
        var toff = doc.createElement('canvas'); toff.width = TXT_W; toff.height = TXT_H;
        var tctx = toff.getContext('2d');
        tctx.fillStyle = '#fff';
        tctx.textAlign = 'center';
        tctx.textBaseline = 'middle';
        var fs = 150;
        tctx.font = '800 ' + fs + 'px Outfit, Arial, sans-serif';
        while (tctx.measureText(this.HERO_TEXT).width > TXT_W * 0.95 && fs > 12) {
            fs -= 4; tctx.font = '800 ' + fs + 'px Outfit, Arial, sans-serif';
        }
        tctx.fillText(this.HERO_TEXT, TXT_W / 2, TXT_H / 2);
        var d;
        try { d = tctx.getImageData(0, 0, TXT_W, TXT_H).data; }
        catch (e) { return; }
        var pts = [], step = 4;
        for (var y = 0; y < TXT_H; y += step) {
            for (var x = 0; x < TXT_W; x += step) {
                if (d[(y * TXT_W + x) * 4 + 3] > 130) pts.push([x / TXT_W, y / TXT_H]);
            }
        }
        if (pts.length >= 40) this.textPts = pts;
    };

    Instance.prototype.applyText = function () {
        if (!this.textPts) this.buildTextPts();
        if (!this.textPts) return false;
        var W = this.W, H = this.H;
        this.shapeIsLogo = true;
        var aspect = this.TXT_W / this.TXT_H;
        var tW = W < 760 ? W * 0.86 : W * 0.52;
        var tH = tW / aspect;
        var cx = W * (W < 760 ? 0.5 : 0.70);
        var cy = H * (W < 760 ? 0.68 : 0.5);
        var target = Math.min(this.textPts.length, W < 760 ? 360 : 720);
        var stride = this.textPts.length / target;
        while (this.shapeP.length < target) {
            this.shapeP.push({ x: Math.random() * W, y: Math.random() * H, tx: 0, ty: 0 });
        }
        this.shapeP.length = target;
        for (var i = 0; i < target; i++) {
            var pt = this.textPts[Math.floor(i * stride)];
            this.shapeP[i].tx = cx + (pt[0] - 0.5) * tW;
            this.shapeP[i].ty = cy + (pt[1] - 0.5) * tH;
            this.shapeP[i].rgb = null;
            this.shapeP[i].t = pt[0];
        }
        return true;
    };

    // Header: siempre visible. Idle = "CertifAI"; al hover = tigre. Interpola
    // posición y color entre ambos según `morph`.
    Instance.prototype.frameAmbient = function () {
        var ctx = this.ctx, W = this.W, H = this.H;
        if (!this.shapeP.length) return;
        var goal = this.active ? 1 : 0;
        this.morph += (goal - this.morph) * 0.09;
        var m = this.morph, aBase = isDark ? 0.92 : 0.9;
        ctx.clearRect(0, 0, W, H);
        for (var i = 0; i < this.shapeP.length; i++) {
            var p = this.shapeP[i];
            var x = p.tX + (p.gX - p.tX) * m, y = p.tY + (p.gY - p.tY) * m;
            var tc = rgbThemed(p.tcol), r = tc[0], g = tc[1], b = tc[2];
            if (p.grgb) {
                r = Math.round(r + (p.grgb[0] - r) * m);
                g = Math.round(g + (p.grgb[1] - g) * m);
                b = Math.round(b + (p.grgb[2] - b) * m);
            }
            ctx.fillStyle = 'rgba(' + r + ',' + g + ',' + b + ',' + aBase + ')';
            ctx.fillRect(x, y, 1.8, 1.8);
        }
    };

    Instance.prototype.frame = function (ts) {
        if (this.ambientOnly) { this.frameAmbient(); return; }
        var ctx = this.ctx;
        if (this.mouse.on) {
            if (!this.hoverText) this.hoverText = this.applyText();
        } else {
            if (this.hoverText) { this.hoverText = false; this.applyShapeAt(this.glyphIndex); this.lastSwitch = ts; }
            if (!this.lastSwitch) this.lastSwitch = ts;
            if (ts - this.lastSwitch > this.SWITCH_MS) {
                this.glyphIndex = (this.glyphIndex + 1) % this.totalShapes();
                this.lastSwitch = this.applyShapeAt(this.glyphIndex) ? ts : (ts - this.SWITCH_MS + 500);
            }
        }
        ctx.clearRect(0, 0, this.W, this.H);

        for (var i = 0; i < this.ambient.length; i++) {
            var a = this.ambient[i];
            a.x += a.vx; a.y += a.vy;
            if (a.x < 0) a.x = this.W; else if (a.x > this.W) a.x = 0;
            if (a.y < 0) a.y = this.H; else if (a.y > this.H) a.y = 0;
            var r = this.repel(a.x, a.y);
            ctx.fillStyle = colorFor(a.t, isDark ? 0.55 : 0.6);
            ctx.beginPath(); ctx.arc(r[0], r[1], 1.7, 0, 6.2832); ctx.fill();
        }

        for (var j = 0; j < this.shapeP.length; j++) {
            var p = this.shapeP[j];
            p.x += (p.tx - p.x) * 0.085;
            p.y += (p.ty - p.y) * 0.085;
            var rr = this.repel(p.x, p.y);
            ctx.fillStyle = this.styleFor(p, 0.95);
            if (this.shapeIsLogo) {
                ctx.fillRect(rr[0], rr[1], 1.8, 1.8);
            } else {
                ctx.beginPath(); ctx.arc(rr[0], rr[1], 2.6, 0, 6.2832); ctx.fill();
            }
        }
    };

    Instance.prototype.drawStatic = function () {
        var ctx = this.ctx;
        if (this.ambientOnly) {
            ctx.clearRect(0, 0, this.W, this.H);
            var ab = isDark ? 0.92 : 0.9;
            for (var s = 0; s < this.shapeP.length; s++) {
                var q = this.shapeP[s], qc = rgbThemed(q.tcol);
                ctx.fillStyle = 'rgba(' + qc[0] + ',' + qc[1] + ',' + qc[2] + ',' + ab + ')';
                ctx.fillRect(q.tX, q.tY, 1.8, 1.8);
            }
            return;
        }
        ctx.clearRect(0, 0, this.W, this.H);
        for (var i = 0; i < this.ambient.length; i++) {
            ctx.fillStyle = colorFor(this.ambient[i].t, isDark ? 0.55 : 0.6);
            ctx.beginPath(); ctx.arc(this.ambient[i].x, this.ambient[i].y, 1.7, 0, 6.2832); ctx.fill();
        }
        for (var j = 0; j < this.shapeP.length; j++) {
            ctx.fillStyle = this.styleFor(this.shapeP[j], 0.95);
            if (this.shapeIsLogo) { ctx.fillRect(this.shapeP[j].tx, this.shapeP[j].ty, 1.8, 1.8); }
            else { ctx.beginPath(); ctx.arc(this.shapeP[j].tx, this.shapeP[j].ty, 2.6, 0, 6.2832); ctx.fill(); }
        }
    };

    // ─────────────────────────── orquestación ───────────────────────────
    var instances = [];
    for (var h = 0; h < hosts.length; h++) {
        var mode = hosts[h].id === 'hero-fx' ? 'full' : 'ambient';
        instances.push(new Instance(hosts[h], mode));
    }

    var raf = null;
    function loop(ts) {
        for (var i = 0; i < instances.length; i++) {
            if (instances[i].visible) instances[i].frame(ts);
        }
        raf = requestAnimationFrame(loop);
    }

    function startInstance(inst) {
        inst.size();
        // headers ambient no animan bajo reduced-motion => sin logo ni dibujo
        if (inst.LOGO_URL && !(inst.ambientOnly && reduce)) inst.loadLogo(inst.LOGO_URL);
        if (reduce) inst.drawStatic();
    }

    function startAll() {
        for (var i = 0; i < instances.length; i++) startInstance(instances[i]);

        if ('IntersectionObserver' in window) {
            var io = new IntersectionObserver(function (entries) {
                for (var k = 0; k < entries.length; k++) {
                    var inst = entries[k].target.__fxInst;
                    if (inst) inst.visible = entries[k].isIntersecting;
                }
            }, { rootMargin: '80px' });
            for (var j = 0; j < instances.length; j++) {
                instances[j].host.__fxInst = instances[j];
                io.observe(instances[j].host);
            }
        }

        if (!reduce) raf = requestAnimationFrame(loop);
    }

    if (doc.fonts && doc.fonts.load) {
        var started = false;
        var go = function () { if (started) return; started = true; startAll(); };
        doc.fonts.load('900 40px "Font Awesome 6 Free"').then(go).catch(go);
        setTimeout(go, 1200);
    } else {
        startAll();
    }

    var rsTimer;
    window.addEventListener('resize', function () {
        clearTimeout(rsTimer);
        rsTimer = setTimeout(function () {
            for (var i = 0; i < instances.length; i++) {
                instances[i].size();
                if (reduce) instances[i].drawStatic();
            }
        }, 200);
    }, { passive: true });
})();
