# -*- coding: utf-8 -*-
"""
《物竞天择-功能实作.md》→ natural-selection/index.html
────────────────────────────────────────────────────────────
这是**正式工具**（不是临时脚本）：改 md 后运行它，再跑 tools/build.ps1。

  结构：一句话 → 精简骨架（<dl>）→ 实现拆解（每步：一句话 + 详解条 + 代码条）
  格式：行内 `x` 分三类渲染（中文标识符 / 数值运算符 / 代码原语），都不套代码底框
  命名：run:  python tools/md2page.py
"""
import io, os, re, html as H, urllib.parse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MD = os.path.join(ROOT, os.pardir, '物竞天择-功能实作.md')
OUT = os.path.join(ROOT, os.pardir, 'CD2-upstream-src', 'natural-selection', 'index.html')

CIRCLED = '①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬'

# ── 原语 → mutators 锚点（取自实际产物） ──────────────────────────────
ARITH = 'add-subtract-multiply-divide-pow-modulo-round-ceil-floor'
LOCKS = 'LockFloat, LockBoolean, LockString'
ANCHOR = {
    'Accumulate': 'accumulate', 'Sequence': 'Sequence', 'Select': 'Select',
    'Clamp': 'clamp', 'If': 'if', 'IfFloat': 'iffloat', 'Iffloat': 'iffloat',
    'Delta': 'delta', 'Join': 'join', 'Max': 'max', 'Min': 'min',
    'Floor': ARITH, 'Ceil': ARITH, 'Modulo': ARITH, 'Add': ARITH,
    'Subtract': ARITH, 'Multiply': ARITH, 'Divide': ARITH,
    'And': 'and-or-not', 'Or': 'and-or-not', 'Not': 'and-or-not',
    'LockFloat': LOCKS, 'LockBoolean': LOCKS, 'LockString': LOCKS,
    'TriggerOnChange': 'triggeronchange', 'TriggerOnchange': 'triggeronchange',
    'TriggerFixedDuration': 'triggerfixedduration', 'TriggerDelay': 'triggerdelay',
    'TriggerSustain': 'triggersustain', 'TriggerOnce': 'triggeronce',
    'TriggerNTimes': 'triggerntimes', 'TriggerSometimes': 'triggersometimes',
    'TriggerCooldown': 'triggercooldown', 'TriggerTimer': 'triggertimer',
    'SelectFromArray': 'selectfromarray', 'RandomChoice': 'randomchoice',
    'RandomChoicePerMission': 'randomchoicepermission', 'Random': 'random',
    'EnemiesKilled': 'enemieskilled', 'EnemyCount': 'enemycount',
    'EnemiesRecentlySpawned': 'enemiesrecentlyspawned',
    'EnemyCooldown': 'enemycooldown', 'EnemyHealth': 'EnemyHealth',
    'EnemyDistance': 'EnemyDistance', 'ByMissionType': 'bymissiontype',
    'ByPlayerCount': 'byplayercount', 'ByTime': 'bytime', 'ByBiome': 'bybiome',
    'ByEscortPhase': 'byescortphase', 'BySalvagePhase': 'bysalvagephase',
    'ByRefineryPhase': 'byrefineryphase', 'BySaboPhase': 'bysabophase',
    'ByDDStage': 'byddstage', 'BySecondary': 'bysecondary',
    'ByResuppliesCalled': 'byresuppliescalled', 'ByDNA': 'bydna',
    'Countdown': 'countdown', 'DefenseProgress': 'defenseprogress',
    'SquareWave': 'squarewave', 'StopWatch': 'StopWatch', 'TimeDelta': 'timedelta',
    'Int2String': 'int2string', 'Float2String': 'float2string',
    'Nonzero': 'Nonzero', 'SecondaryFinished': 'SecondaryFinished',
    'DwarvesHealth': 'dwarveshealth', 'DwarvesAmmo': 'dwarvesammo',
    'DwarvesDown': 'dwarvesdown', 'DwarvesDowns': 'dwarvesdowns',
    'DwarvesRevives': 'dwarvesrevives', 'DwarvesShield': 'dwarvesshield',
    'IWsLeft': 'iwsleft', 'DepositedResource': 'depositedresource',
    'ResuppliesCalled': 'resuppliescalled', 'DwarfCount': 'dwarfcount',
    'DuringMission': 'duringmission', 'DuringExtraction': 'duringextraction',
    'DuringDefend': 'duringdefend', 'DuringDread': 'duringdread',
    'DuringDrillevator': 'duringdrillevator',
    'DuringGenericSwarm': 'duringgenericswarm',
    'DuringPECountdown': 'duringpecountdown', 'DuringEggAmbush': 'duringeggambush',
}


def esc(t):
    return H.escape(t or '', quote=True)


def shorten_label(s, maxlen=20):
    s = s.replace('`', '')
    s = re.sub(r'[（(][^（()）]*[)）]', '', s)
    s = re.sub(r'[「」『』]', '', s).strip(' ·')
    return s[:maxlen].rstrip(' ·') if len(s) > maxlen else s


