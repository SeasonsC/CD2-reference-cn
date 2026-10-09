# -*- coding: utf-8 -*-
"""自检：内链 / 锚点 / 图片 / 结构 / 相对路径 / 预算。按改进清单 §1 支持相对路径。"""
import os, io, re, posixpath
import urllib.parse
import json
import html as H
from lxml import html as LH

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(ROOT, 'docs')
OUT = os.path.join(ROOT, 'tools', 'verify_report.txt')
# 预算上限（字节）。R16：CSS 从 30,720 抬到 32,768 —— 搜索面板 + Mutators 卡片索引
# 是真实功能增长，靠清理死规则腾不出空间（全站只剩一条不可删的 .ns-impl 规则）。
# R17：JS 从 20,480 抬到 28,672 —— 块级搜索（块锚点 + 落地高亮）是新增能力。
CSS_MAX, JS_MAX = 32768, 28672
L = []
P = L.append

pages = []
for dirpath, dirnames, filenames in os.walk(SITE):
    if any(x in dirpath for x in ('\\assets', '\\.git')):
        continue
    for f in filenames:
        if f.endswith('.html'):
            pages.append(os.path.join(dirpath, f))
pages.sort()


def resolve(page_rel, href):
    """把 href 解析成站点内路径（'/' 开头），非站内返回 None。"""
    if href.startswith('#') or re.match(r'^[a-z][a-z0-9+.-]*:', href, re.I) or href.startswith('//'):
        return None
    base = posixpath.dirname(page_rel)
    p = posixpath.normpath(posixpath.join(base, href.split('#')[0].split('?')[0]))
    return '/' + p.lstrip('/') if not p.startswith('..') else None


errors, warns = [], []
tot_fold = tot_code = 0
abs_links = 0
xref_bad = []                 # R11：跨页锚点缺失（含目标页自身不存在的 id）


def page_key(rel):
    """页面相对路径 → 站点内路径键（与 resolve() 的返回值对齐）。"""
    if rel == 'index.html':
        return '/'
    if rel.endswith('/index.html'):
        return '/' + rel[:-len('/index.html')]
    return '/' + rel


# 先收集所有页面的 id 集合，供跨页锚点检查用（需要区分大小写）
PAGE_IDS = {}
for fp in pages:
    rel = os.path.relpath(fp, SITE).replace('\\', '/')
    d = LH.fromstring(io.open(fp, encoding='utf-8').read().encode('utf-8'))
    PAGE_IDS[page_key(rel)] = {e.get('id') for e in d.xpath('//*[@id]')}

for fp in pages:
    rel = os.path.relpath(fp, SITE).replace('\\', '/')
    raw = io.open(fp, encoding='utf-8').read()
    doc = LH.fromstring(raw.encode('utf-8'))
    ids = {e.get('id') for e in doc.xpath('//*[@id]')}
    h1 = doc.xpath('//h1')
    if len(h1) != 1:
        errors.append(f'{rel}: h1 数量 {len(h1)}')
    if (doc.get('lang') or '') != 'zh-CN':
        errors.append(f'{rel}: lang={doc.get("lang")!r}')
    is404 = rel == '404.html'
    for a in doc.xpath('//a[@href]'):
        h = a.get('href')
        if not h:
            continue
        if h.startswith('#'):
            if h != '#' and urllib.parse.unquote(h[1:]) not in ids:
                errors.append(f'{rel}: 锚点 #{h[1:]} 不存在')
            continue
        if re.match(r'^[a-z][a-z0-9+.-]*:', h, re.I) or h.startswith('//'):
            continue
        if h.startswith('/'):
            if not is404:
                abs_links += 1
                errors.append(f'{rel}: 站内链接仍是根绝对路径 {h}')
            continue
        t = resolve(rel, h)
        if t is None:
            errors.append(f'{rel}: 链接越出站点根 {h}')
            continue
        dst = os.path.join(SITE, t.strip('/').replace('/', os.sep))
        if not os.path.exists(dst) and not os.path.exists(os.path.join(dst, 'index.html')):
            errors.append(f'{rel}: 内链目标缺失 {h} → {t}')
        # R11：跨页锚点也要真的存在（同页锚点在上面已查过）
        if '#' in h:
            frag = urllib.parse.unquote(h.split('#', 1)[1])
            if frag and t in PAGE_IDS and frag not in PAGE_IDS[t]:
                xref_bad.append(f'{rel}: 跨页锚点缺失 {h} → {t}#{frag}')
    for im in doc.xpath('//img[@src]'):
        s = im.get('src')
        if s.startswith('/'):
            if not is404:
                errors.append(f'{rel}: 图片仍是根绝对路径 {s}')
            continue
        t = resolve(rel, s)
        if t and not os.path.exists(os.path.join(SITE, t.strip('/').replace('/', os.sep))):
            errors.append(f'{rel}: 图片缺失 {s} → {t}')
        if not (im.get('width') and im.get('height')):
            warns.append(f'{rel}: 图片缺 width/height {s}')
        if im.get('loading') != 'lazy' and not im.xpath('ancestor::header'):
            warns.append(f'{rel}: 图片缺 loading=lazy {s}')
    ncode = len(doc.xpath('//div[@class="code-block"]'))
    nbtn = len(doc.xpath('//div[@class="code-block"]//button[@class="copy-btn"]'))
    tot_code += ncode
    tot_fold += len(doc.xpath('//details[@class="orig"]'))
    if ncode != nbtn:
        errors.append(f'{rel}: 代码块 {ncode} 但复制按钮 {nbtn}')
    if not is404:
        for bad in ('theme.css', 'theme_extra', 'jquery', 'ds-theme', 'mkdocs', 'pictures/'):
            if bad in raw:
                warns.append(f'{rel}: 残留旧站痕迹 {bad!r}')
        if 'href="/assets' in raw or 'src="/assets' in raw:
            errors.append(f'{rel}: 仍引用根绝对资源')
        if 'data-base' not in raw:
            errors.append(f'{rel}: 缺 data-base')

