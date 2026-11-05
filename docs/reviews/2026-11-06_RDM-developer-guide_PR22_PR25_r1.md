# REV PR22 and PR25 review r1 / PR22・PR25 レビュー r1

> **Summary:** Independent review of the pinned integration revisions and the 2027 environment guide. Both proposals need documentation corrections; all eleven integration revisions and the manifest excerpt passed verification.
> **概要:** 統合版の固定と 2027 環境ガイドを独立レビューした。両提案とも文書修正が必要だが、統合版 11 件とマニフェスト抄録の照合は合格した。

**Jump:** [English](#english) · [日本語](#japanese)

- Version / 版: 0.1 — 2026-11-06. **Learned:** correct pinned revisions do not prove that status history or the documented security commands are correct; each requires separate evidence. ／ 固定版が正しくても、進捗履歴やセキュリティ検査コマンドの説明が正しい証拠にはならず、それぞれの根拠が必要と分かった。
- Applies to: PR (pull request, a proposed change awaiting review) #22 and #25 of RDM-developer-guide; reviewer REV（担当レビュワ, Codex Astra）.
- Related: [Review index](README.md) · [SPEC-01](../spec/01_manifest.md) · [SPEC-02](../spec/02_installer_cli.md) · [SPEC-03](../spec/03_security_gate.md) · [SPEC-06](../spec/06_documentation_conventions.md) · [ADR-02](../decisions/ADR-02_Network_Model.md)
- Used by: [Status board](../status/README.md) · [Environment guide](../guides/environment/README.md)

---

<a id="english"></a>
## English

[→ 日本語版へ](#japanese)

### Scope and verdicts

Working brief: review both proposals using GitHub CLI reads, compare their claims with the specifications and implementation, record findings bilingually, and post one Japanese comment per proposal. No approval, merge, commit, push, or Docker execution was performed.

A SHA is the 40-character fingerprint of a saved code revision. A manifest is a list of components and their fixed revisions. TOON is a compact text representation of structured data. Evidence was fetched with `gh pr diff` and `gh api .../contents/<path>?ref=<branch>`; line numbers refer to the reviewed proposal files and the fetched develop reference files.

- **PR #22: changes requested for the status wording (22-01); revision pinning passes.** Reviewed public proposal head `c3cdf706a83a45a94c403bdbafe9fc2f1e31f8e0`.
- **PR #25: changes requested, including two high-priority security-check descriptions.** Reviewed public proposal head `b37c71e1024611485aebb6d9d8b63878b7ae4db6`.
- Reference develop revision: `e2f3858eac63b990a27158314889c406aa9a42a6`. No full startup, image build, browser acceptance test, or live security scan was attempted. Verdicts are review recommendations, not GitHub approval/review submissions.

### PR #22 verification

All eleven non-infrastructure components have lowercase 40-hex `integration_sha` values matching their integration repository's live develop tip. The following is review evidence, not a canonical manifest excerpt; private repositories are named without links.

```toon
verified[11]{repository,develop_tip_matches,hex40}:
  RDM-osf.io-dev2027,yes,yes
  RDM-waterbutler-dev2027,yes,yes
  RDM-modular-file-renderer-dev2027,yes,yes
  RDM-ember-osf-web-dev2027,yes,yes
  RDM-cas-overlay-dev2027,yes,yes
  RDM-wiki-frontend-dev2027,yes,yes
  RDM-y-websocket-dev2027,yes,yes
  RDM-OASys-dev2027,yes,yes
  RDM-Shibboleth-SP-dev2027,yes,yes
  RDM-rdmcp-dev2027,yes,yes
  RDM-aipf_mcp_data_grdm-dev2027,yes,yes
```

The branch-tip check used `gh api repos/RCOSDP/<repo>/branches/develop --jq .commit.sha`. Wiki also matches both RDM-wiki-frontend and RDM-wiki-frontend-develop-private develop tips. OASys, rdmcp, and aipf match the main tips of RDM-OASys-main-private, RDM-rdmcp-private, and RDM-aipf_mcp_data_grdm-private respectively. Infrastructure entries were excluded from remote queries.

From a temporary copy, the following check returned exit 0 and zero findings:

```bash
cd /tmp/rev-pr22-pr25
python3 tools/manifest_check.py --manifest-only
```

This validates the manifest and TOON projection. The projection does not include `integration_sha`, so the unchanged TOON file is correct. A repository-wide policy scan was not claimed from this partial temporary copy.

The seven strict reconstruction merges were confirmed through `gh pr list --state merged --base develop`: osf.io #2 and waterbutler, modular-file-renderer, ember-osf-web, cas-overlay, y-websocket, Shibboleth-SP #1. They occurred on 2026-11-05 at 19:25 UTC, which is 2026-11-06 JST; the board's date is correct in the team's timezone.

### Ranked findings for PR #22

- **22-01 / P2 — Correct “no PR” to “PR #1 closed without merge; tips identical.”** `docs/status/README.md:38` and `:79` say wiki-frontend had no PR. GitHub reports RDM-wiki-frontend-dev2027 #1 created at 2026-11-05 11:09:10 UTC and closed at 11:21:58 UTC, with no merge. The identical-tip claim is verified, but the historical claim is false in both languages. Keep the seven-merge count and correct the wiki history.
- **22-02 / P3 — Update the board's version and clarify superseded review status.** `docs/status/README.md:8` retains the November 5 version despite this edit; SPEC-06 §6 requires a version update with the change. Existing rows `:41` / `:82` still present osf.io #1 decisions as pending although #1 is closed and #2 merged. These stale rows predate this proposal; mark them historical/superseded when touching the board.

### Ranked findings for PR #25

All guide evidence below refers to `docs/guides/environment/README.md`; each pair gives English and Japanese lines.

- **25-01 / P1 — The “whole security gate” command skips vulnerability analysis.** Lines 180–188 / 509–517 use `scan --baseline --secrets` and promise CVE (a public identifier for a known weakness) threshold results. SPEC-02 §3 and `installer/grdm_dev/scan.py:902`, `:932`, `:940`, `:944` show that these flags select only baseline and secret checks; Trivy, Semgrep and ZAP run in the unfiltered scan. Show `scan` for the full gate, or accurately label the subset; explain milestone rules and missing-scanner exit 51 (and exit 52 for unavailable dynamic checks).
- **25-02 / P1 — The documented health command does not check host exposure.** Lines 171–176 / 500–505 and 309 / 638 promise rejection of non-loopback listeners for plain `health`. SPEC-02 §3, SPEC-03 §3.2 and `installer/grdm_dev/health.py:314`, `:330` require `health --network` for that check. Add the flag wherever that guarantee is made, preventing a healthy response from being mistaken for proof of network isolation.
- **25-03 / P2 — Correct exit-code claims.** Lines 95 / 424 classify missing Docker as 10, but SPEC-02 §6 assigns 11. Lines 135 / 464 say rendering never fails and call 0 a failure code; `installer/grdm_dev/compose.py:746`, `:750`, `:775`, `:784` return 20, 2 and 12. Document 0 as success and the real failure cases; this also removes the contradiction with the guide's own troubleshooting section.
- **25-04 / P2 — Distinguish the installation sequence from optional manual tests.** Lines 83 / 412 say the installer runs all listed steps; lines 90 / 419 invoke the entire installer under the doctor heading. SPEC-02 §2.1 and `installer/grdm_dev/install.py:39`–`:51` instead run doctor → plan → secrets → render → build → up → health --network → scan → report, without accept. Show the doctor-only command after bootstrap and place acceptance outside that automatic sequence.
- **25-05 / P2 — Make acceptance instructions executable and describe seed lifetime.** Lines 195–202 / 524–531 omit the optional Python dependencies and Chromium preparation required by SPEC-02 §2.2 and `installer/grdm_dev/accept.py:574`–`:585`. They also suggest running `accept --seed` first to prepare users, but `:619`–`:636` creates users, runs tests, then removes them in the same invocation. Show setup in the existing virtual environment and run the desired acceptance test with `--seed`; do not imply a persistent preparatory seed step.
- **25-06 / P2 — Do not promise read-only roots for every service.** Lines 265 / 594 overstate SPEC-03 §3.3 (`docs/spec/03_security_gate.md:74`), which permits documented per-service exceptions in `manifest/hardening.json`. Explain the exception mechanism and link its record. The random-secret, 0600 file mode, loopback-only publishing and digest-policy statements otherwise match SPEC-03 §3 as requirements, without proving live compliance.
- **25-07 / P2 — Use the chosen port in quick-start results.** Lines 29 / 358 and 162 / 491 hardcode port 5000 although the guide correctly describes reassignment at 280 / 609. `installer/grdm_dev/compose.py:210` searches from the requested port through +100, preserving owned bindings, and `:784` returns 12 only if none is free. Tell readers to use the reported URL or recorded port. The +100 description should say “requested/saved port”, not always “default”, because saved overrides also feed the search.
- **25-08 / P2 — Correct the current fallback state and bilingual timing.** Line 8 explicitly labels full startup unverified, which is good, but says in English that fallback images will be added *once* Dockerfiles update while Japanese says *until* they update. The ember fallback is already present in `manifest/upstreams.json:409` and `:415` (note and prebuilt image); DEMO-20 records the decision. State that it is already configured until modernization and preserve the unverified-startup caveat near quick start. A failed source build does not prove the configured fallback also fails.
- **25-09 / P2 — Ground the old/new table in the actual legacy guide.** Lines 321–322 / 650–651 attribute manual `docker pull` and `postgres/postgres` credentials to README.legacy.md, but neither appears there. Its lines 33, 36–39 and 47–56 describe the alias, copied local settings, Compose overrides and image-based startup. Replace unsupported attributions with those concrete differences, including internal/external URL settings required by ADR-02 §4; if retaining default credentials, attribute them to upstream Compose files/SPEC-03 §3.1 rather than the legacy guide.
- **25-10 / P3 — Complete SPEC-06 form and newcomer explanations.** Anchors, Jump, Version 1.0 and Learned exist, but the previous 0.1 version is removed (line 8); parent-index and Used-by links are absent (line 10); a glossary interrupts the English/Japanese halves (line 328) and is repeated at 657. Terms TOON, manifest, profile, EOL, wheel, WSL2 and emulation lack first-use notes (examples: 35, 93, 109, 147–152). Add short explanations and shared-glossary links. Remove the incorrect “Ventura” label from “macOS 14” at 33 / 362, and preserve the numeric SPEC-02 host requirement. Explain that the seven publishing services already have outbound access; `--egress` adds it for others, and `--egress none` clears the saved choice (ADR-02:85; compose.py:14–18). The egress example at 238 / 567 needs the full profile selected; it is valid after the preceding full-profile step, but fails for a reader still using default core.

Comments posted: [PR #22 r1](https://github.com/RCOSDP/RDM-developer-guide/pull/22#issuecomment-6667432843) · [PR #25 r1](https://github.com/RCOSDP/RDM-developer-guide/pull/25#issuecomment-6667433707). The review record passed the SPEC-06 mechanical checks for anchors, Jump, version, links and TOON with zero errors.

### Additional checks and limits

The seven default port rows agree with SPEC-02 §4. The two-network model and persisted `GRDM_EGRESS_SERVICES` agree with ADR-02; the diagram should also attach web to the internal network to depict its service calls (guide:74 / 403; compose.py:365). The `--yes`, `--profile`, `--egress`, `--seed`, build, down and reset command names/flags exist in SPEC-02. The missing flags and misleading outcomes are ranked separately. Git clone, cd, Docker logs and lsof are supporting shell commands, not grdm-dev subcommands specified by SPEC-02.

Both language halves mostly mirror one another, including the defects; the fallback timing mismatch is called out above. The manifest checker's private-URL/token text scanner reported zero findings for the proposed guide. No private repository URL is reproduced here. Fix the findings in both languages and re-review; full startup still needs a separate recorded run.

---

<a id="japanese"></a>
## 日本語

[→ To English](#english)

### 範囲と判定

作業要約: GitHub CLI で両提案を読み、仕様・実装と照合し、日英記録と各提案への日本語コメントを作成する。承認、マージ、コミット、push、Docker 実行は行っていない。

SHA は保存済みコード版を表す 40 文字の指紋、マニフェストは部品と固定版の一覧、TOON は構造化データの短いテキスト表現である。根拠は `gh pr diff` と `gh api .../contents/<path>?ref=<branch>` で取得した。行番号は対象提案ファイルと取得時の develop 参照資料に対応する。

- **PR #22: 進捗文言の修正要求（22-01）。版固定の検証は合格。** 対象先端は `c3cdf706a83a45a94c403bdbafe9fc2f1e31f8e0`。
- **PR #25: 修正要求。セキュリティ検査説明に優先度の高い指摘が 2 件。** 対象先端は `b37c71e1024611485aebb6d9d8b63878b7ae4db6`。
- develop 参照版は `e2f3858eac63b990a27158314889c406aa9a42a6`。完全起動、イメージのビルド、ブラウザ受入試験、稼働環境のセキュリティ検査は未実施。判定はレビュー上の推奨で、GitHub の承認・レビュー送信ではない。

### PR #22 の検証

英語節の TOON に列挙した統合リポジトリ 11 件すべてで、小文字 40 桁 16 進の `integration_sha` と実際の develop 先端が一致した。確認方法は `gh api repos/RCOSDP/<repo>/branches/develop --jq .commit.sha`。基盤サービスはリモート照合から除外した。

Wiki は RDM-wiki-frontend と RDM-wiki-frontend-develop-private の develop 両先端とも一致。OASys・rdmcp・aipf は、それぞれ RDM-OASys-main-private・RDM-rdmcp-private・RDM-aipf_mcp_data_grdm-private の main 先端とも一致した。非公開リポジトリは名前のみを記録する。

一時コピー `/tmp/rev-pr22-pr25` を作業ディレクトリとして実行した検査は終了コード 0、指摘 0 件だった。

```bash
cd /tmp/rev-pr22-pr25
python3 tools/manifest_check.py --manifest-only
```

検査範囲はマニフェストと TOON 抄録の一致。抄録には `integration_sha` が含まれないため、TOON が無変更なのは正しい。この部分コピーからリポジトリ全体のポリシー検査に合格したとは主張しない。

厳密再構築 7 本のマージは `gh pr list --state merged --base develop` で確認した。osf.io #2、および waterbutler・modular-file-renderer・ember-osf-web・cas-overlay・y-websocket・Shibboleth-SP の #1 である。UTC では 2026-11-05 19:25、JST では 2026-11-06 であり、ボードの日付はチームの時間帯と合う。

### PR #22 の優先順位付き指摘

- **22-01 / P2 — 「PR なし」を「#1 を未マージで閉鎖、先端同一」に修正。** `docs/status/README.md:38`・`:79` は wiki-frontend に PR がなかったとするが、実際には RDM-wiki-frontend-dev2027 #1 が 2026-11-05 11:09:10 UTC に作成され、11:21:58 UTC に未マージで閉鎖された。先端同一は確認済み。7 本のマージ数を保ち、両言語で履歴を直す。
- **22-02 / P3 — ボードの版を更新し、置換済みレビューを明示。** `docs/status/README.md:8` が 11 月 5 日の版のままで、変更と同時の版更新を求める SPEC-06 §6 に合わない。既存の `:41`・`:82` は osf.io #1 の判断を待機中とするが、#1 は閉鎖済み、#2 はマージ済み。この行は既存の不整合であり、ボード更新時に履歴・置換済みと分かるようにする。

### PR #25 の優先順位付き指摘

対象行はすべて `docs/guides/environment/README.md`。英語／日本語の順に示す。

- **25-01 / P1 — 「全セキュリティ検査」のコマンドが脆弱性解析を省く。** 180–188／509–517 行の `scan --baseline --secrets` は基本対策と秘密情報の検査だけを選択する。CVE（既知の弱点に付く公開番号）の基準内判定を保証しない。SPEC-02 §3、`installer/grdm_dev/scan.py:902`・`:932`・`:940`・`:944` が根拠。全検査なら `scan` にし、限定検査ならその範囲を明示する。節目ごとの判定と、検査ツール不足の 51、動的検査が実行不能な場合の 52 も説明する。
- **25-02 / P1 — 記載の健康確認ではホスト公開先を検査しない。** 171–176／500–505 行、および 309／638 行は通常の `health` でループバック以外の待受を検出するとする。SPEC-02 §3、SPEC-03 §3.2、`installer/grdm_dev/health.py:314`・`:330` に従い、その保証をする箇所は `health --network` に修正する。応答の正常だけでネットワーク隔離が確認できたと誤認させない。
- **25-03 / P2 — 終了コードを修正。** 95／424 行は Docker 不足を 10 とするが、SPEC-02 §6 では 11。135／464 行は render が失敗しないとし、成功の 0 を失敗コードとしているが、`installer/grdm_dev/compose.py:746`・`:750`・`:775`・`:784` は 20・2・12 を返す。実際の成功・失敗条件を示し、トラブル対応節との矛盾を解消する。
- **25-04 / P2 — 自動導入の順序と任意の手動試験を分ける。** 83／412 行は全掲載手順が自動実行されるとし、doctor 節の 90／419 行は導入全体を呼ぶ。SPEC-02 §2.1 と `installer/grdm_dev/install.py:39`–`:51` の順序は doctor → plan → secrets → render → build → up → health --network → scan → report で、accept を含まない。初期準備後の doctor 単独コマンドを示し、受入試験を任意操作として分ける。
- **25-05 / P2 — 受入試験の準備と試験利用者の寿命を正確にする。** 195–202／524–531 行は SPEC-02 §2.2 と `installer/grdm_dev/accept.py:574`–`:585` が要求する追加 Python 依存と Chromium の準備を欠く。`accept --seed` を先に実行して利用者を準備する説明も不正確で、`:619`–`:636` は一回の呼出しで作成・試験・削除まで行う。既存の仮想環境内での準備と、実際に実行する試験への `--seed` 指定を示す。
- **25-06 / P2 — 全サービスの読み取り専用ルートを保証しない。** 265／594 行は SPEC-03 §3.3（`docs/spec/03_security_gate.md:74`）の「対応できるサービスのみ」と `manifest/hardening.json` の例外を落としている。例外の仕組みと記録へのリンクを付ける。乱数の秘密、0600、ループバック限定公開、ダイジェスト固定方針は SPEC-03 §3 の要求と合うが、稼働環境での遵守を実証したわけではない。
- **25-07 / P2 — 起動結果には選ばれたポートを案内する。** 29／358 行と 162／491 行は 5000 固定だが、280／609 行では正しく再割当を説明している。`installer/grdm_dev/compose.py:210` は指定値から +100 まで探索し、自プロジェクトの待受を保持し、`:784` は代替がない場合だけ 12 を返す。出力 URL または保存ポートを使うよう案内する。保存済み指定値も探索元になるため「既定から +100」は「要求・保存ポートから +100」に直す。
- **25-08 / P2 — 代替イメージの現状と日英の時期を揃える。** 8 行の完全起動未検証という明記は適切だが、英語は Dockerfile 更新「後」、日本語は更新「まで」代替を追加すると読める。ember の代替は `manifest/upstreams.json:409`・`:415` の注記・prebuilt_image に既に存在し、DEMO-20 に決定が記録されている。近代化まで設定済みであることを示し、クイックスタートにも未検証の注意を置く。ソースビルド失敗だけで設定済み代替の失敗を断定しない。
- **25-09 / P2 — 新旧比較表を旧ガイドの実際の記述に基づかせる。** 321–322／650–651 行が旧方法とする `docker pull` と `postgres/postgres` は README.legacy.md に登場しない。旧 33・36–39・47–56 行にある別名、local 設定のコピー、Compose 上書き、イメージによる起動を比較する。ADR-02 §4 が要求する内部・外部 URL 設定の違いも加える。既定認証情報を残す場合は旧ガイドではなく上流 Compose／SPEC-03 §3.1 に帰属させる。
- **25-10 / P3 — SPEC-06 の体裁と初学者向け注を補う。** アンカー、Jump、Version 1.0、Learned はある。一方、旧版 0.1 が削除（8 行）、親索引・Used-by が欠落（10 行）、用語集が英語と日本語の間に挿入（328 行）され末尾 657 行でも重複する。TOON、manifest、profile、EOL、wheel、WSL2、エミュレーションの初出注がない（例: 35・93・109・147–152 行）。短い説明と共通用語集リンクを補う。33／362 行の「macOS 14 (Ventura)」は誤った名称を外し、SPEC-02 の数値条件を維持する。公開サービス 7 種は既に外向き通信が可能、`--egress` は他サービスに追加し `--egress none` で保存設定を消すと明示する（ADR-02:85、compose.py:14–18）。238／567 行の例は full 選択後なら有効だが、既定 core のままなら失敗するため前提を添える。

投稿済みコメント: [PR #22 r1](https://github.com/RCOSDP/RDM-developer-guide/pull/22#issuecomment-6667432843) · [PR #25 r1](https://github.com/RCOSDP/RDM-developer-guide/pull/25#issuecomment-6667433707)。本記録の SPEC-06 機械検査（アンカー・Jump・版・リンク・TOON）はエラー 0 件だった。

### その他の照合と限界

既定ポート 7 行は SPEC-02 §4 と一致。二つのネットワークと `GRDM_EGRESS_SERVICES` の保存は ADR-02 と一致する。図にも web の内部ネットワーク接続を追加するとサービス間通信を正しく表せる（ガイド:74／403、compose.py:365）。`--yes`・`--profile`・`--egress`・`--seed`、build・down・reset のコマンド名とフラグは SPEC-02 に存在する。不足フラグ・誤った結果説明は個別に指摘した。git clone、cd、Docker logs、lsof は補助的なシェル操作で、SPEC-02 の grdm-dev サブコマンドではない。

日英の大部分は不具合も含め対応し、代替導入時期の相違を個別に指摘した。マニフェスト検査ツールの非公開 URL・トークン文字列検査では、提案ガイドの指摘は 0 件だった。この記録にも非公開リポジトリ URL を載せていない。両言語を修正して再レビューし、完全起動は別途実行記録で実証する。

---

## Glossary / 用語

| Term | English note | 日本語注 |
|---|---|---|
| REV | Reviewer responsible for checking a proposed change. | 変更案を点検する担当レビュワ。 |
| P1 / P2 / P3 | High-priority correction / normal correction / minor documentation improvement. | 優先度の高い修正／通常修正／軽微な文書改善。 |
| Branch tip | The latest saved revision on a named line of development. | 名前付き開発系列の最新保存版。 |
| Parity | Two representations say the same thing. | 二つの表現の内容が一致すること。 |
| Egress | Traffic sent from a service to the outside network. | サービスから外部ネットワークへ出る通信。 |
| Baseline | Minimum security checks required for every installation. | 毎回の導入に必要な最低限の安全確認。 |
