# 提交表单填写清单（Track 1）

截止：**2026-11-21 17:00 Europe/London**（= 现场 code freeze，取最后一 commit）。
一个队只能提交一次。下面每一项都按官方 `/submit` 页面字段排列，`【待填】`的是我此刻无法替你确认的信息。

---

## 1. 项目名（Project name）

三个候选，全部 ≤ 20 字符、好念、能上标题：

| # | 名称 | 一句话理由 |
|---|---|---|
| A（推荐） | **Casefile** | 一个案子一个档案：告警、证据、判定都在一个文件里。README 已按这个名字写。 |
| B | **AlertDesk** | 直白说明是"告警复核台"，评委听到名字就知道产品是什么。 |
| C | **Closing Line** | 双关：结案（close）的那条线，也是"写清楚理由的那一行"。 |

> 换名字的话，`README.md` 首行标题和视频里的口播要同步改，别只改表单。

## 2. 赛道（Track）

**Track 1 — Stop suspicious payments (Transaction Monitoring)**
一个队只能选一个赛道；Top 5 是两条赛道合并评选，不是每条各取 5 个。

## 3. 项目简介（20–1200 字符）

官方限制 **20–1200 characters**，按字符数（含空格）算。下面这版实测 **997 字符**（含空格），可直接粘贴：

> Casefile closes transaction-monitoring alerts by reading the evidence, not by guessing. For each
> case it takes the alerts as measured facts and finds the documents on file that carry the same
> money: an invoice for the exact amount, a solicitor's letter naming the estate and the
> entitlement, a cash reconciliation listing the four deposits. It then returns CLOSE, RFI or
> ESCALATE with a reason code, a two-to-four sentence reason citing real amounts, dates and
> document IDs, and the evidence IDs it relied on. Four institutions run different policies —
> profile multiples, cash thresholds, beneficiary limits and which rules exist — so every threshold
> is read per institution, never as a global constant. The system is a pure function of the case:
> Python standard library only, no network, no model calls, byte-identical output across runs, and
> 4,000 cases in 5.5 seconds. A console shows the whole chain — alert, transactions, documents,
> verdict, reason — with every cited document one click away.

中文版（内部核对用，不要贴进英文表单）：

> Casefile 通过"读证据"而不是"猜"来复核交易监控告警：把每条告警当作已被测量的事实，在客户档案里
> 找承载同一笔钱的文档（金额完全一致的发票、写明遗产与具体份额的律师函、列出四笔现金存款的
> 对账表），然后给出 CLOSE / RFI / ESCALATE，附理由码、含真实金额日期与文档编号的 2–4 句理由、
> 以及所引用的证据 ID。四家机构政策不同，阈值逐家读取。系统是案件的纯函数：只用 Python 标准库、
> 不联网、不调模型、多次运行字节一致，4,000 例 5.5 秒。

**粘贴后一定要数一遍字符数**：`python3 -c "print(len(open('desc.txt').read()))"`；表单页面通常也有实时计数，别贴着 1200 上限。

## 4. 队伍信息（每名队员必填）

| 字段 | 值 |
|---|---|
| 联系人邮箱（contact email） | 【待填】 |
| 队员 1 姓名 | 【待填】 |
| 队员 1 Cursor email | 【待填】 |
| 队员 1 LinkedIn 或 X 链接 | 【待填】 |
| 队员 2 姓名 / Cursor email / LinkedIn 或 X | 【待填】×3 |
| 队员 3 姓名 / Cursor email / LinkedIn 或 X | 【待填】×3 |
| 队员 4 姓名 / Cursor email / LinkedIn 或 X | 【待填】×3 |

注意：**Cursor email 是发奖用的账号邮箱**，不是随便一个邮箱；每人一个链接就够（LinkedIn 或 X，
二选一），不要留空。

## 5. 链接

| 字段 | 值 |
|---|---|
| GitHub 仓库（必填，公开） | `https://github.com/【org】/【repo】` |
| 2 分钟视频（必填，可播放） | 【待填】YouTube unlisted / Loom / Vimeo / Google Drive 公开链接 |
| Live demo（可选） | 建议留空，或视频里演示本地 `python3 ui/server.py`；现场没有公网就别承诺在线地址 |

仓库必须是 **public**，评委看的是**最后一 commit**。`data/` 和任何 key 都不能在仓库里。

## 6. 提交前 5 分钟的逐项自检（最容易漏的）

- [ ] **仓库 public**：用无痕窗口打开 repo 链接，确认不用登录也能看文件。
- [ ] **最后一 commit 就是冻结的代码**：17:00 之后不要再 push。
- [ ] 仓库根目录有 `system/`（含 `run`、`main.py`、`decide.py`、`policy/*.json`）和 `output/*.jsonl`（4 个文件、各 1000 行）。
- [ ] **没有 `data/`**：`git ls-files | grep -c '^data/'` 必须是 `0`。
- [ ] **没有 key**：`git grep -nEi 'sk-[a-z0-9]{16,}|api[_-]?key|secret|token' -- . ':!*.md'` 人工看一遍结果。
- [ ] `.env` / `hermes/` 没有被 `git add -f` 进去（`.gitignore` 已列，但 `-f` 会绕过）。
- [ ] `python3 ui/server.py` 在干净 clone 上能起（不依赖 `data/` 之外的东西，出错也要有提示而不是 500 白屏）。
- [ ] 视频链接在**无痕窗口**能直接播放，不用申请权限、不是 "request access"。
- [ ] 简介字符数在 20–1200 之间（贴进去后页面会实时计数，截图留档）。
- [ ] 每个队员的 **姓名 + Cursor email + LinkedIn/X** 三项齐全——这是最常被漏掉的一栏。
- [ ] 只选了 **一个** 赛道：Track 1。
- [ ] 表单提交成功后截图/邮件留档（一个队只能提交一次，改不了就麻烦）。

## 7. 提交文案以外的加分动作

- 仓库 About 栏写一句和简介一致的话，加 topics：`aml` `transaction-monitoring` `fintech` `python`。
- `README.md` 顶部第一屏就要能看到：一句话定位、跑起来的命令、三个真实案例。
- 把 `output/` 一起提交（已包含），评委不跑代码也能读到 4,000 条判定。