# 搜索索引结构（§4：headings 带 id）
import json
idx = json.load(io.open(os.path.join(SITE, 'search-index.json'), encoding='utf-8'))
nsec = sum(len(p.get('headings') or []) for p in idx)
noid = sum(1 for p in idx for h in (p.get('headings') or []) if not h.get('id'))
if noid:
    errors.append(f'search-index.json: {noid} 个 heading 缺 id')
longdesc = [p['path'] for p in idx if len(p.get('desc') or '') > 120]

# 404 自足性
f4 = io.open(os.path.join(SITE, '404.html'), encoding='utf-8').read()
for bad in ('site.css', 'site.js', 'assets/'):
    if bad in f4:
        errors.append(f'404.html 不自足：引用了 {bad}')

# ── 回归清单（R1 / R2 / R3）机器核对 ──────────────────────────────────
css = io.open(os.path.join(SITE, 'assets/css/site.css'), encoding='utf-8').read()
js = io.open(os.path.join(SITE, 'assets/js/site.js'), encoding='utf-8').read()
raw_all = '\n'.join(io.open(p, encoding='utf-8').read() for p in pages)
# R17 §S7 / R18 A：块级搜索会给每个块加 id（`b-<slug>`，兜底 `b-<n>`）。它只是锚点，
# 不影响结构/样式，但会让原有的「字面量标签断言」失配 —— 因此做那些检查时先剥掉。
# 已核：产物里 `id="b-` 开头的元素恰好等于块索引条数（973），不会误伤任何原生 id。
_BID_RE = re.compile(r' id="b-[^"]*"')


def pg(rel):
    return _BID_RE.sub('', io.open(os.path.join(SITE, *rel.split('/')),
                                   encoding='utf-8').read())


raw_all = _BID_RE.sub('', raw_all)


# R15 §P2-1：正文里「成句英文 + 中文」粘在同一行（= 上游把两种语言写在同一个 <li>/<td>）。
# 排除：英文原文折叠块、代码块、右侧目录（右侧目录在 </main> 之后，天然不在切片内）。
def glued_lines(raw):
    body = raw[raw.find('<main'):raw.find('</main>')]
    body = re.sub(r'<details class="orig">.*?</details>', ' ', body, flags=re.S)
    body = re.sub(r'<pre>.*?</pre>', ' ', body, flags=re.S)
    bad = []
    for m in re.finditer(r'<(li|td|p)[^>]*>(.*?)</\1>', body, re.S):
        for part in re.split(r'<br\s*/?>', m.group(2), flags=re.I):
            t = re.sub(r'\s+', ' ', H.unescape(re.sub(r'<[^>]+>', ' ', part))).strip()
            k = re.search(r'[\u4e00-\u9fff]', t)
            if not k:
                continue
            head = re.sub(r'《[^》]*》', '', t[:k.start()])   # 中文句里的《英文书名》不算混排
            if (re.search(r'[A-Za-z]{3,}\s+[A-Za-z]{3,}\s+[A-Za-z]{3,}', head)
                    and len(re.findall(r'[\u4e00-\u9fff]', t)) >= 4):
                bad.append(t[:80])
    return bad


GLUED = []
for _p in pages:
    GLUED += [(os.path.relpath(_p, SITE).replace('\\', '/'), x)
              for x in glued_lines(io.open(_p, encoding='utf-8').read())]


# ── R17（独立审查 S5.4）：示例 JSON 语法断言 ────────────────────────────
# 为什么需要：B-1/B-2 那类「示例 JSON 语法错误」能长期留存、而回归仍 126/126 全绿，
# 就是因为缺这一条。跳过：片段（不以 { / [ 开头）、含 `...` 省略写法、含 Mutator1~4 占位。
_JSON_PH = re.compile(r'"Mutator[1-4]"')
JSON_BAD = []
for _p in pages:
    _t = io.open(_p, encoding='utf-8').read()
    for _i, _m in enumerate(re.finditer(r'<pre><code class="language-json">(.*?)</code></pre>',
                                        _t, re.S)):
        _b = H.unescape(_m.group(1)).strip()
        if not _b.startswith(('{', '[')) or '...' in _b or _JSON_PH.search(_b):
            continue
        try:
            json.loads(_b)
        except Exception as _e:
            JSON_BAD.append('%s 块#%d %s'
                            % (os.path.relpath(_p, SITE).replace('\\', '/'), _i, _e))


