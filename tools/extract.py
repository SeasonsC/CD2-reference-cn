# -*- coding: utf-8 -*-
"""
CD2 参考文档 v2 · 内容提取器（M1）
────────────────────────────────────────────────────────────
把旧 MkDocs 产物 HTML 提取为**结构化 JSON**，与渲染完全解耦。

按施工方案 v2.1 实现：
  §3.1  定位正文 / h1 剥离 / 保留标题 id / 代码块还原纯文本 / 表格外包 /
        内链重写根绝对路径 / 剥内联样式 / 外链 target=_blank / 双语配对 / 搜索索引
  §3.2  路径重写映射表
  §3.4  盘古之白（中英文间加空格）
  §3.5  成对段落（中文 + 英文折叠）· 单飞英文保留 · 纯英页标记
  §5    标题统一「中文 · 英文」/「英文 · 中文」（direct 页反向）

输出：build/content/<slug>.json、build/nav.json、build/search-index.json
      tools/{extract_report,pairing_report,heading_report}.txt
"""
import os, re, io, json, posixpath
from lxml import html as LH

SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'CD2-upstream-src')   # 上游源（MkDocs 老站 + 中文编辑）
DEST = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILD = os.path.join(DEST, 'build')
CONTENT = os.path.join(BUILD, 'content')

APPLY_PANGU = True          # §3.4 盘古之白
CJK = re.compile(r'[\u4e00-\u9fff]')
LAT = re.compile(r'[A-Za-z]')

# 页面清单：(旧路径, slug)
PAGES = [
    ('index.html', ''), ('faq/index.html', 'faq'), ('basics/index.html', 'basics'),
    ('modules/index.html', 'modules'), ('enemies/index.html', 'enemies'),
    ('direct/index.html', 'direct'), ('wavespawners/index.html', 'wavespawners'),
    ('projectiles/index.html', 'projectiles'), ('mutators/index.html', 'mutators'),
    ('resources/index.html', 'resources'), ('tips/index.html', 'tips'),
    ('natural-selection/index.html', 'natural-selection'),
    ('Common edits/index.html', 'common-edits'),
    ('tutorial/index.html', 'tutorial'),
]
# R5：已删除的页面 —— 指向它们的 <a> 一律拆掉只留文字，避免死链
#   mev-dea 整页删除；tutorials 内容并入 resources 的「其他资源」
#   common-edits 已在 R12 恢复（它就是「常见修改 · Cookbook」）
REMOVED = {'mev-dea', 'tutorials'}
# 标题方向：direct 页是「英文键 · 中文」，其余「中文 · 英文」（§5）
EN_FIRST_PAGES = {'direct'}

DIR_MAP = {'common edits': 'common-edits', 'grouped_cooldowns': 'tutorials', '': ''}
KNOWN_DIRS = {p[1] for p in PAGES if p[1]} | {'toc'}   # toc 由 render.py 合成，不在上游页里
ASSET_MAP = {
    'pictures/cd2-modhub.png': '/assets/media/cd2-modhub.webp',
    'pictures/countdown-mutator.png': '/assets/media/countdown-mutator.webp',
    'pictures/orange-septic.png': '/assets/media/orange-septic.webp',
    'pictures/ice-spreader.gif': '/assets/media/ice-spreader.gif',
    'media/Materials-1.pdf': '/assets/media/Materials-1.pdf',
    'img/favicon.ico': '/assets/img/favicon.svg',
}

REPORT = {'pairs': [], 'lone_en': [], 'headings': [], 'warnings': []}

# ── R12：人话搜索 ───────────────────────────────────────────────────────
#   新人不会输入 EnemyCountModifier，他们会输入「虫更多」「删怪」「动态刷怪」。
#   这些词**不进正文、不进摘要**，只在建索引时并进倒排表（site.js 里一行）。
#   页面自己的正文照旧；这里只补「用户的说法 → 正式术语」这层桥。
SEARCH_KW = {
    # 首页只接「导航类说法」——具体目标交给具体页面，避免首页盖住 Cookbook / Debug
    '': '我想做什么 第一次修改 从哪里开始 从哪里入手 新手 新手怎么开始 怎么开始 入门 术语 '
        '学习路线 我该看什么 完全不懂 第一步做什么',
    'tutorial': '新手 新手怎么开始 怎么开始 从零开始 从哪里入手 完全不懂 第一次 第一次修改 '
                '第一步做什么 我该看什么 教程 学习路线 五个词 cd2 是什么 长什么样 最小难度 '
                'vars watch 变量 怎么组织逻辑',
    'common-edits': '删怪 怎么删怪 删除敌人 移除敌人 去掉敌人 去掉水蛭 不要某种虫子 虫更多 '
                    '虫更少 虫变多 虫太少 虫太多 敌人更多 敌人更少 敌人变少 数量太多 数量太少 '
                    '虫量 数量 倍率 加虫 减虫 怪池 移除原版敌人 常见修改',
    'natural-selection': '案例 完整难度 实战 拆解 组合 一整套 怎么组合 机制怎么拼 综合 '
                         '参考案例 别人怎么写的 动态换池 兜底 锁血 加血 回血 硝石不够 '
                         '阶段评级',
    'basics': '基础 界面 文件格式 最小示例 最小难度 数组 数组怎么用 按人数 按玩家人数 '
              '每个玩家不同 修改一个数字 顶层字段 基准难度',
    'modules': '模块 顶层字段 虫量上限 上限 虫子上限 补给 补给太贵 怪池 硝石 硝石不够 '
               '硝石太多 改硝石 光照 矮人 回血 变量 信息 声音',
    'enemies': '敌人 怪物 血量 敌人血更多 敌人血更厚 敌人更肉 敌人太弱 加强敌人 虫子加强 '
               '爆炸虫 速度 抗性 材质 外观 精英 变种 生成器 同步 不同步 删掉某个敌人 '
               '敌人变强 敌人变弱',
    'direct': '底层 属性 默认值 血量 移动速度 抗性 敌人底层数值',
    'wavespawners': '波次 刷怪 动态刷怪 无宣告潮 生成一波 敌人波次 主动生成 刷怪器 '
                    '一波敌人 定时刷怪',
    'projectiles': '发射物 投射物 远程敌人 弹道 子弹 弹速 爆炸',
    'mutators': '动态 条件 计算 表达式 加减乘 判断 随机 计时 触发 按人数 按玩家人数 '
                '根据人数 按玩家数量 按时间 按阶段 补给以后虫变多 按补给次数 读游戏状态 '
                '加血 回血 变量 锁存',
    'resources': '资源 下载 获取 速查 默认值表 敌人名字 描述符 中英对照 外部链接 '
                 '公开房间 指南',
    'tips': '没生效 没变化 没效果 为什么没效果 为什么没生效 改了没生效 改了没变化 '
            '照着写没效果 不生效 无效 不工作 报错 排查 为什么 调试 常见错误 坑 调不通 '
            '看不到变化 联机问题 别人进不来 加血 回血',
    'faq': '别人进不来 朋友进不来 进不去 房间进不来 联机问题 需要装吗 兼容 卡不卡 '
           '从哪一页开始学',
}


