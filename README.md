<p align="center">
  <img src="assets/logo.png" width="128" height="128" alt="PS5 AMPR LZ4 Icon" style="border-radius: 28px; box-shadow: 0 10px 30px rgba(0, 112, 209, 0.4);" />
</p>

<h1 align="center">PS5 AMPR LZ4 游戏压缩工具 (fnOS 飞牛版)</h1>

<p align="center">
  <b>专为飞牛私有云 (fnOS) 深度定制的 PlayStation 5 游戏资产高速压缩与部署应用套件</b>
</p>

<p align="center">
  <a href="https://github.com/foxhound1227/ps5pack_fnos/releases"><img src="https://img.shields.io/badge/Release-v1.2.6-0070d1?style=flat-square" alt="Version"></a>
  <a href="https://www.fnnas.com/"><img src="https://img.shields.io/badge/Platform-fnOS%20%7C%20Windows%2010%2F11-00d2ff?style=flat-square" alt="Platform"></a>
  <a href="https://github.com/Nazky/Lazy_AMPR"><img src="https://img.shields.io/badge/Engine-AMPR%20LZ4-10b981?style=flat-square" alt="AMPR LZ4"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-amber?style=flat-square" alt="License"></a>
</p>

---

## 🌟 项目简介

**PS5 AMPR LZ4 游戏压缩工具** 是一款多平台支持的高性能 PS5 游戏资产打包与压缩套件（原生支持**飞牛私有云 fnOS** 与 **Windows 10/11 本地免安装独立版**）。

工具基于社区先进的 **AMPR LZ4 规范** 与多线程调度流式架构，在保证 PS5 主机端秒级透明解压的同时，通常可为大型 PS5 游戏缩减 **40% ~ 60%** 的存储体积（例如实测 83.7 GiB 游戏可大幅压缩至 39.5 GiB，净省 44.1 GiB 宝贵 SSD 空间）。

同时提供现代化 PS5 质感 Web 控制台、原生文件夹选择器、单文件镜像免解包挂载压缩、**libSceAmpr 运行时全自动版本比对与智能替换升级**、**底层引擎智能透视**、**多 Profile 智能级联匹配**、实时吞吐大屏以及自适应微胶囊状态监控。

---

## ✨ 核心特性

- 💻 **多平台支持：Windows 本地独立免安装绿色版首发 (v1.2.6)**
  - **零 Python 依赖开箱即用**：完整内置 Python 运行时、官方 `lz4` 高性能 C 扩展加速模块与多进程调度内核，在本地 Windows 电脑解压即可满血利用 PC 高性能 CPU（Intel i7/i9 / AMD Ryzen）极速压缩；
  - **双击一键启动 + 自动唤起浏览器**：运行 `启动PS5压缩工具.bat` 自动启动本地后台服务，并在 0.8s 内自动调用默认浏览器打开 Web 控制大屏；
  - **Windows 系统原生文件夹选择器**：支持点击“浏览”呼出 Windows 经典文件夹选择对话框，告别浏览器安全限制，路径选择直观顺畅；
  - **全盘物理驱动器自由穿梭**：根目录视图自适应探测并呈现所有 Windows 本地磁盘（`本地磁盘 (C:)`、`本地磁盘 (D:)` 等）与移动硬盘。
- 🛡️ **libSceAmpr.sprx 运行时解压驱动版本比对与智能替换升级 (v1.2.6)**
  - **深度版本解析**：支持流式解析 SPRX 内部 Drakmor 签名版本号及语义化版本号（Semver）；
  - **智能替换升级**：若目标目录缺失驱动，全自动注入 Drakmor 官方最新版（v0.4.2.1）；若源盘残留早期不支持 LZ4 的旧版驱动（如 v0.3.x 或 224KB 早期版本），**自动执行覆盖替换升级**，彻底防止游戏在 PS5 开机封面（`pic0.png`）死锁；若驱动已是最新或更高，则予以安全保留；
  - **128MB 流式大作架构透视**：升级架构分析引擎为 128MB 流式扫描，秒级识别 200MB+ 大作（如卡普空 RE 引擎《鬼武者：剑之道-PPSA27836》）的 `libSceAmpr` 符号。