# ── R17 §S7：块级搜索锚点一致性 ────────────────────────────────────────
# 索引里的每个块锚点都必须在对应产物页面上真实存在，否则搜索结果会跳空。
_BLKDATA = json.loads(io.open(os.path.join(SITE, 'search-blocks.json'),
                              encoding='utf-8').read())
BLK_TOTAL, BLK_MISSING = 0, []
for _path, _arr in _BLKDATA.items():
    _sub = _path.strip('/').replace('/', os.sep)
    _f = os.path.join(SITE, _sub, 'index.html') if _sub else os.path.join(SITE, 'index.html')
    if not os.path.exists(_f):
        BLK_MISSING.append(_path + '（页面不存在）')
        continue
    _ids = set(re.findall(r'\bid="([^"]+)"', io.open(_f, encoding='utf-8').read()))
    for _a, _x in _arr:
        BLK_TOTAL += 1
        if _a not in _ids:
            BLK_MISSING.append('%s#%s' % (_path, _a))


# ── R17 §S8：CSS 断言改为「空白无关」比对 ──────────────────────────────
# 产物 CSS 现在做保守空白压缩（去掉缩进、结构符号周围空白、块内最后一条的分号），
# 所以断言统一在「归一化后的文本」上做字面量匹配。
def _cssnorm(frag):
    return re.sub(r'\s+', '', frag).replace(';}', '}').rstrip(';')


_CSS_N = _cssnorm(css)


def incss(frag):
    return _cssnorm(frag) in _CSS_N

def count(pat, flags=0):
    return len(re.findall(pat, raw_all, flags))


CHECKS = [
    # R3 §1 语言开关
    ('R3 §1 语言开关胶囊内边距', incss('gap:2px; padding:2px')),
    ('R3 §1 激活段独立圆角块', incss('padding:.28rem .75rem') and incss('border-radius:999px')),
    ('R3 §1 顶栏按钮间距 .35rem', incss('align-items:center; gap:.35rem')),
    # R3 §2.1 目录筛选框
    ('R3 §2.1 目录内筛选框已删', count(r'toc-filter') == 0 and not incss('.toc-filter')),
    ('R5 ③ 章节筛选框已整体移除', count(r'class="section-filter') == 0
     and not incss('.section-filter') and 'section-filter' not in js),
    # R3 §2.2 搜索模态框（404 为自足页，不含搜索框）
    ('R3 §2.2 输入行 + 图标 + Esc', count(r'class="search-input-row"') == len(pages) - 1),
    ('R3 §2.2 底部快捷键提示条', count(r'class="search-foot"') == len(pages) - 1),
    ('R3 §2.2 聚焦蓝线已杀', incss('.search-panel input:focus-visible{ outline:none; }')),
    ('R3 §2.2 空态不再撑高', incss('.search-results .empty-state{ border:0')),
    ('R3 §2.2 章节结果不暴露 hash', 'r.page.title_zh || r.page.title' in js),
    # R3 §3 宽度阶梯
    ('R3 §3 ≥1600 内容 960 / 目录 240', incss('--content-w:960px; --toc-w:240px')),
    ('R3 §3 ≥1920 内容 1040', incss('--content-w:1040px')),
    # R3 §4 滚动条
    ('R3 §4 横向条物理消除', incss('overflow-y:auto; overflow-x:clip')),
    ('R3 §4 纵向条平时隐形', incss('scrollbar-color:transparent transparent')),
    ('R3 §4 悬停才浮现', incss('.toc:hover .toc-list::-webkit-scrollbar-thumb')),
    ('R3 §4 长键 anywhere 断行', incss('overflow-wrap:anywhere')),
    ('R3 §4 左导航纤细滚动条', incss('.drawer::-webkit-scrollbar-thumb')),
    # R3 §5.1 单元格中文行
    ('R3 §5.1 单元格中文行全部有 .td-zh',
     count(r'<br\s*/?>\s*(?!<span class="td-zh")[\u4e00-\u9fff]', re.I) == 0),
    # R3 §5.2 衬线
    ('R3 §5.2 --font-serif token', incss('--font-serif:')),
    ('R3 §5.2 正文整体衬线', incss('.content,.home-main{ font-family:var(--font-serif); }')),
    ('R3 §5.2 标题/控件回归无衬线', incss('.content :is(h1,h2,h3,h4,h5,h6),')),
    # R3 §6 表头 / Default 前缀
    ('R3 §6 表头内无 td 残留', count(r'<thead>(?:(?!</thead>).)*?<td\b', re.S) == 0),
    ('R3 §6 Default: 前缀已剔除', count(r'>Default: ') == 0),
    # R3 §7 复制按钮
    ('R3 §7 复制按钮悬停浮现', incss('opacity:0; transition:opacity .15s')
     and incss(':focus-within .copy-btn')),
    ('R3 §7 触屏降级常显淡化', incss('@media (hover:none){ .copy-btn{ opacity:.55; } }')),
    # R3 §8 单列名录
    ('R3 §8 单列表已转 name-grid', count(r'class="name-grid"') > 0),
    ('R3 §8 名录 CSS（grid + 断行）',
     incss('display:grid; gap:.15rem .9rem') and incss('overflow-wrap:anywhere')),
    # R3 §9 审核补充
    ('R3 §9.1 悬浮主题按钮已删', count(r'theme-fab') == 0 and not incss('theme-fab')),
    ('R3 §9.2 表内嵌套滚动已删', count(r'sticky-head') == 0 and not incss('sticky-head')),
    ('R4 §1 列表内折叠条不再吸附', incss('li > details.orig{ margin:.25em 0 .2em; }')),
    ('R3 §9.5 无空 href', count(r'href=""') == 0),
    ('R3 §9.6 description 无注记', count(r'name="description" content="[^"]*\[注') == 0),
    # R1/R2 无回归
    ('R1 §1 站内相对路径（无根绝对）', abs_links == 0),
    ('R2 §1 左导航栏头已删', count(r'drawer-head') == 0),
    ('R2 §3 卡片用 SVG 图标', count(r'class="card-icon"><svg') == 14),
]