# ── 工具 ────────────────────────────────────────────────────────────────
def txt(el):
    return re.sub(r'\s+', ' ', (el.text_content() or '')).strip()


def kind(t):
    t = (t or '').strip()
    if not t:
        return 'empty'
    c, l = bool(CJK.search(t)), bool(LAT.search(t))
    if c and l:
        return 'mixed'
    if c:
        return 'zh'
    if l:
        return 'en'
    return 'other'


def is_zh(t):
    """是否为「中文段」：中文字符占比 >= 10%（英文段里偶尔夹一个中文词不算）。"""
    t = (t or '').strip()
    if not t:
        return False
    return len(CJK.findall(t)) / len(t) >= 0.10


def is_en(t):
    return bool(t and t.strip() and not CJK.search(t))


def inner(el):
    s = LH.tostring(el, encoding='unicode')
    return s[s.index('>') + 1:s.rindex('</')]


# ── R2 §4：单元格 / 图注内「英文 → 中文」分行 ───────────────────────────
CJK1 = re.compile(r'[\u4e00-\u9fff]')


def wrap_after_br(html):
    """已有 <br> 分行的单元格：给最后一行的中文补上 .td-zh 包裹（R3 §5.1）。
    源站 Comment/Description 列本身就是「英文<br>中文」，但中文没有层级标记。"""
    if 'td-zh' in html:
        return html, False
    parts = re.split(r'(<br\s*/?>)', html, flags=re.I)
    idx = None
    for i in range(len(parts) - 1, -1, -1):
        if re.fullmatch(r'<br\s*/?>', parts[i] or '', re.I):
            idx = i
            break
    if idx is None:
        return html, False
    tail = ''.join(parts[idx + 1:]).strip()
    if not tail or not CJK1.search(tail):
        return html, False
    if len(re.findall(r'<(?!/)[^>]*>', tail)) != len(re.findall(r'</[^>]*>', tail)):
        return html, False
    return ''.join(parts[:idx + 1]) + f'<span class="td-zh">{tail}</span>', True


def split_bilingual(html):
    """把「英文…中文…」切成两行：英文一行 + <span class="td-zh">中文</span>。
    已经用 <br> 分行的，只补中文行的层级标记；含 <p> 块结构的不动。"""
    if re.search(r'<br\b', html, re.I):
        return wrap_after_br(html)
    if re.search(r'<p\b', html, re.I):
        return html, False
    # R5 ⑦：`Field name(字段名称)` / `MaxAngle(最大角度)` —— 英文后跟括号中文
    m0 = re.match(r'^([^（）()]*?)\s*[（(]\s*([^（）()]*)\s*[）)]\s*$', html)
    if m0 and not CJK1.search(m0.group(1)) and CJK1.search(m0.group(2)):
        en, zh = m0.group(1).strip(), m0.group(2).strip()
        if en and zh:
            return f'{en}<br><span class="td-zh">{zh}</span>', True
    m = CJK1.search(html)
    if not m:
        return html, False
    head, tail = html[:m.start()], html[m.start():]
    if not re.search(r'[A-Za-z]', head):
        return html, False
    # 切点必须落在标签之外、且前面标签成对闭合
    if len(re.findall(r'<(?!/)[^>]*>', head)) != len(re.findall(r'</[^>]*>', head)):
        return html, False
    head, tail = head.rstrip(), tail.strip()
    if not head or not tail:
        return html, False
    # 中文行开头若被截掉了英文词（如 "…Modhub.Modhub 中的"），把该词挪回中文行
    if ' ' in head:
        m2 = re.search(r'^(.*[.。!！?？:：;；])\s*([A-Za-z][A-Za-z0-9_\-]*)$', head)
        if m2 and ' ' in m2.group(1):
            head, tail = m2.group(1), m2.group(2) + ' ' + tail
    return f'{head}<br><span class="td-zh">{tail}</span>', True


def replace_inner(el, html):
    for ch in list(el):
        el.remove(ch)
    el.text = None
    frag = LH.fragment_fromstring(html, create_parent='span')
    el.text = frag.text
    for ch in list(frag):
        frag.remove(ch)
        el.append(ch)


