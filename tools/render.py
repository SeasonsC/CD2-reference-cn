# -*- coding: utf-8 -*-
"""
CD2 参考文档 v2 · 静态站渲染器（M2 + 改进清单）
────────────────────────────────────────────────────────────
读 build/ 下的结构化内容，套统一模板生成纯静态 HTML。
  · 改进清单 §1：全站相对路径（适配 GitHub Pages 项目子路径）；404.html 自足
  · 改进清单 §2：≥1200px 左侧导航常驻（三栏 grid）
  · 改进清单 §6：meta description ≤120 字；首页 tagline 控断行
  · 方案 v2.1 §3.5：成对段落 → 中文 + <details class="orig"> 折叠英文
"""
import os, io, re, json, html as H, sys, shutil

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mtio                                   # 「类型栏」散文 → 结构化

ROOT = r'E:\learn\github\dsh\CD2\CD2-reference-cn-v2'
SITE = os.path.join(ROOT, 'docs')          # R2 §6.1：GitHub Pages 发布源
BUILD = os.path.join(ROOT, 'build')
CONTENT = os.path.join(BUILD, 'content')

SITE_NAME = 'CD2 参考文档'
REPO_PATH = '/CD2-reference-cn'                    # GitHub Pages 项目子路径
SITE_URL = 'https://seasonsc.github.io' + REPO_PATH
GITHUB = 'https://github.com/SeasonsC/CD2-reference-cn'
TAGLINE = '深岩银河（Deep Rock Galactic）自定义难度模组 CD2 的中文参考手册'
DESC_MAX = 120

HOME = {'slug': '', 'path': '/', 'label': SITE_NAME, 'label_raw': ''}
MEDIA = {}

EARLY = ("!function(){try{var t=localStorage.getItem('cd2-theme')||'auto';"
         "document.documentElement.setAttribute('data-theme',t==='auto'?"
         "(matchMedia('(prefers-color-scheme: light)').matches?'light':'dark'):t);"
         "var l=localStorage.getItem('cd2-lang')==='zh'?'zh':'both';"
         "document.documentElement.setAttribute('data-lang',l);}"
         "catch(e){document.documentElement.setAttribute('data-theme','dark');}}();")

MONO = {
    '': 'CD', 'faq': 'FQ', 'basics': 'BA', 'modules': 'MO', 'enemies': 'EN',
    'direct': 'DR', 'wavespawners': 'WS', 'projectiles': 'PR', 'mutators': 'MU',
    'mev-dea': 'MD', 'common-edits': 'CE', 'tutorials': 'TU', 'resources': 'RE',
    'tips': 'TI',
}

