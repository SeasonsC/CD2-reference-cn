# -*- coding: utf-8 -*-
"""
Mutators「字段表」重设计：散文类型栏 → 字段表 + 返回类型
────────────────────────────────────────────────────────────
输入（源站散文）：
    类型 — 输入：Initial（数值）、Value（数值 / Mutator）、Min、Max（夹取范围） · 输出：float

输出：
    字段  = [(名称, 类型, 注记), …]
    返回  = ('float', None)
    说明  = [补充说明, …]        # 「；」之后的内容

原则：不推测缺失的类型；类型列只放明确的类型词，其余注记进「注记」。
"""
import re, html as H

CJK = re.compile(r'[\u4e00-\u9fff]')
# 兼容两种输入：带 <b> 标签的原始 HTML，以及已取过 text_content() 的纯文本
PREFIX = re.compile(r'^\s*(?:<b>)?类型(?:</b>)?\s*[—\-–]\s*')
PAREN = re.compile(r'^(?P<name>.*)（(?P<note>[^（）]*)）\s*$')   # 贪婪：取最后一组括号
# 「And / Or 的任意布尔字段」这类——英文标识符 + 中文描述，本身不是字段名
NAME_DESC = re.compile(r'^(?P<name>[A-Za-z0-9_][A-Za-z0-9_.: /+\-–—]*?)(?:的)?(?P<desc>[\u4e00-\u9fff].*)$')
IDENT = re.compile(r'^[A-Za-z0-9_][A-Za-z0-9_.: /+\-–—]*$')

# 明确的「类型词」——只有这些进类型列，其余进注记列（不猜测）
TYPE_WORDS = {
    '数值', 'float', 'Float', 'int', 'Int', '整数', '浮点数', 'Boolean', 'boolean',
    'bool', 'Bool', 'string', 'String', '数组', 'Array', 'Mutator',
    '任意', '值类型自定', '索引',
}
# 单位与格式类注记（不算类型）
UNIT_HINT = re.compile(r'^(秒|每秒|cm|°|%|概率|次数|个|米|帧)$')

try:
    from mut_field_notes import FIELDS as NOTES
    from mut_field_notes import REPLACE, RETURN as RET_OVERRIDE, EXTRA_NOTE
    from mut_field_notes import RETURN_ONLY
except Exception as _e:                             # noqa: BLE001
    # 语料缺失不应中断构建，但**必须报出来**——静默吞掉会让人以为语料生效了
    import sys as _sys
    print(f'⚠️  mut_field_notes 加载失败，字段语料未生效：{_e!r}', file=_sys.stderr)
    NOTES, REPLACE, RET_OVERRIDE, EXTRA_NOTE = {}, {}, {}, {}
    RETURN_ONLY = set()



def esc(s):
    return H.escape(s or '', quote=True)


def split_top(s, seps):
    """按 seps 切分，忽略括号内部的分隔符。"""
    out, buf, depth = [], [], 0
    for ch in s:
        if ch in '（(':
            depth += 1
        elif ch in '）)':
            depth = max(0, depth - 1)
        if depth == 0 and ch in seps:
            out.append(''.join(buf))
            buf = []
        else:
            buf.append(ch)
    out.append(''.join(buf))
    return [x.strip() for x in out]


def classify(note):
    """括号里的内容 → ('type', 值) 或 ('note', 值) 或 (None, None)。"""
    n = (note or '').strip()
    if not n:
        return None, None
    if n in TYPE_WORDS:
        return 'type', n
    # 复合类型：「数值 / Mutator」「int / float」「ED / EDs」——各段都是类型词才算
    segs = [x.strip() for x in re.split(r'\s*[/、]\s*', n) if x.strip()]
    if len(segs) > 1 and all(s in TYPE_WORDS or s in ('ED', 'EDs', 'Integer') for s in segs):
        return 'type', n
    # 「数值，默认 0」这类：类型 + 附加说明
    for t in TYPE_WORDS:
        if n.startswith(t + '，') or n.startswith(t + ','):
            return 'type_desc', (t, n[len(t) + 1:].strip())
    return 'note', n