def merge_translation_column(table):
    """R5 ④：把「翻译列」并进该行第一列，删掉那一列。命中两种形态：
      1) 表头含「翻译」；
      2) 表头为空、但正文里所有非空值都是纯中文（源站漏写表头的翻译列）。"""
    trs = table.xpath('.//tr')
    if not trs:
        return 0
    head = trs[0].xpath('./td | ./th')
    body = table.xpath('.//tbody/tr') or trs[1:]
    if not body:
        return 0
    ncol = max(len(tr.xpath('./td | ./th')) for tr in trs)

    def col_vals(c):
        out = []
        for tr in body:
            cs = tr.xpath('./td | ./th')
            out.append(cs[c].text_content().strip() if len(cs) > c else '')
        return out

    idx = None
    for i in range(1, ncol):
        h = head[i].text_content().strip() if len(head) > i else ''
        if '翻译' in h:
            idx = i
            break
        if not h:
            vals = [v for v in col_vals(i) if v]
            if vals and all(CJK1.search(v) and not re.search(r'[A-Za-z]', v) for v in vals):
                idx = i
                break
    if idx is None:
        return 0

    n = 0
    for tr in body:
        cs = tr.xpath('./td | ./th')
        if len(cs) <= idx:
            continue
        zh = inner(cs[idx]).strip()
        if not zh:
            continue
        first = cs[0]
        replace_inner(first, inner(first) + f'<br><span class="td-zh">{zh}</span>')
        n += 1
    for tr in trs:                                  # 删列（表头一起删）
        cs = tr.xpath('./td | ./th')
        if len(cs) > idx:
            tr.remove(cs[idx])
    REPORT['transcol'] = REPORT.get('transcol', 0) + 1
    return n


def drop_empty_columns(table):
    """R5 ⑧：正文里整列全空（表头可能还有字）的列直接删掉。"""
    trs = table.xpath('.//tr')
    if not trs:
        return 0
    body = table.xpath('.//tbody/tr') or trs[1:]
    if not body:
        return 0
    ncol = max(len(tr.xpath('./td | ./th')) for tr in trs)
    dropped = 0
    for c in range(ncol - 1, 0, -1):                # 第 0 列永远保留
        cs_all = [tr.xpath('./td | ./th') for tr in body]
        if not any(len(cs) > c for cs in cs_all):
            continue
        if all(len(cs) <= c or not cs[c].text_content().strip() for cs in cs_all):
            for tr in trs:
                cs = tr.xpath('./td | ./th')
                if len(cs) > c:
                    tr.remove(cs[c])
            dropped += 1
    if dropped:
        REPORT['emptycol'] = REPORT.get('emptycol', 0) + dropped
    return dropped


def is_empty_table(table):
    """R5：正文行内容全空的表（`<thead>Control</thead><tbody><tr><td></td>`）。"""
    tbody = table.xpath('.//tbody')
    body = tbody[0].xpath('./tr') if tbody else table.xpath('.//tr')[1:]
    return bool(body) and not any(r.text_content().strip() for r in body)


def align_columns(table, short=16):
    """R5：按列内容长度分情况决定对齐 —— 短列（Int/Float/Boolean/数值）居中，
    长列（标识符、描述文本）左对齐；**表头跟随所在列**，避免表头与正文错位。"""
    trs = table.xpath('.//tr')
    if not trs:
        return
    ncol = max(len(r.xpath('./td | ./th')) for r in trs)
    body = table.xpath('.//tbody/tr') or trs[1:]
    centers = []
    for c in range(ncol):
        mx = 0
        for r in body:
            cs = r.xpath('./td | ./th')
            if len(cs) <= c:
                continue
            head = inner(cs[c]).split('<br>')[0]
            mx = max(mx, len(re.sub(r'<[^>]+>', '', head).strip()))
        centers.append(mx <= short)
    for r in trs:
        for c, cell in enumerate(r.xpath('./td | ./th')):
            if c < len(centers) and centers[c]:
                cell.set('class', ((cell.get('class') or '') + ' tc').strip())
    REPORT['aligncol'] = REPORT.get('aligncol', 0) + sum(1 for x in centers if x)


def split_cells(el):
    n = 0
    for cell in el.xpath('.//td | .//th | .//figcaption'):
        if cell.xpath('.//td | .//th'):
            continue                       # 嵌套表格（当前为 0）不处理
        raw = inner(cell)
        m = re.match(r'^Default:\s*([^<>]{1,40})$', raw.strip())
        if m:                              # R3 §6：列名已经是 Default，值里不必再重复
            raw = m.group(1).strip()
            replace_inner(cell, raw)
            n += 1
        new, ok = split_bilingual(raw)
        if ok:
            replace_inner(cell, new)
            n += 1
    return n


# ── R4 §6：把英文原文里的外链搬到中文译文对应名词上 ────────────────────
LINK_RE = re.compile(r'<a\b([^>]*)>(.*?)</a>', re.S | re.I)
# 英文锚文本 → 中文行里要包成链接的文本（无《》书名号时的落点）
ZH_ANCHORS = {
    'A Quick and Dirty Guide to Custom Difficulty for Deep Rock Galactic':
        '《深岩银河自定义难度快速入门》',
    'Vanilla descriptors': '原版敌人描述符及 5 级难度的默认数值',
    'Materials Guide': '《材质指南》',
    'Vanilla projectiles compilation': '原版发射物清单',
    'On Pubbing With CD2': '《On Pubbing With CD2》',
    'DRG Hazard Scaling': '《DRG Hazard Scaling》',
    'here': '敌人列表',
}


