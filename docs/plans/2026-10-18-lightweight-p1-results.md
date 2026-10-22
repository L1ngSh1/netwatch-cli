# P1 重修：基础不动，仅高级功能减负

状态：旧 P1 已按用户要求退回并撤回；本页只记录重修版本，未提交或推送。P0 提交 `2f6a465` 保留，P2 未开始。

## 先纠正产品边界

旧方案把“默认安装缺少浏览器测速”和“移除基础定位依赖”当成减重，违反基础功能保持不变的要求。旧版即使 346 个测试绿色，也不代表 P1 产品验收通过；旧约 93.68 MiB 节省数字不再作为成果。

撤回前对全部 120 个工作区文件保存哈希和副本；旧 P1 源码包、补丁与验证日志保留在本地 `.netwatch/p1-rework-2026-10-18/`，原证据目录已标记 `REJECTED_BY_USER`。随后按原补丁哈希撤回 14 个旧 P1 文件，117 个文件与 P0 基线全部一致。P0 原 323 个测试重跑通过。

## 基础功能和安装：与 P0 保持一致

以下文件与 P0 逐字节相同：

- `README.md`：默认安装仍含 `.[browser]` 和 `python -m playwright install chromium`。
- `pyproject.toml`：原依赖和 extras 全部保留；reverse-geocoder 仍在基础依赖中。
- `scripts/check_install.sh`：原安装检查流程保留；没有换成“缺核心功能也算成功”的新检查器。
- `netwatch/cli_modules/speedtest.py`、`netwatch/speedtest/runner.py`：测速实现、默认输出、错误行为及 fallback 策略原样保留。
- `netwatch/location/geolocation/device.py`：基础浏览器定位及离线反向编码不变。
- `netwatch/core/config.py`、`netwatch/network/router.py`：配置和路由器实现不变。

主菜单、主循环、实时流量、本机网络信息和基础定位展示的函数体同时由 AST 固定和原行为测试保护。用户原 `.venv`、配置、浏览器数据和地理数据未改。

## 只改两处高级实现

1. `netwatch/cli_modules/location.py`：把精确行政区/附近道路编排的导入放进高级定位调用函数。启动、查看普通本机信息、打开高级菜单或取消高级定位时，不再提前加载该模块链。原参数、结构化结果、算法、数据和兼容桥保留。
2. `netwatch/cli.py`：高级菜单按“测速操作 / 配置与诊断 / 网页对照与定位实验”分组；13 个动作及原编号、返回项 14 全部保留。测速专用解释只在选择高级 1 后显示，不再在查看配置或返回时反复打印；高级 1 的完整诊断不变。

这轮减的是高级功能的无关启动加载和菜单噪声，不是删除功能或裁剪安装依赖。没有宣称安装体积、内存或启动耗时减少多少。

## 实测结果

- P0 基线：323 passed，意外外部调用 0。
- 新增 25 个回归，先在旧实现上得到 3 failed / 22 passed（重复提示及提前导入），再修正实现；原始红/绿日志保留。
- 重修完整套件：348 passed，原 323 个 nodeid 全数保留，新增 25；无新增 skip/xfail，意外外部调用 0。`pytest` 与 `python -m pytest` 两个入口均通过。
- 13 个高级动作的编号和分派全覆盖；高级定位取消不执行，高级编排参数/结果保持不变；基础函数体与默认安装要求有专门回归。
- 编译和 `git diff --check` 通过；静态边界脚本只保留原观察结果，不算 P4 完成。

### 独立冷进程探针

普通基础信息使用合成输入且不选择浏览器定位；所有外部行为均 mock，外部调用事件为 0。

| 时点 | P0 提前加载的地理相关 Python 模块 | 重修后 |
| --- | ---: | ---: |
| 仅导入 CLI | 7 | 0 |
| 普通本机信息 | 7 | 0 |
| 打开高级菜单后返回 | 7 | 0 |
| 取消高级精确定位 | 7 | 0 |
| 确认调用高级精确定位 | 7 | 7 |

两版实际调用编排后都返回相同的合成错误报告。模块集合包含基础定位也会按需使用的共享模块，不等于删掉这些模块；基础定位主动使用时仍保留原能力。

### 安装包和推荐默认安装

- 从独立构建输入生成 wheel，直接依赖及全部 extras 的 METADATA 与 P0 wheel 完全一致。
- 新建独立环境，安装推荐的 browser + dev 组合；Playwright、reverse-geocoder、NumPy、SciPy 均存在，Shapely 仍按原 geo 选项提供。原 `.venv` 未重装任何包。
- 初次在线安装遇到 SSL EOF，保留失败日志并停止该下载进程；随后从既有 pip 缓存中取出原固定版本 wheel，记录来源、哈希与平台 tag，以 `--no-index` 完成离线安装，`pip check` 通过。
- 源码目录外以 `python -I` 验证实际安装的包：菜单 4 模拟测速成功，固定后台且不截图，不回退其他后端；基础地理依赖存在；高级定位在没有 Shapely / 自定义边界时仍返回原有中心点回退报告。外部调用事件 0。
- 独立默认环境另跑基础相关回归；完整高级几何正向用例由原全依赖环境的 348 个完整测试覆盖，不用基础子集冒充全套覆盖。

## 复验与回退

在仓库根目录：

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m pytest -q tests/core/test_p1_advanced_contracts.py
.venv/bin/python -m compileall -q netwatch tests
git diff --check
```

详细命令、输入、输出、退出码、原文件哈希和冷进程模块集合在本地证据目录：
`/Users/y4n9/Workspace/Projects/My-github-projects/netwatch-cli/.netwatch/p1-rework-2026-10-18/`。

本轮单独生成 `MODIFIED_FILE.tar.gz`、`DIFF_FILE.patch`、`VERIFICATION.txt` 和可执行 `ROLLBACK.sh`；回退在独立副本演练，回退后 117 个 P0 文件哈希一致，原 323 个测试通过。撤销重修只回到 P0，不复活已被否决的旧 P1。

## 剩余验证与停止点

当前实测为本机 macOS / Python 3.14。未跑真实公网测速、真实 Chromium 或跨平台验证；基础源码、默认安装和依赖保持 P0 相同，并不等于替外部网站承诺可用性。
本轮停在 P1 重修评审点，未提交、未进入 P2，没有删除高级功能或迁移开发资产。