# R2 §3.3：手写 SVG 线性图标（24 视窗、stroke=currentColor、1.8 线宽）
_ICON_PATHS = {
    '': '<path d="M3 10.5 12 3l9 7.5"/><path d="M5.5 9.6V20h13V9.6"/>',
    'faq': '<circle cx="12" cy="12" r="9"/><path d="M9.4 9.4a2.7 2.7 0 1 1 3.4 2.6c-.7.2-1 .7-1 1.4v.4"/>'
           '<circle cx="12" cy="17.1" r=".95" fill="currentColor" stroke="none"/>',
    'basics': '<path d="M5 4h8.5A2.5 2.5 0 0 1 16 6.5V20H7.5A2.5 2.5 0 0 1 5 17.5z"/>'
              '<path d="M19 6.5V20h-3"/><path d="M8 8.5h5"/>',
    'modules': '<path d="M4 4h6v2.8a1.9 1.9 0 1 0 3.8 0V4H20v6h-2.8a1.9 1.9 0 1 0 0 3.8H20V20h-6v-2.8a1.9 1.9 0 1 0-3.8 0V20H4v-6h2.8a1.9 1.9 0 1 0 0-3.8H4z"/>',
    'enemies': '<ellipse cx="12" cy="13.5" rx="5" ry="6.2"/><path d="M12 7.3V4.5M9.6 5.4 8 3.6M14.4 5.4 16 3.6"/>'
               '<path d="M7 10.5H3.6M17 10.5h3.4M7.2 16.5l-3.4 2.6M16.8 16.5l3.4 2.6"/>',
    'direct': '<rect x="3" y="4.5" width="18" height="15" rx="1.6"/>'
              '<path d="M3 9.5h18M9 9.5v10M15 9.5v10"/>',
    'wavespawners': '<path d="M2 12h3.5l2.5-6.5 3 13 3-9.5 2 3h6"/>',
    'projectiles': '<path d="M21 3.5 3.5 11.2l6.8 2.4"/>'
                   '<path d="M21 3.5 10.3 13.6l2.4 6.9z"/><path d="M21 3.5 10.3 13.6"/>',
    'mutators': '<path d="M13.2 2.5 4.6 13.6H11l-.8 8 8.9-11.4h-6.3z"/>',
    'mev-dea': '<rect x="2.6" y="4" width="7.2" height="7.2" rx="1.2"/>'
               '<rect x="14.2" y="4" width="7.2" height="7.2" rx="1.2"/>'
               '<rect x="8.4" y="13.2" width="7.2" height="7.2" rx="1.2"/>',
    'common-edits': '<path d="M9.4 5.3a4.1 4.1 0 0 1 6.8-1.2l-2.7 2.7 1.5 1.5 2.7-2.7a4.1 4.1 0 0 1-5.2 5.2l-6 6a2 2 0 1 1-2.8-2.8l6-6a4.1 4.1 0 0 1-.3-2.7z"/>',
    'tutorials': '<path d="M12 3.2v17.6"/><path d="M5.4 5.6h10.2l3 3-3 3H5.4z"/>',
    'resources': '<path d="M3 7.2A2.2 2.2 0 0 1 5.2 5h3.6l2.2 2.6h8A2.2 2.2 0 0 1 21 9.8V18a2.2 2.2 0 0 1-2.2 2.2H5.2A2.2 2.2 0 0 1 3 18z"/>',
    'tips': '<path d="M12 3a6 6 0 0 0-3.4 10.9c.6.5.9 1.2.9 2v.6h5v-.6c0-.8.3-1.5.9-2A6 6 0 0 0 12 3z"/>'
            '<path d="M9.8 19.7h4.4M10.6 22h2.8"/>',
    'get-cd2': '<path d="M12 3v12"/><path d="M7 10l5 5 5-5"/><path d="M4 20h16"/>',
}


def icon(slug):
    return ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" '
            'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
            + _ICON_PATHS.get(slug, _ICON_PATHS['']) + '</svg>')


# R2 §3.5：卡片简介人工撰写（≤40 字），不用正文首段截断
CARD_DESC = {
    'faq': '关于 CD2 的常见疑问与解答',
    'basics': 'CD2 界面、文件格式与最小可用难度示例',
    'modules': '有效 CD2 配置文件的顶层字段说明',
    'enemies': '敌人描述符模块的全部控制项',
    'direct': '92 种敌人的 Direct 底层控制项与默认值',
    'wavespawners': '创建无预警敌人波次与生成规则',
    'projectiles': '修改远程敌人的投射物行为',
    'mutators': '让字段随游戏条件动态变化的表达式',
    'resources': '原版默认值表与外部参考资料',
    'tips': '写难度文件时的调试技巧与常见避坑',
}

THEME_ICON = ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
              'stroke-linecap="round"><rect x="2" y="4" width="20" height="13" rx="2"/>'
              '<path d="M8 21h8M12 17v4"/></svg>')
SEARCH_ICON = ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
               'stroke-linecap="round"><circle cx="11" cy="11" r="6.5"/><path d="M16 16l4.5 4.5"/></svg>')
MENU_ICON = ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
             'stroke-linecap="round"><path d="M3 6h18M3 12h18M3 18h18"/></svg>')
ARROW_UP = ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
            'stroke-linecap="round" stroke-linejoin="round"><path d="M12 19V5"/>'
            '<path d="M6 11l6-6 6 6"/></svg>')

