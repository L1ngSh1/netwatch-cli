# Documentation

`docs/` 按用途分组，避免历史计划和交接文档堆在同一层。

## Directories

- `handoff/`：给不同 AI agent 的交接文档，记录当前状态、边界和下一步注意事项。
- `plans/`：版本规划与历史路线，保留各个 v0.x 阶段的设计记录。
- `features/`：专项功能设计文档，例如 `speedtest.cn` browser automation。

## 当前状态

- [唯一交接状态：轻量化 P0–P6 验收](handoff/current-status.md)
- [下一阶段工程计划（2026-10-22）](plans/2026-10-22-lightweight-next-stage-plan.md)：保留已有成果，分步收口诊断、安装数据验收与可选安装减重。
- [诊断与安装验收实施记录](plans/2026-10-22-cohesion-results.md)：实际变更、验证、安装实验与回退。
- 其余 agent handoff 是历史记录，不作为当前状态来源。

## Key Links

- [Codex handoff](handoff/handoff-to-codex.md)
- [Claude handoff](handoff/handoff-to-claude.md)
- [DeepSeek handoff](handoff/handoff-to-deepseek.md)
- [speedtest.cn browser automation](features/speedtest-cn-browser-automation.md)
