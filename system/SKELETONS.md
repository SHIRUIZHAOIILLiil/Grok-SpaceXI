# SKELETONS.md - skeleton to semantic tag map

Owner: B.  Generated from the four development institutions by
`scratch/skeletons.py`; do not hand edit the appendix.

Everything here is a template or a phrase pattern. No case id, customer
name, amount or document id from the development data is stored in the
system (docs/CONTRACT.md §1).

## 1. Fingerprints

`evidence.skeleton(text)` replaces `£nnn.nn` with `<AMT>`, dates with
`<DATE>`, remaining digits with `<N>` and capitalised words with `<NAME>`,
then collapses whitespace. Two instances of one template share a
fingerprint. On the development set the opening of the skeleton is what
identifies a template, which is why `template_key` keeps 120 characters
of it: the body still varies with the goods, the wording variant and the
table size, and a fingerprint that keeps all of that is too fine to label
by hand.

`evidence.template_key(type, text)` = document type + the first 120
characters of the skeleton. That is the unit this table maps: heading and
first field labels identify the template, the body can vary.

`evidence.classify(type, text)` applies the ordered rules below to the
whole document, so a chat that recruits a money mule is a mule chat even
though its heading says "Chat with the customer".

## 2. Tags

| tag | what the document is | recognised by | docs | share | supports |
|---|---|---|---|---|---|
| `invoice_matches_payment` | A supplier or sales invoice that states the goods, the amount and the payee. | type is invoice / supplier_invoice(s) / carrier_invoice / freight_invoices | 400 | 2.4% | CLOSE / `INVOICE_MATCHES` |
| `purchase_order_documented` | A purchase order that fixes the amount and the counterparty before payment. | type purchase_order | 33 | 0.2% | CLOSE / `INVOICE_MATCHES` |
| `business_contract` | A contract or schedule that sets out the work and the staged payments. | type consulting_contract / contract_schedule / supply_contract / employment_contract / factoring_agreement | 212 | 1.3% | CLOSE / `DOCUMENTED_EVENT` |
| `asset_sale` | Sale of a car, bike or property: advert, receipt, completion statement. | type sale_receipt / vehicle_sale_receipt / advert / completion_statement; chat says 'selling my car' | 248 | 1.5% | CLOSE / `DOCUMENTED_EVENT` |
| `asset_purchase` | Dealer invoice for a vehicle the customer bought. | type dealer_invoice | 38 | 0.2% | CLOSE / `DOCUMENTED_EVENT` |
| `gift_from_relative` | Signed gift letter from a named relative, with the giver's date of birth. | type gift_letter; chat says 'gift from my uncle/aunt' | 175 | 1.1% | CLOSE / `DOCUMENTED_EVENT` |
| `inheritance` | Solicitor letter confirming a bequest from an estate. | type solicitor_letter | 39 | 0.2% | CLOSE / `DOCUMENTED_EVENT` |
| `insurance_settlement` | Insurer letter accepting a claim and paying a stated sum. | type insurer_letter | 153 | 0.9% | CLOSE / `DOCUMENTED_EVENT` |
| `employment_payout` | Redundancy or settlement agreement paying compensation. | type redundancy_letter / settlement_letter | 91 | 0.6% | CLOSE / `DOCUMENTED_EVENT` |
| `holdings_sale` | Customer instruction to sell fund holdings and withdraw the proceeds. | type customer_email with 'sell my ... fund' + redundancy / living expenses | 46 | 0.3% | CLOSE / `DOCUMENTED_EVENT` |
| `medical_treatment_abroad` | Hospital invoice or chat naming the treatment, patient and hospital. | type hospital_invoice; text 'heart surgery' / 'university medical center' | 166 | 1.0% | CLOSE / `DOCUMENTED_EVENT` |
| `event_booking` | Booking confirmation for a trip or event, with the price per person. | type booking_confirmation | 84 | 0.5% | CLOSE / `DOCUMENTED_EVENT` |
| `purchase_receipt` | Receipt or schedule evidencing a purchase or cover already paid. | type receipt / insurance_schedule | 144 | 0.9% | CLOSE / `DOCUMENTED_EVENT` |
| `cash_withdrawal_returned` | Customer says the cash paid in is the same cash withdrawn earlier. | chat 'deposited that cash back' / 'same cash you previously withdrew' | 39 | 0.2% | CLOSE / `DOCUMENTED_EVENT` |
| `refund` | Credit note, cancellation or deposit return showing money coming back. | type credit_note / cancellation_confirmation / venue_email / deposit_return_letter / holding_deposit_receipt | 263 | 1.6% | CLOSE / `REFUND_OF_EARLIER_PAYMENT` |
| `erroneous_transfer_refund` | Customer email asking for a misdirected transfer to be returned. | type customer_email with 'accidentally transferred' / 'in error' / 'by mistake' | 45 | 0.3% | CLOSE / `REFUND_OF_EARLIER_PAYMENT` |
| `cash_business_records` | Takings book, reconciliation or management accounts that tie cash to sales. | type takings_book / cash_reconciliation / management_accounts / ticket_report / cash_handling_procedure | 197 | 1.2% | CLOSE / `BUSINESS_RECORDS_RECONCILE` |
| `cash_collection_documented` | Collection reports, contractor payment files or remittance advices. | type cash_collection_reports / payment_file / remittance_advice | 124 | 0.8% | CLOSE / `COLLECTION_DOCUMENTED` |
| `own_account_statement` | Statement from another provider in the customer's own name. | type bank_statement | 801 | 4.9% | CLOSE / `OWN_ACCOUNT` |
| `own_account_instruction` | Customer letter directing funds to an account held in their own name. | type customer_letter | 46 | 0.3% | CLOSE / `OWN_ACCOUNT` |
| `company_ownership_record` | Register extract, PSC register or group chart: officers, addresses, ownership. | type company_register_extract / significant_control_register / group_structure | 1817 | 11.1% | CLOSE / `GROUP_COMPANY` |
| `dormant_return` | Re-verification record showing the customer returned and was identified again. | type reverification_record | 152 | 0.9% | CLOSE / `RETURNING_CUSTOMER` |
| `loan_documented` | Signed loan agreement stating principal, term and purpose. | type loan_agreement | 38 | 0.2% | CLOSE / `THIRD_PARTY_DOCUMENTED` |
| `family_support_abroad` | Chat claim that the payment supports family overseas (claim only). | chat 'sending money to help my family' | 78 | 0.5% | RFI / `RFI_PURPOSE_DOCUMENTS` |
| `loan_from_friend_claim` | Chat claim that incoming funds are a loan from a friend, with no agreement. | chat 'loan from a friend' / 'loan provided by a friend' | 127 | 0.8% | RFI / `RFI_SOURCE_OF_FUNDS` |
| `background_kyc` | KYC summary, proof of address, routine contact note: profile, not explanation. | type due_diligence_summary / proof_of_address / contact_note | 10195 | 62.2% | neutral |
| `no_explanation` | A document that answers a different question and explains nothing. | chat or letter with no explanation phrase | 0 | 0.0% | neutral |
| `mule_recruitment_chat` | Account used to receive other people's money and pass it on for a cut. | 'payments assistant' / 'clients pay into my account' / 'as my wages' | 78 | 0.5% | ESCALATE / `ESC_MULE_ACTIVITY` |
| `third_party_funds_held` | Customer holds or invests other people's money through their own account. | 'invest for a few people' / 'investing through mine' / 'cannot open an account here' | 150 | 0.9% | ESCALATE / `ESC_THIRD_PARTY_FUNDING` |
| `group_funds_pass_through` | A connected company funds the payment to a supplier: money routed through. | 'cover our supplier payment' / 'both companies are mine' | 22 | 0.1% | ESCALATE / `ESC_PASS_THROUGH` |
| `structuring_enquiry` | Customer asks how to split payments to stay under the reporting threshold. | 'under £10,000' / 'aggregated' + 'exempt' / 'avoid' | 119 | 0.7% | ESCALATE / `ESC_STRUCTURING` |
| `high_risk_routing_unexplained` | Director cannot explain why goods from Turkey are paid for via Lebanon. | 'unable/declined to explain' + 'Lebanon' / 'routing' | 42 | 0.3% | ESCALATE / `ESC_HIGH_RISK_CORRIDOR` |
| `shared_device_export` | One device or IP used by several customers. | type device_export | 84 | 0.5% | ESCALATE / `ESC_ACCOUNT_MISUSE` |
| `incoming_fraud_report` | Another bank reports an authorised push payment scam into this account. | type sending_bank_fraud_report | 156 | 1.0% | ESCALATE / `ESC_UNEXPLAINED_FUNDS` |
| `unknown` | Unrecognised template: no rule fired and the document type is not known. | type outside KNOWN_TYPES and no phrase rule matched | 0 | 0.0% | neutral |
| **total** | | | **16402** | **100.0%** | |

## 3. Unseen templates

`classify` never raises. The last line of the rule ladder is:

- a document type outside `KNOWN_TYPES` (54 types) that matches no phrase
  rule returns `tag = "unknown"`;
- an empty or unreadable file returns `"unknown"`;
- any exception inside the classifier is caught and returns `"unknown"`.

`features.build_case` also forces `doc["tag"]` to exist on every document
(`setdefault("tag", "unknown")`), so `decide` can always fall through to
its default branch instead of raising `KeyError`.

## 4. Coverage

| tag | bank | payments_fx | emoney | investment | total |
|---|---|---|---|---|---|
| `invoice_matches_payment` | 35 | 323 | 42 | 0 | 400 |
| `purchase_order_documented` | 0 | 33 | 0 | 0 | 33 |
| `business_contract` | 36 | 131 | 0 | 45 | 212 |
| `asset_sale` | 110 | 0 | 92 | 46 | 248 |
| `asset_purchase` | 38 | 0 | 0 | 0 | 38 |
| `gift_from_relative` | 35 | 0 | 0 | 140 | 175 |
| `inheritance` | 39 | 0 | 0 | 0 | 39 |
| `insurance_settlement` | 39 | 22 | 46 | 46 | 153 |
| `employment_payout` | 0 | 0 | 45 | 46 | 91 |
| `holdings_sale` | 0 | 0 | 0 | 46 | 46 |
| `medical_treatment_abroad` | 76 | 0 | 90 | 0 | 166 |
| `event_booking` | 39 | 0 | 45 | 0 | 84 |
| `purchase_receipt` | 77 | 22 | 45 | 0 | 144 |
| `cash_withdrawal_returned` | 39 | 0 | 0 | 0 | 39 |
| `refund` | 38 | 45 | 135 | 45 | 263 |
| `erroneous_transfer_refund` | 0 | 0 | 0 | 45 | 45 |
| `cash_business_records` | 151 | 0 | 46 | 0 | 197 |
| `cash_collection_documented` | 39 | 85 | 0 | 0 | 124 |
| `own_account_statement` | 149 | 210 | 180 | 262 | 801 |
| `own_account_instruction` | 0 | 0 | 0 | 46 | 46 |
| `company_ownership_record` | 365 | 1232 | 170 | 50 | 1817 |
| `dormant_return` | 38 | 22 | 46 | 46 | 152 |
| `loan_documented` | 38 | 0 | 0 | 0 | 38 |
| `family_support_abroad` | 36 | 0 | 42 | 0 | 78 |
| `loan_from_friend_claim` | 36 | 0 | 41 | 50 | 127 |
| `background_kyc` | 2636 | 1824 | 2835 | 2900 | 10195 |
| `no_explanation` | 0 | 0 | 0 | 0 | 0 |
| `mule_recruitment_chat` | 36 | 0 | 42 | 0 | 78 |
| `third_party_funds_held` | 0 | 0 | 0 | 150 | 150 |
| `group_funds_pass_through` | 0 | 22 | 0 | 0 | 22 |
| `structuring_enquiry` | 36 | 42 | 41 | 0 | 119 |
| `high_risk_routing_unexplained` | 0 | 42 | 0 | 0 | 42 |
| `shared_device_export` | 0 | 0 | 84 | 0 | 84 |
| `incoming_fraud_report` | 72 | 0 | 84 | 0 | 156 |
| `unknown` | 0 | 0 | 0 | 0 | 0 |

Explanation-bearing documents (a tag that can support a CLOSE): **5351** of
16402 (32.6%).  Red-flag documents (a tag that supports an ESCALATE): **651**
(4.0%).  Neutral (profile, background, no explanation, unknown): **10195**
(62.2%).

`unknown` on the development set: **0**.

## 5. Families

