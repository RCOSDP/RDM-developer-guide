# REV PR56 Installer final pins review r2 / インストーラー最終固定版レビュー r2

> **Summary:** Changes requested: the original false-success reproduction is fixed, but a malformed redirect Location escapes as an exception instead of scanner-unavailable exit 51. R1-02 is closed; all four requested check suites pass.
> **概要:** 要修正。元の誤成功の再現は解消したが、不正な Location が未処理例外となり、スキャナー未完の終了 51 にならない。R1-02 は解消し、指定の四検査は通過した。

**Jump:** [English](#english) · [日本語](#japanese)

- Version / 版: 0.2 — 2026-11-13. **Learned:** REV changed only link destinations for publication: scratch-path links were replaced by repository-relative links or plain-text references. ／ REV は公開のためリンク先のみを変更し、作業用パスへのリンクをリポジトリ相対リンクまたは平文の参照に置き換えた。
- Provenance / 出典: Original file / 原本: `/private/tmp/claude-501/-Users-komiyama-ai-development-GitHub-RDM-developer-guide/8baac84b-080f-4104-a2b5-7416702c57e1/scratchpad/reviews/2026-11-13_RDM-developer-guide_PR56_Installer_Final_Pins_r2.md`. All other original text is retained verbatim below, including the original version and review-time context. ／ 以下は元の版とレビュー時点の文脈を含め、それ以外の原文をそのまま保持する。
- Version / 版: 0.1 — 2026-11-13. **Learned:** a non-following HTTP probe can successfully return an invalid Location; validating its output must itself fail closed without interrupting the scanner report. ／ 転送を追わない HTTP の探りは不正な Location も正常に返しうるため、その出力の検証自体も報告の生成を中断せず安全に失敗する必要がある。
- Applies to: RCOSDP/RDM-developer-guide PR #56, `eae88bdd9b61550920d975146d3275ba6aca43bc..cb93d48a855dbb894575c1efa815b65668dbaecc`; REV round 2.
- Related: [PR #56](https://github.com/RCOSDP/RDM-developer-guide/pull/56) · [review index](../reviews/README.md) · [SPEC-06](../spec/06_documentation_conventions.md) · [r1](2026-11-13_RDM-developer-guide_PR56_Installer_Final_Pins_r1.md).
- Reviewer: REV（担当レビュワ, Codex Astra）.

---

<a id="english"></a>
## English

[→ 日本語版へ](#japanese)

### Verdict and remaining finding

**Changes requested.** R1-01's original arbitrary-host bypass is fixed, but its requirement that other failures remain exit 51 is not fully met. R1-02 is closed. No other blocking finding was identified in the seven-file delta.

**R2-01 — P2: reject malformed redirect URLs without escaping the scan.** Location: `installer/grdm_dev/scan.py:1103` (also URL parsing at 1076 and 1097). After the expected ZAP message and mandatory-sign-in configuration pass, the probe can return exit 0 and `302 http://[broken`. `urlsplit()` raises `ValueError: Invalid IPv6 URL`. Neither `run_zap`, `scan.run`, nor the CLI catches that error, so the process exits 1 with a traceback before writing the normal scan report, instead of recording an incomplete ZAP result and returning 51. This remains a nonzero failure, not a false successful scan; the defect is the promised failure classification and loss of the report.

Reproduced using `ScannerRobustnessTests`: `setUp()`, `write_osf_env()`, then `zap_web(probe=(0, '302 http://[broken\n'))`, with cleanup in `finally`. The standalone reproduction process exited 1. This is not just an impossible mocked stdout: a temporary loopback HTTP server returned that Location, and the exact `ZAP_REDIRECT_PROBE` source executed with `/usr/bin/python3 -c` returned exit 0 and that line. An ordinary sign-in Location returned exit 0 and produced the expected skipped result. Two invocations generated exactly two server requests, confirming that redirects were not followed. A closed-port probe exited 1; existing tests confirm a nonzero probe result becomes scan exit 51.

Catch URL-validation errors at the exception boundary and treat them as no verified sign-in evidence, allowing the existing missing-report path to return 51. Add a behavioral regression asserting exit 51, an incomplete result, and no `skipped_targets` for malformed Location; cover malformed addresses in the ZAP message and configured destination as well. The new configuration reads should also degrade to no exemption when their evidence cannot be read or decoded, rather than interrupting report generation.

### What is verified

The exception is restricted to `web`. It requires rendered `ENABLE_PUBLIC_ACCESS=false`, no conflicting `GRDM_ENABLE_PUBLIC_ACCESS`, the matching seed, the configured CAS host and explicit port (case-normalized, with no default-port or localhost guessing), and a separate probe showing an accepted redirect status and that same destination. Unknown hosts, changed ports, different seeds, public access, absent configuration, wrong services, missing/failed probes, relative Locations and ordinary wrong destinations retain 51 in the passing tests. The exact r1 `unexpected.invalid:9443` reproduction now returns 51. A fixture with the Shibboleth SP destination `127.0.0.1:8082` (its template default), distinct from CAS, also returns 51. This verifies the destination rejection, not a live Shibboleth login.

Verified exclusions appear in `skipped_targets`, are removed from `targets`, and produce `ok (0 scanned, 1 skipped behind sign-in: http://web:5000)` plus the explicit `ZAP NOT RUN` note. The probe argv invokes `python3 -c` inside the ZAP image on the scan network; it uses `HTTPConnection`, a 20-second socket timeout, one GET to `/`, and no redirect follower. Current seeds are fixed HTTP root URLs, so the hardcoded path and HTTP connection match them. Docker execution, image availability, and the probe inside that image were not tested; Docker/Python execution failure is represented by a nonzero runner return and is rejected. The malformed-Location parsing failure is the remaining exception to this handling.

ADR-14 0.2 now prescribes `secrets init --missing`, render/build/render/up and a once-only `invoke migrate_search`, linked to the canonical guide, in both languages. Its obsolete first-scan-pending statement is corrected without implying that the allow-list has been reviewed. SPEC-02 0.32, SPEC-03 0.17, environment guide 1.10 and DEMO-20 0.21 have corresponding English/Japanese updates. A script confirmed that all previous Learned/version entries remain. DEMO-20 explicitly corrects the earlier “ZAP (3) all ok” wording: the raw final scan is uncommitted, coverage/counts are operator records or inference, web was not proven scanned, and the stricter code has not run on the Mac Studio stack. That limitation is honest.

### Checks and boundaries

Clean detached clone: `/private/tmp/rev-pr56-r2-clone`; GitHub head was checked with `gh pr view`. Commands ran from that clone; process exits were checked individually:

```toon
checks[4]{command,exit,result}:
  "PYTHONPATH=installer /usr/bin/python3 -m unittest discover -s installer/tests",0,"677 tests; 10 skipped; 88.044 seconds"
  "/usr/bin/python3 -m unittest discover -s tools/tests",0,"93 tests; 5.595 seconds"
  "/usr/bin/python3 tools/docs_check.py",0,"193 files; 8 exempt; 58 warnings"
  "/usr/bin/python3 tools/manifest_check.py",0,"0 manifest findings; 0 policy findings; 780 scanned; 63 non-UTF-8 skipped"
```

The targeted probe script and version-preservation checks exited 0; the deliberately uncaught malformed-Location reproduction exited 1. Logs/scripts are `/private/tmp/rev-pr56-r2-{installer,tools,docs,manifest,probe}.log`, `/private/tmp/rev-pr56-r2-probe.py`, `/private/tmp/rev-pr56-r2-malformed.py`, and `/private/tmp/rev-pr56-r2-versions.py`. The clone has no tracked changes. No live Docker command, live `runtime/.env` access, commit, push, approval, merge, close or prune was performed. Temporary fixtures contain synthetic values only. One concise Japanese PR comment accompanies this report. Remaining work: fix R2-01 and rerun its regression; a real Docker probe/stack scan remains explicitly unverified.

---

<a id="japanese"></a>
## 日本語

[→ To English](#english)

### 判定と残件

**Changes requested（要修正）。** R1-01 の任意ホストによる誤成功は解消したが、それ以外の失敗を終了 51 にする要件が残る。R1-02 は解消した。七ファイルの差分に、ほかの統合を止める指摘はない。

**R2-01 — P2: 不正な転送 URL を検査全体の例外にせず拒否する。** 対象は `installer/grdm_dev/scan.py:1103`（1076、1097 の URL 解析も関連する）。想定した ZAP メッセージと必須サインイン設定が成立しても、探りが終了 0 と `302 http://[broken` を返すと `urlsplit()` が `ValueError: Invalid IPv6 URL` を送出する。`run_zap`、`scan.run`、CLI のいずれも捕捉しないため、未完の ZAP 結果と終了 51 を出す代わりに、通常の報告を書かず traceback と終了 1 で終わる。誤成功ではなく非ゼロの失敗ではあるが、約束した失敗分類と報告の生成が失われる。

既存の `ScannerRobustnessTests` で `setUp()`、`write_osf_env()`、`zap_web(probe=(0, '302 http://[broken\n'))` を実行し、`finally` で片付ける単独スクリプトが終了 1 になった。模擬出力だけの話ではない。一時的なループバック HTTP サーバーからその Location を返し、実装そのままの `ZAP_REDIRECT_PROBE` を `/usr/bin/python3 -c` で動かすと、終了 0 と該当行が返る。正常なサインイン Location では正しく対象外になる。二回の実行でサーバーへの要求は二回だけで、転送を追わないことを確認した。閉じたポートへの探りは終了 1。探りの非ゼロが検査の終了 51 になることは既存試験が確認している。

URL 検証の例外を除外判定の境界で捕捉し、認証転送の証拠なしとして既存の報告欠落経路から終了 51 にすること。不正な Location に対して終了 51、未完の結果、`skipped_targets` なしを確認する回帰試験を追加する。ZAP メッセージと設定先の不正なアドレスも対象にする。新しい設定読取りについても、読取り・文字デコードができない証拠は除外を認めず、報告の生成を中断しない形にする。

### 確認できた点

除外は `web` に限定され、生成済みの `ENABLE_PUBLIC_ACCESS=false`、矛盾する `GRDM_ENABLE_PUBLIC_ACCESS` がないこと、対象の種 URL、設定済み CAS のホストと明示ポート、そして独立した探りの対応する転送先を要求する。大文字小文字は正規化するが、既定ポートや localhost の同一視はしない。未知ホスト、別ポート、別の種、公開アクセス、設定欠落、別サービス、探りの欠落・失敗、相対 Location、通常の別転送先は、通過した試験で終了 51 を保つ。r1 の `unexpected.invalid:9443` は実際に 51 になった。CAS と異なる Shibboleth SP の宛先 `127.0.0.1:8082`（テンプレートの既定値）の模擬例も 51 になった。これは宛先拒否の確認であり、実 Shibboleth ログインの検証ではない。

正当な対象外は `skipped_targets` に載り、`targets` から外れ、`ok (0 scanned, 1 skipped behind sign-in: http://web:5000)` と明示的な `ZAP NOT RUN` 注を出す。探りの引数は検査ネットワーク上の ZAP イメージ内で `python3 -c` を実行する形である。`HTTPConnection`、20 秒のソケット timeout、`/` への GET 一回で、転送を追わない。現在の種 URL は HTTP のルートに固定されるため、パスと接続方式は一致する。Docker 実行、イメージの有無、そのイメージ内の探りは試していない。Docker/Python の実行失敗は runner の非ゼロで拒否されるが、不正な Location の解析だけは残件のとおり例外になる。

ADR-14 0.2 は英和とも `secrets init --missing`、render/build/render/up、一度だけの `invoke migrate_search` に訂正され、正本のガイドへリンクする。最初の検査が未了という記述も、許容リストの見直し済みと誤解させず訂正された。SPEC-02 0.32、SPEC-03 0.17、環境ガイド 1.10、DEMO-20 0.21 も英和対応で更新され、過去の Learned/版の行すべてが残ることをスクリプトで確認した。DEMO-20 は以前の「ZAP（3）はすべて ok」を明示的に訂正する。最終検査の生データは未コミットで、網羅と件数は作業者の記録または推定であり、web の検査は証明されず、厳格化した処理は Mac Studio で未実行と開示する。限界の記述は正直である。

### 検査と範囲

`/private/tmp/rev-pr56-r2-clone` の隔離した detached clone を使い、`gh pr view` で GitHub の head を確認した。正確なコマンドは英語部の一覧に記録した。installer は 677 件・10 skip・88.044 秒、tools は 93 件・5.595 秒、docs_check は 193 ファイル・8 例外・58 警告、manifest_check は manifest/policy とも指摘 0（780 検査、非 UTF-8 の 63 を除外）。四コマンドは終了コードを個別に確認し、すべて 0 だった。

追加の探り・版保持の確認スクリプトは終了 0、意図して例外を捕捉しない不正 Location 再現は終了 1。ログとスクリプトのパスは英語部に記録した。clone に追跡ファイルの変更はない。実 Docker 操作、実環境の `runtime/.env` 参照、commit、push、approve、merge、close、prune は行っていない。一時試験の値は合成データだけである。日本語の PR コメントは一件のみとする。残件は R2-01 の修正と回帰試験。実 Docker の探りとスタック検査は引き続き未検証である。
