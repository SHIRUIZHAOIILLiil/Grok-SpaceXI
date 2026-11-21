# 冻结契约 · Track 1

来源：`data/README.md` RULES 段 + `data/institutions/*/POLICY.md`（官方原文）。
冻结时间：2026-11-21 12:00 GMT。改动需经 HQ。

## 1. 硬约束（违反即失分）

- `system/` 内**只允许 Python 3 标准库 / Node 内置 / shell**。禁止 pandas、numpy、requests、rapidfuzz 等需安装的包。
- 入口：`system/run <机构目录> <输出文件>`。评测方传**全路径**，并**从 `system/` 内部**调用，不得依赖当前工作目录。
- 只读给定的机构文件夹，只写输出文件（及 `system/` 内文件）。
- 200 例 < 30 分钟。
- **不得把 dev 的 case_id / 人名 / 金额 / 文档 ID / 结论写进系统**。可学模板、阈值、短语，不可存实例。
- 5 次运行 verdict 与 reason_code 必须完全一致：只用 `sorted()` 遍历，无随机、无 `time.time()`、无 dict 顺序依赖、无并行。
- 一案一个 verdict；`alert_ids` 必须列出该案全部告警。

## 2. 输出 schema（每家机构一个文件，UTF-8）

```json
{"case_id":"BK-CS112964","alert_ids":["BK-AL4810357"],"verdict":"CLOSE","reason_code":"LIST_MATCH_DIFFERENT_PARTY","reason":"...","evidence":["REG-5461","INV-7291"]}
```

- `verdict` ∈ `CLOSE | RFI | ESCALATE`
- `reason_code` 必须属于该 verdict（见 `system/policy/<inst>.json` 的 `codes`）
- `reason`：2–4 句，必须写本案具体人物/金额/日期/文档；RFI 必须写明要什么材料。禁止通用句。
- `evidence`：文档 ID / 交易 ID / 名单条目 ID，必须真实存在于该案输入。

## 3. 文件所有权

| 文件 | 所有者 | 职责 |
|---|---|---|
| `system/run`, `system/main.py`, `system/emit.py` | HQ | 入口、装载、写盘、reason 渲染 |
| `system/decide.py`, `system/policy/*.json` | A | 决策表 |
| `system/features.py`, `system/evidence.py` | B | 特征与证据匹配 |
| `tools/*` | C | 标注、校验、复现、报告 |
| `ui/*`, `submission/*`, `README.md` | D | 演示与提交 |

C 不写 `system/`；D 不写 `system/` 与 `tools/`。

## 4. 接口签名（冻结）

### `features.build_case(institution_dir, case, index) -> dict`

```
{
  "case_id","institution","customer_id","review_window",
  "alerts":[{"alert_id","rule_id","rule_name","message","measured","transaction_ids"}],
  "rules":["TM01",...],                        # 去重排序
  "customer":{...customers 原始行...},          # 含 kind / declared
  "tx_in_window":[...], "tx_by_id":{...},
  "evidence":[{"doc_id","type","title","dated","text","skeleton","amounts"}],
  "docs_by_type":{type:[doc]},
  "signature":[...],                           # 去重排序的证据类型
  "internal_matches":[{"entry":{...},"matched_on":[...],"party":str}],
  "previous_reviews":[...],
  "held_payment": {...}|None
}
```

### `evidence.Index(institution_dir)`

- `.docs(customer_id)` / `.docs_by_type(customer_id)` / `.internal_list()` / `.previous_reviews(customer_id)`
- `.find_by_amount(customer_id, gbp, tol=0.01)` / `.find_by_text(customer_id, needle)`
- `.skeleton(text)`（金额→AMT、日期→DATE、数字→N、姓名→NAME 后的指纹）

### `decide.decide(features, policy) -> dict`

返回 `{"verdict","reason_code","evidence_ids","reason"}`；无副作用、不读盘、不用随机。

## 5. 兜底铁律

- 未被证据确证 → `ESCALATE`（默认 `ESC_UNEXPLAINED_FUNDS`），不猜 CLOSE。
- 一案多告警：**全部告警都被解释**才允许 CLOSE。
- 阈值：CLOSE 需确信度 ≥ 0.72；ESC vs RFI：犯罪概率 > 0.4 选 ESC。
- `previous_reviews`（历史全是 CLOSE）是干扰项，不得单独作为解释依据。

---

# Appendix: coding rules (from the working agreement)

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
