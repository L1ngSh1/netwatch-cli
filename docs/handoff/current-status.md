# 当前工程状态（唯一交接入口）

更新：2026-10-22。当前工程分支为 `codex/post-p6-cohesion`，基点 `e5e2572`；用户同意推送独立分支并运行 CI，不合并主分支、不发布版本。

## 2026-10-22 增量工程

- N1-A/B/C：无效结果停止成功诊断，接口路径线索统一，等待提示不再虚报下载/上传阶段。未知质量使用 `UNKNOWN`，保留部分有效测量及原菜单行为。
- N2：源码、wheel、安装数据共用固定真值；安装后实际读取中心点，保留冷启动 `0 → 7` 合同。
- 本地全依赖 **604 passed**；Python 3.10 基础组合 **590 passed / 14 原有可选用例 skipped**；外部 I/O 尝试为 0。两种干净 wheel 安装通过。
- N3：仅 shell 本地 HTML/JS 实验通过，但最低允许版本 Playwright 1.44 不支持 `--only-shell`。默认依赖与安装命令保持不变，不把候选节省量说成已减少的安装体积。
- 新一轮平台 CI、完整证据与回退见[实施记录](../plans/2026-10-22-cohesion-results.md)。以下 P0–P6 记录继续保留为历史验收依据，不能替代新分支验收。

## 既有 P0–P6 基线（2026-10-19）

**P0–P6 工程验收完成；五组合 CI、干净 wheel 安装和回退均有实测证据。** 其他 handoff 页面是历史记录，以本页为当前事实来源。此前“基础功能保留，只简化高级功能”的范围纠正继续有效。

## 变更

| 阶段 | 实际交付 | 当前证据 |
| --- | --- | --- |
| P0 | 默认测试外部 I/O guard、主菜单行为及冻结函数保护 | 原 323 个测试保留 |
| P1 重修 | 高级菜单分组、解释按操作显示、精确定位延迟导入 | 基础功能、默认 browser 安装与 reverse-geocoder 保留 |
| P2 | 官方 Ookla 专用列表契约；关键词/运营商选服来源与执行一致 | Python-only、Ookla-only、两者都有/都无、空列表、非法输入、取消及候选成功/失败回归 |
| P3a/b/c | 定位、路由、测速消费显式依赖，测试 mock 实际调用位置 | `cli_override` 调用数 15 → 9 → 6 → 0 |
| P4 | 普通共享 Console、移除入口反查和无消费者再导出、严格 AST 边界门禁 | 0 个运行时反查桥、0 个 ConsoleProxy、0 个严格违规；人为违规 fixture 必须失败 |
| P5 | 只迁出地理开发资产 | helper 到 `scripts/geo/`，原始构建 CSV 到 `scripts/geo/data/`；定位算法、运行时中心点及 sample 数据保留 |
| P6 | 单一交接页、包合同检查、隔离安装验收、跨平台 CI | 本地全依赖 451 passed；远端五组合通过，隔离安装确认冷启动高级模块 0 → 7 |

两处冻结函数体保持原样：`runner.run_best_speedtest()`、`cli_modules.speedtest.show_auto_speedtest()`；AST 哈希和原行为回归均继续执行。主菜单 4、主菜单 5 的简洁/详情切换、高级 1 的完整诊断不变。

开发者迁移：业务测试应替换 `netwatch.cli_modules.location/router/speedtest` 实际使用的绑定，而不是 `netwatch.cli` 的兼容再导出。共享 console 来自 `netwatch.cli_modules.common`；替换单个模块的 console 不会再通过入口影响其他模块。

## 复验命令

沿用 README 默认安装，**仍需 `.[browser]` 和匹配当前 Playwright 的 Chromium**；基础包单独安装只是原来存在的显式选项，不是替代默认功能的减重方案。

```bash
source .venv/bin/activate
python -m compileall -q netwatch scripts
python -m pytest -q
python scripts/dev/check_cli_boundaries.py
git diff --check
```

构建使用独立开发环境，避免给现有用户环境增删依赖：

```bash
python3 -m venv .venv-build
.venv-build/bin/python -m pip install build
.venv-build/bin/python -m build --wheel
.venv-build/bin/python scripts/dev/verify_wheel.py dist/netwatch_cli-0.9.3-py3-none-any.whl
```

CI 从干净 checkout 构建 wheel，再创建新的环境安装该 wheel；使用该环境的 `python -I scripts/dev/verify_installed.py --browser yes --geo no` 验证默认组合。`--browser/--geo` 必须与实际安装的 extra 对应。该脚本隔离 HOME/config，断言包来自新环境，模拟主菜单 4、退出与高级定位，不访问公网、不启动真实测速浏览器。

浏览器文件检查是**单独显式的安装验收**，不属于默认 pytest：安装 Chromium 后运行 `scripts/dev/verify_browser_runtime.py`，只加载内联 HTML，不访问测速网。不要用仅 Python 包 import 成功代替浏览器可启动验收。

## 已观察结果

