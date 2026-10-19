# 当前工程状态（唯一交接入口）

更新：2026-10-19。工作分支将使用 `codex/lightweight-p6-validation`；不合并主分支、不发布版本。

**P0–P5 本地验收完成；P6 正在运行安装包与远端平台矩阵验收。** 其他 handoff 页面是历史记录，以本页为当前事实来源。此前“基础功能保留，只简化高级功能”的范围纠正继续有效。

## 变更

| 阶段 | 实际交付 | 当前证据 |
| --- | --- | --- |
| P0 | 默认测试外部 I/O guard、主菜单行为及冻结函数保护 | 原 323 个测试保留 |
| P1 重修 | 高级菜单分组、解释按操作显示、精确定位延迟导入 | 基础功能、默认 browser 安装与 reverse-geocoder 保留 |
| P2 | 官方 Ookla 专用列表契约；关键词/运营商选服来源与执行一致 | Python-only、Ookla-only、两者都有/都无、空列表、非法输入、取消及候选成功/失败回归 |
| P3a/b/c | 定位、路由、测速消费显式依赖，测试 mock 实际调用位置 | `cli_override` 调用数 15 → 9 → 6 → 0 |
| P4 | 普通共享 Console、移除入口反查和无消费者再导出、严格 AST 边界门禁 | 0 个运行时反查桥、0 个 ConsoleProxy、0 个严格违规；人为违规 fixture 必须失败 |
| P5 | 只迁出地理开发资产 | helper 到 `scripts/geo/`，原始构建 CSV 到 `scripts/geo/data/`；定位算法、运行时中心点及 sample 数据保留 |
| P6 | 单一交接页、包合同检查、隔离安装验收、跨平台 CI | 本地全依赖 451 passed；远端五组合待验收 |

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

### 平台矩阵（P6 当前待远端完成）

| 系统 / Python | 安装组合 | 目标 |
| --- | --- | --- |
| macOS / 3.14 | all | 完整 mock 回归 + 干净 wheel 安装 |
| macOS / 3.14 | 原推荐 browser 默认组合 | 同上，几何依赖缺失路径 + 单独的 Chromium 本地安装验收 |
| Linux / 3.10 | 原基础包 + dev | 最低 Python、基础依赖及可选能力缺失路径 |
| Linux / 3.14 | all | 完整 mock 回归 + 干净 wheel 安装 |
| Windows / 3.14 | all | 完整 mock 回归 + 干净 wheel 安装；不是 Windows 真实网络功能验收 |

CI 文件：`.github/workflows/engineering.yml`。原有可选 Shapely 用例在缺依赖组合中可以按原条件 skip；all 组合必须执行其正向语义，不新增宽泛 skip/xfail 换绿色。原 358 个进入本轮前的测试均须保留。

## 未验证项与暂留问题

- 测速网当前现场出现人工滑块验证；已有补丁只识别并正确报告该状态，**完整网页测速尚未恢复**。用户明确要求本轮先搁置，不把它写成 P6 已修好。
- 不运行真实公网带宽测试、真实路由器 API、真实定位或用户网络配置改动。平台 CI 的网络功能均 mock；Chromium 安装验收只用本地合成页面。
- 尚无远端 CI 完成结论时，不将 P6 标为完成。
- 没有版本号调整、主分支合并、GitHub Release、旧环境/数据清理。

## 回退方式

阶段补丁分别留存，可按 P6 → P5 → P4 → P3c → P3b → P3a → P2 逆序回退，连同对应测试/文档一起处理；P1 及网页验证识别补丁独立保留。

本地整体回退证据与执行脚本位于 `.netwatch/engineering-p2-p6-2026-10-19/`。脚本只处理该轮记录过的文件，并在写入前检查当前哈希；不卸载依赖、不删除用户地理数据、不回退浏览器缓存。最终交付前会在独立源码副本恢复本轮前 358 测试状态并重跑，实际工作区保留工程改动。