def copy_links_to_zh(en_html, zh_html):
    """中文行没有链接时，从英文原文把外链搬过来（有《…》优先包《…》）。"""
    if re.search(r'<a\b', zh_html, re.I):
        return zh_html                       # 中文行已有链接，不动
    out = zh_html
    for attrs, text in LINK_RE.findall(en_html):
        if 'href=' not in attrs:
            continue
        label = re.sub(r'<[^>]+>', '', text).strip()
        target = ZH_ANCHORS.get(label)
        if not target:
            m = re.search(r'《[^》]+》', out)
            if not m:
                continue
            target = m.group(0)
        if target not in out:
            continue
        out = out.replace(target, f'<a{attrs}>{target}</a>', 1)
        REPORT['linkmove'] = REPORT.get('linkmove', 0) + 1
    return out


def try_namegrid(lis):
    """R4 §4：≥8 项、每项都是「标识符 + 空格 + 中文」的 <ul> → 紧凑名录。"""
    if len(lis) < 8:
        return None
    out = []
    for li in lis:
        if len(li):                          # 含子元素（链接等）不动
            return None
        m = re.match(r'^([A-Za-z][A-Za-z0-9_.\-]*)\s+([\u4e00-\u9fff].*)$', txt(li))
        if not m:
            return None
        out.append(f'<li>{m.group(1)}<span class="td-zh">{m.group(2)}</span></li>')
    return '<ul class="name-grid">' + ''.join(out) + '</ul>'


def auto_pair_text(s):
    """R3 §9.3：「英文句号直贴中文」的粘连串拆成 (英文, 中文)。"""
    if not s or '<' in s:
        return None
    m = re.search(r'[a-z0-9][.][\u4e00-\u9fff]', s)
    if not m:
        return None
    cut = m.start() + 2
    en, zh = s[:cut].strip(), s[cut:].strip()
    if not en or not zh:
        return None
    if not re.search(r'[。！？.!?]$', zh):
        zh += '。'
    return en, zh


def build_namegrid(table):
    """R3 §8：单列表（1 列、≥8 行）改输出多列紧凑名录。"""
    tbody = table.xpath('.//tbody/tr')
    if tbody:
        body = tbody
    else:
        allr = table.xpath('.//tr')
        body = allr[1:] if allr else []
    items = []
    for tr in body:
        cells = tr.xpath('./td | ./th')
        if not cells:
            continue
        inner_ = inner(cells[0]).strip()
        if not inner_:
            continue
        inner_ = re.sub(r'<br\s*/?>\s*(?=<span class="td-zh")', '', inner_)
        items.append(f'<li>{inner_}</li>')
    if len(items) < 8:
        return None
    return '<ul class="name-grid">' + ''.join(items) + '</ul>'


def pangu(s):
    """盘古之白：中文与拉丁字母/数字之间插入一个空格（§3.4）。"""
    if not s:
        return s
    s = re.sub(r'([\u4e00-\u9fff])([A-Za-z0-9])', r'\1 \2', s)
    s = re.sub(r'([A-Za-z0-9])([\u4e00-\u9fff])', r'\1 \2', s)
    return s


def clean_desc(s):
    """R3 §9.6：剥掉源码里的 [注：…] / {…} 注记，再去空白、截 120 字。"""
    s = s or ''
    s = re.sub(r'\[注[：:][^\]]*\]', '', s)      # 有闭合方括号的注记
    s = re.split(r'\[注[：:]', s)[0]              # 未闭合的注记：直接从这里截断
    s = re.sub(r'\{[^{}]*\}', '', s)             # {Ctrl+F …} 之类
    s = re.sub(r'\s+', ' ', s).strip()
    return s[:120]


SKIP_PANGU = {'code', 'pre', 'script', 'style', 'kbd', 'samp'}


def pangu_tree(el, counter):
    """对元素树里的文本节点做盘古之白，跳过 <code>/<pre> 内部。"""
    if not APPLY_PANGU:
        return
    for node in el.iter():
        if not isinstance(node.tag, str) or node.tag in SKIP_PANGU:
            continue
        if node.text:
            n = pangu(node.text)
            if n != node.text:
                counter[0] += 1
                node.text = n
        for c in node:
            if c.tag in SKIP_PANGU:
                continue
            if c.tail:
                n = pangu(c.tail)
                if n != c.tail:
                    counter[0] += 1
                    c.tail = n


def normalize_heading(text, slug):
    """§5 标题规范：中文 · 英文 / 英文 · 中文。返回 (新标题, 说明)。"""
    t = re.sub(r'\s+', ' ', (text or '').strip())
    if not t or ' · ' in t:
        return pangu(t), ''
    m = re.match(r'^(?P<en>[^（()）]+?)\s*[（(]\s*(?P<zh>[^）)]+?)\s*[)）]$', t)
    if not m:
        m = re.match(r"^(?P<en>[A-Za-z0-9][A-Za-z0-9_:.,'\"\-]*)\s+(?P<zh>[\u4e00-\u9fff].*)$", t)
    if not m:
        return pangu(t), ''
    en = re.sub(r'\s+', ' ', m.group('en')).strip(' -')
    zh = re.sub(r'\s+', ' ', m.group('zh')).strip()
    if not CJK.search(zh) or not LAT.search(en):
        return pangu(t), ''
    zh = pangu(zh)
    new = f'{en} · {zh}' if slug in EN_FIRST_PAGES else f'{zh} · {en}'
    return new, f'{t}  →  {new}'


