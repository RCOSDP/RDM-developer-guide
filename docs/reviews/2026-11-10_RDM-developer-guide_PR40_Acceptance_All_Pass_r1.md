# PR40 Acceptance review r1 / 受入全件合格のレビュー r1

> **Summary:** Changes requested: C6 does not establish cross-institution isolation, and two operational records need correction. The recorded twelve passes and unchanged rejection statuses are consistent with the submitted evidence.
> **概要:** 要修正。C6 は機関間の分離を証明できず、運用記録にも二点の修正が必要。記録された十二件の合格と変更されていない拒否ステータスは提出証跡と一致する。

**Jump:** [English](#english) · [日本語](#japanese)

- Version / 版: 0.1 — 2026-11-10. **Learned:** excluding an unaffiliated account does not prove that an institution administrator cannot see another institution's members. ／ 無所属のアカウントを除外できても、機関管理者が他機関の利用者を見られないことは証明できない。
- Applies to: RCOSDP/RDM-developer-guide PR #40, head `2998b5293f983c3d3d8521b928394013689413e6`, branch `fix/accept-c2-c6`; REV（担当レビュワ, Codex Astra）.
- Related: [Review index](README.md) · [SPEC-02](../spec/02_installer_cli.md) · [SPEC-03](../spec/03_security_gate.md) · [SPEC-04](../spec/04_acceptance_tests.md) · [SPEC-06](../spec/06_documentation_conventions.md) · [ADR-04](../decisions/ADR-04_AI_Autonomy_and_Roles.md).
- Used by: [DEMO-20](../demo/20_core_install_mac_studio.md) · [Status board](../status/README.md).

---

<a id="english"></a>
## English

[→ 日本語版へ](#japanese)

### Verdict and findings

**Changes requested.** Review performed in an independent clean clone under `/tmp/pr40-rev-ngfGaK/repo`. No application fix, commit, push, merge, approval, closure, live-stack mutation, or live credential-file access was performed. One PR comment accompanies this uncommitted record.

**R1-01 (P2): C6 does not prove institution isolation.** `installer/acceptance/test_c6_admin.py:20–30` checks that one member of the administrator's institution is present and that unaffiliated `user_a` is absent. The seed in `installer/grdm_dev/accept.py:252–259` creates no member of a different institution. A broken listing that returns every affiliated user would pass both assertions. I executed the actual success function extracted through Python AST with a fake page containing the expected member plus an unrelated institution member: it passed. This is an assertion counterexample, not a claim that the live application leaks users. Seed a second, distinct institution and a member belonging only to it; prove the administrator is affiliated only with the first; assert the second member is absent from the relevant complete or explicitly searched listing. Preserve the current positive and unaffiliated checks and exact API rejection status. Repeat C6 and the core run before claiming that the administrator sees “only” its institution's users in DEMO-20.

**R1-02 (P2): document the development-only static-file exception.** `installer/grdm_dev/templates/admin.json:5–11` now uses `manage.py runserver ... --insecure`. Generated host publication is constrained to `127.0.0.1` by `compose.py:587`, and this is a development installer, so I found no newly exposed host interface. However, SPEC-02 and DEMO-20 do not explain this flag, its need with DEBUG false, or its loopback development restriction. The PR body, a test comment, and a historical review mentioning a needed adjustment do not replace the shipped operating contract. Add matching English/Japanese documentation explaining the static-asset purpose and that this command is not a production deployment mechanism; keep loopback binding enforced.

**R1-03 (P3): reconcile the status board's Wiki item.** `docs/status/README.md:62` and its Japanese counterpart still mark the `edit.mako` wiring/browser verification as open or not started, immediately before the new all-green C1–C6 row. DEMO-20 attributes C4 success to that wiring, and results.json records C4 success. Close or accurately qualify the old item in both languages with the relevant review/run reference so the board has one consistent status.

### Checks of the requested behavior

C1–C6 rejection expectations were not relaxed: the run records 401, 403, 403, 4401, 401 and 403 respectively. C4 waits at most 30 seconds for peer awareness before typing, still gives each newly typed marker only five seconds to propagate, and requires both markers in both independent editors. Removing `.ProseMirror-yjs-cursor` from a cloned DOM removes presence-widget text, not persisted document content or the live editor; it cannot create a missing remote marker. This change does not hide a content-sync failure under the stated scenario.

C5 rejection reads `window.contextVars.file.urls.render`, verifies the MFR origin, and requests that exact embedded URL through the cookie-less guarded API context. It retains the 401/403 requirement. The MFR configuration limits credential-source origins to `http://web:5000` and credential-target origins to `http://wb:7777`; the patch adds no wildcard origin. The web token key maps to the same secret used by y-websocket.

The administrator is seeded as staff and not superuser, with the first non-deleted institution; its OSF password reaches pytest via `GRDM_ACCEPT_ADMIN_OSF_PASSWORD`. `seed_secret_values` includes every seeded OSF password and identity before subprocess output can be reported. Seed failures, cleanup warnings, pytest output, collected results and textual evidence pass through masking. The seed command still carries the password inside the existing shell snippet, but the runner captures its output rather than logging the command. No new credential logging path was found. The evidence directory contains five textual files, no browser traces or screenshots; manual inspection and redacted gitleaks found no credentials. This is a checked finding, not a guarantee against every possible secret format.

The newly published y_websocket and sharejs ports use the common loopback-only renderer and are listed in both SPEC-02 port tables (1234 and 7007). Unit coverage checks remapping and the browser URLs. The admin static flag remains subject to R1-02.

The ADR-04 new row has matching English/Japanese scope. GitHub read APIs report zero workflows for each of the three named repositories; y-websocket PR #2 is merged with an empty check rollup and has local test results in its body, consistent with the stated incident. The owner's private session authorization and the historical merge-check implementation cannot be independently established from this repository or these read APIs; they remain attributed statements, not newly verified authorization.

The canonical [results.json](../demo/runs/acc-20261110T014431Z-2b91e6/results.json), collector, JUnit, pytest log and TOON agree on twelve passing core cases, no failures or skips, and the stated rejection statuses. Results record 96 known external requests blocked, not zero external attempts; this is allowed by the current SPEC-04 exception list. DEMO-20's six component short pins match the manifest, but results.json does not attest running image digests, so the exact deployed image provenance remains author-reported. Live acceptance was not rerun under the no-stack-change instruction. The numeric all-pass claim is supported; its C6 interpretation and the board item need the corrections above.

### Local validation

Commands ran from the scratch clone, using its source and disposable test fixtures. The unit suite's Docker Compose parser check is read-only; no Docker state-changing command was issued.

```sh
PYTHONPATH=installer python3 -m unittest discover -s installer/tests
python3 -m unittest discover -s tools/tests
python3 tools/docs_check.py
python3 tools/manifest_check.py
gitleaks dir docs/demo/runs/acc-20261110T014431Z-2b91e6 --redact --no-banner --report-path /tmp/pr40-rev-ngfGaK/gitleaks.json
```

```toon
validation[5]{check,exit_code,result}:
  installer_unit,0,535 tests; 10 skipped
  tools_unit,0,93 tests
  docs_check,0,138 files before review; 25 warnings; 8 exempt
  manifest_check,0,zero manifest and policy findings
  evidence_gitleaks,0,no leaks found
```

The documentation check after adding this review also exited 0 (138 tracked files; 25 warnings). Because the new report is untracked, it was separately checked with the same checker’s `check_file` function: zero errors. Logs remain in the scratch parent directory. Required follow-up is R1-01–R1-03, refreshed acceptance evidence, and re-review; no merge verdict of pass is granted.

---

<a id="japanese"></a>
## 日本語

[→ To English](#english)

### 判定と指摘

**Changes requested（要修正）。** `/tmp/pr40-rev-ngfGaK/repo` の独立したクリーンクローンで確認した。アプリ修正、commit、push、merge、approve、close、稼働スタックの変更、稼働環境の資格情報ファイル参照はしていない。この未コミット記録と PR コメント一件を提出する。

**R1-01（P2）: C6 は機関間の分離を証明しない。** `installer/acceptance/test_c6_admin.py:20–30` は、自機関の一人が表示され、無所属の `user_a` が表示されないことだけを確認する。`installer/grdm_dev/accept.py:252–259` の種データに他機関だけに所属する利用者はいない。そのため「全機関の所属者を返す」不具合があっても両方の条件を満たす。実際の成功関数を Python AST で抽出し、自機関の利用者と他機関の利用者を含む偽ページで実行すると合格した。これは判定の反例であり、稼働アプリの漏えいを実証したものではない。異なる第二機関とそこだけに所属する利用者を用意し、管理者が第一機関だけに所属することを確認したうえで、一覧全体または明示的な検索で他機関の利用者が表示されないことを確認してほしい。現行の正常表示・無所属の除外・API の厳密な拒否ステータスを維持し、C6 とコア全件を再実行してから DEMO-20 の「自機関の利用者だけ」という主張を確定する。

**R1-02（P2）: 静的ファイル配信の開発専用例外を文書化する。** `installer/grdm_dev/templates/admin.json:5–11` は `manage.py runserver ... --insecure` を使う。`compose.py:587` がホスト公開を `127.0.0.1` に限定し、開発用インストーラーであるため、新たなホスト外向け公開は見つからない。ただし SPEC-02 と DEMO-20 は、このフラグ、DEBUG false で必要な理由、ループバック開発専用という制約を説明していない。PR 本文、試験のコメント、必要な調整に触れた過去のレビューは、配布される運用契約の代わりにはならない。静的資産の配信用であり本番配備用のコマンドではないことを英和で記し、ループバックの強制を維持してほしい。

**R1-03（P3）: 進捗ボードの Wiki 項目を整合させる。** `docs/status/README.md:62` と日本語の対応行は、`edit.mako` の配線とブラウザ確認を未解決・未着手のままとし、直後で C1〜C6 全件合格とする。DEMO-20 はその配線を C4 合格の理由に挙げ、results.json も C4 成功を記録する。両言語の古い項目を解決済み、または実態に合う限定的な残件へ変更し、レビューと実行への参照を付けてほしい。

### 指定された挙動の確認

C1〜C6 の拒否期待値は緩められていない。実行で記録された値は順に 401、403、403、4401、401、403。C4 は入力前に相手の存在通知を最大 30 秒待つが、入力した各マーカーの伝播期限は五秒のままで、独立した双方のエディタに両マーカーを要求する。複製 DOM からの `.ProseMirror-yjs-cursor` 除去は存在通知の文字を除くだけで、保存本文や実エディタを変更せず、欠けた相手のマーカーを作れない。指定シナリオにおける本文同期失敗を隠す変更ではない。

C5 拒否は `window.contextVars.file.urls.render` を読み、MFR の起点を検証し、その埋込 URL 自体を cookie のない保護付き API context で要求する。401/403 の条件は維持する。MFR の資格情報転送元は `http://web:5000`、転送先は `http://wb:7777` だけで、ワイルドカードは加えていない。web のトークン鍵も y-websocket と同じ秘密へ接続する。

管理者は staff かつ非 superuser とし、最初の未削除機関に所属させる。OSF パスワードは `GRDM_ACCEPT_ADMIN_OSF_PASSWORD` 環境変数で pytest へ渡す。`seed_secret_values` はサブプロセス出力が報告される前に全員の OSF パスワードと識別情報を対象にする。種データ作成失敗、後片付けの警告、pytest 出力、集約結果、文字形式の証跡は伏せ字処理を通る。既存の種データ作成コマンドではパスワードを shell snippet 内に含むが、runner は出力を捕捉し、コマンドをログへ出さない。新たな資格情報のログ出力経路は見つからなかった。証跡は文字ファイル五個でトレース・画像はなく、目視と伏せ字付き gitleaks では資格情報を検出しなかった。これは検査結果であり、あらゆる秘密形式への無条件の保証ではない。

新たに公開する y_websocket と sharejs は共通のループバック限定描画を使い、SPEC-02 の英和両方のポート表に 1234 と 7007 がある。単体試験はポート変更とブラウザ URL を確認する。admin の静的配信フラグについては R1-02 が残る。

ADR-04 の追加行は英和で範囲が一致する。GitHub の読取 API では記載された三リポジトリのワークフローはすべてゼロで、y-websocket PR #2 は空の check rollup のままマージ済み、本文にはローカル試験結果があり、記載された事象と一致する。所有者の非公開セッション内の承認と過去のマージ判定実装は、このリポジトリや読取 API から独立に確定できない。記録上の説明として扱い、新たに検証済みの権限とは扱わない。

正本の [results.json](../demo/runs/acc-20261110T014431Z-2b91e6/results.json)、collector、JUnit、pytest log、TOON は、コア十二件合格・失敗とスキップなし・拒否ステータスで一致する。既知の外部要求は 96 件遮断されており、外部要求の試行ゼロではない。現行 SPEC-04 の例外一覧に沿う。DEMO-20 の六構成要素の短縮 SHA は manifest と一致するが、results.json は実行イメージの digest を証明しないため、実際の配備イメージの由来は著者報告の範囲に留まる。スタック変更禁止の指示に従い、実受入は再実行していない。全件合格という数値は裏付けられるが、C6 の解釈とボード項目には修正が必要。

### ローカル検証

クローン内のソースと使い捨て試験データで実行した。単体試験の Docker Compose 構文確認は読取専用で、Docker の状態を変更するコマンドは実行していない。再現コマンドは英語節のコードブロックに示す。

```toon
validation[5]{check,exit_code,result}:
  installer_unit,0,535 件; 10 件スキップ
  tools_unit,0,93 件
  docs_check,0,レビュー追加前 138 ファイル; 警告 25 件; 対象外 8 件
  manifest_check,0,manifest と policy の指摘ゼロ
  evidence_gitleaks,0,秘密の検出なし
```

レビュー追加後の文書検査も終了 0（追跡済み 138 ファイル、警告 25 件）。新規記録は未追跡なので、同じ検査の `check_file` 関数でも別途確認し、エラーはゼロだった。ログは scratch の親ディレクトリに保存した。残件は R1-01〜R1-03、受入証跡の更新、再レビューであり、マージへ進める合格判定は与えない。
