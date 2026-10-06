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
import mtio2                                  # 「类型栏」→ 字段表 + 返回类型
try:
    from mut_field_notes import INTRO            # 人工重写的简介
except Exception:
    INTRO = {}

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
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
    'tutorial': '<path d="M9 4.5 5 6.2v13.3l4-1.7 6 1.7 4-1.7V4.5l-4 1.7z"/>'
                '<path d="M9 4.5v13.3M15 6.2v13.3"/>',
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
    'natural-selection': '一个完整 CD2 是怎么把多个机制拼起来的：六道功能由浅入深拆开讲',
    'common-edits': '两种最常见的改动：让虫变多／变少、从难度里删掉某类敌人',
    'tutorial': '完全不懂 CD2？从这里走到「改出第一个生效的数字」',
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

# R11：学习路径 vs 查表路径 —— 左导航与目录页分组。
#   分组必须连续，所以这里同时定义「组名」与「组内顺序」，nav 会按它重排；
#   没有列到的页面自动落到末尾的「其他」，将来新增页不会凭空消失。
NAV_GROUPS = [
    ('入门 · 从这里开始', ['', 'toc', 'tutorial', 'basics']),
    ('实战 · 学着做', ['common-edits', 'natural-selection']),
    ('Reference · 查表', ['modules', 'enemies', 'direct', 'wavespawners',
                          'projectiles', 'mutators', 'resources']),
    ('排障 · 出问题', ['faq', 'tips']),
]
NAV_GROUP_OTHER = '其他'

# R12 §13：Reference → 新手内容 的反向连接。
#   只在 Reference / FAQ 页出现；用 div 而不是 h2，避免污染右侧目录与搜索索引。
#   目的是「在 Reference 里走不死」：查完字段还能往下动手。
PRACTICE = {
    'basics': [('新手入门 · 从零走到第一次修改', '/tutorial/'),
               ('常见修改 · Cookbook', '/common-edits/')],
    'modules': [('Cookbook · 让虫更多 / 更少', '/common-edits/#enemy-count'),
                ('Cookbook · 删掉某类敌人', '/common-edits/#remove-vanilla-enemies'),
                ('案例拆解 · 这些模块拼出来的完整难度', '/natural-selection/')],
    'enemies': [('Cookbook · 从难度里移除原版敌人', '/common-edits/#remove-vanilla-enemies'),
                ('案例拆解 · 锁血与生态重置怎么用敌人控制项', '/natural-selection/')],
    'wavespawners': [('案例拆解 · 动态怪池与波次生成', '/natural-selection/'),
                     ('Debug · 写了 WaveSpawner 却没有生成', '/tips/#debug-wavespawner')],
    'mutators': [('新手入门 · 早点学会 Vars', '/tutorial/#vars'),
                 ('案例拆解 · Trigger / Vars 的组合用法', '/natural-selection/'),
                 ('Debug · Mutator 不工作或报错', '/tips/#debug-mutator')],
    'faq': [('新手入门 · 从零走到第一次修改', '/tutorial/'),
            ('为什么没生效 · Debug', '/tips/')],
}

# R11 首页新人入口：① 三条入口 ② 3 步第一次修改 ③ 术语地图 ④ 我想做什么
#   链接一律写根绝对（relize() 会按页面深度改成相对），锚点全部经构建产物核对。
# R12：完整 6 步教程已移入「新手入门 · Getting Started」，首页只留极短预览。
HOME_PATHS = [
    ('第一次接触 CD2？', '新手入门 · 从零走到第一次修改', '/tutorial/', 'primary'),
    ('已经会写一点？', '常见修改 · Cookbook', '/common-edits/', ''),
    ('知道自己要找什么？', '进入 Reference 查表', '/toc/', ''),
]

HOME_STEPS = [
    '复制 <a href="/basics/#the-cd2-files">Hazard 5x2 最小示例</a>，粘进游戏里的 CD2 面板',
    '把 <code>EnemyCountModifier</code> 里的 <code>1.7</code> 改成 <code>2</code>'
    ' —— 见<a href="/modules/#difficultysetting">模块 · DifficultySetting</a>',
    '点 <code>Save</code> 保存，再进游戏验证；没变化就去'
    '<a href="/tips/">为什么没生效 · Debug</a>',
]

HOME_MAP = [
    ('Module 模块', '一个功能板块：补给、虫量上限、光照、矮人属性……',
     [('模块', '/modules/')]),
    ('Enemy / Descriptor', '某类敌人的配置 / 描述：血量、速度、抗性、外观',
     [('敌人配置', '/enemies/'), ('Direct 底层属性', '/direct/')]),
    ('Pool 怪池', '哪些敌人可以出现、按什么权重出现',
     [('模块 · 怪池', '/modules/#pools')]),
    ('Mutator', '让某个值跟着游戏条件变：加减乘、判断、按人数……',
     [('动态参数与逻辑控制', '/mutators/')]),
    ('WaveSpawner', '主动安排一波敌人：何时、在哪、多少、什么怪',
     [('波次生成器', '/wavespawners/')]),
]

