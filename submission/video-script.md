# 2 分钟视频分镜（Track 1）

成片 **1:58–2:00**，1080p，旁白中文、画面英文字幕（评委是伦敦的银行/支付/卡组织风控负责人，
字幕必须英文；如果队里有人能配英文旁白更好，中文稿可直接对照翻译）。

结构按官方要求的节奏走：问题 15s → 架构 30s → 真实案例 45s → 评分维度 20s → 收尾 10s。

---

## 录制前 10 分钟的准备

| 项目 | 设置 |
|---|---|
| 屏幕 | 浏览器 **1440×900**，缩放 100%，隐藏书签栏，关掉所有通知（勿扰模式） |
| UI | 先 `cd /workspace && python3 ui/server.py` 预热，把四个机构各点一次（服务端索引已在内存，录制时不会等） |
| 预置页面 | 标签页 1：`http://127.0.0.1:8000/#bank/BK-CS100112`（CLOSE）；标签页 2：`#bank/BK-CS109535`（ESCALATE）；标签页 3：终端 |
| 终端 | 字号 16pt，深色主题，先 `clear`；提前把命令敲好但不回车 |
| 鼠标 | 慢、准、每次点击停 0.5 秒；不要晃 |
| 录音 | 一段一段录，最后拼接；每段重录不要超过 2 次，口播比画面重要 |

**必录屏的镜头**：S4（终端跑批）、S5、S6、S7、S8。S1/S2/S3/S9 可以用标题卡或静态图。

---

## 分镜表

### S1 · 0:00–0:08 · 冷开场（标题卡，不用录屏）

- **画面**：黑底，白字逐行出现：
  `4,000 cases` / `6,467 alerts` / `16,402 documents` / `209,212 transactions`
  第 5 行：`one analyst cannot read all of it`
- **旁白**：
  > 四千个案子，六千多条告警，一万六千份文档。没有哪个分析师读得完。
- **字幕**：*4,000 cases. 6,467 alerts. 16,402 documents. No analyst reads all of it.*

### S2 · 0:08–0:15 · 问题（UI 静态画面，可不录屏，用截图缓慢推近）

- **画面**：`BK-CS100112` 的告警卡片特写——"£7,702.22 moved to or from Lebanon, limit £5,000"。
- **旁白**：
  > 告警从不告诉你结论；它只告诉你规则被触发了。结论要靠证据。
- **字幕**：*An alert never tells you the answer. It tells you a rule fired. The answer is in the evidence.*

### S3 · 0:15–0:30 · 架构一句话（幻灯片，画 ASCII 管线）

- **画面**：`run → main.py → features → decide → emit`，右侧标 `stdlib only · no network · pure function`。
- **旁白**：
  > 整条链路只有四步：装载案件，把告警还原成它测量的事实，在客户档案里按金额、对手方、日期找
  > 证据，最后由政策表给出判定。纯函数，只用标准库，不联网、不调模型。
- **字幕**：*Load → reconstruct what the alert measured → find the document that carries the same money → decide under the institution's policy. Stdlib only, no network, no model calls.*

### S4 · 0:30–0:45 · 真的能跑（**录屏：终端**）

- **动作**：敲 `for i in bank payments_fx emoney investment; do ./system/run data/institutions/$i output/$i.jsonl; done`，回车；
  再用 `time` 跑一次 bank，光标停在 `real 0m1.9s`；`head -c 400 output/bank.jsonl` 露出 JSON 行。
- **旁白**：
  > 一条命令跑完一千例，不到两秒；四千例五秒半。输出是每案一行的 JSON，字段就是契约里的六个。
- **字幕**：*1,000 cases in under 2 seconds. 4,000 in 5.5. One JSON line per case.*

### S5 · 0:45–1:07 · CLOSE 案例（**录屏：标签页 1**）