- ⚖️ **全量真实落盘体积精准对比与统计 (v1.2.5)**
  - **原始基准自适应识别**：当输入为 `.exfat`、`.img`、`.iso` 等单文件镜像时，直接读取该镜像的物理落盘文件大小作为基准；若输入为解包目录，则递归扫描全目录全量文件总大小；
  - **产物全量物理复核**：压缩完成、散文件直通复制与 `fakelib` 驱动注入完成后，递归统计输出目录全量文件落盘总字节数（涵盖 `.pak`、`ampr_assets.index`、`libSceAmpr.sprx`、`eboot.bin`、音视频 Loose 资产等）；
  - **端到端真实节省率**：彻底解决以往仅统计 `.pak` 内部资产而排除了数十 GB Loose 媒体文件或镜像头尾空间导致的体积认知偏差，使大屏监控、历史记录和总结日志展现绝对真实的磁盘节省效果。
- 🔄 **交互视觉打磨升级 (v1.2.4)**
  - 顶栏“检查更新”按钮全面摒弃各操作系统/浏览器字体渲染各异的方形 Emoji（`🔄`），升级为高保真原生圆形矢量 SVG 动画图标，旋转时完美绕圆心自转，彻底消除方形旋转边缘失真感。
- 🎼 **多阶梯自适应超兼容兜底配置升级 (v1.2.3)**
  - 吸收社区启发式内核精髓，将全局兜底配置 `generic_ps5.toml` 升级为多阶梯自适应架构：
    1. **音频低延迟 16 KiB 极小分块**：针对音效与语音资产采用 `16KiB` + `layout="random"` + `hot=true`，大幅降低 PS5 瞬时解压负载，消除音频卡顿爆音；
    2. **大资产 64 KiB 页面对齐分块**：契合 PS5 物理页面 Direct IO，提高缓存命中率；
    3. **PS5 运行时 8 线程并发**：充分释放 PS5 Zen 2 8核处理器性能，大幅加快关卡载入耗时；
    4. **无后缀媒体流容器全面防崩**：补全 `**/soundbank*`、`**/movie*`、`**/wem*` 等流式大包通配规则。
- 🎯 **多 Profile 智能级联匹配机制与社区精选库 (v1.2.2 新增)**

  - 内置整合开源社区成熟经过实机验证的精调配置库（`profiles/`）：
    - `astrobot.toml`（索尼第一方《宇宙机器人》实机 Trace 精炼规则）；
    - `insomniac.toml`（Insomniac 引擎专有规则：解决漫威蜘蛛侠全家桶开机闪退问题，安全压缩 `d/*` 资产）；
    - `unity.toml`（Unity 引擎专属规则：安全压缩 `StreamingAssets`，彻底保护 `global-metadata.dat` 与启动核心）；
    - `ufc6-PPSA23566.toml`（寒霜引擎 EA Sports UFC 6 专有分块规则）；
  - **4 级级联自适应匹配**：源目录自定义配置优先 ➔ 社区 Title ID 专属精调 ➔ 引擎特征布局匹配（Insomniac / Unity） ➔ 全引擎大一统母版兜底（`generic_ps5.toml`）；
  - 前端 UI 实时呈现选定的专属打包策略标签与提示，兼顾小白一键打包与高玩精调定制。
- 💉 **`libSceAmpr.sprx` 运行时全自动补全注入 (v1.2.1 核心突破)**
  - 内置 Drakmor 官方原生 `libSceAmpr.sprx` 用户态解压驱动 (`v0.4.2.1-test`)；
  - 自动检测并于散文件复制阶段自动向 `fakelib/` 目录注入解压动态库并赋予 `0755` 权限；
  - **彻底解决 95% 以上原始 Dump 游戏在 LZ4 压缩后因缺失解压钩子而卡在开机启动图 (`pic0.png`) 的死锁痛点**，真正实现即拷即玩。
- 🔍 **底层游戏引擎架构与 Title ID 智能透视 (v1.2.1 新增)**
  - 自动解析 `sce_sys/param.json`，秒级提取官方游戏名称与标准 Title ID（如 `PPSA02530`）；
  - 深度扫描 `eboot.bin` 二进制指令，智能识别是否为索尼第一方原生 AMPR、Capcom RE Engine、虚幻引擎 (Unreal) 或 Unity，并在前端面板呈现实时引擎诊断标签。
- 💿 **单文件磁盘镜像直接输入（免解压直接挂载）**
  - 全面支持直接选取 `.exfat`、`.img`、`.iso` 等单文件虚拟磁盘镜像；
  - 基于 Linux 内核原生 `loop` 机制在后台全自动只读挂载，**0 额外临时磁盘开销**，AMPR 引擎以磁盘原生总线速度直接流式读取压缩；
  - 任务完成、终止或异常中断时，在 `finally` 安全管线中**确定性卸载 (`umount`)**，杜绝文件系统锁死与内存泄露。
