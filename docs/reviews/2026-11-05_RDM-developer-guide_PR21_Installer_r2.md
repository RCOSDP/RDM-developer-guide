# REV PR21 Installer review r2 / インストーラーレビュー r2

> **Summary:** Re-review of all 14 r1 findings at `3149c7601f8e199d599c5e0abb721d87f56e2696`. Changes requested: three security defects and two implementation/documentation contract defects remain despite 247 passing unit tests.
> **概要:** `3149c7601f8e199d599c5e0abb721d87f56e2696` で r1 の14件を再レビューした。単体テスト247件は合格したが、安全性の欠陥3件と実装・文書の契約不一致2件が残るため修正を要求する。

**Jump:** [English](#english) · [日本語](#japanese)

- Version / 版: 0.1 — 2026-11-05. **Learned:** correcting the original examples is insufficient when failure artefacts and alternative probe paths bypass the same protection. ／ 元の再現例を直しても、失敗時の証跡や別の検査経路が同じ保護を迂回するなら十分ではないと分かった。
- Applies to: PR #21, `feat/m2-installer` → `develop`; REV (担当レビュワ), independent r2, no approval or merge.
- Related: [Review index](README.md) · [r1](2026-11-05_RDM-developer-guide_PR21_Installer_r1.md) · [SPEC-01](../spec/01_manifest.md) · [SPEC-02](../spec/02_installer_cli.md) · [SPEC-03](../spec/03_security_gate.md) · [SPEC-04](../spec/04_acceptance_tests.md) · [SPEC-06](../spec/06_documentation_conventions.md) · [ADR-02](../decisions/ADR-02_Network_Model.md) · [Shared glossary](../reference/REF-01_Glossary.md).
- Used by: [Installer](../../installer/README.md) · [Acceptance suite](../../installer/acceptance/README.md) · [Status board](../status/README.md) · [Mac Studio run record](../demo/20_core_install_mac_studio.md).

---

<a id="english"></a>
## English

[→ 日本語版へ](#japanese)

### Verdict and scope

**Changes requested.** P1 means a safety defect to fix before reliance; P2 means an implementation or documentation contract defect. A unit test replaces external programs with controlled responses; it does not certify a real installation. Docker (a tool for running applications in separate boxes) runs applications in separate containers; Compose describes those containers together. A secret is a password or key; egress is traffic leaving a network.

Terminology: PR (a proposed change), CI (automatic checks), Semgrep (a source-code checker), Playwright (a browser automation tool), arm64 (the Apple Silicon CPU family), amd64 (the Intel/AMD CPU family), and mfr (the file-preview service).

Read the r1 record, the fixes in `1caaace`, `ae273d4`, and `3149c76`, source, tests, and the requested specifications. GitHub access used `gh` only. No Docker command was executed against the real daemon, and no product source, commit, push, approval, merge, or closure was made. Local probes used temporary directories, synthetic secrets, and injected command runners. The second real install, if running, was left alone.

The shared checkout and remote head advanced to `1c2a925d6af687129e8f9c23f06d629db58996c0` during review. That commit changes only Semgrep annotations in `accept.py` and a synthetic test literal in `test_accept.py`. Downloaded the exact `3149c76` archive through `gh api`, repeated all 247 installer tests and the probes with that source, and checked its documentation separately. Findings refer to `3149c76`; the newer CI result is reported separately.

### Remaining findings

1. **R2-01 — P1: retained browser traces still contain secrets (r1 #6 partially fixed).** `installer/grdm_dev/accept.py:275` enables `--tracing retain-on-failure`, but `sanitize_run_dir` at lines 359–363 masks only `junit.xml`, `collector.json`, and `pytest.log`. Files under `artifacts/` only receive permission changes. Reproduction: write a synthetic `.env` value into both `pytest.log` and a `trace.network` member of `artifacts/trace.zip`, then call `sanitize_run_dir(run_dir, [value])`. The log is masked; the ZIP member still contains the exact value. Browser traces may carry cookies, headers and response bodies, so 0600 permissions do not satisfy the no-secret evidence contract. Sanitize retained trace contents and other exported artefacts, or disable/quarantine them until safe; add a ZIP-content assertion. The existing test named “every evidence file” covers text files only.

2. **R2-02 — P1: the API guard allows redirects to bypass the origin check (r1 #7 partially fixed).** `installer/acceptance/conftest.py:162` uses `kwargs.setdefault("max_redirects", 0)`. Calling `GuardedRequest(...).get("http://127.0.0.1:5000", max_redirects=20)` passes 20 unchanged to the underlying request context; captured arguments confirm it. A local response can therefore redirect externally before the response URL is checked. A later failure cannot undo the request, and an external hop returning to loopback is invisible to the final-URL check. Force zero redirects and validate each manually followed hop, or reject the override. Also, `guard_context` silently omits WebSocket routing when the method is absent (`:204`), while `pyproject.toml:19` permits Playwright 1.47; enforce a compatible capability/version or fail closed. Exact-origin parsing, guarded core call sites, and blocked service workers are improvements, but do not close these paths.

3. **R2-03 — P1: a broken attacker-side probe is still classified as proven isolation (r1 #4 partially fixed).** `installer/grdm_dev/redteam.py:207–220` maps every nonzero `nc` execution to `GRDM_REACH_FAIL`, then to `unreachable`. Reproduction without network access: place a stub `nc` on PATH that exits 2 (representing unsupported options), execute `probe_script("192.0.2.1", 443)` through `/bin/sh`, and pass its output to `verdict`. The shell exits 0, emits `GRDM_REACH_FAIL`, and receives `unreachable`, not `inconclusive`. The positive control uses another container's binary, so it cannot validate the attacker's tool. The HTTP fallback against port 443 can likewise fail after making a connection. Use a known TCP probe, verify its operation in the attacker environment, distinguish tool/protocol errors from blocked connections, and return 53 on uncertainty. The new missing-tool, absent-marker, failed-control, attachment, and approval-field tests pass, but do not cover this case.

4. **R2-04 — P2: explicitly granted egress fails the baseline (r1 #8/#2 follow-up).** `installer/grdm_dev/scan.py:487–489` rejects every non-publishing service on a non-internal network, without reading the recorded `GRDM_EGRESS_SERVICES` grant. Reproduction: render the real core manifest with `egress="worker"`; rendering returns 0 and records the choice, but `check_baseline(compose_path, hardening_path, env_path)` emits `BASE-NETWORK` for `worker`. The same render without egress has zero findings and 14 accepted hardening controls. SPEC-03 §3.2 explicitly says a recorded grant is not a baseline violation. Validate the recorded grant against actual attachments, accept the authorized service, and still reject undeclared attachments; add a renderer-to-baseline test for both cases.

5. **R2-05 — P2: the changed documentation still omits or misstates contracts.** SPEC-01 mentions `build_platform` in its new version note, but neither §3 schema table defines the field, accepted values, optionality, or precedence. Its Japanese `integration_sha` row remains entirely English. SPEC-02 §3 still describes the build default as host-only although components now choose amd64, and calls `redteam preflight` read-only although it creates/removes a canary container/network. ADR-02 §3 describes dual attachment for published services, but §4 says “no egress by default”; those seven services already have an ordinary bridge attachment without an explicit grant. Correct both language halves together and describe that exposure plainly. The two halves of the new SPEC-03 §3.2/§6, ADR-02 §3/§4, and SPEC-02 changed rows are otherwise materially equivalent; parity alone does not make the statements accurate.

### Disposition of all 14 r1 findings

“Resolved” means the reported code-level defect is corrected in this review scope; real-Docker confirmation remains a separate stage. Each row uses the original r1 number.

| r1 | r2 disposition | Evidence |
|---|---|---|
| 1 | Resolved at code/test level | Live PostgreSQL/RabbitMQ changes, old/new authentication checks and force recreation replace restart. Injected RabbitMQ failure returns 40 and restores both `.env` and the PostgreSQL fake store. Health-failure rollback test also passes. Real stores remain unverified. |
| 2 | Original cases resolved | `user: 0:0` now emits `BASE-USER`; actual core render yields zero findings and 14 accepted exception controls. Environment mode/defaults, exceptions and expiry are tested. See R2-04 for explicit egress. |
| 3 | Resolved | Ownerless `LISTEN 0 4096 0.0.0.0:5000 0.0.0.0:*` is now a project-port violation; the corresponding command test returns 40. Inspect/ps address and command-failure tests pass. |
| 4 | Partial | Actual attacker attachment, canary control and approval scope/date checks added; inconclusive tests return 53. Broken-tool path remains R2-03. |
| 5 | Resolved for reported cases | Semgrep exit 2 with `errors` yields incomplete/51; all four local packs are invoked. Tests cover every Compose image, integration filesystem scans, failed SBOM generation and failed image scans. |
| 6 | Partial | Synthetic values are masked in logs, result text and seed/cleanup messages; owner-only modes pass. Trace ZIP still leaks (R2-01). |
| 7 | Partial | Exact origins and guarded API/browser contexts added; redirects and absent WebSocket interception remain R2-02. |
| 8 | Partial | `grdm.internal: true` is generated; published services additionally use `grdm-edge`, now described normatively. Explicit egress and documentation remain R2-04/R2-05. |
| 9 | Resolved | Private URL literal removed; manifest/private-URL policy check passes on the shared checkout and CI. |
| 10 | Resolved | Re-render with own web listener on 5000 preserves `127.0.0.1:5000:5000`; foreign collision/remap tests pass. |
| 11 | Resolved | Captured push arguments contain one tag, `ghcr.io/rcosdp/web:abc123`, and no local registry destination; load-form test also passes. |
| 12 | Resolved for reported cases | Health precheck precedes pytest; missing Chromium, zero rows and missing rejection fail. C2 checks actual permissions, C3 uses a signed-in non-contributor, C4 checks both directions, C6 requires API 403. Selectors and real integration still need stage two. |
| 13 | Resolved | Non-editable install into a temporary target resolves the installed acceptance package, with 11 scenario files, `conftest.py` and `pytest.ini`, outside the checkout. |
| 14 | Original link/check failure resolved | Required docs check passes. At requested head Semgrep CI fails; follow-up `1c2a925` makes all six CI jobs pass. New documentation defects are R2-05. |

### Validation and documentation evidence

Observed results, not a canonical manifest (TOON is a compact text form for structured data):

```toon
checks[7]{check,result}:
  pinned_installer_tests,"247 run; OK at 3149c76"
  pinned_docs_check,"PASSED; 51 checked; 8 exempt; 126 warnings"
  shared_installer_tests,"247 run; OK"
  shared_docs_check,"PASSED before this review; 51 checked; 8 exempt; 126 warnings"
  installed_package,"non-editable install OK; 11 scenario files plus conftest and pytest.ini"
  requested_head_ci,"5 pass; Semgrep fail"
  followup_head_ci,"1c2a925: all 6 pass"
```

Run from the repository root; expected result is exit 0. Tests use fake external runners and do not change Docker state:

```sh
PYTHONPATH=installer python3 -m unittest discover -s installer/tests
python3 tools/docs_check.py
python3 tools/manifest_check.py
python3 -m unittest discover -s tools/tests
gh pr checks 21 --repo RCOSDP/RDM-developer-guide
```

The shared-checkout tools suite also passed all 66 tests; the manifest/private-URL policy check passed with zero findings. The [Playwright 1.47 generated API](https://github.com/microsoft/playwright-python/blob/v1.47.0/playwright/sync_api/_generated.py), retrieved through `gh api`, has no `route_web_socket` method.

The original Semgrep failure reports two 0700 directory-mode findings and one synthetic JWT literal. Do not weaken owner-only permissions to satisfy it; the follow-up uses documented suppression and a constructed test string. [Requested-head CI](https://github.com/RCOSDP/RDM-developer-guide/actions/runs/42023479058) and [follow-up CI](https://github.com/RCOSDP/RDM-developer-guide/actions/runs/42023972325) are distinct evidence.

Packaging initially generated `installer/build/` inside the temporary archive and caused an extra docs-check failure there. Removed only that temporary build output and reran: 51 checked, zero errors. The archive has no Git metadata, so its private-URL policy scan cannot run; the real-checkout policy check and CI supply that evidence. This tooling artefact is not attributed to the PR. The new, untracked review was additionally passed directly to `docs_check.check_file`: zero errors; the tracked-file command alone does not include it.

DEMO-20 run 1 has matching English/Japanese commands, host facts, five step outcomes and three image outcomes. It accurately labels the attempt as exit 30 before startup, not a completed installation. The source build flow supports stopping at the first failed component. However, the full log exists only in the author's session scratchpad, so the recorded host measurements, sizes and package failure were not independently re-established here. The failed mfr build alone does not prove ember/cas cannot build on arm64, nor prove the chosen amd64 builds succeed. “runtime holds two built images” should distinguish Docker's image store from files under `runtime/`. No claim is made about run 2 or M2 acceptance completion.

### Required follow-up

Fix R2-01–R2-05 and add tests that traverse the failing paths, then re-review the resulting head. Keep real install/build/startup, credential rejection against initialized stores, browser C1–C6 and actual network behavior as stage-two evidence. Existing M3 skips and upstream command placeholders are not delivered acceptance. This review grants no red-team execution or merge approval.

---

<a id="japanese"></a>
## 日本語

[→ To English](#english)

### 判定と範囲

**修正要求。** P1 は信頼する前に直す安全性の欠陥、P2 は実装または文書の契約不一致を表す。単体テストは外部プログラムを決まった応答へ置き換えるもので、実機導入の証明ではない。Docker はプログラムを分離したコンテナで動かし、Compose はその箱をまとめて記述する。秘密とはパスワードや鍵、egress とはネットワークの外へ出る通信である。

用語注: PR（変更案）、CI（自動検査）、Semgrep（ソースコード検査道具）、Playwright（ブラウザ操作の自動化道具）、arm64（Apple Silicon の CPU 系列）、amd64（Intel/AMD の CPU 系列）、mfr（ファイルプレビュー用サービス）。

r1、`1caaace`・`ae273d4`・`3149c76` の修正、ソース、テスト、指定仕様を確認した。GitHub 操作は `gh` のみ。実 Docker へのコマンド実行、製品ソース変更、commit・push・approve・merge・close はしていない。再現は一時ディレクトリ・合成秘密・差し替えた実行関数を使用した。実行中の可能性がある第2回の実機導入には触れていない。

レビュー中に共有 checkout と remote head が `1c2a925d6af687129e8f9c23f06d629db58996c0` へ進んだ。この変更は `accept.py` の Semgrep 注釈と `test_accept.py` の合成リテラルだけである。`gh api` で正確な `3149c76` のアーカイブを取得し、そのソースで247件と再現試験を実行し、文書も別途検査した。指摘の対象は `3149c76` とし、新しい CI 結果は分けて記載する。

### 残る指摘

1. **R2-01 — P1: 保存するブラウザ trace に秘密が残る（r1 #6 は一部解消）。** `installer/grdm_dev/accept.py:275` は `--tracing retain-on-failure` を指定するが、359〜363行の `sanitize_run_dir` は `junit.xml`・`collector.json`・`pytest.log` しかマスクしない。`artifacts/` 以下は権限変更だけである。再現では、合成 `.env` 値を `pytest.log` と `artifacts/trace.zip` の `trace.network` メンバーに入れ、`sanitize_run_dir(run_dir, [value])` を実行した。ログは消えたが ZIP 内には同じ値が残った。trace は cookie・ヘッダ・応答本文を持ち得るため、0600 だけでは証跡へ秘密を書かない契約を満たさない。trace 内部と他の出力を無害化するか、安全になるまで無効化・隔離し、ZIP 内部の検査を追加する。「every evidence file」という既存テストはテキストだけを検査している。

2. **R2-02 — P1: API の転送が通信ガードを迂回する（r1 #7 は一部解消）。** `installer/acceptance/conftest.py:162` は `kwargs.setdefault("max_redirects", 0)` である。`GuardedRequest(...).get("http://127.0.0.1:5000", max_redirects=20)` を呼ぶと、下位の要求に20がそのまま渡ることを引数捕捉で確認した。ローカル応答から外部へ転送すると、応答 URL の確認前に通信が発生する。後からの失敗では取り消せず、外部を経てループバックへ戻る場合は最終 URL 検査でも分からない。転送を強制的に0にして各転送先を確認するか、上書きを拒否する。また `guard_context:204` は WebSocket ルーティングのメソッドが無い場合に黙って省略し、`pyproject.toml:19` は Playwright 1.47 を許す。必要な機能・版を必須にするか、検査不能なら停止する。正確な origin 判定、コア試験のラップ、service worker 禁止は改善だが、これらの経路は残る。

3. **R2-03 — P1: 攻撃側の壊れた疎通検査を隔離の証明と誤認する（r1 #4 は一部解消）。** `installer/grdm_dev/redteam.py:207–220` は `nc` のすべての非ゼロ終了を `GRDM_REACH_FAIL`、さらに `unreachable` と扱う。通信しない再現として、未対応オプションを模した終了2の `nc` スタブを PATH に置き、`/bin/sh` で `probe_script("192.0.2.1", 443)` を実行して `verdict` へ渡した。シェルは終了0で `GRDM_REACH_FAIL` を出し、`inconclusive` でなく `unreachable` となる。対照試験は別コンテナの別の実行ファイルなので攻撃側の道具を検証できない。443への HTTP 代替処理も接続後に失敗し得る。既知の TCP 検査を用い、攻撃側で道具自体の動作を確認し、道具・プロトコルの異常と通信遮断を区別し、不確かなら53を返す。道具欠落・マーカー欠落・対照失敗・接続先・承認欄の追加試験は合格したが、この経路を覆わない。

4. **R2-04 — P2: 明示的に許可した外向き通信を baseline が拒否する（r1 #8/#2 の続き）。** `installer/grdm_dev/scan.py:487–489` は、ポートを公開しないサービスの外部ネットワーク接続を、記録済みの `GRDM_EGRESS_SERVICES` を見ずに拒否する。実 core manifest を `egress="worker"` で生成すると終了0で選択も記録されるが、`check_baseline(compose_path, hardening_path, env_path)` は `worker` の `BASE-NETWORK` を返した。外向き許可なしなら検出0件、hardening 例外対策14件を受理する。SPEC-03 §3.2 は記録した許可を違反としないと明記する。許可記録と実接続を照合し、許可済みは通し、未申告は拒否する生成→検査の試験を追加する。

5. **R2-05 — P2: 変更文書にも契約の欠落・誤記がある。** SPEC-01 は新版履歴に `build_platform` を挙げるが、両言語の §3 の表に型・許容値・任意性・優先順位の定義がない。日本語 `integration_sha` 行も全文英語のままである。SPEC-02 §3 は部品が amd64 を選ぶようになっても build 既定をホストのみと記し、カナリアのコンテナ・ネットワークを作成・削除する `redteam preflight` を read-only とする。ADR-02 §3 は公開サービスの二重接続を説明するが、§4 は「既定では外向き通信がない」と述べる。その7サービスは明示許可なしでも通常 bridge に接続する。両言語を同時に直し、外へ通信できる範囲を明記する。新しい SPEC-03 §3.2/§6、ADR-02 §3/§4、SPEC-02 の変更行は、それ以外では英和の意味が対応するが、翻訳一致だけでは内容の正しさにならない。

### r1 全14件の判定

「解消」は報告されたコード上の欠陥が対象範囲で直ったという意味で、実 Docker の確認は別段階である。番号は r1 と同じ。

| r1 | r2 判定 | 証拠 |
|---|---|---|
| 1 | コード・試験上解消 | PostgreSQL/RabbitMQ の実効更新、新旧認証確認、強制再作成へ変更。RabbitMQ 失敗注入で40を返し `.env` と PostgreSQL の模擬値を旧値へ復元。再作成後 health 失敗の復旧試験も合格。実 DB は未確認。 |
| 2 | 元の再現は解消 | `user: 0:0` は `BASE-USER`。実 core 生成は検出0、例外対策14件受理。環境ファイルの権限・既定値・例外・期限も試験済み。明示 egress は R2-04。 |
| 3 | 解消 | 所有者なしの `LISTEN 0 4096 0.0.0.0:5000 0.0.0.0:*` はプロジェクトポート違反。対応コマンド試験は40。inspect/ps の公開先と道具失敗の試験も合格。 |
| 4 | 一部解消 | 実攻撃側の接続網・カナリア対照・承認範囲と日付を追加。不確かな場合の試験は53。壊れた道具は R2-03。 |
| 5 | 報告した経路は解消 | Semgrep 終了2＋errors は incomplete/51。ローカル4パック、全 Compose イメージ、統合ソースの filesystem、SBOM 失敗、イメージ検査失敗を試験。 |
| 6 | 一部解消 | ログ・結果テキスト・seed/cleanup 出力の合成秘密をマスクし、所有者限定権限も合格。trace ZIP は R2-01。 |
| 7 | 一部解消 | 正確な origin と API/browser のガード追加。転送と WebSocket 遮断欠落は R2-02。 |
| 8 | 一部解消 | `grdm.internal: true` を生成し、公開サービスは仕様改定どおり `grdm-edge` にも接続。明示 egress と文書は R2-04/R2-05。 |
| 9 | 解消 | 非公開 URL 直書きを除去。共有 checkout と CI の manifest/非公開 URL 方針検査合格。 |
| 10 | 解消 | 自身の web が5000使用中でも再生成後は `127.0.0.1:5000:5000`。他プロセスの衝突・再割当試験も合格。 |
| 11 | 解消 | push 引数のタグは `ghcr.io/rcosdp/web:abc123` の一つで、ローカルタグの送信先なし。load 形式の試験も合格。 |
| 12 | 報告した経路は解消 | pytest 前の health、Chromium 実体、結果0行・拒否行欠落の失敗を確認。C2 実権限、C3 ログイン済み非参加者、C4 双方向、C6 API 403 を要求。実セレクタ・統合は第二段階。 |
| 13 | 解消 | 一時領域へ非 editable 導入し、checkout 外で同梱 acceptance を解決。シナリオ11ファイル、conftest、pytest.ini を確認。 |
| 14 | 元のリンク・検査失敗は解消 | 必須文書検査合格。指定 head の Semgrep CI は失敗したが、追補 `1c2a925` は6ジョブすべて合格。新たな文書欠陥は R2-05。 |

### 検証と文書証跡

実測であり manifest 正本の転載ではない。TOON は構造化データを短く表す文字形式である。

```toon
checks[7]{check,result}:
  pinned_installer_tests,"3149c76 で247件; OK"
  pinned_docs_check,"合格; 51検査; 8除外; 126警告"
  shared_installer_tests,"247件; OK"
  shared_docs_check,"本レビュー追加前に合格; 51検査; 8除外; 126警告"
  installed_package,"非 editable 導入成功; シナリオ11ファイルと conftest・pytest.ini"
  requested_head_ci,"5合格; Semgrep失敗"
  followup_head_ci,"1c2a925: 6件すべて合格"
```

リポジトリ root から実行し、期待値は終了0。単体テストは外部実行を模擬するため Docker の状態を変更しない。

```sh
PYTHONPATH=installer python3 -m unittest discover -s installer/tests
python3 tools/docs_check.py
python3 tools/manifest_check.py
python3 -m unittest discover -s tools/tests
gh pr checks 21 --repo RCOSDP/RDM-developer-guide
```

共有 checkout の tools テストも66件すべて合格し、manifest/非公開 URL 方針検査は検出0件で合格した。`gh api` で取得した [Playwright 1.47 の生成 API](https://github.com/microsoft/playwright-python/blob/v1.47.0/playwright/sync_api/_generated.py) に `route_web_socket` メソッドがないことも確認した。

元の Semgrep 失敗は0700ディレクトリ権限2箇所と合成 JWT リテラル1箇所である。権限を緩めて直すべきではなく、追補は根拠付き除外とテスト文字列の構築を使用する。[指定 head の CI](https://github.com/RCOSDP/RDM-developer-guide/actions/runs/42023479058) と [追補 CI](https://github.com/RCOSDP/RDM-developer-guide/actions/runs/42023972325) は別の証跡である。

パッケージ試験が一時アーカイブ内に `installer/build/` を作り、その一時領域の文書検査が追加で失敗した。その生成物だけを除去して再実行し、51件検査・エラー0となった。アーカイブには Git 情報がないので非公開 URL 方針検査を実行できず、実 checkout と CI の検査を証拠とした。この検証作業の生成物による失敗を PR の欠陥とは扱わない。未追跡の新レビュー自体も `docs_check.check_file` へ直接渡し、エラー0を確認した。追跡済みファイルだけを見る通常コマンドには含まれないためである。

DEMO-20 第1回は、英和でコマンド・ホスト情報・5段階の結果・3イメージの結果が一致する。起動前の終了30と明記し、導入完了と誤記していない。build の制御も最初の失敗で止まる。ただし全ログは作者のセッション作業領域にしかなく、ホスト実測・サイズ・パッケージ失敗を本レビューで独立再確認したわけではない。mfr の失敗だけでは ember/cas の arm64 不可や amd64 成功を証明しない。また「runtime にビルド済みイメージ2つ」は Docker のイメージ保管場所と runtime のファイルを区別すべきである。第2回や M2 受入完了は認定していない。

### 必要な次の作業

R2-01〜R2-05 を直し、失敗経路を通る試験を加えて、その head を再レビューする。実導入・build・起動、初期化済み DB の旧認証拒否、ブラウザ C1〜C6、実ネットワーク挙動は第二段階の証跡とする。M3 向け skip と upstream の未実装入口は受入完了ではない。本レビューはレッドチーム実行やマージの承認ではない。

---

## Glossary / 用語

| Term | English note | 日本語注 |
|---|---|---|
| Baseline | Checks that every installation must pass. | すべての導入が通る必須検査。 |
| Trace | A saved record of browser actions and network exchanges. | ブラウザ操作と通信を保存した記録。 |
| Origin | The exact scheme, host and port of a URL. | URL の方式・ホスト・ポートの組合せ。 |
| Canary / control | A known reachable target used to check the probe itself. | 検査自体が動くか確かめる既知の接続先。 |
| Rollback | Restore the previous working values after a failure. | 失敗後に以前の値へ戻す処理。 |
| CI | Automatic checks run for a proposed code change. | 変更案に対して自動で実行する検査。 |
| SBOM | A list of the software parts in an image or project. | イメージやプロジェクトに入るソフトウェア部品の一覧。 |