def mixed(expr):
    """含中文的表达式：ASCII 标识符 → 蓝色无框，其余 → 正文次级色。"""
    out = []
    for tok in re.findall(r'[A-Za-z_][A-Za-z0-9_.]*|\d+(?:\.\d+)?%?|[^A-Za-z0-9_]+', expr):
        if re.match(r'^[A-Za-z_]', tok):
            out.append(f'<span class="vcode">{esc(tok)}</span>')
        else:
            out.append(f'<span class="vnum">{esc(tok)}</span>')
    return ''.join(out)


def inline(t):
    """行内格式：按反引号切「文本/代码」，文本段处理 **粗体** 与 *斜体*。"""
    parts = re.split(r'(`[^`]+`)', t)
    for k in range(0, len(parts), 2):
        p = esc(parts[k])
        p = re.sub(r'\*\*([^*]+)\*\*', r'<b>\1</b>', p)
        p = re.sub(r'(?<!\*)\*([^*]+)\*(?!\*)', r'<em>\1</em>', p)
        parts[k] = p
    for k in range(1, len(parts), 2):
        name = parts[k][1:-1]
        if re.search(r'[\u4e00-\u9fff]', name) and not re.search(r'[A-Za-z]', name):
            parts[k] = f'<span class="vzh">{esc(name)}</span>'
        elif re.search(r'[\u4e00-\u9fff]', name):
            parts[k] = mixed(name)
        elif re.fullmatch(r'[+-]?\d+(?:\.\d+)?%?', name) or \
                re.fullmatch(r'==|!=|>=|<=|<|>', name):
            parts[k] = f'<span class="vnum">{esc(name)}</span>'
        elif name in ANCHOR:
            a = urllib.parse.quote(ANCHOR[name])
            parts[k] = (f'<a href="../mutators/#{a}"><span class="vcode">'
                        f'{esc(name)}</span></a>')
        elif name in ANCHOR.values():
            parts[k] = f'<span class="vcode">{esc(name)}</span>'
        else:
            parts[k] = f'<span class="vcode">{esc(name)}</span>'
    return ''.join(parts)


def esc_code(code):
    """代码块高亮：变量名蓝 / 注释灰 / 数值次级。"""
    out = []
    for ln in code.split('\n'):
        m = re.search(r'(?<![:/"])//', ln)
        head, tail = (ln[:m.start()], ln[m.start():]) if m else (ln, '')
        head = esc(head)
        head = re.sub(r'&quot;([^&]{1,60}?)&quot;',
                      lambda x: f'<span class="jk">&quot;{x.group(1)}&quot;</span>', head)
        head = re.sub(r'(?<![\w&;])([-+]?\d+(?:\.\d+)?%?)(?![\w;])',
                      r'<span class="jn">\1</span>', head)
        out.append(head + (f'<span class="jc">{esc(tail)}</span>' if tail else ''))
    return '\n'.join(out)


def code_html(code, label, opened=False):
    n = len(code.splitlines())
    tail = ' · 已展开' if opened else ' · 点击展开'
    return (f'<details class="ns-code"{" open" if opened else ""}>'
            f'<summary>{esc(shorten_label(label))} · {n} 行{tail}</summary>'
            f'<pre><code>{esc_code(code)}</code></pre></details>')


def slug(t):
    return re.sub(r'[^\w\u4e00-\u9fff]+', '-', t).strip('-').lower() or 'sec'


def render(lines, code_label=None, code_open=False):
    out, i = [], 0
    while i < len(lines):
        ln = lines[i]
        if ln.startswith('```'):
            buf = []
            i += 1
            while i < len(lines) and not lines[i].startswith('```'):
                buf.append(lines[i]); i += 1
            i += 1
            out.append(code_html('\n'.join(buf).strip('\n'), code_label or 'json', code_open))
            continue
        if ln.startswith('>'):
            buf = []
            while i < len(lines) and (lines[i].startswith('>') or not lines[i].strip()):
                if lines[i].startswith('>'):
                    buf.append(lines[i].lstrip('>').strip())
                elif buf:
                    buf.append('')
                i += 1
            ps, para = [], []
            for x in buf:
                if x:
                    para.append(x)
                elif para:
                    ps.append(' '.join(para)); para = []
            if para:
                ps.append(' '.join(para))
            out.append('<blockquote>' +
                       ''.join(f'<p>{inline(p)}</p>' for p in ps if p) + '</blockquote>')
            continue
        if ln.startswith('|'):
            rows = []
            while i < len(lines) and lines[i].startswith('|'):
                raw = lines[i].strip().strip('|')
                if not re.match(r'^[-:\s|]+$', raw):
                    rows.append([inline(c.strip()) for c in raw.split('|')])
                i += 1
            if rows:
                th = ''.join(f'<th>{c}</th>' for c in rows[0])
                tb = ''.join('<tr>' + ''.join(f'<td>{c}</td>' for c in r) + '</tr>'
                             for r in rows[1:])
                out.append(f'<table><thead><tr>{th}</tr></thead><tbody>{tb}</tbody></table>')
            continue
        if re.match(r'^\s*[-*]\s+', ln):
            items = []
            while i < len(lines) and re.match(r'^\s*[-*]\s+', lines[i]):
                items.append(inline(re.sub(r'^\s*[-*]\s+', '', lines[i]))); i += 1
                while i < len(lines) and lines[i].startswith('  ') and lines[i].strip() \
                        and not re.match(r'^\s*[-*]\s', lines[i]) \
                        and not lines[i].lstrip().startswith('#'):
                    items[-1] += '<br>' + inline(lines[i].strip()); i += 1
            out.append('<ul>' + ''.join(f'<li>{x}</li>' for x in items) + '</ul>')
            continue
        if re.match(r'^\s*\d+[.)]\s+', ln):
            items = []
            while i < len(lines):
                m = re.match(r'^(\s*)\d+[.)]\s+(.*)$', lines[i])
                if m and not m.group(1):
                    items.append(inline(m.group(2))); i += 1
                elif lines[i].startswith('  ') and lines[i].strip() \
                        and not lines[i].lstrip().startswith('#'):
                    if items:
                        items[-1] += '<br>' + inline(lines[i].strip()); i += 1
                    else:
                        break
                else:
                    break
            out.append('<ol>' + ''.join(f'<li>{x}</li>' for x in items) + '</ol>')
            continue
        if re.match(r'^\s*(-{3,}|\*{3,}|_{3,})\s*$', ln):
            i += 1          # markdown 分隔线：h2 自带分隔，不再画 <hr>
            continue
        if ln.strip():
            out.append(f'<p>{inline(ln.strip())}</p>')
        i += 1
    return ''.join(out)


