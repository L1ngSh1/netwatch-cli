# netwatch-cli 轻量化与解耦工程计划

日期：2026-10-16（Asia/Shanghai）

状态：2026-10-18 用户打回旧 P1。P0 提交 `2f6a465` 保留；P1 重修仅简化高级功能，基础功能与默认安装保持 P0 原样。P2 及以后未开始。

阶段记录：[P0 验收](2026-10-16-lightweight-p0-results.md)、[P1 重修](2026-10-18-lightweight-p1-results.md)。

最新硬约束：**基础功能原样保留，简化与减重只发生在高级功能。旧 P1 的安装矩阵和约 93.68 MiB 节省结论已被用户否决，不再作为本期验收目标。**

工作分支：`codex/architecture-audit`

基线提交：`33ca7b5b466cd9152954db235654ffa0efbc0eb9`

依据：[架构审计报告](/Users/y4n9/Workspace/Projects/My-github-projects/netwatch-cli/docs/audits/2026-10-15-architecture.md)。

## 1. 先定目标：减负，不做第二次大重构

项目仍然回答三个问题：**现在连在哪、流量走哪条路径、这条路径的网络表现怎样。**

首期交付不是“目录更漂亮”，而是：

1. 普通网络诊断、网页测速及默认安装步骤不变；高级功能不再给基础启动附加无关模块加载。
2. CLI 子模块使用明确依赖，不再反查主入口的运行时对象。
3. 关键词测速的服务器来源与执行后端一致。
4. 默认测试真正隔离外部副作用，原有用户流程可回归。

**推荐按三个里程碑、八个必做小补丁推进，另留一个可选清理补丁。每个补丁验收后再进入下一步。** 不以文件数、源码行数、模式数量或新增后端作为成果指标。

## 2. 首期默认决策

| 决策 | 推荐方案 | 原因与代价 |
| --- | --- | --- |
| 基础定位 | 保留主菜单 2 的原有浏览器定位、离线反向编码及依赖 | reverse-geocoder 是基础流程的实际消费者，P1 不移出基础依赖 |
| 高级精确定位 | 保留高级 13，确认运行后再导入精确行政区/道路编排 | 减少基础启动加载；不删除能力，不声称安装包因此减少几十 MiB |
| 浏览器测速 | 保留主菜单 4 和原默认安装中的 browser extra / Chromium 初始化 | 核心测速保持可用，不把少装核心依赖当作轻量化成果 |
| 关键词/运营商选服 | 维持现有菜单定义：Ookla 专用；缺官方 CLI 时提前提示 | 修复来源错配，不顺便扩展一套 Python 选服能力 |
| 通用测速 | 保留 Ookla / LibreSpeed / Python fallback | 已有明确用途，不因为“多后端”就判定为冗余 |
| 路由器增强 | 设备名同步保留在增强入口 | 核心仍是诊断，不演变成路由器管理平台 |
| 地理功能移出项目 | 首期暂缓，单独决定 | 去依赖、迁开发工具与删除用户功能是三种不同变更 |
| 工程形式 | 保留现有包布局，用普通函数和直接依赖 | 暂不引入插件框架、DI 容器、新服务层、数据库或新包管理器 |

基础/高级按实际消费者划分，而非按包名划分。README 默认安装继续包含 `.[browser]` 和 Chromium 初始化；`pyproject.toml` 及安装检查器与 P0 相同。高级功能仅做按需加载、分组展示和按操作显示解释，不删除功能或重编号。

### 保持不变的用户行为

- 主菜单 4 仍运行 speedtest.cn 浏览器自动化，失败后返回明确错误，不转入 Ookla。
- 主菜单 5 默认简洁，完成后再询问详细诊断；高级菜单 1 继续完整诊断。
- 基础网络信息、浏览器定位、反向编码及原有依赖保持不变；高级精确定位仍保留确认、取消、EOF / Ctrl+C 既有行为及配置格式。
- 保持 speedtest.cn 的网页自动化实现方式、后台运行和截图关闭；测速后端返回结构化结果。
- 不增加配置迁移；真实用户配置、浏览器数据、地理数据和已有虚拟环境保持原样。

