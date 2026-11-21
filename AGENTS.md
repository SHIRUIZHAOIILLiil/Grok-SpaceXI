# AGENTS.md — 给所有编码 Agent 的硬规则

项目：Grok Bot London Financial Crime Hackathon，**Track 1（交易监控）**。
提交截止：**2026-11-21 17:00 Europe/London**（代码冻结，取最后一 commit）。

## 不可违反

1. `system/` 内只用 **Python 3 标准库**。没有 pandas / numpy / requests / rapidfuzz。需要模糊匹配就自己写。
2. **不得把 dev 数据写进系统**：case_id、客户名、金额、doc ID、结论，一个都不能硬编码。可以学模板、阈值、短语。
3. **确定性**：只用 `sorted()` 遍历，不用 `random`、`time.time()`、`datetime.now()`、多线程、网络顺序依赖。5 次运行必须字节一致。
4. 入口固定：`./system/run <机构目录> <输出文件>`，必须能从 `system/` 内部以全路径调用。
5. 只改你拥有的文件（见 `CONTRACT.md` §3）。跨文件改动先问 HQ。
6. `data/` 与 `hermes/` 已被 gitignore，**不要 `git add -f`**。

## 每改一次都要跑

```sh
./system/run data/institutions/bank output/bank.jsonl
python3 tools/validate.py output/bank.jsonl --data data/institutions/bank   # C 负责
```

全量：

```sh
for i in bank payments_fx emoney investment; do ./system/run data/institutions/$i output/$i.jsonl; done
```

## 判定口径

- 兜底 `ESCALATE / ESC_UNEXPLAINED_FUNDS`，**不猜 CLOSE**。
- 一案多告警：全部告警都被证据解释才可 CLOSE。
- CLOSE 需确信度 ≥ 0.72；ESC vs RFI：犯罪概率 > 0.4 选 ESC。
- `previous_reviews` 全是 CLOSE 的历史复核，是干扰项。

## reason 写法

2–4 句，必须包含本案的具体金额、对手方/人名、日期、文档 ID。RFI 必须写清要客户提供什么材料。
反例：「经审阅证据，活动已解释。」→ 这种句子拿 0 分。
