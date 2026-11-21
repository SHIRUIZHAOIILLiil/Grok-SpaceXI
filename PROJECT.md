# Grok Bot London Financial Crime Hackathon — Track 1

**赛道**：Track 1 · Stop suspicious payments（交易监控）
**截止**：2026-11-21 17:00 Europe/London · 代码冻结 + 提交
**提交**：公开 GitHub 仓库 + 2 分钟视频 + 表单（含赛道、20–1200 字简介、队员 LinkedIn/X）

## 评分（官方，满分 100）

- 隐藏集 60%（verdict 60% / reason 40%）
- dev 集 20%（verdict 60% / reason 40%）
- 可复现 20%（5 次运行 verdict + reason_code 一致）
- 成本：该 CLOSE 却 RFI/ESC = 3；该 RFI 却 CLOSE = 10、发 ESC = 2；该 ESC 却 CLOSE = 10、发 RFI = 3
- 全部 ESCALATE = verdict 0 分

→ 阈值：CLOSE 需确信 ≥ 0.72；ESC vs RFI：犯罪概率 > 0.4 选 ESC。

## 数据

`data/`（gitignored），4 家机构 × 1,000 例 = 4,000；6,467 告警；16,402 证据文档。
告警已预生成，**不需要实现触发规则**。证据高度模板化（6 种 contact_note 骨架 / 785 篇）。

## 架构

```
system/run → main.py → features.build_case → decide.decide → emit.to_line
```

- `features.py` / `evidence.py`：告警 → 交易 → 文档的定位、骨架指纹、名单匹配（B）
- `decide.py` / `policy/*.json`：决策表（A）
- `tools/`：标注、校验、复现、报告（C）
- `ui/` `submission/` `README.md`：演示与提交（D）

## 当前状态

- [x] 数据下载、结构核对、模板化分析
- [x] 骨架 + 冻结契约（`CONTRACT.md`）
- [x] 端到端 baseline 跑通 4 家 × 1,000 例（全 ESCALATE，证明格式与确定性）
- [ ] 决策表（A）
- [ ] 证据匹配与骨架分类（B）
- [ ] 伪标签 + 校验 + 5 次复现（C）
- [ ] UI / 视频 / 提交（D）

## 关键文件

`CONTRACT.md` 冻结契约 · `AGENTS.md` 编码规则 · `TASKS.md` 任务板
