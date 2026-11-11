# REV PR48 Missing review records r1 / 欠落レビュー記録のレビュー r1

> **Summary:** The nine references match the real review comments; the new seven-column data tables need the format required by SPEC-06 §4.
> **概要:** 9 件の参照は実際のレビューコメントと一致する。追加した 7 列のデータ表は SPEC-06 §4 の形式に修正が必要。

**Jump:** [English](#english) · [日本語](#japanese)

- Version / 版: 0.1 — 2026-11-12. **Learned:** passing automated documentation checks does not prove compliance with the data-format rule, which requires manual review. ／ 文書の自動検査に合格しても、データ形式の規則への適合は証明されず、人による確認が必要と分かった。
- Applies to: [RDM-developer-guide PR #48](https://github.com/RCOSDP/RDM-developer-guide/pull/48), head `01709926bcba997fb8eb1ccb502bfdcaf670f872`, base `f4199fb3c6cc49fd93816c4896d8a56380cf57d8`.
- Related: [Review index](../pr48-rev-r1/docs/reviews/README.md) · [SPEC-06](../pr48-rev-r1/docs/spec/06_documentation_conventions.md) · [ADR-04](../pr48-rev-r1/docs/decisions/ADR-04_AI_Autonomy_and_Roles.md).
- Used by: [PR #48](https://github.com/RCOSDP/RDM-developer-guide/pull/48).

---

<a id="english"></a>
## English

[→ 日本語版へ](#japanese)

### Verdict and finding

**changes requested** for one documentation-format issue. Review date: 2026-11-12. Reviewer: REV (Codex Astra). The scope is the README change in PR #48, titled “docs(review): 保存されなかった 9 件のレビュー記録を注記し、代わりの PR コメントを示す”.

**R1-01 / P2 — Use TOON for the record data.** `docs/reviews/README.md:56–66` and `114–124` add nine records with seven fields each. SPEC-06 §4 requires document data in a `toon` fenced block and reserves tables for comparisons with few columns. These are record inventories, not compact comparisons. Convert both inventories to TOON while retaining every value and the scope restrictions on the two pass verdicts. Translate those scope descriptions into English in the English half. No new machine-readable canonical file is necessary for this documentation-only inventory. The automated checker does not enforce this format rule.

### Evidence and scope

A fresh clone under `scratchpad/pr48-rev-r1` was clean before and after review. The PR changes only `docs/reviews/README.md` (38 insertions, one deletion). Removing the two new sections and reversing the version-header update reproduces the base file byte for byte; no other existing content changed. The new Version 0.2 header records a lesson and preserves Version 0.1.

Read-only `gh api` requests retrieved the comments from each PR and by comment ID. Every ID belongs to the stated PR in RDM-osf.io-dev2027, every body starts with `REV（担当レビュワ`, and every round, verdict, reviewed head and UTC minute matches. PR #11 r3 uses capitalized “Pass” and names the head as the endpoint of its reviewed range. PR #8 r3 and #11 r3 are limited passes, not whole-PR approvals; the table preserves those limitations. Exact UTC posting times are recorded here:

```toon
records[9]{pr,round,comment_id,created_at_utc,verdict,reviewed_head}:
  8,r1,6757009993,2026-11-10T02:12:35Z,changes requested,e7f23e13141f
  8,r2,6758141691,2026-11-10T03:28:56Z,changes requested,8bb07f17c2
  8,r3,6759472716,2026-11-10T05:03:01Z,pass (R2 changes only),49e5521451
  10,r1,6759171742,2026-11-10T04:41:17Z,changes requested,5355858363b6
  11,r1,6759274738,2026-11-10T04:48:29Z,changes requested,75ceaf5cb492
  11,r2,6760403905,2026-11-10T06:08:17Z,changes requested,58ba83af4b7c
  11,r3,6763524193,2026-11-10T09:13:37Z,pass (58ba83a..3eb4042 only),3eb4042
  12,r1,6763575801,2026-11-10T09:16:17Z,changes requested,aa30a37d
  13,r1,6763600948,2026-11-10T09:17:37Z,changes requested,ef9e64261b
```

The English and Japanese inventories contain identical values, and the surrounding prose has the same meaning. The English verdict cells still use Japanese explanatory labels; translate them during R1-01. No private repository URL appears in the README. Anchors, Jump links, relative links and version structure pass inspection. The explanation that records were lost and the owner's 2026-11-12 decision are task-supplied history; the surviving comments cannot independently prove that history.

### Validation

Run from the clean clone root `scratchpad/pr48-rev-r1`:

```sh
python3 tools/docs_check.py
python3 tools/manifest_check.py
git diff --check f4199fb3c6cc49fd93816c4896d8a56380cf57d8...HEAD
```

All three exit codes were 0. `docs_check` checked 174 files, exempted eight, and reported 38 nonfatal glossary warnings outside the modified file. `manifest_check` reported zero manifest findings and zero policy findings, scanning 726 text files and skipping 63 non-UTF-8 files. A row-verification probe initially compared “pass” case-sensitively and stopped on “Pass”; the corrected case-insensitive comparison completed all nine rows successfully. That was a probe issue, not a source-data discrepancy.

No source files were edited. This record is uncommitted. No merge, approval, closure, push, commit, Docker state change, or runtime/.env access was performed. R1-01 remains for the author.

---

<a id="japanese"></a>
## 日本語

[→ To English](#english)

### 判定と指摘

文書形式の指摘 1 件により **changes requested（要修正）**。レビュー日は 2026-11-12、担当は REV（Codex Astra）。範囲は PR #48「docs(review): 保存されなかった 9 件のレビュー記録を注記し、代わりの PR コメントを示す」の README 差分。

**R1-01 / P2 — 記録データを TOON にする。** `docs/reviews/README.md:56–66` と `114–124` は、各 7 項目の記録 9 件を追加している。SPEC-06 §4 は文書中のデータを `toon` コードブロックで記載し、表を列の少ない比較に限定している。今回の一覧は記録データであり、少数列の比較ではない。英日両方を TOON に変え、全値と pass 2 件の対象範囲を保持すること。英語側の対象範囲の説明は英訳すること。文書だけの一覧なので、機械向け正本ファイルの新設は不要。自動検査はこの形式規則を検査しない。

### 証拠と範囲

`scratchpad/pr48-rev-r1` に新規 clone し、レビュー前後とも作業ツリーは clean だった。変更ファイルは `docs/reviews/README.md` のみで、38 行追加・1 行削除。新設した英日 2 節を除き、版ヘッダを元に戻すと基点のファイルとバイト単位で一致し、それ以外の既存内容は変わっていない。新しい Version 0.2 は学びを記録し、Version 0.1 を保持している。

読み取り専用の `gh api` で PR ごとのコメント一覧とコメント ID ごとの内容を取得した。全 ID は RDM-osf.io-dev2027 の指定 PR に属し、本文はすべて `REV（担当レビュワ` で始まる。回、判定、対象の先頭、UTC の分まで一致した。PR #11 r3 は大文字始まりの “Pass” で、対象の先頭はレビュー範囲の終点として記載されている。PR #8 r3 と #11 r3 は差分限定の合格で、PR 全体の承認ではない。表もこの限定を保持している。正確な UTC 投稿日時は次のとおり。

```toon
records[9]{pr,round,comment_id,created_at_utc,verdict,reviewed_head}:
  8,r1,6757009993,2026-11-10T02:12:35Z,changes requested,e7f23e13141f
  8,r2,6758141691,2026-11-10T03:28:56Z,changes requested,8bb07f17c2
  8,r3,6759472716,2026-11-10T05:03:01Z,pass (R2 changes only),49e5521451
  10,r1,6759171742,2026-11-10T04:41:17Z,changes requested,5355858363b6
  11,r1,6759274738,2026-11-10T04:48:29Z,changes requested,75ceaf5cb492
  11,r2,6760403905,2026-11-10T06:08:17Z,changes requested,58ba83af4b7c
  11,r3,6763524193,2026-11-10T09:13:37Z,pass (58ba83a..3eb4042 only),3eb4042
  12,r1,6763575801,2026-11-10T09:16:17Z,changes requested,aa30a37d
  13,r1,6763600948,2026-11-10T09:17:37Z,changes requested,ef9e64261b
```

英日一覧の値は同一で、周囲の説明も同じ意味だった。英語側の判定欄には日本語の説明が残るため、R1-01 の修正時に英訳する。README に非公開リポジトリの URL はない。アンカー、Jump、相対リンク、版構成を確認した。記録喪失の経緯と所有者の 2026-11-12 の決定は依頼で与えられた履歴であり、現存するコメントだけでは独立に証明できない。

### 検査

実行場所は clean clone のルート `scratchpad/pr48-rev-r1`。

```sh
python3 tools/docs_check.py
python3 tools/manifest_check.py
git diff --check f4199fb3c6cc49fd93816c4896d8a56380cf57d8...HEAD
```

3 コマンドとも終了コードは 0。`docs_check` は 174 ファイルを検査し、8 件を免除、変更対象以外で失敗扱いではない用語注警告 38 件を報告した。`manifest_check` は manifest・公開方針とも指摘 0 件で、テキスト 726 ファイルを検査し、非 UTF-8 の 63 ファイルを除外した。行照合用の初回 probe は “pass” と “Pass” の大文字小文字の違いで停止したが、大小文字を正規化した照合では全 9 件が成功した。これは probe の問題で、元データの不一致ではない。

ソースファイルは未編集で、この記録は未コミット。merge・approve・close・push・commit、Docker の状態変更、runtime/.env の参照は行っていない。作者の残作業は R1-01 の修正。
