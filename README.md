# CD2 参考文档 · v2

《深岩银河》（Deep Rock Galactic）自定义难度 mod **Custom Difficulty 2（CD2）** 的中文参考站。

由原 MkDocs（Read the Docs 主题）站点重建为**零生成器、零框架的纯静态站**：不引任何 CDN / CSS 框架 / 字体文件 / JS 库，只用系统字体栈与原生 HTML/CSS/JS。

- 线上地址：<https://seasonsc.github.io/CD2-reference-cn/>
- 主仓库：<https://github.com/SeasonsC/CD2-reference-cn>
- 本仓库：`CD2-reference-cn-v2`（并行预览用，验收通过后替换主仓库 main）

---

## 仓库结构

```
.
├── docs/                  # ★ GitHub Pages 发布源（只有这个目录会上线）
│   ├── index.html         # 首页（路由器：三条入口 + 3 步预览 + 术语地图 + 我想做什么 + 更新日志）
│   ├── tutorial/          # 新手入门 · Getting Started（本站自写，承接完整 6 步）
│   ├── common-edits/      # 常见修改 · Cookbook（译自上游 Common Edits）
│   ├── tips/              # 为什么没生效 · Debug（分诊表 + 九步排查 + 七节深挖）
│   ├── natural-selection/ # 案例拆解 · Case Study（完整难度的机制组合）
│   ├── faq/  basics/  modules/  enemies/  direct/  wavespawners/
│   ├── projectiles/  mutators/  resources/
│   ├── 404.html           # 自足页（内联样式 + 旧路径智能跳转）
│   ├── search-index.json  # 内置搜索数据源（打开搜索时才加载）
│   ├── sitemap.xml  robots.txt  .nojekyll
│   └── assets/
│       ├── css/site.css   # 构建产物（由 src/site.css 去注释生成）
│       ├── js/site.js     # 构建产物（由 src/site.js 去注释生成）
│       ├── img/           # favicon.svg / logo.svg
│       └── media/         # WebP 图片 + GIF + Materials-1.pdf
│
├── src/                   # ★ 手写源码（带注释，不发布）
│   ├── site.css           # 全站唯一样式表（在此修改）
│   └── site.js            # 全站唯一脚本（在此修改）
│
├── tools/                 # 构建脚本（不发布）
│   ├── extract.py         # 内容提取：HTML → build/content/*.json（含人话搜索关键词 SEARCH_KW）
│   ├── build_media.py     # 图片转 WebP + 尺寸清单
│   ├── build_assets.py    # src/ → docs/assets/（去注释、压空行）
│   ├── render.py          # 渲染：JSON → docs/ 静态页
│   ├── md2page.py         # 《物竞天择-功能实作.md》→ 案例拆解页
│   ├── md2page_tutorial.py# 《新手入门.md》→ 新手入门页
│   ├── verify.py          # 自检 + 98 项回归清单（含跨页锚点检查）
│   └── build.ps1          # 一键构建（保持纯 ASCII）
│
├── build/                 # 中间产物（不发布）
│   ├── content/*.json     # 每页结构化内容
│   ├── nav.json  media.json  search-index.json
│   └── *_report.txt       # 提取/配对/标题规范化报告
│
└── _preview/              # 一次性预览页（不发布）
```

> **改样式/脚本请改 `src/`，不要改 `docs/assets/`**——后者每次构建都会被覆盖。

## 构建

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File tools\build.ps1
```

依次执行 `extract.py` → `build_media.py` → `build_assets.py` → `render.py` → `verify.py`，全部产物落在 `docs/`。

两个 Markdown 源需要**先单独运行**它们各自的转换脚本，再跑 `build.ps1`：

```powershell
python tools\md2page.py            # ..\物竞天择-功能实作.md → CD2-upstream-src\natural-selection\
python tools\md2page_tutorial.py   # ..\新手入门.md        → CD2-upstream-src\tutorial\
```

**依赖**：Python 3 + Pillow（仅构建期用于转 WebP）。运行期零依赖。
**内容源**：`../CD2-reference-cn`（旧 MkDocs 站，含后续人工修订）。

本地预览（`docs/` 即站点根）：

```powershell
python -m http.server 8767 --bind 127.0.0.1 --directory docs
```

## 部署

GitHub Pages → **Settings → Pages → Source = Deploy from a branch → `main` + `/docs`**。

站点使用**相对路径**，因此可以部署在仓库子路径（`/<repo>/`）下而无需改动；`canonical` / `og:url` / `sitemap.xml` 中的子路径由 `tools/render.py` 顶部的 `REPO_PATH` 常量控制。

## 页面结构约定

- 每页有且仅有一个 `<h1>`；`<html lang="zh-CN">`。
- 双语处理：正文成对段落「中文为主 + `<details class="orig">` 折叠英文」；无中文对应的英文段落原样保留。
- 表格单元格与图注中的中英并存内容**分行**显示（英文一行 + `.td-zh` 中文一行）。
- 顶部栏「中 / 中＋英」开关控制折叠条显隐（`localStorage`: `cd2-lang`）；主题三态（`localStorage`: `cd2-theme`）。
- 断点：`<1200px` 单栏 + 抽屉；`≥1200px` 左导航常驻两栏；`≥1360px` 三栏（加右侧本页目录）。

## Cookbook 准入规则（R13 起生效）

`常见修改 · Cookbook` 只收录**一个目标、一个最小方案**。新增条目必须**同时**满足六条：

| # | 条件 | 不满足的反例 |
|---|---|---|
| 1 | **单一目标**：读者能一句话说清「我要实现 X」 | 「一整套动态敌群系统」 |
| 2 | **已在当前 CD2 版本实际跑通** | 语法看着对、但没实测过；或按旧版本行为写的 |
| 3 | **最小独立示例**：不依赖案例专用 Vars / 隐含变量 / 未解释的前置配置 | 从案例里整段抄走、却没有上下文 |
| 4 | **新人能看懂**：做什么 → 改哪里 → 为什么 → 怎么验证 | 只给代码、不给验证方法 |
| 5 | **有 Reference 出口**：链到对应字段的完整定义 | 自成一体、不指向 Reference |
| 6 | **不重复 Reference**：只讲完成这个目标需要知道的部分 | 把字段表再抄一遍 |

**数量不是目标。** 目前 8 篇：前 2 篇译自上游 Common Edits，后 6 篇（补给成本 / 按玩家人数 /
地图硝石 / 矮人属性 / 敌人属性 / WaveSpawner）的字段与示例**取自本站 Reference**，
按用户决定先发布、并在页首如实标注「尚未在游戏内逐条实测」。

**来源规则（R15 起）**：新增配方只允许从**已有 Reference 字段表或上游示例**里取，
不允许自行编写未在站内文档中出现过的字段；也无法声称实测状态——标注写清楚即可。

## FAQ 锚点命名规则（R13 起生效）

- id 加在**英文问句**那条 `<li>` 上；`extract.py` 配对时会把它带到输出条目。
- 命名：`faq-` + 英文短横线语义名，例如 `faq-no-effect`、`faq-client-sync`、`faq-mutator-debug`。
- **不用**中文 id、不用位置编号（如 `faq-li-7`）、不用随标题变化而自动生成的 id。
- `verify.py` 的跨页锚点检查覆盖它们：Debug / 首页 / 新手页指向的 FAQ 锚点必须真实存在。

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

**英文原文**：<https://vonacht.github.io/cd2reference/>
