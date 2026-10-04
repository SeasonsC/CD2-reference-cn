# -*- coding: utf-8 -*-
"""静态资源处理：图片转 WebP（quality=85）、拷贝 PDF/GIF，输出尺寸清单。"""
import os, io, json
from PIL import Image

SRC = r'E:\learn\github\dsh\CD2\CD2-reference-cn'
ROOT = r'E:\learn\github\dsh\CD2\CD2-reference-cn-v2'
SITE = os.path.join(ROOT, 'docs')          # R2 §6.1：发布源
MEDIA = os.path.join(SITE, 'assets', 'media')
IMG = os.path.join(SITE, 'assets', 'img')

# (源文件, 输出名, 是否转 WebP)
ITEMS = [
    ('pictures/cd2-modhub.png', 'cd2-modhub.webp', True),
    ('pictures/countdown-mutator.png', 'countdown-mutator.webp', True),
    ('pictures/orange-septic.png', 'orange-septic.webp', True),
    ('pictures/ice-spreader.gif', 'ice-spreader.gif', False),
    ('media/Materials-1.pdf', 'Materials-1.pdf', False),
]


def main():
    os.makedirs(MEDIA, exist_ok=True)
    os.makedirs(IMG, exist_ok=True)
    manifest, rows = {}, []
    for rel, out, webp in ITEMS:
        sp = os.path.join(SRC, rel.replace('/', os.sep))
        dp = os.path.join(MEDIA, out)
        if not os.path.exists(sp):
            rows.append((out, 'MISSING', '', ''))
            continue
        before = os.path.getsize(sp)
        if webp:
            im = Image.open(sp)
            w, h = im.size
            if im.mode in ('RGBA', 'LA', 'P'):
                im = im.convert('RGBA')
            else:
                im = im.convert('RGB')
            im.save(dp, 'WEBP', quality=85, method=6)
            manifest['/assets/media/' + out] = {'w': w, 'h': h}
        else:
            io.open(sp, 'rb') if False else None
            with open(sp, 'rb') as f:
                data = f.read()
            with open(dp, 'wb') as f:
                f.write(data)
            w = h = None
            if out.endswith('.gif'):
                im = Image.open(sp)
                w, h = im.size
                manifest['/assets/media/' + out] = {'w': w, 'h': h}
        after = os.path.getsize(dp)
        rows.append((out, f'{before:,}', f'{after:,}',
                     f'-{100 - after * 100 // before}%' if before else ''))
    for a, b, c, d in rows:
        print(f'{a:26s} {b:>10s} → {c:>10s}  {d}')
    io.open(os.path.join(ROOT, 'build', 'media.json'), 'w', encoding='utf-8').write(
        json.dumps(manifest, ensure_ascii=False, indent=1))
    total_before = sum(os.path.getsize(os.path.join(SRC, i[0].replace('/', os.sep)))
                       for i in ITEMS if os.path.exists(os.path.join(SRC, i[0].replace('/', os.sep))))
    total_after = sum(os.path.getsize(os.path.join(MEDIA, i[1])) for i in ITEMS
                      if os.path.exists(os.path.join(MEDIA, i[1])))
    print(f'合计 {total_before:,} → {total_after:,} 字节')


main()
