# -*- coding: utf-8 -*-
"""
Mutator 字段语料（人工撰写，可审阅、可逐条修改）
────────────────────────────────────────────────────────────
FIELDS[(锚点 id 小写)][字段名] = (填写, 作用)  或  (填写, 作用, 可选)
                                 = None          → 删掉这一行
REPLACE[锚点] = [(字段名, 类型, 注记), …]        → 整表替换
RETURN[锚点]  = HTML 片段                        → 覆盖「返回」行
EXTRA_NOTE[锚点] = 文字                          → 追加一条脚注

撰写原则：只依据字段名和原文正文已明确的含义，不编造原文没有的行为。
「填写」用自然语言（数字 / 字符串 / 布尔值 / 数组 / Mutator / 任意值）。
"""

FIELDS = {
    # ── ① Accumulate ────────────────────────────────────────────────
    'accumulate': {
        'Initial': ('数字', '设置初始值'),
        'Value': ('数字或 Mutator', '设置每次累加的值'),
        'Min': ('数字', '限制最小值', True),
        'Max': ('数字', '限制最大值', True),
    },

    # ── Clamp ──────────────────────────────────────────────────────
    'clamp': {
        'Value': ('数字', '要限制的值'),
        'Min': ('数字', '限制最小值'),
        'Max': ('数字', '限制最大值'),
    },

    # ── ③ ByBiome：值是 float / bool / string 皆可 ────────────────────
    'bybiome': {
        'Default': ('数字 / 布尔值 / 字符串', '没有匹配到生物群系时返回的值'),
        '+各群系键': ('数字 / 布尔值 / 字符串', '该生物群系对应的返回值'),
    },

    # ── ④ ByDDStage ────────────────────────────────────────────────
    'byddstage': {
        'Default': ('数字 / 布尔值 / 字符串', '没有匹配到阶段时返回的值'),
        'Stage1–3': ('数字 / 布尔值 / 字符串', '处于该深潜阶段时返回的值'),
    },

    # ── ⑤⑥⑦⑧⑩⑪⑫⑬ 各类 By*：删掉开放式字段行，值类型自由 ──────────────
    'bydna':          {'+条件键（如「任务类型，长度，复杂度」）': None},
    'byescortphase':  {'+各阶段字段': None},
    'bymissiontype':  {'+各任务类型字段': None},
    'bysecondary':    {'+次要目标名字段': None},
    'byrefineryphase': {'+各阶段字段': None},
    'bysabophase':    {'+各阶段字段': None},
    'bysalvagephase': {'+各阶段字段': None},

    # ── ⑭⑮ DuringEggAmbush / DuringMission ─────────────────────────
    'duringeggambush': {
        'StartingAt': ('数字（秒）', '蛋潮开始多少秒后才算「期间」'),
        'StoppingAfter': ('数字（秒）', '蛋潮结束多少秒后就不再算「期间」'),
    },
    'duringmission': {
        'StartingAt': ('数字（秒）', '任务开始多少秒后才算「期间」'),
        'StoppingAfter': ('数字（秒）', '任务结束多少秒后就不再算「期间」'),
    },

    # ── ⑯ EnemiesKilled：作用留空 ───────────────────────────────────
    'enemieskilled': {
        'ED': ('字符串', ''),
        'EDs': ('数组', ''),
    },

    # ── ⑰ EnemiesRecentlySpawned ───────────────────────────────────
    'enemiesrecentlyspawned': {
        'Seconds': ('数字（秒）', '往前统计多少秒内生成的敌人'),
        'ED': ('字符串', ''),
        'EDs': ('数组', ''),
    },

    # ── ⑱ EnemyCooldown ───────────────────────────────────────────
    'enemycooldown': {
        'ED': ('字符串', ''),
        'CooldownTime': ('数字（秒）', ''),
        'ValueDuringCooldown': ('数字', ''),
        'DefaultValue': ('数字', ''),
    },

    # ── ⑲⑳ EnemyHealth / EnemyDistance ────────────────────────────
    'enemyhealth': {
        'ED / EDs': ('字符串 / 数组', '要检测的敌人描述符，单个或一组'),
        'Default': ('数字', '没有匹配的存活敌人时返回的值，默认 0'),
        'Type': ('字符串', '取值方式：Min / Max / Average'),
    },
    'enemydistance': {
        'ED / EDs': ('字符串 / 数组', '要测距的敌人描述符，单个或一组'),
        'Default': ('数字', '没有匹配的存活敌人时返回的值，默认 0'),
        'Type': ('字符串', '取值方式：Min / Max / Average'),
    },

    # ── ㉑ EnemyCount ──────────────────────────────────────────────
    'enemycount': {
        'ED': ('字符串', ''),
        'EDs': ('数组', ''),
    },

    # ── ㉒ IfFloat ─────────────────────────────────────────────────
    'iffloat': {
        'Value': ('数字', ''),
        '比较运算符': ('==、>=、>、<=、<', ''),
    },

    # ── ㉓㉔ Max / Min ─────────────────────────────────────────────
    'max': {'Values': ('数组', '')},
    'min': {'Values': ('数组', '')},

    # ── ㉖ Select ──────────────────────────────────────────────────
    'select': {'+任意命名的选项字段': None},
}