- 📂 **飞牛原生文件选择器 & 纯净 NAS 目录树**
  - 原生无缝集成飞牛 OS 前端 SDK，点击“浏览”直接呼出系统级“选择文件夹”对话框；
  - 备用浏览器重构为“纯净 NAS 视图”，彻底剔除 Linux 底层系统无权目录，仅展示存储空间卷（如 `存储空间 1`），清晰标亮并呈现 `💿` 镜像单文件。
- ⚡ **AMPR LZ4 4-Lane 高并发压缩引擎**
  - 内置 4-Lane 资产自动分流策略与 `workers` 多线程并发，充分释放 NAS 多核 CPU 与 NVMe/SATA 阵列性能；
  - 压缩等级支持 1~12 级平滑微调（推荐 Level 9，实现速率与压缩率的黄金平衡点）。
- 🛡️ **Loose 启动散文件自动补齐与双重校验**
  - 自动识别并保留 PS5 系统引导必需散文件（`eboot.bin`、`sce_sys/param.json`、`icon0.png` 等），确保产物直接拷贝至主机即可被引导启动；
  - 实时比对原盘文件与已打包分卷数据块的 SHA-256 / 哈希一致性，杜绝解压数据损坏。
- 📊 **现代化实时监控大屏 & 胶囊防撑爆排版**
  - 仪表盘实时呈现瞬时压缩速率（MiB/s）、空间节省率（%）、已节省体积与精确用时；
  - 单行原地刷新升级为**结构化微胶囊徽章（Status Badges）**，窄屏或浮动窗口下**自适应自动折行**，CSS 加装防爆锁，彻底杜绝撑破页面窗口；
  - 历史日志采用每 10% 里程碑智能打点，配备【自动换行 / 横向滚动】切换开关与一键清屏工具。
- 💾 **表单参数与选择路径双重持久化记忆**
  - 关闭应用窗口或刷新页面后，自动恢复上次填写的源目录、输出目录及多线程参数，无需每次重新配置。
- 🎨 **飞牛标准圆角高清微光图标**
  - 采用标准 23% 超椭圆 (Squircle) 连续曲率与全画幅微留白设计，89 阶超采样抗锯齿，与飞牛应用中心桌面图标尺寸 1:1 完美平齐。

---

## 🖼️ 界面预览

### 1. 实时监控与大屏看板
支持实时吞吐速率走字、空间节省率透视、自适应胶囊状态条与里程碑打点：
![监控大屏看板](assets/dashboard.png)

### 2. 真实压缩成效与历史记录
单款游戏即可节省超过 44 GB 空间（压缩率达 52.7%），历史记录自动持久化留痕：
![压缩历史与空间节省](assets/history_savings.png)

### 3. 飞牛原生“选择文件夹”对话框集成
无缝调用飞牛 OS 原生文件选择器，交互原生自然：
![飞牛原生文件选择器](assets/picker.png)

### 4. 飞牛桌面应用中心图标对齐
89 阶平滑抗锯齿与 PlayStation 微光深邃渐变，尺寸与系统卡片完美贴合：
![应用中心图标展示](assets/appcenter.png)

---

## 📦 安装与部署指南