def render_skeleton(lines):
    """精简骨架：md 表格 → <dl>（绕开 extract.py 的表格流水线）。"""
    rows, pre = [], []
    started = has_sep = False
    for ln in lines:
        s = ln.strip()
        if s.startswith('|'):
            started = True
            raw = s.strip('|')
            if re.match(r'^[-:\s|]+$', raw):
                has_sep = True
                continue
            rows.append([x.strip() for x in raw.split('|')])
        elif not started and s:
            pre.append(re.sub(r'^>\s*', '', s))
    if has_sep and rows:   # markdown 表：只要有分隔线，第一行就一定是表头
        rows = rows[1:]
    res = ''.join(f'<p class="sk-lead">{inline(x)}</p>' for x in pre)
    res += '<dl class="sk">'
    for cells in rows:
        if len(cells) < 3 or not any(cells):
            continue
        stage, var, role = cells[0], cells[1], cells[2]
        if stage and var:
            res += f'<dt class="sk-stage">{inline(stage)}</dt>'
        if var:
            res += f'<dt>{inline(var)}</dt>'
        if role:
            res += f'<dd>{inline(role)}</dd>'
    return res + '</dl>'


def split_step(lines):
    """拆成 (常显, 详解)：表格 / ≤4 项无公式短列表 → 常显；公式与推演 → 详解。"""
    blocks, cur, in_code = [], [], False
    for ln in lines:
        if ln.strip().startswith('```'):
            in_code = not in_code
        if in_code:
            cur.append(ln); continue
        if ln.strip():
            cur.append(ln)
        elif cur:
            blocks.append(cur); cur = []
    if cur:
        blocks.append(cur)
    always, dive = [], []
    for b in blocks:
        head = b[0].strip()
        is_table = head.startswith('|')
        is_list = bool(re.match(r'^\s*[-*]\s+', head))
        is_ol = bool(re.match(r'^\s*\d+[.)]\s+', head))
        n_items = sum(1 for x in b if re.match(r'^\s*([-*]|\d+[.)])\s+', x))
        has_formula = any(('=' in x) or re.match(r'^\s*[-*]\s*`', x) for x in b)
        if is_table:
            always += b
        elif (is_list or is_ol) and n_items <= 4 and not has_formula \
                and max(len(x.strip()) for x in b) <= 90:
            always += b
        elif len(b) == 1 and head.endswith('：') and '=' not in head \
                and '`' not in head and len(head) < 60:
            always += b
        else:
            dive += b
    return always, dive


def parse(md):
    """只按 h2/h3 切分；h4 保留在所属小节内。"""
    secs, cur, head = [], None, []
    for ln in md.split('\n'):
        m = re.match(r'^(#{1,6})\s+(.*)$', ln)
        if m and len(m.group(1)) <= 3:
            cur = {'lv': len(m.group(1)), 'text': m.group(2).strip(), 'lines': []}
            secs.append(cur)
        elif cur is not None:
            cur['lines'].append(ln)
        else:
            head.append(ln)
    return secs, head