| 检查 | 结果 |
| --- | --- |
| 进入本轮前基线 | 358 passed；未 mock 外部 I/O 为 0 |
| P2 / P3a / P3b / P3c | 389 / 395 / 398 / 405 passed；未 mock 外部 I/O 均为 0 |
| P4 / P5 | 435 / 437 passed；未 mock 外部 I/O 均为 0 |
| 本地 P6 | 451 passed；另在 Python 3.10 基础环境为 437 passed / 14 个原有可选几何用例 skipped；未 mock 外部 I/O 均为 0 |
| P4 严格边界 | `STRICT_BOUNDARY_VIOLATIONS=0`；违规导入、相对导入、动态反查及缺失源码 fixture 非零退出 |
| P5 固定地理结果 | 同一数据的验证、六组坐标探针与压力报告 JSON 迁移前后逐字节相同 |
| P5 原始输入与中心点 | SHA-256 不变；运行时 CSV 的 CRLF 字节也保留，跨平台 checkout 使用 `-text` |
| P5 clean wheel | 158562 → 152134 字节；移出两个开发模块共 22813 个未压缩 Python 字节 |
| P5 wheel 内容对照 | 除移出的 helper、说明中的新开发路径及 RECORD 外，其余成员逐字节相同；依赖和入口 metadata 相同 |
| 隔离默认 wheel 安装 | 通过：包路径位于新环境、基础地理依赖存在、Playwright extra 存在、Shapely 非必需、主菜单/高级流程 mock 正常 |

这里的 6428 字节压缩差是这两个具体 wheel 的实际差值，不是虚拟环境/RAM/耗时节省。原始构建 CSV 原本就不在 wheel，不把移动它算成安装体积减少。没有卸载用户环境中的 Playwright、NumPy、SciPy 或其他依赖。

首轮 CI 揭示并修正了验收可移植性：冻结体仍来自 P0 `2f6a465`，改用版本稳定的 AST 字段序列化而非版本相关的 `ast.dump` 文本；保留旧参数标签，进入本轮前的 358 个 nodeid 全数保留，新增 93 个。缺 Shapely 组合明确断言既有依赖缺失结果，all 组合保留原正向几何断言；没有新增 skip。Windows 测试只修正路径表示和 HOME/USERPROFILE 合成环境，不改变运行时路径处理。

### 平台矩阵（已完成）

通过记录：[五组合 CI 39188660544](https://github.com/L1ngSh1/netwatch-cli/actions/runs/39188660544)。分支上的后续提交继续执行同一门禁；CI 页面可查看该分支最新的完整运行。下载 JUnit 后已确认五组合测试身份集合都与本地的 451 个一致，失败/错误均为 0。

| 系统 / Python | 安装组合 | 目标 |
| --- | --- | --- |
| macOS / 3.14 | all | 451 passed；干净 wheel 安装通过 |
| macOS / 3.14 | 原推荐 browser 默认组合 | 437 passed / 14 原有可选用例 skipped；独立 wheel 与真实 Chromium 本地 HTML 验收通过 |
| Linux / 3.10 | 原基础包 + dev | 437 passed / 14 原有可选用例 skipped；独立 wheel 安装通过 |
| Linux / 3.14 | all | 451 passed；独立 wheel 安装通过 |
| Windows / 3.14 | all | 451 passed；独立 wheel 安装通过；真实网络功能未执行 |

CI 文件：`.github/workflows/engineering.yml`。原有可选 Shapely 用例在缺依赖组合中可以按原条件 skip；all 组合必须执行其正向语义，不新增宽泛 skip/xfail 换绿色。原 358 个进入本轮前的测试均须保留。

## 未验证项与暂留问题

- 测速网当前现场出现人工滑块验证；已有补丁只识别并正确报告该状态，**完整网页测速尚未恢复**。用户明确要求本轮先搁置，不把它写成 P6 已修好。
- 不运行真实公网带宽测试、真实路由器 API、真实定位或用户网络配置改动。平台 CI 的网络功能均 mock；Chromium 安装验收只用本地合成页面。
- 远端五组合已通过；其检查范围为 mock 网络流程、真实包安装和本地浏览器渲染，不扩展为真实公网测速/设备测试结论。
- 没有版本号调整、主分支合并、GitHub Release、旧环境/数据清理。

## 回退方式

阶段补丁分别留存，可按 P6 → P5 → P4 → P3c → P3b → P3a → P2 逆序回退，连同对应测试/文档一起处理；P1 及网页验证识别补丁独立保留。

本地整体回退证据与执行脚本位于 `.netwatch/engineering-p2-p6-2026-10-19/`。脚本只处理该轮记录过的文件，并在写入前检查当前哈希；不卸载依赖、不删除用户地理数据、不回退浏览器缓存。已在独立 Git worktree 逆序执行真实 `git revert --no-commit`：恢复树与本轮前源文件树完全一致、119 个原文件哈希一致，重跑 358 passed；实际工作区保留工程改动。交付脚本另对最终文件副本执行同样的恢复/测试验收。

### 阶段提交索引

- P1：`717d183`；已存在的网页验证识别补丁：`1e189e1`（本轮暂留问题，不计作恢复网页测速）。
- P2：`a062947`；P3a：`ad4d749`；P3b：`32de4e5`；P3c：`0d73e68`。
- P4：`988dace`；P5：`16f42f5`；P6：`6de2b32` 起的 CI、跨平台验收和文档收尾提交。
- 撤回 P2–P6 而保留本轮前 P1/网页补丁的源文件基点为 `1e189e1`。只在独立 worktree 演练，不在用户工作副本执行 reset 或环境清理。