# ── 链接重写 ────────────────────────────────────────────────────────────
def rewrite_url(raw, page_dir):
    if not raw:
        return raw, False
    u = raw.strip()
    if u.startswith(('#', 'mailto:', 'tel:', 'javascript:', 'data:')):
        return u, False
    if re.match(r'^[a-z][a-z0-9+.-]*://', u, re.I):
        return u, True
    frag = ''
    if '#' in u:
        u, frag = u.split('#', 1)
        frag = '#' + frag
    q = ''
    if '?' in u:
        u, q = u.split('?', 1)
        q = '?' + q
    if not u:
        return frag or '#', False
    old = posixpath.normpath(u if u.startswith('/') else posixpath.join(page_dir, u))
    old = old.replace('\\', '/').lstrip('/')
    if old in ASSET_MAP:
        return ASSET_MAP[old] + frag + q, False
    low = old.lower().rstrip('/')
    if low.endswith('/index.html'):
        low = low[: -len('/index.html')].rstrip('/')
    elif low == 'index.html':
        low = ''
    if low in DIR_MAP:
        new = DIR_MAP[low]
        return ('/' + new + '/' if new else '/') + frag + q, False
    if low in KNOWN_DIRS or low == '':
        return ('/' + low + '/' if low else '/') + frag + q, False
    base = posixpath.basename(low)
    for k, v in ASSET_MAP.items():
        if k.endswith(base):
            return v + frag + q, False
    # 指向已删除页面的链接不告警：稍后会被 strip_dead_links 剥成纯文字
    if low.strip('/').split('/')[0] in REMOVED:
        return '/' + old + frag + q, False
    REPORT['warnings'].append(f'未映射链接: {raw}  (page_dir={page_dir})')
    return '/' + old + frag + q, False


def clean(el, page_dir):
    for a in el.xpath('.//a[@href]'):
        new, is_ext = rewrite_url(a.get('href'), page_dir)
        a.set('href', new)
        if is_ext:
            a.set('target', '_blank')
            a.set('rel', 'noopener')
        else:
            a.attrib.pop('target', None)
            a.attrib.pop('rel', None)
    # R5：指向已删除页面的内链 → 拆掉 <a> 只留文字
    for a in el.xpath('.//a[@href]'):
        m = re.match(r'^/(' + '|'.join(sorted(REMOVED)) + r')(?:/|$|#)', a.get('href') or '')
        if m:
            a.drop_tag()
            REPORT['deadlink'] = REPORT.get('deadlink', 0) + 1
    for im in el.xpath('.//img[@src]'):
        new, _ = rewrite_url(im.get('src'), page_dir)
        im.set('src', new)
        im.set('loading', 'lazy')
    for e in el.iter():
        if not isinstance(e.tag, str):
            continue
        cls = (e.get('class') or '').strip()
        keep = [c for c in cls.split()
                if c not in ('None', 'cn', 'reference', 'internal', 'current')
                and not c.startswith('toctree')]
        if keep:
            e.set('class', ' '.join(keep))
        else:
            e.attrib.pop('class', None)
        for attr in ('style', 'role', 'itemprop', 'data-toggle', 'data-spy'):
            e.attrib.pop(attr, None)
    return el


def html_of(el, page_dir, pcount):
    e = clean(el, page_dir)
    pangu_tree(e, pcount)
    s = inner(e)
    # R4 §6 顺手：`</code>=各字段` 这种粘连的等号，中文前不需要
    return re.sub(r'</code>\s*=\s*(?=[\u4e00-\u9fff])', '</code> ', s)


# ── 双语配对（§3.5）────────────────────────────────────────────────────
def make_pair_block(zh_el, en_el, page_dir, pcount, tag='p'):
    """成对：中文在前，英文进折叠块（渲染层决定）。"""
    zh_html = html_of(zh_el, page_dir, pcount) if zh_el is not None else None
    en_html = html_of(en_el, page_dir, pcount) if en_el is not None else None
    return {'t': tag, 'zh': zh_html, 'en': en_html}


def extract_p(el, page_dir, pcount):
    k = kind(txt(el))
    if k in ('empty', 'other'):
        return None
    cls = el.get('class') or ''
    return {'t': 'p', 'lang': k, 'html': html_of(el, page_dir, pcount), 'cls': cls}


def extract_list(el, page_dir, pcount):
    items, i = [], 0
    lis = el.xpath('./li')
    while i < len(lis):
        li = lis[i]
        lt = txt(li)
        nxt = lis[i + 1] if i + 1 < len(lis) else None
        nt = txt(nxt) if nxt is not None else ''
        k = kind(lt)
        if is_en(lt) and CJK.search(nt):      # R4 §2.1：中文字数少的条目也要能配对
            en_html = html_of(li, page_dir, pcount)
            zh_html = html_of(nxt, page_dir, pcount)
            items.append({'zh': copy_links_to_zh(en_html, zh_html), 'en': en_html,
                          'id': li.get('id') or nxt.get('id') or '',
                          'cls': nxt.get('class') or li.get('class') or ''})
            REPORT['pairs'].append(('li', lt, nt))
            i += 2
            continue
        if k in ('empty', 'other'):
            i += 1
            continue
        if is_en(lt):
            REPORT['lone_en'].append((page_dir, lt))
        ap = auto_pair_text(lt) if len(li) == 0 else None
        if ap:                       # R3 §9.3：英文句号直贴中文 → 拆成一对
            REPORT['autopair'] = REPORT.get('autopair', 0) + 1
            items.append({'zh': ap[1], 'en': ap[0], 'id': li.get('id') or '',
                          'cls': li.get('class') or ''})
            i += 1
            continue
        zz, ee = is_zh(lt), is_en(lt)
        if not zz and not ee:
            zz = True          # 中英混排的说明行：归到中文槽，绝不丢内容
        items.append({'zh': html_of(li, page_dir, pcount) if zz else None,
                      'en': html_of(li, page_dir, pcount) if ee else None,
                      'id': li.get('id') or '',
                      'cls': li.get('class') or ''})
        i += 1
    if not items:
        return None
    return {'t': 'list', 'tag': el.tag, 'items': items}