### 方法一：直接安装发布包（推荐）
1. 在本仓库根目录或 [Releases 页面](https://github.com/foxhound1227/ps5pack_fnos/releases) 下载最新的 [`ps5pack.fpk`](ps5pack.fpk)；
2. 登录飞牛 OS (fnOS) 管理桌面，打开 **应用中心**；
3. 点击右上角 **手动安装** -> **选择文件**，上传 `ps5pack.fpk`；
4. 确认安装权限后点击完成，桌面即会出现 **PS5游戏压缩工具** 图标。

### 方法二：源码编译打包
如果您希望自行构建或二次开发，可在安装了官方 `fnpack` 打包工具的终端中执行：
```bash
# 克隆仓库
git clone https://github.com/foxhound1227/ps5pack_fnos.git
cd ps5pack_fnos

# 使用飞牛官方打包工具构建 .fpk
fnpack build --directory ps5pack
```
构建成功后，将在当前目录生成 `ps5pack.fpk`。

---

## 🚀 使用教程

```mermaid
flowchart LR
    A["输入源 (文件夹 / .exfat 镜像)"] --> B["智能叶子与引导特征嗅探"]
    B --> C["AMPR 索引构建"]
    C --> D["4-Lane 多线程并发压缩"]
    D --> E["Loose 散文件自动补齐"]
    E --> F["双重哈希一致性比对"]
    F --> G["产物完成 (直接拷入 PS5 玩耍)"]
```

### 第一步：选择游戏源路径
- **直接选择游戏解包目录**：例如 `/vol1/GAME/艾尔登法环-CUSA...`；
- **或直接选择虚拟磁盘单文件**：例如 `/vol2/PS5_ISOS/双影奇境.exfat` 或 `.img`，应用会自动进行只读挂载嗅探。

### 第二步：选择压缩输出目录
- 选择您的 NAS 共享文件夹或外接移动硬盘目标路径（例如 `/vol1/PS5_COMPRESSED/`）。

### 第三步：调整性能与压缩参数（可选）
| 参数项 | 说明 | 推荐设定 |
| :--- | :--- | :--- |
| **工作线程 (Workers)** | 压缩并行线程数 | 设为 NAS CPU 物理核心数（如 4~8） |
| **压缩级别 (Level)** | LZ4 压缩强度 (1~12) | **推荐 9**（兼顾极速吞吐与高压缩率） |
| **最大分卷 (Max Pack Size)** | 单个 `.pak` 容器最大尺寸 | `16GiB`（适应 exFAT 及各类外置文件系统） |
| **分流车道 (Lanes)** | 并行大文件打包通道数 | `4` |
| **自动 Loose 判定比例** | 若压缩节省率低于该阈值，文件自动转为 loose 不压缩 | `0.05` (5%) |
| **自动补齐 Loose** | 补齐 `eboot.bin`、`sce_sys` 等必要启动文件 | **开启**（PS5 正常开机必需） |
| **产物完整性校验** | 压缩后全量比对哈希与文件结构 | **开启**（确保资产万无一失） |

### 第四步：开始压缩
点击 **⚡ 开始压缩与打包**，大屏将实时展示进度、每 10% 关键里程碑打点与实时吞吐速率。

### 第五步：部署至 PlayStation 5
压缩完成后，输出目录内将包含：
- 若干个分卷压缩包：`re_chunk_000.pak`, `re_chunk_001.pak` 等；
- 索引文件与 loose 引导散文件：`ampr_index.bin`, `eboot.bin`, `sce_sys/` 等；
- 校验清单：`verify.log`（保留于目标目录，便于留存和随时校验数据完整性）。

> [!NOTE]
> **目录纯净保护机制**：压缩过程中的详细终端日志（`pack.log`）会自动存放于**目标目录的上级目录**中，不会混入游戏产物根目录，保证部署至 PS5 主机 `/app0` 时的纯净规范。

直接将该输出文件夹拷入移动固态硬盘插入 PS5，或通过 FTP/AMPR 工具部署至主机 `/app0`，即可享受高速免解压即点即玩！

---

## 🛠️ 目录结构规范

```text
ps5pack_fnos/
├── assets/                     # 截图与品牌资源
│   ├── logo.png                # 高清超采样应用图标
│   ├── dashboard.png           # 监控大屏看板
│   ├── history_savings.png     # 历史记录与节省体积
│   ├── picker.png              # 原生文件选择器
│   └── appcenter.png           # 桌面图标效果
├── ps5pack/                    # 飞牛 OS 规范应用包根目录
│   ├── manifest                # 应用元数据清单
│   ├── ICON.PNG                # 64x64 商店图标
│   ├── ICON_256.PNG            # 256x256 桌面高清图标
│   ├── app/
│   │   ├── server/             # Python 后端调度引擎
│   │   │   ├── compressor.py   # 核心调度、loop挂载、架构诊断与日志流
│   │   │   ├── main.py         # HTTP / 统一网关 Socket 服务
│   │   │   ├── engine/         # AMPR LZ4 打包核心
│   │   │   │   ├── fakelib/    # 官方通用 libSceAmpr.sprx 运行时解压库
│   │   │   │   └── profiles/   # 开源社区成熟配置库 (Astrobot, Insomniac, Unity, UFC6 等)
│   │   │   └── static/         # 前端 Web UI (HTML/CSS/JS)
│   │   └── ui/                 # 桌面卡片入口与启动配置
│   ├── cmd/                    # 生命周期契约脚本 (main, install, uninstall)
│   └── config/                 # 权限 (privilege) 与资源访问 (resource)
├── ps5pack.fpk                 # 编译完成的即用型飞牛安装包
├── .gitignore                  # Git 忽略规则
├── LICENSE                     # MIT 开源协议
└── README.md                   # 详细使用说明文档
```

---

## ❓ 常见问题 (FAQ)

<details>
<summary><b>Q1: 使用 .exfat / .img 单文件镜像时，系统会不会耗费几十分钟先解压一次？</b></summary>
<b>完全不会。</b> 本工具采用 Linux 原生 <code>mount -o loop,ro</code> 机制，直接将镜像挂载为虚拟只读文件系统，零额外磁盘空间消耗，AMPR 引擎像读取普通文件夹一样直接流式压缩打包。任务完成后会自动在后台安全卸载。
</details>

<details>
<summary><b>Q2: 为什么我的日志没有频繁滚屏刷屏？</b></summary>
为了避免超长任务时产生数万行无意义的滚屏杂音，本工具采用了<b>“单行微胶囊原地刷新 (In-Place Live Line)” + “每 10% 里程碑智能打点”</b>双模架构，既能秒级看到当前瞬时速率与倒计时，又保证历史日志整洁优雅。
</details>

<details>
<summary><b>Q3: 关闭应用窗口或浏览器标签页，压缩任务会被中断吗？</b></summary>
不会。压缩引擎在 NAS 后台作为独立系统守护进程持续稳定执行，重新打开桌面应用窗口即可自动恢复大屏监控并实时同步进度。
</details>

<details>
<summary><b>Q4: 压缩生成的日志文件保存在哪里？</b></summary>
为了避免日志污染 PS5 游戏目录：
1. <b>打包详细日志 (<code>pack.log</code>)</b>：自动存放在压缩目标目录的<b>上一级目录</b>中。
2. <b>数据校验日志 (<code>verify.log</code>)</b>：保留在<b>目标游戏目录</b>内，作为资产文件哈希校验的一致性存证凭据。
</details>

<details>
<summary><b>Q5: 为什么以前压缩的游戏在 PS5 启动画面 (pic0.png) 卡死，v1.2.1 是如何解决的？</b></summary>
PS5 系统底层内核无法原生直接透明读取 LZ4 压缩分卷包（<code>.pak</code>），必须依赖 <code>fakelib/libSceAmpr.sprx</code> 用户态动态解压模块拦截并处理文件读取。绝大多数原始游戏 Dump 本身并不自带此文件。<br>
在 v1.2.1 中，系统已内置 Drakmor 官方 <code>libSceAmpr.sprx</code> 核心运行时，在完成资产压缩与散文件拷贝后，<b>全自动无感补全注入该动态库并赋予可执行权限</b>，彻底免去手动拷贝配置的繁琐流程，保证所有支持 AMPR 的游戏启动开箱即玩！
</details>

<details>
<summary><b>Q6: 针对特殊引擎（如 Insomniac、Unity）或个别游戏（如宇宙机器人），为什么需要专用配置？</b></summary>
不同游戏引擎资产加载机制截然不同：例如 Insomniac 引擎（漫威蜘蛛侠、金刚狼等）若将 <code>dag</code>、<code>toc</code> 或音频包压缩，会导致进入游戏时指针异常闪退，仅允许压缩 <code>d/*</code> 目录；Unity 引擎对 <code>level*</code>、<code>sharedassets*</code> 及内存映射文件 <code>global-metadata.dat</code> 具有严苛的只读寻址依赖。因此 v1.2.2 深度整合了开源社区验证配置库并建立四级级联匹配机制，实现全自动智能防闪退调度。
</details>

---

## 🤝 鸣谢与致谢

- 核心打包引擎规范基于 [drakmor/ampr_emu](https://github.com/drakmor/ampr_emu) 与 [Nazky/Lazy_AMPR](https://github.com/Nazky/Lazy_AMPR)；
- 社区精选配置库参考自 [theghostonline/PS5-LZ4-Compression](https://github.com/theghostonline/PS5-LZ4-Compression) 开源贡献；
- 感谢 **飞牛私有云 (fnOS)** 团队提供的优秀 NAS 操作系统与微应用开放生态。

---

## 📄 开源许可证

本项目基于 [MIT License](LICENSE) 协议开源。欢迎提交 Issue 或 Pull Request！