def parse(text):
    t = PREFIX.sub('', H.unescape(text or '')).strip()
    inp_raw, out_raw = '', t
    if '· 输出：' in t:
        inp_raw, out_raw = t.split('· 输出：', 1)
    inp_raw = re.sub(r'^输入：', '', inp_raw).strip()

    notes, fields = [], []
    if inp_raw and inp_raw != '无':
        parts = split_top(inp_raw, '；')
        notes = [x for x in parts[1:] if x]
        raw_items = [x for x in split_top(parts[0], '、') if x]
        # 「A + 各X字段（数值）」这种开放写法：拆成具名字段 + 一行开放说明
        for it in raw_items:
            m = PAREN.match(it)
            name, note = (m.group('name').strip(), m.group('note')) if m else (it.strip(), None)
            if ' + ' in name:
                head, tail = name.split(' + ', 1)
                kind, val = classify(note)
                # 「Default + 各群系键（数值）」：括号里的说明属于右边那个开放字段，
                # 不属于 Default —— 归属含糊时按「不推测」处理，Default 留空
                fields.append((head.strip(), None, None))
                if tail.strip():
                    if kind == 'type':
                        fields.append(('+' + tail.strip(), val, None))
                    elif kind == 'type_desc':
                        fields.append(('+' + tail.strip(), val[0], val[1]))
                    elif kind == 'note':
                        fields.append(('+' + tail.strip(), None, val))
                    else:
                        fields.append(('+' + tail.strip(), None, None))
                continue
            if name.startswith('各'):
                fields.append(('+' + name, None, None))
                continue
            kind, val = classify(note)
            if kind == 'type':
                fields.append((name, val, None))
            elif kind == 'type_desc':
                fields.append((name, val[0], val[1]))
            elif kind == 'note':
                fields.append((name, None, val))
            elif not name.startswith('+'):
                # 「And / Or 的任意布尔字段」：拆成 字段名 + 描述
                m2 = NAME_DESC.match(name)
                if m2 and ' ' in name:
                    fields.append((m2.group('name').strip(), None, m2.group('desc').strip()))
                else:
                    fields.append((name, None, None))
            else:
                fields.append((name, None, None))
    # 「Min、Max（夹取范围）」：注记应同时作用于 Min 与 Max
    fields = _spread_shared(fields)

    out = split_top(out_raw, '、；')[0] if out_raw else ''
    ret, ret_note = None, None
    if out:
        m = PAREN.match(out)
        if m:
            ret, ret_note = m.group('name').strip(), m.group('note').strip()
        else:
            ret = out.strip()
    return {'fields': fields, 'ret': ret, 'ret_note': ret_note, 'notes': notes}


def _spread_shared(fields):
    """「Min、Max（夹取范围）」——注记/类型作用于整段裸字段；
       但「ED、CooldownTime（秒）」的「秒」只属于后者，不能回溯。
       区分依据：单位类注记不回填，其余（类型、片语）回填。"""
    out = list(fields)
    i = 0
    while i < len(out):
        j = i
        while j < len(out) and not out[j][1] and not out[j][2]:
            j += 1
        if j < len(out) and j > i:
            ty, nt = out[j][1], out[j][2]
            # 「Default + 条件键（数值）」这类归属含糊的开放字段：不回溯
            if out[j][0].startswith('+'):
                i = j + 1
                continue
            share = None
            if ty:                                  # 类型可回填
                share = ('type', ty)
            elif nt and not UNIT_HINT.match(nt):    # 非单位注记可回填
                share = ('note', nt)
            if share:
                for k in range(i, j):
                    out[k] = (out[k][0], share[1], None) if share[0] == 'type' \
                        else (out[k][0], None, share[1])
        i = j + 1
    return out


# 代码类型 → 中文注解（只是给新作者的中文提示，不改语义）
TYPE_GLOSS = {'float': '浮点数', 'int': '整数', 'bool': '布尔值',
              'string': '字符串', 'Array': '数组'}


def _ret_line(d, key=''):
    if key in RET_OVERRIDE:
        return (f'<p class="mf-ret"><b>返回：</b> {RET_OVERRIDE[key]}</p>')
    if not d['ret']:
        return ''
    code = _code_type(d['ret'])
    gloss = TYPE_GLOSS.get(code) or ''
    if d['ret_note']:
        gloss = f'{gloss}，{d["ret_note"]}' if gloss else d['ret_note']
    r = f'<p class="mf-ret"><b>返回：</b> <code>{esc(code)}</code>'
    if gloss:
        r += f'<span class="mf-gloss">（{esc(gloss)}）</span>'
    return r + '</p>'


# 「夹取范围」这类模糊注记 → 按字段名换成明确措辞
NOTE_BY_NAME = {
    'min': '最小值', 'max': '最大值',
    'minedge': '最小值', 'maxedge': '最大值',
}