def extract_block(el, page_dir, pcount, slug):
    tag = el.tag
    if tag in ('h1', 'h2', 'h3', 'h4', 'h5', 'h6'):
        t = txt(el)
        if not t:
            return None
        hid = el.get('id') or re.sub(r'[^\w\u4e00-\u9fff]+', '-', t.lower()).strip('-') or 'sec'
        new, note = normalize_heading(t, slug)
        if note:
            REPORT['headings'].append((slug, int(tag[1]), note))
        return {'t': 'h', 'level': int(tag[1]), 'id': hid, 'text': new, 'text_raw': t}
    if tag == 'p':
        return extract_p(el, page_dir, pcount)
    if tag in ('ul', 'ol'):
        grid = try_namegrid(el.xpath('./li')) if tag == 'ul' else None
        if grid:                             # R4 §4：字段清单转名录
            REPORT['namegrid'] = REPORT.get('namegrid', 0) + 1
            return {'t': 'namegrid', 'html': grid}
        return extract_list(el, page_dir, pcount)
    if tag == 'pre':
        code = el.xpath('.//code')
        cls = (code[0].get('class') or '') if code else ''
        m = re.search(r'language-([\w+#-]+)', cls)
        raw = (el.text_content() or '').replace('\r\n', '\n').strip('\n')
        return {'t': 'code', 'lang': (m.group(1) if m else 'text'), 'text': raw}
    if tag == 'table':
        e = clean(el, page_dir)
        for cell in e.xpath('.//thead//td'):       # R3 §6：表头内一律 th
            cell.tag = 'th'
        merge_translation_column(e)                # R5 ④：并入「翻译」列
        drop_empty_columns(e)                      # R5 ⑧：删掉整列全空
        if is_empty_table(e):                      # R5：空表不用表格写「无」
            REPORT['emptytbl'] = REPORT.get('emptytbl', 0) + 1
            return {'t': 'p', 'zh': '无', 'cls': 'tbl-none'}
        align_columns(e)                           # R5：短列居中、长列左对齐
        nsplit = split_cells(e)
        REPORT['td_split'] = REPORT.get('td_split', 0) + nsplit
        th = [txt(x) for x in e.xpath('.//thead//th')] or \
             [txt(x) for x in e.xpath('.//tr[1]/*[self::th or self::td]')]
        rows = len(e.xpath('.//tbody/tr')) or max(len(e.xpath('.//tr')) - 1, 0)
        first = e.xpath('.//tr[1]')
        ncol = len(first[0].xpath('./th | ./td')) if first else 0
        if ncol == 1 and rows >= 8:                # R3 §8：单列表 → 紧凑名录
            grid = build_namegrid(e)
            if grid:
                REPORT['namegrid'] = REPORT.get('namegrid', 0) + 1
                return {'t': 'namegrid', 'html': grid, 'rows': rows}
        return {'t': 'table', 'html': LH.tostring(e, encoding='unicode'),
                'head': th, 'rows': rows}
    if tag == 'figure':
        e = clean(el, page_dir)
        nsplit = split_cells(e)
        REPORT['td_split'] = REPORT.get('td_split', 0) + nsplit
        return {'t': 'figure', 'html': LH.tostring(e, encoding='unicode')}
    if tag in ('div', 'section'):
        out = []
        for c in el:
            r = extract_block(c, page_dir, pcount, slug)
            if r:
                out.extend(r if isinstance(r, list) else [r])
        return out or None
    if tag in ('script', 'style', 'hr', 'nav'):
        return None
    if tag in ('td', 'th', 'tr', 'tbody', 'thead', 'tfoot'):
        return None          # 源站个别表格未闭合，游离的空单元格，丢弃
    REPORT['warnings'].append(f'未处理标签 <{tag}> @ {page_dir}')
    return {'t': 'html', 'html': LH.tostring(clean(el, page_dir), encoding='unicode')}