# R4 §8.6：页脚中栏「相关资源」——只用能核实的链接
RESOURCES = [
    ('深岩资源站 · CD2 中文教学', 'https://drg.arthurlin.dev/zh-cn/'),
    ('原英文文档 · CD2 Reference', 'https://vonacht.github.io/cd2reference/'),
    ('GitHub 仓库', 'https://github.com/SeasonsC/CD2-reference-cn'),
    ('Deep Rock Galactic（Steam）',
     'https://store.steampowered.com/app/548430/Deep_Rock_Galactic/'),
    ('原版敌人描述符 DATA.md',
     'https://github.com/trumank/drg-custom-difficulties/blob/master/DATA.md'),
    ('DRG Hazard Scaling 数值表',
     'https://docs.google.com/spreadsheets/u/0/d/15L6sCaM5WdfuI65X54qDhD5sRDCGpb1Q4fkVkRhbBU4/htmlview'),
]
GH_ICON = ('<svg viewBox="0 0 24 24" fill="currentColor"><path d="M12 2A10 10 0 0 0 8.8 21.5c.5.1.7-.2'
           '.7-.5v-1.7c-2.8.6-3.4-1.3-3.4-1.3-.5-1.2-1.1-1.5-1.1-1.5-.9-.6.1-.6.1-.6 1 .1 1.5 1 1.5 1'
           '.9 1.6 2.4 1.1 3 .9.1-.7.4-1.1.6-1.4-2.2-.2-4.6-1.1-4.6-5 0-1.1.4-2 1-2.7-.1-.3-.4-1.3.1-2.7'
           ' 0 0 .8-.3 2.7 1a9.4 9.4 0 0 1 5 0c1.9-1.3 2.7-1 2.7-1 .5 1.4.2 2.4.1 2.7.6.7 1 1.6 1 2.7'
           ' 0 3.9-2.4 4.8-4.6 5 .4.3.7.9.7 1.9v2.8c0 .3.2.6.7.5A10 10 0 0 0 12 2z"/></svg>')


def esc(s):
    return H.escape(s or '', quote=True)


def clean_desc(s):
    """R3 §9.6：剥掉 [注：…] / {…} 注记，去空白，截 120 字。"""
    s = s or ''
    s = re.sub(r'\[注[：:][^\]]*\]', '', s)
    s = re.split(r'\[注[：:]', s)[0]
    s = re.sub(r'\{[^{}]*\}', '', s)
    s = re.sub(r'\s+', ' ', s).strip()
    return s[:DESC_MAX]


def relize(html, prefix):
    """把正文里的根绝对路径改成相对路径（R1 §1）。"""
    html = re.sub(r'href="/"', 'href="' + (prefix or './') + '"', html)   # R3 §9.5
    return re.sub(r'(href|src)="/(?!/)', lambda m: f'{m.group(1)}="{prefix}', html)


def fix_images(s, prefix):
    def repl(m):
        tag = m.group(0)
        src = re.search(r'src="([^"]+)"', tag)
        if not src:
            return tag
        key = src.group(1)
        if key.startswith('/'):
            key = key
        else:
            key = '/' + key
        d = MEDIA.get(key)
        if not d or 'width=' in tag:
            return tag
        return tag[:-1] + f' width="{d["w"]}" height="{d["h"]}">'
    return re.sub(r'<img\b[^>]*>', repl, s)


# ── 区块渲染 ────────────────────────────────────────────────────────────
def fold(en):
    return ('<details class="orig"><summary>英文原文</summary>'
            f'<div class="orig-body">{en}</div></details>')


def list_items(b):
    out = []
    for it in b['items']:
        cls = f' class="{esc(it["cls"])}"' if it.get('cls') else ''
        zh, en = it.get('zh'), it.get('en')
        if zh and en:
            out.append(f'<li{cls}>{zh}{fold(en)}</li>')
        elif zh:
            out.append(f'<li{cls}>{zh}</li>')
        else:
            out.append(f'<li lang="en"{cls}>{en}</li>')
    return out