冻结两处实现，使用 AST 对照加行为回归双重检查：

- [runner.run_best_speedtest](/Users/y4n9/Workspace/Projects/My-github-projects/netwatch-cli/netwatch/speedtest/runner.py#L33)
- [CLI show_auto_speedtest](/Users/y4n9/Workspace/Projects/My-github-projects/netwatch-cli/netwatch/cli_modules/speedtest.py#L102)

删除调用兼容包装时可更换外部绑定，但这两个函数体及其既有语义保持不变。若后续方案需要改变它们，先回到本计划重新讨论，不把变化藏进清理提交。

## 3. 已有证据与本轮复核

2026-10-16 已核对：原有 110 个跟踪文件与审计时哈希一致，审计报告哈希也一致。以下测试和体积数据来自 2026-10-15 的实际审计，今天未重复运行完整测试：

| 项目 | 基线 | 目标 |
| --- | --- | --- |
| 完整隔离套件 | 288 passed、2 failed；两次真实子进程尝试被阻断 | 修复隔离缺口；完整配置保留原有用例语义，外部副作用尝试为 0 |
| cli_override 调用 | 15：location 6、router 3、speedtest 6 | 按 15 → 9 → 6 → 0 收敛 |
| ConsoleProxy 反查入口 | 1 个实现 | 0；使用明确的共享 console |
| 关键词选服 | Python 提供列表，却调用缺失的 Ookla | 缺 Ookla 时提前结束，不列 fallback 列表、不执行测速 |
| 基础依赖 | reverse-geocoder 引入 NumPy / SciPy，且基础定位使用它 | 与 P0 保持一致；只减高级功能的无关启动加载 |
| 地理依赖体积 | 历史测量约 99.8 MiB | 不移除基础定位能力来换体积；高级独占资产另行逐项评审 |
| 边界检查 | 实际反查入口仍显示 ok_adapter | 人为违规样例失败；完成迁移后存量例外清零 |

80 处旧入口 monkeypatch 是迁移排查清单，不是“全部删到 0”的指标：主菜单自身的输入、输出和调度测试仍可合理替换主入口对象。

## 4. 目标依赖方向

```text
主菜单 / 各功能 CLI
        ↓ 输入转换、调用、展示
现有领域函数与调度器
        ↓
平台适配 / 外部后端 / 本地可选数据

测试 → 替换真实调用位置的依赖
各 CLI → 明确共享的 console
```

子模块没有反向访问主菜单的箭头。位置、测速、路由器按原有领域边界维护；同一目录里的所有函数也不必强行拆成类。

## 5. 实施顺序与每轮交付

| 补丁 | 做什么 | 依赖 | 完成后停在哪 |
| --- | --- | --- | --- |
| P0 | 建立可信测试基线 | 计划确认 | 只交付隔离修复和行为保护，先评审 |
| P1（重修） | 仅简化高级菜单与高级精确定位启动加载 | P0 | 基础一致性、全部高级入口及冷启动探针通过后评审 |
| P2 | 修复关键词选服契约 | P0，建议接 P1 | 仅修复已知错配，不扩充后端能力 |
| P3a | 移除 location 的 6 处兼容桥 | P1、P2 | 观察一次小模块迁移成本 |
| P3b | 移除 router 的 3 处兼容桥 | P3a | 路由器与 LAN 回归通过 |
| P3c | 移除 speedtest 的 6 处兼容桥 | P3b | 冻结函数不变，测速回归通过 |
| P4 | 移除 ConsoleProxy、清理无消费者再导出、启用严格边界检查 | P3c | 核心解耦完成 |
| P5（可选） | 迁出地理开发 helper 与构建输入 | P4，单独确认 | 不动用户可见定位功能 |
| P6 | 文档收口、安装包与平台验收 | P4；若做 P5 则在其后 | 输出收尾报告；发布另行决定 |

### M1：可信基线、基础能力保护、高级功能减负与明确缺陷修复（P0–P2）

#### P0 — 测试先能保护我们

**目标文件**：[路由测试](/Users/y4n9/Workspace/Projects/My-github-projects/netwatch-cli/tests/network/test_router.py)、[地理压力测试](/Users/y4n9/Workspace/Projects/My-github-projects/netwatch-cli/tests/location/test_boundary_stress.py)，以及相关菜单测试。拟新增 `/Users/y4n9/Workspace/Projects/My-github-projects/netwatch-cli/tests/conftest.py` 和针对 guard 自身的负向测试。

实施：

1. 路由测试直接 mock 当前实际调用的 LAN 网关依赖，不再意外读取真实系统路由。
2. 地理脚本已有 `main() -> int`；在进程内导入、替换 argv、捕获 stderr 并断言返回 1，保留原来的错误语义，不启动子进程。
3. 从本地审计驱动提炼可清理的 pytest guard，阻断未 mock 的外部 HTTP、DNS、socket、子进程和真实浏览器调用。只为现有定位回调测试显式允许 localhost，不给整个网络层放行。
4. guard 记录尝试，确保被业务代码捕获的异常也会使对应测试失败；增加“允许 mock、阻断真实尝试、恢复状态”的回归。处理线程内调用，避免测试顺序决定结果。
5. 固定主菜单 4、主菜单 5、高级菜单 1、取消和缺依赖行为。关键词缺陷用本地探针继续复现；期望行为回归与 P2 修复一起合入，保持提交可通过。

**验收**：当前全依赖环境原有 290 个用例的语义保留；加入新保护用例后全部通过；未 mock 的外部调用为 0。不得用排除旧用例、宽泛 skip 或长期 xfail 达成绿色。临时 HOME/config 路径只使用合成数据，测试不依赖用户已有配置。

**回滚**：独立回退测试补丁，运行时代码保持不变。P0 是第一轮实施的唯一内容，完成后停下复核。

#### P1（重修）— 基础功能原样保留，只简化高级功能

旧 P1 因把默认安装改成缺少网页测速、并移出基础定位依赖而退回。其测试绿色只说明旧测试目标通过，不代表产品验收通过。旧补丁和原始日志已备份至本地 `.netwatch/p1-rework-2026-10-18/` 与原证据目录，未提交旧 P1。

**只改两处高级实现**：

1. `netwatch.cli_modules.location.run_precise_location_report()` 在高级 13 确认执行时才导入原领域编排。保留函数参数、结构化结果、兼容桥、数据及算法；取消时不导入、不启动浏览器。
2. `build_advanced_menu()` 只增加操作分组；`show_advanced_menu()` 把测速专用解释移到实际选择高级 1 后显示。保留全部 13 个动作、原选项编号、返回项 14 与完整通用诊断。

**明确不改**：README 默认 `.[browser]` / Chromium 安装；依赖声明；原安装检查脚本；主菜单、基础本机信息及定位；测速执行与 fallback；用户配置、原 `.venv`、地理数据；冻结函数。

**验收**：
- 与 P0 对照默认安装、依赖和基础文件哈希；主菜单/基础定位函数体通过 AST 对照及行为回归。
- 主菜单 4/5 与高级 1 原有回归保留，全部高级动作的编号和分派均有测试；配置操作不再反复显示测速免责声明，高级 1 解释仍完整。
- 独立冷进程探针记录导入模块集合；启动与默认基础信息不加载精确地理编排链，真正执行高级功能后再加载；所有外部行为 mock。
- 原 323 个 P0 nodeid 全数保留，无新增 skip/xfail；完整套件副作用尝试为 0。
- 不把延迟加载说成安装依赖体积减少，也不承诺未测的耗时/内存收益。

**回滚**：保留被退回补丁的备份；重修补丁独立打包，原文件哈希留存，在独立副本回退到 P0 并重跑 323 个测试。当前工作副本保留重修改动。

#### P2 — 解决“列得出、测不了”的后端错配

**目标文件**：[runner](/Users/y4n9/Workspace/Projects/My-github-projects/netwatch-cli/netwatch/speedtest/runner.py)、[测速 CLI](/Users/y4n9/Workspace/Projects/My-github-projects/netwatch-cli/netwatch/cli_modules/speedtest.py)、[测速测试](/Users/y4n9/Workspace/Projects/My-github-projects/netwatch-cli/tests/speedtest/test_speedtest_backends.py)。

实施：

- 给关键词/运营商选服一个明确的 Ookla 列表查询入口，后端可用性判断集中在领域侧。
- 缺少官方 Ookla 时直接提示安装，或让用户自行选择高级菜单 1；不调用 Python 列表，不自动跳转测速。
- 关键词手动选择、auto 前三个候选、运营商预设共用这条明确契约；每条路径测试均断言调用次数与后端身份。
- 通用 `list_speedtest_servers()` 的既有 fallback 行为及“指定 server id”现有流程保留。只修这条错配，不全局禁用 Python 列表。

**验收**：覆盖仅 Python、仅 Ookla、两者都有、都没有、空列表、非法选择、取消、候选失败与成功。缺 Ookla 时测速调用次数为 0；有 Ookla 时列表与执行都属于 Ookla。两处冻结函数通过 AST 和行为检查。

**回滚**：领域入口、CLI 接线与新回归同一补丁回退；其他后端流程不受影响。

### M2：把隐式兼容关系真正拆掉（P3a–P4）

#### P3a / P3b / P3c — 一次只迁一个模块

**目标文件**：[location CLI](/Users/y4n9/Workspace/Projects/My-github-projects/netwatch-cli/netwatch/cli_modules/location.py)、[router CLI](/Users/y4n9/Workspace/Projects/My-github-projects/netwatch-cli/netwatch/cli_modules/router.py)、[speedtest CLI](/Users/y4n9/Workspace/Projects/My-github-projects/netwatch-cli/netwatch/cli_modules/speedtest.py)，分别搭配所在领域及消费者的测试。

每次按同一顺序执行：先列出该模块实际消费者和旧 monkeypatch → 测试改为替换消费模块中的绑定 → 改为直接依赖 → 移除该模块的 `cli_override` 调用 → 跑相关和完整测试。

- P3a：6 个 location 包装，覆盖网络信息、定位成功/失败/缺依赖、详细信息展开与取消。
- P3b：3 个 router 包装，覆盖网关选择、后台地址、设备同步及 LAN 入口消费者。
- P3c：6 处 speedtest 反查，保留状态展示、详情切换和原有调用参数；旧测试打印回调的特殊兼容也一并迁移。
- 暂留仍有实际消费者的主入口导出与共享 ConsoleProxy 到 P4，不在中间阶段宣布“已彻底解耦”。

**验收**：调用数依次变成 9、6、0；每个新迁移模块的行为不受替换主入口同名业务函数影响；真实调用位置的 mock 则生效。除了正常入口调度测试，业务测试不再要求通过主入口才能运行。

**回滚**：三个模块各自一个补丁、各自回退；共享依赖留到最后，避免回退一处牵动整仓。

#### P4 — 共享 console 与严格边界检查收口

**目标文件**：[common](/Users/y4n9/Workspace/Projects/My-github-projects/netwatch-cli/netwatch/cli_modules/common.py)、[主入口](/Users/y4n9/Workspace/Projects/My-github-projects/netwatch-cli/netwatch/cli.py)、[边界检查器](/Users/y4n9/Workspace/Projects/My-github-projects/netwatch-cli/scripts/dev/check_cli_boundaries.py)、实际 console 消费者及测试。

实施：

- 使用普通共享 Console；测试替换消费模块的 console 或方法，移除反查 `netwatch.cli` 的 ConsoleProxy 和已无消费者的 cli_override。
- 搜索仓内代码、测试、脚本消费者后，再删除纯兼容再导出；保留真实菜单调度符号。
- 边界检查覆盖领域包反向导入 CLI、CLI 子模块反查主入口，包含绝对/相对 import 和已知动态查找形式。
- 先用人为违规 fixture 证明检查会失败，再启用非零退出。迁移期间的存量清单只缩不增；P4 完成时清零。
- 保留大文件提示作为观察项；不为了低于 900 行强拆文件。静态检查是回归约束，不宣传为完整架构证明。

**验收**：cli_override 调用 0、ConsoleProxy 0、存量反查例外 0；合法 fixture 成功、违规 fixture 非零退出；所有入口调用与模块内业务在相同 mock 条件下保持行为一致。冻结函数及配置格式不变。

**回滚**：console 接线、测试适配和严格检查同一独立补丁回退，保留已完成的 P3 模块直接依赖。

### M3：可选清理与交付验收（P5–P6）

#### P5（可选）— 只迁开发资产，不删除定位能力

候选为 [boundary_tools](/Users/y4n9/Workspace/Projects/My-github-projects/netwatch-cli/netwatch/location/admin/boundary_tools.py)、[boundary_stress](/Users/y4n9/Workspace/Projects/My-github-projects/netwatch-cli/netwatch/location/admin/boundary_stress.py) 和仅供构建使用的行政区原始输入。优先利用现有 [scripts/geo](/Users/y4n9/Workspace/Projects/My-github-projects/netwatch-cli/scripts/geo) 结构，先复核消费者，再决定具体落点。

迁移时同步改脚本、测试和数据引用；保留运行时需要的中心点 CSV、sample 数据与定位入口。用固定数据的结果等价测试、文件哈希和构建后的 wheel 清单验收。只看目录变小不算完成。

这一步单独确认；不承诺把全部地理实现移出项目。若收益仅是视觉整洁，就跳过 P5，并在收尾报告中说明暂留项。回滚是原样迁回，避免留一层永久转发模块。

#### P6 — 文档与安装包收口

维护 [README](/Users/y4n9/Workspace/Projects/My-github-projects/netwatch-cli/README.md)、[文档索引](/Users/y4n9/Workspace/Projects/My-github-projects/netwatch-cli/docs/README.md) 和现有 handoff：只指定一份当前状态来源，其他交接页指向它并标历史内容。旧审计保留日期，避免改写历史结论。

从干净构建输入生成 wheel，在临时环境安装并验证入口、依赖 metadata、包内数据与模块。必要回归进入 Git 跟踪测试，小型验收指标进入文档；详细日志保留本地，验收以可随仓库复现的测试为准，而非仅依赖被 ignore 的审计脚本。

输出“变更、命令、结果、未验证项、回退方式”五项收尾记录。版本号、提交合并、远端推送、发布和旧环境清理分别处理，不捆绑为自动动作。

## 6. 验收矩阵与复验方式

### 安装与基础功能保护（按 2026-10-18 修订）

| 组合 | 用途 | 约束 |
| --- | --- | --- |
| 原推荐默认安装：先基础，再 `.[browser]` 与 Chromium 初始化 | 日常本机信息、LAN、测速网和代理测速 | 安装步骤和依赖不因 P1 改变 |
| 原基础包单独安装 | 显式选择不安装浏览器测速的人 | 历史存在的选项，不把它改成默认推荐；仍保留基础定位依赖 |
| `.[geo]` | 高级精确边界/道路实验 | 保留原可选能力及数据，不另造隐式下载 |
| `.[all]` | 完整可选能力与回归 | 保留原有正向用例语义；浏览器和公网调用全部 mock |

P1 重修只比较安装/依赖与 P0 的一致性，不再执行“基础包必须没有地理链/Playwright”的旧验收标准。安装包体积和平台矩阵若在 P6 继续评估，必须在相同用户能力下比较，不能把缺功能当作减重。

### 平台与 Python

- macOS：当前 Python 3.14 的全依赖回归。
- Linux：Python 3.10 的基础环境、Python 3.14 的全依赖环境。
- Windows：Python 3.14 的全依赖 mock 回归；这不等于真实 Windows 网络功能已验证。
- 后续体积比较固定相同平台/Python/依赖版本和相同用户能力；P1 重修不承诺安装体积变化。
- 首期复验可用脚本；流程稳定后再接到现有托管 CI。建立 CI 系统本身不是独立扩展项目。

源码、wheel 压缩体积、已安装文件体积分别记录；比较环境锁定相同 Python、架构和公共依赖版本。测量新增依赖闭包与文件大小，不用整个虚拟环境的 `du` 单值代表产品体积。

### 每个实施补丁的基础命令

以下是 P0 完成后的常规命令；P0 前沿用审计驱动阻断副作用。命令本身不代表已完成上述矩阵。

```bash
cd /Users/y4n9/Workspace/Projects/My-github-projects/netwatch-cli
.venv/bin/python -m compileall -q netwatch
.venv/bin/python -m pytest -q
.venv/bin/python scripts/dev/check_cli_boundaries.py
git diff --check
```

P4 前边界检查仍主要用于观察，P4 后才以严格退出状态验收。原安装脚本保持不变，包含显式运行脚本时的浏览器启动检查，不纳入默认自动测试。

## 7. 提交、回退与停止规则

1. 审计与计划基线已在 `8792bcd` 固化，P0 已在 `2f6a465` 提交；重修先备份并撤回旧 P1，再保留基础基线与新补丁。
2. 一个补丁只解决一个验收目标。若出现无关领域修改，拆开而不是顺手重构。
3. 记录 patch 对应提交、固定测试输入、实际输出及改动前后指标。代码和对应测试/文档一起提交。
4. 对已提交补丁，在一次性副本上演练 revert，再重跑同一组验证；生产工作副本不执行破坏性 reset。多补丁有依赖时逆序回退，或连同消费者一起处理。
5. 包声明、安装检查和说明作为同一回退单位；不把用户环境卸载、数据删除混进回退脚本。
6. 任一验收失败就停在当前补丁修复；用例未覆盖、平台未跑或安装组合未测时明确记录，不自动降级验收标准。

### 首期完成定义

- P0–P4 与 P6 达标；P5 做或不做都有明确记录。
- 基础功能与默认安装能力不变；高级专属实现按需加载、按操作显示解释。
- 反查入口消失，关键词后端契约一致，已知两处隔离缺口关闭。
- 默认测试隔离外部副作用，菜单 4 / 5 / 高级 1 与冻结实现受回归保护。
- 文档、实际依赖和安装检查一致；输出安装矩阵与平台实测记录。

达到这些条件就停止本轮整理。完整地理功能拆成独立项目、菜单删减和真实跨平台网络验证作为后续产品决定，保持未完成状态透明。

## 8. 第一轮执行任务卡

确认计划后，第一轮只执行 P0。以下任务卡可直接复用：

```text
在当前 codex/architecture-audit 分支按轻量化计划执行 P0。
先核对工作区并保留审计、计划及用户现有修改。
只修路由测试的真实网关调用、把地理脚本子进程测试改为进程内等价验证，
并建立默认测试外部副作用 guard 和主菜单关键行为保护。
保留原有用例语义；所有测速、浏览器及外部命令均 mock。
本轮不调整依赖、不迁移 CLI 包装、不改后端策略、不删除功能。
完成后给出改动文件、验证命令、完整结果和回退证据，停在 P0 验收点。
```

2026-10-18 用户已纠正 P1 范围：基础能力原样保留，仅简化高级功能；此前将基础定位依赖改为 geo 按需的取舍已撤回。P2 的 Ookla 专用契约与 P5 的实际迁移仍分别处理。