# ── R4 回归清单 ────────────────────────────────────────────────────────
home_html = pg('index.html')
toc_html = pg('toc/index.html')
_stats = re.search(r'<div class="stats">(.*?)</div>', toc_html, re.S)
_stats_b = _stats.group(1).count('<b>') if _stats else -1
_toc_nav = re.search(r'class="drawer-list">(.*?)</ul>', home_html, re.S)
_toc_nav_labels = re.findall(r'<a [^>]*>([^<]*)</a>', _toc_nav.group(1)) if _toc_nav else []
res_html = pg('resources/index.html')
tut_html = pg('tutorial/index.html')
ce_html = pg('common-edits/index.html')
tips_html = pg('tips/index.html')
basics_html = pg('basics/index.html')
mods_html = pg('modules/index.html')
faq_html = pg('faq/index.html')
mut_html = pg('mutators/index.html')
# R16 ③：索引里的 chip 锚点必须覆盖该页全部 h2（无遗漏）
_mut_anchors = set(re.findall(r'class="mut-chip" href="#([^"]*)"', mut_html))
_mut_h2 = set(re.findall(r'<h2 id="([^"]+)"', mut_html)) - {'mutator-index'}
MUT_IDX_OK = bool(_mut_h2) and _mut_h2 <= _mut_anchors
tzh_empty = [p['path'] for p in idx if not (p.get('title_zh') or '').strip()]
CHECKS += [
    # §1 折叠条按钮化
    ('R4 §1 折叠条 hover 有底色反馈', incss('details.orig > summary:hover{ background:var(--panel)')),
    ('R4 §1 summary 按钮化内边距', incss('padding:.18rem .5rem; border-radius:5px')),
    # §2.1 更新日志无孤儿英文条目
    ('R4 §2.1 首页无孤儿英文条目', len(re.findall(r'<li lang="en">', home_html)) == 0),
    # §2.2 行内代码 chips
    ('R4 §2.2 行内代码调谐', incss('padding:.12em .4em; font-size:.88em')),
    # §2.3 字号补偿（R5 ⑥ 再次上调到 19px）
    ('R5 ⑥ 正文 21px', incss('font-size:21px; line-height:1.75')),
    ('R4 §2.3 表格字号与正文同级', incss('font-size:1.05em;')
     and incss('width:max-content; max-width:100%;')),
    ('R5 字号全部相对正文（无 rem 字号）',
     len(re.findall(r'font-size:[\d.]+rem', css)) == 0),
    ('R5 ⑤ 无列宽上限（内容不被压窄）', not incss('max-width:40ch')),
    ('R5 单元格中文行 .95em', incss('.td-zh{ font-size:.95em')),
    # §3.1 搜索胶囊
    ('R4 §3.1 搜索是整体胶囊', count(r'class="search-btn-text"') == len(pages) - 1
     and incss('.search-btn{\n  display:inline-flex')),
    # §3.2 title_zh 已填
    ('R4 §3.2 索引 title_zh 全部非空', not tzh_empty),
    # §3.3 结果面板贴合 + 语言开关同高
    ('R15 结果面板贴合内容并内部滚动',
     incss('.search-results{ list-style:none; margin:0; padding:.4rem; overflow-y:auto; flex:0 1 auto; }')
     and incss('max-height:60vh')),
    ('R4 §3.3 语言开关与图标同高', incss('min-height:34px; box-sizing:border-box')),
    # §4 名录扩展
    ('R4 §4 名录 ≥2 处（OBJ + ByMissionType）', count(r'class="name-grid"') >= 2),
    # §5 中文行配色 + 短列不换行
    ('R4 §5 新增 --muted2 中间色', incss('--muted2:#b7c0ca') and incss('--muted2:#454f59')),
    ('R5 ⑤ 中文行允许换行（keep-all）', incss('td:not(:last-child) .td-zh{ word-break:keep-all; }')
     and 'white-space:nowrap' not in css.split('th,td{')[1].split('}')[0]),
    # §6 资源页中文行找回链接
    ('R4 §6 资源页中文行链接齐全', len(re.findall(r'<a href="https?://', res_html)) >= 7),
    # §7 首页导航空链接
    ('R4 §7 首页导航首项 href="./"', 'href="./" class="current"' in home_html),
    # ── R4 Part 2 §8 美化拓展（404 为自足页，不含这些组件）──
    ('R4 §8.1 阅读进度条', count(r'class="read-progress"') == len(pages) - 1
     and incss('.read-progress{') and 'read-progress' in js),
    ('R5 ⑤ 三线表（无竖线无行线）',
     incss('border:0; border-top:1.5px solid var(--strong); border-bottom:1.5px solid var(--strong);')
     and incss('border-bottom:1px solid var(--strong);')),
    ('R5 ⑤ 表头跟随列对齐', incss('thead th, tbody td{ text-align:left; }')
     and incss('th.tc, td.tc{ text-align:center; }')),
    ('R5 短列居中 class 已生成', count(r'class="tc"') > 20),
    ('R5 空表改成一行「无」', count(r'class="tbl-none">无<') >= 11
     and incss('p.tbl-none{') and not incss('td-none')),
    ('无斑马纹（用户决定不要）', not incss('nth-child(even)')),
    ('R5 ① 目录页统计条 3 项', _stats_b == 3),
    ('R5 目录页：首页无卡片无统计',
     not re.search(r'class="card"|class="stats"', home_html)),
    ('R5 目录页插在首页之后',
     len(_toc_nav_labels) > 1 and _toc_nav_labels[1] == '目录 · Contents'),
    ('R5 目录页 14 张卡片', len(re.findall(r'class="card"', toc_html)) == 14),
    ('R5 已删页面无死链', count(r'href="(?:\.\./)?/(?:mev-dea|tutorials)/') == 0
     and count(r'href="(?:\.\./)+(?:mev-dea|tutorials)/') == 0),
    ('R5 已删页面不存在', not any(os.path.exists(os.path.join(SITE, s))
                                  for s in ('mev-dea', 'tutorials'))
     and os.path.exists(os.path.join(SITE, 'common-edits', 'index.html'))
     and os.path.exists(os.path.join(SITE, 'tutorial', 'index.html'))),
    ('R5 分组冷却已并入资源页',
     'id="grouped-cooldowns"' in io.open(os.path.join(SITE, 'resources', 'index.html'),
                                         encoding='utf-8').read()),
    # ── R6 收尾 ──
    ('R6 资源带缓存指纹',
     'assets/css/site.css?v=' in home_html and 'assets/js/site.js?v=' in home_html),
    ('R6 所有 img 带 width/height',
     len(re.findall(r'<img (?![^>]*\bwidth=)', raw_all)) == 0),
    ('R6 media.json 有尺寸记录',
     len(json.load(io.open(os.path.join(ROOT, 'build', 'media.json'), encoding='utf-8'))) >= 4),
    ('R6 Salvage 表单独定列宽',
     count(r'class="tbl-salvage"') == 1 and incss('.tbl-salvage th:nth-child(5)')),
    ('R4 §8.4 h2 琥珀竖条', incss('.content h2{') and incss('border-left:4px solid var(--brand)')),
    ('R4 §8.5 返回顶部小圆钮', count(r'id="to-top"') == len(pages) - 1 and incss('.to-top.show{')
     and 'to-top' in js),
    ('R4 §8.6 页脚三栏', count(r'class="footer-col"') == (len(pages) - 1) * 3
     and incss('.footer-cols{')
     and count(r'class="footer-links"') >= (len(pages) - 1) * 2),
    # ── R5 首批（视觉项）──
    ('R5 ③ 表格中文行与正文同色', incss('.td-zh{ font-size:.95em; color:var(--strong); }')),
    ('R5 ⑨ 顶栏已删 GitHub 图标', count(r'aria-label="GitHub 仓库"') == 0),
    ('R5 ⑨ 搜索居中拉长 960px', incss('flex:0 1 960px')
     and count(r'class="topbar-spacer"') == (len(pages) - 1) * 2),
    ('R6 Mutator 字段表 + 返回类型',
     count(r'<div class="mt-fields') >= 80
     and count(r'<table class="mf-table mf-fields">') >= 45
     and count(r'class="mf-ret"') >= 80
     and incss('.mf-table{') and '<th>字段</th><th>填写</th><th>作用</th>' in raw_all),
    ('R6 旧类型栏已移除', '<div class="mt-io">' not in raw_all and not incss('.mt-io{')),
    ('R5 附 标题锚点 # 已移除',
     not incss('.anchor') and '.anchor' not in js
     and 'class="anchor"' not in raw_all),
    # ── R5 第二批（提取器）──
    ('R5 ② 导航标签无「(客机…」', '敌人配置 · Enemies / EnemiesNoSync' in raw_all
     and '(客机' not in raw_all and '（客机' not in raw_all),
    ('R5 ④ 无「翻译」列残留', count(r'>\s*翻译[（(]?\s*<') == 0),
    ('R5 ⑦ 无「字段名称)」残留括号',
     count(r'<span class="td-zh">[^<]*\)</span>') == 0
     and count(r'<t[dh][^>]*>[^<]*[（(]\s*<br') == 0),
    ('R5 ⑧ 无空表头 / 空列', count(r'<th>\s*</th>') == 0),
    # ── R11 信息架构 ──
    ('R11 跨页锚点全部存在', not xref_bad),
    ('R11 左导航有分组标题', count(r'class="nav-head"') == (len(pages) - 1) * 4),
    ('R11 目录页分组卡片 4 组', len(re.findall(r'class="card-group"',
                                                io.open(os.path.join(SITE, 'toc', 'index.html'),
                                                        encoding='utf-8').read())) == 4),
    ('R11 首页三条入口 + 三节新手内容',
     'class="home-paths"' in home_html and 'id="first-edit"' in home_html
     and 'id="map"' in home_html and 'id="what"' in home_html
     and 'class="home-cta"' not in raw_all),
    ('R11 首页新手小节进了搜索索引',
     any(h.get('id') in ('first-edit', 'map', 'what')
         for h in next((p.get('headings') or [] for p in idx if p.get('slug') == ''),
                       []))),
    # ── R12 新手层 ──
    ('R12 新手入门页存在且九节齐全',
     all((f'id="{x}"' in tut_html) for x in
         ('what-is-cd2', 'what-is-a-cd2-file', 'two-parts', 'five-words',
          'first-edit', 'first-test', 'vars', 'next', 'exits'))),
    ('R12 首页不再承担完整教程（6 步已移出）',
     len(re.findall(r'<li>', re.search(r'<ol class="home-steps">(.*?)</ol>',
                                       home_html, re.S).group(1))) == 3
     and '新手入门' in home_html),
    ('R12/R15 Cookbook 8 条配方，Descriptor 已核实',
     all((f'id="{i}"' in ce_html) for i in
         ('enemy-count', 'remove-vanilla-enemies', 'cb-supply-cost', 'cb-player-count',
          'cb-nitra', 'cb-dwarves', 'cb-enemy-tune', 'cb-wavespawner'))
     and 'ED_Spider_Stalker' in ce_html and 'ED_Spider_Lobber' in ce_html
     and 'Pools module field' in ce_html),
    ('R15 每条 Cookbook 配方都有「没生效？」与 Reference 出口',
     ce_html.count('没生效？') == 8 and ce_html.count('想深入了解') >= 8
     and ce_html.count('../tips/#debug-') >= 8),
    ('R12 Cookbook 声明了上限与未确认行为',
     'MaxActiveEnemies' in ce_html and '还没有被完全弄明白' in ce_html
     and '不建议超过 300' in ce_html),
    ('R12 Debug 页有分诊表 + 九步 + 五类症状',
     'id="debug-symptoms"' in tips_html and 'id="debug-order"' in tips_html
     and all((f'id="{x}"' in tips_html) for x in
             ('debug-no-change', 'debug-wrong-effect', 'debug-wavespawner',
              'debug-mutator', 'debug-mp'))),
    ('R12 tips 导语不再被 title 吞掉（存量 bug）',
     '这一页专门回答一件事' in tips_html),
    ('R12 人话关键词已进搜索索引',
     sum(1 for p in idx if (p.get('kw') or '').strip()) >= 10
     and '删怪' in next((p.get('kw') or '' for p in idx if p.get('slug') == 'common-edits'), '')
     and '虫更多' in next((p.get('kw') or '' for p in idx if p.get('slug') == 'common-edits'), '')
     and '我想做什么' in next((p.get('kw') or '' for p in idx if p.get('slug') == ''), '')),
    ('R12 面包屑带分组层级',
     'class="crumb-g"' in raw_all and 'Reference · 查表' in raw_all),
    ('R12 Reference 页有「想继续实践？」出口',
     count(r'class="admonition practice"') >= 6
     and '想继续实践？' in raw_all),
    ('R12 案例拆解与 Cookbook 名称不再冲突',
     '案例拆解 · Case Study' in raw_all and '常见修改 · Cookbook' in raw_all
     and '实战配方 · Cookbook' not in raw_all),
    # ── R13 链路闭环 ──
    ('R13 FAQ 问答条目有稳定英文锚点', count(r'<li id="faq-') == 14),
    ('R13 Debug 的 FAQ 链接指向具体问题',
     'faq/#faq-no-effect' in tips_html and 'faq/#faq-mutator-debug' in tips_html
     and 'faq/#faq-public-match' in tips_html and 'faq/#faq-cd1-conflict' in tips_html),
    ('R13 返回上一位置按钮', count(r'id="jump-back"') == len(pages) - 1
     and 'jump-back' in js and incss('.jump-back{')),
    ('R13 BaseHazard 口径已按实测修正',
     'BaseHazard' in tut_html and '默认使用 Hazard 5' not in tut_html
     and '玩家在任务里选择的那个官难' in basics_html
     and '玩家在任务里选择的那个官难' in mods_html),
    ('R13 Reference 反向入口收敛到核心页',
     count(r'class="admonition practice"') == 6),
    # ── R14 Vars 定位与措辞一致性 ──
    ('R14 新手页 Vars 一节保留，并按「作者工具」定位',
     'id="vars"' in tut_html and '建议尽早认识' in tut_html
     and '看得见' in tut_html and '写得短' in tut_html and '连得通' in tut_html
     and '不需要把 Vars 的全部细节学完' in tut_html),
    ('R14 新手页给出「什么时候需要 Vars」三档',
     '只改一个数字' in tut_html and '开始写动态机制' in tut_html
     and '写复杂的 Mutator / Trigger / WaveSpawner' in tut_html),
    ('R14 新手页在早期小节预告 Vars', 'href="#vars"' in tut_html),
    ('R14 新手页不把示例钉死在 Hazard 5',
     '基于 Hazard 5' not in tut_html and '当前基准难度' in tut_html),
    ('R14 FAQ「从哪一页开始学」指向新手入门与现结构',
     'faq-where-to-start' in faq_html and '../tutorial/' in faq_html
     and '写作提示与常见错误' not in faq_html),
    ('R14 Cookbook 片段措辞已修正',
     '放进你自己的难度文件对应位置即可使用' in ce_html
     and '抄进你自己的文件就能用' not in ce_html),
    ('R14「{} = Hazard 5」已标待核实', '待核实' in basics_html),
    ('R14 全站无旧页面名残留（不把读者送回旧结构）',
     '写作提示与常见错误' not in raw_all and '实战配方 · Cookbook' not in raw_all
     and '难度实战拆解' not in raw_all and '案例拆解 · Case Study' in raw_all),
    # ── R15 §P0-1 搜索：原位展开 + 下拉结果面板 ──
    ('R15 搜索不再有遮罩层',
     count(r'class="search-modal"') == 0 and not incss('.search-modal')),
    ('R15 结果面板挂在搜索槽内（每页一份）',
     count(r'id="search-panel"') == len(pages) - 1
     and count(r'class="search-slot"') == len(pages) - 1),
    ('R15 面板锚定在搜索框正下方',
     incss('top:calc(100% + 8px)') and incss('translateX(-50%)')),
    ('R15 窄屏退化为顶部结果页',
     incss('top:var(--topbar-h)')),
    ('R15 空态给常用入口 + 点面板外关闭',
     '常用入口' in js and 'SUGGEST' in js and '#search-slot' in js),
    ('R15 键盘行为保留（Ctrl K / 方向键 / Enter / Esc）',
     "toLowerCase() === 'k'" in js and 'ArrowDown' in js and 'ArrowUp' in js
     and "e.key === 'Escape'" in js),
    # ── R15 §P2-3 猜测路径与去向引导 ──
    ('R15 404 有去向引导 + 猜测路径跳转',
     '你可能在找' in f4 and "'/getting-started/': '/tutorial/'" in f4
     and "'/cookbook/': '/common-edits/'" in f4 and "'/debug/': '/tips/'" in f4),
    # ── R15 §P2-1 中英呈现统一 ──
    ('R15 正文无「成句英文 + 中文」同行混排', not GLUED),
    ('R15 无未译的英文小标题残留',
     '<p lang="en">Parameters:</p>' not in raw_all
     and '<p lang="en">Note:</p>' not in raw_all),
    # ── R16 ① 侧栏跟随 / ② 访问态颜色 / ③ Mutators 索引重做 ──
    ('R16 侧栏加载后滚到当前项（只滚抽屉自身）',
     'drawer.scrollTop +=' in js and '#drawer .drawer-list a.current' in js),
    ('R16 链接不再区分访问态颜色',
     not incss('var(--visited)') and not incss('--visited:')
     and incss('a:visited{ color:var(--link); }')),
    ('R16 Mutators 索引：卡片 + chip + 筛选框',
     'class="mut-filter"' in mut_html and 'id="mut-filter"' in mut_html
     and 'details class="mut-card"' in mut_html and 'mut-chip' in mut_html
     and 'mut-chip' in js and 'mut-filter' in js),
    ('R16 Mutators 索引覆盖全部小节（无遗漏）', MUT_IDX_OK),
    ('R16 多合一条目已拆成独立 chip',
     all((f'>{x}<span class="en">' in mut_html) for x in
         ('加', '减', '乘', '除', '幂', '取模', '四舍五入', '向上取整', '向下取整',
          '锁定浮点数', '锁定布尔值', '锁定字符串'))),
    # ── R17（独立审查）──
    ('R17 示例 JSON 全部可解析', not JSON_BAD),
    ('R17 代码块长行折行（不靠横滚）',
     incss('.code-block pre code{ white-space:pre-wrap; overflow-wrap:anywhere; }')),
    ('R17 窄屏三线表补行线',
     incss('tbody td{ border-top:1px solid var(--border); }')),
    ('R17 tips 页「深挖」七节已降级为 H3',
     'id="debug-deepdive"' in tips_html
     and len(re.findall(r'<h3[^>]*>\s*[一二三四五六七]、', tips_html)) == 7),
    # ── R17 §S7 块级搜索 ──
    ('R17 块级搜索锚点全部存在于产物中', BLK_TOTAL > 500 and not BLK_MISSING),
    ('R18 块锚点是文本派生的稳定 slug（不是页内序号）',
     all(a.startswith('b-') for _p, _arr in _BLKDATA.items() for a, _x in _arr)
     and sum(1 for _p, _arr in _BLKDATA.items() for a, _x in _arr
             if not re.match(r'^b-\d+$', a)) > 500),
    ('R18「想深入了解」链接组已转成原子单元 + 灰色页面名前缀',
     count(r'class="reflinks"') >= 12 and count(r'class="rp"') >= 25
     and incss('.reflinks a + a::before{ content:"｜"')),
    ('R18 那条断言没有漏成「链接之间仍是 · 」',
     not re.search(r'想(?:深入|继续)(?:了解|实践)[^<>]*</b>\s*<a\b', raw_all)
     and not re.search(r'<td\b[^>]*>\s*<a\b[^>]*>[^<]*</a>\s*·\s*<a\b', raw_all)),
    ('R17 块级搜索已接通（索引 + 锚点链接 + 落地高亮 + 折叠块自动展开）',
     'search-blocks.json' in js and '?q=' in js and 'createTreeWalker' in js
     and incss('mark.hit{')
     and "d.tagName === 'DETAILS' && !d.open" in js),
]
if BLK_MISSING:
    errors.extend('块锚点缺失：' + x for x in BLK_MISSING[:10])