- **动作**：
  1. 停在 `BK-CS100112`，鼠标划过高亮的 `2 alerts → 19 transactions → 3 documents → 3 evidence IDs`；
  2. 指一下两条告警（TM06 黎巴嫩 £7,702.22；TM01 收入是申报的 4.6 倍）；
  3. 滚到证据区，点开 `EML-8464`——酒店邮件，"full refund of your deposit in the amount of £7,702.22"；
  4. 滚到底，指 reason 里的高亮 `EML-8464` 与 `CLOSE / REFUND_OF_EARLIER_PAYMENT`。
- **旁白**：
  > 这笔七千七百镑来自黎巴嫩，客户没申报过这个国家，收入还是申报的四点六倍——看起来该升级。
  > 但档案里有一封酒店邮件：婚礼取消，定金全额退回，金额一分不差；六月的原付款也在，同一个
  > 预订号。退款不是新钱，所以结案。
- **字幕**：*£7,702 from Lebanon, an undeclared corridor, 4.6× declared income — it looks like an escalation. The venue email says the wedding was cancelled and the deposit refunded in full, to the penny, against a June payment with the same booking reference. A refund is not new money. Closed.*

### S6 · 1:07–1:30 · ESCALATE 案例（**录屏：标签页 2**）

- **动作**：切到 `BK-CS109535`；停在交易表——三笔进账来自三个不同的人，四笔出账各 £4,803.01 汇往
  黎巴嫩四个不同姓名；滚到证据区，只有 KYC、地址证明和一句客服对话；指 reason 与 `ESC_HIGH_RISK_CORRIDOR`。
- **旁白**：
  > 这个案子反过来：三个互不相关的人打钱进来，四天之内被切成四笔一模一样的金额汇给黎巴嫩四个
  > 不同的人，备注都是"家庭支援"。档案里没有任何单据，只有客户一句口述。有疑点就不问客户——
  > 直接升级，理由里写清是哪六笔交易。
- **字幕**：*Three unrelated people pay in. Within four days the money leaves in four identical £4,803.01 slices to four different names in Lebanon, all marked "family support". No document, only the customer's own statement. Once there is suspicion you do not ask the customer. Escalated, citing the six transactions.*

### S7 · 1:30–1:40 · 确定性（**录屏：终端**）

- **动作**：跑两次 `./system/run` 到两个不同文件，`md5sum` 两行，MD5 相同；画面停住。
- **旁白**：
  > 同一份输入，跑两次，字节完全一致：没有随机数、没有时钟、没有并行，遍历全部排序。
- **字幕**：*Same input, same bytes: no randomness, no clock, no parallelism, every iteration sorted.*

### S8 · 1:40–1:50 · 证据引用（**录屏：回到标签页 1**）

- **动作**：点 reason 里的证据 chip，页面跳到并高亮那份文档；再点一个交易 ID，跳到交易行。
- **旁白**：
  > 理由里每一个编号都能点：点到文档，点到交易。评委不用相信我们，点一下就知道。
- **字幕**：*Every ID in the reason is clickable — it jumps to the document or the transaction. You do not have to trust us; click it.*

### S9 · 1:50–2:00 · 收尾（标题卡 + repo 地址）

- **画面**：`github.com/【org】/【repo】` / `python3 ui/server.py` / `MIT`（如适用）。
- **旁白**：
  > 代码、四千条判定、这个控制台都在仓库里；一条命令就能跑起来。
- **字幕**：*Code, 4,000 verdicts and this console are in the repo. One command to run it.*

---

## 后期检查

- [ ] 总长 ≤ 2:00（超时会被截断，宁可 1:55）
- [ ] 英文字幕无错字，专有名词大小写统一（CLOSE / RFI / ESCALATE 全大写）
- [ ] 画面里不出现真实姓名以外的隐私信息（数据是合成数据，可放心）
- [ ] 不要出现浏览器书签栏里的私人链接、邮箱、token
- [ ] 导出 1080p H.264，上传 YouTube **unlisted** 或 Loom，用无痕窗口验证可直接播放
- [ ] 视频描述里放 repo 链接 + 一句话定位