# ── 三层阅读：人工撰写的导读（流程条 / 白话 / 读取-判断-输出） ──────────
GUIDE = {
 '①': {'flow': ['断源', '记账', '加倍率', '计数', '结算', '播报'],
       'plain': '地图本来会长硝石，作者把产出关掉，改成自己记一本账：每击杀一种「固定单位」'
                '就往账上记点数，而点数还乘着一个会自己往上涨的倍率——杀得越密，硝石攒得越快。'
                '账上每满 60 点就送一次免费补给，最多 6 次，每叫一次补给再扣掉一次。'
                '「免费」不是打折，是把补给要花的硝石直接乘 0。',
       'table': [('读取', '固定单位击杀事件 / 地图时间 / 补给调用次数 / 存入资源'),
                 ('判断', '硝石存量每跨过 60 的整数倍 → 免费补给次数 +1'),
                 ('输出', 'Resupply.Cost 指向变量 → 还有免费次数时整个成本为 0')]},
 '②': {'flow': ['抽签', '开窗', '停潮', '乘子', '避坑'],
       'plain': '地图上会随机刷出五种「勘探者」，打死哪一只就触发哪一条增益，各持续 20~30 秒。'
                '最方便的一只直接关掉「恒压潮」这个刷怪闸门；另外两只改的是全局倍率'
                '（敌方伤害 ×0.8、敌方弹速 ×0.5）。它教的是一件事：'
                '一次性事件要先用 TriggerFixedDuration 拉成一个「窗口」，下游才能持续读到它。',
       'table': [('读取', '击杀事件 EnemiesKilled / 某单位最近是否出现过'),
                 ('判断', 'TriggerOnChange 取上升沿 → 用 TriggerFixedDuration 开 20~30 秒窗口'),
                 ('输出', '一个 Boolean 开关 → 闸门变量 / 条件乘子')]},
 '③': {'flow': ['公式', '采样', '接回血', '四处下游'],
       'plain': '打死医疗补给勘探者后 30 秒内，全队血量不会再掉到 70% 以下，'
                '而且回血更快、受伤后立刻回、敌人打你只算一半。'
                '实现只用一个公式：Max（0.7, LockFloat（Lock = 医疗无人机, Value = DwarvesHealth））。'
                '关键在 LockFloat 会「采样一次然后保持住」，锁的正是开门那一瞬间的血量。',
       'table': [('读取', '全队血量比例 DwarvesHealth，开门瞬间采样一次'),
                 ('判断', 'Max 取「锁到的血量」与 70% 里更高的那个'),
                 ('输出', '接管全局回血上限 HealthRegenerationMax，再改写三处参数')]},
 '④': {'flow': ['评级', '防抖', '酒名', '杀手黑啤', '红岩', '昏迷黑啤'],
       'plain': '每过一个阶段，mod 按你这一阶段的表现给一个 0~6 的评级，换算成酒名播报出来，'
                '并解锁对应的「啤酒」奖励：评级 4 给 5 秒回血，评级 5 给 20 秒回血 + 减伤，'
                '评级 6 给 20 秒无敌 + 清图。评级每阶段只采样一次，中途不许跳档。',
       'table': [('读取', '每分钟击杀 / 硝石采集效率 / 1 分钟内倒人数 / 团队状态评估'),
                 ('判断', 'Sequence 加减分 → 0~6 档 → LockFloat 每阶段锁一次'),
                 ('输出', '三套啤酒技能，各自用 Sequence 存次数、TriggerTimer 攒次数')]},
 '⑤': {'flow': ['检测', '锁存', '换池', '清场', '补给'],
       'plain': '全队被打得很惨、而兜底次数还没用掉时，图上会刷出两颗悬停的石头当「是 / 否」按钮。'
                '打爆绿灯就启动兜底：清场、换一套怪池 150 秒、给 25 秒无敌，'
                '免费补给与满血复活各 +1。打爆红灯、或者干脆不管，就当没发生过。',
       'table': [('读取', '团队状态评估 / 生态重置次数 / 危机庇护是否占用'),
                 ('判断', '状态 ≤ 0.4 且还有次数 → 刷出「是 / 否」单位'),
                 ('输出', '生态重置激活 → 一整套兜底效果')]},
 '⑥': {'flow': ['计时', '判断', '锁存', '换池', '分发'],
       'plain': '每过一个阶段，mod 会看你这阶段打得怎么样——击杀效率、死亡率、采矿量，'
                '还有你叫了几次补给。据此从 5 套怪池里挑一套换上；同一套不会连着出现两次；'
                '选中的池子会发给全图所有出怪器。',
       'table': [('读取', '本阶段击杀数 / 死亡 / 采集量 / 补给调用次数'),
                 ('判断', '有效 KPM 高或低 → 5 套怪池的映射表'),
                 ('输出', '最终生效怪池编号 → 单位名数组 → 全局敌人池')]},
}

