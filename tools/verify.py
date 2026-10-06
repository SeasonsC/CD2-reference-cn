# -*- coding: utf-8 -*-
"""自检：内链 / 锚点 / 图片 / 结构 / 相对路径 / 预算。按改进清单 §1 支持相对路径。"""
import os, io, re, posixpath
import urllib.parse
from lxml import html as LH

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(ROOT, 'docs')
OUT = os.path.join(ROOT, 'tools', 'verify_report.txt')
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


def count(pat, flags=0):
    return len(re.findall(pat, raw_all, flags))


CHECKS = [
    # R3 §1 语言开关
    ('R3 §1 语言开关胶囊内边距', 'gap:2px; padding:2px' in css),
    ('R3 §1 激活段独立圆角块', 'padding:.28rem .75rem' in css and 'border-radius:999px' in css),
    ('R3 §1 顶栏按钮间距 .35rem', 'align-items:center; gap:.35rem' in css),
    # R3 §2.1 目录筛选框
    ('R3 §2.1 目录内筛选框已删', count(r'toc-filter') == 0 and '.toc-filter' not in css),
    ('R5 ③ 章节筛选框已整体移除', count(r'class="section-filter') == 0
     and '.section-filter' not in css and 'section-filter' not in js),
    # R3 §2.2 搜索模态框（404 为自足页，不含搜索框）
    ('R3 §2.2 输入行 + 图标 + Esc', count(r'class="search-input-row"') == len(pages) - 1),
    ('R3 §2.2 底部快捷键提示条', count(r'class="search-foot"') == len(pages) - 1),
    ('R3 §2.2 聚焦蓝线已杀', '.search-box input:focus-visible{ outline:none; }' in css),
    ('R3 §2.2 空态不再撑高', '.search-results .empty-state{ border:0' in css),
    ('R3 §2.2 章节结果不暴露 hash', 'r.page.title_zh || r.page.title' in js),
    # R3 §3 宽度阶梯
    ('R3 §3 ≥1600 内容 960 / 目录 240', '--content-w:960px; --toc-w:240px' in css),
    ('R3 §3 ≥1920 内容 1040', '--content-w:1040px' in css),
    # R3 §4 滚动条
    ('R3 §4 横向条物理消除', 'overflow-y:auto; overflow-x:clip' in css),
    ('R3 §4 纵向条平时隐形', 'scrollbar-color:transparent transparent' in css),
    ('R3 §4 悬停才浮现', '.toc:hover .toc-list::-webkit-scrollbar-thumb' in css),
    ('R3 §4 长键 anywhere 断行', 'overflow-wrap:anywhere' in css),
    ('R3 §4 左导航纤细滚动条', '.drawer::-webkit-scrollbar-thumb' in css),
    # R3 §5.1 单元格中文行
    ('R3 §5.1 单元格中文行全部有 .td-zh',
     count(r'<br\s*/?>\s*(?!<span class="td-zh")[\u4e00-\u9fff]', re.I) == 0),
    # R3 §5.2 衬线
    ('R3 §5.2 --font-serif token', '--font-serif:' in css),
    ('R3 §5.2 正文整体衬线', '.content,.home-main{ font-family:var(--font-serif); }' in css),
    ('R3 §5.2 标题/控件回归无衬线', '.content :is(h1,h2,h3,h4,h5,h6),' in css),
    # R3 §6 表头 / Default 前缀
    ('R3 §6 表头内无 td 残留', count(r'<thead>(?:(?!</thead>).)*?<td\b', re.S) == 0),
    ('R3 §6 Default: 前缀已剔除', count(r'>Default: ') == 0),
    # R3 §7 复制按钮
    ('R3 §7 复制按钮悬停浮现', 'opacity:0; transition:opacity .15s' in css
     and ':focus-within .copy-btn' in css),
    ('R3 §7 触屏降级常显淡化', '@media (hover:none){ .copy-btn{ opacity:.55; } }' in css),
    # R3 §8 单列名录
    ('R3 §8 单列表已转 name-grid', count(r'class="name-grid"') > 0),
    ('R3 §8 名录 CSS（grid + 断行）',
     'display:grid; gap:.15rem .9rem' in css and 'overflow-wrap:anywhere' in css),
    # R3 §9 审核补充
    ('R3 §9.1 悬浮主题按钮已删', count(r'theme-fab') == 0 and 'theme-fab' not in css),
    ('R3 §9.2 表内嵌套滚动已删', count(r'sticky-head') == 0 and 'sticky-head' not in css),
    ('R4 §1 列表内折叠条不再吸附', 'li > details.orig{ margin:.25em 0 .2em; }' in css),
    ('R3 §9.5 无空 href', count(r'href=""') == 0),
    ('R3 §9.6 description 无注记', count(r'name="description" content="[^"]*\[注') == 0),
    # R1/R2 无回归
    ('R1 §1 站内相对路径（无根绝对）', abs_links == 0),
    ('R2 §1 左导航栏头已删', count(r'drawer-head') == 0),
    ('R2 §3 卡片用 SVG 图标', count(r'class="card-icon"><svg') == 14),
]

