# CD2 参考文档 · 中文

《深岩银河》（Deep Rock Galactic）自定义难度模组 **Custom Difficulty 2（CD2）** 的中文参考手册。

**在线访问**：<https://seasonsc.github.io/CD2-reference-cn/>

---

## 关于本项目

本仓库收录 **CD2 Mod Reference** 的中文翻译。原参考文档主要由 **vonacht** 编写，与 **Brain** 共同制作，并有 carrot、spy、noskill 等多位作者的协作与贡献。

注意：本项目为**非官方**的中文翻译项目。

除了翻译，本站在原作者文档之外补充了面向中文作者的「写作提示与常见错误」一页。

**英文原文**：<https://vonacht.github.io/cd2reference/>

## 站点特点

| | |
|---|---|
| **零依赖** | 全站只有 **1 个 CSS + 1 个 JS**，无框架、无 CDN、无第三方请求 |
| **纯静态** | 任意静态托管都能跑，不需要服务端 |
| **中英对照** | 默认中文；顶栏可切换「中 / 中 + 英」，英文原文折叠在 `<details>` 中 |
| **本地搜索** | 内置 bigram 倒排索引（`search-index.json`），不依赖外部搜索服务 |
| **离线可用** | 无外部字体、无外部脚本、无统计代码 |

## 目录结构

仓库根目录**就是** GitHub Pages 的发布目录（Pages 源 = `main` + `/`）：

```
.
├── index.html          首页（引言 + 更新日志）
├── 404.html            404（含旧站路径重定向）
├── toc/                ★ 目录页（章节卡片网格 + 统计条）
├── basics/  faq/  modules/  enemies/  direct/  wavespawners/
├── projectiles/  mutators/  resources/  tips/     内容页（共 10 章）
├── assets/
│   ├── css/site.css    样式（由 src/site.css 构建）
│   ├── js/site.js      脚本（由 src/site.js 构建）
│   ├── img/            图标（由 src/img/ 拷贝）
│   └── media/          图片与 PDF
├── search-index.json   搜索索引
├── sitemap.xml  robots.txt  .nojekyll
│
├── src/                ★ 作者源：site.css / site.js / img/（构建后输出到 assets/）
└── tools/              ★ 构建脚本（见下）
```

> `src/` 与 `tools/` 是站点的**构建源**，会被 Pages 一并发布为静态文件，但不参与页面渲染。
>
> 章节卡片与统计条在**目录页**（`toc/`），首页只保留引言与更新日志。

## 本地预览

纯静态，任意 HTTP 服务即可：

```bash
python -m http.server 8000
# 打开 http://127.0.0.1:8000/
```

> 注意：站点大量使用相对路径，**必须经过 HTTP 服务访问**，直接双击 `index.html` 会因 `file://` 协议而链接失效。

## 重新构建

构建流程是「从上游 MkDocs 老站抽取内容 → 生成静态页」，需要 **Windows + PowerShell + Python 3**，并安装：

```bash
pip install lxml Pillow
```

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File tools\build.ps1
```

脚本依次执行：`extract.py`（抽取）→ `build_media.py`（转图）→ `build_assets.py`（压缩 CSS/JS、拷贝图标）→ `render.py`（生成页面）→ `verify.py`（**83 项**回归自检）。

### ⚠️ 已知限制

`tools/` 里的路径目前是**绝对路径**，指向作者的本地目录：

- `tools/extract.py` 顶部的 `SRC` —— 上游 MkDocs 老站的位置
- `tools/extract.py` 顶部的 `DEST` —— 构建输出位置
- `tools/build.ps1` 里的 `$PY` —— Python 解释器路径

要在别的机器上重建，需要先改这三处。上游老站本身不在本仓库内（历史上曾是，见 commit `4c14730` 及更早）。

## 许可与声明

本翻译**已获原作者授权**。

- **本项目仅提供翻译工作** —— 界面设计、排版结构与原始内容均归原作者所有
- 本项目为**非官方**中文翻译项目，与文档原作者、模组作者均无从属关系
- 由于个人水平有限，翻译中可能仍有不准确之处，欢迎各位指正
- 《深岩银河》及相关素材版权归 **Ghost Ship Games** 所有

## 致谢

| | |
|---|---|
| **vonacht** | 撰写了原参考文档的主要内容，并授权本项目进行翻译 |
| **Brain**（@TheBrain） | 开发了 **CD2 模组**，并撰写了原文档的部分内容 |
| **carrot**、**spy**、**noskill** 等 | 以及所有参与原 cd2-reference 的贡献者 |
| **Kugua** | 提供了翻译帮助 |

本翻译仅用于帮助更多玩家学习和理解 CD2 的难度编写。