def render_block(b):
    t = b['t']
    if t == 'h':
        lv = b['level']
        return f'<h{lv} id="{esc(b["id"])}">{esc(b["text"])}</h{lv}>'
    if t == 'p':
        if 'mt-io' in (b.get('cls') or ''):        # 类型栏：散文 → 结构化（R4 补充）
            return mtio.to_html(b.get('zh') or b.get('en') or '')
        cls = f' class="{esc(b["cls"])}"' if b.get('cls') else ''
        zh, en = b.get('zh'), b.get('en')
        if zh and en:
            return f'<p{cls}>{zh}</p>\n{fold("<p>" + en + "</p>")}'
        if zh:
            return f'<p{cls}>{zh}</p>'
        return f'<p lang="en"{cls}>{en}</p>'
    if t == 'list':
        return f'<{b["tag"]}>' + ''.join(list_items(b)) + f'</{b["tag"]}>'
    if t == 'code':
        lang = b['lang']
        body = H.escape(b['text'])
        return ('<div class="code-block"><div class="code-head">'
                f'<span class="code-lang">{esc(lang)}</span>'
                '<button class="copy-btn" type="button" aria-label="复制代码">复制</button>'
                f'</div><pre><code class="language-{esc(lang)}">{body}</code></pre></div>')
    if t == 'table':
        sticky = ''                       # R3 §9.2：取消表内嵌套滚动
        return f'<div class="table-wrap">{b["html"]}</div>'
    if t == 'namegrid':
        return b['html']
    if t == 'figure':
        return b['html']
    return b.get('html', '')


# ── 页面骨架 ────────────────────────────────────────────────────────────
def drawer_html(nav, cur):
    items = []
    for n in nav:
        c = ' class="current"' if n['slug'] == cur else ''
        aria = ' aria-current="page"' if n['slug'] == cur else ''
        items.append(f'<li><a href="{n["path"]}"{c}{aria}>{esc(n["label"])}</a></li>')
    return ('<nav class="drawer" id="drawer" aria-label="站点导航">'
            f'<ul class="drawer-list">{"".join(items)}</ul></nav>')


def topbar_html():
    return f'''<header class="topbar">
  <div class="topbar-inner">
    <div class="topbar-left">
      <button class="icon-btn" id="drawer-btn" type="button" aria-label="打开导航" aria-expanded="false" aria-controls="drawer">{MENU_ICON}</button>
      <a class="brand" href="/"><img src="/assets/img/logo.svg" alt="" width="22" height="22" loading="eager"><span>{esc(SITE_NAME)}</span></a>
    </div>
    <div class="topbar-mid">
      <div class="topbar-spacer"></div>
      <button class="search-btn" type="button" data-search-open aria-label="搜索文档">{SEARCH_ICON}<span class="search-btn-text">搜索</span><kbd>Ctrl K</kbd></button>
      <div class="topbar-spacer"></div>
    </div>
    <div class="topbar-right">
      <div class="lang-switch" role="group" aria-label="语言显示">
        <button type="button" data-lang-btn="zh" aria-pressed="false" title="仅显示中文">中</button>
        <button type="button" data-lang-btn="both" aria-pressed="true" title="中文 + 英文原文">中 + 英</button>
      </div>
      <button class="icon-btn" type="button" data-theme-btn aria-label="切换主题">{THEME_ICON}</button>
    </div>
  </div>
</header>'''


def toc_html(page):
    hs = page['headings']
    n2 = sum(1 for h in hs if h['level'] == 2)
    use3 = n2 <= 30
    items = []
    for h in hs:
        if h['level'] == 2:
            items.append(f'<li class="lvl-2"><a href="#{esc(h["id"])}">{esc(h["text"])}</a></li>')
        elif h['level'] == 3 and use3:
            items.append(f'<li class="lvl-3"><a href="#{esc(h["id"])}">{esc(h["text"])}</a></li>')
    if not items:
        return '', False
    return (f'<aside class="toc" aria-label="本页目录"><div class="toc-inner">'
            f'<div class="toc-title">本页目录</div>'
            f'<ul class="toc-list">{"".join(items)}</ul></div></aside>'), True