# ── R4 回归清单 ────────────────────────────────────────────────────────
home_html = io.open(os.path.join(SITE, 'index.html'), encoding='utf-8').read()
toc_html = io.open(os.path.join(SITE, 'toc', 'index.html'), encoding='utf-8').read()
_stats = re.search(r'<div class="stats">(.*?)</div>', toc_html, re.S)
_stats_b = _stats.group(1).count('<b>') if _stats else -1
_toc_nav = re.search(r'class="drawer-list">(.*?)</ul>', home_html, re.S)
_toc_nav_labels = re.findall(r'<a [^>]*>([^<]*)</a>', _toc_nav.group(1)) if _toc_nav else []
res_html = io.open(os.path.join(SITE, 'resources', 'index.html'), encoding='utf-8').read()
tut_html = io.open(os.path.join(SITE, 'tutorial', 'index.html'), encoding='utf-8').read()
ce_html = io.open(os.path.join(SITE, 'common-edits', 'index.html'), encoding='utf-8').read()
tips_html = io.open(os.path.join(SITE, 'tips', 'index.html'), encoding='utf-8').read()
basics_html = io.open(os.path.join(SITE, 'basics', 'index.html'), encoding='utf-8').read()
mods_html = io.open(os.path.join(SITE, 'modules', 'index.html'), encoding='utf-8').read()
faq_html = io.open(os.path.join(SITE, 'faq', 'index.html'), encoding='utf-8').read()
tzh_empty = [p['path'] for p in idx if not (p.get('title_zh') or '').strip()]
CHECKS += [
    # §1 折叠条按钮化
    ('R4 §1 折叠条 hover 有底色反馈', 'details.orig > summary:hover{ background:var(--panel)' in css),
    ('R4 §1 summary 按钮化内边距', 'padding:.18rem .5rem; border-radius:5px' in css),
    # §2.1 更新日志无孤儿英文条目
    ('R4 §2.1 首页无孤儿英文条目', len(re.findall(r'<li lang="en">', home_html)) == 0),
    # §2.2 行内代码 chips
    ('R4 §2.2 行内代码调谐', 'padding:.12em .4em; font-size:.88em' in css),
    # §2.3 字号补偿（R5 ⑥ 再次上调到 19px）
    ('R5 ⑥ 正文 21px', 'font-size:21px; line-height:1.75' in css),
    ('R4 §2.3 表格字号与正文同级', 'font-size:1.05em;' in css
     and 'width:max-content; max-width:100%;' in css),
    ('R5 字号全部相对正文（无 rem 字号）',
     len(re.findall(r'font-size:[\d.]+rem', css)) == 0),
    ('R5 ⑤ 无列宽上限（内容不被压窄）', 'max-width:40ch' not in css),
    ('R5 单元格中文行 .95em', '.td-zh{ font-size:.95em' in css),
    # §3.1 搜索胶囊
    ('R4 §3.1 搜索是整体胶囊', count(r'class="search-btn-text"') == len(pages) - 1
     and '.search-btn{\n  display:inline-flex' in css),
    # §3.2 title_zh 已填
    ('R4 §3.2 索引 title_zh 全部非空', not tzh_empty),
    # §3.3 模态框贴合 + 语言开关同高
    ('R4 §3.3 模态框高度贴合内容', 'align-items:flex-start;' in css
     and '.search-results{ list-style:none; margin:0; padding:.4rem; overflow-y:auto; flex:0 1 auto; }' in css),
    ('R4 §3.3 语言开关与图标同高', 'min-height:34px; box-sizing:border-box' in css),
    # §4 名录扩展
    ('R4 §4 名录 ≥2 处（OBJ + ByMissionType）', count(r'class="name-grid"') >= 2),
    # §5 中文行配色 + 短列不换行
    ('R4 §5 新增 --muted2 中间色', '--muted2:#b7c0ca' in css and '--muted2:#454f59' in css),
    ('R5 ⑤ 中文行允许换行（keep-all）', 'td:not(:last-child) .td-zh{ word-break:keep-all; }' in css
     and 'white-space:nowrap' not in css.split('th,td{')[1].split('}')[0]),
    # §6 资源页中文行找回链接
    ('R4 §6 资源页中文行链接齐全', len(re.findall(r'<a href="https?://', res_html)) >= 7),
    # §7 首页导航空链接
    ('R4 §7 首页导航首项 href="./"', 'href="./" class="current"' in home_html),
    # ── R4 Part 2 §8 美化拓展（404 为自足页，不含这些组件）──
    ('R4 §8.1 阅读进度条', count(r'class="read-progress"') == len(pages) - 1
     and '.read-progress{' in css and 'read-progress' in js),
    ('R5 ⑤ 三线表（无竖线无行线）',
     'border:0; border-top:1.5px solid var(--strong); border-bottom:1.5px solid var(--strong);' in css
     and 'border-bottom:1px solid var(--strong);' in css),
    ('R5 ⑤ 表头跟随列对齐', 'thead th, tbody td{ text-align:left; }' in css
     and 'th.tc, td.tc{ text-align:center; }' in css),
    ('R5 短列居中 class 已生成', count(r'class="tc"') > 20),
    ('R5 空表改成一行「无」', count(r'class="tbl-none">无<') >= 11
     and 'p.tbl-none{' in css and 'td-none' not in css),
    ('无斑马纹（用户决定不要）', 'nth-child(even)' not in css),
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
     count(r'class="tbl-salvage"') == 1 and '.tbl-salvage th:nth-child(5)' in css),
    ('R4 §8.4 h2 琥珀竖条', '.content h2{' in css and 'border-left:4px solid var(--brand)' in css),
    ('R4 §8.5 返回顶部小圆钮', count(r'id="to-top"') == len(pages) - 1 and '.to-top.show{' in css
     and 'to-top' in js),
    ('R4 §8.6 页脚三栏', count(r'class="footer-col"') == (len(pages) - 1) * 3
     and '.footer-cols{' in css
     and count(r'class="footer-links"') >= (len(pages) - 1) * 2),
    # ── R5 首批（视觉项）──
    ('R5 ③ 表格中文行与正文同色', '.td-zh{ font-size:.95em; color:var(--strong); }' in css),
    ('R5 ⑨ 顶栏已删 GitHub 图标', count(r'aria-label="GitHub 仓库"') == 0),
    ('R5 ⑨ 搜索居中拉长 960px', 'flex:0 1 960px' in css
     and count(r'class="topbar-spacer"') == (len(pages) - 1) * 2),
    ('R6 Mutator 字段表 + 返回类型',
     count(r'<div class="mt-fields') >= 80
     and count(r'<table class="mf-table mf-fields">') >= 45
     and count(r'class="mf-ret"') >= 80
     and '.mf-table{' in css and '<th>字段</th><th>填写</th><th>作用</th>' in raw_all),
    ('R6 旧类型栏已移除', '<div class="mt-io">' not in raw_all and '.mt-io{' not in css),
    ('R5 附 标题锚点 # 已移除',
     '.anchor' not in css and '.anchor' not in js
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
    ('R12 Cookbook 存在且两条配方 + 已核实 Descriptor',
     'id="enemy-count"' in ce_html and 'id="remove-vanilla-enemies"' in ce_html
     and 'ED_Spider_Stalker' in ce_html and 'ED_Spider_Lobber' in ce_html
     and 'Pools module field' in ce_html),
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
     and 'jump-back' in js and '.jump-back{' in css),
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
]
if xref_bad:
    errors.extend(xref_bad[:40])
failed = [name for name, ok in CHECKS if not ok]
if failed:
    errors.extend('回归检查未通过：' + n for n in failed)

sz_css = os.path.getsize(os.path.join(SITE, 'assets/css/site.css'))
sz_js = os.path.getsize(os.path.join(SITE, 'assets/js/site.js'))
if sz_css > 30720 * 0.95 or sz_js > 20480 * 0.95:
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
P(f'预算：CSS {sz_css:,} / 30,720 = {sz_css / 30720 * 100:.2f}%'
  f'（余 {30720 - sz_css:,} 字节 = {(30720 - sz_css) / 30720 * 100:.2f}%）'
  f' ｜ JS {sz_js:,} / 20,480 = {sz_js / 20480 * 100:.2f}%'
  f'（余 {20480 - sz_js:,} 字节 = {(20480 - sz_js) / 20480 * 100:.2f}%）')
sizes = sorted(((os.path.getsize(p), os.path.relpath(p, SITE)) for p in pages), reverse=True)
P('最大的 5 个页面：')
for s, r in sizes[:5]:
    P(f'   {r:28s} {s:,} 字节')
io.open(OUT, 'w', encoding='utf-8').write('\n'.join(L))
print('\n'.join(L))
