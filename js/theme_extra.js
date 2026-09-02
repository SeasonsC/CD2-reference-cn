/*
 * Assign 'docutils' class to tables so styling and
 * JavaScript behavior is applied.
 *
 * https://github.com/mkdocs/mkdocs/issues/2028
 */

$('div.rst-content table').addClass('docutils');

/*
 * 右侧“本页目录”：从文章 h2/h3 生成一个独立的目录栏。
 * 独立滚动（position: fixed + overflow-y: auto），点击链接只让正文跳到锚点，
 * 目录栏不发生自动跳动（方案A 效果）。
 */
(function () {
  var content = document.querySelector('.rst-content');
  if (!content) return;
  var heads = content.querySelectorAll('h2[id], h3[id]');
  if (heads.length < 2) return;

  var root = document.querySelector('.ds-toc');
  if (!root) {
    root = document.createElement('div');
    root.className = 'ds-toc';
    document.body.appendChild(root);
  }

  var box = document.createElement('nav');
  box.className = 'ds-toc-inner';

  var label = document.createElement('h4');
  label.textContent = '本页目录';
  box.appendChild(label);

  var ul = document.createElement('ul');
  Array.prototype.forEach.call(heads, function (h) {
    var li = document.createElement('li');
    if (h.tagName === 'H3') li.className = 'toc-l3';
    var a = document.createElement('a');
    a.href = '#' + h.id;
    var raw = (h.textContent || '').replace(/\s+/g, ' ').trim();
    // ③ 右侧目录：把“(...中文...)”/“（...中文...）”改写成“「...中文...」”
    var fmt = raw.replace(/\(([^()\n]*[\u4e00-\u9fff][^()\n]*)\)/g, '「$1」')
                 .replace(/（([^（）\n]*[\u4e00-\u9fff][^（）\n]*)）/g, '「$1」');
    // 特别长的条目：让中文翻译另起一行（在第一个「中文」前插入换行）
    var beforeGloss = fmt.split('「')[0];
    if (fmt.indexOf('「') !== -1 && beforeGloss.trim().length >= 20) {
      fmt = fmt.replace('「', '<br>「');
    }
    a.setAttribute('title', raw);
    a.innerHTML = fmt;
    li.appendChild(a);
    ul.appendChild(li);
  });
  box.appendChild(ul);
  root.appendChild(box);
  // 只有真的生成了目录，才让页面预留右侧空间 / 隐藏左侧二三级
  if (document.body) document.body.classList.add('ds-has-toc');
})();

/*
 * 代码块高亮（方案A）：原生 JS 轻量分色，不依赖任何第三方库。
 * 对 <pre><code> 里的 JSON 做：键=蓝、字符串=绿、数字=橙、布尔/null=紫。
 */
(function () {
  function esc(s) { return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;'); }
  function hl(raw) {
    var e = esc(raw);
    return e.replace(/("(?:[^"\\]|\\.)*")(\s*:)?|(\b\d+(?:\.\d+)?\b)|(\b(?:true|false)\b)|(\bnull\b)/g, function (m, str, col, num, bool, nul) {
      if (str) { return col ? '<span class="hljs-attr">' + str + '</span>' + col : '<span class="hljs-string">' + str + '</span>'; }
      if (num) { return '<span class="hljs-number">' + m + '</span>'; }
      if (bool || nul) { return '<span class="hljs-literal">' + m + '</span>'; }
      return m;
    });
  }
  document.querySelectorAll('.rst-content pre code').forEach(function (c) {
    if (c.querySelector('span')) return;      // 已高亮则跳过
    var raw = c.textContent;
    if (raw && raw.indexOf('"') !== -1) { c.innerHTML = hl(raw); }
  });
})();

/*
 * ① 左侧导航：所有页面默认收起（无痕迹），鼠标靠近左缘（≤30px）自动展开 300px；
 * 鼠标移离侧边栏（>360px）且空闲 700ms 后收起。
 * 有右侧目录（body.ds-has-toc）时，展开会隐藏右侧目录（互斥）。
 */
(function () {
  var open = false, timer = null;
  function setOpen(v) {
    if (open === v) return;
    open = v;
    document.body.classList.toggle('ds-nav-open', v);
  }
  document.addEventListener('mousemove', function (e) {
    if (e.clientX <= 30) { clearTimeout(timer); setOpen(true); return; }
    if (open && e.clientX > 360) {
      clearTimeout(timer);
      timer = setTimeout(function () { setOpen(false); }, 700);
    }
  });
})();

/*
 * 主题切换（浅色/深色/跟随系统）：控件注入到左侧边栏底部。
 * data-theme 已由 <head> 里的早期脚本按偏好设好；这里负责控件与交互。
 */
(function () {
  function pref() { try { return localStorage.getItem('ds-theme') || 'auto'; } catch (e) { return 'auto'; } }
  function resolved(p) {
    if (p === 'light' || p === 'dark') return p;
    return matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark';
  }
  function apply(p) { document.documentElement.setAttribute('data-theme', resolved(p)); }

  var root = document.querySelector('.wy-side-scroll') || document.querySelector('.wy-nav-side');
  if (!root) return;

  var sw = document.createElement('div');
  sw.className = 'ds-theme-switch';
  var label = document.createElement('span');
  label.className = 'ds-label';
  label.textContent = '主题';
  sw.appendChild(label);

  var modes = [['auto', '跟随系统'], ['light', '浅色'], ['dark', '深色']];
  var btns = {};
  modes.forEach(function (m) {
    var b = document.createElement('button');
    b.textContent = m[1];
    b.setAttribute('data-mode', m[0]);
    sw.appendChild(b);
    btns[m[0]] = b;
  });
  root.appendChild(sw);

  function sync() {
    var p = pref();
    for (var k in btns) if (Object.prototype.hasOwnProperty.call(btns, k)) btns[k].classList.toggle('active', k === p);
  }
  sw.addEventListener('click', function (e) {
    var b = e.target && e.target.closest ? e.target.closest('button') : null;
    if (!b) return;
    var m = b.getAttribute('data-mode');
    try { localStorage.setItem('ds-theme', m); } catch (err) {}
    apply(m);
    sync();
  });
  sync();

  // 跟随系统：系统主题变化时自动更新
  try {
    var mq = matchMedia('(prefers-color-scheme: light)');
    var onChange = function () { if (pref() === 'auto') apply('auto'); };
    if (mq.addEventListener) mq.addEventListener('change', onChange);
    else if (mq.addListener) mq.addListener(onChange);
  } catch (e) {}
})();


