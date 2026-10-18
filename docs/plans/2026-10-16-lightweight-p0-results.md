# 轻量化改装 P0 验收记录

日期：2026-10-16（Asia/Shanghai）。仅实施 P0；在本轮验收点停止，P1 及以后未开始。
分支：`codex/architecture-audit`；基线：`33ca7b5b466cd9152954db235654ffa0efbc0eb9`。
2026-10-18（Asia/Taipei）复审通过，本轮作为独立 P0 补丁提交。原审计内容保留；计划状态同步更新。

## 变更

- `tests/network/test_router.py`：在实际消费位置 mock LAN 网关，保留缺失 stok 的错误提示断言。
- `tests/location/test_boundary_stress.py`：进程内调用现有 `main()`，保留固定 whole-city fixture、返回 1 和 stderr 错误语义。
- `tests/location/test_device_location.py`：仅六个现有定位服务器/回调用例显式申请 localhost。
- `tests/_io_guard.py`、`tests/conftest.py`：默认阻断未 mock 的 requests、DNS、socket、子进程、浏览器入口；事件只记录类别。每测试独立恢复 monkeypatch；合成 HOME/config 在收集前设置，逐用例配置隔离。回调测试的 loopback 不放行外部主机；本机 PTR 使用合成结果。
- `tests/test_io_guard.py`：正反向测试，覆盖 mock 可用、阻断发生在真实调用前、捕获异常和延迟线程仍使 teardown 失败、下一用例状态恢复。负向用例在进程内独立 guard/pytest 会话运行，预期违规不会混入正式套件计数。
- `tests/core/test_cli_contracts.py`：主菜单 4/5 与高级 1 调度，浏览器失败不 fallback，缺依赖/取消，主菜单 EOF/Ctrl+C，代理详情默认关闭且在结果后询问，冻结函数体 AST 哈希。

`netwatch/`、依赖、配置格式、安装器和两处冻结实现均未修改。没有移除旧测试或新增长期 xfail/宽泛 skip。

## 验证与结果

仓库根目录执行：

```bash
.venv/bin/python -m pytest -q
.venv/bin/pytest -q
.venv/bin/python -m compileall -q netwatch tests
.venv/bin/python scripts/dev/check_cli_boundaries.py
git diff --check
```

- 修改前审计驱动：`288 passed, 2 failed`，退出 1，`AUDIT_IO_EVENTS={'subprocess.Popen': 2}`。
- 修改后：`323 passed`，退出 0，`NETWATCH_UNMOCKED_IO_ATTEMPTS=0`。原有 290 个 nodeid 全部保留，新增 33 个；无 skip/xfail。
- guard 自测实际证明：业务捕获线程异常后，该测试仍在 teardown 报错；后续用例无事件、localhost 默认关闭。
- 编译和 diff 检查退出 0；边界检查仅维持原有观察结果，不计作 P4 完成。
- 本地关键词探针仍复现 Python 列表/缺失 Ookla 执行错配，留到 P2 修复；不是本轮绿色测试掩盖的问题。
- 在独立副本恢复改前文件与新文件缺席状态后，原始 112 文件哈希全部一致；同一审计驱动重新得到原来的两个失败与 288 passed，符合回退到基线的预期。

## 回退及本地证据

本地证据目录：`/Users/y4n9/Workspace/Projects/My-github-projects/netwatch-cli/.netwatch/lightweight-p0-2026-10-16/`。

包含 `MODIFIED_FILE.tar.gz`（八个变更文件副本）、`DIFF_FILE.patch`、`VERIFICATION.txt`、可执行 `ROLLBACK.sh`，以及原文件哈希、原文件副本、完整日志。详细精确命令和退出码以 `VERIFICATION.txt` 为准。该目录被忽略，不是默认测试的依赖。

回退命令必须显式给出目标目录，脚本先校验全部改后哈希，任何漂移均在写入前结束；只恢复本轮文件，不覆盖已有审计/计划或用户其他文件。独立副本演练完成，当前工作区保留 P0 改动。

## 未验证项

当前实测为 macOS / Python 3.14.6 / 现有全依赖环境。Linux、Windows、Python 3.10、四种干净安装组合与真实网络功能留到后续里程碑；本轮未运行安装器或真实浏览器。guard 是可清理的 Python 测试调用边界检查，不是针对恶意代码、原生扩展或收集期任意代码的系统沙箱。

## 下一轮任务卡

```text
先评审并验收轻量化 P0 补丁；通过后仅执行 P1。
把 reverse-geocoder 移入 geo extra，保留现有功能和 speedtest-cli fallback，
同步安装检查、缺依赖提示与 README，在独立环境验证 core/browser/geo/all。
不修改两处冻结函数，不进入 P2/P3，不卸载既有 .venv 中任何包。
```

## 2026-10-18 复审

- 无阻塞发现；检查了实际 mock 位置、错误语义、线程归属、逐测试恢复、缺依赖/取消及 AST 冻结。
- 再次运行 `.venv/bin/python -m pytest -q`：`323 passed in 19.62s`、`NETWATCH_UNMOCKED_IO_ATTEMPTS=0`，退出 0。编译和 `git diff --check` 通过。
- 先固化审计/计划文档，再提交本 P0 补丁；在独立副本演练提交级反向补丁，不在当前工作区执行 revert。
- 本轮用户已明确授权通过后推进 P1；P0 验收不代表原生扩展/恶意代码隔离或跨平台实测。
