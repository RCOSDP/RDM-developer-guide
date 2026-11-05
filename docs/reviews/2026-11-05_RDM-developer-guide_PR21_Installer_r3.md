# REV PR21 Installer review r3 / インストーラーレビュー r3

> **Summary:** The five r2 findings are resolved on their reported paths at `9fbb734`. Changes requested for one new prebuilt-image reporting defect; passing checks do not establish a completed real installation.
> **概要:** `9fbb734` で r2 の5件は報告された経路の修正を確認した。事前ビルド済みイメージの結果記録に新しい不一致が1件あるため修正要求とする。検査合格は実機導入完了を意味しない。

**Jump:** [English](#english) · [日本語](#japanese)

- Version / 版: 0.1 — 2026-11-05. **Learned:** a fallback must report only the platforms it actually handled, even when the ordinary build accepts a platform list. ／ 通常のビルドが複数プラットフォームを受け付けても、代替経路の記録は実際に処理した対象だけでなければならないと分かった。
- Applies to: PR (proposed change / 変更案) #21, `feat/m2-installer` → `develop`, head `9fbb7340f96957f3e56ca6034d3b303fe4cc58c0`; REV（担当レビュワ）, independent review / 独立レビュー.
- Related: [Review index](README.md) · [r2](2026-11-05_RDM-developer-guide_PR21_Installer_r2.md) · [SPEC-01](../spec/01_manifest.md) · [SPEC-02](../spec/02_installer_cli.md) · [SPEC-04](../spec/04_acceptance_tests.md) · [SPEC-06](../spec/06_documentation_conventions.md) · [ADR-02](../decisions/ADR-02_Network_Model.md) · [Shared glossary](../reference/REF-01_Glossary.md).
- Used by: [Installer](../../installer/README.md) · [Acceptance suite](../../installer/acceptance/README.md) · [Status board](../status/README.md) · [Mac Studio run record](../demo/20_core_install_mac_studio.md).

---

<a id="english"></a>
## English

[→ 日本語版へ](#japanese)

### Verdict and scope

**Changes requested: R3-01 (P2, implementation/reporting contract).** R2-01–R2-05 are resolved for the reported cases. No approval, merge, close, commit or push was performed. GitHub access used `gh` only. All command runners that could change Docker (the container execution tool) state were replaced with fakes; no real installation or red-team run was started. Synthetic secrets and temporary directories were used. Compared local file bytes with the requested head's Git blob hashes through `gh api`: all 325 tracked files under `installer/`, `tools/`, `manifest/` and `docs/` matched before writing this record.

Terminology: arm64 (Apple Silicon CPU family), amd64 (Intel/AMD CPU family), modular-file-renderer (file-preview service), ember-osf-web (browser-facing application).

### Disposition of r2

| Finding | Result | Reproduced evidence |
|---|---|---|
| R2-01 | Resolved for reported trace leak | Put the same synthetic secret into `pytest.log`, ZIP member `trace.network`, and `resources/body`; after `sanitize_run_dir`, log and network member are `***`, and the response body member is removed. Default tracing is off. The execution path moves trace ZIPs into private quarantine before sanitizing public evidence. |
| R2-02 | Resolved | `GuardedRequest(...).get("http://127.0.0.1:5000", max_redirects=20)` raises `ValueError` with zero underlying calls. A context without WebSocket interception raises `RuntimeError`. All 10 guard tests pass in `.venv`, covering hop validation and the missing capability. |
| R2-03 | Resolved for broken-tool probe | A temporary `nc` executable containing `exit 2`, with the real generated shell probe, emits `GRDM_SELFTEST_FAIL tool=nc open-port-rc=2 closed-port-rc=2`; `verdict` returns `inconclusive`, not proven isolation. The probe never reaches the external target. |
| R2-04 | Resolved | Render the real core manifest with `egress="worker"` using fake external runners: exit 0; baseline findings empty; one `accepted-egress` entry for worker, network `grdm-edge`, source `env`. The suite also rejects undeclared attachments and stale grants. |
| R2-05 | Resolved for reported omissions/misstatements | Both SPEC-01 §3 tables now describe `build_platform`, absence behavior, example `linux/amd64`, override precedence and infra restriction; Japanese `integration_sha` is translated. SPEC-02 build describes CLI → component → host precedence, and redteam preflight explicitly creates/removes a canary container/network. ADR-02 §4 explicitly names seven publishing services with outbound Internet access. |

The platform rows give an example rather than an exhaustive accepted-value grammar; MC-10 currently type-checks `build_platform`. This review does not claim exhaustive platform-value validation.

### New finding

**R3-01 — P2: prebuilt multi-platform requests silently drop platforms but record all as handled.** In [build.py](../../installer/grdm_dev/build.py), `pull_argv` (line 168) uses only `platforms[0]`; the prebuilt branch (lines 211–217) records `",".join(platforms)` and returns success. With the real manifest and an injected runner, select `ember-osf-web`, set `platform="linux/amd64,linux/arm64"`, and set `push=True`: the only call is `docker pull --platform linux/amd64 <pinned-reference>`, exit is 0, and the result reports `platforms: linux/amd64,linux/arm64`, `status: prebuilt`, `push: true`. No arm64 operation occurs. The same truncation follows without `--push` because `pull_argv` is independent of that flag. The new fallback thus misstates work performed, and SPEC-02's general multi-platform push description does not define the exception.

Reject unsupported multi-platform requests for a prebuilt component before pulling, or implement each requested platform and report actual results. Define whether `--push` is rejected or explicitly skipped for prebuilt components, and make the result/documentation reflect that policy. Add a regression test checking both invoked arguments and recorded platforms; do not require real Docker for this test.

### Prebuilt and trace contracts

SPEC-01's English/Japanese `prebuilt_image` rows agree: digest pin, explanatory note, no infra/private-repository reference, bypass of source provenance, removal by M4. MC-06 checks syntax, a nonempty note, prohibited reference forms and infra role; it does not prove registry accessibility or that a free-text note actually explains a milestone. The real note states the schema-1 build failure and M4 removal. The real reference is:

```text
niicloudoperation/rdm-ember-osf-web@sha256:65ee1fae52a33ec7dbc42546f5b3a240dddd70eb963d1ebe2ededa80135cc2e7
```

A default fake-runner build of this component makes exactly one pull for `linux/amd64`, records `prebuilt`, and makes no clone/build call. Rendered `ember_osf_web.image` equals that digest reference and its platform is `linux/amd64`. Unit tests cover pull failure returning 30; manifest tests cover missing digest/note, private references, infra usage and the actual entry. No registry pull or independent image provenance/architecture verification was performed here.

SPEC-04 §7, acceptance README and demo-runs README consistently describe tracing off by default, opt-in failure traces under `runtime/reports/quarantine/<run_id>/`, and the raw cookie/body risk. The main installer README does not make a conflicting trace promise. Source moves ZIPs before sanitizing the remaining evidence and restricts quarantine directories/files to 0700/0600. Quarantine is raw, not an exportable sanitized artifact. The ZIP probe establishes removal of the tested secret, not a general guarantee about image pixels, metadata or arbitrary encodings.

DEMO-20 run 2 has equivalent English/Japanese steps and image outcomes. It records exit 30 at ember-osf-web after the amd64 modular-file-renderer build, not startup success; this motivates the fallback but does not prove it completes installation. Measurements and registry claims in that run were read, not independently repeated. Real startup, initialized-store credential rejection, browser acceptance and actual network behavior remain separate evidence.

### Validation

Observed results (TOON is a compact structured-text format; these are review observations, not canonical manifest data):

```toon
checks[7]{check,result}:
  installer_unittest,"288 run; OK; 10 skipped because system Python lacks pytest"
  guard_tests_venv,"10 run; OK; covers the 10 system-Python skips"
  tools_unittest,"77 run; OK"
  docs_check,"PASSED; 52 checked; 8 exempt; 127 warnings before this record"
  manifest_check,"PASSED; zero findings"
  head_file_comparison,"325 files match 9fbb734"
  github_ci,"all 6 checks pass on 9fbb734"
```

Run from the repository root; each command completed with exit 0:

```sh
PYTHONPATH=installer python3 -m unittest discover -s installer/tests
python3 -m unittest discover -s tools/tests
python3 tools/docs_check.py
python3 tools/manifest_check.py
PYTHONPATH=installer:installer/tests .venv/bin/python -m unittest test_accept.GuardedRequestTests
gh pr checks 21 --repo RCOSDP/RDM-developer-guide
```

CI (automatic checks) evidence: [documentation](https://github.com/RCOSDP/RDM-developer-guide/actions/runs/42027270163) and [security/manifest](https://github.com/RCOSDP/RDM-developer-guide/actions/runs/42027270050). The new untracked review passed separately through `docs_check.check_file` with zero errors and warnings, because the normal command selects tracked files. Fix R3-01 and re-review; this verdict is not a real-install acceptance or a merge authorization.

---

<a id="japanese"></a>
## 日本語

[→ To English](#english)

### 判定と範囲

**修正要求: R3-01（P2、実装と結果記録の契約不一致）。** R2-01〜R2-05 は報告されたケースの解消を確認した。approve・merge・close・commit・push はしていない。GitHub 操作は `gh` のみ。Docker（コンテナ実行の道具）の状態を変え得る実行関数は偽物に置き換え、実機導入もレッドチーム実行も開始していない。合成秘密と一時ディレクトリを使った。`gh api` で指定 head の Git blob ハッシュとローカルを比較し、記録作成前の `installer/`・`tools/`・`manifest/`・`docs/` の追跡済み325ファイルがすべて一致した。

用語注: arm64（Apple Silicon の CPU 系列）、amd64（Intel/AMD の CPU 系列）、modular-file-renderer（ファイルプレビュー用サービス）、ember-osf-web（ブラウザ向けアプリケーション）。

### r2 の処置

| 指摘 | 結果 | 再現した証拠 |
|---|---|---|
| R2-01 | 報告された trace 漏えいは解消 | `pytest.log`、ZIP の `trace.network` と `resources/body` に同じ合成秘密を置いた。`sanitize_run_dir` 後、ログと network は `***`、応答本文メンバーは削除された。既定の trace は無効で、実行経路は公開証跡の無害化前に ZIP を隔離する。 |
| R2-02 | 解消 | `GuardedRequest(...).get("http://127.0.0.1:5000", max_redirects=20)` は下位呼出し0件で `ValueError`。WebSocket を遮断できない context は `RuntimeError`。転送先と機能欠落を含む guard 10試験が `.venv` で合格した。 |
| R2-03 | 壊れた道具の経路は解消 | 終了2の一時 `nc` で実際の生成シェルを実行すると `GRDM_SELFTEST_FAIL tool=nc open-port-rc=2 closed-port-rc=2`。`verdict` は隔離成功でなく `inconclusive`。外部宛て検査には進まない。 |
| R2-04 | 解消 | 実 core manifest を外部実行関数だけ偽物にして `egress="worker"` で生成すると終了0。baseline 指摘0件で、worker・`grdm-edge`・source `env` の `accepted-egress` が1件。未記録の接続と古い許可の拒否試験も合格した。 |
| R2-05 | 報告された欠落・誤記は解消 | SPEC-01 §3 の両表に `build_platform`、省略時、`linux/amd64` の例、優先順位、infra 制約がある。`integration_sha` の和訳もある。SPEC-02 は CLI → 部品 → ホストの順序と preflight のカナリア作成・削除を明記。ADR-02 §4 は公開7サービスの外向き通信を明示した。 |

プラットフォーム欄は例示であり、許容値の網羅的な文法ではない。現在 MC-10 は `build_platform` の型を検査する。値の網羅的な妥当性検査まで確認したとはしない。

### 新しい指摘

**R3-01 — P2: prebuilt の複数プラットフォーム指定を切り捨て、全件処理したように記録する。** [build.py](../../installer/grdm_dev/build.py) の `pull_argv`（168行）は `platforms[0]` だけを使うが、prebuilt 分岐（211〜217行）は全件を `",".join(platforms)` で記録して成功する。実 manifest と差し替えた実行関数で `ember-osf-web`、`platform="linux/amd64,linux/arm64"`、`push=True` を選ぶと、呼出しは `docker pull --platform linux/amd64 <固定参照>` だけで終了0、結果は `platforms: linux/amd64,linux/arm64`、`status: prebuilt`、`push: true` になる。arm64 の処理はない。`pull_argv` は push に依存しないため、`--push` なしでも切捨ては同じ。SPEC-02 の複数プラットフォーム push の一般説明にも例外の定義がない。

prebuilt で未対応の複数指定は pull 前に拒否するか、指定をすべて処理して実績を記録すること。prebuilt に対する `--push` を拒否するか明示的にスキップするかも定義し、結果と文書を合わせること。実 Docker を使わず、呼出し引数と記録したプラットフォームの両方を見る回帰試験を追加すること。

### prebuilt と trace の契約

SPEC-01 の英和 `prebuilt_image` 行は、ダイジェスト固定、説明 note、infra・非公開リポジトリ参照禁止、ソース由来保証の除外、M4 での撤去について一致している。MC-06 は構文・空でない note・禁止参照・infra を検査するが、レジストリ到達性や note に本当に節目の説明があるかまでは証明しない。実 note には schema 1 の失敗と M4 撤去が書かれている。実参照は次のとおり。

```text
niicloudoperation/rdm-ember-osf-web@sha256:65ee1fae52a33ec7dbc42546f5b3a240dddd70eb963d1ebe2ededa80135cc2e7
```

既定の偽実行では `linux/amd64` の pull が1回、記録は `prebuilt`、clone・build は0回。生成した `ember_osf_web.image` は同じ参照、platform は `linux/amd64`。単体試験は pull 失敗の終了30、manifest 試験は digest/note 欠落、非公開参照、infra、実エントリーを検査している。実 pull と独立した画像の由来・アーキテクチャ検証は行っていない。

SPEC-04 §7、acceptance README、demo-runs README は、既定の trace 無効、明示指定時の失敗 trace の `runtime/reports/quarantine/<run_id>/` への隔離、生の cookie・本文の危険を整合して説明する。installer 本体の README に矛盾する trace 保証はない。実装は残りの証跡の無害化前に ZIP を移し、隔離先はディレクトリ0700・ファイル0600。隔離物は生データであり、公開できる無害化済み証跡ではない。ZIP 再現は試した秘密の除去を示すだけで、画像の画素・メタデータ・任意の符号化までの保証ではない。

DEMO-20 run 2 の英和の手順・画像結果は一致している。amd64 の modular-file-renderer 成功後、ember-osf-web で終了30と記録され、起動成功とはしていない。これは代替経路の動機だが、導入完了の証明ではない。測定値とレジストリに関する記録は読んだだけで再実行していない。実起動、初期化済みストアでの旧資格情報拒否、ブラウザ受入、実ネットワーク挙動は別の証拠として残る。

### 検証

観測結果（TOON は構造化データの短い表記。manifest の正本ではない）:

```toon
checks[7]{check,result}:
  installer_unittest,"288件; OK; system Python に pytest がないため10件スキップ"
  guard_tests_venv,"10件; OK; system Python のスキップ分を補完"
  tools_unittest,"77件; OK"
  docs_check,"PASSED; 記録作成前52件検査・8件除外・127警告"
  manifest_check,"PASSED; 指摘0件"
  head_file_comparison,"325ファイルが9fbb734と一致"
  github_ci,"9fbb734の6チェックがすべて成功"
```

リポジトリのルートで次を実行し、すべて終了0を確認した。

```sh
PYTHONPATH=installer python3 -m unittest discover -s installer/tests
python3 -m unittest discover -s tools/tests
python3 tools/docs_check.py
python3 tools/manifest_check.py
PYTHONPATH=installer:installer/tests .venv/bin/python -m unittest test_accept.GuardedRequestTests
gh pr checks 21 --repo RCOSDP/RDM-developer-guide
```

CI（自動検査）の証拠: [文書](https://github.com/RCOSDP/RDM-developer-guide/actions/runs/42027270163)、[セキュリティ・manifest](https://github.com/RCOSDP/RDM-developer-guide/actions/runs/42027270050)。通常の文書検査は追跡済みファイルを選ぶため、新規記録は `docs_check.check_file` で別途検査し、エラー・警告とも0件だった。R3-01 を修正して再レビューすること。実機受入の合格やマージ承認は与えない。

## Glossary / 用語

| Term | English | 日本語 |
|---|---|---|
| REV | Reviewer | 担当レビュワ |
| Digest | Content fingerprint identifying an image | イメージの内容を固定する指紋 |
| Prebuilt image | Already-built application package | 既に組み立てられた実行用の包み |
| Egress | Outbound network traffic | 外へ出る通信 |
| Quarantine | Private storage excluded from public evidence | 公開証跡に含めない隔離保管 |
| Probe | Small check of a condition | 状態を調べる小さな検査 |
| P2 | Implementation or documentation contract defect | 実装・文書の契約不一致 |
