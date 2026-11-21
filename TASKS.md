# TASKS

状态：`[ ]` 未开始 · `[~]` 进行中 · `[x]` 完成 · `[!]` 阻塞

## A · 决策核心（system/decide.py, system/policy/*.json）
- [~] 核对四份 POLICY.md 的全部阈值，写入 policy JSON（保留原文引用）
- [ ] CLOSE 十一条理由码的判定条件（先做 INVOICE_MATCHES / DOCUMENTED_EVENT / BUSINESS_RECORDS_RECONCILE / OWN_ACCOUNT / WITHIN_PROFILE / LIST_MATCH_DIFFERENT_PARTY）
- [ ] RFI 五条（含 RFI_UPDATED_PROFILE 的 5 倍规则）
- [ ] ESCALATE 十条（MULE / STRUCTURING / PASS_THROUGH 优先）
- [ ] 多告警合并口径：全部解释才 CLOSE

## B · 证据与匹配（system/features.py, system/evidence.py）
- [~] 骨架指纹 + 文档类型索引（已交付 v0）
- [ ] 告警→交易→文档的金额/对手方/日期定位
- [ ] 内部名单实体消歧（TM22，464 告警）
- [ ] 模板分类器：骨架 → 语义标签（解释/可疑/无关）
- [ ] 未知骨架兜底

## C · 标注与验证（tools/）
- [ ] validate.py：schema、reason_code ∈ verdict、evidence ID 真实存在、case 全覆盖
- [ ] 100 个证据组合的伪标签表（LABELS.md 或 labels.json）
- [ ] repro.sh：5 次运行字节一致
- [ ] report.py：兜底率、verdict 分布、按规则的成功率

## D · 演示与提交（ui/, submission/, README.md）
- [ ] 单页 demo：告警 → 证据链 → 判定 → 理由
- [ ] 根 README.md（架构图、如何运行、三个案例）
- [ ] 2 分钟视频脚本 + 录制
- [ ] 仓库公开 + /submit 表单
