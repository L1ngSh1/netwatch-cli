# netwatch-cli：耦合与轻量化审计

日期：2026-10-15（Asia/Shanghai）

分支：`codex/architecture-audit`

基线提交：`33ca7b5b466cd9152954db235654ffa0efbc0eb9`

本轮变更：新增这份审计报告；运行时代码、依赖配置、测试文件和旧报告保持原样。

## 结论先说

**你的感觉有依据。问题不是项目已经“大到要重写”，而是产品功能向地理信息工具扩张，安装依赖偏重，以及拆文件后仍保留了隐式的反向依赖。**

最值得处理的三件事：

1. 把地理定位依赖从基础安装中移出；这比删几个 Python 文件更有效。
2. 逐模块移除 CLI 子模块反查主入口的兼容桥，让测试直接对准真正的调用位置。
3. 收回 CLI 中散落的后端选择策略；已有一个可复现的“能列服务器、却执行错后端”的问题。

保留平台适配、结构化测速结果和多后端执行层。当前不需要新插件框架、依赖注入容器、统一 service 层或全仓搬目录。**先减少职责，再决定是否拆文件。**

## 1. 测量口径：源码、安装体积、维护负担分开看

数据来自当前 Git 跟踪文件、Python AST、一次入口导入，以及本机虚拟环境的 distribution RECORD；不是下载体积、性能基准或覆盖率报告。

| 项目 | 实测 | 解读 |
| --- | ---: | --- |
| 原有 Git 跟踪文件 | 110 个，1,051,293 字节 | 仓库工作内容约 1.00 MiB，并非大体积代码仓库 |
| 运行时 Python | 47 个文件，7,167 行 | 包含空行和注释 |
| 测试 Python | 17 个文件，5,465 行 | 行数比不等于覆盖率 |
| 地理定位子系统 | 13 个 Python 文件，1,869 行 | 占运行时源码 26.1%，尚未计入定位 CLI、脚本和测试 |
| 定位目录全部跟踪内容 | 495,299 字节 | 包含中心点数据及原始行政区数据，并非全是代码 |
| 测速 CLI 单文件 | 894 行、52 个顶层函数 | 体积只是线索；职责混合和实际缺陷才是结论依据 |
| 地理依赖链 | 104,652,471 字节，约 99.8 MiB | reverse-geocoder + NumPy + SciPy 已安装文件总和；不含未登记缓存 |
| Playwright 包 | 139,774,395 字节，约 133.3 MiB | 当前为可选依赖；不含浏览器下载，不计入基础安装体积 |
| CLI 导入的项目模块 | 43 个，含包模块 | 主入口加载范围广；未据此推断启动慢 |

入口导入后 `numpy/scipy/reverse_geocoder/playwright/shapely` 均未出现在 `sys.modules`。已有延迟导入值得保留，**安装重量与启动重量是两回事**。

原始数据与统计脚本：[metrics.json](/Users/y4n9/Workspace/Projects/My-github-projects/netwatch-cli/.netwatch/audit-2026-10-15/metrics.json)、[collect_metrics.py](/Users/y4n9/Workspace/Projects/My-github-projects/netwatch-cli/.netwatch/audit-2026-10-15/collect_metrics.py)。

## 2. 主要发现（按整改优先级）

### F1 / P1：可选定位能力变成了所有用户的安装成本