STEP_NOTE = {
 '①-1': '先把两个入口铺好：地图硝石产出关掉，补给成本改成读变量。',
 '①-2': '造一个只往上加的账本——把「累计击杀数」转成「这一帧新增的击杀数」。',
 '①-3': '账本的点数还要乘一个自己会涨的倍率：击杀越密，涨得越快。',
 '①-4': '每满 60 点换一次免费补给，最多 6 次；每叫一次补给扣掉一次。',
 '①-5': '「免费」的实现是把成本乘 0，而不是去改成本数字。',
 '①-6': '把计数器播成 0/6 … 6/6——数组长度必须和 Sequence 同步。',
 '②-1': '这五个勘探者不是手刷的，是一张权重表抽出来的。',
 '②-2': '一次性的击杀事件，先拉成一个 30 秒的持续窗口。',
 '②-3': '窗口被一个「总闸门」读取：闸门是并联条件取反，默认开、被事件关。',
 '②-4': '另外两只勘探者改的是全局乘子：敌伤 ×0.8、弹速 ×0.5。',
 '②-5': '条件乘子必须写 Else，漏了整条链归零；颜色只是外观，逻辑只认 ED id。',
 '③-1': '整节就一个公式：Max（0.7, LockFloat（Lock = 医疗无人机, Value = DwarvesHealth））。',
 '③-2': 'LockFloat 的两种接法，以及它为什么能当「采样保持器」。',
 '③-3': '游戏里没有「血量下限」参数，所以只能临时抬高「回血天花板」。',
 '③-4': '同一个开关要接四处下游，才凑齐锁血 + 回血 + 免延迟 + 减伤。',
 '④-1': '评级是一个 0~6 的阶梯，每阶段重算一次。',
 '④-2': '加一层锁存，让评级在阶段中途不许跳档。',
 '④-3': '把 0~6 档播成酒名——数组下标就是评级数字。',
 '④-4': '评级 4：16 秒充能窗口里每 5 秒攒一次，最多 3 次。',
 '④-5': '评级 5：61 秒窗口里每 15 秒攒一次，还要本阶段用过补给。',
 '④-6': '评级 6：无敌是把一个乘子变成 0，清图是刷一只一出生就自爆的单位。',
 '⑤-1': '判断「现在该不该弹兜底」：状态够差、次数还有、庇护没占用。',
 '⑤-2': '打爆绿灯 = 是、红灯 = 否；用锁存把结果固定住。',
 '⑤-3': '激活瞬间摇一次 0~4，然后锁住不再抖动。',
 '⑤-4': '一次性把七项兜底效果全部挂上去。',
 '⑤-5': '用两条播报让玩家知道发生了什么。',
 '⑥-1': '把游戏时间切成一个个「阶段」，并给出阶段切换的那一瞬间。',
 '⑥-2': '先算四个「本阶段」统计量，再折算成三条 true/false 判定。',
 '⑥-3': '三条判定 → 0~4 号怪池；再用奇偶双锁存让评价延迟一个阶段生效。',
 '⑥-4': '发现连续两个阶段用了同一池，就换成另一个池。',
 '⑥-5': '把编号展开成 5 套敌人名单，发给所有读取它的地方。',
 '⑥-6': '同一套评级也是功能 ④ 的主角，这里只补它另外三个下游。',
 '⑥-7': '前面那些统计量，原始数据从哪来。',
}

MERGE = {
 '①': [('关掉地图硝石，把补给成本换成变量引用', ['A']),
        ('硝石存量：Accumulate + Delta 的记账法', ['B']),
        ('硝石获取增益：击杀与时间双驱动', ['C']),
        ('免费补给次数：Sequence 既是计数器也是上限', ['D']),
        ('补给硝石量：免费是乘 0，不是减免', ['E']),
        ('面板播报：数组长度必须与 Sequence 同步', ['F'])],
 '②': [('这五个勘探者从哪来', ['A']),
        ('击杀边沿 → 30 秒窗口', ['B']),
        ('效果一：用闸门变量停掉恒压潮', ['C']),
        ('效果二、三：条件乘子', ['D']),
        ('Else 必须显式写 1，颜色只是 Materials', ['E'])],
 '③': [('核心公式', ['A']),
        ('LockFloat 当采样保持器', []),
        ('从「回血上限」到「血量下限」', ['B', 'C']),
        ('同一个开关的另外三处下游', ['D'])],
 '④': [('评级：Sequence + Reset 的周期状态机', ['A']),
        ('防抖：每阶段只采样一次', []),
        ('酒名播报', ['F']),
        ('杀手黑啤（==4）：5 秒回血', ['B']),
        ('红岩爆破手（==5）：20 秒回血 + 50% 减伤', ['C']),
        ('昏迷黑啤（==6）：20 秒无敌 + 清图', ['D', 'E'])],
 '⑤': [('前置：条件检测', ['1']), ('激活锁存：`生态重置激活`', ['2']),
        ('随机换池：`生态重置怪池选择`', ['3']),
        ('清场 / 无敌 / 补给 / 复活 / 延迟反弹', ['4']),
        ('玩家可见播报', ['5'])],
 '⑥': [('前置：时间定周期', ['A']),
        ('判断：三条布尔判定 + 一个效率因子', ['B', 'C']),
        ('决定：`选择逻辑:物竞天择` → 双锁存', ['D']),
        ('决定：疲劳转换（避免连续同怪池）', []),
        ('改变：`最终生效怪池` → 分发', ['E', 'F']),
        ('并行评价：`玩家阶段表现等级评估`', ['G']),
        ('附录：判断链用到的底层指标', ['H'])],
}

