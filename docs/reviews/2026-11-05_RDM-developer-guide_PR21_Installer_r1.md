# REV PR21 Installer review r1 / インストーラーレビュー r1

> **Summary:** Independent review of PR #21 at `6985d0600c2a9dcec5c50331aebcb60fb4f23b13`. Changes requested: security checks can pass unsafe states, generated settings fail their own baseline, and acceptance evidence is incomplete.
> **概要:** PR #21 の `6985d0600c2a9dcec5c50331aebcb60fb4f23b13` を独立レビューした。安全でない状態を検査が合格させ、生成設定が自身の必須検査に落ち、受入証跡も不足するため修正を要求する。

**Jump:** [English](#english) · [日本語](#japanese)

- Version / 版: 0.1 — 2026-11-05. **Learned:** passing isolated command tests does not prove that generated configuration, scanners, and credential rotation agree. ／ コマンド単独の試験だけでは、生成設定・検査・認証情報更新の整合は証明できないと分かった。
- Applies to: PR #21, `feat/m2-installer` → `develop`; independent REV review, no merge or approval.
- Related: [Review index](README.md) · [SPEC-01](../spec/01_manifest.md) · [SPEC-02](../spec/02_installer_cli.md) · [SPEC-03](../spec/03_security_gate.md) · [SPEC-04](../spec/04_acceptance_tests.md) · [SPEC-06](../spec/06_documentation_conventions.md) · [ADR-02](../decisions/ADR-02_Network_Model.md) · [ADR-03](../decisions/ADR-03_Staged_Security_Gate.md) · [ADR-04](../decisions/ADR-04_AI_Autonomy_and_Roles.md) · [Shared glossary](../reference/REF-01_Glossary.md).
- Used by: [Installer](../../installer/README.md) · [Acceptance suite](../../installer/acceptance/README.md) · [Status board](../status/README.md).

---

<a id="english"></a>
## English

[→ 日本語版へ](#japanese)

### Verdict and method

**Changes requested.** P1 means a defect to fix before relying on the installer; P2 means a functional or contract defect requiring correction. A security gate is a check that decides whether the environment is safe enough to use. Docker (a tool for running separate application boxes) is the tool that runs applications in separate containers; Compose describes those containers together. Unit tests replace external programs with controlled responses and do not prove real container behavior.

Reviewed the PR (a proposed change) body and diff through `gh`, the specified rules, source, tests, templates, manifests (lists of selected versions), and the supplied upstream reference files. Ran the required checks and all 21 leaf command helps plus root help. Reproductions used temporary directories and injected runners; no real Docker build, startup, registry push, or attack was run. No product source was modified.

The remote head moved to `1caaaceb4d436db99a35aa159a7abd9586df6462` before publication. This review remains scoped to the requested `6985d06`; it does not certify the newer revision. A final repository docs check passed on the changed tracked set (49 checked, 8 exempt, 121 warnings), superseding the local docs failure only for that changed workspace.

### Ranked findings

1. **P1 — Rotation does not replace live credentials.** `installer/grdm_dev/secrets.py:232,246` writes new values, then `installer/grdm_dev/lifecycle.py:54` calls `docker compose restart`. Existing containers retain their original environment; the captured command confirms no recreation. Database initialization passwords also do not change passwords in an existing database. After a captured secret, the old credential therefore remains usable while `.env` claims a different value. Implement coordinated application/database rotation and recreation, with failure recovery and an old-credential rejection test (SPEC-03 §6).

2. **P1 — Baseline validation both misses root and rejects the shipped configuration.** `installer/grdm_dev/scan.py:252-295` accepts any nonempty `user`, including `0:0`; a synthetic root service with `cap_drop: ALL` and loopback ports returns no findings. It does not validate `.env` mode/defaults, resource limits, or network isolation. Conversely, rendering the actual core manifest and hardening exceptions produces five `BASE-USER` failures: postgres, elasticsearch, mongo, rabbitmq, unoconv. The validator never reads those exceptions. Reconcile the non-root rule with the approved exception contract, then test renderer output through the real baseline checker; the current install cannot reach a successful full gate even if startup succeeds.

3. **P1 — Network health silently ignores listeners without visible process ownership.** `installer/grdm_dev/health.py:174-204` filters exclusively by Docker process name. On Linux, unprivileged `ss -ltnp` can show a root-owned wildcard listener without its process field. Feeding `LISTEN 0 4096 0.0.0.0:5000 0.0.0.0:*` yields no offending socket and no error. Correlate actual project port bindings through Docker inspection and fail closed when ownership cannot be established. Cover Docker Desktop on macOS and Linux without elevated privileges.

4. **P1 — The red-team egress probe cannot establish isolation.** `installer/grdm_dev/redteam.py:24,90-99` probes `example.invalid`, which cannot resolve even on an unrestricted network, and labels wget failure as blocked. It runs a fresh Alpine container, not the attacker container whose other network attachments and routes matter. Checking the selected network's `Internal` flag does not close that gap. Verify the actual attacker network namespace against controlled reachable destinations, distinguishing probe failure from proven isolation; also validate the approval record's scope and owner rather than file existence alone (`:114-119`).

5. **P1 — Scanner errors can become clean results and the scan omits infrastructure images.** `installer/grdm_dev/scan.py:398-407` accepts Semgrep (a source-code checker) JSON (structured machine-readable text) regardless of nonzero exit or its `errors` array; exit 2 with `{"errors":[{"message":"failed"}],"results":[]}` is reported as `result: ok`. `:355-395` selects only locally tagged `grdm-dev/` images, excluding postgres, Redis (a fast data store), Mongo and other images actually used by Compose; integration lockfiles are not explicitly scanned once local images exist. SBOM (a list of software parts) generation failures only add notes. Return 51 for incomplete scanners and enumerate all project images and required lockfiles (SPEC-03 §4); use all four required Semgrep packs, not only `p/default`.

6. **P1 — Acceptance logs bypass secret masking.** `installer/grdm_dev/accept.py:307,318,320` prints seed/cleanup subprocess output and writes pytest output verbatim under `docs/demo/runs/`. Unlike `scan.py` and `report_cmd.py`, this path never applies `.env` masking. An injected synthetic secret in runner output was copied unchanged to `pytest.log`. Exceptions can include credentials, and traces can include session material. Sanitize output before persistence or display, restrict evidence permissions, and test the evidence paths with synthetic `.env` values; do not rely on later report bundling to clean already-written files.

7. **P1 — Acceptance's network guard does not cover every request.** `installer/acceptance/conftest.py:136-156` installs only browser routing. Calls through `context.request` and independently created API request contexts (for example `installer/acceptance/test_c3_file_upload.py:29,41-43`) are not intercepted by that browser route and may follow external redirects. The download URL prefix assertion also accepts lookalike hostnames. Parse exact origins and guard API requests, redirects, WebSockets, and service-worker traffic, or enforce isolation outside the browser; SPEC-04 §3.4 promises every non-loopback request is blocked.

8. **P1 — The generated network has no Docker internal isolation flag.** `installer/grdm_dev/compose.py:316` emits only a named bridge, without `internal: true`. The actual rendered core configuration confirms this. A regular bridge permits outbound routes, contrary to the internal-network baseline in SPEC-03 §3.2 and ADR-03 §3.2. Make the intended isolation explicit and verify it on Docker Desktop; if ordinary development requires egress, obtain a normative change instead of claiming that the existing output enforces the baseline.

9. **P2 — Private repository URL fails the mandatory policy check.** `installer/tests/test_build.py:88` contains a full private integration repository URL. Production `build.py:64-66` correctly composes its URL at runtime, but the test violates the same names-only policy. Construct the expected value from separate components without committing a private URL. `tools/manifest_check.py` and the tools regression suite both reject this exact line. No apparent live token was found in the diff search; that limited search is not a full secret-scanner certification.

10. **P2 — Rendering a running installation changes its own ports.** `installer/grdm_dev/compose.py:116-153,649` treats every occupied port as foreign. Re-running install while its own web service occupies 5000 assigns 5001 and rewrites URLs; repeated runs keep moving. The idempotence test at `installer/tests/test_compose.py:180` uses a checker that always returns free (`:40`), so it cannot detect this. Preserve project-owned bindings and test both own-service and unrelated-process collisions.

11. **P2 — `build --push` attempts to publish the local tag as well.** `installer/grdm_dev/build.py:123-127` supplies both `grdm-dev/<component>` and `ghcr.io/rcosdp/<component>` with `--push`. The unqualified first tag addresses Docker Hub, outside the promised private GHCR destination, and can fail authorization or publish to the wrong registry. Use only the GHCR tag for push; keep local tags for load. Test the complete argument list and the absence of other registry destinations.

12. **P2 — Acceptance omits the mandatory integration precheck and has weak success criteria.** `installer/grdm_dev/accept.py:265-320` proceeds directly to pytest after dependency/path checks; a fake successful pytest yields exit 0 with no health/integration call and zero collected result rows. SPEC-04 §2 requires integration first. C2 supplies `['admin']` when permissions are missing (`installer/acceptance/test_c2_create_project.py:31`); C3 tests anonymous PUT instead of a signed-in non-contributor (`test_c3_file_upload.py:35-48`); C4 checks only B-to-A propagation (`test_c4_wiki_collab.py:47-53`); C6 accepts API 404 although the contract requires 403 (`test_c6_admin.py:39-40`). Require the specified success and rejection evidence and fail incomplete runs. Check Chromium's executable, not merely a nonempty browser directory (`accept.py:277-279`).

13. **P2 — Installed package omits its acceptance suite.** `installer/pyproject.toml:25-30` packages only `grdm_dev`, messages and templates; `installer/grdm_dev/accept.py:44` searches a sibling `acceptance` directory. In a non-editable installation that suite is absent. Include it in the distribution or resolve it explicitly from the selected repository. The PR's console-script/data-file smoke test does not validate acceptance execution from the installed package.

14. **P2 — Documentation and reported validation are not green at the reviewed head.** The PR-added `docs/reviews/2026-11-05_RDM-developer-guide_PR20_Manifest_Shibboleth_r3.md:10` links to the absent `2026-11-05_dev2027_Strict_Reconstruction_PRs_r2.md`; confirmed in the remote head through `gh api`. The first docs run reports that broken link; later runs report the tracked review file missing locally. Installer tests consequently fail their repository docs check. Report this workspace change separately from the confirmed remote-head broken link. Fix the link and update the PR's passing-test claims after rerunning on a stable checkout.

### Coverage, contract gaps, and evidence

The following are observations, not additional security approvals. Secret (a password or key) generation uses random values and writes `.env` as 0600 inside a 0700 directory. Rendered files preserve secret references rather than values, bind published ports to 127.0.0.1, set `cap_drop: ALL` and `no-new-privileges`, and use non-root users except the reasoned hardening exceptions. The old alias occurs in prohibition checks/tests and historical material in the diff; it is not emitted by the renderer or added to the host. Report masking covers known `.env` string values of length at least eight; it is not universal redaction of unknown secrets.

All requested helps returned 0 and the 13 message codes agree with SPEC-02 §6. `upstream mirror/integrate` exist only as exit-2 placeholders (`installer/grdm_dev/upstream.py:1-32`), so full §3 conformance is not delivered; the PR body does not explicitly claim those two functions. Non-interactive confirmation is implemented for reset through `Context.confirm`; there is no general no-terminal/without-`--yes` rejection for install or seed. Resolve the distinction between the global flag's “required without a terminal” wording and §7's question-specific rule. `secrets init` keeps an existing file by refusing with exit 2, consistent with §3's overwrite prohibition but not a repeated-success interpretation of §7.

The staged thresholds correctly distinguish M1 reporting, M2/M3 count ceilings, M4 open HIGH/CRITICAL and M5 high-severity allow-list restrictions. Expired entries stop suppressing findings. However, malformed milestone JSON silently falls back to M1 (`scan.py:100-112,560-566`), and no next-milestone expiry boundary is enforced; these are further fail-closed contract gaps to address before later milestones. The current scan also does not implement the promised `docs/status/security_<milestone>.md` excerpt or an M5 unresolved-red-team-path check.

SPEC-01 adds matching `integration_sha` rows in both halves, but the Japanese row is English. All current integration pins remain null, explicitly disallowed for M2 acceptance. SPEC-04's browser-install wording is consistent in both languages. The README files have bilingual anchors, Jump, versions and glossary tables; the installer README still lacks an Applies-to line and a link to its acceptance child, and its test procedure is inline rather than a complete fenced procedure required by SPEC-06. Compared the generated local settings with the supplied upstream reference; URL separation is present, but runtime consumer names, authentication paths and writable directory ownership still require stage-two validation.

Observed results (TOON is a compact text form for structured data; these are review observations, not mirrored canonical data):

```toon
checks[6]{check,result}:
  installer_unittest,"174 run; 1 failure in test_docs"
  tools_unittest,"66 run; 1 failure in tracked private-URL policy"
  manifest_check,"exit 1; test_build.py:88 private URL"
  docs_check,"exit 1; PR20 review link or locally missing tracked file"
  cli_help,"root and 21 leaf helps exit 0"
  bash_syntax,"bash -n passes; no executable Bash-4-only construct found"
```

Commands were run from the repository root; expected merge-ready results are zero exits:

```sh
PYTHONPATH=installer python3 -m unittest discover -s installer/tests
python3 -m unittest discover -s tools/tests
python3 tools/manifest_check.py
python3 tools/docs_check.py
PYTHONPATH=installer python3 -m grdm_dev.cli --help
bash -n installer/install.sh
```

### Required second stage on Mac Studio

**Real-Docker build, up, and acceptance are deferred to stage two, as the PR body states; none is certified by this review.** After fixing the findings, verify all of the following before declaring M2 complete:

- Pin integration SHAs (exact source revisions) and base-image digests (exact image identities), then build cleanly on arm64 (the Apple Silicon CPU family); verify Dockerfile selection, image tags and Compose image identity, and separately verify amd64 (the Intel/AMD CPU family)/multi-platform behavior.
- Start minimum/core and test volume ownership, non-root startup, read-only paths, capability exceptions and resource limits. Verify the settings consumers against the pinned upstream code, not only the reference sample.
- Measure host listeners on macOS, loopback accessibility, internal connectivity and egress isolation. Test an AirPlay port collision and repeat install/render/up without changing existing project ports.
- Rotate secrets on an initialized database and prove new credentials work while old credentials fail; inject a synthetic credential into failure output and inspect every report/log/trace for leakage.
- Run the full scanner suite against every running image and integration lockfile, including scanner failure, allow-list expiry/count and staged threshold cases; verify generated hardening passes the intended baseline.
- Run C1–C6 success/rejection cases through Chromium, verify fakecas (a test login server) redirects/cookies, file byte equality and preview, two-way Wiki convergence and 4401 rejection, and institution-scoped admin behavior. Confirm seed APIs, exact selectors and cleanup, including partial seeding failure; retain sanitized JSON/TOON evidence under `docs/demo/runs/`.
- Exercise non-editable installation and its acceptance resources. Treat S1–S5 (currently unconditional M3 skips), Shibboleth (a system for institution logins) wiring, and upstream automation placeholders as remaining scope, not delivered acceptance.

---

<a id="japanese"></a>
## 日本語

[→ To English](#english)

### 判定と方法

**修正要求。** P1 はインストーラーを信頼する前に直す欠陥、P2 は機能または契約の欠陥を表す。セキュリティの門とは、安全に使えるかを決める検査である。Docker は分離された箱でプログラムを動かす道具、Compose は複数の箱をまとめて記述する仕組みである。単体テストは外部の道具を決まった応答に置き換えるため、実機の動作を証明しない。

`gh` で PR（変更案）の本文と差分を読み、指定仕様、実装、試験、テンプレート、manifest（採用版の一覧）、指定された上流参考ファイルを照合した。必須検査と root および末端 21 コマンドの help を実行した。再現には一時ディレクトリと差し替え関数を使った。実 Docker のビルド・起動・イメージ公開・攻撃は行わず、製品のソースは変更していない。

公開前にリモート head は `1caaaceb4d436db99a35aa159a7abd9586df6462` へ進んだ。このレビューは指定された `6985d06` が対象で、新版を認証しない。変更後の追跡対象に対する最終 docs 検査は合格した（検査 49、除外 8、警告 121）。これは変更後の作業場所についてのみ、先のローカル文書検査失敗を更新する。

### 重要度順の指摘

1. **P1 — 秘密の更新が稼働中の認証情報を置き換えない。** `installer/grdm_dev/secrets.py:232,246` は新値を保存するが、`installer/grdm_dev/lifecycle.py:54` は `docker compose restart` だけを呼ぶ。既存の箱の環境変数は変わらず、既存データベースのパスワードも初期化用環境変数では変わらない。呼出引数の再現でも再作成がなかった。漏洩した旧認証情報が使える一方で `.env` だけ新値になる。アプリとデータベースを協調更新し、失敗回復と旧値拒否を試験する（SPEC-03 §6）。

2. **P1 — 必須検査が root を見逃し、同梱の生成結果を拒否する。** `installer/grdm_dev/scan.py:252-295` は `user` が空でなければ許し、`0:0`、`cap_drop: ALL`、ループバック公開の合成設定を指摘ゼロで通した。`.env` の権限・既定値、資源制限、ネットワーク隔離も調べない。逆に実 manifest と hardening 例外から core を生成すると postgres、elasticsearch、mongo、rabbitmq、unoconv の五つが `BASE-USER` になる。検査が例外を読まないためである。非 root 規則と承認済み例外の契約を整え、生成結果を実検査へ渡す試験を追加する。現状は起動しても全体検査を成功できない。

3. **P1 — プロセス所有者が見えない待受をネットワーク検査が無視する。** `installer/grdm_dev/health.py:174-204` は Docker のプロセス名だけで抽出する。Linux の一般権限の `ss -ltnp` は root 所有の待受のプロセス欄を省略する場合がある。`LISTEN 0 4096 0.0.0.0:5000 0.0.0.0:*` を与えると違反もエラーもゼロになる。Docker の実際の公開設定と照合し、所有関係が不明なら合格させない。macOS の Docker Desktop と一般権限の Linux を試験する。

4. **P1 — レッドチームの外向き通信検査が隔離を証明できない。** `installer/grdm_dev/redteam.py:24,90-99` は通常の接続でも名前解決できない `example.invalid` に接続し、失敗を遮断と判定する。実際の攻撃側の箱でなく、新しい Alpine の箱を使うため、別ネットワークへの接続や経路も確認できない。指定ネットワークの `Internal` 属性だけでは不足する。管理された接続可能な宛先に対して実際の攻撃側の環境で検査し、検査不能と遮断を分ける。承認記録も存在だけでなく所有者と対象範囲を検証する（`:114-119`）。

5. **P1 — スキャナーのエラーが正常扱いになり、基盤イメージが漏れる。** `installer/grdm_dev/scan.py:398-407` は Semgrep の終了値と `errors` 配列を確認しない。終了 2、エラーあり、結果空の JSON（機械が読む構造化データ）を渡しても `result: ok` となる。`:355-395` は `grdm-dev/` イメージだけを選び、実際に使う postgres、Redis、Mongo などを除外する。ローカルイメージがあれば統合側の依存固定ファイルも明示的に検査しない。構成部品一覧の生成失敗も注記だけである。不完全な検査は 51 とし、全イメージ・依存固定ファイルと、`p/default` 以外も含む必須四組の Semgrep 規則を検査する（SPEC-03 §4）。

6. **P1 — 受入ログが秘密のマスクを通らない。** `installer/grdm_dev/accept.py:307,318,320` は seed・cleanup の出力を表示し、pytest の出力を `docs/demo/runs/` にそのまま書く。`scan.py` と `report_cmd.py` と違い `.env` の値を隠さない。差し替え関数の合成秘密文字列が `pytest.log` に残ることを確認した。例外や追跡記録には認証情報が入る場合がある。表示・保存前のマスクと証跡の権限制限を行い、合成 `.env` 値で全出力を試験する。後の報告集約だけでは既存ファイルを消毒できない。

7. **P1 — 受入の通信制限が全要求を覆わない。** `installer/acceptance/conftest.py:136-156` はブラウザ経路だけを遮断する。`context.request` や独立した API 要求の文脈（例 `installer/acceptance/test_c3_file_upload.py:29,41-43`）はその経路を通らず、外部への転送を追える。ダウンロード URL の前方一致も似たホスト名を許す。正確な接続先を解析し、API・転送・WebSocket・service worker を制限するかブラウザ外で隔離する。SPEC-04 §3.4 の約束は全非ループバック要求の遮断である。

8. **P1 — 生成ネットワークに Docker の内部隔離属性がない。** `installer/grdm_dev/compose.py:316` は名前付き bridge だけを生成し、`internal: true` がない。実 core の生成結果でも確認した。通常の bridge は外向き経路を持ち、SPEC-03 §3.2 と ADR-03 §3.2 の内部ネットワーク必須対策に合わない。隔離設定を明示し Docker Desktop で確認する。通常開発で外向き通信が必要なら、現出力が必須対策を満たすと主張せず規範側の変更を行う。

9. **P2 — 非公開リポジトリ URL が必須方針検査に落ちる。** `installer/tests/test_build.py:88` に非公開統合リポジトリの URL 全体が直書きされる。本体 `build.py:64-66` は実行時に組み立てているが、試験も名前だけの方針に従う必要がある。期待値を別々の部品から組み立てる。`tools/manifest_check.py` と tools の回帰試験がこの行を拒否した。差分検索で実トークンらしい値は見つけなかったが、完全な秘密検査の認証ではない。

10. **P2 — 稼働中に再生成すると自身のポートが移動する。** `installer/grdm_dev/compose.py:116-153,649` は使用中ポートをすべて他者のものと扱う。自分の web が 5000 を使っていると再導入で 5001 に変わり、URL を書き換える。繰返すたびに移動する。`installer/tests/test_compose.py:180` の再実行試験は常に空きと返す関数（`:40`）のため検出できない。自分の公開設定を保持し、自身と他プロセスの両方の衝突を試験する。

11. **P2 — `build --push` がローカル用タグも公開しようとする。** `installer/grdm_dev/build.py:123-127` は `--push` に `grdm-dev/<component>` と `ghcr.io/rcosdp/<component>` の両方を渡す。最初の省略形式は Docker Hub を指すため、認証失敗や意図しない公開先への送信になる。push は GHCR 用タグだけにし、ローカル用は load に限定する。引数全体と余分な公開先がないことを試験する。

12. **P2 — 受入が必須の統合事前検査をせず、合格条件も弱い。** `installer/grdm_dev/accept.py:265-320` は依存・パス確認後に直接 pytest を呼ぶ。合成 pytest の正常終了だけで、health・統合検査なし、結果行ゼロでも 0 になった。SPEC-04 §2 は統合検査を先に要求する。C2 は権限欠落時に `['admin']` を補う（`installer/acceptance/test_c2_create_project.py:31`）。C3 はログイン済み非参加者でなく匿名 PUT（`test_c3_file_upload.py:35-48`）、C4 は B→A の片方向（`test_c4_wiki_collab.py:47-53`）、C6 は契約の 403 に加えて 404 も許す（`test_c6_admin.py:39-40`）。所定の成功・拒否証跡を必須にし、不完全実行を失敗させる。ブラウザも空でないディレクトリでなく実行ファイルを検査する（`accept.py:277-279`）。

13. **P2 — 通常インストールの配布物に受入スイートがない。** `installer/pyproject.toml:25-30` は `grdm_dev` と messages・templates だけを同梱するが、`installer/grdm_dev/accept.py:44` は隣の `acceptance` を探す。非 editable 導入では存在しない。配布物へ含めるか、指定リポジトリから明示的に解決する。PR の console script とデータファイルの確認だけでは受入実行を証明できない。

14. **P2 — 文書検査と PR の合格報告が一致しない。** PR が追加する `docs/reviews/2026-11-05_RDM-developer-guide_PR20_Manifest_Shibboleth_r3.md:10` は存在しない `2026-11-05_dev2027_Strict_Reconstruction_PRs_r2.md` を参照する。`gh api` で対象 head の内容も確認した。最初の docs 検査はリンク切れ、その後は追跡済みレビュー自体がローカルで見つからないと報告した。installer 試験も文書検査で落ちる。作業場所の変化と、対象 head で確認したリンク切れを区別して扱う。修正後に安定した checkout で再検査し、PR 本文の全件合格記載を更新する。

### 確認範囲・契約の不足・証拠

次は観測であり追加の安全承認ではない。秘密は乱数生成され `.env` は 0600、親は 0700 で保存する。生成ファイルは秘密の値でなく参照を保持し、公開は 127.0.0.1、`cap_drop: ALL` と `no-new-privileges` を設定し、理由付き例外以外は非 root にする。旧別名は差分の禁止検査・試験・歴史資料に現れるが、生成結果やホスト設定には追加しない。報告のマスクは `.env` にある八文字以上の既知の文字列が対象であり、未知の秘密をすべて消す仕組みではない。

全 help は 0、13 個のメッセージコードは SPEC-02 §6 と一致した。`upstream mirror/integrate` は終了 2 の未実装入口である（`installer/grdm_dev/upstream.py:1-32`）。§3 全体への準拠は未達だが、PR 本文はこの二機能を明示的に主張していない。非対話確認は reset で `Context.confirm` を通す。install・seed 全般には端末なし・`--yes` なしの拒否がない。グローバルフラグの「端末なしで必須」と §7 の質問に対する規則の違いを整理する。`secrets init` は既存ファイルを残して 2 を返す。§3 の上書き拒否には合うが、§7 を再実行でも成功と読むなら一致しない。

段階別の判定は M1 報告、M2/M3 件数上限、M4 未許容 HIGH/CRITICAL、M5 高重大度の許容禁止を区別する。期限切れは抑制対象から外れる。ただし milestone JSON の破損は M1 に戻る（`scan.py:100-112,560-566`）。次の節目より前という期限境界も検証しない。後続段階までに、検査不能なら通さない契約へ直す必要がある。約束された `docs/status/security_<milestone>.md` の抄録と、M5 の未解決侵入経路確認も未実装である。

SPEC-01 の `integration_sha` 行は両半分で対応するが、日本語側も英文のままである。現在の統合 pin（正確な版の指定）はすべて null で、M2 受入には不可と明記される。SPEC-04 のブラウザ導入説明は英和一致する。両 README は英和アンカー・Jump・版・用語表を備えるが、installer README は適用対象行と子の acceptance へのリンクがなく、試験手順も SPEC-06 の完全なコードブロックでなく本文内表記である。生成 local 設定を指定の上流参考と照合し、内外 URL の分離は確認した。実際の利用側の設定名、認証経路、書込ディレクトリ所有者は第二段階で検証する。

観測結果を TOON（構造化データを短く書く文字形式）で記す。正本の転載ではなくレビュー実測である。

```toon
checks[6]{check,result}:
  installer_unittest,"174 件実行; test_docs で 1 件失敗"
  tools_unittest,"66 件実行; 非公開 URL 方針で 1 件失敗"
  manifest_check,"終了 1; test_build.py:88 非公開 URL"
  docs_check,"終了 1; PR20 レビューのリンクまたはローカル追跡ファイル欠落"
  cli_help,"root と末端 21 個の help が終了 0"
  bash_syntax,"bash -n 合格; Bash 4 専用の実行構文なし"
```

リポジトリのルートで実行した。統合可能な状態ではすべて終了 0 を期待する。

```sh
PYTHONPATH=installer python3 -m unittest discover -s installer/tests
python3 -m unittest discover -s tools/tests
python3 tools/manifest_check.py
python3 tools/docs_check.py
PYTHONPATH=installer python3 -m grdm_dev.cli --help
bash -n installer/install.sh
```

### Mac Studio で必須の第二段階

**実 Docker の build・up・受入は PR 本文のとおり第二段階へ延期され、このレビューでは認証していない。** 指摘修正後、M2 完了前に次を実施する。

- 統合 SHA（ソースの正確な版）と基盤 digest（イメージの正確な識別値）を固定し arm64 で新規ビルドする。Dockerfile 選択、タグと Compose の参照一致、別途 amd64・複数環境向けのビルドを確認する。
- minimum/core を起動し、保存領域の所有者、非 root 起動、読取専用パス、権限例外、資源制限を確認する。設定を読む実コードも固定した上流版と突き合わせる。
- macOS の実待受、ループバック接続、内部通信、外向き隔離を測る。AirPlay 衝突と再導入・再生成・再起動でも自身のポートが変わらないことを確認する。
- 初期化済みデータベースの秘密を更新し、新値成功・旧値拒否を確認する。合成秘密を異常出力へ入れ、全報告・ログ・追跡記録に漏れがないか確認する。
- 全稼働イメージと統合側の依存固定ファイルを検査し、検査不能、許容期限・件数、段階別閾値も確認する。生成 hardening が意図した必須検査を通ることを確認する。
- Chromium で C1–C6 の成功・拒否を実行する。fakecas の転送と cookie、ファイル一致とプレビュー、Wiki の双方向同期と 4401、所属機関の管理画面を確認する。seed API・セレクタ・部分失敗時も含む後片付けを確定し、秘密を除いた JSON/TOON を `docs/demo/runs/` に残す。
- 非 editable 導入で受入資源を確認する。現在 M3 として無条件スキップする S1–S5、Shibboleth 接続、上流自動化の未実装入口は、受入済みでなく残作業とする。

---

## Glossary / 用語

| Term | English note | 日本語注 |
|---|---|---|
| P1 / P2 | Before-reliance defect / functional or contract defect. | 信頼する前に直す欠陥／機能・契約の欠陥。 |
| Credential rotation | Replace keys and make the previous keys stop working. | 鍵を交換し、以前の鍵を使えなくすること。 |
| Loopback | An address that leads back to the same computer. | 同じ計算機へ戻るアドレス。 |
| Egress | A connection leaving the isolated environment. | 隔離環境から外へ向かう通信。 |
| Runner | A function that executes an external program, replaced in tests. | 外部プログラムを実行し、試験で置き換える関数。 |
| Registry | A service that stores and distributes container images. | コンテナのイメージを保管・配布する場所。 |
| Idempotence | Repeating an operation preserves the intended state. | 繰返しても意図した状態を保つこと。 |