def page_nav_html(nav, slug):
    order = [n['slug'] for n in nav]
    i = order.index(slug) if slug in order else -1
    prev = nav[i - 1] if i > 0 else None
    nxt = nav[i + 1] if 0 <= i < len(nav) - 1 else None
    a = (f'<a class="prev" href="{prev["path"]}"><span class="dir">上一页</span>'
         f'<span class="title">{esc(prev["label"])}</span></a>') if prev else '<span></span>'
    b = (f'<a class="next" href="{nxt["path"]}"><span class="dir">下一页</span>'
         f'<span class="title">{esc(nxt["label"])}</span></a>') if nxt else '<span></span>'
    return f'<nav class="page-nav" aria-label="翻页">{a}{b}</nav>'


def footer_html(nav):
    """R4 §8.6：页脚三栏——站点地图 / 相关资源 / 声明。"""
    sitemap = ''.join(f'<li><a href="{n["path"]}">{esc(n["label"])}</a></li>' for n in nav)
    res = ''.join(f'<li><a href="{x}" target="_blank" rel="noopener">{esc(t)}</a></li>'
                  for t, x in RESOURCES)
    return f'''<footer class="footer">
  <div class="footer-cols">
    <div class="footer-col">
      <h3>站点地图</h3>
      <ul class="footer-links">{sitemap}</ul>
    </div>
    <div class="footer-col">
      <h3>相关资源</h3>
      <ul class="footer-links">{res}</ul>
    </div>
    <div class="footer-col">
      <h3>声明</h3>
      <p>本项目为<b>非官方</b>的中文翻译项目，仅提供翻译工作；界面设计、排版结构与原始内容均为原作者所有。</p>
    </div>
  </div>
</footer>'''


# R5：已删除的页面 —— 出口兜底，任何指向它们的 <a> 一律剥成纯文字（防死链）
REMOVED_SLUGS = {'mev-dea', 'common-edits', 'tutorials'}


def strip_dead_links(t):
    """把 href 指向已删页面的 <a> 拆掉，只保留内部文字。"""
    def rep(m):
        href = m.group(1)
        path = re.sub(r'^(?:\.\./)+|^/', '', href)
        if path.split('/')[0].split('#')[0] in REMOVED_SLUGS:
            return m.group(2)
        return m.group(0)
    return re.sub(r'<a\b[^>]*href="([^"]*)"[^>]*>(.*?)</a>', rep, t, flags=re.S)


def shell(title, desc, path, body, nav, slug, prefix, has_toc=False):
    canonical = SITE_URL + (path if path != '/' else '/')
    page = f'''<!DOCTYPE html>
<html lang="zh-CN" data-theme="dark" data-lang="both" data-base="{prefix}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{esc(title)}</title>
<meta name="description" content="{esc(clean_desc(desc))}">
<link rel="canonical" href="{esc(canonical)}">
<meta property="og:type" content="article">
<meta property="og:site_name" content="{esc(SITE_NAME)}">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(clean_desc(desc))}">
<meta property="og:url" content="{esc(canonical)}">
<link rel="icon" href="/assets/img/favicon.svg" type="image/svg+xml">
<script>{EARLY}</script>
<link rel="stylesheet" href="/assets/css/site.css">
</head>
<body{' class="has-toc"' if has_toc else ''}>
<a class="skip-link" href="#main">跳到正文</a>
{topbar_html()}
<div class="read-progress" id="read-progress" aria-hidden="true"></div>
<div class="drawer-overlay" id="drawer-overlay"></div>
{body}
{footer_html(nav)}
<button class="to-top" id="to-top" type="button" aria-label="返回顶部">{ARROW_UP}</button>
<div class="search-modal" id="search-modal" hidden>
  <div class="search-box" role="dialog" aria-modal="true" aria-label="搜索文档">
    <div class="search-input-row">
      {SEARCH_ICON}
      <input id="search-input" type="search" placeholder="搜索文档" aria-label="搜索文档" autocomplete="off">
      <kbd>Esc</kbd>
    </div>
    <ul class="search-results" id="search-results"></ul>
    <div class="search-foot">
      <span><kbd>↑</kbd><kbd>↓</kbd> 选择</span>
      <span><kbd>Enter</kbd> 打开</span>
      <span><kbd>Esc</kbd> 关闭</span>
    </div>
  </div>
</div>
<script src="/assets/js/site.js" defer></script>
</body>
</html>'''
    page = fix_images(page, prefix)
    return relize(page, prefix)