# ── 页面 ────────────────────────────────────────────────────────────────
def extract_page(old_rel, slug):
    fp = os.path.join(SRC, old_rel.replace('/', os.sep))
    if not os.path.exists(fp):
        REPORT['warnings'].append(f'缺文件: {old_rel}')
        return None
    doc = LH.fromstring(open(fp, 'rb').read())
    secs = doc.xpath('//div[@role="main"]//div[@class="section"]')
    if not secs:
        REPORT['warnings'].append(f'找不到正文区: {old_rel}')
        return None
    sec = secs[0]
    for bad in sec.xpath('.//script | .//style'):
        bad.getparent().remove(bad)
    page_dir = '/' + posixpath.dirname(old_rel.replace('\\', '/'))
    if page_dir == '/.' or not page_dir.endswith('/'):
        page_dir = (page_dir if page_dir != '/.' else '/')
    if page_dir != '/' and not page_dir.endswith('/'):
        page_dir += '/'

    title, title_zh = '', ''
    h1s = sec.xpath('./h1')
    if h1s:
        title = txt(h1s[0])
        nxt = h1s[0].getnext()
        if nxt is not None and nxt.tag == 'p' and kind(txt(nxt)) == 'zh':
            title_zh = txt(nxt)          # h1 之后紧跟的中文标题行，收进页面标题
            nxt.getparent().remove(nxt)
        h1s[0].getparent().remove(h1s[0])

    pcount = [0]
    blocks, seen = [], set()
    for child in sec:
        r = extract_block(child, page_dir, pcount, slug)
        if not r:
            continue
        for b in (r if isinstance(r, list) else [r]):
            if b['t'] == 'h':
                if b['id'] in seen:
                    n = 2
                    while f"{b['id']}-{n}" in seen:
                        n += 1
                    b['id'] = f"{b['id']}-{n}"
                seen.add(b['id'])
            blocks.append(b)

    # 配对：紧邻的 英文 <p> + 中文 <p>（§3.5.1）
    merged, i = [], 0
    while i < len(blocks):
        b = blocks[i]
        nx = blocks[i + 1] if i + 1 < len(blocks) else None
        bt = txt_lite(b.get('html')) if b['t'] == 'p' else ''
        nt = txt_lite(nx.get('html')) if (nx and nx['t'] == 'p') else ''
        if b['t'] == 'p' and is_en(bt) and nx and nx['t'] == 'p' and CJK.search(nt):
            zh = copy_links_to_zh(b['html'], nx['html'])      # R4 §6：外链搬到中文行
            merged.append({'t': 'p', 'zh': zh, 'en': b['html'],
                           'cls': nx.get('cls') or b.get('cls') or ''})
            REPORT['pairs'].append(('p', bt, nt))
            i += 2
            continue
        if b['t'] == 'p' and is_en(bt):
            REPORT['lone_en'].append((page_dir, bt))
        merged.append(b)
        i += 1

    # 统一表示：所有 <p> 都变成 {zh, en} 形状（至少一边有值）
    for b in merged:
        if b['t'] == 'p' and 'html' in b:
            h = b.pop('html')
            b.pop('lang', None)
            b['zh' if CJK.search(txt_lite(h)) else 'en'] = h
    headings = [{'id': b['id'], 'level': b['level'], 'text': b['text']}
                for b in merged if b['t'] == 'h']

    # 搜索正文：折叠的英文**不进**索引（§3.1）
    parts = []
    for b in merged:
        if b['t'] == 'p':
            parts.append(txt_lite(b.get('zh') or b.get('en') or ''))
        elif b['t'] == 'list':
            for it in b['items']:
                parts.append(txt_lite(it.get('zh') or it.get('en') or ''))
        elif b['t'] == 'code':
            parts.append(b['text'])
        elif b['t'] in ('table', 'figure', 'html'):
            parts.append(txt(LH.fromstring(b['html'])))
        elif b['t'] == 'h':
            parts.append(b['text'])
    text = re.sub(r'\n{2,}', '\n', '\n'.join(x for x in parts if x)).strip()

    langs, counts = {}, {}
    for b in merged:
        counts[b['t']] = counts.get(b['t'], 0) + 1
        if b['t'] == 'p':
            key = 'pair' if b.get('zh') and b.get('en') else ('en' if b.get('en') else 'zh')
            langs[key] = langs.get(key, 0) + 1
        elif b['t'] == 'list':
            for it in b['items']:
                key = 'pair' if it.get('zh') and it.get('en') else ('en' if it.get('en') else 'zh')
                langs[key] = langs.get(key, 0) + 1

    ext = sorted({a.get('href') for a in sec.xpath('.//a[@href]')
                  if re.match(r'^https?://', a.get('href') or '')})
    desc = next((txt_lite(b['zh']) for b in merged
                 if b['t'] == 'p' and b.get('zh')), '')
    return {
        'slug': slug, 'path': ('/' + slug + '/') if slug else '/', 'title': title,
        'title_zh': title_zh, 'blocks': merged, 'headings': headings, 'desc': desc,
        'external_links': ext, 'no_translation': langs.get('zh', 0) + langs.get('pair', 0) == 0,
        'stats': {'blocks': counts, 'langs': langs, 'text_chars': len(text),
                  'pangu_edits': pcount[0]},
        'text': text,
    }


def txt_lite(h):
    if not h:
        return ''
    return re.sub(r'\s+', ' ', LH.fromstring('<x>' + h + '</x>').text_content()).strip()


NAV_OVERRIDE = {
    '': '首页 · Introduction',
    'enemies': '敌人配置 · Enemies / EnemiesNoSync',   # R5 ②：去掉「(客机 同步/非同步)」
    'tips': '写作提示与常见错误 · Tips',              # R5：与其它中英混排标题对齐
    'natural-selection': '案例拆解 · Case Study',   # R12：它是完整案例，不是 Cookbook
    'common-edits': '常见修改 · Cookbook',        # R12：上游 Common Edits，恢复并译为 Cookbook
    'tutorial': '新手入门 · Getting Started',     # R12：本站自写的新人第一段路
    'tips': '为什么没生效 · Debug',               # R12：重定位为排障页
}


def normalize_nav(label, slug):
    """导航标签规范：中文 · 英文（§5）。源站是「English中文」无空格，先盘古再切。"""
    if slug in NAV_OVERRIDE:
        return NAV_OVERRIDE[slug]
    t = pangu(re.sub(r'\s+', ' ', (label or '')).strip())
    t = re.sub(r'^\(Module\)\s*', '', t)          # 「(Module) 」是全站冗余前缀
    m = CJK.search(t)
    if not m:
        return t
    en, zh = t[:m.start()].strip(' -·'), t[m.start():].strip()
    zh = pangu(zh)
    if not en:
        return zh
    return f'{en} · {zh}' if slug in EN_FIRST_PAGES else f'{zh} · {en}'


def extract_nav():
    """从首页左导航提取 14 项（href + 双语标签），顺序以 PAGES 为准。"""
    doc = LH.fromstring(open(os.path.join(SRC, 'index.html'), 'rb').read())
    order = [p[1] for p in PAGES]
    out = []
    for li in doc.xpath('//li[contains(@class,"toctree-l1")]'):
        a = li.xpath('./a')
        if not a:
            continue
        href = a[0].get('href') or ''
        label = re.sub(r'\s+', ' ', a[0].text_content()).strip()
        new, _ = rewrite_url(href, '/')
        if new.startswith('#') or new in ('', '.'):
            new, slug = '/', ''
        else:
            slug = new.strip('/')
        if slug not in order:
            continue
        out.append({'slug': slug, 'path': new, 'label': normalize_nav(label, slug),
                    'label_raw': label})
    have = {x['slug'] for x in out}
    for old_rel, slug in PAGES:
        if slug not in have:
            out.append({'slug': slug, 'path': ('/' + slug + '/') if slug else '/',
                        'label': normalize_nav('', slug), 'label_raw': ''})
    out.sort(key=lambda x: order.index(x['slug']))
    return out