# 整表替换（解析出来的字段名不合适时用）
REPLACE = {
    # ② And / Or 的两个操作数本身就是字段，Not 走脚注
    'and-or-not': [('A', '布尔值', ''),
                   ('B', '布尔值', '')],
}

# 覆盖「返回」行（HTML 片段）
RETURN = {
    'bybiome':         '<code>float</code> / <code>bool</code> / <code>string</code>'
                       '<span class="mf-gloss">（取决于你为各群系设置的值）</span>',
    'byddstage':       '<code>float</code> / <code>bool</code> / <code>string</code>'
                       '<span class="mf-gloss">（取决于你为各阶段设置的值）</span>',
    'bydna':           '<code>float</code> / <code>bool</code> / <code>string</code>'
                       '<span class="mf-gloss">（取决于你设置的值）</span>',
    'byescortphase':   '<code>float</code> / <code>bool</code> / <code>string</code>'
                       '<span class="mf-gloss">（取决于你为各阶段设置的值）</span>',
    'bymissiontype':   '<code>float</code> / <code>bool</code> / <code>string</code>'
                       '<span class="mf-gloss">（取决于你为各任务类型设置的值）</span>',
    'bysecondary':     '<code>float</code> / <code>bool</code> / <code>string</code>'
                       '<span class="mf-gloss">（取决于你为各次要目标设置的值）</span>',
    'byplayercount':   '<code>float</code> / <code>bool</code> / <code>string</code>'
                       '<span class="mf-gloss">（取决于你为各人数设置的值）</span>',
    'byrefineryphase': '<code>float</code> / <code>bool</code> / <code>string</code>'
                       '<span class="mf-gloss">（取决于你为各阶段设置的值）</span>',
    'byresuppliescalled': '<code>float</code> / <code>bool</code> / <code>string</code>'
                          '<span class="mf-gloss">（取决于你为各次数设置的值）</span>',
    'bysabophase':     '<code>float</code> / <code>bool</code> / <code>string</code>'
                       '<span class="mf-gloss">（取决于你为各阶段设置的值）</span>',
    'bysalvagephase':  '<code>float</code> / <code>bool</code> / <code>string</code>'
                       '<span class="mf-gloss">（取决于你为各阶段设置的值）</span>',
}

# 追加脚注
EXTRA_NOTE = {
    'and-or-not': 'Not 用 Value（布尔值）',
}

# 只输出「返回」行、不出字段表的 Mutator。
# 这些是「键 → 值」映射型：字段名本身就是各任务/阶段/群系/次要目标的名字，
# 逐个罗列只会重复正文里已有的列表，读者真正需要知道的只有「返回什么」。
RETURN_ONLY = {
    'bybiome', 'byddstage', 'bydna', 'byescortphase', 'bymissiontype',
    'bysecondary', 'byrefineryphase', 'bysabophase', 'bysalvagephase',
}

# 简介重写（人工）：锚点 id → 新的中文简介
INTRO = {
    'accumulate': '从 Initial 指定的值开始累加 Value。如果 Value 是另一个 Mutator，'
                  '累计值会随它的结果变化。可以用 Min 和 Max 限制最终结果的范围。',
}