# R12 §16：顺序永远是「用户目标 → 技术机制 → Reference」，不拿具体字段当入口
#   （旧版把「特定条件下的敌人」直接指向 ByTime，会让人以为条件只有时间一种）
HOME_WANT = [
    ('让虫更多 / 更少', '虫量倍率 + 上限',
     [('Cookbook · 增加或减少敌人数量', '/common-edits/#enemy-count'),
      ('模块 · 难度设置 DifficultySetting', '/modules/#difficultysetting'),
      ('模块 · 虫量上限 Caps', '/modules/#caps')]),
    ('删掉 / 换掉某类敌人', '怪池',
     [('Cookbook · 从难度里移除原版敌人', '/common-edits/#remove-vanilla-enemies'),
      ('模块 · 怪池 Pools', '/modules/#pools')]),
    ('让某个敌人更肉 / 更快 / 更痛', '敌人控制项',
     [('敌人配置 · 敌人控制项', '/enemies/#enemy-controls')]),
    ('改某个敌人的底层数值', 'Direct',
     [('Direct 底层属性', '/direct/'),
      ('敌人配置 · Direct 特殊控制', '/enemies/#direct-special-control')]),
    ('满足条件后生成一波敌人', '条件判断 + 生成器',
     [('Mutators（条件与计算）', '/mutators/'),
      ('Mutator · 触发类 Trigger', '/mutators/#trigger-mutators'),
      ('波次生成器 WaveSpawners', '/wavespawners/')]),
    ('按玩家人数改变数值', '按人数选择值',
     [('Mutator · 根据玩家数量', '/mutators/#byplayercount'),
      ('基础部分 · 难度文件要求', '/basics/#the-cd2-files')]),
    ('按补给次数 / 任务阶段改变难度', '读游戏状态 → 改数值',
     [('Mutator · 根据呼叫补给次数', '/mutators/#byresuppliescalled'),
      ('动态参数与逻辑控制（全部条件）', '/mutators/')]),
    ('做动态事件（条件 → 延迟 → 持续）', 'Trigger 系列',
     [('Mutator · 触发类 Trigger', '/mutators/#trigger-mutators')]),
    ('改远程敌人的投射物', 'Projectile',
     [('发射物 Projectiles', '/projectiles/')]),
    ('想让别人也能玩（公共房间）', '同步相关机制',
     [('FAQ · 我的难度能给别人玩吗', '/faq/#faq-public-match'),
      ('模块 · 敌人配置（同步 / 不同步）', '/modules/#enemies-enemiesnosync')]),
    ('改完没生效', '按症状排查',
     [('为什么没生效 · Debug', '/tips/'), ('FAQ · 改完难度文件，为什么游戏里没变化', '/faq/#faq-no-effect')]),
]