# 中文类型词 → 代码类型（面向开发者；只做词表替换，不改语义）
TYPE_CODE = {
    '数值': 'float', '浮点数': 'float', 'float': 'float',
    '整数': 'int', 'int': 'int',
    '布尔': 'bool', 'Boolean': 'bool', 'boolean': 'bool', 'bool': 'bool',
    '字符串': 'string', 'string': 'string', 'String': 'string',
    '数组': 'Array', 'Array': 'Array',
    'Mutator': 'Mutator',
    '任意': 'any', '值类型自定': 'any',
    '索引': 'int',
}


def _code_type(ty):
    """类型列：优先代码类型；词表里没有的原样保留（不猜测）。"""
    if not ty:
        return ty
    t = ty.strip()
    if t in TYPE_CODE:
        return TYPE_CODE[t]
    segs = [x.strip() for x in re.split(r'\s*/\s*', t)]
    if len(segs) > 1 and all(s in TYPE_CODE for s in segs):
        return ' / '.join(TYPE_CODE[s] for s in segs)
    return t


# ── 第三轮：「填写」列（这里应该放什么） ─────────────────────────────────
# 源文类型词 → 填写语。显式代码类型（float/int/...）额外把类型名括注出来，
# 保留原文精度；中文词只给自然语言，不硬塞代码类型。
FILL_CJK = {
    '数值': '数字', '浮点数': '数字', '整数': '整数',
    'Boolean': '布尔值', 'boolean': '布尔值', '布尔': '布尔值',
    'string': '字符串', '字符串': '字符串',
    '数组': '数组', 'Array': '数组',
    'Mutator': 'Mutator',
    '任意': '任意值', '值类型自定': '任意值', 'any': '任意值',
    '索引': '数字（索引）',
}
FILL_CODE_NOTE = {'float': 'float', 'int': 'int', 'bool': 'bool',
                  'Boolean': 'bool', 'string': 'string', 'Array': 'Array'}


def _fill(ty):
    """类型 → 填写列文案。原文没给类型时返回 None（由调用方决定留空）。"""
    if not ty:
        return None
    t = ty.strip()
    segs = [x.strip() for x in re.split(r'\s*/\s*', t)]
    out = []
    for s in segs:
        if s in FILL_CJK:
            out.append(FILL_CJK[s])
        elif s in FILL_CODE_NOTE:
            # 原文已是代码类型：自然语 + 括注，保留精度
            base = FILL_CJK.get({'float': '数值', 'int': '整数', 'bool': 'Boolean',
                                 'Boolean': 'Boolean', 'string': 'string',
                                 'Array': '数组'}.get(s, s), s)
            out.append(f'{base}（{FILL_CODE_NOTE[s]}）')
        else:
            out.append(s)
    return ' 或 '.join(out) if len(out) > 1 else out[0]


# ── 「作用」列：字段名 → 这个字段控制什么 ─────────────────────────────────
# 只写字段名本身已明确表达的含义，不编造原文没有的行为。
ROLE_BY_NAME = {
    'initial': '设置初始值',
    'value': '要处理的值',
    'min': '限制最小值',
    'max': '限制最大值',
    'default': '没有匹配结果时使用的值',
    'defaultvalue': '默认值',
    'type': '选择取值方式',
    'enable': '是否启用',
    'enabled': '是否启用',
    'reset': '是否重置',
    'in': '输入信号',
    'values': '一组可选值',
    'then': '条件成立时返回的值',
    'else': '条件不成立时返回的值',
    'resource': '资源类型',
    'ed': '敌人描述符',
    'eds': '敌人描述符（一组）',
    'sequence': '要循环的数组',
    'next': '是否前进一位',
    'previous': '是否后退一位',
    'interval': '自动前进的间隔',
    'repeat': '是否循环',
    'lock': '是否锁定',
    'update': '是否更新',
    'choices': '候选数组',
    'weights': '各项权重',
    'sep': '分隔符',
    'select': '要选中的项',
    'array': '供选择的数组',
    'shuffle': '是否打乱顺序',
    'shuffleonce': '是否每局只打乱一次',
    'initialoffset': '起始位置',
    'start': '起始值',
    'stop': '结束值',
    'startdelay': '延迟多久开始',
    'rateofchange': '每秒变化多少',
    'initialvalue': '初始值',
    'condition': '判断条件',
    'round': '是否取整',
    'exclude': '要排除的描述符',
    'descriptors': '敌人描述符列表',
    'biome': '生物群系',
    'missiontype': '任务类型',
    'stage': '阶段',
    'period': '周期',
    'high': '高值',
    'low': '低值',
}


