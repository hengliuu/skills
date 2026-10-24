# Worked examples

## Contents

- [Before and after](#before-and-after)
- [A good intent](#a-good-intent)
- [What the interview sounded like](#what-the-interview-sounded-like)

Read this when you want to see the failure modes concretely — a weak intent rewritten,
and a good one for reference.

- [Before and after](#before-and-after)
- [A good intent](#a-good-intent)
- [What the interview sounded like](#what-the-interview-sounded-like)

## Before and after

What a requester typically hands over, written up without an interview:

```markdown
# Intent: WhatsApp notification feature
Author: Rina. Status: draft.

## Problem
Customers don't know their delivery status. We need to send them WhatsApp
notifications when the order status changes.

## Proposed outcome
WhatsApp notification sent on every status change.

## Affected users and systems
Order system.

## Constraints
-

## Open questions
-
```

Four things are wrong, and they are the four that always go wrong:

| Problem | Why it costs later |
| --- | --- |
| The solution is in the title and in every section | Nobody will now check whether SMS is cheaper, or whether the real issue is an unfindable tracking page |
| "Customers don't know" has no number | Nothing to measure success against, and no way to argue for the budget |
| Constraints empty | Nobody asked. The PII limit surfaces during implementation instead |
| Open questions empty | The corporate-customer question resurfaces in week three as rework |

After the interview:

```markdown
# Intent: pelanggan tidak tahu status kiriman
Author: Rina (customer support). Status: draft.
Source: meeting ops 2026-09-01; keluhan CS minggu 34-35.

## Problem
CS menerima ~40 telepon/hari yang isinya hanya "paket saya di mana". Tim CS
menghabiskan ~3 jam sehari untuk pertanyaan yang jawabannya sudah ada di sistem.

## Proposed outcome
Pelanggan bisa tahu status kiriman tanpa menghubungi CS.

## Success measure
Telepon "paket saya di mana" turun dari ~40/hari ke di bawah 10/hari, dibaca dari
kategori tiket di log CS, dicek 30 hari setelah rilis.

## Affected users and systems
Pelanggan ritel, tim CS, sistem order, layanan kurir pihak ketiga.

## Constraints
Nomor telepon pelanggan tidak boleh keluar dari sistem kami.
Tidak ada anggaran vendor baru kuartal ini — harus pakai channel yang sudah ada.

## Risks
API tracking kurir pihak ketiga bisa berubah tanpa pemberitahuan — dipantau tim order.
Puncak volume akhir tahun jatuh dua minggu setelah target rilis.

## Open questions
Pelanggan korporat perlu akses yang sama, atau cukup ritel?
Kurir mana saja yang sudah punya API tracking?
```

Same request. WhatsApp is gone, and the design stage is now free to find that the
cheapest fix is a tracking link in the existing order-confirmation email.

## A good intent

The upstream playbook's own example, for reference:

```markdown
# Intent: claims status self-service
Author: J. Ortiz (claims operations). Status: draft.

## Problem
Customers phone the contact center to ask where their claim is.

## Proposed outcome
Customers see claim status, next step and expected date in the portal.

## Affected users and systems
Claims handlers, portal team, claims-core API.

## Constraints
No new PII in the portal session. Existing authentication only.

## Open questions
Do third-party loss adjusters need access too?
```

Note how short it is. Length is not the goal — a page of prose usually means a spec
wearing an intent's heading structure.

## What the interview sounded like

The delta between the two versions above came from six questions, asked one at a time:

1. "Kalau notifikasi ini tidak pernah dibuat, apa yang rusak hari ini?"
   → surfaces the CS load rather than the missing feature
2. "Berapa banyak? Ada catatannya?"
   → produces the 40/day and the 3 hours
3. "Yang telepon itu pelanggan ritel, korporat, atau dua-duanya?"
   → the requester doesn't know; becomes an open question rather than an assumption
4. "Data pelanggan apa yang tidak boleh keluar dari sistem kita?"
   → the phone-number constraint, never mentioned in the meeting
5. "Ada anggaran untuk vendor baru kuartal ini?"
   → the budget constraint, which quietly rules out several designs
6. "Apa lagi yang belum jelas buat kamu sendiri?"
   → the carrier-API question

Question 6 is worth asking every time. It reliably returns something, and requesters
rarely offer it unless invited.