def content_page(page, nav):
    slug = page['slug']
    prefix = '../'
    navitem = next((n for n in nav if n['slug'] == slug), None) or HOME
    title = f'{navitem["label"]} — {SITE_NAME}'
    toc, has_toc = toc_html(page)
    main = [f'<main id="main" class="content">',
            f'<nav class="breadcrumb" aria-label="面包屑"><a href="/">首页</a> › '
            f'{esc(navitem["label"])}</nav>',
            f'<h1>{esc(navitem["label"])}</h1>']
    if page.get('no_translation'):
        main.append('<div class="admonition notice"><div class="admonition-title">'
                    '本页尚未翻译</div><p>以下为英文原文。</p></div>')
    for b in page['blocks']:
        main.append(render_block(b))
    main.append(page_nav_html(nav, slug))
    main.append('</main>')
    body = (f'<div class="layout{" has-toc" if has_toc else ""}">'
            + drawer_html(nav, slug) + '\n'.join(main) + toc + '</div>')
    return shell(title, page['desc'] or TAGLINE, page['path'], body, nav, slug,
                 prefix, has_toc)


def cards_html(nav, pages):
    """章节卡片网格（目录页用）。"""
    out = ['<a class="card" href="/resources/#get-cd2">'
           f'<span class="card-icon">{icon("get-cd2")}</span>'
           '<span class="card-main"><span class="card-title">获取 CD2'
           '<span class="card-en">Get CD2</span></span>'
           '<span class="card-desc">官方 Discord、友站与中文交流群</span></span></a>']
    for n in nav:
        if n['slug'] in ('', 'toc'):
            continue
        desc = CARD_DESC.get(n['slug'], clean_desc(pages.get(n['slug'], {}).get('desc') or ''))
        en = n['label'].split(' · ')[-1] if ' · ' in n['label'] else ''
        zh = n['label'].split(' · ')[0]
        out.append(
            f'<a class="card" href="{n["path"]}">'
            f'<span class="card-icon">{icon(n["slug"])}</span>'
            f'<span class="card-main">'
            f'<span class="card-title">{esc(zh)}'
            + (f'<span class="card-en">{esc(en)}</span>' if en and en != zh else '')
            + f'</span><span class="card-desc">{esc(desc)}</span></span></a>')
    return ''.join(out)


def stats_html(nav, pages):
    """站点规模统计条（数字从内容里现算）。"""
    n_chapters = len([n for n in nav if n['slug'] not in ('', 'toc')])
    n_direct = pages.get('direct', {}).get('stats', {}).get('blocks', {}).get('h', 0)
    n_code = sum(p.get('stats', {}).get('blocks', {}).get('code', 0) for p in pages.values())
    return (f'<div class="stats">'
            f'<span><b>{n_chapters}</b> 个章节</span>'
            f'<span><b>{n_direct}</b> 种敌人控制项</span>'
            f'<span><b>{n_code}</b> 段配置示例</span></div>')


def home_page(nav, pages):
    """首页 = 引言 + 更新日志（章节卡片已移到「目录」页）。"""
    home = pages.get('', {})
    intro, log, log_items = [], [], []
    state = 'intro'
    for b in home.get('blocks', []):
        if b['t'] == 'h':
            raw = b.get('text_raw', '')
            if 'Main Sections' in raw or '主要章节' in b['text']:
                state = 'sections'
                continue
            state = 'log'
            log.append(render_block(b))
            continue
        if state == 'intro':
            intro.append(render_block(b))
        elif state == 'sections':
            if b['t'] == 'figure':
                intro.append(render_block(b))
        else:
            if b['t'] == 'list':
                log_items.extend(list_items(b))
            else:
                log.append(render_block(b))
    if log_items:
        log.append('<ul class="update-log">' + ''.join(log_items) + '</ul>')
    body = f'''<div class="layout">
{drawer_html(nav, '')}
<div class="home-main">
<main id="main">
<div class="home-wrap">
  <h1>{esc(SITE_NAME)}</h1>
  <div class="home-lead">{''.join(intro)}</div>
  {''.join(log)}
</div>
</main>
</div>
</div>'''
    return shell(f'{SITE_NAME} — 深岩银河自定义难度中文参考', TAGLINE, '/', body,
                 nav, '', '')