def _role(nm, nt):
    """作用列：优先用字段名明确含义；其次用原文注记（若非单位/格式类）。"""
    key = re.sub(r'[^a-z0-9]', '', nm.lower())
    if key in ROLE_BY_NAME:
        return ROLE_BY_NAME[key]
    if nt in ('夹取范围', '范围'):
        return None
    return None



def _note(nm, nt):
    if nt in ('夹取范围', '范围'):
        key = re.sub(r'[^a-z]', '', nm.lower())
        return NOTE_BY_NAME.get(key, nt)
    return nt


def to_html(text, anchor=None):
    """散文类型栏 → 「字段表（字段 / 填写 / 作用） + 返回」。
       anchor：当前 Mutator 的锚点 id，用于套用人工语料（mut_field_notes）。"""
    d = parse(text)
    key = (anchor or '').lower()
    notes = NOTES.get(key, {})
    parts = []
    # 「键 → 值」映射型：只给返回行，不出字段表
    if key in RETURN_ONLY:
        return ('<div class="mt-fields mt-fields-ret">'
                + _ret_line(d, key) + '</div>')
    if key in REPLACE:
        d['fields'] = REPLACE[key]
    if d['fields']:
        rows = []
        for nm, ty, nt in d['fields']:
            cls_extra = ''
            cls = ' class="mf-plus"' if nm.startswith('+') else ''
            ov = notes.get(nm)
            if ov is None and nm in notes:
                continue                                # 语料置 None = 删掉该行
            note = nt or ''
            if ov:
                fill, role = ov[0], ov[1]
                opt = len(ov) > 2 and ov[2]
            else:
                fill = _fill(ty)
                role = _role(nm, nt)
                if not fill and note and UNIT_HINT.match(note):
                    fill = f'数字（{note}）'
                opt = ('可选' in note) or bool(re.search(r'默认\s*\S', note))
                m_def = re.search(r'默认\s*([^，,）]+)', note)
                if m_def and not role:
                    role = f'默认 {m_def.group(1).strip()}'
                if role is None and note and note not in ('夹取范围', '范围') \
                        and '可选' not in note and not UNIT_HINT.match(note) \
                        and '默认' not in note:
                    role = note
            # 「可选」放在字段名后，避免被误读成「填写内容可以随便写」
            if opt:
                cls_extra = ' <span class="mf-opt">可选</span>'
            fill_cell = _fill_html(fill) if fill else '<span class="mf-empty">—</span>'
            role_cell = esc(role) if role else '<span class="mf-empty">—</span>'
            rows.append(f'<tr><td{cls}><code>{esc(nm)}</code>{cls_extra}</td>'
                        f'<td>{fill_cell}</td><td>{role_cell}</td></tr>')
        parts.append('<table class="mf-table mf-fields"><thead><tr>'
                     '<th>字段</th><th>填写</th><th>作用</th></tr></thead><tbody>'
                     + ''.join(rows) + '</tbody></table>')
    else:
        parts.append('<p class="mf-none">无需配置字段</p>')
    parts.append(_ret_line(d, key))
    nz = list(d['notes'])
    if key in EXTRA_NOTE:
        nz.append(EXTRA_NOTE[key])
    if nz:
        parts.append('<p class="mf-note">' +
                     '；'.join(esc(x) for x in nz) + '</p>')
    return '<div class="mt-fields">' + ''.join(parts) + '</div>'


def _fill_html(fill):
    """填写列：识别其中的代码/API 词，套 <code>（只有它们用蓝色）。"""
    out = esc(fill)
    for w in ('Mutator', 'Array', 'string', 'bool', 'float', 'int'):
        out = re.sub(rf'(?<![A-Za-z0-9_]){re.escape(w)}(?![A-Za-z0-9_])',
                     f'<code>{w}</code>', out)
    return out


def ret_only_html(text, anchor=None):
    """正文里已有字段表时，只输出「返回：」一行。"""
    d = parse(text)
    key = (anchor or '').lower()
    if key not in RET_OVERRIDE and not d['ret']:
        return ''
    return ('<div class="mt-fields mt-fields-ret">'
            + _ret_line(d, key) + '</div>')

