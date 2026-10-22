# 诊断一致性与安装验收实施记录

日期：2026-10-22（Asia/Taipei）。分支：`codex/post-p6-cohesion`，基点 `e5e25724893b65520b26f23b37d7a307b3061513`。

本轮先复核已完成 P0–P6，再按[增量计划](2026-10-22-lightweight-next-stage-plan.md)实施。用户已同意推送独立分支及运行 CI；合并、发布与默认安装推广分开处理。

## 实际改动

| 阶段 | 交付 | 用户可见变化 |
| --- | --- | --- |
| N1-A | 单一诊断有效性检查，覆盖分析、质量建议与 CLI 消费者 | 失败、空结果、非有限/负值或越界丢包率不再得到成功诊断；质量未知为 `UNKNOWN`。缺可选指标仍可展示部分测量 |
| N1-B | 平台分类与完整合法 `198.18.0.0/15` 线索集中判断 | 普通 bridge 不再被误当 VPN；未检出 VPN 不再被说成证实直连；基准测试地址仅为线索 |
| N1-C | 删除后端调用前虚报的下载/上传阶段 | 只显示调用/等待，保留取消与返回行为 |
| N2 | 一份固定数据真值，wheel/安装完整性与本地查询验收 | 不改变定位算法；交付数据损坏会使验收失败 |
| N3 | 开发侧隔离浏览器验收和跨平台 CI 实验 | 用户默认依赖、安装方式与测速入口不变 |

两处冻结函数、配置、菜单编号、测速后端执行和 parser 保持原样；未增加生产依赖、兼容桥、插件框架或新功能入口。没有访问真实测速网、路由器或用户定位。

N1-B 有一处有意修正的旧断言：`test_proxy_speedtest_no_vpn_tun_judgment` 保留测试身份和简洁输出检查，把“更接近直连”的旧文案改为“仍未证实物理直连”。这不是通过删用例或放宽断言取得绿色。

## 本地验收

| 检查 | 实际结果 |
| --- | --- |
| 改前 | 451 passed；未 mock 外部 I/O 为 0 |
| N1-A 新契约 RED | 51 failed / 9 passed；随后专项 243 passed |
| N1-B 新契约 RED | 42 failed / 9 passed；其中 2 个验证新增 helper，其余覆盖既有判定/文案分歧；随后测速及菜单合同 319 passed |
| N1-C 新契约 RED → GREEN | 2 failed → 连同菜单合同 16 passed |
| N2 wheel 负向 RED | 12 failed / 9 passed，均为损坏/重复成员未被拒绝；不存在以缺失函数异常代替缺陷证据的问题 |
| N2 专项 GREEN | 44 passed，含三份数据的缺失/空/截断/替换、重复成员、错误查询/记录数和来源检查 |
| N3 verifier RED → GREEN | 新缓存/offline 约束 6 failed / 1 passed → 7 passed；默认 pytest 全 mock |
| 完整 Python 3.14 / all | 604 passed，外部 I/O 为 0 |
| Python 3.10 / base | 590 passed / 14 原有 Shapely 可选用例 skipped，外部 I/O 为 0 |
| 静态门禁 | compileall、diff check 通过；`STRICT_BOUNDARY_VIOLATIONS=0` |
| 干净 wheel | 三份固定数据 SHA 正确；开发资产未进入运行时包 |
| 独立 wheel 安装 / browser 与 all | pip check 通过；`python -I` 确认实际安装来源，冷启动 `0 → 7`，实际中心点查询为东城区、记录 2851；外部 I/O 为 0 |

RED 数量是回归目标，不是漏洞数量。N1-A 的原正常 HIGH/MEDIUM/LOW 及部分指标合同继续测试；新增 UNKNOWN 并不把缺 jitter/loss 判为后端失败。

## 浏览器安装实验结论

**当前决定：保留原默认安装，精简方案尚不推广。**

- 从官方 PyPI 下载并核对 SHA 的 Playwright 1.44.0 wheel，在隔离解包目录运行随包 CLI：`install --only-shell --dry-run chromium` 返回 `error: unknown option '--only-shell'`，退出 1。没有把旧包安装进用户环境。
- 固定本机 Playwright 1.64.0、macOS ARM/Python 3.14，重新核对同版包/浏览器 URL 的 HEAD 长度。以 P6 固定 wheel 为共同输入，默认下载主体估算 **374,328,968 B**，仅 shell 估算 **179,497,115 B**，差值 **194,831,853 B（约 52%）**。这是同能力候选比较，不是本轮真实下载流量，也不是改后 wheel 的完整安装量。
- 本地既有完整 Chromium 目录逻辑文件大小 382,785,075 B，分配空间 374,920 KiB；只是现有安装测量，不是新释放的磁盘空间。没有删除缓存或旧环境。
- 独立目录仅链接已存在的匹配版本 shell/FFmpeg；默认和既有 HTTP2 重试参数均通过本地 HTML/JS、阻网负向检查及合成取消后关闭检查。两个 CLI 入口的 headless 参数保持一致。缺浏览器时返回结构化错误。
- 新 CI 保留原 macOS 默认完整浏览器验收，另对四个 browser 组合在独立目录执行 only-shell 实验；它使用该次安装的现代 Playwright，不证明 1.44 支持新参数。

官方候选依据：[Playwright headless shell 文档](https://playwright.dev/python/docs/browsers#chromium-headless-shell)。最低版本不兼容已由随包 CLI 实验确认；推广前须单独决定兼容分支或版本下限，并重新验收。网页滑块问题仍保留原状态，本地 HTML 成功不代表完整网页测速恢复。

## 复验命令

```bash
source .venv/bin/activate
python -m compileall -q netwatch scripts
python -m pytest -q
python scripts/dev/check_cli_boundaries.py
git diff --check
```

干净构建和安装流程见 `.github/workflows/engineering.yml`。安装验收必须用独立环境 `python -I scripts/dev/verify_installed.py`，`--browser` / `--geo` 与对应 extra 一致。浏览器验收在默认 pytest 之外显式执行，只加载内联页面并阻断网络。

## CI 与回退

平台矩阵：Linux 3.10 base、Linux 3.14 all、Windows 3.14 all、macOS 3.14 all、macOS 3.14 browser。推送后核验精确提交对应的运行、JUnit 与安装/浏览器产物，结果待回填。

分阶段提交：N1-A `c2dc3b3`、N1-B `3ade12c`、N1-C `4e008f8`、N2 `3ee8008`、N3/CI `75c6d32`。每一步可单独审查；回退时按相反顺序处理。整体副本回退、文件哈希和精确命令记录在本地 `.netwatch/implementation-2026-10-22/VERIFICATION.txt`，完成后补录结果。

本地原始日志、数据真值对照、固定版本安装实验和阶段差异保留于 `.netwatch/implementation-2026-10-22/`；随仓库的回归与 CI 才是可重复验收入口，不依赖个人目录即可执行。