if JSON_BAD:
    errors.extend('示例 JSON 语法错误：' + x for x in JSON_BAD[:10])
if GLUED:
    errors.extend('EN/ZH 同行混排 %s → %s' % (f, t) for f, t in GLUED[:20])
if xref_bad:
    errors.extend(xref_bad[:40])
failed = [name for name, ok in CHECKS if not ok]
if failed:
    errors.extend('回归检查未通过：' + n for n in failed)

sz_css = os.path.getsize(os.path.join(SITE, 'assets/css/site.css'))
sz_js = os.path.getsize(os.path.join(SITE, 'assets/js/site.js'))
if sz_css > CSS_MAX * 0.95 or sz_js > JS_MAX * 0.95:
    warns.append('预算余量不足 5%%，下一轮改动容易超限')

P(f'检查页面 {len(pages)} 个')
P(f'英文折叠条 {tot_fold} ｜ 代码块 {tot_code} ｜ 搜索索引章节 {nsec} 条（缺 id {noid} 条）')
P(f'站内根绝对路径残留 {abs_links} 处 ｜ description 超 120 字的页面 {len(longdesc)} 个')
P(f'回归清单：{len(CHECKS) - len(failed)} / {len(CHECKS)} 通过')
P('')
P(f'❌ 错误 {len(errors)} 条')
for e in errors[:60]:
    P('   ' + e)
P('')
P(f'⚠️ 提示 {len(warns)} 条')
for w in warns[:40]:
    P('   ' + w)
P('')
P(f'预算：CSS {sz_css:,} / {CSS_MAX:,} = {sz_css / CSS_MAX * 100:.2f}%'
  f'（余 {CSS_MAX - sz_css:,} 字节 = {(CSS_MAX - sz_css) / CSS_MAX * 100:.2f}%）'
  f' ｜ JS {sz_js:,} / {JS_MAX:,} = {sz_js / JS_MAX * 100:.2f}%'
  f'（余 {JS_MAX - sz_js:,} 字节 = {(JS_MAX - sz_js) / JS_MAX * 100:.2f}%）')
sizes = sorted(((os.path.getsize(p), os.path.relpath(p, SITE)) for p in pages), reverse=True)
P('最大的 5 个页面：')
for s, r in sizes[:5]:
    P(f'   {r:28s} {s:,} 字节')
io.open(OUT, 'w', encoding='utf-8').write('\n'.join(L))
print('\n'.join(L))