# 首页新增小节由 render 直接生成、不经过 extract，必须手工补进搜索索引的
# 章节级结果（关键词走 extract.py 的 SEARCH_KW，见那边）。
HOME_SEARCH = {
    'headings': [{'id': 'first-edit', 'level': 2, 'text': '第一次修改：3 步，5 分钟'},
                 {'id': 'map', 'level': 2, 'text': 'CD2 是怎么运作的（术语地图）'},
                 {'id': 'what', 'level': 2, 'text': '我想做什么？'}],
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
        # R13：列表项也能带稳定锚点（FAQ 的 id="faq-…" 靠这条落进输出）
        aid = f' id="{esc(it["id"])}"' if it.get('id') else ''
        cls = f' class="{esc(it["cls"])}"' if it.get('cls') else ''
        zh, en = it.get('zh'), it.get('en')
        if zh and en:
            out.append(f'<li{aid}{cls}>{zh}{fold(en)}</li>')
        elif zh:
            out.append(f'<li{aid}{cls}>{zh}</li>')
        else:
            out.append(f'<li{aid} lang="en"{cls}>{en}</li>')
    return out



# 与中文同义的短英文（生成折叠条纯属噪音）
_TRIVIAL_EN = re.compile(r'^\s*(example|note|tips?|warning|caution|default|' 
                         r'usage|description|result|output|input)\s*[:：]?\s*$', re.I)


def _skip_fold(zh, en):
    """英文原文过短且只是中文的等价标签时，不生成折叠条。"""
    e = (en or '').strip()
    if not e:
        return True
    if len(e) < 20 and _TRIVIAL_EN.match(e):
        return True
    return False


def render_block(b, has_table=False, anchor=''):
    t = b['t']
    if t == 'h':
        lv = b['level']
        return f'<h{lv} id="{esc(b["id"])}">{esc(b["text"])}</h{lv}>'
    if t == 'p':
        if 'mt-io' in (b.get('cls') or ''):
            # 类型栏 → 字段表 + 返回；本节正文里已有字段表时只补「返回」
            txt = b.get('zh') or b.get('en') or ''
            return (mtio2.ret_only_html(txt, anchor=anchor) if has_table
                    else mtio2.to_html(txt, anchor=anchor))
        cls = f' class="{esc(b["cls"])}"' if b.get('cls') else ''
        zh, en = b.get('zh'), b.get('en')
        if zh and en:
            if _skip_fold(zh, en):
                return f'<p{cls}>{zh}</p>'
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
def nav_order(nav):
    """R11：按 NAV_GROUPS 重排导航 —— 分组必须连续，否则左导航里会一段段跳。
    未列进分组的页面按原顺序追加到末尾（不会被丢掉）。"""
    by = {}
    for n in nav:
        by.setdefault(n['slug'], n)
    out, seen = [], set()
    for _, slugs in NAV_GROUPS:
        for s in slugs:
            if s in by and s not in seen:
                out.append(by[s])
                seen.add(s)
    for n in nav:
        if n['slug'] not in seen:
            out.append(n)
            seen.add(n['slug'])
    return out


def nav_group_title(slug, fallback):
    for title, slugs in NAV_GROUPS:
        if slug in slugs:
            return title
    return fallback


def _nav_link(n, cur):
    c = ' class="current"' if n['slug'] == cur else ''
    aria = ' aria-current="page"' if n['slug'] == cur else ''
    return f'<li><a href="{n["path"]}"{c}{aria}>{esc(n["label"])}</a></li>'


def drawer_html(nav, cur):
    """R11：在平铺列表里插入非链接分组标题（保持「首页 / 目录」仍是前两个 <a>）。"""
    items, prev = [], None
    for n in nav:
        g = nav_group_title(n['slug'], NAV_GROUP_OTHER)
        if g != prev:
            items.append(f'<li class="nav-head">{esc(g)}</li>')
            prev = g
        items.append(_nav_link(n, cur))
    return ('<nav class="drawer" id="drawer" aria-label="站点导航">'
            f'<ul class="drawer-list">{"".join(items)}</ul></nav>')


def topbar_html():
    # R15 §P0-1：搜索改成「原位展开 + 下拉结果面板」——面板就挂在按钮下方，
    # 没有遮罩层、不锁滚动，读者可以边看正文边查（移动端在 CSS 里退化为顶部页）。
    return f'''<header class="topbar">
  <div class="topbar-inner">
    <div class="topbar-left">
      <button class="icon-btn" id="drawer-btn" type="button" aria-label="打开导航" aria-expanded="false" aria-controls="drawer">{MENU_ICON}</button>
      <a class="brand" href="/"><img src="/assets/img/logo.svg" alt="" width="22" height="22" loading="eager"><span>{esc(SITE_NAME)}</span></a>
    </div>
    <div class="topbar-mid">
      <div class="topbar-spacer"></div>
      <div class="search-slot" id="search-slot">
        <button class="search-btn" type="button" data-search-open aria-label="搜索文档" aria-expanded="false" aria-controls="search-panel">{SEARCH_ICON}<span class="search-btn-text">搜索</span><kbd>Ctrl K</kbd></button>
        <div class="search-panel" id="search-panel" hidden>
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
    items, cur = [], None
    for h in hs:
        if h['level'] == 2:
            cur = h['id']
            items.append(f'<li class="lvl-2" data-h="{esc(h["id"])}">'
                         f'<a href="#{esc(h["id"])}">{esc(h["text"])}</a></li>')
        elif h['level'] == 3 and use3:
            # R10：带上父级 id，前端据此决定「滚到这一节才展开」
            p = f' data-p="{esc(cur)}"' if cur else ''
            items.append(f'<li class="lvl-3"{p}>'
                         f'<a href="#{esc(h["id"])}">{esc(h["text"])}</a></li>')
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
REMOVED_SLUGS = {'mev-dea', 'tutorials'}


def strip_dead_links(t):
    """把 href 指向已删页面的 <a> 拆掉，只保留内部文字。"""
    def rep(m):
        href = m.group(1)
        path = re.sub(r'^(?:\.\./)+|^/', '', href)
        if path.split('/')[0].split('#')[0] in REMOVED_SLUGS:
            return m.group(2)
        return m.group(0)
    return re.sub(r'<a\b[^>]*href="([^"]*)"[^>]*>(.*?)</a>', rep, t, flags=re.S)


# R6：资源版本号 —— 让 CSS/JS 更新后浏览器立即取新版，不再吃旧缓存
ASSET_VER = '0'


def compute_asset_ver():
    """取 site.css + site.js 的内容指纹前 8 位。"""
    import hashlib
    h = hashlib.md5()
    for rel in ('assets/css/site.css', 'assets/js/site.js'):
        p = os.path.join(SITE, rel)
        if os.path.exists(p):
            h.update(io.open(p, 'rb').read())
    return h.hexdigest()[:8]


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
<link rel="stylesheet" href="/assets/css/site.css?v={ASSET_VER}">
</head>
<body{' class="has-toc"' if has_toc else ''}>
<a class="skip-link" href="#main">跳到正文</a>
{topbar_html()}
<div class="read-progress" id="read-progress" aria-hidden="true"></div>
<div class="drawer-overlay" id="drawer-overlay"></div>
{body}
{footer_html(nav)}
 <button class="btn jump-back" id="jump-back" type="button" aria-label="返回上一位置" hidden>&larr; 返回上一位置</button>
<button class="to-top" id="to-top" type="button" aria-label="返回顶部">{ARROW_UP}</button>
<script src="/assets/js/site.js?v={ASSET_VER}" defer></script>
</body>
</html>'''
    page = fix_images(page, prefix)
    return relize(page, prefix)


def content_page(page, nav):
    slug = page['slug']
    prefix = '../'
    navitem = next((n for n in nav if n['slug'] == slug), None) or HOME
    title = f'{navitem["label"]} — {SITE_NAME}'
    # R15 §P1-2：Mutators 页在最前面插入「按用途」索引，并让它进右侧目录
    idx = mutator_index_html(page) if slug == 'mutators' else ''
    toc_src = page
    if idx:
        toc_src = dict(page, headings=[{'id': 'mutator-index', 'level': 2,
                                        'text': '按用途查 Mutator'}] + page['headings'])
    toc, has_toc = toc_html(toc_src)
    # R12 §14：面包屑带层级 —— 从搜索 / 分享链接直接落进来的人，一眼知道自己在哪
    grp = nav_group_title(slug, '')
    crumb = '<a href="/">首页</a>'
    if grp:
        crumb += f' › <span class="crumb-g">{esc(grp)}</span>'
    crumb += f' › {esc(navitem["label"])}'
    main = [f'<main id="main" class="content">',
            f'<nav class="breadcrumb" aria-label="面包屑">{crumb}</nav>',
            f'<h1>{esc(navitem["label"])}</h1>']
    if idx:
        main.append(idx)
    if page.get('no_translation'):
        main.append('<div class="admonition notice"><div class="admonition-title">'
                    '本页尚未翻译</div><p>以下为英文原文。</p></div>')
    # 预扫描：每个 h2 小节内是否已有表格（用于「正文已有字段表」判断）
    blks = list(page['blocks'])
    # 结构：一句话说明 → 字段表 → 返回 → 详细说明…
    # 把紧跟类型栏的那段描述提到字段表之前（交换后要跳过，否则会一路下移）
    i = 0
    while i < len(blks) - 1:
        if blks[i]['t'] == 'p' and 'mt-io' in (blks[i].get('cls') or ''):
            if blks[i + 1]['t'] == 'p':
                # 有人工重写的简介时，替换掉原简介的中文
                anc = next((blks[k].get('id') for k in range(i, -1, -1)
                            if blks[k]['t'] == 'h' and blks[k].get('level') == 2), '')
                new_intro = INTRO.get((anc or '').lower())
                if new_intro:
                    nxt = dict(blks[i + 1])
                    nxt['zh'] = new_intro
                    blks[i + 1] = nxt
                blks[i], blks[i + 1] = blks[i + 1], blks[i]
                i += 1
        i += 1
    sec_tbl = [False] * len(blks)
    starts = [i for i, b in enumerate(blks) if b['t'] == 'h' and b.get('level') == 2]
    starts.append(len(blks))
    for a, z in zip(starts, starts[1:]):
        if any(blks[j]['t'] == 'table' for j in range(a, z)):
            for k in range(a, z):
                sec_tbl[k] = True
    cur_anchor = ''
    for i, b in enumerate(blks):
        if b['t'] == 'h' and b.get('level') == 2:
            cur_anchor = b.get('id') or ''
        main.append(render_block(b, has_table=sec_tbl[i], anchor=cur_anchor))
    pr = PRACTICE.get(slug)
    if pr:
        main.append('<aside class="admonition practice">'
                    '<div class="admonition-title">想继续实践？</div><ul>' +
                    ''.join(f'<li><a href="{h}">{esc(t)}</a></li>' for t, h in pr) +
                    '</ul></aside>')
    main.append(page_nav_html(nav, slug))
    main.append('</main>')
    body = (f'<div class="layout{" has-toc" if has_toc else ""}">'
            + drawer_html(nav, slug) + '\n'.join(main) + toc + '</div>')
    return shell(title, page['desc'] or TAGLINE, page['path'], body, nav, slug,
                 prefix, has_toc)


# R15 §P1-2 / R16 ③：Mutators 页的「按用途」索引。
#   每个分组一张卡片，卡片内是一个个 chip（中文名 + 英文名的小链接）。
#   多合一条目（加/减/乘/除…、LockFloat/Boolean/String）拆成独立 chip——它们指向
#   同一节，但读起来是「一个词一个 chip」，不再是塞满一行的一长串。
#   没列到的节自动落进「其他」卡片 → 「索引覆盖全部 Mutator」是结构上保证的。
MUTATOR_GROUPS = [
    ('数学、计数与状态', 'Math & State', [
        ('累加', 'Accumulate', 'accumulate'),
        ('最大值', 'Max', 'max'), ('最小值', 'Min', 'min'),
        ('变量', 'Delta', 'delta'), ('序列', 'Sequence', 'Sequence'),
        ('加', 'Add', 'add-subtract-multiply-divide-pow-modulo-round-ceil-floor'),
        ('减', 'Subtract', 'add-subtract-multiply-divide-pow-modulo-round-ceil-floor'),
        ('乘', 'Multiply', 'add-subtract-multiply-divide-pow-modulo-round-ceil-floor'),
        ('除', 'Divide', 'add-subtract-multiply-divide-pow-modulo-round-ceil-floor'),
        ('幂', 'Pow', 'add-subtract-multiply-divide-pow-modulo-round-ceil-floor'),
        ('取模', 'Modulo', 'add-subtract-multiply-divide-pow-modulo-round-ceil-floor'),
        ('四舍五入', 'Round', 'add-subtract-multiply-divide-pow-modulo-round-ceil-floor'),
        ('向上取整', 'Ceil', 'add-subtract-multiply-divide-pow-modulo-round-ceil-floor'),
        ('向下取整', 'Floor', 'add-subtract-multiply-divide-pow-modulo-round-ceil-floor'),
        ('限制', 'Clamp', 'clamp')]),
    ('条件、选择与触发', 'Logic & Trigger', [
        ('条件判断', 'If', 'if'), ('浮点数条件判断', 'IfFloat', 'iffloat'),
        ('与', 'And', 'and-or-not'), ('或', 'Or', 'and-or-not'), ('非', 'Not', 'and-or-not'),
        ('非零判断', 'Nonzero', 'Nonzero'),
        ('选择', 'Select', 'Select'), ('从数组选择', 'SelectFromArray', 'selectfromarray'),
        ('锁定浮点数', 'LockFloat', 'LockFloat, LockBoolean, LockString'),
        ('锁定布尔值', 'LockBoolean', 'LockFloat, LockBoolean, LockString'),
        ('锁定字符串', 'LockString', 'LockFloat, LockBoolean, LockString'),
        ('触发类', 'Trigger', 'trigger-mutators')]),
    ('时间与节奏', 'Time', [
        ('根据时间', 'ByTime', 'bytime'), ('倒计时', 'Countdown', 'countdown'),
        ('秒表', 'StopWatch', 'StopWatch'), ('时间变量', 'TimeDelta', 'timedelta'),
        ('撤离已用时间', 'ElapsedExtraction', 'elapsedextraction'),
        ('轮切', 'SquareWave', 'squarewave')]),
    ('任务阶段与进度', 'Mission phase', [
        ('根据深潜阶段', 'ByDDStage', 'byddstage'),
        ('根据炼油阶段', 'ByRefineryPhase', 'byrefineryphase'),
        ('根据设施破坏阶段', 'BySaboPhase', 'bysabophase'),
        ('根据搜救行动阶段', 'BySalvagePhase', 'bysalvagephase'),
        ('根据执勤护送阶段', 'ByEscortPhase', 'byescortphase'),
        ('根据任务类型', 'ByMissionType', 'bymissiontype'),
        ('根据次要目标', 'BySecondary', 'bysecondary'),
        ('根据次要完成情况', 'SecondaryFinished', 'SecondaryFinished'),
        ('守点进度', 'DefenseProgress', 'defenseprogress')]),
    ('敌人与战斗', 'Enemies', [
        ('已击杀敌人数量', 'EnemiesKilled', 'enemieskilled'),
        ('近期生成敌人计数', 'EnemiesRecentlySpawned', 'enemiesrecentlyspawned'),
        ('敌人生成冷却', 'EnemyCooldown', 'enemycooldown'),
        ('敌人血量比例', 'EnemyHealth', 'EnemyHealth'),
        ('敌人距离', 'EnemyDistance', 'EnemyDistance'),
        ('当前敌人计数', 'EnemyCount', 'enemycount'),
        ('描述符是否可用', 'DescriptorExists', 'descriptorexists')]),
    ('矮人与团队', 'Dwarves & team', [
        ('矮人数量', 'DwarfCount', 'dwarfcount'),
        ('团队弹药量比例', 'DwarvesAmmo', 'dwarvesammo'),
        ('倒地矮人数量', 'DwarvesDown', 'dwarvesdown'),
        ('倒地时间', 'DwarvesDownTime', 'dwarvesdowntime'),
        ('矮人总倒地次数', 'DwarvesDowns', 'dwarvesdowns'),
        ('团队生命值比例', 'DwarvesHealth', 'dwarveshealth'),
        ('矮人复活次数', 'DwarvesRevives', 'dwarvesrevives'),
        ('团队护盾值比例', 'DwarvesShield', 'dwarvesshield'),
        ('钢铁意志剩余数量', 'IWsLeft', 'iwsleft'),
        ('钻机数量检测', 'DrillerCount', 'drillercount'),
        ('工程数量计数', 'EngineerCount', 'engineercount'),
        ('枪手数量计数', 'GunnerCount', 'gunnercount'),
        ('侦察数量计数', 'ScoutCount', 'scoutcount')]),
    ('资源与补给', 'Resources & resupply', [
        ('存放资源', 'DepositedResource', 'depositedresource'),
        ('携带资源计数', 'HeldResource', 'heldresource'),
        ('资源总量', 'TotalResource', 'totalresource'),
        ('补给剩余使用次数', 'ResupplyUsesLeft', 'resupplyusesleft'),
        ('已呼叫补给次数', 'ResuppliesCalled', 'resuppliescalled'),
        ('已消耗补给使用次数', 'ResupplyUsesConsumed', 'resupplyusesconsumed'),
        ('根据呼叫补给次数', 'ByResuppliesCalled', 'byresuppliescalled')]),
    ('游戏条件与任务期间', 'Game state & During', [
        ('根据生物群系', 'ByBiome', 'bybiome'), ('ByDNA', 'ByDNA', 'bydna'),
        ('根据玩家数量', 'ByPlayerCount', 'byplayercount'),
        ('是否在太空站', 'IfOnSpaceRig', 'ifonspacerig'),
        ('任务期间', 'DuringMission', 'duringmission'),
        ('宣告潮期间', 'DuringGenericSwarm', 'duringgenericswarm'),
        ('守点期间', 'DuringDefend', 'duringdefend'),
        ('撤离期间', 'DuringExtraction', 'duringextraction'),
        ('对战无畏异虫期间', 'DuringDread', 'duringdread'),
        ('定点提取撤离期间', 'DuringPECountdown', 'duringpecountdown'),
        ('蛋潮期间', 'DuringEggAmbush', 'duringeggambush'),
        ('钻井电梯期间', 'DuringDrillevator', 'duringdrillevator'),
        ('遭遇潮期间', 'DuringEncounters', 'duringencounters')]),
    ('随机', 'Random', [
        ('随机值', 'Random', 'random'), ('随机选择', 'RandomChoice', 'randomchoice'),
        ('每个任务随机选择一次', 'RandomChoicePerMission', 'randomchoicepermission')]),
    ('位置与距离', 'Position', [
        ('空降舱距离', 'DistanceToDroppod', 'DistanceToDroppod'),
        ('矿骡与空降舱的距离', 'MuleDistanceToDroppod', 'MuleDistanceToDroppod')]),
    ('值与字符串', 'Value & string', [
        ('整数转字符串', 'Int2String', 'int2string'),
        ('浮点数转字符串', 'Float2String', 'float2string'),
        ('字符串拼接', 'Join', 'join')]),
]


def _chip(zh, en, anchor):
    return (f'<li><a class="mut-chip" href="#{esc(anchor)}">{esc(zh)}'
            f'<span class="en">{esc(en)}</span></a></li>')


def mutator_index_html(page):
    """按用途索引：卡片式分组 + chip；未列到的节自动进「其他」，保证无遗漏。"""
    hs = [h for h in page['headings'] if h['level'] == 2]
    byid = {h['id']: h for h in hs}
    covered, cards = set(), []
    for zh, en, chips in MUTATOR_GROUPS:
        items = []
        for czh, cen, aid in chips:
            if aid in byid:
                covered.add(aid)          # 只用于「其他」兜底；chip 本身不去重
                items.append(_chip(czh, cen, aid))
        if items:
            cards.append((zh, en, items))
    rest = []
    for h in hs:
        if h['id'] in covered:
            continue
        parts = (h['text'] or '').split(' · ', 1)
        rest.append(_chip(parts[0].strip(), parts[1].strip() if len(parts) > 1 else '',
                          h['id']))
    if rest:
        cards.append(('其他', 'Other', rest))
    if not cards:
        return ''
    body = ''.join(
        f'<details class="mut-card" open><summary><b>{esc(zh)}</b>'
        f'<span class="en">{esc(en)}</span></summary>'
        f'<ul>{"".join(items)}</ul></details>'
        for zh, en, items in cards)
    return ('<h2 id="mutator-index">按用途查 Mutator</h2>'
            '<p>不知道某个 Mutator 叫什么？直接在下框里筛，或者按用途找——'
            '每个标签点进去就是它的完整说明。</p>'
            '<p class="mut-filter"><input id="mut-filter" type="search" '
            'placeholder="筛选：输入中文名或英文名" aria-label="筛选 Mutator"></p>'
            f'<div class="mut-idx">{body}</div>')


def cards_html(nav, pages):
    """章节卡片（目录页用）—— R11：按 NAV_GROUPS 分组，与左导航同构。"""
    cards = {}
    for n in nav:
        if n['slug'] in ('', 'toc'):
            continue
        desc = CARD_DESC.get(n['slug'], clean_desc(pages.get(n['slug'], {}).get('desc') or ''))
        en = n['label'].split(' · ')[-1] if ' · ' in n['label'] else ''
        zh = n['label'].split(' · ')[0]
        cards[n['slug']] = (
            f'<a class="card" href="{n["path"]}">'
            f'<span class="card-icon">{icon(n["slug"])}</span>'
            f'<span class="card-main">'
            f'<span class="card-title">{esc(zh)}'
            + (f'<span class="card-en">{esc(en)}</span>' if en and en != zh else '')
            + f'</span><span class="card-desc">{esc(desc)}</span></span></a>')
    # 「获取 CD2」不是站内页，挂在第一组的开头（新人第一件事就是装它）
    get_cd2 = ('<a class="card" href="/resources/#get-cd2">'
               f'<span class="card-icon">{icon("get-cd2")}</span>'
               '<span class="card-main"><span class="card-title">获取 CD2'
               '<span class="card-en">Get CD2</span></span>'
               '<span class="card-desc">官方 Discord、友站与中文交流群</span></span></a>')
    groups, seen = [], set()
    for title, slugs in NAV_GROUPS:
        items = [get_cd2] if not groups else []
        for s in slugs:
            if s in cards and s not in seen:
                items.append(cards[s])
                seen.add(s)
        if items:
            groups.append(f'<div class="card-group">'
                          f'<h2 class="card-group-title">{esc(title)}</h2>'
                          f'<div class="card-grid">{"".join(items)}</div></div>')
    rest = [cards[n['slug']] for n in nav if n['slug'] in cards and n['slug'] not in seen]
    if rest:
        groups.append(f'<div class="card-group">'
                      f'<h2 class="card-group-title">{esc(NAV_GROUP_OTHER)}</h2>'
                      f'<div class="card-grid">{"".join(rest)}</div></div>')
    return ''.join(groups)


def stats_html(nav, pages):
    """站点规模统计条（数字从内容里现算）。"""
    n_chapters = len([n for n in nav if n['slug'] not in ('', 'toc')])
    n_direct = pages.get('direct', {}).get('stats', {}).get('blocks', {}).get('h', 0)
    n_code = sum(p.get('stats', {}).get('blocks', {}).get('code', 0) for p in pages.values())
    return (f'<div class="stats">'
            f'<span><b>{n_chapters}</b> 个章节</span>'
            f'<span><b>{n_direct}</b> 种敌人控制项</span>'
            f'<span><b>{n_code}</b> 段配置示例</span></div>')


def _linx(pairs):
    return ' · '.join(f'<a href="{h}">{esc(t)}</a>' for t, h in pairs)


def home_entry_html():
    """R11：首页三条入口（问题 → 按钮），替代原来两个孤立按钮。"""
    items = []
    for q, label, href, cls in HOME_PATHS:
        btn = f'btn {cls}' if cls else 'btn'
        items.append(f'<li><span class="hp-q">{esc(q)}</span>'
                     f'<a class="{btn}" href="{href}">{esc(label)}</a></li>')
    return f'<ul class="home-paths">{"".join(items)}</ul>'


def home_sections_html():
    """R11：5 分钟第一个难度 / 术语地图 / 我想做什么 —— 只做导航与出路指向，
    机制解释一律留在 Reference（首页不重复正文）。"""
    steps = ''.join(f'<li>{s}</li>' for s in HOME_STEPS)
    maprows = ''.join(f'<tr><td>{esc(k)}</td><td>{esc(v)}</td><td>{_linx(l)}</td></tr>'
                      for k, v, l in HOME_MAP)
    wantrows = ''.join(f'<tr><td>{esc(k)}</td><td>{esc(v)}</td><td>{_linx(l)}</td></tr>'
                       for k, v, l in HOME_WANT)
    return f'''<h2 id="first-edit">第一次修改：3 步，5 分钟</h2>
<p>不需要先读完文档。改一个数字、看一眼游戏里的变化，你就入门了。</p>
<ol class="home-steps">{steps}</ol>
<p class="home-next">每一步的出处、以及之后该走哪条路，见
<a href="/tutorial/">新手入门 · Getting Started</a>；想直接找事做，看下面的
<a href="#what">「我想做什么？」</a>。</p>
<h2 id="map">CD2 是怎么运作的</h2>
<p>一个 CD2 难度 = <b>基础配置</b>（Module / Pool / Enemy）+ <b>动态逻辑</b>（Mutator / Trigger / WaveSpawner）。
先知道哪个词管哪一块，再去查它的完整字段。</p>
<div class="table-wrap"><table>
<thead><tr><th>术语</th><th>它管什么</th><th>去哪看</th></tr></thead>
<tbody>{maprows}</tbody></table></div>
<h2 id="what">我想做什么？</h2>
<p>从「玩法目标」反查「技术实现」：每行给出这类需求通常要动什么，以及先看哪一页。
字段的完整含义一律在 Reference，本页只负责把你送过去。</p>
<div class="table-wrap"><table>
<thead><tr><th>我想做什么</th><th>通常要动什么</th><th>先看这里</th></tr></thead>
<tbody>{wantrows}</tbody></table></div>'''


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
    # R11：三条入口插在引言之后、截图之前（不恢复 hero，也不用卡片）
    pos = next((k for k, h in enumerate(intro) if '<figure' in h), len(intro))
    intro.insert(pos, home_entry_html())
    if log_items:
        log.append('<ul class="update-log">' + ''.join(log_items) + '</ul>')
    body = f'''<div class="layout">
{drawer_html(nav, '')}
<div class="home-main">
<main id="main">
<div class="home-wrap">
  <h1>{esc(SITE_NAME)}</h1>
  <div class="home-lead">{''.join(intro)}</div>
  {home_sections_html()}
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
{cards_html(nav, pages)}
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
  <p>你访问的地址没有对应的页面。</p>
  <p><b>你可能在找：</b></p>
  <ul>
    <li><a href="{REPO_PATH}/tutorial/">新手入门 · Getting Started</a> —— 完全不懂 CD2？从这里开始</li>
    <li><a href="{REPO_PATH}/common-edits/">常见修改 · Cookbook</a> —— 一个目标，一个最小方案</li>
    <li><a href="{REPO_PATH}/toc/">Reference · 目录</a> —— 查字段、查机制</li>
  </ul>
  <p>站内搜索：回到任意页面后按 <kbd>Ctrl</kbd>+<kbd>K</kbd>。</p>
  <p>旧站路径变更对照：</p>
  <ul>
    <li><code>Common%20edits/</code> → 现为<a href="{REPO_PATH}/common-edits/">常见修改 · Cookbook</a></li>
    <li><code>/grouped_cooldowns/</code> → 该页已删除，见<a href="{REPO_PATH}/toc/">目录</a></li>
    <li><code>/search.html</code> → 站内搜索（按 <kbd>Ctrl</kbd>+<kbd>K</kbd>）</li>
  </ul>
  <p><a class="btn" href="{REPO_PATH}/toc/">打开目录</a> <a class="btn" href="{REPO_PATH}/">回到首页</a></p>
</main>
<script>
(function(){{
  var BASE = '{REPO_PATH}';
  /* 旧站路径 + 常见猜测路径（GitHub Pages 无服务端重定向，只能在这里兜） */
  var LEGACY = {{
    '/getting-started/': '/tutorial/',
    '/getting-started': '/tutorial/',
    '/cookbook/': '/common-edits/',
    '/cookbook': '/common-edits/',
    '/debug/': '/tips/',
    '/debug': '/tips/',
    '/common edits/': '/common-edits/',
    '/common edits': '/common-edits/',
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
def wtext(path, s):
    """统一按 LF 落盘。

    内容里可能已经带 CRLF（来自上游 HTML / 切片）。若用默认的 open(..., 'w')
    去写，Windows 会把每个 '\\n' 再翻成 '\\r\\n'，于是出现 '\\r\\r\\n' ——
    这种**落单的 CR** 会让 git 把整个文件判定成二进制（i/-text），从此
    它的 diff 在版本历史里完全看不见。所以这里先归一，再用 newline='' 写。
    """
    s = s.replace('\r\n', '\n').replace('\r', '\n')
    io.open(path, 'w', encoding='utf-8', newline='').write(s)


def write_sitemap(nav):
    rows = []
    for n in nav:
        loc = SITE_URL + (n['path'] if n['path'] != '/' else '/')
        rows.append(f'  <url><loc>{H.escape(loc)}</loc></url>')
    xml = ('<?xml version="1.0" encoding="UTF-8"?>\n'
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
           + '\n'.join(rows) + '\n</urlset>\n')
    wtext(os.path.join(SITE, 'sitemap.xml'), xml)
    wtext(os.path.join(SITE, 'robots.txt'),
          'User-agent: *\nAllow: /\n\nSitemap: %s/sitemap.xml\n' % SITE_URL)
    wtext(os.path.join(SITE, '.nojekyll'), '')


def main():
    global MEDIA, ASSET_VER
    MEDIA = json.load(io.open(os.path.join(BUILD, 'media.json'), encoding='utf-8'))
    ASSET_VER = compute_asset_ver()
    print('资源版本号:', ASSET_VER)
    nav = json.load(io.open(os.path.join(BUILD, 'nav.json'), encoding='utf-8'))
    # R5：目录页插在首页之后（导航、翻页、页脚地图、sitemap 都会自动带上）
    if not any(n['slug'] == 'toc' for n in nav):
        nav.insert(1, {'slug': 'toc', 'path': '/toc/', 'label': '目录 · Contents',
                       'label_raw': ''})
    # R11：按分组重排（分组必须连续）—— 左导航、翻页、页脚地图、目录卡片、sitemap 共用
    nav = nav_order(nav)
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
        wtext(os.path.join(d, 'index.html'), out)
        rows.append((slug, len(out), len(p['blocks'])))

    wtext(os.path.join(SITE, 'index.html'),
          strip_dead_links(home_page(nav, pages)))
    d = os.path.join(SITE, 'toc')
    os.makedirs(d, exist_ok=True)
    out = strip_dead_links(toc_page(nav, pages))
    wtext(os.path.join(d, 'index.html'), out)
    rows.append(('toc', len(out), 0))
    wtext(os.path.join(SITE, '404.html'), strip_dead_links(notfound_page()))
    # R11：把首页新人入口的章节补进搜索索引（它们由 render 生成，不经过 extract）
    # R12：关键词改走 extract.py 的 SEARCH_KW（kw 字段），这里只补章节级结果
    idx = json.loads(io.open(os.path.join(BUILD, 'search-index.json'),
                             encoding='utf-8').read())
    home_idx = next((p for p in idx if p.get('slug') == ''), None)
    if home_idx is not None:
        home_idx['headings'] = (home_idx.get('headings') or []) + HOME_SEARCH['headings']
    wtext(os.path.join(SITE, 'search-index.json'),
          json.dumps(idx, ensure_ascii=False, separators=(',', ':')))
    write_sitemap(nav)

    L = ['%-14s %10s %8s' % ('slug', 'HTML字节', '区块数'), '-' * 36]
    L += ['%-14s %10s %8s' % (a, f'{b:,}', c) for a, b, c in rows]
    wtext(os.path.join(ROOT, 'tools', 'render_report.txt'), '\n'.join(L))
    print('\n'.join(L))
    print('\nindex.html + 404.html + sitemap.xml + robots.txt + .nojekyll + %d 个内容页' % len(rows))


main()
