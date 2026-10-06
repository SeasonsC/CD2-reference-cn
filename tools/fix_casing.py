# -*- coding: utf-8 -*-
"""CD2 JSON 名字规范化（大小写 / 拼写）——只改**引号内的字符串**，不动结构、缩进、注释与空行。

用法:
  python tools/fix_casing.py <输入.json> <输出.json> [--dry]
  python tools/fix_casing.py <输入.md>  <输出.md>  [--slices]   # 同样规则，用于文档里的逐字切片

安全保证（脚本自己会验）:
  1) 输出仍能用 json.load(strict=False) 解析（.md 模式跳过此项）
  2) 把同一张映射表递归作用到「原结构」上，结果必须与「新结构」**完全相等**
     → 证明文本层面只发生了预期的改名，没有任何其它改动
  3) 逐条打印命中位置（行号 + 上下文），便于人工过目
"""
import io, json, os, re, sys

# ── 规范名映射 ────────────────────────────────────────────────
# mode: 'exact' = 整个引号内字符串必须完全等于 old 才替换
#       'sub'   = 引号内字符串里出现的 old 子串都替换（用于改名单位 ID 的词根）
RULES = [
    # ── 大小写：原语名 / 字段名 ─────────────────────────────
    ('Iffloat',          'IfFloat',          'exact'),
    ('BymissionType',    'ByMissionType',    'exact'),
    ('TriggerOnchange',  'TriggerOnChange',  'exact'),
    ('SendOnchange',     'SendOnChange',     'exact'),
    ('MUtate',           'Mutate',           'exact'),
    ('Displayname',      'DisplayName',      'exact'),
    ('Riseonly',         'RiseOnly',         'exact'),
    ('initial',          'Initial',          'exact'),
    ('initialRate',      'InitialRate',      'exact'),
    ('interval',         'Interval',         'exact'),
    ('float',            'Float',            'exact'),
    ('in',               'In',               'exact'),
    ('IN',               'In',               'exact'),
    ('weight',           'Weight',           'exact'),
    ('add',              'Add',              'exact'),
    ('clear',            'Clear',            'exact'),
    ('remove',           'Remove',           'exact'),
    ('if',               'If',               'exact'),
    ('IF',               'If',               'exact'),
    ('floor',            'Floor',            'exact'),
    ('join',             'Join',             'exact'),
    ('Bytime',           'ByTime',           'exact'),
    ('int2String',       'Int2String',       'exact'),
    ('CanBeUsedinEncounters',     'CanBeUsedInEncounters',     'exact'),
    ('Isbossfight',               'IsBossFight',               'exact'),
    ('internalDamageMultiplier',  'InternalDamageMultiplier',  'exact'),
    ('WarMingRate',               'WarmingRate',               'exact'),
    ('EnemyWaveinterval',         'EnemyWaveInterval',         'exact'),
    ('EnemyNormalWaveinterval',   'EnemyNormalWaveInterval',   'exact'),
    ('PlayerIlluMination',        'PlayerIllumination',        'exact'),
    ('BitesPersecond',            'BitesPerSecond',            'exact'),
    ('Timedilation',              'TimeDilation',              'exact'),
    ('Flatdamage',                'FlatDamage',                'exact'),
    # Direct 底层属性路径（UE4 反射名，前缀大写）
    ('int:NumClusterBombs',             'Int:NumClusterBombs',             'exact'),
    ('int:NumShootersKilledToOpen',     'Int:NumShootersKilledToOpen',     'exact'),
    ('int:NumPhaseBombs',               'Int:NumPhaseBombs',               'exact'),
    ('int:EnemyBuffer.MaxBuffedTargets', 'Int:EnemyBuffer.MaxBuffedTargets', 'exact'),
    ('Float:MaxinGroundTime',           'Float:MaxInGroundTime',           'exact'),
    ('Float:MininGroundTime',           'Float:MinInGroundTime',           'exact'),
    # ── 值 / 敌人 ID ───────────────────────────────────────
    ('ED_YEs',                   'ED_Yes',                   'exact'),
    ('ED_TerMinator',            'ED_Terminator',            'exact'),
    ('ED_infectedMule',          'ED_InfectedMule',          'exact'),
    ('ED_Barrageinfector',       'ED_BarrageInfector',       'exact'),
    ('ED_Spider_tank_Boss',      'ED_Spider_Tank_Boss',      'exact'),
    ('WRN_Rockinfestation',      'WRN_RockInfestation',      'exact'),
    ('Prosepctor',               'Prospector',               'sub'),
    ('Enhace',                   'Enhance',                  'sub'),
    ('ED_Spider_Tank_Boss_WeaK', 'ED_Spider_Tank_Boss_Weak', 'exact'),
    ('ED_Glyphid_Time_praetorian', 'ED_Glyphid_Time_Praetorian', 'exact'),
]