def main():
    os.makedirs(CONTENT, exist_ok=True)
    # 清空上一轮的页面 JSON，避免已删除的页面残留在构建里
    for fn in sorted(os.listdir(CONTENT)):
        if fn.endswith('.json'):
            os.remove(os.path.join(CONTENT, fn))
    nav = extract_nav()
    index, rows = [], []
    for old_rel, slug in PAGES:
        page = extract_page(old_rel, slug)
        if page is None:
            rows.append((slug or 'home', 'MISSING', '', '', '', '', ''))
            continue
        navitem = next((n for n in nav if n['slug'] == slug), None)
        page['nav'] = navitem or {'slug': slug, 'path': page['path'],
                                  'label': page['title'], 'label_raw': page['title']}
        # R4 §3.2：搜索结果的展示标题用导航标签（「Direct · 底层属性」这种）
        page['title_zh'] = page['nav'].get('label') or page['title']
        io.open(os.path.join(CONTENT, (slug or 'home') + '.json'), 'w',
                encoding='utf-8').write(json.dumps(page, ensure_ascii=False, indent=1))
        index.append({'title': page['title'], 'title_zh': page['title_zh'],
                      'path': page['path'], 'slug': slug, 'headings': page['headings'],
                      'text': page['text'], 'kw': SEARCH_KW.get(slug, ''),
                      'desc': clean_desc(page['desc'])})
        s, l = page['stats']['blocks'], page['stats']['langs']
        rows.append((slug or '(home)', s.get('h', 0), s.get('p', 0), s.get('list', 0),
                     s.get('table', 0), s.get('code', 0),
                     f"成对={l.get('pair',0)} 中文={l.get('zh',0)} 英文={l.get('en',0)}"
                     + ('  ⚠️无译文' if page['no_translation'] else '')))

    io.open(os.path.join(BUILD, 'nav.json'), 'w', encoding='utf-8').write(
        json.dumps(nav, ensure_ascii=False, indent=1))
    io.open(os.path.join(BUILD, 'search-index.json'), 'w', encoding='utf-8').write(
        json.dumps(index, ensure_ascii=False, separators=(',', ':')))

    L = ['%-13s %5s %5s %5s %6s %5s   %s' % ('slug', '标题', '段落', '列表', '表格', '代码', '语言分布'),
         '-' * 96]
    L += ['%-13s %5s %5s %5s %6s %5s   %s' % r for r in rows]
    L += ['-' * 96]
    sz = os.path.getsize(os.path.join(BUILD, 'search-index.json'))
    pg = sum(p['stats']['pangu_edits'] for p in
             [json.loads(io.open(os.path.join(CONTENT, (s or 'home') + '.json'), encoding='utf-8').read())
              for _, s in PAGES])
    L.append(f'页面 {len(index)} ｜ 正文纯文本 {sum(len(i["text"]) for i in index):,} 字符 ｜ '
             f'search-index.json {sz:,} 字节 ｜ 盘古之白改动 {pg} 处 ｜ '
             f'表格/图注中英分行 {REPORT.get("td_split", 0)} 处 ｜ '
             f'单列表转名录 {REPORT.get("namegrid", 0)} 张 ｜ '
             f'外链搬回中文行 {REPORT.get("linkmove", 0)} 处 ｜ '
             f'翻译列并入 {REPORT.get("transcol", 0)} 张表 ｜ '
             f'空列删除 {REPORT.get("emptycol", 0)} 列 ｜ '
             f'空表补「无」 {REPORT.get("emptytbl", 0)} 张 ｜ '
             f'死链剥离 {REPORT.get("deadlink", 0)} 处 ｜ '
             f'粘连段自动配对 {REPORT.get("autopair", 0)} 处')
    io.open(os.path.join(DEST, 'tools', 'extract_report.txt'), 'w', encoding='utf-8').write('\n'.join(L))

    # 配对报告
    P = [f'双语配对样本（共 {len(REPORT["pairs"])} 对，展示前 25 对）', '=' * 90]
    for t, en, zh in REPORT['pairs'][:25]:
        P.append(f'[{t}] EN: {en[:88]}')
        P.append(f'      ZH: {zh[:88]}')
    P += ['', f'英文单飞段（无中文对应，共 {len(REPORT["lone_en"])} 段，全部列出）', '=' * 90]
    for pg, t in REPORT['lone_en']:
        P.append(f'[{pg}] {t[:110]}')
    io.open(os.path.join(DEST, 'tools', 'pairing_report.txt'), 'w',
            encoding='utf-8').write('\n'.join(P))

    # 标题规范化报告
    H = [f'标题规范化（共改动 {len(REPORT["headings"])} 条，全部列出）', '=' * 90]
    cur = None
    for slug, lvl, note in REPORT['headings']:
        if slug != cur:
            H.append('')
            H.append(f'── /{slug or ""} ──')
            cur = slug
        H.append(f'  h{lvl}  {note}')
    io.open(os.path.join(DEST, 'tools', 'heading_report.txt'), 'w',
            encoding='utf-8').write('\n'.join(H))

    io.open(os.path.join(DEST, 'tools', 'warnings.txt'), 'w', encoding='utf-8').write(
        '\n'.join(sorted(set(REPORT['warnings']))))

    print('OK  pages=%d  pairs=%d  lone_en=%d  heading_norm=%d  warnings=%d'
          % (len(index), len(REPORT['pairs']), len(REPORT['lone_en']),
             len(REPORT['headings']), len(set(REPORT['warnings']))))
    print('search-index.json %d bytes' % sz)


main()
