(function () {
'use strict';
var doc = document, root = doc.documentElement;
var LS_THEME = 'cd2-theme', LS_LANG = 'cd2-lang';
var BASE = root.getAttribute('data-base') || '';
function siteUrl(p) { return BASE + String(p || '').replace(/^\//, ''); }
var $ = function (s, c) { return (c || doc).querySelector(s); };
var $$ = function (s, c) { return Array.prototype.slice.call((c || doc).querySelectorAll(s)); };
function store(k, v) { try { localStorage.setItem(k, v); } catch (e) {} }
function load(k) { try { return localStorage.getItem(k); } catch (e) { return null; } }
var THEMES = ['auto', 'light', 'dark'];
var THEME_LABEL = { auto: '跟随系统', light: '浅色', dark: '深色' };
var THEME_ICON = {
auto: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><rect x="2" y="4" width="20" height="13" rx="2"/><path d="M8 21h8M12 17v4"/></svg>',
light: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="12" r="4.2"/><path d="M12 2v2.4M12 19.6V22M2 12h2.4M19.6 12H22M4.9 4.9l1.7 1.7M17.4 17.4l1.7 1.7M19.1 4.9l-1.7 1.7M6.6 17.4l-1.7 1.7"/></svg>',
dark: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M20 13.4A8.4 8.4 0 1 1 10.6 4a6.9 6.9 0 0 0 9.4 9.4z"/></svg>'
};
function mq() { return matchMedia('(prefers-color-scheme: light)'); }
function themePref() { var p = load(LS_THEME); return THEMES.indexOf(p) >= 0 ? p : 'auto'; }
function applyTheme(p) {
root.setAttribute('data-theme', p === 'auto' ? (mq().matches ? 'light' : 'dark') : p);
$$('[data-theme-btn]').forEach(function (b) {
b.innerHTML = THEME_ICON[p];
b.setAttribute('aria-label', '主题：' + THEME_LABEL[p] + '（点击切换）');
b.title = '主题：' + THEME_LABEL[p];
});
}
function cycleTheme() {
var p = themePref();
p = THEMES[(THEMES.indexOf(p) + 1) % THEMES.length];
store(LS_THEME, p); applyTheme(p);
}
applyTheme(themePref());
doc.addEventListener('click', function (e) {
var b = e.target.closest && e.target.closest('[data-theme-btn]');
if (b) { e.preventDefault(); cycleTheme(); }
});
try {
var onSys = function () { if (themePref() === 'auto') applyTheme('auto'); };
if (mq().addEventListener) mq().addEventListener('change', onSys);
else if (mq().addListener) mq().addListener(onSys);
} catch (e) {}
function langPref() { return load(LS_LANG) === 'zh' ? 'zh' : 'both'; }
function applyLang(v) {
root.setAttribute('data-lang', v);
$$('[data-lang-btn]').forEach(function (b) {
b.setAttribute('aria-pressed', String(b.getAttribute('data-lang-btn') === v));
});
}
applyLang(langPref());
doc.addEventListener('click', function (e) {
var b = e.target.closest && e.target.closest('[data-lang-btn]');
if (!b) return;
e.preventDefault();
var v = b.getAttribute('data-lang-btn');
store(LS_LANG, v); applyLang(v);
});
(function () {
var drawer = $('#drawer'), overlay = $('#drawer-overlay'), btn = $('#drawer-btn');
if (!drawer) return;
var lastFocus = null;
function setOpen(v) {
drawer.classList.toggle('open', v);
if (overlay) overlay.classList.toggle('open', v);
if (btn) btn.setAttribute('aria-expanded', String(v));
doc.body.style.overflow = v ? 'hidden' : '';
if (v) { lastFocus = doc.activeElement; var f = drawer.querySelector('a,button'); if (f) f.focus(); }
else if (lastFocus && lastFocus.focus) lastFocus.focus();
}
if (btn) btn.addEventListener('click', function () { setOpen(!drawer.classList.contains('open')); });
if (overlay) overlay.addEventListener('click', function () { setOpen(false); });
doc.addEventListener('keydown', function (e) { if (e.key === 'Escape') setOpen(false); });
$$('#drawer a').forEach(function (a) { a.addEventListener('click', function () { setOpen(false); }); });
})();
var copiedTimer = [];
function copy(text) {
if (navigator.clipboard && navigator.clipboard.writeText) {
return navigator.clipboard.writeText(text).catch(function () { return legacyCopy(text); });
}
return Promise.resolve(legacyCopy(text));
}
function legacyCopy(text) {
var ta = doc.createElement('textarea');
ta.value = text; ta.setAttribute('readonly', '');
ta.style.cssText = 'position:fixed;top:-1000px;opacity:0';
doc.body.appendChild(ta); ta.select();
try { doc.execCommand('copy'); } catch (e) {}
doc.body.removeChild(ta);
}
(function highlight() {
var esc = function (s) { return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;'); };
var RE = /("(?:[^"\\]|\\.)*")(\s*:)?|(\b\d+(?:\.\d+)?\b)|(\b(?:true|false)\b)|(\bnull\b)/g;
function hl(raw) {
return esc(raw).replace(RE, function (m, str, col, num, bool, nul) {
if (str) return col ? '<span class="hl-attr">' + str + '</span>' + col
: '<span class="hl-string">' + str + '</span>';
if (num) return '<span class="hl-number">' + m + '</span>';
if (bool || nul) return '<span class="hl-literal">' + m + '</span>';
return m;
});
}
$$('.code-block pre code').forEach(function (c) {
if (c.querySelector('span')) return;
var raw = c.textContent;
if (raw && raw.indexOf('"') !== -1) c.innerHTML = hl(raw);
});
})();
doc.addEventListener('click', function (e) {
var b = e.target.closest && e.target.closest('.copy-btn');
if (!b) return;
var block = b.closest('.code-block') || b.closest('figure');
var pre = block && block.querySelector('pre');
if (!pre) return;
var text = pre.textContent;
copy(text).then(function () {
b.textContent = '已复制'; b.classList.add('done');
clearTimeout(copiedTimer[0]);
copiedTimer[0] = setTimeout(function () {
b.textContent = '复制'; b.classList.remove('done');
}, 1500);
});
});
(function () {
var toc = $('.toc-list');
if (!toc) return;
var links = $$('a', toc);
var subs = $$('li.lvl-3[data-p]', toc);
var map = {}, heads = [];
links.forEach(function (a) {
var id = (a.getAttribute('href') || '').slice(1);
var h = id && doc.getElementById(id);
if (h) { map[id] = a; heads.push(h); }
});
if (!heads.length || !('IntersectionObserver' in window)) return;
var visible = {};
var io = new IntersectionObserver(function (entries) {
entries.forEach(function (en) {
visible[en.target.id] = en.isIntersecting ? en.boundingClientRect.top : null;
});
var best = null, bestTop = Infinity;
heads.forEach(function (h) {
var t = visible[h.id];
if (t !== null && t !== undefined && t >= -40 && t < bestTop) { bestTop = t; best = h.id; }
});
if (!best) {
for (var i = heads.length - 1; i >= 0; i--) {
if (heads[i].getBoundingClientRect().top < 120) { best = heads[i].id; break; }
}
}
links.forEach(function (a) { a.classList.remove('current'); });
if (map[best]) map[best].classList.add('current');
var grp = '';
if (map[best]) {
var pli = map[best].parentNode;
grp = pli.getAttribute('data-h') || pli.getAttribute('data-p') || '';
}
subs.forEach(function (li) {
li.classList.toggle('show', !!grp && li.getAttribute('data-p') === grp);
});
if (map[best]) {
var box = toc.getBoundingClientRect(), lb = map[best].getBoundingClientRect();
if (lb.top < box.top || lb.bottom > box.bottom) {
toc.scrollTo({
top: toc.scrollTop + (lb.top - box.top) - toc.clientHeight / 2 + lb.height / 2,
behavior: 'smooth'
});
}
}
}, { rootMargin: '-20% 0px -70% 0px', threshold: [0, 1] });
heads.forEach(function (h) { io.observe(h); });
})();
(function () {
var panel = $('#search-panel'), slot = $('#search-slot');
if (!panel || !slot) return;
var input = $('#search-input'), list = $('#search-results');
var btn = $('[data-search-open]', slot);
var SUGGEST = [
['新手入门 · Getting Started', 'tutorial/'],
['常见修改 · Cookbook', 'common-edits/'],
['案例拆解 · Case Study', 'natural-selection/'],
['为什么没生效 · Debug', 'tips/'],
['Reference · 目录', 'toc/']
];
var data = null, index = null, loading = false, SECTIONS = [];
var CACHE = [];
var BDATA = {}, BYPATH = {};
var BLK_READY = false, BLK_LOADING = false;
function terms(s) {
s = (s || '').toLowerCase();
var out = [];
(s.match(/[a-z0-9_]{2,}/g) || []).forEach(function (w) { out.push(w); });
(s.match(/[\u4e00-\u9fff]+/g) || []).forEach(function (run) {
if (run.length === 1) out.push(run);
for (var i = 0; i + 2 <= run.length; i++) out.push(run.substr(i, 2));
});
return out;
}
function build() {
index = {};
SECTIONS = [];
BYPATH = {};
data.forEach(function (pg, pi) {
BYPATH[pg.path] = pg;
var seen = {};
var push = function (t) { if (!seen[t]) { seen[t] = 1; (index[t] = index[t] || []).push(pi); } };
terms(pg.text + ' ' + (pg.kw || '')).forEach(push);
(pg.headings || []).forEach(function (h) {
if (h.text) SECTIONS.push({ pi: pi, id: h.id, level: h.level, text: h.text, page: pg });
});
});
}
function search(q) {
var ql = q.toLowerCase();
var perPage = {}, secOut = [];
SECTIONS.forEach(function (s) {
if ((s.text || '').toLowerCase().indexOf(ql) < 0) return;
if ((perPage[s.pi] || 0) >= 3) return;
perPage[s.pi] = (perPage[s.pi] || 0) + 1;
secOut.push(s);
});
var out = secOut.slice(0, 12).map(function (s) {
return { type: 'section', title: s.text, path: s.page.path, id: s.id, page: s.page };
});
if (out.length >= 12) return out;
var paths = Object.keys(BDATA), per = {};
for (var i = 0; i < paths.length && out.length < 12; i++) {
var arr = BDATA[paths[i]] || [];
for (var k = 0; k < arr.length; k++) {
if (arr[k][1].toLowerCase().indexOf(ql) < 0) continue;
if ((per[paths[i]] || 0) >= 2) break;
per[paths[i]] = (per[paths[i]] || 0) + 1;
out.push({ type: 'block', a: arr[k][0], text: arr[k][1],
path: paths[i], page: BYPATH[paths[i]] });
if (out.length >= 12) break;
}
}
if (out.length >= 12) return out;
var ts = terms(q), ids = [];
if (ts.length) {
var hit = null;
ts.forEach(function (t) {
var s = {};
(index[t] || []).forEach(function (i) { s[i] = 1; });
hit = hit === null ? s : Object.keys(hit).reduce(function (o, k) { if (s[k]) o[k] = 1; return o; }, {});
});
ids = Object.keys(hit || {});
if (!ids.length) {
ids = data.map(function (p, i) { return i; }).filter(function (i) {
return (data[i].text + data[i].title).toLowerCase().indexOf(ql) >= 0;
});
}
}
ids.forEach(function (i) {
if (out.length >= 12) return;
var pg = data[i];
if (out.some(function (r) { return r.type === 'page' && r.path === pg.path; })) return;
out.push({ type: 'page', title: pg.title_zh || pg.title, path: pg.path, page: pg });
});
return out.slice(0, 12);
}
function snippet(t, q) {
t = t || '';
var ql = q.toLowerCase(), i = t.toLowerCase().indexOf(ql);
if (i < 0) return t.slice(0, 90);
var a = Math.max(0, i - 34), b = Math.min(t.length, i + ql.length + 56);
return (a ? '…' : '') + t.slice(a, b).replace(/\n/g, ' ') + (b < t.length ? '…' : '');
}
function render(results, q) {
if (!results.length) {
list.innerHTML = '<li class="empty-state">没有找到与「' + esc(q) + '」相关的内容</li>';
return;
}
list.innerHTML = results.map(function (r, i) {
var isSec = r.type === 'section', isBlk = r.type === 'block';
var href = siteUrl(r.path) + (isBlk
? '?q=' + encodeURIComponent(q) + '#' + r.a
: (r.id ? '#' + r.id : ''));
var pt = r.page ? (r.page.title_zh || r.page.title) : r.path;
var sub = (isSec || isBlk) ? pt : r.path;
var sn = isBlk ? snippet(r.text, q) : (r.type === 'page' ? snippet(r.page.text, q) : '');
var mark = function (s) {
if (!q) return esc(s);
return esc(s).replace(new RegExp(escRe(q), 'ig'), function (m) { return '<mark>' + m + '</mark>'; });
};
if (sn) {
sn = esc(sn).replace(new RegExp(escRe(q), 'ig'), function (m) { return '\u0001' + m + '\u0002'; });
sn = sn.replace(/\u0001/g, '<mark>').replace(/\u0002/g, '</mark>');
}
return '<li><a href="' + href + '"' + (i === 0 ? ' class="active"' : '') + '>' +
'<span class="sr-title">' + mark(isBlk ? pt : r.title) +
(isSec ? '<span class="sr-badge">章节</span>'
: (isBlk ? '<span class="sr-badge">正文</span>' : '')) + '</span>' +
'<span class="sr-path">' + esc(sub) + '</span>' +
(sn ? '<div class="sr-snippet">' + sn + '</div>' : '') + '</a></li>';
}).join('');
}
function esc(s) { return (s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;'); }
function escRe(s) { return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'); }
function showSuggest() {
list.innerHTML = SUGGEST.map(function (s, i) {
return '<li><a href="' + siteUrl('/' + s[1]) + '"' + (i === 0 ? ' class="active"' : '') +
'><span class="sr-title">' + esc(s[0]) + '</span>' +
'<span class="sr-path">常用入口</span></a></li>';
}).join('');
}
function open() {
panel.hidden = false;
if (btn) btn.setAttribute('aria-expanded', 'true');
input.value = '';
showSuggest();
input.focus();
if (data || loading) return;
loading = true;
list.innerHTML = '<li class="empty-state">正在载入索引…</li>';
fetch(siteUrl('/search-index.json')).then(function (r) { return r.json(); })
.then(function (j) {
data = j; build(); loading = false;
var q = input.value.trim();
if (q) render(search(q), q); else showSuggest();
}).catch(function () {
loading = false;
list.innerHTML = '<li class="empty-state">索引载入失败</li>';
});
}
function loadBlocks() {
if (BLK_READY || BLK_LOADING) return;
BLK_LOADING = true;
fetch(siteUrl('/search-blocks.json')).then(function (r) { return r.json(); })
.then(function (j) {
BDATA = j || {}; BLK_READY = true; BLK_LOADING = false;
var q = input.value.trim();
if (q) render(search(q), q);
}).catch(function () { BLK_LOADING = false; });
}
function close() {
panel.hidden = true;
if (btn) btn.setAttribute('aria-expanded', 'false');
}
list.addEventListener('click', function (e) {
if (e.target.closest && e.target.closest('a')) close();
});
function move(d) {
var as = $$('a', list);
if (!as.length) return;
var i = as.findIndex(function (a) { return a.classList.contains('active'); });
i = Math.max(0, Math.min(as.length - 1, (i < 0 ? 0 : i) + d));
as.forEach(function (a) { a.classList.remove('active'); });
as[i].classList.add('active');
as[i].scrollIntoView({ block: 'nearest' });
}
doc.addEventListener('click', function (e) {
var t = e.target;
if (t.closest && t.closest('[data-search-open]')) {
e.preventDefault();
if (panel.hidden) open(); else close();
return;
}
if (!panel.hidden && t.closest && !t.closest('#search-slot')) close();
});
doc.addEventListener('keydown', function (e) {
if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') { e.preventDefault(); open(); return; }
if (panel.hidden) return;
if (e.key === 'Escape') close();
else if (e.key === 'ArrowDown') { e.preventDefault(); move(1); }
else if (e.key === 'ArrowUp') { e.preventDefault(); move(-1); }
else if (e.key === 'Enter') {
var a = $('a.active', list);
if (a) { close(); location.href = a.getAttribute('href'); }
}
});
var timer = null;
input.addEventListener('input', function () {
var q = input.value.trim();
if (q) loadBlocks();
clearTimeout(timer);
timer = setTimeout(function () {
if (!q) { showSuggest(); return; }
if (!data) return;
render(search(q), q);
}, 90);
});
})();
(function () {
var bar = $('#read-progress'), top = $('#to-top');
if (!bar && !top) return;
var ticking = false;
function update() {
ticking = false;
var el = doc.documentElement;
var max = el.scrollHeight - el.clientHeight;
var y = el.scrollTop || doc.body.scrollTop || 0;
if (bar) bar.style.width = (max > 0 ? (y / max) * 100 : 0).toFixed(2) + '%';
if (top) top.classList.toggle('show', y > 600);
}
addEventListener('scroll', function () {
if (ticking) return;
ticking = true;
requestAnimationFrame(update);
}, { passive: true });
addEventListener('resize', update, { passive: true });
if (top) top.addEventListener('click', function () {
scrollTo({ top: 0, behavior: 'smooth' });
});
update();
})();
(function () {
var settled = false;
function go() {
if (!location.hash) return;
var el;
try { el = doc.getElementById(decodeURIComponent(location.hash.slice(1))); }
catch (e) { el = doc.getElementById(location.hash.slice(1)); }
if (el) el.scrollIntoView();
}
addEventListener('load', function () {
setTimeout(function () { if (!settled) go(); }, 80);
});
addEventListener('wheel', function () { settled = true; }, { passive: true });
addEventListener('touchmove', function () { settled = true; }, { passive: true });
go();
addEventListener('hashchange', go);
})();
(function () {
var back = $('#jump-back');
if (!back) return;
if (history.length > 1) back.hidden = false;
back.addEventListener('click', function () { history.back(); });
})();
(function () {
var drawer = $('#drawer'), cur = $('#drawer .drawer-list a.current');
if (!drawer || !cur) return;
var d = drawer.getBoundingClientRect(), c = cur.getBoundingClientRect();
if (c.top < d.top || c.bottom > d.bottom) {
drawer.scrollTop += (c.top - d.top) - (d.height - c.height) / 2;
}
})();
(function () {
var box = $('#mut-filter');
if (!box) return;
var cards = $$('.mut-idx details.mut-card');
if (!cards.length) return;
box.addEventListener('input', function () {
var q = box.value.trim().toLowerCase();
cards.forEach(function (c) {
var n = 0;
$$('.mut-chip', c).forEach(function (a) {
var hit = !q || a.textContent.toLowerCase().indexOf(q) >= 0;
a.parentNode.hidden = !hit;
if (hit) n++;
});
c.hidden = !n;
if (q && n) c.open = true;
});
});
})();
(function () {
function run() {
var m = /[?&]q=([^&]*)/.exec(location.search || '');
var raw = (location.hash || '').slice(1);
var aid = raw;
try { aid = decodeURIComponent(raw); } catch (e) {}
if (!m || !aid) return;
var el = doc.getElementById(aid);
var term = decodeURIComponent(m[1]);
if (!el || !term) return;
for (var d = el; d; d = d.parentElement) {
if (d.tagName === 'DETAILS' && !d.open) d.open = true;
}
var mk = el.querySelector('mark.hit');
if (!mk) {
var tl = term.toLowerCase(), w = doc.createTreeWalker(el, NodeFilter.SHOW_TEXT, null), n;
while ((n = w.nextNode())) {
var i = n.nodeValue.toLowerCase().indexOf(tl);
if (i < 0) continue;
var r = doc.createRange();
r.setStart(n, i);
r.setEnd(n, i + term.length);
mk = doc.createElement('mark');
mk.className = 'hit';
try { r.surroundContents(mk); } catch (e) { return; }
break;
}
}
if (mk) setTimeout(function () { mk.scrollIntoView({ block: 'center' }); }, 0);
}
run();
addEventListener('hashchange', run);
addEventListener('load', run);
})();
})();