def toc_page(nav, pages):
    """目录页：站名后的第一个内容页，放统计条 + 章节卡片。"""
    body = f'''<div class="layout">
{drawer_html(nav, 'toc')}
<main id="main" class="content">
<nav class="breadcrumb" aria-label="面包屑"><a href="/">首页</a> › 目录</nav>
<h1>目录 · Contents</h1>
{stats_html(nav, pages)}
<div class="card-grid">{cards_html(nav, pages)}</div>
{page_nav_html(nav, 'toc')}
</main>
</div>'''
    return shell(f'目录 · Contents — {SITE_NAME}', TAGLINE, '/toc/', body, nav, 'toc', '../', False)


# ── 404：自足页（内联样式，硬编码子路径）────────────────────────────────
F404_CSS = """
:root{--bg:#0b0f14;--surface:#0d1117;--panel:#161b22;--text:#e6edf3;--strong:#f0f6fc;
--muted:#8b949e;--border:#21262d;--border-soft:#30363d;--link:#388bfd;--brand:#f5a623;
--font:system-ui,-apple-system,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif}
[data-theme=light]{--bg:#fff;--surface:#f6f8fa;--panel:#e9edf1;--text:#1f2328;
--strong:#0a0c10;--muted:#59636e;--border:#d0d7de;--border-soft:#d8dee4;--link:#0969da;--brand:#9a6200}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--text);font-family:var(--font);
font-size:16px;line-height:1.75;display:flex;min-height:100vh;align-items:center;justify-content:center;padding:2rem}
main{max-width:640px}
h1{color:var(--strong);font-size:1.75rem;margin:0 0 .6em}
p,li{color:var(--text)}
code{background:var(--panel);border:1px solid var(--border-soft);border-radius:4px;
padding:.1em .35em;font-family:ui-monospace,Consolas,monospace;font-size:.875em}
a{color:var(--link)}
ul{padding-left:1.3em}
.btn{display:inline-block;margin-top:1rem;padding:.55rem 1.1rem;border-radius:6px;
background:var(--panel);border:1px solid var(--border-soft);color:var(--text);
text-decoration:none;font-weight:600}
.btn:hover{border-color:var(--brand)}
""".strip()


def notfound_page():
    return f'''<!DOCTYPE html>
<html lang="zh-CN" data-theme="dark">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>页面不存在 — {esc(SITE_NAME)}</title>
<meta name="robots" content="noindex">
<script>{EARLY}</script>
<style>
{F404_CSS}
</style>
</head>
<body>
<main>
  <h1>页面不存在</h1>
  <p>你访问的地址没有对应的页面。站内搜索请到首页后按 <kbd>Ctrl</kbd>+<kbd>K</kbd> 唤起。</p>
  <p>旧站路径变更对照：</p>
  <ul>
    <li><code>/Common%20edits/</code>、<code>/grouped_cooldowns/</code> → 该页已删除，见<a href="{REPO_PATH}/toc/">目录</a></li>
    <li><code>/search.html</code> → 站内搜索（按 <kbd>Ctrl</kbd>+<kbd>K</kbd>）</li>
  </ul>
  <p><a class="btn" href="{REPO_PATH}/toc/">打开目录</a> <a class="btn" href="{REPO_PATH}/">回到首页</a></p>
</main>
<script>
(function(){{
  var BASE = '{REPO_PATH}';
  var LEGACY = {{
    '/common edits/': '/toc/',
    '/common edits': '/toc/',
    '/common-edits/': '/toc/',
    '/grouped_cooldowns/': '/toc/',
    '/grouped_cooldowns': '/toc/',
    '/grouped-cooldowns/': '/toc/',
    '/grouped-cooldowns': '/toc/',
    '/mev-dea/': '/toc/',
    '/mev-dea': '/toc/',
    '/search.html': '/'
  }};
  var p = decodeURIComponent(location.pathname).toLowerCase();
  if (p.indexOf(BASE.toLowerCase()) === 0) p = p.slice(BASE.length);
  var hit = LEGACY[p];
  if (hit) location.replace(BASE + hit + location.hash);
}})();
</script>
</body>
</html>'''


