# REV PR56 Installer final pins review r1 / インストーラー最終固定版レビュー r1

> **Summary:** Changes requested: the ZAP sign-in exception accepts unrelated connection failures, and ADR-14 prescribes the wrong upgrade sequence. The four requested check suites passed.
> **概要:** 要修正。ZAP のサインイン除外が無関係な接続失敗も成功扱いにし、ADR-14 の更新手順も誤っている。指定された四種類の検査は通過した。

**Jump:** [English](#english) · [日本語](#japanese)

- Version / 版: 0.3 — 2026-11-13. **Learned:** Publication must redact provenance locations and body artifact paths as well as link destinations; only these location labels changed, with judgments, findings, test results and earlier version lines preserved. ／ 公開時はリンク先だけでなく出典の場所と本文の成果物パスも秘匿する。場所の表記のみを変更し、判定、指摘、試験結果、過去の版行を保持した。
- Version / 版: 0.2 — 2026-11-13. **Learned:** REV changed only link destinations for publication: scratch-path links were replaced by repository-relative links or plain-text references. ／ REV は公開のためリンク先のみを変更し、作業用パスへのリンクをリポジトリ相対リンクまたは平文の参照に置き換えた。
- Provenance / 出典: Original file / 原本: `2026-11-13_RDM-developer-guide_PR56_Installer_Final_Pins_r1.md`. Publication 0.3 redacts only original-file locations, local artifact paths and the guest checkout location to basenames or neutral artifact names; prior publication link changes remain. Judgments, findings, test results and earlier version lines are unchanged. ／ 公開版 0.3 では原本の場所、ローカル成果物のパス、ゲスト配置先のみをファイル名または中立的な成果物名に置換し、前公開版のリンク修正を維持する。判定、指摘、試験結果、過去の版行は変更しない。
- Version / 版: 0.1 — 2026-11-13. **Learned:** successful unit tests do not establish that a scanner exemption identifies the authentication boundary; an unrelated redirect must remain a failed scan. ／ 単体試験の成功だけでは検査除外が認証の境界を識別しているとは言えず、無関係な転送先への失敗は検査失敗として残す必要がある。
- Applies to: RCOSDP/RDM-developer-guide PR #56, head `eae88bdd9b61550920d975146d3275ba6aca43bc`, base `develop`; REV round 1.
- Related: [PR #56](https://github.com/RCOSDP/RDM-developer-guide/pull/56) · [review index](../reviews/README.md) · [SPEC-06](../spec/06_documentation_conventions.md).
- Reviewer: REV（担当レビュワ, Codex Astra）.

---

<a id="english"></a>
## English

[→ 日本語版へ](#japanese)

### Verdict

**Changes requested.** R1-01 and R1-02 should be corrected before integration. Review used a clean, detached clone at the specified head. No live Docker commands, live runtime secrets, repository edits, commits, pushes, approvals or merges were used. Test fixtures created only their own temporary files. One PR comment accompanies this report.

### R1-01 — P2: restrict the ZAP exception to a verified sign-in redirect

Location: `installer/grdm_dev/scan.py:1058–1065,1108–1113`; related test `installer/tests/test_scan.py:796–807`.

`zap_behind_sign_in()` accepts any unreachable host different from the target's netloc. It does not check the redirect chain, configured identity-provider endpoint, service, or public-access setting. `run_zap()` then discards a missing report and nonzero scanner exit, and reports the tool as `ok`. An application redirect to a broken unrelated host, or a scanner connection message using a different address representation, can therefore silently bypass dynamic scanning. The note additionally asserts mandatory sign-in without proving it.

Reproduced without Docker using the existing scanner test harness: `write_compose()`, a healthy web row, `zap_rc=3`, no JSON report, and this output:

```text
Job spider failed to access URL http://web:5000 : Connect to http://unexpected.invalid:9443 failed: Connection refused
```

Observed result:

```toon
reproduction:
  exit: 0
  tool: zap
  result: ok
  targets: 1
  problems: 0
  note: "ZAP skipped web ... unexpected.invalid:9443 ... mandatory sign-in, ENABLE_PUBLIC_ACCESS=false"
```

Require positive evidence of the expected authentication redirect, restricted to the intended service and configured authentication destination. Unknown destinations, public-access mode, and missing reports without that evidence must retain scanner-unavailable exit 51. Record an authenticated-wall exclusion explicitly as skipped coverage, rather than counting it as a scanned target. Add behavioral regression tests for unknown hosts, a different representation of an unreachable target, public access, and the legitimate configured sign-in redirect. Existing tests exercise only the happy exception and exactly matching target host, so they pass despite this defect.

### R1-02 — P2: replace ADR-14's rotate-before-render upgrade instructions

Location: `docs/decisions/ADR-14_Elasticsearch_8_with_TLS_and_Authentication.md:50,92`.

Both language halves tell an existing installation to run `secrets rotate` before `compose render`. This contradicts the environment guide §8, the PR procedure, and SPEC-02's existing warning that rendering must precede rotation when keys are retired. Rotation changes all current secrets, drops `SHAREJS_SECRET`, and recreates containers using the still-old Compose definition, which can still reference that removed key and the retired services. It is an unnecessary credential-changing upgrade path and can fail or roll back before the new configuration is rendered.

Use the implemented `secrets init --missing` followed by render/build/render/up and the once-only `invoke migrate_search` step, or link to that canonical guide sequence. Preserve the old version header and add the correction in English and Japanese. The unrelated ADR statement that the first new-image scan is still pending should also be reconciled with DEMO-20's completed final-pin scan.

### Checks and evidence

Commands ran from the clean review clone using `/usr/bin/python3`; each process exit was checked:

```toon
checks[4]{command,exit,result}:
  "PYTHONPATH=installer /usr/bin/python3 -m unittest discover -s installer/tests",0,"672 tests; 10 skipped; 85.924 seconds"
  "/usr/bin/python3 -m unittest discover -s tools/tests",0,"93 tests"
  "/usr/bin/python3 tools/docs_check.py",0,"193 files; 8 exempt; 59 warnings"
  "/usr/bin/python3 tools/manifest_check.py",0,"0 manifest findings; 0 policy findings; 780 scanned; 63 non-UTF-8 skipped"
```

The three requested pins match. Rendering keeps secrets as variable references, separates the ES bootstrap credential from the application credential, gives clients only the public CA mount, publishes no ES8 host port, and retains loopback publication and non-root settings. ES8 HTTP TLS and authentication are enabled, scripts disabled, and setup completion gates initialization and application startup. The setup script verifies its CA and exits on failed API requests. Ember's pinned upstream Dockerfile was read through `gh`: it builds the production bundle from source and serves it with nginx as UID 101; the installer no longer overrides its entrypoint or uses the prebuilt fallback. ES2, mongo and sharejs are absent from the active manifest; lifecycle `up --remove-orphans` removes their obsolete containers without deleting their data.

`init --missing` has behavioral tests preserving existing values and custom ports, adding the new keys, dropping the retired key, keeping mode 0600, redacting output, and producing identical bytes on the second run. C6 performs the real second-factor step and checks institution isolation; C7 checks bidirectional editor convergence, anonymous socket rejection and non-contributor token rejection. ES setup/TLS tests are chiefly rendered-configuration assertions, not executed ES integration tests. No live rotation, TLS handshake, cold installation or migration was repeated in this review. A possible rotation concern was investigated against Elasticsearch 8.19.24's entrypoint and ReservedRealm source: an explicit bootstrap password remains the fallback until an elastic-user password is persisted, so merely adding these keys is not evidence of a rotation defect; no such finding is asserted.

The pinned osf.io task definitions confirm that `search_ensure_index` ensures the mapped index before initial writes and that `migrate_search` invokes the database-backed migration. This supports the intended sequence, not proof of a populated ES2 migration. Migrations 0006 and 0007 exist at the pinned source.

The five committed files in `acc-20261112T223428Z-fda84a` were inspected and scanned for credential-shaped values, identities, private keys, tokens and host scratch paths. No such disclosure was found. JSON, collector, TOON, JUnit and pytest output agree on 14 passes, no failures/errors/skips; external-request block count is 138. Evidence paths are repository-relative; tracing is off. These are committed results, not freshly rerun browser tests.

DEMO-20 v0.20 and status v0.17 preserve historical versions and distinguish the final-pin warm upgrade from the earlier cold run. They explicitly exclude an empty-runtime cold install, real ES2-data reindexing, `images.yml`/per-OS workflow updates, Shibboleth idp admin login and public-access mode; R7-01 remains deferred. The 6,264 open findings and report-only gate are disclosed, not represented as a clean security bill. The complete scan's raw report is not in the committed acceptance folder, so that count remains the documented operator result rather than independently rederived evidence. The wording that all ZAP targets are `ok` must be read with R1-01's skipped-coverage limitation.

---

<a id="japanese"></a>
## 日本語

[→ To English](#english)

### 判定

**Changes requested（要修正）。** 統合前に R1-01 と R1-02 を修正する。指定 head の隔離クローンで実施した。稼働中の Docker 操作、実環境の秘密の参照、リポジトリ編集、commit、push、approve、merge は行っていない。試験は自身の一時ファイルだけを作成した。PR コメントは一件のみ投稿する。

### R1-01 — P2: ZAP の除外を確認済みのサインイン転送に限定する

対象: `installer/grdm_dev/scan.py:1058–1065,1108–1113`、関連試験 `installer/tests/test_scan.py:796–807`。

`zap_behind_sign_in()` は対象の netloc と違う接続失敗先ならすべて受け入れる。転送経路、設定された認証先、サービス、公開アクセス設定を確認しない。`run_zap()` はレポート欠落と非ゼロ終了を捨て、検査を `ok` とする。このため無関係な壊れた転送先や、対象ホストの別表記でも動的検査をすり抜けうる。注記の「必須サインイン」も確認されていない。

既存の模擬試験で、正常な web、ZAP 終了 3、JSON レポートなし、転送先 `unexpected.invalid:9443` の接続拒否を与えると、終了 0、`result: ok`、対象 1、問題 0 を再現した。入力全文と結果は英語部に示した。

予定したサービスと設定済み認証先への転送であることを肯定的に確認すること。不明な宛先、公開アクセス、根拠のないレポート欠落は終了 51 のままにする。正当な認証壁による除外も、検査済み対象に数えず対象外として記録する。不明ホスト、対象の別表記、公開アクセス、正当な認証転送の挙動試験を追加する。現行試験は許可例と対象ホストの完全一致しか確認せず、この欠陥を検出しない。

### R1-02 — P2: ADR-14 の render 前 rotate を修正する

対象: `docs/decisions/ADR-14_Elasticsearch_8_with_TLS_and_Authentication.md:50,92`。

英和とも既存環境に `compose render` より先に `secrets rotate` を要求している。環境ガイド §8、PR 手順、廃止キーがある更新では render が先という SPEC-02 と矛盾する。rotate は全秘密を変更し `SHAREJS_SECRET` を削除したうえで、古い Compose によりコンテナを再作成する。その定義には廃止キーやサービスが残りうる。不要な資格情報変更を伴い、新設定の生成前に失敗・ロールバックする可能性がある。

実装済みの `secrets init --missing`、render/build/render/up、初回だけの `invoke migrate_search` に統一するか、正本であるガイドの手順へリンクする。過去の版を保持し、英和を同時に訂正する。初回検査が未実施という ADR の残存記述も、DEMO-20 の最終固定版の検査完了と整合させる。

### 検査と証拠

隔離クローンでシステムの `/usr/bin/python3` を使用し、終了コードを確認した。installer は 672 件・10 skip・85.924 秒、tools は 93 件、docs_check は 193 ファイル・8 例外・59 警告、manifest_check は manifest/policy とも指摘 0（780 検査、非 UTF-8 の 63 を除外）。四コマンドとも終了 0。正確なコマンドは英語部の一覧に記録した。

指定した三つの固定 SHA は一致する。Compose の秘密は変数参照で、ES の管理者資格情報とアプリ用資格情報は分離され、クライアントは公開 CA のみをマウントする。ES8 のホストポートは公開されず、ほかの公開はループバックと非 root の方針を保持する。HTTP TLS・認証は有効、スクリプトは無効、setup 成功が初期化とアプリ起動の条件になっている。setup は CA を検証し API 失敗で停止する。固定先 Ember Dockerfile を gh で読み、ソースからの本番ビルド、nginx の UID 101 配信を確認した。installer は entrypoint を上書きせず事前ビルド代替も使わない。ES2・mongo・sharejs は有効な manifest に存在せず、up の `--remove-orphans` は旧コンテナを除去するがデータを削除しない。

`init --missing` の試験は既存値と独自ポートの保持、新キー追加、廃止キー除去、0600、出力秘匿、二回目のバイト一致を実行している。C6 は実際の第二要素入力と所属機関の分離、C7 は双方向の文字伝播、匿名ソケット拒否、非共同研究者のトークン拒否を検証する。ES setup/TLS の試験は主に生成設定の確認で、実 ES の統合試験ではない。今回、実際の rotate・TLS 接続・コールド導入・移行は再実行していない。rotate の懸念は ES 8.19.24 の entrypoint と ReservedRealm ソースで確認した。明示した bootstrap password は elastic 利用者のパスワードが永続化されるまで既定の認証として使われるため、新キー追加だけを根拠とする rotate 不具合は指摘しない。

固定先 osf.io のタスクは初回書き込み前の `search_ensure_index` と、DB に基づく `migrate_search` を備える。予定する順序の裏付けであり、実データを持つ ES2 移行の実証ではない。0006・0007 の migration ファイルも固定先に存在する。

`acc-20261112T223428Z-fda84a` の五ファイルを読み、秘密らしい値、識別情報、秘密鍵、トークン、ホストの作業パスを検査した。該当する漏えいは見つからなかった。JSON・collector・TOON・JUnit・pytest は 14 成功、失敗・error・skip 0 で一致し、外部要求の遮断数は 138。証拠パスはリポジトリ相対、trace は無効である。これはコミット済み証拠の確認で、ブラウザ試験の再実行ではない。

DEMO-20 v0.20 と状況ボード v0.17 は旧版を保持し、最終固定版の既存環境更新と過去のコールド実行を区別する。空 runtime からの最終版導入、実 ES2 データの索引再構築、images.yml/per-OS ワークフロー変更、Shibboleth idp 管理者ログイン、公開アクセスは未実証と明示し、R7-01 も保留である。未解決 6,264 件と report-only は開示され、安全性が完全と主張していない。ただし完全な scan の生レポートは受入フォルダに含まれず、件数は今回独立再集計した値ではなく作業者の記録である。ZAP 全対象が ok という表現には R1-01 の除外範囲の限界がある。