# ── R11：Cookbook 入口 —— 从「我想做什么」反查配方 ─────────────────────
#   左列是玩法目标，中列是配方编号（由下方 fmap 生成锚点），右列是这类需求通常
#   会用到的原语。只做导航，不在这里解释原语含义（那是 Reference 的事）。
CB_GOALS = [
    ('让一个数值自己累加、记账', '①', 'Accumulate · Delta'),
    ('一次性事件 → 拉成一个持续窗口', '②', 'TriggerOnChange · TriggerFixedDuration'),
    ('在关键时刻采样一次并保持住', '③', 'LockFloat · Max'),
    ('按阶段发奖励、播报', '④', 'Sequence · TriggerTimer'),
    ('满足条件才出现的兜底机制（是 / 否）', '⑤', '状态评估 · 是 / 否选择单位'),
    ('按玩家表现动态换怪池', '⑥', 'Sequence · 怪物池分发'),
    ('计时 / 冷却 / 延迟', '② ④ ⑤ ⑥', 'StopWatch · TriggerTimer · TriggerDelay'),
]

_LOCKS = urllib.parse.quote('LockFloat, LockBoolean, LockString')

# R11：每道配方末尾的「想深入了解」出口 —— 锚点全部来自构建产物，已被跨页锚点检查覆盖
CB_REF = {
    '①': [('模块 · 硝石倍率 NitraMultiplier', '../modules/#nitramultiplier'),
          ('模块 · 补给 Resupply', '../modules/#resupply'),
          ('Mutator · 累加 Accumulate', '../mutators/#accumulate'),
          ('Mutator · 变量 Delta', '../mutators/#delta')],
    '②': [('敌人生成器 Spawner', '../enemies/#spawner'),
          ('Mutator · 变化触发 TriggerOnChange', '../mutators/#triggeronchange'),
          ('Mutator · 固定持续时间 TriggerFixedDuration', '../mutators/#triggerfixedduration')],
    '③': [('Mutator · ' + '、'.join(['锁定浮点数', '锁定布尔值', '锁定字符串']),
           '../mutators/#' + _LOCKS),
          ('Mutator · 最大值 Max', '../mutators/#max'),
          ('Mutator · 团队生命值比例 DwarvesHealth', '../mutators/#dwarveshealth'),
          ('模块 · 矮人属性 Dwarves', '../modules/#dwarves')],
    '④': [('Mutator · 序列 Sequence', '../mutators/#Sequence'),
          ('Mutator · 秒表 StopWatch', '../mutators/#StopWatch'),
          ('Mutator · 定时触发 TriggerTimer', '../mutators/#triggertimer')],
    '⑤': [('Mutator · ' + '、'.join(['锁定浮点数', '锁定布尔值', '锁定字符串']),
           '../mutators/#' + _LOCKS),
          ('模块 · 怪池 Pools', '../modules/#pools'),
          ('Mutator · 非零判断 Nonzero', '../mutators/#Nonzero')],
    '⑥': [('模块 · 怪池 Pools', '../modules/#pools'),
          ('Mutator · 已击杀敌人数量 EnemiesKilled', '../mutators/#enemieskilled'),
          ('Mutator · 已呼叫补给次数 ByResuppliesCalled', '../mutators/#byresuppliescalled'),
          ('Mutator · 近期生成敌人计数 EnemiesRecentlySpawned',
           '../mutators/#enemiesrecentlyspawned')],
}


