/* ==========================================================================
   CD2 参考文档 · 全站脚本（原生 JS，零依赖）
   按施工方案 v2.1 §7 实现：
     主题切换 / 语言开关 / 抽屉 / scrollspy / 章节筛选 /
     代码高亮 + 复制 / 标题锚点复制 / 搜索模态框
   ========================================================================== */
(function () {
  'use strict';

  var doc = document, root = doc.documentElement;
  var LS_THEME = 'cd2-theme', LS_LANG = 'cd2-lang';
  /* 改进清单 §1：站点用相对路径，页面深度前缀由渲染器写在 <html data-base> */
  var BASE = root.getAttribute('data-base') || '';
  function siteUrl(p) { return BASE + String(p || '').replace(/^\//, ''); }
  var $ = function (s, c) { return (c || doc).querySelector(s); };
  var $$ = function (s, c) { return Array.prototype.slice.call((c || doc).querySelectorAll(s)); };
  function store(k, v) { try { localStorage.setItem(k, v); } catch (e) {} }
  function load(k) { try { return localStorage.getItem(k); } catch (e) { return null; } }

  /* ── 1. 主题切换（跟随系统 / 浅色 / 深色）──────────────────────────── */
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

  /* ── 2. 语言开关（中 / 中+英；代码永远英文）────────────────────────── */
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

  /* ── 3. 抽屉导航 ─────────────────────────────────────────────────── */
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

  /* ── 4. 复制工具 + 代码块高亮 / 复制 ─────────────────────────────── */
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

  /* ── 5. 右侧目录 scrollspy ───────────────────────────────────────── */
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

      /* R10：右侧目录「有次级标题的默认收起」—— 滚到哪一节，就只展开哪一节的次级条目 */
      var grp = '';
      if (map[best]) {
        var pli = map[best].parentNode;
        grp = pli.getAttribute('data-h') || pli.getAttribute('data-p') || '';
      }
      subs.forEach(function (li) {
        li.classList.toggle('show', !!grp && li.getAttribute('data-p') === grp);
      });

      if (map[best]) {
        /* 改进清单 §5：只滚目录容器自身，绝不动主窗口 */
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

  /* ── 6. 章节筛选：已移除（R5 ③ 全站只保留顶栏那一个搜索入口）──────── */

  /* ── 7. 搜索（内置轻量版：bigram 倒排 + 子串兜底）─────────────────── */
  (function () {
    var modal = $('#search-modal');
    if (!modal) return;
    var input = $('#search-input'), list = $('#search-results');
    var data = null, index = null, loading = false, SECTIONS = [];
    var CACHE = [];

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
      data.forEach(function (pg, pi) {
        var seen = {};
        var push = function (t) { if (!seen[t]) { seen[t] = 1; (index[t] = index[t] || []).push(pi); } };
        terms(pg.text).forEach(push);                       // 章节标题不进页面级索引
        (pg.headings || []).forEach(function (h) {          // 它们走章节级结果（§4）
          if (h.text) SECTIONS.push({ pi: pi, id: h.id, level: h.level, text: h.text, page: pg });
        });
      });
    }
    /* 改进清单 §4：命中标题 → 章节级结果（带锚点）；命中正文 → 页面级结果 */
    function search(q) {
      var ql = q.toLowerCase();
      var perPage = {}, secOut = [];
      SECTIONS.forEach(function (s) {
        if ((s.text || '').toLowerCase().indexOf(ql) < 0) return;
        if ((perPage[s.pi] || 0) >= 3) return;              // 同页最多 3 条，避免 direct 刷屏
        perPage[s.pi] = (perPage[s.pi] || 0) + 1;
        secOut.push(s);
      });
      var out = secOut.slice(0, 12).map(function (s) {
        return { type: 'section', title: s.text, path: s.page.path, id: s.id, page: s.page };
      });
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
        if (!ids.length) {                                   // 子串兜底
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
    function snippet(pg, q) {
      var t = pg.text || '', ql = q.toLowerCase(), i = t.toLowerCase().indexOf(ql);
      if (i < 0) return t.slice(0, 90);
      var a = Math.max(0, i - 34), b = Math.min(t.length, i + ql.length + 56);
      return (a ? '…' : '') + t.slice(a, b).replace(/\n/g, ' ') + (b < t.length ? '…' : '');
    }
    function render(results, q) {
      if (!results.length) {
        list.innerHTML = '<li class="empty-state">没有匹配「' + esc(q) + '」的内容</li>';
        return;
      }
      list.innerHTML = results.map(function (r, i) {
        var href = siteUrl(r.path) + (r.id ? '#' + r.id : '');
        /* R3 §2.2：章节结果副行显示所属页面中文名，不暴露 #hash */
        var sub = r.type === 'section' ? (r.page.title_zh || r.page.title) : r.path;
        var sn = r.type === 'page' ? snippet(r.page, q) : '';
        var mark = function (s) {
          if (!q) return esc(s);
          return esc(s).replace(new RegExp(escRe(q), 'ig'), function (m) { return '<mark>' + m + '</mark>'; });
        };
        if (sn) {
          sn = esc(sn).replace(new RegExp(escRe(q), 'ig'), function (m) { return '\u0001' + m + '\u0002'; });
          sn = sn.replace(/\u0001/g, '<mark>').replace(/\u0002/g, '</mark>');
        }
        return '<li><a href="' + href + '"' + (i === 0 ? ' class="active"' : '') + '>' +
          '<span class="sr-title">' + mark(r.title) +
          (r.type === 'section' ? '<span class="sr-badge">章节</span>' : '') + '</span>' +
          '<span class="sr-path">' + esc(sub) + '</span>' +
          (sn ? '<div class="sr-snippet">' + sn + '</div>' : '') + '</a></li>';
      }).join('');
    }
    function esc(s) { return (s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;'); }
    function escRe(s) { return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'); }

    function open() {
      modal.hidden = false; input.value = ''; list.innerHTML = '';
      input.focus();
      if (data) return;
      if (loading) return;
      loading = true;
      list.innerHTML = '<li class="empty-state">正在载入索引…</li>';
      fetch(siteUrl('/search-index.json')).then(function (r) { return r.json(); }).then(function (j) {
        data = j; build(); loading = false;
        list.innerHTML = '<li class="empty-state">输入关键词开始搜索</li>';
      }).catch(function () {
        loading = false;
        list.innerHTML = '<li class="empty-state">索引载入失败</li>';
      });
    }
    function close() { modal.hidden = true; }
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
      if (e.target.closest && e.target.closest('[data-search-open]')) { e.preventDefault(); open(); }
      else if (e.target === modal) close();
    });
    doc.addEventListener('keydown', function (e) {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') { e.preventDefault(); open(); return; }
      if (modal.hidden) return;
      if (e.key === 'Escape') close();
      else if (e.key === 'ArrowDown') { e.preventDefault(); move(1); }
      else if (e.key === 'ArrowUp') { e.preventDefault(); move(-1); }
      else if (e.key === 'Enter') { var a = $('a.active', list); if (a) location.href = a.getAttribute('href'); }
    });
    var timer = null;
    input.addEventListener('input', function () {
      var q = input.value.trim();
      clearTimeout(timer);
      timer = setTimeout(function () {
        if (!q) { list.innerHTML = '<li class="empty-state">输入关键词开始搜索</li>'; return; }
        if (!data) return;
        render(search(q), q);
      }, 90);
    });
  })();

  /* ── 8. 阅读进度条 + 返回顶部（R4 §8.1 §8.5）────────────────────── */
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

  /* ── 9. 滚动到 hash（深链落点校正）───────────────────────────────── */
  (function () {
    var settled = false;                     // 用户一旦自己滚动就不再校正
    function go() {
      if (!location.hash) return;
      var el;
      try { el = doc.getElementById(decodeURIComponent(location.hash.slice(1))); }
      catch (e) { el = doc.getElementById(location.hash.slice(1)); }
      if (el) el.scrollIntoView();
    }
    // 重页面（modules 有 92 张表）在初次滚动后仍会被后续布局顶走，
    // 因此 load 之后再校正一次，保证深链落点准确。
    addEventListener('load', function () {
      setTimeout(function () { if (!settled) go(); }, 80);
    });
    addEventListener('wheel', function () { settled = true; }, { passive: true });
    addEventListener('touchmove', function () { settled = true; }, { passive: true });
    go();
    addEventListener('hashchange', go);
  })();
})();