632 families cover 16402 documents. 5 families carry more than one tag,
because the same opening line (for example a chat that starts with the
customer's question) wraps different answers; the tag there is decided by
the body, which is the point of classifying text rather than headings.

### Largest families

| docs | type | tag | opening |
|---|---|---|---|
| 2851 | due_diligence_summary | `background_kyc` | # <NAME> due diligence summary **<NAME> ID:** KYC-<N> **<NAME>:** <DATE> **<NAME>:** <NAME |
| 2851 | proof_of_address | `background_kyc` | # <NAME> bill used as proof of address **<NAME> ID:** POA-<N> **<NAME>:** <DATE> **<NAME>: |
| 1149 | company_register_extract | `company_ownership_record` | # <NAME> register extract for <NAME> **<NAME> ID:** INC-<N> **<NAME>:** <DATE> **<NAME>:** |
| 1149 | due_diligence_summary | `background_kyc` | # <NAME> due diligence summary **<NAME> ID:** KYC-<N> **<NAME>:** <DATE> **<NAME>:** <NAME |
| 672 | bank_statement | `own_account_statement` | # <NAME> from <NAME> **<NAME> ID:** STM-<N> **<NAME>:** <DATE> **<NAME> holder:** <NAME> * |
| 585 | contact_note | `background_kyc` | # <NAME> contact note **<NAME> ID:** NTE-<N> **<NAME>:** <DATE> <NAME> called in requestin |
| 561 | contact_note | `background_kyc` | # <NAME> contact note **<NAME> ID:** NTE-<N> **<NAME>:** <DATE> <NAME> with the customer t |
| 560 | contact_note | `background_kyc` | # <NAME> contact note **<NAME> ID:** NTE-<N> **<NAME>:** <DATE> <NAME> customer contacted  |
| 556 | contact_note | `background_kyc` | # <NAME> contact note **<NAME> ID:** NTE-<N> **<NAME>:** <DATE> <NAME> a routine data veri |
| 556 | contact_note | `background_kyc` | # <NAME> contact note **<NAME> ID:** NTE-<N> **<NAME>:** <DATE> <NAME> with the customer t |
| 526 | contact_note | `background_kyc` | # <NAME> contact note **<NAME> ID:** NTE-<N> **<NAME>:** <DATE> <NAME> customer reached ou |
| 156 | sending_bank_fraud_report | `incoming_fraud_report` | # <NAME> report from <NAME> **<NAME> ID:** RPT-<N> **<NAME>:** <DATE> **<NAME>:** <NAME> o |
| 154 | company_register_extract | `company_ownership_record` | # <NAME> register extract for <NAME> **<NAME> ID:** REG-<N> **<NAME>:** <DATE> **<NAME>:** |
| 152 | reverification_record | `dormant_return` | # <NAME> re-verification record **<NAME> ID:** RVF-<N> **<NAME>:** <DATE> <NAME> re-verifi |
| 127 | company_register_extract | `company_ownership_record` | # <NAME> register extract for <NAME> **<NAME> ID:** REG-<N> **<NAME>:** <DATE> **<NAME>:** |
| 119 | company_register_extract | `company_ownership_record` | # <NAME> register extract for <NAME>: officers **<NAME> ID:** REG-<N> **<NAME>:** <DATE> * |
| 119 | significant_control_register | `company_ownership_record` | # <NAME> of people with significant control for <NAME> **<NAME> ID:** PSC-<N> **<NAME>:**  |
| 105 | company_register_extract | `company_ownership_record` | # <NAME> register extract for <NAME> **<NAME> ID:** REG-<N> **<NAME>:** <DATE> **<NAME> nu |
| 99 | support_chat | `loan_from_friend_claim` | # <NAME> with the customer **<NAME> ID:** CHT-<N> **<NAME>:** <DATE> **<NAME>:** <NAME>, w |
| 84 | device_export | `shared_device_export` | # <NAME> and login export **<NAME> ID:** DEV-<N> **<NAME>:** <DATE> / <NAME> / <NAME> seen |
| 83 | hospital_invoice | `medical_treatment_abroad` | # <NAME> from <NAME> **<NAME> ID:** INV-<N> **<NAME>:** <DATE> **<NAME>:** <NAME> **<NAME> |
| 78 | support_chat | `mule_recruitment_chat` | # <NAME> with the customer **<NAME> ID:** CHT-<N> **<NAME>:** <DATE> **<NAME>:** <NAME>, a |
| 78 | support_chat | `family_support_abroad` | # <NAME> with the customer **<NAME> ID:** CHT-<N> **<NAME>:** <DATE> **<NAME>:** <NAME>, w |
| 77 | consulting_contract | `business_contract` | # <NAME> contract with <NAME> **<NAME> ID:** CON-<N> **<NAME>:** <DATE> **<NAME>:** <NAME> |
| 63 | payment_file | `cash_collection_documented` | # <NAME> payment file **<NAME> ID:** PAY-<N> **<NAME>:** <DATE> / <NAME> / <NAME> / <NAME> |
| 50 | support_chat | `third_party_funds_held` | # <NAME> with the customer **<NAME> ID:** CHT-<N> **<NAME>:** <DATE> **<NAME>:** <NAME>, t |
| 50 | support_chat | `third_party_funds_held` | # <NAME> with the customer **<NAME> ID:** CHT-<N> **<NAME>:** <DATE> **<NAME>:** <NAME>, w |
| 50 | support_chat | `third_party_funds_held` | # <NAME> with the customer **<NAME> ID:** CHT-<N> **<NAME>:** <DATE> **<NAME>:** <NAME>, w |
| 46 | advert | `asset_sale` | # <NAME> advert **<NAME> ID:** ADV-<N> **<NAME>:** <DATE> <NAME> road bike, size <N>, two  |
| 46 | bank_statement | `own_account_statement` | # <NAME> from <NAME> SAL **<NAME> ID:** STM-<N> **<NAME>:** <DATE> **<NAME> holder:** <NAM |
| 46 | completion_statement | `asset_sale` | # <NAME> statement from <NAME> LLP **<NAME> ID:** CMP-<N> **<NAME>:** <DATE> **<NAME>:** < |
| 46 | customer_email | `holdings_sale` | # <NAME> from the customer **<NAME> ID:** EML-<N> **<NAME>:** <DATE> <NAME>: <NAME>: <NAME |
| 46 | takings_book | `cash_business_records` | # <NAME> takings book **<NAME> ID:** TAK-<N> **<NAME>:** <DATE> / <NAME> / <NAME> / <NAME> |
| 45 | bank_statement | `own_account_statement` | # <NAME> account statement from <NAME> **<NAME> ID:** STM-<N> **<NAME>:** <DATE> **<NAME>  |
| 45 | credit_note | `refund` | # <NAME> note from <NAME> SAL **<NAME> ID:** CRN-<N> **<NAME>:** <DATE> **<NAME>:** <NAME> |
| 42 | supplier_invoices | `invoice_matches_payment` | # <NAME> from <NAME> **<NAME> ID:** INV-<N> **<NAME>:** <DATE> **<NAME>:** <NAME>, <NAME>  |
| 42 | supplier_invoices | `invoice_matches_payment` | # <NAME> from <NAME> SARL **<NAME> ID:** INV-<N> **<NAME>:** <DATE> / <NAME> / <NAME> / <N |
| 39 | cash_collection_reports | `cash_collection_documented` | # <NAME> collection reports from <NAME> **<NAME> ID:** COL-<N> **<NAME>:** <DATE> <NAME> b |
| 39 | cash_handling_procedure | `cash_business_records` | # <NAME> handling procedure, <NAME> **<NAME> ID:** PRC-<N> **<NAME>:** <DATE> <NAME> car p |
| 39 | vehicle_sale_receipt | `asset_sale` | # <NAME> vehicle sale receipt **<NAME> ID:** SAL-<N> **<NAME>:** <DATE> <NAME> from <NAME> |

### Appendix A - every family (632)

| docs | type | tag | opening |
|---|---|---|---|
| 2851 | due_diligence_summary | `background_kyc` | # <NAME> due diligence summary **<NAME> ID:** KYC-<N> **<NAME>:** <DATE> **<NAME>:** <NAME> **<NAME> type:** i |
| 2851 | proof_of_address | `background_kyc` | # <NAME> bill used as proof of address **<NAME> ID:** POA-<N> **<NAME>:** <DATE> **<NAME>:** <NAME> **<NAME> h |
| 1149 | company_register_extract | `company_ownership_record` | # <NAME> register extract for <NAME> **<NAME> ID:** INC-<N> **<NAME>:** <DATE> **<NAME>:** <NAME> **<NAME> num |
| 1149 | due_diligence_summary | `background_kyc` | # <NAME> due diligence summary **<NAME> ID:** KYC-<N> **<NAME>:** <DATE> **<NAME>:** <NAME> **<NAME> type:** b |
| 672 | bank_statement | `own_account_statement` | # <NAME> from <NAME> **<NAME> ID:** STM-<N> **<NAME>:** <DATE> **<NAME> holder:** <NAME> **<NAME>:** <NAME> ** |
| 585 | contact_note | `background_kyc` | # <NAME> contact note **<NAME> ID:** NTE-<N> **<NAME>:** <DATE> <NAME> called in requesting assistance with se |
| 561 | contact_note | `background_kyc` | # <NAME> contact note **<NAME> ID:** NTE-<N> **<NAME>:** <DATE> <NAME> with the customer today. <NAME> request |
| 560 | contact_note | `background_kyc` | # <NAME> contact note **<NAME> ID:** NTE-<N> **<NAME>:** <DATE> <NAME> customer contacted us today to inquire  |
| 556 | contact_note | `background_kyc` | # <NAME> contact note **<NAME> ID:** NTE-<N> **<NAME>:** <DATE> <NAME> a routine data verification check, the  |
| 556 | contact_note | `background_kyc` | # <NAME> contact note **<NAME> ID:** NTE-<N> **<NAME>:** <DATE> <NAME> with the customer today regarding an up |
| 526 | contact_note | `background_kyc` | # <NAME> contact note **<NAME> ID:** NTE-<N> **<NAME>:** <DATE> <NAME> customer reached out via phone today to |
| 156 | sending_bank_fraud_report | `incoming_fraud_report` | # <NAME> report from <NAME> **<NAME> ID:** RPT-<N> **<NAME>:** <DATE> **<NAME>:** <NAME> operations, <NAME> ** |
| 154 | company_register_extract | `company_ownership_record` | # <NAME> register extract for <NAME> **<NAME> ID:** REG-<N> **<NAME>:** <DATE> **<NAME>:** <NAME> **<NAME>:**  |
| 152 | reverification_record | `dormant_return` | # <NAME> re-verification record **<NAME> ID:** RVF-<N> **<NAME>:** <DATE> <NAME> re-verified on <DATE> with a  |
| 127 | company_register_extract | `company_ownership_record` | # <NAME> register extract for <NAME> **<NAME> ID:** REG-<N> **<NAME>:** <DATE> **<NAME>:** <NAME> **<NAME> num |
| 119 | company_register_extract | `company_ownership_record` | # <NAME> register extract for <NAME>: officers **<NAME> ID:** REG-<N> **<NAME>:** <DATE> **<NAME> number:** <N |
| 119 | significant_control_register | `company_ownership_record` | # <NAME> of people with significant control for <NAME> **<NAME> ID:** PSC-<N> **<NAME>:** <DATE> / <NAME> / <N |
| 105 | company_register_extract | `company_ownership_record` | # <NAME> register extract for <NAME> **<NAME> ID:** REG-<N> **<NAME>:** <DATE> **<NAME> number:** <N> **<NAME> |
| 99 | support_chat | `loan_from_friend_claim` | # <NAME> with the customer **<NAME> ID:** CHT-<N> **<NAME>:** <DATE> **<NAME>:** <NAME>, we noticed some large |
| 84 | device_export | `shared_device_export` | # <NAME> and login export **<NAME> ID:** DEV-<N> **<NAME>:** <DATE> / <NAME> / <NAME> seen / <NAME> who logged |
| 83 | hospital_invoice | `medical_treatment_abroad` | # <NAME> from <NAME> **<NAME> ID:** INV-<N> **<NAME>:** <DATE> **<NAME>:** <NAME> **<NAME>:** <NAME> bypass su |
| 78 | support_chat | `mule_recruitment_chat` | # <NAME> with the customer **<NAME> ID:** CHT-<N> **<NAME>:** <DATE> **<NAME>:** <NAME>, a transfer from your  |
| 78 | support_chat | `family_support_abroad` | # <NAME> with the customer **<NAME> ID:** CHT-<N> **<NAME>:** <DATE> **<NAME>:** <NAME>, we are checking your  |
| 77 | consulting_contract | `business_contract` | # <NAME> contract with <NAME> **<NAME> ID:** CON-<N> **<NAME>:** <DATE> **<NAME>:** <NAME> **<NAME>:** <NAME>  |
| 63 | payment_file | `cash_collection_documented` | # <NAME> payment file **<NAME> ID:** PAY-<N> **<NAME>:** <DATE> / <NAME> / <NAME> / <NAME> / <NAME> / /---/--- |
| 50 | support_chat | `third_party_funds_held` | # <NAME> with the customer **<NAME> ID:** CHT-<N> **<NAME>:** <DATE> **<NAME>:** <NAME>, two payments came int |
| 50 | support_chat | `third_party_funds_held` | # <NAME> with the customer **<NAME> ID:** CHT-<N> **<NAME>:** <DATE> **<NAME>:** <NAME>, we are checking your  |
| 50 | support_chat | `third_party_funds_held` | # <NAME> with the customer **<NAME> ID:** CHT-<N> **<NAME>:** <DATE> **<NAME>:** <NAME>, we need to check your |
| 46 | advert | `asset_sale` | # <NAME> advert **<NAME> ID:** ADV-<N> **<NAME>:** <DATE> <NAME> road bike, size <N>, two years old, recently  |
| 46 | bank_statement | `own_account_statement` | # <NAME> from <NAME> SAL **<NAME> ID:** STM-<N> **<NAME>:** <DATE> **<NAME> holder:** <NAME> **<NAME>:** <NAME |
| 46 | completion_statement | `asset_sale` | # <NAME> statement from <NAME> LLP **<NAME> ID:** CMP-<N> **<NAME>:** <DATE> **<NAME>:** <NAME> **<NAME> sold: |
| 46 | customer_email | `holdings_sale` | # <NAME> from the customer **<NAME> ID:** EML-<N> **<NAME>:** <DATE> <NAME>: <NAME>: <NAME> to sell holdings < |
| 46 | takings_book | `cash_business_records` | # <NAME> takings book **<NAME> ID:** TAK-<N> **<NAME>:** <DATE> / <NAME> / <NAME> / <NAME> / <NAME> topped up  |
| 45 | bank_statement | `own_account_statement` | # <NAME> account statement from <NAME> **<NAME> ID:** STM-<N> **<NAME>:** <DATE> **<NAME> holders:** <NAME> an |
| 45 | credit_note | `refund` | # <NAME> note from <NAME> SAL **<NAME> ID:** CRN-<N> **<NAME>:** <DATE> **<NAME>:** <NAME> SAL, <NAME> **<NAME |
| 42 | supplier_invoices | `invoice_matches_payment` | # <NAME> from <NAME> **<NAME> ID:** INV-<N> **<NAME>:** <DATE> **<NAME>:** <NAME>, <NAME> **<NAME>:** <NAME> / |
| 42 | supplier_invoices | `invoice_matches_payment` | # <NAME> from <NAME> SARL **<NAME> ID:** INV-<N> **<NAME>:** <DATE> / <NAME> / <NAME> / <NAME> / /---/---/---/ |
| 39 | cash_collection_reports | `cash_collection_documented` | # <NAME> collection reports from <NAME> **<NAME> ID:** COL-<N> **<NAME>:** <DATE> <NAME> by two staff at each  |
| 39 | cash_handling_procedure | `cash_business_records` | # <NAME> handling procedure, <NAME> **<NAME> ID:** PRC-<N> **<NAME>:** <DATE> <NAME> car park: machines are em |
| 39 | vehicle_sale_receipt | `asset_sale` | # <NAME> vehicle sale receipt **<NAME> ID:** SAL-<N> **<NAME>:** <DATE> <NAME> from <NAME> the sum of <AMT> in |
| 38 | bank_statement | `own_account_statement` | # <NAME> from <NAME> PJSC **<NAME> ID:** STM-<N> **<NAME>:** <DATE> **<NAME> holder:** <NAME> **<NAME>:** <NAM |
| 38 | cash_reconciliation | `cash_business_records` | # <NAME> reconciliation sheets for <NAME> **<NAME> ID:** REC-<N> **<NAME>:** <DATE> <NAME> by two staff after  |
| 38 | ticket_report | `cash_business_records` | # <NAME> sales report for <NAME> **<NAME> ID:** TKT-<N> **<NAME>:** <DATE> <NAME> ran on <DATE> and <DATE>. <N |
| 37 | staff_note | `high_risk_routing_unexplained,structuring_enquiry` | # <NAME> from the client relationship team **<NAME> ID:** NTE-<N> **<NAME>:** <DATE> I spoke with the director |
| 36 | management_accounts | `cash_business_records` | # <NAME> accounts for the year to <DATE> **<NAME> ID:** ACC-<N> **<NAME>:** <DATE> **<NAME>:** <AMT> **<NAME>  |
| 36 | support_chat | `asset_sale` | # <NAME> with the customer **<NAME> ID:** CHT-<N> **<NAME>:** <DATE> **<NAME>:** <NAME>, I paid in some cash a |
| 35 | support_chat | `asset_sale` | # <NAME> with the customer **<NAME> ID:** CHT-<N> **<NAME>:** <DATE> **<NAME>:** <NAME> is my transfer pending |
| 35 | support_chat | `gift_from_relative` | # <NAME> with the customer **<NAME> ID:** CHT-<N> **<NAME>:** <DATE> **<NAME>:** <NAME>, thanks for paying in  |
| 34 | contract_schedule | `business_contract` | # <NAME> schedule, contract with <NAME> **<NAME> ID:** CON-<N> **<NAME>:** <DATE> **<NAME>:** <NAME> fit-out * |
| 34 | supplier_invoice | `invoice_matches_payment` | # <NAME> INV <N> from <NAME> **<NAME> ID:** INV-<N> **<NAME>:** <DATE> **<NAME>:** <NAME>, <NAME>, <NAME> **<N |
| 33 | support_chat | `loan_from_friend_claim,medical_treatment_abroad` | # <NAME> with the customer **<NAME> ID:** CHT-<N> **<NAME>:** <DATE> **<NAME>:** <NAME>, thank you for contact |
| 32 | loan_agreement | `loan_documented` | # <NAME> loan agreement with <NAME> **<NAME> ID:** LOA-<N> **<NAME>:** <DATE> **<NAME>** **<NAME>:** <NAME> ** |
| 29 | supplier_invoice | `invoice_matches_payment` | # <NAME> forma invoice from <NAME> **<NAME> ID:** INV-<N> **<NAME>:** <DATE> **<NAME>:** <NAME>, <NAME> **<NAM |
| 26 | insurer_letter | `insurance_settlement` | # <NAME> settlement letter from <NAME> plc **<NAME> ID:** INS-<N> **<NAME>:** <DATE> <NAME>, <NAME> are writin |
| 25 | venue_email | `refund` | # <NAME> from <NAME> and <NAME> **<NAME> ID:** EML-<N> **<NAME>:** <DATE> <NAME>, <NAME> were sorry to hear th |
| 24 | insurer_letter | `insurance_settlement` | # <NAME> settlement letter from <NAME> plc **<NAME> ID:** INS-<N> **<NAME>:** <DATE> <NAME> plc <NAME>, <NAME> |
| 22 | carrier_invoice | `invoice_matches_payment` | # <NAME> CARRIER <N> from <NAME> BV **<NAME> ID:** INV-<N> **<NAME>:** <DATE> **<NAME>:** <NAME> BV, <NAME> ** |
| 22 | freight_invoices | `invoice_matches_payment` | # <NAME> invoices issued by <NAME> **<NAME> ID:** INV-<N> **<NAME>:** <DATE> / <NAME> / <NAME> / <NAME> / /--- |
| 22 | group_structure | `company_ownership_record` | # <NAME> structure chart **<NAME> ID:** GRP-<N> **<NAME>:** <DATE> / <NAME> / <NAME> by / <NAME> / /---/---/-- |
| 22 | group_structure | `company_ownership_record` | # <NAME> structure chart **<NAME> ID:** GRP-<N> **<NAME>:** <DATE> / <NAME> / <NAME> / <NAME> / /---/---/---/  |
| 22 | remittance_advice | `cash_collection_documented` | # <NAME> advice from <NAME> **<NAME> ID:** RMT-<N> **<NAME>:** <DATE> **<NAME>:** <NAME> **<NAME> financed:**  |
| 21 | receipt | `purchase_receipt` | # <NAME> from <NAME> **<NAME> ID:** RCT-<N> **<NAME>:** <DATE> <NAME>: <NAME> - <NAME> <NAME> there, <NAME> em |
| 21 | supplier_invoice | `invoice_matches_payment` | # <NAME> INV <N> from <NAME> **<NAME> ID:** INV-<N> **<NAME>:** <DATE> **<NAME>:** <NAME>, <NAME> **<NAME>:**  |
| 20 | support_chat | `medical_treatment_abroad` | # <NAME> with the customer **<NAME> ID:** CHT-<N> **<NAME>:** <DATE> **<NAME>:** <NAME>, we are currently revi |
| 19 | customer_email | `erroneous_transfer_refund` | # <NAME> from the customer **<NAME> ID:** EML-<N> **<NAME>:** <DATE> <NAME>: <NAME>: <NAME> transfer to invest |
| 19 | purchase_order | `purchase_order_documented` | # <NAME> order from <NAME> **<NAME> ID:** ORD-<N> **<NAME>:** <DATE> <NAME>: <NAME> - PO <N> <NAME>, <NAME> ac |
| 18 | insurer_letter | `insurance_settlement` | # <NAME> settlement letter from <NAME> plc **<NAME> ID:** INS-<N> **<NAME>:** <DATE> <NAME> plc <NAME> are ple |
| 18 | supplier_invoice | `invoice_matches_payment` | # <NAME> for order PO <N> from <NAME> **<NAME> ID:** INV-<N> **<NAME>:** <DATE> **<NAME>:** <NAME>, <NAME>, th |
| 17 | deposit_return_letter | `refund` | # <NAME> return from <NAME> **<NAME> ID:** LET-<N> **<NAME>:** <DATE> <NAME>: <NAME> - <NAME> <NAME>, <NAME> t |
| 16 | gift_letter | `gift_from_relative` | # <NAME> letter from <NAME> **<NAME> ID:** GFT-<N> **<NAME>:** <DATE> I, <NAME>, hereby confirm that I am gift |
| 15 | venue_email | `refund` | # <NAME> from <NAME> and <NAME> **<NAME> ID:** EML-<N> **<NAME>:** <DATE> <NAME>: <NAME> - BOOKING <N> <NAME>, |
| 14 | cancellation_confirmation | `refund` | # <NAME> confirmation **<NAME> ID:** CAN-<N> **<NAME>:** <DATE> <NAME> cancelled your stocks and shares ISA wi |
| 14 | dealer_invoice | `asset_purchase` | # <NAME> INV <N> from <NAME> **<NAME> ID:** INV-<N> **<NAME>:** <DATE> **<NAME>:** <NAME> **<NAME>:** <N> SUV, |
| 14 | dealer_invoice | `asset_purchase` | # <NAME> INV <N> from <NAME> **<NAME> ID:** INV-<N> **<NAME>:** <DATE> **<NAME>:** <NAME> **<NAME>:** <N> esta |
| 14 | gift_letter | `gift_from_relative` | # <NAME> letter from <NAME> **<NAME> ID:** GFT-<N> **<NAME>:** <DATE> <NAME>, I, <NAME>, born <DATE>, am provi |
| 14 | sale_receipt | `asset_sale` | # <NAME> sale receipt **<NAME> ID:** SAL-<N> **<NAME>:** <DATE> **<NAME> of <NAME>** <NAME> document confirms  |
| 13 | gift_letter | `gift_from_relative` | # <NAME> letter from <NAME> **<NAME> ID:** GFT-<N> **<NAME>:** <DATE> <NAME> whom it may concern, I, <NAME>, b |
| 13 | insurer_letter | `insurance_settlement` | # <NAME> settlement letter from <NAME> plc **<NAME> ID:** INS-<N> **<NAME>:** <DATE> <NAME> plc <NAME> are wri |
| 13 | insurer_letter | `insurance_settlement` | # <NAME> settlement letter from <NAME> plc **<NAME> ID:** INS-<N> **<NAME>:** <DATE> <NAME>, <NAME> are please |
| 13 | settlement_letter | `employment_payout` | # <NAME> agreement letter from <NAME> **<NAME> ID:** SET-<N> **<NAME>:** <DATE> <NAME>/<NAME>, <NAME> the sett |
| 13 | support_chat | `medical_treatment_abroad` | # <NAME> with the customer **<NAME> ID:** CHT-<N> **<NAME>:** <DATE> **<NAME>:** <NAME>, we are currently revi |
| 12 | gift_letter | `gift_from_relative` | # <NAME> letter from <NAME> **<NAME> ID:** GFT-<N> **<NAME>:** <DATE> I, <NAME>, confirm that I am gifting the |
| 12 | insurance_schedule | `purchase_receipt` | # <NAME> insurance schedule **<NAME> ID:** INS-<N> **<NAME>:** <DATE> **<NAME>:** <NAME> **<NAME>:** <N> SUV,  |
| 12 | insurance_schedule | `purchase_receipt` | # <NAME> insurance schedule **<NAME> ID:** INS-<N> **<NAME>:** <DATE> **<NAME>:** <NAME> **<NAME>:** <N> hatch |
| 12 | receipt | `purchase_receipt` | # <NAME> from <NAME> **<NAME> ID:** RCT-<N> **<NAME>:** <DATE> <NAME>: <NAME> - <NAME> <NAME> there, <NAME> fo |
| 12 | receipt | `purchase_receipt` | # <NAME> from <NAME> **<NAME> ID:** RCT-<N> **<NAME>:** <DATE> <NAME>: <NAME> for your order - <NAME> <NAME> t |
| 11 | customer_letter | `own_account_instruction` | # <NAME> from the customer **<NAME> ID:** LTR-<N> **<NAME>:** <DATE> <NAME>, I am writing to inform you that I |
| 11 | employment_contract | `business_contract` | # <NAME> contract **<NAME> ID:** EMP-<N> **<NAME>:** <DATE> <NAME> has entered into an employment agreement wi |
| 11 | gift_letter | `gift_from_relative` | # <NAME> letter from <NAME> **<NAME> ID:** GFT-<N> **<NAME>:** <DATE> <NAME>, I, <NAME>, born <DATE>, am writi |
| 11 | gift_letter | `gift_from_relative` | # <NAME> letter from <NAME> **<NAME> ID:** GFT-<N> **<NAME>:** <DATE> <NAME>, I, <NAME>, born <DATE>, am writi |
| 11 | insurance_schedule | `purchase_receipt` | # <NAME> insurance schedule **<NAME> ID:** INS-<N> **<NAME>:** <DATE> **<NAME>:** <NAME> **<NAME>:** <N> saloo |
| 11 | insurer_letter | `insurance_settlement` | # <NAME> settlement letter from <NAME> plc **<NAME> ID:** INS-<N> **<NAME>:** <DATE> <NAME> plc <NAME>, <NAME> |
| 11 | settlement_letter | `employment_payout` | # <NAME> agreement letter from <NAME> **<NAME> ID:** SET-<N> **<NAME>:** <DATE> <NAME>/<NAME>, <NAME> to the s |
| 11 | staff_note | `structuring_enquiry` | # <NAME> by <NAME>, <NAME> branch **<NAME> ID:** NTE-<N> **<NAME>:** <DATE> <NAME> visited the branch today to |
| 11 | staff_note | `high_risk_routing_unexplained,structuring_enquiry` | # <NAME> from the client relationship team **<NAME> ID:** NTE-<N> **<NAME>:** <DATE> <NAME> with the director  |
| 11 | support_chat | `loan_from_friend_claim,medical_treatment_abroad` | # <NAME> with the customer **<NAME> ID:** CHT-<N> **<NAME>:** <DATE> **<NAME>:** <NAME>, thank you for reachin |
| 10 | dealer_invoice | `asset_purchase` | # <NAME> INV <N> from <NAME> **<NAME> ID:** INV-<N> **<NAME>:** <DATE> **<NAME>:** <NAME> **<NAME>:** <N> hatc |
| 9 | cancellation_confirmation | `refund` | # <NAME> confirmation **<NAME> ID:** CAN-<N> **<NAME>:** <DATE> <NAME>: <NAME> of your ISA cancellation <NAME> |
| 9 | gift_letter | `gift_from_relative` | # <NAME> letter from <NAME> **<NAME> ID:** GFT-<N> **<NAME>:** <DATE> I, <NAME>, born <DATE>, hereby confirm t |
| 9 | insurer_letter | `insurance_settlement` | # <NAME> settlement letter from <NAME> plc **<NAME> ID:** INS-<N> **<NAME>:** <DATE> <NAME>, <NAME> are writin |
| 9 | receipt | `purchase_receipt` | # <NAME> from <NAME> **<NAME> ID:** RCT-<N> **<NAME>:** <DATE> <NAME>: <NAME>: <NAME> <NAME> there, <NAME> for |
| 9 | redundancy_letter | `employment_payout` | # <NAME> from <NAME> plc **<NAME> ID:** RED-<N> **<NAME>:** <DATE> <NAME> plc <NAME>, <NAME> are writing to fo |
| 9 | solicitor_letter | `inheritance` | # <NAME> from <NAME> LLP **<NAME> ID:** SOL-<N> **<NAME>:** <DATE> <NAME>/<NAME>, <NAME> are writing to you in |
| 9 | staff_note | `structuring_enquiry` | # <NAME> from the client relationship team **<NAME> ID:** NTE-<N> **<NAME>:** <DATE> I received a call today f |
| 9 | supply_contract | `business_contract` | # <NAME> contract with <NAME> **<NAME> ID:** CON-<N> **<NAME>:** <DATE> <NAME> supply agreement confirms that  |
| 9 | support_chat | `cash_withdrawal_returned` | # <NAME> with the customer **<NAME> ID:** CHT-<N> **<NAME>:** <DATE> **<NAME>:** <NAME> there, I’ve just depos |
| 8 | customer_letter | `own_account_instruction` | # <NAME> from the customer **<NAME> ID:** LTR-<N> **<NAME>:** <DATE> <NAME> whom it may concern, I am writing  |
| 8 | customer_letter | `own_account_instruction` | # <NAME> from the customer **<NAME> ID:** LTR-<N> **<NAME>:** <DATE> <NAME>, I am writing to notify you that I |
| 8 | gift_letter | `gift_from_relative` | # <NAME> letter from <NAME> **<NAME> ID:** GFT-<N> **<NAME>:** <DATE> I, <NAME>, born <DATE>, confirm that I a |
| 8 | holding_deposit_receipt | `refund` | # <NAME> deposit receipt from <NAME> **<NAME> ID:** LET-<N> **<NAME>:** <DATE> <NAME>: <NAME> deposit confirma |
| 8 | insurer_letter | `insurance_settlement` | # <NAME> settlement letter from <NAME> plc **<NAME> ID:** INS-<N> **<NAME>:** <DATE> <NAME> plc <NAME> your re |
| 8 | invoice | `invoice_matches_payment` | # <NAME> <N> from <NAME> FZE **<NAME> ID:** INV-<N> **<NAME>:** <DATE> **<NAME> to:** <NAME> **<NAME>:** machi |
| 8 | receipt | `purchase_receipt` | # <NAME> from <NAME> **<NAME> ID:** RCT-<N> **<NAME>:** <DATE> <NAME> for booking your spot on our four-week s |
| 8 | redundancy_letter | `employment_payout` | # <NAME> from <NAME> **<NAME> ID:** RED-<N> **<NAME>:** <DATE> <NAME> <NAME>, <NAME> are writing to formally c |
| 8 | supply_contract | `business_contract` | # <NAME> contract with <NAME> **<NAME> ID:** CON-<N> **<NAME>:** <DATE> <NAME> agreement confirms that <NAME>, |
| 8 | venue_email | `refund` | # <NAME> from <NAME> and <NAME> **<NAME> ID:** EML-<N> **<NAME>:** <DATE> <NAME>, <NAME> are writing to formal |
| 7 | holding_deposit_receipt | `refund` | # <NAME> deposit receipt from <NAME> **<NAME> ID:** LET-<N> **<NAME>:** <DATE> <NAME>: <NAME> deposit received |
| 7 | holding_deposit_receipt | `refund` | # <NAME> deposit receipt from <NAME> **<NAME> ID:** LET-<N> **<NAME>:** <DATE> <NAME>: <NAME> for your holding |
| 7 | invoice | `invoice_matches_payment` | # <NAME> <N> from <NAME> FZE **<NAME> ID:** INV-<N> **<NAME>:** <DATE> **<NAME> to:** <NAME> **<NAME>:** furni |
| 7 | invoice | `invoice_matches_payment` | # <NAME> RA/<N> from <NAME> **<NAME> ID:** INV-<N> **<NAME>:** <DATE> **<NAME> to:** <NAME> **<NAME>:** <NAME> |
| 7 | receipt | `purchase_receipt` | # <NAME> from <NAME> **<NAME> ID:** RCT-<N> **<NAME>:** <DATE> <NAME>: <NAME>: <NAME> <NAME> there, <NAME> ema |
| 7 | solicitor_letter | `inheritance` | # <NAME> from <NAME> LLP **<NAME> ID:** SOL-<N> **<NAME>:** <DATE> <NAME>, <NAME> are writing to you in our ca |
| 7 | staff_note | `high_risk_routing_unexplained` | # <NAME> from the client relationship team **<NAME> ID:** NTE-<N> **<NAME>:** <DATE> I spoke with <NAME> today |
| 6 | factoring_agreement | `business_contract` | # <NAME> finance agreement with <NAME> **<NAME> ID:** FAC-<N> **<NAME>:** <DATE> <NAME> the terms of the agree |
| 6 | gift_letter | `gift_from_relative` | # <NAME> letter from <NAME> **<NAME> ID:** GFT-<N> **<NAME>:** <DATE> <NAME>, I, <NAME>, born <DATE>, confirm  |
| 6 | gift_letter | `gift_from_relative` | # <NAME> letter from <NAME> **<NAME> ID:** GFT-<N> **<NAME>:** <DATE> I, <NAME>, born <DATE>, hereby confirm t |
| 6 | holding_deposit_receipt | `refund` | # <NAME> deposit receipt from <NAME> **<NAME> ID:** LET-<N> **<NAME>:** <DATE> <NAME>: <NAME> deposit receipt  |
| 6 | holding_deposit_receipt | `refund` | # <NAME> deposit receipt from <NAME> **<NAME> ID:** LET-<N> **<NAME>:** <DATE> <NAME>: <NAME> of <NAME> - <NAM |
| 6 | insurer_letter | `insurance_settlement` | # <NAME> settlement letter from <NAME> plc **<NAME> ID:** INS-<N> **<NAME>:** <DATE> <NAME>, <NAME> are please |
| 6 | invoice | `invoice_matches_payment` | # <NAME> <N> from <NAME> FZE **<NAME> ID:** INV-<N> **<NAME>:** <DATE> **<NAME> to:** <NAME> **<NAME>:** fresh |
| 6 | purchase_order | `purchase_order_documented` | # <NAME> order from <NAME> **<NAME> ID:** ORD-<N> **<NAME>:** <DATE> <NAME>: <NAME>: PO <N> <NAME>, <NAME> acc |
| 6 | staff_note | `structuring_enquiry` | # <NAME> by <NAME>, <NAME> branch **<NAME> ID:** NTE-<N> **<NAME>:** <DATE> <NAME> attended the branch today t |
| 6 | staff_note | `structuring_enquiry` | # <NAME> by <NAME>, <NAME> branch **<NAME> ID:** NTE-<N> **<NAME>:** <DATE> <NAME> with <NAME> today regarding |
| 6 | venue_email | `refund` | # <NAME> from <NAME> and <NAME> **<NAME> ID:** EML-<N> **<NAME>:** <DATE> <NAME>: <NAME> - BOOKING <N> <NAME>, |
| 5 | deposit_return_letter | `refund` | # <NAME> return from <NAME> **<NAME> ID:** LET-<N> **<NAME>:** <DATE> <NAME>, <NAME> the conclusion of your te |
| 5 | deposit_return_letter | `refund` | # <NAME> return from <NAME> **<NAME> ID:** LET-<N> **<NAME>:** <DATE> <NAME>: <NAME> return - <NAME> <NAME>, < |
| 5 | employment_contract | `business_contract` | # <NAME> contract **<NAME> ID:** EMP-<N> **<NAME>:** <DATE> <NAME> has entered into a two-year employment agre |
| 5 | gift_letter | `gift_from_relative` | # <NAME> letter from <NAME> **<NAME> ID:** GFT-<N> **<NAME>:** <DATE> <NAME>, I, <NAME>, am writing to formall |
| 5 | gift_letter | `gift_from_relative` | # <NAME> letter from <NAME> **<NAME> ID:** GFT-<N> **<NAME>:** <DATE> <NAME>, I, <NAME>, confirm that I am gif |
| 5 | invoice | `invoice_matches_payment` | # <NAME> HA/<N> from <NAME> **<NAME> ID:** INV-<N> **<NAME>:** <DATE> **<NAME> to:** <NAME> **<NAME>:** <NAME> |
| 5 | receipt | `purchase_receipt` | # <NAME> from <NAME> **<NAME> ID:** RCT-<N> **<NAME>:** <DATE> <NAME> there, <NAME> for choosing <NAME>. <NAME |
| 5 | receipt | `purchase_receipt` | # <NAME> from <NAME> **<NAME> ID:** RCT-<N> **<NAME>:** <DATE> <NAME>: <NAME> confirmation - <NAME> <NAME> the |
| 5 | sale_receipt | `asset_sale` | # <NAME> sale receipt **<NAME> ID:** SAL-<N> **<NAME>:** <DATE> **<NAME>** I, <NAME>, have this day sold one c |
| 5 | solicitor_letter | `inheritance` | # <NAME> from <NAME> LLP **<NAME> ID:** SOL-<N> **<NAME>:** <DATE> <NAME> firm acts on behalf of the executors |
| 5 | staff_note | `structuring_enquiry` | # <NAME> by <NAME> report, <NAME> office, <NAME> **<NAME> ID:** NTE-<N> **<NAME>:** <DATE> <NAME> visited the  |
| 5 | supply_contract | `business_contract` | # <NAME> contract with <NAME> **<NAME> ID:** CON-<N> **<NAME>:** <DATE> <NAME> supply agreement establishes th |
| 5 | support_chat | `cash_withdrawal_returned` | # <NAME> with the customer **<NAME> ID:** CHT-<N> **<NAME>:** <DATE> **<NAME>:** <NAME>, I paid the cash back  |
| 5 | support_chat | `cash_withdrawal_returned` | # <NAME> with the customer **<NAME> ID:** CHT-<N> **<NAME>:** <DATE> **<NAME>:** <NAME>, I’ve just deposited t |
| 4 | cancellation_confirmation | `refund` | # <NAME> confirmation **<NAME> ID:** CAN-<N> **<NAME>:** <DATE> <NAME>, <NAME> are writing to confirm that you |
| 4 | customer_email | `erroneous_transfer_refund` | # <NAME> from the customer **<NAME> ID:** EML-<N> **<NAME>:** <DATE> <NAME> there, I’ve accidentally transferr |
| 4 | customer_letter | `own_account_instruction` | # <NAME> from the customer **<NAME> ID:** LTR-<N> **<NAME>:** <DATE> <NAME>, I am writing to notify you that I |
| 4 | employment_contract | `business_contract` | # <NAME> contract **<NAME> ID:** EMP-<N> **<NAME>:** <DATE> **<NAME>** <NAME> has entered into an agreement wi |
| 4 | factoring_agreement | `business_contract` | # <NAME> finance agreement with <NAME> **<NAME> ID:** FAC-<N> **<NAME>:** <DATE> <NAME> the terms of this faci |
| 4 | gift_letter | `gift_from_relative` | # <NAME> letter from <NAME> **<NAME> ID:** GFT-<N> **<NAME>:** <DATE> I, <NAME>, born <DATE>, am writing to co |
| 4 | gift_letter | `gift_from_relative` | # <NAME> letter from <NAME> **<NAME> ID:** GFT-<N> **<NAME>:** <DATE> I, <NAME>, born <DATE>, confirm that I a |
| 4 | holding_deposit_receipt | `refund` | # <NAME> deposit receipt from <NAME> **<NAME> ID:** LET-<N> **<NAME>:** <DATE> <NAME>: <NAME> - <NAME> <NAME>, |
| 4 | insurance_schedule | `purchase_receipt` | # <NAME> insurance schedule **<NAME> ID:** INS-<N> **<NAME>:** <DATE> **<NAME>:** <NAME> **<NAME>:** <N> estat |
| 4 | invoice | `invoice_matches_payment` | # <NAME> <N> from <NAME> FZE **<NAME> ID:** INV-<N> **<NAME>:** <DATE> **<NAME> to:** <NAME> **<NAME>:** cater |
| 4 | invoice | `invoice_matches_payment` | # <NAME> <N> from <NAME> FZE **<NAME> ID:** INV-<N> **<NAME>:** <DATE> **<NAME> to:** <NAME> **<NAME>:** food  |
| 4 | invoice | `invoice_matches_payment` | # <NAME> <N> from <NAME> FZE **<NAME> ID:** INV-<N> **<NAME>:** <DATE> **<NAME> to:** <NAME> **<NAME>:** timbe |
| 4 | invoice | `invoice_matches_payment` | # <NAME> <N> from <NAME> FZE **<NAME> ID:** INV-<N> **<NAME>:** <DATE> **<NAME> to:** <NAME> **<NAME>:** wine, |
| 4 | invoice | `invoice_matches_payment` | # <NAME> BR/<N> from <NAME> **<NAME> ID:** INV-<N> **<NAME>:** <DATE> **<NAME> to:** <NAME> **<NAME>:** <NAME> |
| 4 | invoice | `invoice_matches_payment` | # <NAME> DR/<N> from <NAME> **<NAME> ID:** INV-<N> **<NAME>:** <DATE> **<NAME> to:** <NAME> **<NAME>:** <NAME> |
| 4 | invoice | `invoice_matches_payment` | # <NAME> EV/<N> from <NAME> **<NAME> ID:** INV-<N> **<NAME>:** <DATE> **<NAME> to:** <NAME> **<NAME>:** <NAME> |
| 4 | invoice | `invoice_matches_payment` | # <NAME> HO/<N> from <NAME> **<NAME> ID:** INV-<N> **<NAME>:** <DATE> **<NAME> to:** <NAME> **<NAME>:** <NAME> |
| 4 | invoice | `invoice_matches_payment` | # <NAME> HO/<N> from <NAME> **<NAME> ID:** INV-<N> **<NAME>:** <DATE> **<NAME> to:** <NAME> **<NAME>:** <NAME> |
| 4 | invoice | `invoice_matches_payment` | # <NAME> NO/<N> from <NAME> **<NAME> ID:** INV-<N> **<NAME>:** <DATE> **<NAME> to:** <NAME> **<NAME>:** <NAME> |
| 4 | loan_agreement | `loan_documented` | # <NAME> loan agreement with <NAME> **<NAME> ID:** LOA-<N> **<NAME>:** <DATE> ### <NAME> **<NAME>:** <NAME> ** |
| 4 | receipt | `purchase_receipt` | # <NAME> from <NAME> **<NAME> ID:** RCT-<N> **<NAME>:** <DATE> <NAME>: <NAME> - <NAME> <NAME> there, <NAME> fo |
| 4 | sale_receipt | `asset_sale` | # <NAME> sale receipt **<NAME> ID:** SAL-<N> **<NAME>:** <DATE> **<NAME> of <NAME>** <NAME>: <NAME> road bike  |
| 4 | sale_receipt | `asset_sale` | # <NAME> sale receipt **<NAME> ID:** SAL-<N> **<NAME>:** <DATE> **<NAME>** I, <NAME>, have today sold one carb |
| 4 | settlement_letter | `employment_payout` | # <NAME> agreement letter from <NAME> **<NAME> ID:** SET-<N> **<NAME>:** <DATE> <NAME> to the settlement agree |
| 4 | staff_note | `high_risk_routing_unexplained` | # <NAME> from the client relationship team **<NAME> ID:** NTE-<N> **<NAME>:** <DATE> I spoke with a representa |
| 4 | supplier_invoice | `invoice_matches_payment` | # <NAME> forma invoice from <NAME>. z o.o. **<NAME> ID:** INV-<N> **<NAME>:** <DATE> **<NAME>:** <NAME>. z o.o |
| 4 | support_chat | `medical_treatment_abroad` | # <NAME> with the customer **<NAME> ID:** CHT-<N> **<NAME>:** <DATE> **<NAME>:** <NAME> you for contacting our |
| 4 | support_chat | `cash_withdrawal_returned` | # <NAME> with the customer **<NAME> ID:** CHT-<N> **<NAME>:** <DATE> **<NAME>:** <NAME>, I just dropped that c |
| 4 | support_chat | `cash_withdrawal_returned` | # <NAME> with the customer **<NAME> ID:** CHT-<N> **<NAME>:** <DATE> **<NAME>:** <NAME>, I just wanted to upda |
| 4 | support_chat | `cash_withdrawal_returned` | # <NAME> with the customer **<NAME> ID:** CHT-<N> **<NAME>:** <DATE> **<NAME>:** <NAME>, I've just deposited t |
| 4 | venue_email | `refund` | # <NAME> from <NAME> and <NAME> **<NAME> ID:** EML-<N> **<NAME>:** <DATE> <NAME>, <NAME> are writing to formal |
| 3 | cancellation_confirmation | `refund` | # <NAME> confirmation **<NAME> ID:** CAN-<N> **<NAME>:** <DATE> <NAME>: <NAME> confirmation for your stocks an |
| 3 | customer_email | `erroneous_transfer_refund` | # <NAME> from the customer **<NAME> ID:** EML-<N> **<NAME>:** <DATE> <NAME> there, I’ve made a mistake and acc |
| 3 | deposit_return_letter | `refund` | # <NAME> return from <NAME> **<NAME> ID:** LET-<N> **<NAME>:** <DATE> <NAME>: <NAME> regarding your tenancy de |
| 3 | email | `group_funds_pass_through` | # <NAME> from <NAME> **<NAME> ID:** EML-<N> **<NAME>:** <DATE> <NAME>: <NAME> supplier payment <NAME> team, I’ |
| 3 | employment_contract | `business_contract` | # <NAME> contract **<NAME> ID:** EMP-<N> **<NAME>:** <DATE> **<NAME>** <NAME> has entered into a two-year empl |
| 3 | employment_contract | `business_contract` | # <NAME> contract **<NAME> ID:** EMP-<N> **<NAME>:** <DATE> <NAME> summary outlines the employment terms for < |
| 3 | factoring_agreement | `business_contract` | # <NAME> finance agreement with <NAME> **<NAME> ID:** FAC-<N> **<NAME>:** <DATE> <NAME> the terms of the agree |
| 3 | factoring_agreement | `business_contract` | # <NAME> finance agreement with <NAME> **<NAME> ID:** FAC-<N> **<NAME>:** <DATE> <NAME> the terms of this agre |
| 3 | gift_letter | `gift_from_relative` | # <NAME> letter from <NAME> **<NAME> ID:** GFT-<N> **<NAME>:** <DATE> <NAME> whom it may concern, I, <NAME>, a |
| 3 | gift_letter | `gift_from_relative` | # <NAME> letter from <NAME> **<NAME> ID:** GFT-<N> **<NAME>:** <DATE> I, <NAME>, born <DATE>, am providing a g |
| 3 | insurer_letter | `insurance_settlement` | # <NAME> settlement letter from <NAME> plc **<NAME> ID:** INS-<N> **<NAME>:** <DATE> <NAME> plc <NAME>/<NAME>, |
| 3 | insurer_letter | `insurance_settlement` | # <NAME> settlement letter from <NAME> plc **<NAME> ID:** INS-<N> **<NAME>:** <DATE> <NAME> plc <NAME>: CLAIM  |
| 3 | invoice | `invoice_matches_payment` | # <NAME> <N> from <NAME> FZE **<NAME> ID:** INV-<N> **<NAME>:** <DATE> **<NAME> to:** <NAME> **<NAME>:** cloth |
| 3 | invoice | `invoice_matches_payment` | # <NAME> EL/<N> from <NAME> **<NAME> ID:** INV-<N> **<NAME>:** <DATE> **<NAME> to:** <NAME> **<NAME>:** <NAME> |
| 3 | invoice | `invoice_matches_payment` | # <NAME> EL/<N> from <NAME> **<NAME> ID:** INV-<N> **<NAME>:** <DATE> **<NAME> to:** <NAME> **<NAME>:** <NAME> |
| 3 | invoice | `invoice_matches_payment` | # <NAME> HA/<N> from <NAME> **<NAME> ID:** INV-<N> **<NAME>:** <DATE> **<NAME> to:** <NAME> **<NAME>:** <NAME> |
| 3 | invoice | `invoice_matches_payment` | # <NAME> LA/<N> from <NAME> **<NAME> ID:** INV-<N> **<NAME>:** <DATE> **<NAME> to:** <NAME> **<NAME>:** <NAME> |
| 3 | invoice | `invoice_matches_payment` | # <NAME> MA/<N> from <NAME> **<NAME> ID:** INV-<N> **<NAME>:** <DATE> **<NAME> to:** <NAME> **<NAME>:** <NAME> |
| 3 | invoice | `invoice_matches_payment` | # <NAME> MI/<N> from <NAME> **<NAME> ID:** INV-<N> **<NAME>:** <DATE> **<NAME> to:** <NAME> **<NAME>:** <NAME> |
| 3 | invoice | `invoice_matches_payment` | # <NAME> WI/<N> from <NAME> **<NAME> ID:** INV-<N> **<NAME>:** <DATE> **<NAME> to:** <NAME> **<NAME>:** <NAME> |
| 3 | purchase_order | `purchase_order_documented` | # <NAME> order from <NAME> **<NAME> ID:** ORD-<N> **<NAME>:** <DATE> <NAME>: <NAME> - PO <N> <NAME> team, <NAM |
| 3 | redundancy_letter | `employment_payout` | # <NAME> from <NAME> **<NAME> ID:** RED-<N> **<NAME>:** <DATE> **<NAME>** <NAME>, <NAME> are writing to formal |
| 3 | redundancy_letter | `employment_payout` | # <NAME> from <NAME> **<NAME> ID:** RED-<N> **<NAME>:** <DATE> <NAME> <NAME>, <NAME> accept this letter as for |
| 3 | sale_receipt | `asset_sale` | # <NAME> sale receipt **<NAME> ID:** SAL-<N> **<NAME>:** <DATE> **<NAME> of <NAME>** <NAME>: <NAME> road bike, |
| 3 | settlement_letter | `employment_payout` | # <NAME> agreement letter from <NAME> **<NAME> ID:** SET-<N> **<NAME>:** <DATE> <NAME>/<NAME>, <NAME> letter s |
| 3 | settlement_letter | `employment_payout` | # <NAME> agreement letter from <NAME> **<NAME> ID:** SET-<N> **<NAME>:** <DATE> <NAME>/<NAME>, <NAME> the exec |
| 3 | solicitor_letter | `inheritance` | # <NAME> from <NAME> LLP **<NAME> ID:** SOL-<N> **<NAME>:** <DATE> <NAME> LLP <NAME>, <NAME> are writing to yo |
| 3 | staff_note | `structuring_enquiry` | # <NAME> by <NAME> report, <NAME> office, <NAME> **<NAME> ID:** NTE-<N> **<NAME>:** <DATE> <NAME> came into th |
| 3 | staff_note | `high_risk_routing_unexplained` | # <NAME> from the client relationship team **<NAME> ID:** NTE-<N> **<NAME>:** <DATE> <NAME> with the director  |
| 3 | staff_note | `high_risk_routing_unexplained` | # <NAME> from the client relationship team **<NAME> ID:** NTE-<N> **<NAME>:** <DATE> I spoke with the director |
| 3 | supplier_invoice | `invoice_matches_payment` | # <NAME> for order PO <N> from <NAME>. z o.o. **<NAME> ID:** INV-<N> **<NAME>:** <DATE> **<NAME>:** <NAME>. z  |
| 3 | support_chat | `loan_from_friend_claim` | # <NAME> with the customer **<NAME> ID:** CHT-<N> **<NAME>:** <DATE> **<NAME>:** <NAME> there, I’m reaching ou |
| 3 | support_chat | `loan_from_friend_claim` | # <NAME> with the customer **<NAME> ID:** CHT-<N> **<NAME>:** <DATE> **<NAME>:** <NAME> there. I'm reaching ou |
| 3 | support_chat | `cash_withdrawal_returned` | # <NAME> with the customer **<NAME> ID:** CHT-<N> **<NAME>:** <DATE> **<NAME>:** <NAME>, I just wanted to let  |
| 3 | support_chat | `medical_treatment_abroad` | # <NAME> with the customer **<NAME> ID:** CHT-<N> **<NAME>:** <DATE> **<NAME>:** <NAME>, thank you for contact |
| 3 | venue_email | `refund` | # <NAME> from <NAME> and <NAME> **<NAME> ID:** EML-<N> **<NAME>:** <DATE> <NAME>, <NAME> are writing to confir |
| 3 | venue_email | `refund` | # <NAME> from <NAME> and <NAME> **<NAME> ID:** EML-<N> **<NAME>:** <DATE> <NAME>: <NAME> regarding your cancel |
| 2 | cancellation_confirmation | `refund` | # <NAME> confirmation **<NAME> ID:** CAN-<N> **<NAME>:** <DATE> <NAME> are writing to confirm that your reques |
| 2 | cancellation_confirmation | `refund` | # <NAME> confirmation **<NAME> ID:** CAN-<N> **<NAME>:** <DATE> <NAME>: <NAME> of your ISA cancellation reques |
| 2 | cancellation_confirmation | `refund` | # <NAME> confirmation **<NAME> ID:** CAN-<N> **<NAME>:** <DATE> <NAME>: <NAME> of your cancellation request <N |
| 2 | cancellation_confirmation | `refund` | # <NAME> confirmation **<NAME> ID:** CAN-<N> **<NAME>:** <DATE> <NAME>: <NAME> regarding your ISA cancellation |
| 2 | customer_email | `erroneous_transfer_refund` | # <NAME> from the customer **<NAME> ID:** EML-<N> **<NAME>:** <DATE> <NAME> team, I’ve made a mistake and tran |
| 2 | customer_email | `erroneous_transfer_refund` | # <NAME> from the customer **<NAME> ID:** EML-<N> **<NAME>:** <DATE> <NAME> there, I accidentally transferred  |
| 2 | customer_email | `erroneous_transfer_refund` | # <NAME> from the customer **<NAME> ID:** EML-<N> **<NAME>:** <DATE> <NAME>, I’ve made a mistake and accidenta |
| 2 | customer_letter | `own_account_instruction` | # <NAME> from the customer **<NAME> ID:** LTR-<N> **<NAME>:** <DATE> <NAME>, I am writing to formally notify y |
| 2 | customer_letter | `own_account_instruction` | # <NAME> from the customer **<NAME> ID:** LTR-<N> **<NAME>:** <DATE> <NAME>, I am writing to inform you that I |
| 2 | customer_letter | `own_account_instruction` | # <NAME> from the customer **<NAME> ID:** LTR-<N> **<NAME>:** <DATE> <NAME>, I am writing to notify you that I |
| 2 | deposit_return_letter | `refund` | # <NAME> return from <NAME> **<NAME> ID:** LET-<N> **<NAME>:** <DATE> <NAME>, <NAME> the conclusion of your te |
| 2 | deposit_return_letter | `refund` | # <NAME> return from <NAME> **<NAME> ID:** LET-<N> **<NAME>:** <DATE> <NAME>: <NAME> - <NAME> <NAME>, <NAME> a |
| 2 | deposit_return_letter | `refund` | # <NAME> return from <NAME> **<NAME> ID:** LET-<N> **<NAME>:** <DATE> <NAME>: <NAME> of your tenancy deposit < |
| 2 | deposit_return_letter | `refund` | # <NAME> return from <NAME> **<NAME> ID:** LET-<N> **<NAME>:** <DATE> <NAME>: <NAME> return from <NAME> <NAME> |
| 2 | employment_contract | `business_contract` | # <NAME> contract **<NAME> ID:** EMP-<N> **<NAME>:** <DATE> **<NAME>** <NAME> serves as a petroleum engineer f |
| 2 | employment_contract | `business_contract` | # <NAME> contract **<NAME> ID:** EMP-<N> **<NAME>:** <DATE> <NAME> has engaged <NAME> to serve as a petroleum  |
| 2 | factoring_agreement | `business_contract` | # <NAME> finance agreement with <NAME> **<NAME> ID:** FAC-<N> **<NAME>:** <DATE> <NAME> this agreement, <NAME> |
| 2 | gift_letter | `gift_from_relative` | # <NAME> letter from <NAME> **<NAME> ID:** GFT-<N> **<NAME>:** <DATE> <NAME>, I, <NAME>, born <DATE>, hereby c |
| 2 | insurer_letter | `insurance_settlement` | # <NAME> settlement letter from <NAME> plc **<NAME> ID:** INS-<N> **<NAME>:** <DATE> **<NAME> plc** <NAME> you |
| 2 | insurer_letter | `insurance_settlement` | # <NAME> settlement letter from <NAME> plc **<NAME> ID:** INS-<N> **<NAME>:** <DATE> **<NAME> plc** <NAME>, <N |
| 2 | insurer_letter | `insurance_settlement` | # <NAME> settlement letter from <NAME> plc **<NAME> ID:** INS-<N> **<NAME>:** <DATE> **<NAME> plc** <NAME>, <N |
| 2 | insurer_letter | `insurance_settlement` | # <NAME> settlement letter from <NAME> plc **<NAME> ID:** INS-<N> **<NAME>:** <DATE> <NAME>/<NAME>, <NAME> you |
| 2 | invoice | `invoice_matches_payment` | # <NAME> <N> from <NAME> FZE **<NAME> ID:** INV-<N> **<NAME>:** <DATE> **<NAME> to:** <NAME> **<NAME>:** elect |
| 2 | invoice | `invoice_matches_payment` | # <NAME> AL/<N> from <NAME> **<NAME> ID:** INV-<N> **<NAME>:** <DATE> **<NAME> to:** <NAME> **<NAME>:** <NAME> |
| 2 | invoice | `invoice_matches_payment` | # <NAME> CA/<N> from <NAME> **<NAME> ID:** INV-<N> **<NAME>:** <DATE> **<NAME> to:** <NAME> **<NAME>:** <NAME> |
| 2 | invoice | `invoice_matches_payment` | # <NAME> CR/<N> from <NAME> **<NAME> ID:** INV-<N> **<NAME>:** <DATE> **<NAME> to:** <NAME> **<NAME>:** <NAME> |
| 2 | invoice | `invoice_matches_payment` | # <NAME> CR/<N> from <NAME> **<NAME> ID:** INV-<N> **<NAME>:** <DATE> **<NAME> to:** <NAME> **<NAME>:** <NAME> |
| 2 | invoice | `invoice_matches_payment` | # <NAME> DU/<N> from <NAME> **<NAME> ID:** INV-<N> **<NAME>:** <DATE> **<NAME> to:** <NAME> **<NAME>:** <NAME> |
| 2 | invoice | `invoice_matches_payment` | # <NAME> DU/<N> from <NAME> **<NAME> ID:** INV-<N> **<NAME>:** <DATE> **<NAME> to:** <NAME> **<NAME>:** <NAME> |
| 2 | invoice | `invoice_matches_payment` | # <NAME> EV/<N> from <NAME> **<NAME> ID:** INV-<N> **<NAME>:** <DATE> **<NAME> to:** <NAME> **<NAME>:** <NAME> |
| 2 | invoice | `invoice_matches_payment` | # <NAME> FA/<N> from <NAME> **<NAME> ID:** INV-<N> **<NAME>:** <DATE> **<NAME> to:** <NAME> **<NAME>:** <NAME> |
| 2 | invoice | `invoice_matches_payment` | # <NAME> FA/<N> from <NAME> **<NAME> ID:** INV-<N> **<NAME>:** <DATE> **<NAME> to:** <NAME> **<NAME>:** <NAME> |
| 2 | invoice | `invoice_matches_payment` | # <NAME> GL/<N> from <NAME> **<NAME> ID:** INV-<N> **<NAME>:** <DATE> **<NAME> to:** <NAME> **<NAME>:** <NAME> |
| 2 | invoice | `invoice_matches_payment` | # <NAME> KE/<N> from <NAME> **<NAME> ID:** INV-<N> **<NAME>:** <DATE> **<NAME> to:** <NAME> **<NAME>:** <NAME> |
| 2 | invoice | `invoice_matches_payment` | # <NAME> LO/<N> from <NAME> **<NAME> ID:** INV-<N> **<NAME>:** <DATE> **<NAME> to:** <NAME> **<NAME>:** <NAME> |
| 2 | invoice | `invoice_matches_payment` | # <NAME> LY/<N> from <NAME> **<NAME> ID:** INV-<N> **<NAME>:** <DATE> **<NAME> to:** <NAME> **<NAME>:** <NAME> |
| 2 | invoice | `invoice_matches_payment` | # <NAME> MI/<N> from <NAME> **<NAME> ID:** INV-<N> **<NAME>:** <DATE> **<NAME> to:** <NAME> **<NAME>:** <NAME> |
| 2 | invoice | `invoice_matches_payment` | # <NAME> NO/<N> from <NAME> **<NAME> ID:** INV-<N> **<NAME>:** <DATE> **<NAME> to:** <NAME> **<NAME>:** <NAME> |
| 2 | invoice | `invoice_matches_payment` | # <NAME> OA/<N> from <NAME> **<NAME> ID:** INV-<N> **<NAME>:** <DATE> **<NAME> to:** <NAME> **<NAME>:** <NAME> |
| 2 | invoice | `invoice_matches_payment` | # <NAME> SA/<N> from <NAME> **<NAME> ID:** INV-<N> **<NAME>:** <DATE> **<NAME> to:** <NAME> **<NAME>:** <NAME> |
| 2 | invoice | `invoice_matches_payment` | # <NAME> ST/<N> from <NAME> **<NAME> ID:** INV-<N> **<NAME>:** <DATE> **<NAME> to:** <NAME> **<NAME>:** <NAME> |
| 2 | invoice | `invoice_matches_payment` | # <NAME> ST/<N> from <NAME> **<NAME> ID:** INV-<N> **<NAME>:** <DATE> **<NAME> to:** <NAME> **<NAME>:** <NAME> |
| 2 | invoice | `invoice_matches_payment` | # <NAME> WE/<N> from <NAME> **<NAME> ID:** INV-<N> **<NAME>:** <DATE> **<NAME> to:** <NAME> **<NAME>:** <NAME> |
| 2 | invoice | `invoice_matches_payment` | # <NAME> WH/<N> from <NAME> **<NAME> ID:** INV-<N> **<NAME>:** <DATE> **<NAME> to:** <NAME> **<NAME>:** <NAME> |
| 2 | invoice | `invoice_matches_payment` | # <NAME> WH/<N> from <NAME> **<NAME> ID:** INV-<N> **<NAME>:** <DATE> **<NAME> to:** <NAME> **<NAME>:** <NAME> |
| 2 | loan_agreement | `loan_documented` | # <NAME> loan agreement with <NAME> **<NAME> ID:** LOA-<N> **<NAME>:** <DATE> **<NAME>:** <NAME> **<NAME>:** < |
| 2 | receipt | `purchase_receipt` | # <NAME> from <NAME> **<NAME> ID:** RCT-<N> **<NAME>:** <DATE> <NAME> there, <NAME> for booking your spot on o |
| 2 | receipt | `purchase_receipt` | # <NAME> from <NAME> **<NAME> ID:** RCT-<N> **<NAME>:** <DATE> <NAME>: <NAME> - <NAME> <NAME>, <NAME> email co |
| 2 | receipt | `purchase_receipt` | # <NAME> from <NAME> **<NAME> ID:** RCT-<N> **<NAME>:** <DATE> <NAME>: <NAME> booking confirmation - <NAME> <N |
| 2 | receipt | `purchase_receipt` | # <NAME> from <NAME> **<NAME> ID:** RCT-<N> **<NAME>:** <DATE> <NAME>: <NAME> of your booking - <NAME> <NAME>  |
| 2 | receipt | `purchase_receipt` | # <NAME> from <NAME> **<NAME> ID:** RCT-<N> **<NAME>:** <DATE> <NAME>: <NAME> order confirmation - <NAME> <NAM |
| 2 | redundancy_letter | `employment_payout` | # <NAME> from <NAME> **<NAME> ID:** RED-<N> **<NAME>:** <DATE> <NAME> <NAME>, <NAME> our recent consultation p |
| 2 | redundancy_letter | `employment_payout` | # <NAME> from <NAME> LLP **<NAME> ID:** RED-<N> **<NAME>:** <DATE> **<NAME> LLP** <NAME>, <NAME> our recent co |
| 2 | redundancy_letter | `employment_payout` | # <NAME> from <NAME> LLP **<NAME> ID:** RED-<N> **<NAME>:** <DATE> <NAME> LLP <NAME>, <NAME> our recent consul |
| 2 | sale_receipt | `asset_sale` | # <NAME> sale receipt **<NAME> ID:** SAL-<N> **<NAME>:** <DATE> **<NAME> of <NAME>** I, <NAME>, have this day  |
| 2 | sale_receipt | `asset_sale` | # <NAME> sale receipt **<NAME> ID:** SAL-<N> **<NAME>:** <DATE> **<NAME>** I, <NAME>, confirm the sale of one  |
| 2 | sale_receipt | `asset_sale` | # <NAME> sale receipt **<NAME> ID:** SAL-<N> **<NAME>:** <DATE> **<NAME>** I, <NAME>, hereby confirm the sale  |
| 2 | settlement_letter | `employment_payout` | # <NAME> agreement letter from <NAME> **<NAME> ID:** SET-<N> **<NAME>:** <DATE> <NAME> the settlement agreemen |
| 2 | solicitor_letter | `inheritance` | # <NAME> from <NAME> LLP **<NAME> ID:** SOL-<N> **<NAME>:** <DATE> <NAME> LLP <NAME>: <NAME> of <NAME> <NAME>, |
| 2 | solicitor_letter | `inheritance` | # <NAME> from <NAME> LLP **<NAME> ID:** SOL-<N> **<NAME>:** <DATE> <NAME> firm represents the executors handli |
| 2 | solicitor_letter | `inheritance` | # <NAME> from <NAME> LLP **<NAME> ID:** SOL-<N> **<NAME>:** <DATE> <NAME>, <NAME> act on behalf of the executo |
| 2 | solicitor_letter | `inheritance` | # <NAME> from <NAME> LLP **<NAME> ID:** SOL-<N> **<NAME>:** <DATE> <NAME>/<NAME>, <NAME> act on behalf of the  |
| 2 | staff_note | `structuring_enquiry` | # <NAME> by <NAME> report, <NAME> **<NAME> ID:** NTE-<N> **<NAME>:** <DATE> <NAME> visited the store today to  |
| 2 | staff_note | `structuring_enquiry` | # <NAME> by <NAME> report, <NAME> and <NAME> **<NAME> ID:** NTE-<N> **<NAME>:** <DATE> <NAME> visited the stor |
| 2 | staff_note | `structuring_enquiry` | # <NAME> by <NAME> report, <NAME> office, <NAME> **<NAME> ID:** NTE-<N> **<NAME>:** <DATE> <NAME> attended the |
| 2 | staff_note | `structuring_enquiry` | # <NAME> by <NAME> report, <NAME> office, <NAME> **<NAME> ID:** NTE-<N> **<NAME>:** <DATE> <NAME> attended the |
| 2 | staff_note | `structuring_enquiry` | # <NAME> by <NAME> report, <NAME> office, <NAME> **<NAME> ID:** NTE-<N> **<NAME>:** <DATE> <NAME> attended the |
| 2 | staff_note | `structuring_enquiry` | # <NAME> by <NAME>, <NAME> branch **<NAME> ID:** NTE-<N> **<NAME>:** <DATE> <NAME> came into the branch today  |
| 2 | staff_note | `structuring_enquiry` | # <NAME> by <NAME>, <NAME> branch **<NAME> ID:** NTE-<N> **<NAME>:** <DATE> <NAME> visited the <NAME> branch t |
| 2 | staff_note | `structuring_enquiry` | # <NAME> by <NAME>, <NAME> branch **<NAME> ID:** NTE-<N> **<NAME>:** <DATE> <NAME> visited today to deposit <A |
| 2 | staff_note | `structuring_enquiry` | # <NAME> by <NAME>, <NAME> branch **<NAME> ID:** NTE-<N> **<NAME>:** <DATE> I spoke with <NAME> today regardin |
| 2 | staff_note | `structuring_enquiry` | # <NAME> from the client relationship team **<NAME> ID:** NTE-<N> **<NAME>:** <DATE> I had a call today with t |
| 2 | staff_note | `structuring_enquiry` | # <NAME> from the client relationship team **<NAME> ID:** NTE-<N> **<NAME>:** <DATE> I had a conversation toda |
| 2 | supply_contract | `business_contract` | # <NAME> contract with <NAME> **<NAME> ID:** CON-<N> **<NAME>:** <DATE> <NAME> agreement formalizes the supply |
| 2 | supply_contract | `business_contract` | # <NAME> contract with <NAME> **<NAME> ID:** CON-<N> **<NAME>:** <DATE> <NAME> agreement outlines the supply a |
| 2 | supply_contract | `business_contract` | # <NAME> contract with <NAME> **<NAME> ID:** CON-<N> **<NAME>:** <DATE> <NAME> supply agreement formalizes the |
| 2 | support_chat | `loan_from_friend_claim` | # <NAME> with the customer **<NAME> ID:** CHT-<N> **<NAME>:** <DATE> **<NAME>:** <NAME> there. I’m reaching ou |
| 2 | support_chat | `medical_treatment_abroad` | # <NAME> with the customer **<NAME> ID:** CHT-<N> **<NAME>:** <DATE> **<NAME>:** <NAME> you for contacting sup |
| 2 | support_chat | `loan_from_friend_claim,medical_treatment_abroad` | # <NAME> with the customer **<NAME> ID:** CHT-<N> **<NAME>:** <DATE> **<NAME>:** <NAME> you for contacting sup |
| 2 | support_chat | `cash_withdrawal_returned` | # <NAME> with the customer **<NAME> ID:** CHT-<N> **<NAME>:** <DATE> **<NAME>:** <NAME>, I deposited that cash |
| 2 | support_chat | `medical_treatment_abroad` | # <NAME> with the customer **<NAME> ID:** CHT-<N> **<NAME>:** <DATE> **<NAME>:** <NAME>, this is support. <NAM |
| 2 | venue_email | `refund` | # <NAME> from <NAME> and <NAME> **<NAME> ID:** EML-<N> **<NAME>:** <DATE> <NAME>, <NAME> are sorry to hear tha |
| 2 | venue_email | `refund` | # <NAME> from <NAME> and <NAME> **<NAME> ID:** EML-<N> **<NAME>:** <DATE> <NAME>, <NAME> are writing to acknow |
| 2 | venue_email | `refund` | # <NAME> from <NAME> and <NAME> **<NAME> ID:** EML-<N> **<NAME>:** <DATE> <NAME>: <NAME> of cancellation and r |
| 2 | venue_email | `refund` | # <NAME> from <NAME> and <NAME> **<NAME> ID:** EML-<N> **<NAME>:** <DATE> <NAME>: <NAME> your cancellation - B |
| 1 | booking_confirmation | `event_booking` | # <NAME> confirmation BK13694 from <NAME> **<NAME> ID:** BKG-<N> **<NAME>:** <DATE> **<NAME> reference:** BK13 |
| 1 | booking_confirmation | `event_booking` | # <NAME> confirmation BK15402 from <NAME> **<NAME> ID:** BKG-<N> **<NAME>:** <DATE> **<NAME> reference:** BK15 |
| 1 | booking_confirmation | `event_booking` | # <NAME> confirmation BK17194 from <NAME> **<NAME> ID:** BKG-<N> **<NAME>:** <DATE> **<NAME> reference:** BK17 |
| 1 | booking_confirmation | `event_booking` | # <NAME> confirmation BK19428 from <NAME> **<NAME> ID:** BKG-<N> **<NAME>:** <DATE> **<NAME> reference:** BK19 |
| 1 | booking_confirmation | `event_booking` | # <NAME> confirmation BK19764 from <NAME> **<NAME> ID:** BKG-<N> **<NAME>:** <DATE> **<NAME> reference:** BK19 |
| 1 | booking_confirmation | `event_booking` | # <NAME> confirmation BK24374 from <NAME> **<NAME> ID:** BKG-<N> **<NAME>:** <DATE> **<NAME> reference:** BK24 |
| 1 | booking_confirmation | `event_booking` | # <NAME> confirmation BK25299 from <NAME> **<NAME> ID:** BKG-<N> **<NAME>:** <DATE> **<NAME> reference:** BK25 |
| 1 | booking_confirmation | `event_booking` | # <NAME> confirmation BK33521 from <NAME> **<NAME> ID:** BKG-<N> **<NAME>:** <DATE> **<NAME> reference:** BK33 |
| 1 | booking_confirmation | `event_booking` | # <NAME> confirmation BK34759 from <NAME> **<NAME> ID:** BKG-<N> **<NAME>:** <DATE> **<NAME> reference:** BK34 |
| 1 | booking_confirmation | `event_booking` | # <NAME> confirmation BK40950 from <NAME> **<NAME> ID:** BKG-<N> **<NAME>:** <DATE> **<NAME> reference:** BK40 |
| 1 | booking_confirmation | `event_booking` | # <NAME> confirmation BK44264 from <NAME> **<NAME> ID:** BKG-<N> **<NAME>:** <DATE> **<NAME> reference:** BK44 |
| 1 | booking_confirmation | `event_booking` | # <NAME> confirmation BK46821 from <NAME> **<NAME> ID:** BKG-<N> **<NAME>:** <DATE> **<NAME> reference:** BK46 |
| 1 | booking_confirmation | `event_booking` | # <NAME> confirmation BK50122 from <NAME> **<NAME> ID:** BKG-<N> **<NAME>:** <DATE> **<NAME> reference:** BK50 |
| 1 | booking_confirmation | `event_booking` | # <NAME> confirmation BK54022 from <NAME> **<NAME> ID:** BKG-<N> **<NAME>:** <DATE> **<NAME> reference:** BK54 |
| 1 | booking_confirmation | `event_booking` | # <NAME> confirmation BK54474 from <NAME> **<NAME> ID:** BKG-<N> **<NAME>:** <DATE> **<NAME> reference:** BK54 |
| 1 | booking_confirmation | `event_booking` | # <NAME> confirmation BK55884 from <NAME> **<NAME> ID:** BKG-<N> **<NAME>:** <DATE> **<NAME> reference:** BK55 |
| 1 | booking_confirmation | `event_booking` | # <NAME> confirmation BK57721 from <NAME> **<NAME> ID:** BKG-<N> **<NAME>:** <DATE> **<NAME> reference:** BK57 |
| 1 | booking_confirmation | `event_booking` | # <NAME> confirmation BK62302 from <NAME> **<NAME> ID:** BKG-<N> **<NAME>:** <DATE> **<NAME> reference:** BK62 |
| 1 | booking_confirmation | `event_booking` | # <NAME> confirmation BK65851 from <NAME> **<NAME> ID:** BKG-<N> **<NAME>:** <DATE> **<NAME> reference:** BK65 |
| 1 | booking_confirmation | `event_booking` | # <NAME> confirmation BK70241 from <NAME> **<NAME> ID:** BKG-<N> **<NAME>:** <DATE> **<NAME> reference:** BK70 |
| 1 | booking_confirmation | `event_booking` | # <NAME> confirmation BK76044 from <NAME> **<NAME> ID:** BKG-<N> **<NAME>:** <DATE> **<NAME> reference:** BK76 |
| 1 | booking_confirmation | `event_booking` | # <NAME> confirmation BK77550 from <NAME> **<NAME> ID:** BKG-<N> **<NAME>:** <DATE> **<NAME> reference:** BK77 |
| 1 | booking_confirmation | `event_booking` | # <NAME> confirmation BK79235 from <NAME> **<NAME> ID:** BKG-<N> **<NAME>:** <DATE> **<NAME> reference:** BK79 |
| 1 | booking_confirmation | `event_booking` | # <NAME> confirmation BK80177 from <NAME> **<NAME> ID:** BKG-<N> **<NAME>:** <DATE> **<NAME> reference:** BK80 |
| 1 | booking_confirmation | `event_booking` | # <NAME> confirmation BK87901 from <NAME> **<NAME> ID:** BKG-<N> **<NAME>:** <DATE> **<NAME> reference:** BK87 |
| 1 | booking_confirmation | `event_booking` | # <NAME> confirmation BK90375 from <NAME> **<NAME> ID:** BKG-<N> **<NAME>:** <DATE> **<NAME> reference:** BK90 |
| 1 | booking_confirmation | `event_booking` | # <NAME> confirmation BK95911 from <NAME> **<NAME> ID:** BKG-<N> **<NAME>:** <DATE> **<NAME> reference:** BK95 |
| 1 | booking_confirmation | `event_booking` | # <NAME> confirmation BK96689 from <NAME> **<NAME> ID:** BKG-<N> **<NAME>:** <DATE> **<NAME> reference:** BK96 |
| 1 | booking_confirmation | `event_booking` | # <NAME> confirmation BK97550 from <NAME> **<NAME> ID:** BKG-<N> **<NAME>:** <DATE> **<NAME> reference:** BK97 |
| 1 | booking_confirmation | `event_booking` | # <NAME> confirmation GT10305 from <NAME> **<NAME> ID:** BKG-<N> **<NAME>:** <DATE> **<NAME> reference:** GT10 |
| 1 | booking_confirmation | `event_booking` | # <NAME> confirmation GT14143 from <NAME> **<NAME> ID:** BKG-<N> **<NAME>:** <DATE> **<NAME> reference:** GT14 |
| 1 | booking_confirmation | `event_booking` | # <NAME> confirmation GT19326 from <NAME> **<NAME> ID:** BKG-<N> **<NAME>:** <DATE> **<NAME> reference:** GT19 |
| 1 | booking_confirmation | `event_booking` | # <NAME> confirmation GT28453 from <NAME> **<NAME> ID:** BKG-<N> **<NAME>:** <DATE> **<NAME> reference:** GT28 |
| 1 | booking_confirmation | `event_booking` | # <NAME> confirmation GT35433 from <NAME> **<NAME> ID:** BKG-<N> **<NAME>:** <DATE> **<NAME> reference:** GT35 |
| 1 | booking_confirmation | `event_booking` | # <NAME> confirmation GT39775 from <NAME> **<NAME> ID:** BKG-<N> **<NAME>:** <DATE> **<NAME> reference:** GT39 |
| 1 | booking_confirmation | `event_booking` | # <NAME> confirmation GT40307 from <NAME> **<NAME> ID:** BKG-<N> **<NAME>:** <DATE> **<NAME> reference:** GT40 |
| 1 | booking_confirmation | `event_booking` | # <NAME> confirmation GT42208 from <NAME> **<NAME> ID:** BKG-<N> **<NAME>:** <DATE> **<NAME> reference:** GT42 |
| 1 | booking_confirmation | `event_booking` | # <NAME> confirmation GT42557 from <NAME> **<NAME> ID:** BKG-<N> **<NAME>:** <DATE> **<NAME> reference:** GT42 |
| 1 | booking_confirmation | `event_booking` | # <NAME> confirmation GT46139 from <NAME> **<NAME> ID:** BKG-<N> **<NAME>:** <DATE> **<NAME> reference:** GT46 |
| 1 | booking_confirmation | `event_booking` | # <NAME> confirmation GT50327 from <NAME> **<NAME> ID:** BKG-<N> **<NAME>:** <DATE> **<NAME> reference:** GT50 |
| 1 | booking_confirmation | `event_booking` | # <NAME> confirmation GT50911 from <NAME> **<NAME> ID:** BKG-<N> **<NAME>:** <DATE> **<NAME> reference:** GT50 |
| 1 | booking_confirmation | `event_booking` | # <NAME> confirmation GT50985 from <NAME> **<NAME> ID:** BKG-<N> **<NAME>:** <DATE> **<NAME> reference:** GT50 |
| 1 | booking_confirmation | `event_booking` | # <NAME> confirmation GT56178 from <NAME> **<NAME> ID:** BKG-<N> **<NAME>:** <DATE> **<NAME> reference:** GT56 |
| 1 | booking_confirmation | `event_booking` | # <NAME> confirmation GT71020 from <NAME> **<NAME> ID:** BKG-<N> **<NAME>:** <DATE> **<NAME> reference:** GT71 |
| 1 | booking_confirmation | `event_booking` | # <NAME> confirmation GT75084 from <NAME> **<NAME> ID:** BKG-<N> **<NAME>:** <DATE> **<NAME> reference:** GT75 |
| 1 | booking_confirmation | `event_booking` | # <NAME> confirmation GT75479 from <NAME> **<NAME> ID:** BKG-<N> **<NAME>:** <DATE> **<NAME> reference:** GT75 |
| 1 | booking_confirmation | `event_booking` | # <NAME> confirmation GT85799 from <NAME> **<NAME> ID:** BKG-<N> **<NAME>:** <DATE> **<NAME> reference:** GT85 |
| 1 | booking_confirmation | `event_booking` | # <NAME> confirmation GT89318 from <NAME> **<NAME> ID:** BKG-<N> **<NAME>:** <DATE> **<NAME> reference:** GT89 |
| 1 | booking_confirmation | `event_booking` | # <NAME> confirmation GT97412 from <NAME> **<NAME> ID:** BKG-<N> **<NAME>:** <DATE> **<NAME> reference:** GT97 |
| 1 | booking_confirmation | `event_booking` | # <NAME> confirmation TR10536 from <NAME> **<NAME> ID:** BKG-<N> **<NAME>:** <DATE> **<NAME> reference:** TR10 |
| 1 | booking_confirmation | `event_booking` | # <NAME> confirmation TR14368 from <NAME> **<NAME> ID:** BKG-<N> **<NAME>:** <DATE> **<NAME> reference:** TR14 |
| 1 | booking_confirmation | `event_booking` | # <NAME> confirmation TR16831 from <NAME> **<NAME> ID:** BKG-<N> **<NAME>:** <DATE> **<NAME> reference:** TR16 |
| 1 | booking_confirmation | `event_booking` | # <NAME> confirmation TR19184 from <NAME> **<NAME> ID:** BKG-<N> **<NAME>:** <DATE> **<NAME> reference:** TR19 |
| 1 | booking_confirmation | `event_booking` | # <NAME> confirmation TR30119 from <NAME> **<NAME> ID:** BKG-<N> **<NAME>:** <DATE> **<NAME> reference:** TR30 |
| 1 | booking_confirmation | `event_booking` | # <NAME> confirmation TR30328 from <NAME> **<NAME> ID:** BKG-<N> **<NAME>:** <DATE> **<NAME> reference:** TR30 |
| 1 | booking_confirmation | `event_booking` | # <NAME> confirmation TR30725 from <NAME> **<NAME> ID:** BKG-<N> **<NAME>:** <DATE> **<NAME> reference:** TR30 |
| 1 | booking_confirmation | `event_booking` | # <NAME> confirmation TR35945 from <NAME> **<NAME> ID:** BKG-<N> **<NAME>:** <DATE> **<NAME> reference:** TR35 |
| 1 | booking_confirmation | `event_booking` | # <NAME> confirmation TR36166 from <NAME> **<NAME> ID:** BKG-<N> **<NAME>:** <DATE> **<NAME> reference:** TR36 |
| 1 | booking_confirmation | `event_booking` | # <NAME> confirmation TR38672 from <NAME> **<NAME> ID:** BKG-<N> **<NAME>:** <DATE> **<NAME> reference:** TR38 |
| 1 | booking_confirmation | `event_booking` | # <NAME> confirmation TR39148 from <NAME> **<NAME> ID:** BKG-<N> **<NAME>:** <DATE> **<NAME> reference:** TR39 |
| 1 | booking_confirmation | `event_booking` | # <NAME> confirmation TR43784 from <NAME> **<NAME> ID:** BKG-<N> **<NAME>:** <DATE> **<NAME> reference:** TR43 |
| 1 | booking_confirmation | `event_booking` | # <NAME> confirmation TR45388 from <NAME> **<NAME> ID:** BKG-<N> **<NAME>:** <DATE> **<NAME> reference:** TR45 |
| 1 | booking_confirmation | `event_booking` | # <NAME> confirmation TR47684 from <NAME> **<NAME> ID:** BKG-<N> **<NAME>:** <DATE> **<NAME> reference:** TR47 |
| 1 | booking_confirmation | `event_booking` | # <NAME> confirmation TR49879 from <NAME> **<NAME> ID:** BKG-<N> **<NAME>:** <DATE> **<NAME> reference:** TR49 |
| 1 | booking_confirmation | `event_booking` | # <NAME> confirmation TR50557 from <NAME> **<NAME> ID:** BKG-<N> **<NAME>:** <DATE> **<NAME> reference:** TR50 |
| 1 | booking_confirmation | `event_booking` | # <NAME> confirmation TR50884 from <NAME> **<NAME> ID:** BKG-<N> **<NAME>:** <DATE> **<NAME> reference:** TR50 |
| 1 | booking_confirmation | `event_booking` | # <NAME> confirmation TR52668 from <NAME> **<NAME> ID:** BKG-<N> **<NAME>:** <DATE> **<NAME> reference:** TR52 |
| 1 | booking_confirmation | `event_booking` | # <NAME> confirmation TR55033 from <NAME> **<NAME> ID:** BKG-<N> **<NAME>:** <DATE> **<NAME> reference:** TR55 |
| 1 | booking_confirmation | `event_booking` | # <NAME> confirmation TR59656 from <NAME> **<NAME> ID:** BKG-<N> **<NAME>:** <DATE> **<NAME> reference:** TR59 |
| 1 | booking_confirmation | `event_booking` | # <NAME> confirmation TR63346 from <NAME> **<NAME> ID:** BKG-<N> **<NAME>:** <DATE> **<NAME> reference:** TR63 |
| 1 | booking_confirmation | `event_booking` | # <NAME> confirmation TR63367 from <NAME> **<NAME> ID:** BKG-<N> **<NAME>:** <DATE> **<NAME> reference:** TR63 |
| 1 | booking_confirmation | `event_booking` | # <NAME> confirmation TR63391 from <NAME> **<NAME> ID:** BKG-<N> **<NAME>:** <DATE> **<NAME> reference:** TR63 |
| 1 | booking_confirmation | `event_booking` | # <NAME> confirmation TR74014 from <NAME> **<NAME> ID:** BKG-<N> **<NAME>:** <DATE> **<NAME> reference:** TR74 |
| 1 | booking_confirmation | `event_booking` | # <NAME> confirmation TR74123 from <NAME> **<NAME> ID:** BKG-<N> **<NAME>:** <DATE> **<NAME> reference:** TR74 |
| 1 | booking_confirmation | `event_booking` | # <NAME> confirmation TR74222 from <NAME> **<NAME> ID:** BKG-<N> **<NAME>:** <DATE> **<NAME> reference:** TR74 |
| 1 | booking_confirmation | `event_booking` | # <NAME> confirmation TR82634 from <NAME> **<NAME> ID:** BKG-<N> **<NAME>:** <DATE> **<NAME> reference:** TR82 |
| 1 | booking_confirmation | `event_booking` | # <NAME> confirmation TR84057 from <NAME> **<NAME> ID:** BKG-<N> **<NAME>:** <DATE> **<NAME> reference:** TR84 |
| 1 | booking_confirmation | `event_booking` | # <NAME> confirmation TR86182 from <NAME> **<NAME> ID:** BKG-<N> **<NAME>:** <DATE> **<NAME> reference:** TR86 |
| 1 | booking_confirmation | `event_booking` | # <NAME> confirmation TR92646 from <NAME> **<NAME> ID:** BKG-<N> **<NAME>:** <DATE> **<NAME> reference:** TR92 |
| 1 | booking_confirmation | `event_booking` | # <NAME> confirmation TR94057 from <NAME> **<NAME> ID:** BKG-<N> **<NAME>:** <DATE> **<NAME> reference:** TR94 |
| 1 | booking_confirmation | `event_booking` | # <NAME> confirmation TR94346 from <NAME> **<NAME> ID:** BKG-<N> **<NAME>:** <DATE> **<NAME> reference:** TR94 |
| 1 | booking_confirmation | `event_booking` | # <NAME> confirmation TR97867 from <NAME> **<NAME> ID:** BKG-<N> **<NAME>:** <DATE> **<NAME> reference:** TR97 |
| 1 | booking_confirmation | `event_booking` | # <NAME> confirmation TR99062 from <NAME> **<NAME> ID:** BKG-<N> **<NAME>:** <DATE> **<NAME> reference:** TR99 |
| 1 | booking_confirmation | `event_booking` | # <NAME> confirmation TR99367 from <NAME> **<NAME> ID:** BKG-<N> **<NAME>:** <DATE> **<NAME> reference:** TR99 |
| 1 | cancellation_confirmation | `refund` | # <NAME> confirmation **<NAME> ID:** CAN-<N> **<NAME>:** <DATE> <NAME>: <NAME> confirmation <NAME> are writing |
| 1 | cancellation_confirmation | `refund` | # <NAME> confirmation **<NAME> ID:** CAN-<N> **<NAME>:** <DATE> <NAME>: <NAME> confirmation for your ISA <NAME |
| 1 | cancellation_confirmation | `refund` | # <NAME> confirmation **<NAME> ID:** CAN-<N> **<NAME>:** <DATE> <NAME>: <NAME> of ISA cancellation <NAME>, <NA |
| 1 | cancellation_confirmation | `refund` | # <NAME> confirmation **<NAME> ID:** CAN-<N> **<NAME>:** <DATE> <NAME>: <NAME> of your ISA cancellation <NAME> |
| 1 | cancellation_confirmation | `refund` | # <NAME> confirmation **<NAME> ID:** CAN-<N> **<NAME>:** <DATE> <NAME>: <NAME> regarding your recent ISA cance |
| 1 | cancellation_confirmation | `refund` | # <NAME> confirmation **<NAME> ID:** CAN-<N> **<NAME>:** <DATE> <NAME>: <NAME>: <NAME> ISA cancellation confir |
| 1 | cancellation_confirmation | `refund` | # <NAME> confirmation **<NAME> ID:** CAN-<N> **<NAME>:** <DATE> <NAME>: <NAME>: <NAME> ISA cancellation reques |
| 1 | customer_email | `erroneous_transfer_refund` | # <NAME> from the customer **<NAME> ID:** EML-<N> **<NAME>:** <DATE> <NAME> there, I realized I made a mistake |
| 1 | customer_email | `erroneous_transfer_refund` | # <NAME> from the customer **<NAME> ID:** EML-<N> **<NAME>:** <DATE> <NAME> there, I’m reaching out because I  |
| 1 | customer_email | `erroneous_transfer_refund` | # <NAME> from the customer **<NAME> ID:** EML-<N> **<NAME>:** <DATE> <NAME> there, I’ve just realised that I m |
| 1 | customer_email | `erroneous_transfer_refund` | # <NAME> from the customer **<NAME> ID:** EML-<N> **<NAME>:** <DATE> <NAME> there, I’ve made a bit of a blunde |
| 1 | customer_email | `erroneous_transfer_refund` | # <NAME> from the customer **<NAME> ID:** EML-<N> **<NAME>:** <DATE> <NAME> there, I’ve made a bit of a mistak |
| 1 | customer_email | `erroneous_transfer_refund` | # <NAME> from the customer **<NAME> ID:** EML-<N> **<NAME>:** <DATE> <NAME>, I’ve just realised that I made a  |
| 1 | customer_email | `erroneous_transfer_refund` | # <NAME> from the customer **<NAME> ID:** EML-<N> **<NAME>:** <DATE> <NAME>, I’ve made a mistake and transferr |
| 1 | customer_email | `erroneous_transfer_refund` | # <NAME> from the customer **<NAME> ID:** EML-<N> **<NAME>:** <DATE> <NAME>: <NAME> for withdrawal - <NAME> <N |
| 1 | customer_email | `erroneous_transfer_refund` | # <NAME> from the customer **<NAME> ID:** EML-<N> **<NAME>:** <DATE> <NAME>: <NAME>: <NAME> request for accoun |
| 1 | customer_email | `erroneous_transfer_refund` | # <NAME> from the customer **<NAME> ID:** EML-<N> **<NAME>:** <DATE> <NAME>: <NAME>: <NAME> reversal request < |
| 1 | customer_email | `erroneous_transfer_refund` | # <NAME> from the customer **<NAME> ID:** EML-<N> **<NAME>:** <DATE> I am writing to request a return of funds |
| 1 | customer_email | `erroneous_transfer_refund` | # <NAME> from the customer **<NAME> ID:** EML-<N> **<NAME>:** <DATE> I’ve just realised that the transfer of < |
| 1 | customer_email | `erroneous_transfer_refund` | # <NAME> from the customer **<NAME> ID:** EML-<N> **<NAME>:** <DATE> I’ve made a mistake and transferred <AMT> |
| 1 | customer_letter | `own_account_instruction` | # <NAME> from the customer **<NAME> ID:** LTR-<N> **<NAME>:** <DATE> <NAME> the <NAME>, I am writing to formal |
| 1 | customer_letter | `own_account_instruction` | # <NAME> from the customer **<NAME> ID:** LTR-<N> **<NAME>:** <DATE> <NAME> the <NAME>, I am writing to inform |
| 1 | customer_letter | `own_account_instruction` | # <NAME> from the customer **<NAME> ID:** LTR-<N> **<NAME>:** <DATE> <NAME> the <NAME>, I am writing to notify |
| 1 | customer_letter | `own_account_instruction` | # <NAME> from the customer **<NAME> ID:** LTR-<N> **<NAME>:** <DATE> <NAME> whom it may concern, I am writing  |
| 1 | customer_letter | `own_account_instruction` | # <NAME> from the customer **<NAME> ID:** LTR-<N> **<NAME>:** <DATE> <NAME> whom it may concern, I am writing  |
| 1 | customer_letter | `own_account_instruction` | # <NAME> from the customer **<NAME> ID:** LTR-<N> **<NAME>:** <DATE> <NAME>, I am writing to formally notify y |
| 1 | customer_letter | `own_account_instruction` | # <NAME> from the customer **<NAME> ID:** LTR-<N> **<NAME>:** <DATE> <NAME>, I am writing to notify you of a c |
| 1 | customer_letter | `own_account_instruction` | # <NAME> from the customer **<NAME> ID:** LTR-<N> **<NAME>:** <DATE> I am writing to inform you that I have re |
| 1 | customer_letter | `own_account_instruction` | # <NAME> from the customer **<NAME> ID:** LTR-<N> **<NAME>:** <DATE> I am writing to notify you that I have re |
| 1 | deposit_return_letter | `refund` | # <NAME> return from <NAME> **<NAME> ID:** LET-<N> **<NAME>:** <DATE> <NAME>: <NAME> of <NAME> - <NAME> <NAME> |
| 1 | deposit_return_letter | `refund` | # <NAME> return from <NAME> **<NAME> ID:** LET-<N> **<NAME>:** <DATE> <NAME>: <NAME> of deposit return - <NAME |
| 1 | deposit_return_letter | `refund` | # <NAME> return from <NAME> **<NAME> ID:** LET-<N> **<NAME>:** <DATE> <NAME>: <NAME> of your tenancy deposit - |
| 1 | deposit_return_letter | `refund` | # <NAME> return from <NAME> **<NAME> ID:** LET-<N> **<NAME>:** <DATE> <NAME>: <NAME> return - <NAME> <NAME>, < |
| 1 | deposit_return_letter | `refund` | # <NAME> return from <NAME> **<NAME> ID:** LET-<N> **<NAME>:** <DATE> <NAME>: <NAME> return regarding your rec |
| 1 | deposit_return_letter | `refund` | # <NAME> return from <NAME> **<NAME> ID:** LET-<N> **<NAME>:** <DATE> <NAME>: <NAME> your tenancy deposit - <N |
| 1 | deposit_return_letter | `refund` | # <NAME> return from <NAME> **<NAME> ID:** LET-<N> **<NAME>:** <DATE> <NAME>: <NAME> your tenancy deposit retu |
| 1 | email | `group_funds_pass_through` | # <NAME> from <NAME> **<NAME> ID:** EML-<N> **<NAME>:** <DATE> <NAME> there, I am writing to confirm that <NAM |
| 1 | email | `group_funds_pass_through` | # <NAME> from <NAME> **<NAME> ID:** EML-<N> **<NAME>:** <DATE> <NAME>, <NAME> be advised that <NAME> will be s |
| 1 | email | `group_funds_pass_through` | # <NAME> from <NAME> **<NAME> ID:** EML-<N> **<NAME>:** <DATE> <NAME>: <NAME> - <NAME> <NAME> the payments tea |
| 1 | email | `group_funds_pass_through` | # <NAME> from <NAME> **<NAME> ID:** EML-<N> **<NAME>:** <DATE> <NAME>: <NAME> - <NAME> <NAME>, I’m writing to  |
| 1 | email | `group_funds_pass_through` | # <NAME> from <NAME> **<NAME> ID:** EML-<N> **<NAME>:** <DATE> <NAME>: <NAME> <NAME> team, I’m writing to conf |
| 1 | email | `group_funds_pass_through` | # <NAME> from <NAME> **<NAME> ID:** EML-<N> **<NAME>:** <DATE> <NAME>: <NAME> arrangement - <NAME> <NAME>, I’m |
| 1 | email | `group_funds_pass_through` | # <NAME> from <NAME> **<NAME> ID:** EML-<N> **<NAME>:** <DATE> <NAME>: <NAME> arrangements <NAME> team, I’m wr |
| 1 | email | `group_funds_pass_through` | # <NAME> from <NAME> **<NAME> ID:** EML-<N> **<NAME>:** <DATE> <NAME>: <NAME> instruction regarding <NAME> and |
| 1 | email | `group_funds_pass_through` | # <NAME> from <NAME> **<NAME> ID:** EML-<N> **<NAME>:** <DATE> <NAME>: <NAME> outgoing payment <NAME> there, I |
| 1 | email | `group_funds_pass_through` | # <NAME> from <NAME> **<NAME> ID:** EML-<N> **<NAME>:** <DATE> <NAME>: <NAME> payment - <NAME> <NAME>, <NAME>  |
| 1 | email | `group_funds_pass_through` | # <NAME> from <NAME> **<NAME> ID:** EML-<N> **<NAME>:** <DATE> <NAME>: <NAME> payment for <NAME> <NAME>, I’m w |
| 1 | email | `group_funds_pass_through` | # <NAME> from <NAME> **<NAME> ID:** EML-<N> **<NAME>:** <DATE> <NAME>: <NAME> payment for <NAME> I am writing  |
| 1 | email | `group_funds_pass_through` | # <NAME> from <NAME> **<NAME> ID:** EML-<N> **<NAME>:** <DATE> <NAME>: <NAME> payment inquiry <NAME> the payme |
| 1 | email | `group_funds_pass_through` | # <NAME> from <NAME> **<NAME> ID:** EML-<N> **<NAME>:** <DATE> <NAME>: <NAME> payment instructions <NAME> team |
| 1 | email | `group_funds_pass_through` | # <NAME> from <NAME> **<NAME> ID:** EML-<N> **<NAME>:** <DATE> <NAME>: <NAME> payment transfer <NAME> will be  |
| 1 | email | `group_funds_pass_through` | # <NAME> from <NAME> **<NAME> ID:** EML-<N> **<NAME>:** <DATE> <NAME>: <NAME> processing for <NAME> I am writi |
| 1 | email | `group_funds_pass_through` | # <NAME> from <NAME> **<NAME> ID:** EML-<N> **<NAME>:** <DATE> <NAME>: <NAME> regarding <NAME> I’m writing to  |
| 1 | email | `group_funds_pass_through` | # <NAME> from <NAME> **<NAME> ID:** EML-<N> **<NAME>:** <DATE> <NAME>: <NAME> transfer I am writing to let you |
| 1 | email | `group_funds_pass_through` | # <NAME> from <NAME> **<NAME> ID:** EML-<N> **<NAME>:** <DATE> <NAME>: <NAME> transfer for <NAME> I am writing |
| 1 | employment_contract | `business_contract` | # <NAME> contract **<NAME> ID:** EMP-<N> **<NAME>:** <DATE> **<NAME>** **<NAME>:** <NAME> **<NAME>:** <NAME> * |
| 1 | employment_contract | `business_contract` | # <NAME> contract **<NAME> ID:** EMP-<N> **<NAME>:** <DATE> **<NAME>** <NAME> has entered into a formal agreem |
| 1 | employment_contract | `business_contract` | # <NAME> contract **<NAME> ID:** EMP-<N> **<NAME>:** <DATE> **<NAME>** <NAME> has entered into a service agree |
| 1 | employment_contract | `business_contract` | # <NAME> contract **<NAME> ID:** EMP-<N> **<NAME>:** <DATE> **<NAME>** <NAME> has entered into a two-year cont |
| 1 | employment_contract | `business_contract` | # <NAME> contract **<NAME> ID:** EMP-<N> **<NAME>:** <DATE> **<NAME>** <NAME> has entered into a two-year empl |
| 1 | employment_contract | `business_contract` | # <NAME> contract **<NAME> ID:** EMP-<N> **<NAME>:** <DATE> **<NAME>** <NAME> has entered into an employment a |
| 1 | employment_contract | `business_contract` | # <NAME> contract **<NAME> ID:** EMP-<N> **<NAME>:** <DATE> <NAME> agreement confirms the employment of <NAME> |
| 1 | employment_contract | `business_contract` | # <NAME> contract **<NAME> ID:** EMP-<N> **<NAME>:** <DATE> <NAME> agreement confirms the engagement of <NAME> |
| 1 | employment_contract | `business_contract` | # <NAME> contract **<NAME> ID:** EMP-<N> **<NAME>:** <DATE> <NAME> employment summary confirms that <NAME> has |
| 1 | employment_contract | `business_contract` | # <NAME> contract **<NAME> ID:** EMP-<N> **<NAME>:** <DATE> <NAME> has entered into an agreement with <NAME> t |
| 1 | employment_contract | `business_contract` | # <NAME> contract **<NAME> ID:** EMP-<N> **<NAME>:** <DATE> <NAME> has entered into an employment agreement wi |
| 1 | employment_contract | `business_contract` | # <NAME> contract **<NAME> ID:** EMP-<N> **<NAME>:** <DATE> <NAME> is engaged as a petroleum engineer by <NAME |
| 1 | employment_contract | `business_contract` | # <NAME> contract **<NAME> ID:** EMP-<N> **<NAME>:** <DATE> <NAME> summary confirms that <NAME> has entered in |
| 1 | employment_contract | `business_contract` | # <NAME> contract **<NAME> ID:** EMP-<N> **<NAME>:** <DATE> <NAME> summary confirms that <NAME> has entered in |
| 1 | employment_contract | `business_contract` | # <NAME> contract **<NAME> ID:** EMP-<N> **<NAME>:** <DATE> <NAME> summary outlines the terms of employment fo |
| 1 | factoring_agreement | `business_contract` | # <NAME> finance agreement with <NAME> **<NAME> ID:** FAC-<N> **<NAME>:** <DATE> <NAME> this agreement, <NAME> |
| 1 | factoring_agreement | `business_contract` | # <NAME> finance agreement with <NAME> **<NAME> ID:** FAC-<N> **<NAME>:** <DATE> <NAME> this facility, <NAME>  |
| 1 | factoring_agreement | `business_contract` | # <NAME> finance agreement with <NAME> **<NAME> ID:** FAC-<N> **<NAME>:** <DATE> <NAME> this facility, <NAME>  |
| 1 | factoring_agreement | `business_contract` | # <NAME> finance agreement with <NAME> **<NAME> ID:** FAC-<N> **<NAME>:** <DATE> <NAME> this facility, <NAME>  |
| 1 | gift_letter | `gift_from_relative` | # <NAME> letter from <NAME> **<NAME> ID:** GFT-<N> **<NAME>:** <DATE> <NAME> whom it may concern, I, <NAME>, c |
| 1 | gift_letter | `gift_from_relative` | # <NAME> letter from <NAME> **<NAME> ID:** GFT-<N> **<NAME>:** <DATE> <NAME>, I, <NAME>, born <DATE>, am provi |
| 1 | gift_letter | `gift_from_relative` | # <NAME> letter from <NAME> **<NAME> ID:** GFT-<N> **<NAME>:** <DATE> <NAME>, I, <NAME>, born <DATE>, am provi |
| 1 | gift_letter | `gift_from_relative` | # <NAME> letter from <NAME> **<NAME> ID:** GFT-<N> **<NAME>:** <DATE> <NAME>, I, <NAME>, confirm that I am pro |
| 1 | gift_letter | `gift_from_relative` | # <NAME> letter from <NAME> **<NAME> ID:** GFT-<N> **<NAME>:** <DATE> <NAME>, I, <NAME>, hereby confirm that I |
| 1 | gift_letter | `gift_from_relative` | # <NAME> letter from <NAME> **<NAME> ID:** GFT-<N> **<NAME>:** <DATE> I, <NAME> (DOB: <DATE>), confirm that I  |
| 1 | gift_letter | `gift_from_relative` | # <NAME> letter from <NAME> **<NAME> ID:** GFT-<N> **<NAME>:** <DATE> I, <NAME>, born on <DATE>, hereby confir |
| 1 | gift_letter | `gift_from_relative` | # <NAME> letter from <NAME> **<NAME> ID:** GFT-<N> **<NAME>:** <DATE> I, <NAME>, wish to confirm that I am gif |
| 1 | holding_deposit_receipt | `refund` | # <NAME> deposit receipt from <NAME> **<NAME> ID:** LET-<N> **<NAME>:** <DATE> <NAME>, <NAME> are writing to c |
| 1 | holding_deposit_receipt | `refund` | # <NAME> deposit receipt from <NAME> **<NAME> ID:** LET-<N> **<NAME>:** <DATE> <NAME>, <NAME> email serves as  |
| 1 | holding_deposit_receipt | `refund` | # <NAME> deposit receipt from <NAME> **<NAME> ID:** LET-<N> **<NAME>:** <DATE> <NAME>, <NAME> you for confirmi |
| 1 | holding_deposit_receipt | `refund` | # <NAME> deposit receipt from <NAME> **<NAME> ID:** LET-<N> **<NAME>:** <DATE> <NAME>: <NAME> - <NAME> <NAME>, |
| 1 | holding_deposit_receipt | `refund` | # <NAME> deposit receipt from <NAME> **<NAME> ID:** LET-<N> **<NAME>:** <DATE> <NAME>: <NAME> - <NAME> <NAME>, |
| 1 | holding_deposit_receipt | `refund` | # <NAME> deposit receipt from <NAME> **<NAME> ID:** LET-<N> **<NAME>:** <DATE> <NAME>: <NAME> of holding depos |
| 1 | holding_deposit_receipt | `refund` | # <NAME> deposit receipt from <NAME> **<NAME> ID:** LET-<N> **<NAME>:** <DATE> <NAME>: <NAME>: <NAME> <NAME>,  |
| 1 | insurer_letter | `insurance_settlement` | # <NAME> settlement letter from <NAME> plc **<NAME> ID:** INS-<N> **<NAME>:** <DATE> **<NAME> plc** <NAME> you |
| 1 | insurer_letter | `insurance_settlement` | # <NAME> settlement letter from <NAME> plc **<NAME> ID:** INS-<N> **<NAME>:** <DATE> **<NAME> plc** <NAME>, <N |
| 1 | insurer_letter | `insurance_settlement` | # <NAME> settlement letter from <NAME> plc **<NAME> ID:** INS-<N> **<NAME>:** <DATE> **<NAME> plc** <NAME>/<NA |
| 1 | insurer_letter | `insurance_settlement` | # <NAME> settlement letter from <NAME> plc **<NAME> ID:** INS-<N> **<NAME>:** <DATE> <NAME> plc <NAME> are ple |
| 1 | insurer_letter | `insurance_settlement` | # <NAME> settlement letter from <NAME> plc **<NAME> ID:** INS-<N> **<NAME>:** <DATE> <NAME> plc <NAME> your cl |
| 1 | insurer_letter | `insurance_settlement` | # <NAME> settlement letter from <NAME> plc **<NAME> ID:** INS-<N> **<NAME>:** <DATE> <NAME> plc <NAME>, <NAME> |
| 1 | insurer_letter | `insurance_settlement` | # <NAME> settlement letter from <NAME> plc **<NAME> ID:** INS-<N> **<NAME>:** <DATE> <NAME> plc <NAME>: <NAME> |
| 1 | insurer_letter | `insurance_settlement` | # <NAME> settlement letter from <NAME> plc **<NAME> ID:** INS-<N> **<NAME>:** <DATE> <NAME>, <NAME> our assess |
| 1 | insurer_letter | `insurance_settlement` | # <NAME> settlement letter from <NAME> plc **<NAME> ID:** INS-<N> **<NAME>:** <DATE> <NAME>, <NAME> the assess |
| 1 | insurer_letter | `insurance_settlement` | # <NAME> settlement letter from <NAME> plc **<NAME> ID:** INS-<N> **<NAME>:** <DATE> <NAME>, I am writing to c |
| 1 | insurer_letter | `insurance_settlement` | # <NAME> settlement letter from <NAME> plc **<NAME> ID:** INS-<N> **<NAME>:** <DATE> <NAME>/<NAME>, <NAME> are |
| 1 | invoice | `invoice_matches_payment` | # <NAME> AS/<N> from <NAME> **<NAME> ID:** INV-<N> **<NAME>:** <DATE> **<NAME> to:** <NAME> **<NAME>:** <NAME> |
| 1 | invoice | `invoice_matches_payment` | # <NAME> BR/<N> from <NAME> **<NAME> ID:** INV-<N> **<NAME>:** <DATE> **<NAME> to:** <NAME> **<NAME>:** <NAME> |
| 1 | invoice | `invoice_matches_payment` | # <NAME> CO/<N> from <NAME> **<NAME> ID:** INV-<N> **<NAME>:** <DATE> **<NAME> to:** <NAME> **<NAME>:** <NAME> |
| 1 | invoice | `invoice_matches_payment` | # <NAME> FE/<N> from <NAME> **<NAME> ID:** INV-<N> **<NAME>:** <DATE> **<NAME> to:** <NAME> **<NAME>:** <NAME> |
| 1 | invoice | `invoice_matches_payment` | # <NAME> GA/<N> from <NAME> **<NAME> ID:** INV-<N> **<NAME>:** <DATE> **<NAME> to:** <NAME> **<NAME>:** <NAME> |
| 1 | invoice | `invoice_matches_payment` | # <NAME> GA/<N> from <NAME> **<NAME> ID:** INV-<N> **<NAME>:** <DATE> **<NAME> to:** <NAME> **<NAME>:** <NAME> |
| 1 | invoice | `invoice_matches_payment` | # <NAME> GL/<N> from <NAME> **<NAME> ID:** INV-<N> **<NAME>:** <DATE> **<NAME> to:** <NAME> **<NAME>:** <NAME> |
| 1 | invoice | `invoice_matches_payment` | # <NAME> KE/<N> from <NAME> **<NAME> ID:** INV-<N> **<NAME>:** <DATE> **<NAME> to:** <NAME> **<NAME>:** <NAME> |
| 1 | invoice | `invoice_matches_payment` | # <NAME> KI/<N> from <NAME> **<NAME> ID:** INV-<N> **<NAME>:** <DATE> **<NAME> to:** <NAME> **<NAME>:** <NAME> |
| 1 | invoice | `invoice_matches_payment` | # <NAME> KI/<N> from <NAME> **<NAME> ID:** INV-<N> **<NAME>:** <DATE> **<NAME> to:** <NAME> **<NAME>:** <NAME> |
| 1 | invoice | `invoice_matches_payment` | # <NAME> OA/<N> from <NAME> **<NAME> ID:** INV-<N> **<NAME>:** <DATE> **<NAME> to:** <NAME> **<NAME>:** <NAME> |
| 1 | invoice | `invoice_matches_payment` | # <NAME> PE/<N> from <NAME> **<NAME> ID:** INV-<N> **<NAME>:** <DATE> **<NAME> to:** <NAME> **<NAME>:** <NAME> |
| 1 | invoice | `invoice_matches_payment` | # <NAME> RA/<N> from <NAME> **<NAME> ID:** INV-<N> **<NAME>:** <DATE> **<NAME> to:** <NAME> **<NAME>:** <NAME> |
| 1 | invoice | `invoice_matches_payment` | # <NAME> SE/<N> from <NAME> **<NAME> ID:** INV-<N> **<NAME>:** <DATE> **<NAME> to:** <NAME> **<NAME>:** <NAME> |
| 1 | invoice | `invoice_matches_payment` | # <NAME> TA/<N> from <NAME> **<NAME> ID:** INV-<N> **<NAME>:** <DATE> **<NAME> to:** <NAME> **<NAME>:** <NAME> |
| 1 | invoice | `invoice_matches_payment` | # <NAME> TH/<N> from <NAME> **<NAME> ID:** INV-<N> **<NAME>:** <DATE> **<NAME> to:** <NAME> **<NAME>:** <NAME> |
| 1 | invoice | `invoice_matches_payment` | # <NAME> WE/<N> from <NAME> **<NAME> ID:** INV-<N> **<NAME>:** <DATE> **<NAME> to:** <NAME> **<NAME>:** <NAME> |
| 1 | invoice | `invoice_matches_payment` | # <NAME> WI/<N> from <NAME> **<NAME> ID:** INV-<N> **<NAME>:** <DATE> **<NAME> to:** <NAME> **<NAME>:** <NAME> |
| 1 | purchase_order | `purchase_order_documented` | # <NAME> order from <NAME> **<NAME> ID:** ORD-<N> **<NAME>:** <DATE> <NAME>: <NAME> - PO <N> - <NAME> <NAME>,  |
| 1 | purchase_order | `purchase_order_documented` | # <NAME> order from <NAME> **<NAME> ID:** ORD-<N> **<NAME>:** <DATE> <NAME>: <NAME> - PO <N> <NAME>, <NAME> fi |
| 1 | purchase_order | `purchase_order_documented` | # <NAME> order from <NAME> **<NAME> ID:** ORD-<N> **<NAME>:** <DATE> <NAME>: <NAME> - PO <N> <NAME>, <NAME> fi |
| 1 | purchase_order | `purchase_order_documented` | # <NAME> order from <NAME> **<NAME> ID:** ORD-<N> **<NAME>:** <DATE> <NAME>: <NAME>: PO <N> - <NAME> <NAME> te |
| 1 | purchase_order | `purchase_order_documented` | # <NAME> order from <NAME> **<NAME> ID:** ORD-<N> **<NAME>:** <DATE> <NAME>: <NAME>: PO <N> <NAME> team, <NAME |
| 1 | receipt | `purchase_receipt` | # <NAME> from <NAME> **<NAME> ID:** RCT-<N> **<NAME>:** <DATE> <NAME> there, <NAME> for booking onto our four- |
| 1 | receipt | `purchase_receipt` | # <NAME> from <NAME> **<NAME> ID:** RCT-<N> **<NAME>:** <DATE> <NAME>: <NAME> - <NAME> <NAME> there, <NAME> em |
| 1 | receipt | `purchase_receipt` | # <NAME> from <NAME> **<NAME> ID:** RCT-<N> **<NAME>:** <DATE> <NAME>: <NAME> - <NAME> <NAME> there, <NAME> yo |
| 1 | receipt | `purchase_receipt` | # <NAME> from <NAME> **<NAME> ID:** RCT-<N> **<NAME>:** <DATE> <NAME>: <NAME> booking confirmation <NAME> ther |
| 1 | receipt | `purchase_receipt` | # <NAME> from <NAME> **<NAME> ID:** RCT-<N> **<NAME>:** <DATE> <NAME>: <NAME> booking confirmation for <NAME>  |
| 1 | receipt | `purchase_receipt` | # <NAME> from <NAME> **<NAME> ID:** RCT-<N> **<NAME>:** <DATE> <NAME>: <NAME> for your booking at <NAME> <NAME |
| 1 | receipt | `purchase_receipt` | # <NAME> from <NAME> **<NAME> ID:** RCT-<N> **<NAME>:** <DATE> <NAME>: <NAME> for your order at <NAME> <NAME>, |
| 1 | receipt | `purchase_receipt` | # <NAME> from <NAME> **<NAME> ID:** RCT-<N> **<NAME>:** <DATE> <NAME>: <NAME> for your order from <NAME> <NAME |
| 1 | receipt | `purchase_receipt` | # <NAME> from <NAME> **<NAME> ID:** RCT-<N> **<NAME>:** <DATE> <NAME>: <NAME> order with <NAME> <NAME> there,  |
| 1 | receipt | `purchase_receipt` | # <NAME> from <NAME> **<NAME> ID:** RCT-<N> **<NAME>:** <DATE> <NAME>: <NAME>: <NAME> <NAME> student, <NAME> e |
| 1 | receipt | `purchase_receipt` | # <NAME> from <NAME> **<NAME> ID:** RCT-<N> **<NAME>:** <DATE> <NAME>: <NAME>: <NAME> <NAME>, <NAME> email con |
| 1 | receipt | `purchase_receipt` | # <NAME> from <NAME> **<NAME> ID:** RCT-<N> **<NAME>:** <DATE> <NAME>: <NAME>: <NAME>-week screen printing cou |
| 1 | redundancy_letter | `employment_payout` | # <NAME> from <NAME> **<NAME> ID:** RED-<N> **<NAME>:** <DATE> **<NAME>** <NAME>, <NAME> our recent consultati |
| 1 | redundancy_letter | `employment_payout` | # <NAME> from <NAME> **<NAME> ID:** RED-<N> **<NAME>:** <DATE> <NAME> <NAME>, <NAME> accept this letter as for |
| 1 | redundancy_letter | `employment_payout` | # <NAME> from <NAME> **<NAME> ID:** RED-<N> **<NAME>:** <DATE> <NAME> <NAME>, <NAME> our recent consultation p |
| 1 | redundancy_letter | `employment_payout` | # <NAME> from <NAME> **<NAME> ID:** RED-<N> **<NAME>:** <DATE> <NAME> <NAME>, <NAME> our recent consultation,  |
| 1 | redundancy_letter | `employment_payout` | # <NAME> from <NAME> **<NAME> ID:** RED-<N> **<NAME>:** <DATE> <NAME> <NAME>, <NAME> our recent consultations, |
| 1 | redundancy_letter | `employment_payout` | # <NAME> from <NAME> **<NAME> ID:** RED-<N> **<NAME>:** <DATE> <NAME>, <NAME> are writing to formally confirm  |
| 1 | redundancy_letter | `employment_payout` | # <NAME> from <NAME> LLP **<NAME> ID:** RED-<N> **<NAME>:** <DATE> <NAME> LLP <NAME> are writing to formally c |
| 1 | redundancy_letter | `employment_payout` | # <NAME> from <NAME> LLP **<NAME> ID:** RED-<N> **<NAME>:** <DATE> <NAME> LLP <NAME>, <NAME> are writing to fo |
| 1 | redundancy_letter | `employment_payout` | # <NAME> from <NAME> LLP **<NAME> ID:** RED-<N> **<NAME>:** <DATE> <NAME> LLP <NAME>, <NAME> our recent consul |
| 1 | redundancy_letter | `employment_payout` | # <NAME> from <NAME> LLP **<NAME> ID:** RED-<N> **<NAME>:** <DATE> <NAME> LLP <NAME>, <NAME> our recent consul |
| 1 | redundancy_letter | `employment_payout` | # <NAME> from <NAME> LLP **<NAME> ID:** RED-<N> **<NAME>:** <DATE> <NAME> LLP <NAME>, <NAME> our recent discus |
| 1 | redundancy_letter | `employment_payout` | # <NAME> from <NAME> plc **<NAME> ID:** RED-<N> **<NAME>:** <DATE> **<NAME> plc** <NAME>, <NAME> are writing t |
| 1 | redundancy_letter | `employment_payout` | # <NAME> from <NAME> plc **<NAME> ID:** RED-<N> **<NAME>:** <DATE> <NAME> plc <NAME> are writing to formally c |
| 1 | redundancy_letter | `employment_payout` | # <NAME> from <NAME> plc **<NAME> ID:** RED-<N> **<NAME>:** <DATE> <NAME> plc <NAME> are writing to formally n |
| 1 | redundancy_letter | `employment_payout` | # <NAME> from <NAME> plc **<NAME> ID:** RED-<N> **<NAME>:** <DATE> <NAME> plc <NAME>, <NAME> our recent consul |
| 1 | redundancy_letter | `employment_payout` | # <NAME> from <NAME> plc **<NAME> ID:** RED-<N> **<NAME>:** <DATE> <NAME> plc <NAME>, <NAME> our recent consul |
| 1 | redundancy_letter | `employment_payout` | # <NAME> from <NAME> plc **<NAME> ID:** RED-<N> **<NAME>:** <DATE> <NAME> plc <NAME>, <NAME> our recent discus |
| 1 | sale_receipt | `asset_sale` | # <NAME> sale receipt **<NAME> ID:** SAL-<N> **<NAME>:** <DATE> **<NAME> of <NAME>** **<NAME>:** <NAME> road b |
| 1 | sale_receipt | `asset_sale` | # <NAME> sale receipt **<NAME> ID:** SAL-<N> **<NAME>:** <DATE> **<NAME> of <NAME>** <NAME> description: <NAME |
| 1 | sale_receipt | `asset_sale` | # <NAME> sale receipt **<NAME> ID:** SAL-<N> **<NAME>:** <DATE> **<NAME> of <NAME>** <NAME> document confirms  |
| 1 | sale_receipt | `asset_sale` | # <NAME> sale receipt **<NAME> ID:** SAL-<N> **<NAME>:** <DATE> **<NAME> of <NAME>** <NAME> document serves as |
| 1 | sale_receipt | `asset_sale` | # <NAME> sale receipt **<NAME> ID:** SAL-<N> **<NAME>:** <DATE> **<NAME> of <NAME>** <NAME>: [<NAME>] I, <NAME |
| 1 | sale_receipt | `asset_sale` | # <NAME> sale receipt **<NAME> ID:** SAL-<N> **<NAME>:** <DATE> **<NAME> of <NAME>** I, <NAME>, have today sol |
| 1 | sale_receipt | `asset_sale` | # <NAME> sale receipt **<NAME> ID:** SAL-<N> **<NAME>:** <DATE> **<NAME>** **<NAME>:** <NAME> road bike, size  |
| 1 | sale_receipt | `asset_sale` | # <NAME> sale receipt **<NAME> ID:** SAL-<N> **<NAME>:** <DATE> **RECEIPT OF SALE** **<NAME>:** <NAME> road bi |
| 1 | sale_receipt | `asset_sale` | # <NAME> sale receipt **<NAME> ID:** SAL-<N> **<NAME>:** <DATE> **SALE RECEIPT** I, <NAME>, have today sold on |
| 1 | sale_receipt | `asset_sale` | # <NAME> sale receipt **<NAME> ID:** SAL-<N> **<NAME>:** <DATE> I, <NAME>, hereby acknowledge the sale of one  |
| 1 | settlement_letter | `employment_payout` | # <NAME> agreement letter from <NAME> **<NAME> ID:** SET-<N> **<NAME>:** <DATE> <NAME> 12th <NAME>, <NAME> <NA |
| 1 | settlement_letter | `employment_payout` | # <NAME> agreement letter from <NAME> **<NAME> ID:** SET-<N> **<NAME>:** <DATE> <NAME> <NAME>/<NAME>, <NAME> t |
| 1 | settlement_letter | `employment_payout` | # <NAME> agreement letter from <NAME> **<NAME> ID:** SET-<N> **<NAME>:** <DATE> <NAME> former employee, <NAME> |
| 1 | settlement_letter | `employment_payout` | # <NAME> agreement letter from <NAME> **<NAME> ID:** SET-<N> **<NAME>:** <DATE> <NAME> to the execution of our |
| 1 | settlement_letter | `employment_payout` | # <NAME> agreement letter from <NAME> **<NAME> ID:** SET-<N> **<NAME>:** <DATE> <NAME> to the settlement agree |
| 1 | settlement_letter | `employment_payout` | # <NAME> agreement letter from <NAME> **<NAME> ID:** SET-<N> **<NAME>:** <DATE> <NAME> to the settlement agree |
| 1 | settlement_letter | `employment_payout` | # <NAME> agreement letter from <NAME> **<NAME> ID:** SET-<N> **<NAME>:** <DATE> <NAME>, <NAME> the settlement  |
| 1 | settlement_letter | `employment_payout` | # <NAME> agreement letter from <NAME> **<NAME> ID:** SET-<N> **<NAME>:** <DATE> <NAME>/<NAME>, <NAME> letter s |
| 1 | settlement_letter | `employment_payout` | # <NAME> agreement letter from <NAME> **<NAME> ID:** SET-<N> **<NAME>:** <DATE> <NAME>: <NAME> <NAME> the form |
| 1 | solicitor_letter | `inheritance` | # <NAME> from <NAME> LLP **<NAME> ID:** SOL-<N> **<NAME>:** <DATE> **<NAME> LLP** <NAME>, <NAME> are writing t |
| 1 | solicitor_letter | `inheritance` | # <NAME> from <NAME> LLP **<NAME> ID:** SOL-<N> **<NAME>:** <DATE> <NAME> LLP <N> <NAME> <NAME> <NAME>, <NAME> |
| 1 | solicitor_letter | `inheritance` | # <NAME> from <NAME> LLP **<NAME> ID:** SOL-<N> **<NAME>:** <DATE> <NAME> firm has been instructed by the exec |
| 1 | solicitor_letter | `inheritance` | # <NAME> from <NAME> LLP **<NAME> ID:** SOL-<N> **<NAME>:** <DATE> <NAME> firm has been instructed by the exec |
| 1 | solicitor_letter | `inheritance` | # <NAME> from <NAME> LLP **<NAME> ID:** SOL-<N> **<NAME>:** <DATE> <NAME> firm is instructed by the executors  |
| 1 | solicitor_letter | `inheritance` | # <NAME> from <NAME> LLP **<NAME> ID:** SOL-<N> **<NAME>:** <DATE> <NAME>/<NAME>, **<NAME>: <NAME> of the late |
| 1 | solicitor_letter | `inheritance` | # <NAME> from <NAME> LLP **<NAME> ID:** SOL-<N> **<NAME>:** <DATE> <NAME>/<NAME>, <NAME> are instructed by the |
| 1 | staff_note | `structuring_enquiry` | # <NAME> by <NAME> report, <NAME> **<NAME> ID:** NTE-<N> **<NAME>:** <DATE> <NAME> attended the counter today  |
| 1 | staff_note | `structuring_enquiry` | # <NAME> by <NAME> report, <NAME> **<NAME> ID:** NTE-<N> **<NAME>:** <DATE> <NAME> came into the shop today an |
| 1 | staff_note | `structuring_enquiry` | # <NAME> by <NAME> report, <NAME> **<NAME> ID:** NTE-<N> **<NAME>:** <DATE> <NAME> came into the shop today to |
| 1 | staff_note | `structuring_enquiry` | # <NAME> by <NAME> report, <NAME> **<NAME> ID:** NTE-<N> **<NAME>:** <DATE> <NAME> came into the store today t |
| 1 | staff_note | `structuring_enquiry` | # <NAME> by <NAME> report, <NAME> **<NAME> ID:** NTE-<N> **<NAME>:** <DATE> <NAME> customer came in today and  |
| 1 | staff_note | `structuring_enquiry` | # <NAME> by <NAME> report, <NAME> **<NAME> ID:** NTE-<N> **<NAME>:** <DATE> <NAME> customer came into the stor |
| 1 | staff_note | `structuring_enquiry` | # <NAME> by <NAME> report, <NAME> **<NAME> ID:** NTE-<N> **<NAME>:** <DATE> <NAME> customer visited today to d |
| 1 | staff_note | `structuring_enquiry` | # <NAME> by <NAME> report, <NAME> **<NAME> ID:** NTE-<N> **<NAME>:** <DATE> <NAME> visited the branch today to |
| 1 | staff_note | `structuring_enquiry` | # <NAME> by <NAME> report, <NAME> **<NAME> ID:** NTE-<N> **<NAME>:** <DATE> <NAME> visited the counter to top  |
| 1 | staff_note | `structuring_enquiry` | # <NAME> by <NAME> report, <NAME> **<NAME> ID:** NTE-<N> **<NAME>:** <DATE> <NAME> visited the store and compl |
| 1 | staff_note | `structuring_enquiry` | # <NAME> by <NAME> report, <NAME> **<NAME> ID:** NTE-<N> **<NAME>:** <DATE> <NAME> visited the store and proce |
| 1 | staff_note | `structuring_enquiry` | # <NAME> by <NAME> report, <NAME> and <NAME> **<NAME> ID:** NTE-<N> **<NAME>:** <DATE> <NAME> came into the st |
| 1 | staff_note | `structuring_enquiry` | # <NAME> by <NAME> report, <NAME> and <NAME> **<NAME> ID:** NTE-<N> **<NAME>:** <DATE> <NAME> customer visited |
| 1 | staff_note | `structuring_enquiry` | # <NAME> by <NAME> report, <NAME> and <NAME> **<NAME> ID:** NTE-<N> **<NAME>:** <DATE> <NAME> customer visited |
| 1 | staff_note | `structuring_enquiry` | # <NAME> by <NAME> report, <NAME> and <NAME> **<NAME> ID:** NTE-<N> **<NAME>:** <DATE> <NAME> visited the coun |
| 1 | staff_note | `structuring_enquiry` | # <NAME> by <NAME> report, <NAME> and <NAME> **<NAME> ID:** NTE-<N> **<NAME>:** <DATE> <NAME> visited the outl |
| 1 | staff_note | `structuring_enquiry` | # <NAME> by <NAME> report, <NAME> and <NAME> **<NAME> ID:** NTE-<N> **<NAME>:** <DATE> <NAME> visited the stor |
| 1 | staff_note | `structuring_enquiry` | # <NAME> by <NAME> report, <NAME> office, <NAME> **<NAME> ID:** NTE-<N> **<NAME>:** <DATE> <NAME> customer app |
| 1 | staff_note | `structuring_enquiry` | # <NAME> by <NAME> report, <NAME> office, <NAME> **<NAME> ID:** NTE-<N> **<NAME>:** <DATE> <NAME> customer cam |
| 1 | staff_note | `structuring_enquiry` | # <NAME> by <NAME> report, <NAME> office, <NAME> **<NAME> ID:** NTE-<N> **<NAME>:** <DATE> <NAME> customer com |
| 1 | staff_note | `structuring_enquiry` | # <NAME> by <NAME> report, <NAME> office, <NAME> **<NAME> ID:** NTE-<N> **<NAME>:** <DATE> <NAME> customer dep |
| 1 | staff_note | `structuring_enquiry` | # <NAME> by <NAME> report, <NAME> office, <NAME> **<NAME> ID:** NTE-<N> **<NAME>:** <DATE> <NAME> customer pro |
| 1 | staff_note | `structuring_enquiry` | # <NAME> by <NAME> report, <NAME> office, <NAME> **<NAME> ID:** NTE-<N> **<NAME>:** <DATE> <NAME> visited the  |
| 1 | staff_note | `structuring_enquiry` | # <NAME> by <NAME>, <NAME> branch **<NAME> ID:** NTE-<N> **<NAME>:** <DATE> <NAME> attended the <NAME> branch  |
| 1 | staff_note | `structuring_enquiry` | # <NAME> by <NAME>, <NAME> branch **<NAME> ID:** NTE-<N> **<NAME>:** <DATE> <NAME> attended the branch today t |
| 1 | staff_note | `structuring_enquiry` | # <NAME> by <NAME>, <NAME> branch **<NAME> ID:** NTE-<N> **<NAME>:** <DATE> I assisted <NAME> today, who came  |
| 1 | staff_note | `structuring_enquiry` | # <NAME> by <NAME>, <NAME> branch **<NAME> ID:** NTE-<N> **<NAME>:** <DATE> I spoke with <NAME> today at the < |
| 1 | staff_note | `structuring_enquiry` | # <NAME> by <NAME>, <NAME> branch **<NAME> ID:** NTE-<N> **<NAME>:** <DATE> I spoke with <NAME> today when the |
| 1 | staff_note | `high_risk_routing_unexplained` | # <NAME> from the client relationship team **<NAME> ID:** NTE-<N> **<NAME>:** <DATE> <NAME> with a representat |
| 1 | staff_note | `high_risk_routing_unexplained` | # <NAME> from the client relationship team **<NAME> ID:** NTE-<N> **<NAME>:** <DATE> I held a follow-up call w |
| 1 | staff_note | `structuring_enquiry` | # <NAME> from the client relationship team **<NAME> ID:** NTE-<N> **<NAME>:** <DATE> I received a call from th |
| 1 | staff_note | `high_risk_routing_unexplained` | # <NAME> from the client relationship team **<NAME> ID:** NTE-<N> **<NAME>:** <DATE> I spoke with a representa |
| 1 | staff_note | `high_risk_routing_unexplained` | # <NAME> from the client relationship team **<NAME> ID:** NTE-<N> **<NAME>:** <DATE> I spoke with the director |
| 1 | staff_note | `high_risk_routing_unexplained` | # <NAME> from the client relationship team **<NAME> ID:** NTE-<N> **<NAME>:** <DATE> I spoke with the manageme |
| 1 | supplier_invoice | `invoice_matches_payment` | # <NAME> INV <N> from <NAME>. z o.o. **<NAME> ID:** INV-<N> **<NAME>:** <DATE> **<NAME>:** <NAME>. z o.o., <NA |
| 1 | supplier_invoice | `invoice_matches_payment` | # <NAME> for order PO <N> from <NAME> GmbH **<NAME> ID:** INV-<N> **<NAME>:** <DATE> **<NAME>:** <NAME> GmbH,  |
| 1 | supply_contract | `business_contract` | # <NAME> contract with <NAME> **<NAME> ID:** CON-<N> **<NAME>:** <DATE> <NAME> agreement confirms the supply a |
| 1 | supply_contract | `business_contract` | # <NAME> contract with <NAME> **<NAME> ID:** CON-<N> **<NAME>:** <DATE> <NAME> agreement formalizes a supply a |
| 1 | supply_contract | `business_contract` | # <NAME> contract with <NAME> **<NAME> ID:** CON-<N> **<NAME>:** <DATE> <NAME> agreement outlines the terms be |
| 1 | supply_contract | `business_contract` | # <NAME> contract with <NAME> **<NAME> ID:** CON-<N> **<NAME>:** <DATE> <NAME> agreement outlines the terms fo |
| 1 | supply_contract | `business_contract` | # <NAME> contract with <NAME> **<NAME> ID:** CON-<N> **<NAME>:** <DATE> <NAME> contract confirms that <NAME>,  |
| 1 | supply_contract | `business_contract` | # <NAME> contract with <NAME> **<NAME> ID:** CON-<N> **<NAME>:** <DATE> <NAME> supply agreement is entered int |
| 1 | support_chat | `medical_treatment_abroad` | # <NAME> with the customer **<NAME> ID:** CHT-<N> **<NAME>:** <DATE> **<NAME>:** <NAME> there, I’m reaching ou |
| 1 | support_chat | `cash_withdrawal_returned` | # <NAME> with the customer **<NAME> ID:** CHT-<N> **<NAME>:** <DATE> **<NAME>:** <NAME> there, I’ve just depos |
| 1 | support_chat | `loan_from_friend_claim` | # <NAME> with the customer **<NAME> ID:** CHT-<N> **<NAME>:** <DATE> **<NAME>:** <NAME> there. <NAME>’ve flagg |
| 1 | support_chat | `loan_from_friend_claim` | # <NAME> with the customer **<NAME> ID:** CHT-<N> **<NAME>:** <DATE> **<NAME>:** <NAME> you for contacting sup |
| 1 | support_chat | `medical_treatment_abroad` | # <NAME> with the customer **<NAME> ID:** CHT-<N> **<NAME>:** <DATE> **<NAME>:** <NAME> you for reaching out.  |
| 1 | support_chat | `cash_withdrawal_returned` | # <NAME> with the customer **<NAME> ID:** CHT-<N> **<NAME>:** <DATE> **<NAME>:** <NAME>, I just wanted to upda |
| 1 | support_chat | `loan_from_friend_claim` | # <NAME> with the customer **<NAME> ID:** CHT-<N> **<NAME>:** <DATE> **<NAME>:** <NAME>, I'm reaching out beca |
| 1 | support_chat | `cash_withdrawal_returned` | # <NAME> with the customer **<NAME> ID:** CHT-<N> **<NAME>:** <DATE> **<NAME>:** <NAME>, I’ve just deposited t |
| 1 | support_chat | `medical_treatment_abroad` | # <NAME> with the customer **<NAME> ID:** CHT-<N> **<NAME>:** <DATE> **<NAME>:** <NAME>, thanks for reaching o |
| 1 | support_chat | `medical_treatment_abroad` | # <NAME> with the customer **<NAME> ID:** CHT-<N> **<NAME>:** <DATE> **<NAME>:** <NAME>, this is support. <NAM |
| 1 | support_chat | `loan_from_friend_claim` | # <NAME> with the customer **<NAME> ID:** CHT-<N> **<NAME>:** <DATE> **<NAME>:** <NAME>, this is support. <NAM |
| 1 | support_chat | `medical_treatment_abroad` | # <NAME> with the customer **<NAME> ID:** CHT-<N> **<NAME>:** <DATE> **<NAME>:** <NAME>, we are contacting you |
| 1 | support_chat | `medical_treatment_abroad` | # <NAME> with the customer **<NAME> ID:** CHT-<N> **<NAME>:** <DATE> **<NAME>:** <NAME>, we are reviewing your |
| 1 | support_chat | `medical_treatment_abroad` | # <NAME> with the customer **<NAME> ID:** CHT-<N> **<NAME>:** <DATE> **<NAME>:** <NAME>, we are reviewing your |
| 1 | support_chat | `loan_from_friend_claim` | # <NAME> with the customer **<NAME> ID:** CHT-<N> **<NAME>:** <DATE> **<NAME>:** <NAME>, we have flagged some  |
| 1 | support_chat | `loan_from_friend_claim` | # <NAME> with the customer **<NAME> ID:** CHT-<N> **<NAME>:** <DATE> **<NAME>:** <NAME>, we have observed a se |
| 1 | venue_email | `refund` | # <NAME> from <NAME> and <NAME> **<NAME> ID:** EML-<N> **<NAME>:** <DATE> <NAME> client, <NAME> were sorry to  |
| 1 | venue_email | `refund` | # <NAME> from <NAME> and <NAME> **<NAME> ID:** EML-<N> **<NAME>:** <DATE> <NAME> valued client, <NAME> are wri |
| 1 | venue_email | `refund` | # <NAME> from <NAME> and <NAME> **<NAME> ID:** EML-<N> **<NAME>:** <DATE> <NAME> valued guest, <NAME> were sor |
| 1 | venue_email | `refund` | # <NAME> from <NAME> and <NAME> **<NAME> ID:** EML-<N> **<NAME>:** <DATE> <NAME>, <NAME> were saddened to hear |
| 1 | venue_email | `refund` | # <NAME> from <NAME> and <NAME> **<NAME> ID:** EML-<N> **<NAME>:** <DATE> <NAME>, <NAME> were very sorry to he |
| 1 | venue_email | `refund` | # <NAME> from <NAME> and <NAME> **<NAME> ID:** EML-<N> **<NAME>:** <DATE> <NAME>: <NAME> - BOOKING <N> <NAME>  |
| 1 | venue_email | `refund` | # <NAME> from <NAME> and <NAME> **<NAME> ID:** EML-<N> **<NAME>:** <DATE> <NAME>: <NAME> and <NAME> - BOOKING  |
| 1 | venue_email | `refund` | # <NAME> from <NAME> and <NAME> **<NAME> ID:** EML-<N> **<NAME>:** <DATE> <NAME>: <NAME> of <NAME> - BOOKING < |
| 1 | venue_email | `refund` | # <NAME> from <NAME> and <NAME> **<NAME> ID:** EML-<N> **<NAME>:** <DATE> <NAME>: <NAME> of your booking - BOO |
| 1 | venue_email | `refund` | # <NAME> from <NAME> and <NAME> **<NAME> ID:** EML-<N> **<NAME>:** <DATE> <NAME>: <NAME> of your booking at <N |
| 1 | venue_email | `refund` | # <NAME> from <NAME> and <NAME> **<NAME> ID:** EML-<N> **<NAME>:** <DATE> <NAME>: <NAME> of your wedding booki |