def build_map():
    exact = {o: n for o, n, m in RULES if m == 'exact'}
    subs = [(o, n) for o, n, m in RULES if m == 'sub']
    return exact, subs


EXACT, SUBS = build_map()


def rewrite_string(s):
    """引号内的字符串 → 改名后的字符串。"""
    if s in EXACT:
        return EXACT[s]
    for o, n in SUBS:
        if o in s:
            s = s.replace(o, n)
    return s


def scan_strings(text):
    """返回 [(start, end, content)]，content 不含两侧引号；正确处理 \\" 与 \\\\。"""
    out, i, n = [], 0, len(text)
    while i < n:
        if text[i] == '"':
            j = i + 1
            while j < n:
                if text[j] == '\\':
                    j += 2
                    continue
                if text[j] == '"':
                    break
                j += 1
            out.append((i + 1, j, text[i + 1:j]))
            i = j + 1
        else:
            i += 1
    return out


def apply(text):
    """按引号内字符串做替换，返回 (新文本, 命中列表)。"""
    hits = []
    spans = scan_strings(text)
    for a, b, content in reversed(spans):          # 从后往前改，位置不受影响
        new = rewrite_string(content)
        if new != content:
            line = text.count('\n', 0, a) + 1
            hits.append((line, content, new))
            text = text[:a] + new + text[b:]
    return text, list(reversed(hits))


def rename_struct(obj):
    """把同一张映射表作用到已解析的结构上（用于等价性验证）。"""
    if isinstance(obj, dict):
        return {rewrite_string(k): rename_struct(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [rename_struct(x) for x in obj]
    if isinstance(obj, str):
        return rewrite_string(obj)
    return obj


def canon(obj):
    return json.dumps(obj, sort_keys=True, ensure_ascii=False)


def main():
    dry = '--dry' in sys.argv
    is_md = '--slices' in sys.argv
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    if len(args) != 2:
        print(__doc__)
        return 2
    src, dst = args
    raw = io.open(src, encoding='utf-8', newline='').read()
    new, hits = apply(raw)

    print(f'源：{src}')
    print(f'  引号内字符串 {len(scan_strings(raw)):,} 个 ｜ 命中改名 {len(hits):,} 处')
    from collections import Counter
    c = Counter((o, n) for _, o, n in hits)
    for (o, n), k in sorted(c.items(), key=lambda x: -x[1]):
        print(f'    {o!r:26} → {n!r:22} × {k}')

    # ── 验证 1：JSON 仍可解析 ──────────────────────────────
    if not is_md:
        orig_obj = json.loads(raw, strict=False)
        new_obj = json.loads(new, strict=False)
        # ── 验证 2：只改了名字 ────────────────────────────
        a, b = canon(rename_struct(orig_obj)), canon(new_obj)
        if a != b:
            print('  ❌ 结构等价性校验失败：除改名外还有别的差异！')
            for i, (x, y) in enumerate(zip(a, b)):
                if x != y:
                    print(f'     首个差异 @{i}: …{a[max(0,i-70):i+70]}')
                    break
            return 1
        print('  ✔ json.load(strict=False) 可解析')
        print('  ✔ 结构等价：把同一映射作用于原结构后与新结构逐字节相同（只改了名字）')

    # ── 碰撞检查：新名字是不是原文件里已经有了（= 会把两个名字并成一个） ──
    allstr = Counter(c for _, _, c in scan_strings(raw))
    coll = [(o, n, allstr[o], allstr[n]) for o, n, _ in RULES
            if o != n and allstr[o] and allstr[n]]
    if coll:
        print('\n  ⚠ 碰撞检查：以下规则的「新名字」在原文件里**已经存在**')
        print('     （两者本就是同一个东西 → 合并正确；若是两个不同的东西 → 会撞车，必须人工判断）')
        for o, n, a, b in coll:
            print(f'      {o!r:32} ×{a:<4} → {n!r:32} 已存在 ×{b}')
    else:
        print('\n  ✔ 碰撞检查：没有任何「新名字」在原文件里已存在')

    # ── 命中明细 ──────────────────────────────────────────
    lines = raw.split('\n')
    for ln, o, n in hits[:400]:
        print(f'    {ln:>6} : {o}  →  {n}')
    if len(hits) > 400:
        print(f'    … 其余 {len(hits) - 400} 处略')

    if dry:
        print('\n(--dry：未写文件)')
        return 0
    io.open(dst, 'w', encoding='utf-8', newline='').write(new)
    print(f'\n✔ 写出 {dst}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