证据：[pyproject.toml:11–23](/Users/y4n9/Workspace/Projects/My-github-projects/netwatch-cli/pyproject.toml#L11) 将 `reverse-geocoder` 放在基础 dependencies，同时又列入 geo extra。[device.py:106–124](/Users/y4n9/Workspace/Projects/My-github-projects/netwatch-cli/netwatch/location/geolocation/device.py#L106) 却将它当作可选依赖，缺失时已有结构化错误处理。

本机安装元数据确认 `reverse-geocoder 1.5.1 → numpy + scipy`，三者合计约 99.8 MiB。即使用户只查看网卡、网关或做测速，也会安装这条科学计算依赖链。这是当前最明确的基础安装膨胀来源。

**最小改法**：保留 geo extra，将 reverse-geocoder 从基础依赖移出，同时检查 all extra、README 和安装检查脚本的一致性。用“无 geo 环境基础功能正常、定位给出安装提示、有 geo 环境定位测试正常”验收。99.8 MiB 只是本机已安装文件口径，实际新装节省量要在干净环境重测。

不急着移除体积很小的 Python speedtest fallback；它有现成用途。Playwright 本来就是可选，先把文档分为基础安装与浏览器测速安装，保留主菜单 4 的既定行为。

### F2 / P1：文件拆开了，CLI 的依赖方向没有拆开

证据：[common.py:12–32](/Users/y4n9/Workspace/Projects/My-github-projects/netwatch-cli/netwatch/cli_modules/common.py#L12) 的 `ConsoleProxy` 与 `cli_override()` 从 `sys.modules["netwatch.cli"]` 动态查找对象。

```text
cli.py ──导入──> cli_modules/location、router、speedtest
   ↑                      │
   └──── sys.modules 反查 ─┘
```

这是运行时反向依赖，不是声称 Python 已发生循环导入崩溃。三个子模块合计 **15 处 cli_override 调用**；主入口导入 63 个项目符号，其中一部分服务于旧调用位置。AST 还识别出 **80 处测试对 cli / cli_mod 本身的 monkeypatch**（不含 `cli.Prompt` 等属性对象，因此不是全部相关测试数量）。

本轮探针已证明：替换主入口的 `probe_exit_ip`，会改变测速子模块内部实际调用的函数。读子模块本身不足以判断依赖来源。反过来，某些函数又直接绑定默认实现，形成不一致的替换规则。

**最小改法**：每次只迁移一个 CLI 模块的测试，mock 真实调用位置；再删除对应反查包装和无消费者的主入口再导出。优先从 location 的 6 个包装开始，不同时改测速流程。console 使用明确共享对象或参数即可；不引入容器。

### F3 / P1：CLI 承担后端策略，已经造成可复现的选择不一致

证据：[runner.py:145–151](/Users/y4n9/Workspace/Projects/My-github-projects/netwatch-cli/netwatch/speedtest/runner.py#L145) 的服务器列表会在 Ookla 缺失时回退到 Python；但 [CLI speedtest.py:385–415](/Users/y4n9/Workspace/Projects/My-github-projects/netwatch-cli/netwatch/cli_modules/speedtest.py#L385) 与 [467–489](/Users/y4n9/Workspace/Projects/My-github-projects/netwatch-cli/netwatch/cli_modules/speedtest.py#L467) 的手动选择和自动测试都硬编码 `official-ookla-cli`。

固定输入：Ookla 不可用，Python 可用，Python 返回一个名称包含 Fixture、ID 为 777 的服务器。所有后端及交互均 mock。

实测：

```text
KEYWORD_AUTO=CONFIRMED: listed python, invoked unavailable official
KEYWORD_777=CONFIRMED: listed python, invoked unavailable official
```

也就是“列表能显示，测速却调用缺失后端”。即使该菜单刻意只支持 Ookla，也应该在入口明确能力条件，而不是先展示 fallback 列表再失败。

同一文件还负责选网卡、批量选优、保存配置和多种展示；仅按行数切成几个 UI 文件不会消除策略重复。

**最小改法**：先明确关键词测速是“仅 Ookla”还是“随列表提供者执行”，让列表提供者与执行后端匹配；增加仅 Python 环境的两个回归。再把这条策略移到明确的小函数。保持 `run_best_speedtest()` / `show_auto_speedtest()` 的既有实现逻辑不变。

### F4 / P2：地理信息能力明显越过了网络排障的核心问题

浏览器位置、全球离线反查、中国区县中心点、WGS84/GCJ-02 转换、广州边界压力测试和附近道路查询已经组成独立子系统。普通“查看本机网络信息”也混入了浏览器定位交互：[location CLI:60–137](/Users/y4n9/Workspace/Projects/My-github-projects/netwatch-cli/netwatch/cli_modules/location.py#L60)。

其中 [boundary_tools.py](/Users/y4n9/Workspace/Projects/My-github-projects/netwatch-cli/netwatch/location/admin/boundary_tools.py) 与 [boundary_stress.py](/Users/y4n9/Workspace/Projects/My-github-projects/netwatch-cli/netwatch/location/admin/boundary_stress.py) 合计 **626 行**，仓内消费者是开发脚本、测试和 helper 之间的引用，未发现正常 CLI 执行路径需要它们。当前 package discovery 会发现这些 Python 模块；本轮没有构建 wheel，不声称测过实际发行包大小。原始行政区 CSV 则仅发现构建脚本使用，也不据此声称它必然进入 wheel。

**产品取舍建议**：

- 核心保留：实时流量、本机网络、当前出口、LAN 发现、测速、打开路由器后台。
- 定位先维持显式可选实验功能，停止向核心菜单继续扩展；精确边界、道路和数据压力测试优先迁到开发工具或独立实验项目。
- 小米设备名同步是特定厂商增强能力，继续隔离在增强入口，不演进为核心设备管理平台。
- 公网出口所属城市与真实设备位置分开；网络诊断不需要真实位置才能工作。

这些是产品收缩建议，不是本轮已删除的功能。现有主菜单 4、主菜单 5 和高级菜单 1 的行为保持原样。

### F5 / P2：现有边界检查对真正的反向依赖给出“全绿”

证据：[check_cli_boundaries.py:44–62](/Users/y4n9/Workspace/Projects/My-github-projects/netwatch-cli/scripts/dev/check_cli_boundaries.py#L44) 主要检查少数底层库 import 和大于 900 行的文件；[main:83–87](/Users/y4n9/Workspace/Projects/My-github-projects/netwatch-cli/scripts/dev/check_cli_boundaries.py#L83) 始终返回 0。

当前 7 个 CLI 文件全部输出 `ok_adapter`，包括反查入口的 common 和 894 行的测速 CLI。这个结果只能说明“未命中现有启发式”，并非分层验证通过。

**最小改法**：先加两个负向样例——子模块读取 `sys.modules['netwatch.cli']`、领域层导入 CLI；保证违规样例能被检出，再确定严格模式的非零退出规则。为现存债务设明确基线，避免把长期 allowlist 当作修复。无需换成大型架构治理工具。

### F6 / P2：测试隔离有两处例外，旧报告也高估了工程状态

审计驱动禁止真实子进程、外部连接/DNS、浏览器启动；保留 geolocation 测试所需的 localhost HTTP。未读取真实公网出口，未启动浏览器或测速程序。

完整套件：**288 passed，2 failed，退出 1**。两个失败分别是：

1. [test_router.py:14–29](/Users/y4n9/Workspace/Projects/My-github-projects/netwatch-cli/tests/network/test_router.py#L14) 只 mock 旧的默认网关函数；当前调用链先执行 LAN 网关发现，在 macOS 会尝试真实 `route -n get default`。属于遗漏 mock，和反查兼容层的维护成本直接相关。
2. [test_boundary_stress.py:156–172](/Users/y4n9/Workspace/Projects/My-github-projects/netwatch-cli/tests/location/test_boundary_stress.py#L156) 有意启动本地 Python 脚本做 CLI 集成验证。它不是公网访问或恶意行为，但与“默认 subprocess 测试全部 mock”的项目要求不一致；应单独分组，或改为进程内入口测试。

排除这两例后：**288 passed，2 deselected，退出 0，未记录被阻断调用**。这不是声称默认原始 `pytest -q` 会出现功能失败，也不是修复了那两例；它揭示默认套件并不完全满足隔离契约。

旧 [audit_report.md:60、239、296](/Users/y4n9/Workspace/Projects/My-github-projects/netwatch-cli/audit_report.md#L60) 分别用测试/源码行数比推断覆盖良好、只看直接依赖数量断言轻量、笼统判定架构清晰。此次证据不足以支持这些结论，旧报告保留作为历史记录。

交接文档也存在失真：[Codex handoff:49、76](/Users/y4n9/Workspace/Projects/My-github-projects/netwatch-cli/docs/handoff/handoff-to-codex.md#L49) 仍指向旧函数位置和旧路径；[DeepSeek handoff:79–82](/Users/y4n9/Workspace/Projects/My-github-projects/netwatch-cli/docs/handoff/handoff-to-deepseek.md#L79) 把事件进度和隐藏 debug 列为待办，当前代码已经具备这些行为。README 许可证说明也与现有 MIT LICENSE 不一致。继续照旧待办增加能力，会再次推高复杂度。

## 3. 建议实施顺序：一轮只验收一件事

| 顺序 | 小步变更 | 验收条件 |
| --- | --- | --- |
| 0 | 修正路由测试 mock；地理 CLI 集成测试明确分组；加关键词策略回归 | 默认测试无真实外部 IO；记录现有策略缺陷，不以隐藏测试换全绿 |
| 1 | 仅调整 geo 依赖归属及对应安装文档 | 干净基础环境无 NumPy/SciPy；基础功能、缺依赖提示和 geo extra 各自有验证；新测实际体积 |
| 2 | 只移除 location CLI 的反查包装 | 6 处包装消失；测试 mock 子模块真实依赖；网络信息输出不变 |
| 3 | 收敛关键词列表与执行后端契约 | 仅 Python、仅 Ookla、无后端及取消路径均有回归；冻结函数保持不变 |
| 4 | 决定地理实验保留范围；迁出开发专用 helper | 核心用户路径不依赖边界/道路；导入、打包与 geo 测试完整验证 |
| 5 | 将当前状态集中到一份交接页，旧计划标历史 | 新接手者不再按已完成待办继续加功能 |

停止条件：一旦基础安装轻量、依赖方向明确、常用流程可稳定测试，就停止架构整理。不以减少文件数、引入模式或新增测速后端作为成果。

## 4. 验证与交付

已执行：完整隔离测试、排除两处已定位例外的隔离测试、4 个架构探针、CLI 边界检查。完整测试在报告改写前后使用相同驱动复跑；精确命令、原始输出、退出状态、编译检查和回滚结果见验证记录。

```text
BRIDGE=CONFIRMED: child resolves parent replacement
KEYWORD_AUTO=CONFIRMED: listed python, invoked unavailable official
KEYWORD_777=CONFIRMED: listed python, invoked unavailable official
BOUNDARY_GUARD=BLIND: parent lookup accepted as ok_adapter
PROBES=PASS 4
```

四个交付物：

- MODIFIED_FILE：本报告 `/Users/y4n9/Workspace/Projects/My-github-projects/netwatch-cli/docs/audits/2026-10-15-architecture.md`
- DIFF_FILE：`/Users/y4n9/Workspace/Projects/My-github-projects/netwatch-cli/.netwatch/audit-2026-10-15/DIFF.patch`
- VERIFICATION：`/Users/y4n9/Workspace/Projects/My-github-projects/netwatch-cli/.netwatch/audit-2026-10-15/VERIFICATION.txt`
- ROLLBACK：`/Users/y4n9/Workspace/Projects/My-github-projects/netwatch-cli/.netwatch/audit-2026-10-15/ROLLBACK.sh`

报告以旧审计报告的副本为起点重写；DIFF 比较旧报告与新报告，属于审计结论差异，不是运行时代码补丁。旧报告 SHA-256：`647813e3877d15092ebfb0efdd4b3f4c26d735aa454520c9ad7941d8b77e0a12`。

本地复验入口（完整测试预期保留上述两处隔离失败）：

```bash
A=/Users/y4n9/Workspace/Projects/My-github-projects/netwatch-cli/.netwatch/audit-2026-10-15
"$A/CHECK.sh" BASELINE
"$A/CHECK.sh" MODIFIED
"$A/CHECK.sh" ROLLBACK
```

回滚仅对另一份报告副本演练，验证恢复旧报告哈希、110 个原有跟踪文件哈希不变，以及本报告仍保留新内容。未提交、未推送；原始日志和辅助脚本放在已有 ignore 规则覆盖的 `.netwatch` 目录，不增加默认测试和发行包内容。

### 尚待验证 / 未关闭项

本轮是审计，不把建议当作修复。F1–F6 仍待逐步处理。当前验证平台为 macOS、Python 3.14.6；没有验证 Python 3.10、Linux/Windows 原生环境、真实网络测速或浏览器页面，也没有测覆盖率、启动性能、干净安装或实际 wheel。99.8 MiB 是本机静态文件测量，不是跨平台节省承诺。