# ── 主流程 ──────────────────────────────────────────────────────────────
def write_sitemap(nav):
    rows = []
    for n in nav:
        loc = SITE_URL + (n['path'] if n['path'] != '/' else '/')
        rows.append(f'  <url><loc>{H.escape(loc)}</loc></url>')
    xml = ('<?xml version="1.0" encoding="UTF-8"?>\n'
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
           + '\n'.join(rows) + '\n</urlset>\n')
    io.open(os.path.join(SITE, 'sitemap.xml'), 'w', encoding='utf-8').write(xml)
    io.open(os.path.join(SITE, 'robots.txt'), 'w', encoding='utf-8').write(
        'User-agent: *\nAllow: /\n\nSitemap: %s/sitemap.xml\n' % SITE_URL)
    io.open(os.path.join(SITE, '.nojekyll'), 'w', encoding='utf-8').write('')


def main():
    global MEDIA
    MEDIA = json.load(io.open(os.path.join(BUILD, 'media.json'), encoding='utf-8'))
    nav = json.load(io.open(os.path.join(BUILD, 'nav.json'), encoding='utf-8'))
    # R5：目录页插在首页之后（导航、翻页、页脚地图、sitemap 都会自动带上）
    if not any(n['slug'] == 'toc' for n in nav):
        nav.insert(1, {'slug': 'toc', 'path': '/toc/', 'label': '目录 · Contents',
                       'label_raw': ''})
    os.makedirs(SITE, exist_ok=True)
    pages, rows = {}, []
    for fn in sorted(os.listdir(CONTENT)):
        p = json.load(io.open(os.path.join(CONTENT, fn), encoding='utf-8'))
        pages[p['slug']] = p

    # 清掉上一轮遗留、本轮已不存在的页面目录（防止陈旧页面与死链）
    keep = set(pages.keys()) | {'toc', 'assets'}
    stale = []
    for name in sorted(os.listdir(SITE)):
        d = os.path.join(SITE, name)
        if os.path.isdir(d) and name not in keep and os.path.exists(os.path.join(d, 'index.html')):
            shutil.rmtree(d)
            stale.append(name)
    if stale:
        print('已清理陈旧页面目录:', ', '.join(stale))

    for slug, p in pages.items():
        if slug == '':
            continue
        d = os.path.join(SITE, slug)
        os.makedirs(d, exist_ok=True)
        out = strip_dead_links(content_page(p, nav))
        io.open(os.path.join(d, 'index.html'), 'w', encoding='utf-8').write(out)
        rows.append((slug, len(out), len(p['blocks'])))

    io.open(os.path.join(SITE, 'index.html'), 'w', encoding='utf-8').write(
        strip_dead_links(home_page(nav, pages)))
    d = os.path.join(SITE, 'toc')
    os.makedirs(d, exist_ok=True)
    out = strip_dead_links(toc_page(nav, pages))
    io.open(os.path.join(d, 'index.html'), 'w', encoding='utf-8').write(out)
    rows.append(('toc', len(out), 0))
    io.open(os.path.join(SITE, '404.html'), 'w', encoding='utf-8').write(
        strip_dead_links(notfound_page()))
    idx = io.open(os.path.join(BUILD, 'search-index.json'), encoding='utf-8').read()
    io.open(os.path.join(SITE, 'search-index.json'), 'w', encoding='utf-8').write(idx)
    write_sitemap(nav)

    L = ['%-14s %10s %8s' % ('slug', 'HTML字节', '区块数'), '-' * 36]
    L += ['%-14s %10s %8s' % (a, f'{b:,}', c) for a, b, c in rows]
    io.open(os.path.join(ROOT, 'tools', 'render_report.txt'), 'w',
            encoding='utf-8').write('\n'.join(L))
    print('\n'.join(L))
    print('\nindex.html + 404.html + sitemap.xml + robots.txt + .nojekyll + %d 个内容页' % len(rows))


main()
