# REV M1 Skeleton PR Review r1 / M1 文書骨格 PR レビュー r1

> **Summary:** Request changes on PR #19: private repository URLs remain in public text, the secret scanner has no enabled detection rules, despite green CI. Validation and specification defects also need correction.
> **概要:** PR #19 は修正要求。公開文書に非公開リポジトリ URL が残り、秘密スキャナーの検出規則が有効でなく、CI 合格でも保護を保証できません。検査と仕様の不具合も修正が必要です。

**Jump:** [English](#english) · [日本語](#japanese)

- Version / 版: 0.1 — 2026-11-05. **Learned:** passing local checks did not establish specification compliance: independent parsing found malformed blocks, and source inspection found missing validation. ／ ローカル検査の合格だけでは仕様準拠を示せず、独立した構文解析とコード確認で構文不正と未実装の検査を確認した。
- Applies to: PR #19, `feat/m1-skeleton` → `develop`, final reviewed head `1a01c3b1352fb58cfa100e6d200c737213b70464` (updated during review from `df7a4ce`).
- Related: [Review index](README.md) · [SPEC-06](../spec/06_documentation_conventions.md) · [SPEC-01](../spec/01_manifest.md) · [SPEC-02](../spec/02_installer_cli.md).
- Used by: owner merge decision and the author's correction pass.

---

<a id="english"></a>
## English

[→ 日本語版へ](#japanese)

### Verdict and terms

**Request changes.** A PR (pull request) is a proposed change awaiting review; this verdict is a review recommendation, not a GitHub approval or merge. P1 means fix before merge because a protection is ineffective or a required check fails; P2 means a reproducible correctness or documentation defect. CI means the automated checks GitHub runs. See the [shared glossary](../reference/REF-01_Glossary.md).

### Findings, highest severity first

1. **R1 — P1: prohibited private URLs are published as negative examples.** `manifest/README.md:48–49,102–103` contains actual HTTPS and SSH addresses for the private integration repository. Calling them “never write” examples still publishes them and violates SPEC-06 §5 and the task's publication rule. The PR body's “private URL grep: none” is incorrect. Replace them with non-address prose; scan all tracked files, not just the two data files. No private URL is repeated in this review.

2. **R2 — P1: gitleaks runs with zero detection rules.** `.gitleaks.toml:6–28` supplies only an allowlist (exceptions to detection), no rules and no `[extend] useDefault = true`. `default = true` at line 28 is inside `[allowlist]` and is not a supported setting that enables defaults. The pinned version's [configuration source](https://github.com/gitleaks/gitleaks/blob/v8.21.2/config/config.go) defines `Extend.UseDefault` and no such allowlist field. The workflow explicitly selects this config at `.github/workflows/security.yml:23`, so its green “68 commits scanned / no leaks found” is not evidence of an effective secret scan. Enable the default rules, remove unsupported `entropy`, and replace the global unanchored 40-hex exemption with narrowly justified exceptions: secret values can also be 40 hex characters. Verify a synthetic secret is rejected without placing it in Git, then rescan history with redacted output. Add a separate private-URL policy check; default secret rules alone do not enforce that policy.

3. **R3 — P2: declared Trivy coverage is not delivered.** `docs/spec/03_security_gate.md:234,458` promises gitleaks, Semgrep and Trivy on every PR, but `.github/workflows/security.yml:11–59` has no Trivy job. Implement it or explicitly delimit M1's delivered scope. The original Semgrep failure (77 findings) was resolved during review in `1a01c3b` by action SHA pinning and documented exclusions for generated output and legacy examples; [the latest job passes](https://github.com/RCOSDP/RDM-developer-guide/actions/runs/42009965678/job/127186166129). That initial failure is no longer an open finding. The owner should explicitly accept the documented legacy deferral.

4. **R4 — P2: manifest validation does not enforce its advertised contract.** `tools/manifest_check.py:225–235` checks JSON and searches text for URLs, but never calls `validate_toon` or compares JSON and TOON (the compact data notation). Missing TOON passes; changing any TOON SHA, profile, repository, or PR number passes. `validate_component` at lines 122–146 checks only four required fields and validates a SHA only if present. An in-memory component with invalid role and an upstream with no SHA returns no errors; a synthetic token also passes `validate_no_secrets`. Implement SPEC-01 MC-01–11/13 or explicitly document which checks are deferred, without claiming equivalence. The current files do agree semantically, but CI cannot keep them that way. Keep the helper's exit 1 distinct from the future CLI's specified exit 20, or align and document the interface.

5. **R5 — P2: ZAP is instructed to scan itself.** `docs/spec/03_security_gate.md:98,322` starts ZAP (a scanner of a running web application) inside a container on the internal network, then targets `127.0.0.1:5000/8001/4200`. Loopback in that container names ZAP itself, not the web/admin/ember containers or the host. This conflicts with `docs/decisions/ADR-02_Network_Model.md:53–57,131–135`, which separates service-name traffic inside Compose from host loopback traffic. Specify internal service names and container ports for ZAP, retaining SPEC-02's host-port table for browsers and host-side checks; include port-remapping behavior.

6. **R6 — P2: one diagram and three data blocks do not parse.** With the site's Mermaid 11.4.1 parser (text-to-diagram syntax), `docs/spec/04_acceptance_tests.md:94` fails: the semicolon in the English sequence-diagram note starts another statement. Use supported note text/escaping and regenerate HTML. TOON 4.4.0 rejects `docs/spec/02_installer_cli.md:133–134,138` because unquoted commas turn two-column exit-code rows into extra columns. `docs/status/upstream/README.md:38–46,92–100` declares 11 tabular rows but supplies an object-style item and an ellipsis. Supply a valid one-item example, or all 11 correctly shaped items. These errors survive MkDocs strict because it does not parse those embedded languages. The Japanese SPEC-04 diagram parses, so the two rendered halves differ.

7. **R7 — P2: the documentation checker silently skips promised checks and scope.** `tools/docs_check.py:18–43` checks only `docs/` plus root README and excludes legacy content, leaving `manifest/README.md`, installer README and old-path pointers outside SPEC-06 coverage. Lines 96–98 skip every link containing `#`, even when its file does not exist; a call with `absent-file.md#english` returns no errors. Lines 123–126 perform no TOON parity or glossary warning check, despite `docs/spec/06_documentation_conventions.md:87–95`. Check the file portion before the fragment, cover new Markdown throughout the repository, and document an explicit legacy-format exception. The existing 35-file pass is only a subset check.

8. **R8 — P2: M2 acceptance criteria contradict the profile definition.** `docs/spec/04_acceptance_tests.md:54,59,122` makes C4 depend on `y_websocket`, allows it to skip in `core`, yet requires all C1–C6 success and rejection cases green for M2. SPEC-02's profile table at `docs/spec/02_installer_cli.md:96–99` places that service in `full`; the manifest agrees. Define whether M2 includes this service or explicitly defers C4 to M3, and update both language halves. Otherwise a skipped test can be mistaken for a completed milestone.

### What was verified

All commands ran from the repository root. These read-only checks returned exit 0; the second initially reported 35 files; after the concurrent asset-index addition and this review it reported 37 files:

```sh
python3 tools/manifest_check.py
python3 tools/docs_check.py
```

The requested comparison was 506 files changed, 246,242 insertions and 3,246 deletions:

```sh
git diff develop...feat/m1-skeleton --stat
```

- Searched tracked text across the full tree, including site HTML, search-index JSON, legacy Markdown, hidden workflow files, and manifest files. Found the four prohibited URL occurrences in R1. Token-format/private-key searches found no additional matching credential. Legacy default JWT/JWE/test-token values and guest broker credentials exist; these are inherited examples, not verified live credentials. The EC2 legacy guide at lines 364/372 and its HTML/search-index copies contain a clearly placeholder-shaped internal hostname. Institutional support addresses and test emails are not evidence of personal-data leakage. No claim of exhaustive secret clearance is made, especially given R2.
- Visually sampled `new-token.png`, `dev-application.png` and `filled-credential.png`: the first has no issued token, while sensitive application/credential values in the latter two are blurred or password-masked. Other images were not exhaustively inspected; a text search cannot inspect their pixels.
- Observed actual GitHub runs: docs links and MkDocs strict pass, manifest passes, gitleaks exits 0 with the R2 limitation, Semgrep initially failed but the latest head passes all five checks (R3 records the remaining coverage gap). Successful jobs establish usable YAML, action versions, Python 3.11 and pinned MkDocs requirements on the hosted runner. The gitleaks Docker invocation and Semgrep container actually start. Local Docker daemon was unavailable, so containers were not rerun locally.
- Independently parsed all 34 Mermaid and 44 TOON fences in tracked Markdown using Mermaid 11.4.1, a DOM shim (browser-like objects for the parser), and `@toon-format/toon` 4.4.0 installed in a temporary directory outside the repository. Results: 33/34 Mermaid and 41/44 TOON pass. Parsed `manifest/upstreams.toon` and compared its specified projection with JSON: equal, including upstream fields and adopted PRs. This establishes semantic equality, not byte-for-byte output from an unimplemented CLI generator.
- Checked JSON required component fields, roles, profiles, core platforms, SHA shape, service names and tracking-name rules. Counted 20 components, 11 integration repositories, 8 adopted PRs and 25 candidates, matching the PR body. The requested authenticated branch query for `RDM-osf.io-dev2027` returns `develop`, `integrate/public-develop-20261105`, `upstream/public-develop`, `upstream/private-develop`, `upstream/cos-develop`, and `upstream/private-sec-test-fix-sec-test`; all four required tracking branches match SPEC-01 rule 7. Reachability and all 11 repositories' creation/mirroring were not independently audited.
- Compared SPEC-01–05 with ADR-02 and REF-01. The seven default host ports agree; exit 20/40/50–53/60 and principal subcommand names agree at specification level. R5 and R8 are behavioral contradictions despite matching numbers. Legacy guides are intentionally historical; they should not be read as current installation procedures.
- English/Japanese core sections largely align. First-use explanations exist for central terms but full SPEC-06 term-by-term compliance is not established. “Learned” claims about the eleven-upstream survey (`SPEC-05:8`) and newcomer behavior (`REF-01:8`) lack linked evidence in this PR; they are unverified, not proven fabricated. Provide the evidence or phrase them as design rationale. No mixed-language corruption was identified in the reviewed normative text.
- The claimed normative documents, guide pointers, committed site, requirements, and two workflows exist. M2 installer/acceptance implementations are not claimed M1 deliveries. The initial integration-order exception remains explicitly proposed in ADR-01 §5. Commit messages and the PR body carry a Claude session link; its accessibility/content was not inspected.

### Owner decisions

Resolve R1–R8 before merging. Decide the M1 Semgrep/Trivy enforcement scope, the M2 C4 scope, and whether to accept ADR-01 §5's bootstrap interpretation. Decide whether the Claude session link belongs in public metadata after assessing its sharing visibility; no session content is reproduced here. Approving the bootstrap exception must be reflected in SPEC-01 and the affected records, not silently treated as already approved. Add evidence for empirical “Learned” claims or reword them. Author corrections should regenerate `site/` and rerun both parser checks and hosted CI.

---

<a id="japanese"></a>
## 日本語

[→ To English](#english)

### 判定と用語

**Request changes（修正要求）。** PR（プルリクエスト）はレビューを待つ変更提案です。この判定は推奨であり、GitHub の承認やマージではありません。P1 は保護機能が無効または必須検査が失敗するためマージ前に修正すべきもの、P2 は再現可能な仕様・文書・検査の不具合です。CI は GitHub が自動実行する検査です。[共通用語集](../reference/REF-01_Glossary.md)も参照してください。

### 重大度順の指摘

1. **R1 — P1: 禁止例に実際の非公開 URL を掲載。** `manifest/README.md:48–49,102–103` に非公開統合リポジトリの HTTPS/SSH アドレスが計4件あります。「書かない例」でも公開に当たり、SPEC-06 §5 と今回の公開ルールに違反します。PR 本文の「private URL grep 検出なし」は誤りです。アドレスを含まない説明に置き換え、データ2ファイルだけでなく追跡対象の全ファイルを検査してください。このレビューには該当 URL を転記していません。

2. **R2 — P1: gitleaks の検出規則がゼロ。** `.gitleaks.toml:6–28` には allowlist（検出から除外する条件）しかなく、規則も `[extend] useDefault = true` もありません。28行の `default = true` は `[allowlist]` 内にあり、既定規則を有効にする設定ではありません。固定版の[設定コード](https://github.com/gitleaks/gitleaks/blob/v8.21.2/config/config.go)は `Extend.UseDefault` を定義し、該当 allowlist 項目は定義していません。`.github/workflows/security.yml:23` がこの設定を指定するため、「68 commits scanned / no leaks found」の成功表示は有効な秘密検査の証拠になりません。既定規則を有効化し、未対応の `entropy` を削除し、全域の40桁16進除外を根拠のある狭い例外へ変更してください。秘密も40桁16進になり得ます。Git に入れない模擬秘密で拒否を確認し、伏字で履歴を再検査してください。非公開 URL は既定の秘密規則だけでは禁止できないため、別の公開ポリシー検査も必要です。

3. **R3 — P2: 約束した Trivy の検査がない。** `docs/spec/03_security_gate.md:234,458` は全 PR で gitleaks・Semgrep・Trivy を要求しますが、`.github/workflows/security.yml:11–59` に Trivy ジョブはありません。実装するか M1 の提供範囲を明示してください。初回 Semgrep の77件の失敗は、レビュー中の `1a01c3b` で action SHA 固定と生成物・旧サンプルの理由付き除外により解消し、[最新ジョブは合格](https://github.com/RCOSDP/RDM-developer-guide/actions/runs/42009965678/job/127186166129)しています。初回失敗は未解決指摘ではありません。所有者は記録された旧資料の延期を明示的に受け入れる必要があります。

4. **R4 — P2: manifest 検査が契約を実施しない。** `tools/manifest_check.py:225–235` は JSON 検査と URL 検索のみで、`validate_toon` の呼び出しも JSON と TOON（短いデータ記法）の比較もありません。TOON 欠落、SHA・profile・repo・PR 番号の変更が合格します。122–146行の `validate_component` は必須4項目だけを検査し、SHA は存在するときだけ検査します。メモリ上の試験で不正 role と SHA のない upstream が無指摘、模擬 token も `validate_no_secrets` を通過しました。SPEC-01 MC-01–11/13 を実装するか、未実装項目を明示し同等と主張しないでください。現行データは一致しますが CI は一致を維持できません。補助ツールの終了1と将来 CLI の終了20は別契約として明示するか統一してください。

5. **R5 — P2: ZAP が自分自身を検査する指定。** `docs/spec/03_security_gate.md:98,322` は ZAP（稼働中の Web アプリを検査する道具）を内部ネットワークのコンテナで起動し、`127.0.0.1:5000/8001/4200` を対象にします。そのループバックは ZAP 自身であり、web/admin/ember やホストではありません。`docs/decisions/ADR-02_Network_Model.md:53–57,131–135` の内部サービス名とホスト側ループバックの分離に反します。ZAP には内部サービス名・コンテナ側ポートを指定し、SPEC-02 のホスト側表はブラウザとホスト側検査に使ってください。ポート付け替え時の動作も定めてください。

6. **R6 — P2: 図1件・データ3件が構文不正。** サイトと同じ Mermaid 11.4.1（文字から図を作る記法）のパーサーで `docs/spec/04_acceptance_tests.md:94` が失敗します。英語のシーケンス図の注のセミコロンが別の文として解釈されます。対応する記法に直し HTML を再生成してください。TOON 4.4.0 では `docs/spec/02_installer_cli.md:133–134,138` の非引用カンマで終了コード表の列が増えて失敗します。`docs/status/upstream/README.md:38–46,92–100` は11行の表を宣言しつつオブジェクト形式1件と省略記号を載せています。正しい1件の例か11件の表にしてください。MkDocs strict はこれらの内部言語を構文解析しないため見逃します。日本語の SPEC-04 図は解析でき、英和の表示が異なります。

7. **R7 — P2: docs チェッカーが範囲と約束した検査を省略。** `tools/docs_check.py:18–43` は `docs/` とルート README だけを検査し旧資料を除外します。`manifest/README.md`、installer README、旧パスの誘導は SPEC-06 検査の対象外です。96–98行は `#` を含むリンクを丸ごと無視し、ファイル自体がない `absent-file.md#english` も無指摘です。123–126行には `docs/spec/06_documentation_conventions.md:87–95` が約束する TOON 一致検査・用語注警告もありません。フラグメントより前のファイルを検査し、新しい Markdown 全体を対象にして、旧資料の形式例外は規約にも明記してください。35件合格は部分検査にすぎません。

8. **R8 — P2: M2 受入基準と profile が矛盾。** `docs/spec/04_acceptance_tests.md:54,59,122` は C4 に `y_websocket` を要求し、`core` ではスキップを認めながら、M2 では C1–C6 の成功・拒否ケース全合格を要求します。`docs/spec/02_installer_cli.md:96–99` はそのサービスを `full` に置き、manifest も一致します。M2 に当該サービスを含めるか C4 を M3 に延期するかを決め、両言語を修正してください。スキップを節目完了と誤認するおそれがあります。

### 確認したこと

すべてリポジトリルートで実行しました。次の読み取り検査は終了0で、後者は初回35ファイル、並行した assets 索引追加と本レビュー追加後は37ファイル合格でした。

```sh
python3 tools/manifest_check.py
python3 tools/docs_check.py
```

指定の差分は506ファイル、追加246,242行、削除3,246行でした。

```sh
git diff develop...feat/m1-skeleton --stat
```

- サイト HTML・検索 JSON・旧 Markdown・隠し workflow・manifest を含む追跡対象テキスト全体を検索し、R1 の禁止 URL 4件を確認しました。token 形式・秘密鍵の検索では追加の該当認証情報は見つかりませんでした。旧 JWT/JWE/test-token の既定値と guest の接続情報は存在しますが、引き継いだ例であり生きた認証情報とは確認していません。EC2 旧資料364/372行と HTML/検索コピーに明らかな仮値形式の内部ホスト名があります。組織サポートアドレスや試験メールを個人情報漏洩の証拠とは扱いません。特に R2 があるため完全な秘密クリアランスは主張しません。
- `new-token.png`、`dev-application.png`、`filled-credential.png` を目視確認しました。最初は未発行画面、後二つの機微な値はぼかしまたはパスワード伏字です。他の画像は網羅的に見ていません。文字検索では画素を検査できません。
- GitHub の実行で docs リンク・MkDocs strict・manifest は合格、gitleaks は R2 の制限付きで終了0、Semgrep は初回失敗しましたが最新 head では5検査すべて合格です（R3 は残る検査範囲の不一致です）。成功ジョブから、YAML・action バージョン・Python 3.11・固定 MkDocs 依存は hosted runner で利用可能と確認できます。gitleaks の Docker 呼び出しと Semgrep コンテナは起動しています。ローカル Docker daemon は利用できず再実行していません。
- 追跡 Markdown の Mermaid 34件・TOON 44件を Mermaid 11.4.1、DOM shim（パーサー用にブラウザのオブジェクトを用意する仕組み）、`@toon-format/toon` 4.4.0 で独立解析しました。依存はリポジトリ外の一時ディレクトリに置きました。合格は Mermaid 33/34、TOON 41/44。manifest の TOON は解析でき、上流全項目と採用 PR を含む規定の抄録が JSON と意味的に一致しました。未実装 CLI の生成結果とのバイト単位一致は証明していません。
- JSON の必須部品項目、role、profile、コアの platform、SHA 形式、サービス名、追跡名規則を確認しました。部品20、統合リポジトリ11、採用 PR 8、候補25で PR 本文と一致します。指定の認証付きブランチ照会で `RDM-osf.io-dev2027` は `develop`、`integrate/public-develop-20261105`、`upstream/public-develop`、`upstream/private-develop`、`upstream/cos-develop`、`upstream/private-sec-test-fix-sec-test` を返しました。必須追跡4本は SPEC-01 規則7と一致します。到達性と11リポジトリすべての作成・ミラーは独立監査していません。
- SPEC-01〜05 と ADR-02、REF-01 を比較しました。ホスト側既定7ポート、終了20/40/50〜53/60、主要サブコマンド名は仕様間で一致します。R5/R8 は数値が一致していても動作が矛盾する点です。旧ガイドは歴史資料であり現行導入手順ではありません。
- 英和の主要節は概ね対応し、中心用語には初出説明がありますが、全専門語の SPEC-06 準拠までは確認できていません。上流11本の調査（`SPEC-05:8`）と新入社員の行動（`REF-01:8`）の Learned は PR 内に根拠リンクがなく、未検証です。捏造と断定はしません。証拠を添えるか設計理由として記述してください。確認した規範文書に混在言語による文字の破損は見つかりませんでした。
- 主張される規範文書・ガイド誘導・コミット済み site・依存ファイル・workflow 2本は存在します。M2 のインストーラー・受入実装は M1 の提供物とは主張されていません。初回統合順の例外は ADR-01 §5 で提案中と明記されています。コミットメッセージと PR 本文には Claude セッションリンクがあり、公開状態や内容は調べていません。

### 所有者が決めること

マージ前に R1〜R8 を解消してください。M1 の Semgrep/Trivy の合否範囲、M2 の C4 の範囲、ADR-01 §5 の初回構築解釈を決める必要があります。Claude セッションリンクの共有状態を確認し、公開メタデータに残すか判断してください。セッション内容は転載していません。初回構築の例外を認める場合は SPEC-01 と関連記録へ反映し、承認済みと黙って扱わないでください。実証を述べる Learned には根拠を添えるか表現を直してください。作者の修正後は `site/` を再生成し、構文解析と hosted CI を再実行してください。

---

## Glossary / 用語

| Term | English note | 日本語注 |
|---|---|---|
| PR | A change proposed for review and merging. | レビューと統合を求める変更提案。 |
| CI | Checks run automatically when code changes. | 変更時に自動実行する検査。 |
| SHA | A fingerprint identifying a Git commit. | Git の変更記録を識別する指紋。 |
| TOON | A compact way to write structured data as text. | 構造を持つデータを短い文字で書く形式。 |
| Mermaid | Text that a renderer turns into a diagram. | 描画処理が図に変える文字の記法。 |
| Loopback | An address pointing back to the same host or container. | 自分自身のホストまたはコンテナを指す番地。 |
| Allowlist | Explicit exceptions to a check. | 検査から除外すると明示した例外。 |
| Parser | A program that checks and reads a notation's structure. | 記法の構造を検査して読み取るプログラム。 |