def main():
    raw = io.open(MD, encoding='utf-8').read()
    secs, head = parse(raw)
    h1 = next((s for s in secs if s['lv'] == 1), None)
    title = h1['text'] if h1 else '功能实作'

    groups, pre = [], []
    for s in secs:
        if s['lv'] == 1:
            continue
        if s['lv'] == 2:
            groups.append({'h': s, 'sub': []})
        elif groups:
            groups[-1]['sub'].append(s)
        else:
            pre.append(s)

    html = [f'<h1 id="ns-case">{esc(title)}</h1>',
            # R13 §6：定位句必须在最前——读者一眼就知道这是「完整案例」而不是要通读的教程
            '<p><b>这一页是什么：</b>一个完整案例的拆解（Case Study）——回答的是'
            '<b>「一整套机制是怎么拼起来的」</b>。<b>它不要求你从头读到尾</b>：'
            '每道功能后面都有一行「想深入了解」，指向对应字段的完整定义。'
            '只想先做一个小改动，请去看 <a href="../common-edits/">常见修改 · Cookbook</a>；'
            '完全没接触过 CD2，从 <a href="../tutorial/">新手入门</a> 开始。</p>']
    if h1 and any(x.strip() for x in h1['lines']):   # H1 下面的引言/元信息（此前被整个丢掉）
        html.append(render(h1['lines']))
    html += ['<p>下面用的是一个真实存在、能在游戏里跑起来的难度：<b>Hazard 9 · 物竞天择</b>。'
             '它用到的 CD2 能力比较全面——动态取值、变量池、'
             '波次生成、敌人描述符、底层属性都用上了。</p>',
             '<p><b>为什么拿它当样本：</b>这个难度是本站作者自己做的，并且已经在游戏里实测跑过。'
             '拿自己的东西拆解有两个好处：一是<b>讲解不会猜错</b>——每一处为什么这么写，'
             '都是设计时就定下来的，不用靠猜别人的意图；二是<b>每一段都能跑</b>——'
             '你照着抄不会碰上「看着是对的、进游戏却不生效或者直接报错」这类问题。</p>',
             '<p>这里写的不是「这个难度多好玩」，而是<b>「它想实现某个效果时，具体是怎么拼出来的」</b>。'
             '每一步都给出对应的真实代码，你可以照着改。'
             '<b>源文件：</b><a href="../assets/files/Hazard9-NaturalSelection-v0.18.13.json" download>'
             'Hazard 9 · 物竞天择 · v0.18.13（JSON，210 KB）</a></p>',
             '<p class="mt-global"><b>怎么读这页：</b>这页按<b>由浅入深</b>排，建议从头顺着看——'
             '①~④ 各只用到一个到几个原语，学会了再看 ⑤⑥ 这两套系统。'
             '第一遍只看每个功能的流程条、「它做了什么」和精简骨架；'
             '「实现拆解」是你动手写类似功能时的对照参考，可以整节跳过。</p>']
    html.append(render(head))
    for s in pre:
        html.append(f'<h{s["lv"]} id="{slug(s["text"])}">{inline(s["text"])}</h{s["lv"]}>')
        html.append(render(s['lines']))

    fmap = {}
    for g in groups:
        m = re.match(r'功能\s*([①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬])', g['h']['text'])
        if m:
            fmap[m.group(1)] = slug(g['h']['text'])
    # R11：Cookbook 入口表 —— 放在功能索引之前，先按「我想做什么」找，再按难度浏览
    grows = []
    for goal, num, prim in CB_GOALS:
        nums = num.split()
        if len(nums) == 1 and nums[0] in fmap:
            where = f'<a href="#{fmap[nums[0]]}">功能 {nums[0]}</a>'
        else:
            inner = ' '.join(
                (f'<a href="#{fmap[n]}">{n}</a>' if n in fmap else esc(n)) for n in nums)
            where = '功能 ' + inner
        grows.append(f'<tr><td>{esc(goal)}</td><td>{where}</td>'
                     f'<td>{esc(prim)}</td></tr>')
    html.append('<h2 id="cb-goals">按目标查案例</h2>')
    html.append('<p>不知道从哪一节开始，就先看这张表：左边是<b>你想实现的效果</b>，'
                '中间是对应的功能，右边是这类需求通常会用到的原语。</p>')
    html.append('<table><thead><tr><th>我想做什么</th><th>先看哪一节</th>'
                '<th>通常会用到的原语</th></tr></thead><tbody>'
                + ''.join(grows) + '</tbody></table>')
    html.append('<p class="mt-global">字段的完整含义不在本页：顶层模块查 '
                '<a href="../modules/">模块</a>，条件与计算查 '
                '<a href="../mutators/">Mutator</a>，敌人控制项查 '
                '<a href="../enemies/">敌人配置</a>。</p>')
    rows = []
    for num, cn, one, star in (('①', '硝石经济改造', '关掉地图硝石，改用一本自己记的账', '★'),
                               ('②', '勘探者无人机', '击杀换一个 20~30 秒的开关', '★★'),
                               ('③', '锁血', '把回血上限钉在当前血量上', '★★★'),
                               ('④', '阶段评级 → 三种啤酒', '每阶段发一次奖', '★★★★'),
                               ('⑤', '生态重置', '兜底救援 · 是/否选择', '★★★★★'),
                               ('⑥', '物竞天择', '判断玩家水平 → 决定怪池 → 避免连续同怪池', '★★★★★★')):
        name = f'<a href="#{fmap[num]}">{num} {cn}</a>' if num in fmap else f'{num} {cn}'
        rows.append(f'<tr><td>{name}</td><td>{one}</td><td>{star}</td></tr>')
    html.append('<h2 id="ns-index">功能索引</h2>')
    html.append('<p>六个功能按<b>由浅入深</b>排列：①~④ 是单个原语的用法，'
                '⑤⑥ 是把很多原语拼成一套系统。</p>')
    html.append('<table><thead><tr><th>功能</th><th>一句话</th><th>难度</th></tr></thead>'
                '<tbody>' + ''.join(rows) + '</tbody></table>')

    for g in groups:
        h = g['h']
        aid = slug(h['text'])
        subs = {s['text']: s for s in g['sub']}
        order = [s['text'] for s in g['sub']]
        num = re.match(r'功能\s*([①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬])', h['text'])
        num = num.group(1) if num else ''
        guide = GUIDE.get(num)

        code_map, code_order = {}, []
        if '完整代码' in subs:
            cur = None
            for ln in subs['完整代码']['lines']:
                m = re.match(r'^####\s+(?:([A-Z])\.|(\d+)\.)\s*(.*)$', ln)
                if m:
                    cur = m.group(1) or m.group(2)
                    code_map[cur] = {'label': m.group(3).strip(), 'lines': []}
                    code_order.append(cur)
                elif cur and not ln.strip().startswith('```'):
                    code_map[cur]['lines'].append(ln)

        short = re.sub(r'^功能\s*([①-⑬])\s*[「『]?([^·」』（(]+).*$', r'功能 \1 · \2',
                       h['text']).strip().rstrip(' ·')
        html.append(f'<h2 id="{aid}">{inline(short)}</h2>')
        if any(x.strip() for x in h['lines']):   # h2 的直属内容（如「阅读前」的列表）
            html.append(render(h['lines']))

        if guide:
            parts = [f'<a class="fs-chip" href="#{aid}-s{min(k+1, 7)}">{c}</a>'
                     for k, c in enumerate(guide['flow'])]
            html.append('<p class="flow-strip">' +
                        '<span class="fs-arrow">→</span>'.join(parts) + '</p>')

        if '它做了什么' in subs:
            html.append(f'<h3 id="{aid}-intro">它做了什么</h3>')
            if guide:
                html.append(f'<p>{inline(guide["plain"])}</p>')
                tr = ''.join(f'<tr><td><b>{k}</b></td><td>{v}</td></tr>'
                             for k, v in guide['table'])
                html.append(f'<table class="mf-table mf-guide"><tbody>{tr}</tbody></table>')
            else:
                html.append(render(subs['它做了什么']['lines']))

        # R11：每道配方的 Reference 出口（不让本页变成又一个需要通读的大分类）
        ref = CB_REF.get(num)
        if ref:
            links = ' · '.join(f'<a href="{u}">{esc(t)}</a>' for t, u in ref)
            html.append(f'<p class="ns-ref"><b>想深入了解：</b>{links}</p>')

        if '精简骨架' in subs:
            html.append(f'<h3 id="{aid}-skeleton">精简骨架</h3>')
            html.append(render_skeleton(subs['精简骨架']['lines']))

        if '实现拆解' in subs:
            html.append(f'<h3 id="{aid}-impl">实现拆解</h3>')
            steps, cur = [], None
            for ln in subs['实现拆解']['lines']:
                m = re.match(r'^####\s+(?:\d+\.\s*)?(.*)$', ln)
                if m:
                    cur = {'title': m.group(1).strip(), 'lines': []}
                    steps.append(cur)
                elif cur is not None:
                    cur['lines'].append(ln)
            mapping = MERGE.get(num)
            if mapping and len(steps) < len(mapping):
                for extra in mapping[len(steps):]:
                    steps.append({'title': extra[0], 'lines': []})
            for k, st in enumerate(steps):
                t = re.sub(r'`([^`]+)`', r'\1', st['title'])
                cn = CIRCLED[k] if k < len(CIRCLED) else str(k + 1)
                html.append(f'<h4 id="{aid}-s{k+1}">{cn} {inline(t)}</h4>')
                sn = STEP_NOTE.get(f'{num}-{k+1}')
                if sn:
                    html.append(f'<p class="step-note">这一步在算什么：{inline(sn)}</p>')
                always, dive = split_step(st['lines'])
                if always:
                    html.append(render(always))
                if dive:
                    html.append(f'<details class="ns-dive"><summary>{cn} · 详解：公式与推演'
                                f'</summary><div class="ns-dive-body">{render(dive)}</div>'
                                f'</details>')
                keys = mapping[k][1] if mapping and k < len(mapping) else [str(k + 1)]
                for key in keys:
                    cm = code_map.get(key)
                    if cm:
                        html.append(code_html('\n'.join(cm['lines']).strip('\n'),
                                              f'{cn} · {cm["label"]}', False))
            used = set()
            if mapping:
                for _, ks in mapping:
                    used.update(ks)
            else:
                used = set(code_map)
            rest = [k for k in code_order if k not in used]
            if rest:
                html.append('<h4>其余代码</h4>')
                for key in rest:
                    cm = code_map[key]
                    html.append(code_html('\n'.join(cm['lines']).strip('\n'),
                                          f'{key} · {cm["label"]}', False))

        for name in order:
            if name in ('它做了什么', '实现拆解', '完整代码', '精简骨架'):
                continue
            s = subs[name]
            inner = render(s['lines'])
            shortlbl = {'被哪些地方引用': f'{num} · 附：33 处引用清单',
                        '到底是怎么实现的': f'{num} · 附：是/否的实现',
                        '不确定项': f'{num} · 附：细节与待确认',
                        '提取方法': '附：提取方法与可复核性'}.get(
                next((k for k in ('被哪些地方引用', '到底是怎么实现的', '不确定项', '提取方法')
                      if k in name), ''), shorten_label(name))
            html.append(f'<details class="ns-code ns-aside"><summary>{esc(shortlbl)}'
                        f'</summary><div class="ns-aside-body">{inner}</div></details>')

    body = '\n'.join(x for x in html if x)
    body = re.sub(r'`([^`\n]{1,80})`',
                  lambda m: f'<span class="vcode">{esc(m.group(1))}</span>', body)
    io.open(OUT, 'w', encoding='utf-8').write(
        f'<!DOCTYPE html>\n<html lang="zh-CN">\n<head><meta charset="utf-8">'
        f'<title>{esc(title)}</title></head>\n<body>\n'
        f'<div role="main" class="document"><div class="section" itemprop="articleBody">\n'
        f'{body}\n</div></div>\n</body>\n</html>\n')
    print(f'✔ {OUT}')
    print(f'   功能块 {len(groups)}｜折叠条 {body.count("ns-code") // 2}｜'
          f'h4 步骤 {body.count("<h4")}｜正文 {len(body):,} 字符')


if __name__ == '__main__':
    main()
