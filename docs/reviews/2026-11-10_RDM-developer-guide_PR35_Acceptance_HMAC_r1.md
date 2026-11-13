# Review r1: Acceptance and HMAC / 受入試験と HMAC のレビュー

> **Summary:** The HMAC wiring is consistent, but public credential evidence and two fail-closed gaps require changes.
> **概要:** HMAC の配線は整合しているが、公開証跡の資格情報と、安全側に停止する検証の二つの穴について修正が必要。

**Jump:** [English](#english) · [日本語](#japanese)

- Version / 版: 0.1 — 2026-11-10. **Learned:** passing acceptance cases does not prove that evidence is safe to publish or that exception matching fails closed. ／ 受入ケースの合格だけでは、証跡の公開安全性や例外判定が安全側に停止することは証明できない。
- Applies to: RCOSDP/RDM-developer-guide PR #35, `fix/accept-chromium-paths` → `develop`, three commits, head `4f70cfa6acf3d837e7f33a0ebb4b9369718fe4d4`.
- Reviewer / レビュワ: REV（担当レビュワ, Codex Astra）.
- Related: [Review index](README.md) · [SPEC-06](../spec/06_documentation_conventions.md) · [SPEC-03 §3.1](../spec/03_security_gate.md#english) · [SPEC-04 §3 rule 4](../spec/04_acceptance_tests.md#english).
- Used by / 利用先: [DEMO-20](../demo/20_core_install_mac_studio.md) · [Status board](../status/README.md) · [Run records](../demo/runs/README.md).

---

<a id="english"></a>
## English

[→ 日本語版へ](#japanese)

### Verdict and findings

**Changes requested.** P1 means fix before merge because the public evidence violates the secrets baseline; P2 means a correctness gap requiring correction. No approval or merge was performed.

**R1-01 [P1] — Mask disposable credentials before publishing evidence.** In `docs/demo/runs/acc-20261109T131240Z-00dff9/pytest.log:166–167,237,369` and `junit.xml:130–131,198,321`, assertion output includes user dictionaries with plaintext password values. No values are reproduced here. `installer/grdm_dev/accept.py:585,621,657–658` constructs the masking set from the environment file, but never adds the generated users or their derived OSF passwords. These are authentication material even if the accounts are intended to be disposable; cleanup can fail and is only a warning. The new `osf_account_password()` derives the OSF password from the published identity, so masking only the password dictionary key is insufficient. SPEC-03 §3.1 forbids secrets in reports/logs, and runs README 0.3 promises none are written. Sanitize the committed text artifacts, include both fakecas identities/credentials and derived OSF passwords in masking before any seed error or report is emitted, and add a failure-output regression covering pytest, JUnit and collector artifacts. Prefer independent random OSF passwords. Verify exposed accounts have been deleted; handle already-published copies according to repository policy. Do not describe disposable passwords as exempt secrets.

**R1-02 [P2] — Constrain external-asset prefixes to actual asset routes.** `installer/acceptance/netguard.py:31–35,80–82` uses unrestricted `startswith`; consequently a stylesheet request to `https://fonts.googleapis.com/css-unlisted` is treated as known, aborted and counted without failing. `/css2` is also silently covered although only `/css` is named. The directory prefixes for CDN libraries likewise accept arbitrary filenames/versions. Host, type, credentials, port and scheme checks are sound, and requests remain blocked: this is a false acceptance verdict, not demonstrated network egress. SPEC-04 explicitly permits prefixes, but its claim that unlisted requests fail is broader than this matching proves. Define exact stylesheet endpoints and bounded directory/file patterns for the known assets, document the intended scope, and test prefix lookalikes and unknown paths. Keep API requests and navigation/WebSocket requests failing.

**R1-03 [P2] — Validate the decoded GA configuration instead of a raw substring.** `installer/grdm_dev/templates/ember_osf_web.json:7` does not require its HTML replacement to match. Missing/reordered attributes or changed quoting can therefore produce a successful no-op. The subsequent raw `grep GoogleAnalytics` is not a semantic verification of the URI-encoded JSON: an adapter name encoded as `%47oogleAnalytics` decodes to `GoogleAnalytics` but is invisible to that grep. With a changed valid meta-tag layout, both checks can pass while the adapter remains. In addition, cached builds bypass the check entirely. Parse and require exactly one expected configuration tag, validate `metricsAdapters`, remove the adapter, then decode and assert its absence before every serve (including cache hits). Add executable tests for the normal case, missing/no-match tag, alternative encoding and cached output. Current tests only inspect command substrings and cannot establish fail-closed behavior. This is source-level analysis, not a claim that the pinned image currently emits the alternative layout.

### Requested cross-checks

**HMAC:** Checked the pinned integration source with GitHub read-only APIs: WaterButler `core/utils.py` uses server settings; `core/provider.py:891–898` uses `providers/osfstorage/settings.py`; osf.io `framework/auth/signing.py:84` uses website `DEFAULT_HMAC_SECRET`. Both signer environment keys in `wb` and `wb_worker` now resolve to `WATERBUTLER_HMAC_SECRET`. Every template mounting the generated website `local.py` (`web`, `api`, `admin`, `worker`, `osf_init`) receives that key. No missing consumer was found. Removing the JWT fallback is correct: `compose.run` rejects a missing required HMAC key before rendering, and the previous secret generator already generated it.

For an existing environment containing both old keys, re-rendering selects the existing WaterButler key consistently; the old OSF storage key is unused. Rotation creates a new shared HMAC key and recreates services using the rendered configuration. **Maintenance note [P3]:** removal from `SECRET_KEYS` makes `run_init --force` and `run_rotate` preserve `OSFSTORAGE_HMAC_SECRET` as a non-secret setting (`secrets.py:300`); it is neither removed nor rotated. Remove obsolete credential keys explicitly and cover legacy environments in tests. This is stale-secret retention, not an active signing mismatch after re-render. Rotation does not re-render an old Compose file, so upgrade guidance should explicitly require re-rendering before recreation/rotation. No real environment file was read.

**Other changes:** `have_email=True` addresses the email-setup redirect. Fakecas's hidden password field is no longer blindly filled. The Chromium additions cover the stated new macOS application and headless-shell layouts without changing executable checks; they do not prove the installed Playwright revision is compatible. In-place writes preserve bind-mounted inodes; unchanged files remain untouched and new files retain atomic creation. Changed files are now non-atomic during writing, so concurrent readers can observe partial content; document/restrict rendering during active imports or add protection if concurrent rendering is supported. No demonstrated regression in the stated sequential workflow was found.

**Rejection cases:** C1 still requires a redirect to login and an anonymous API 401. `follow_redirects=False` returns the first redirect only after checking its Location is loopback. C3's anonymous 401/403 and authenticated non-contributor 403 remain unchanged. The fixture-cycle repair attaches guards through `new_context`, including default contexts, and keeps service workers blocked. No authorization rejection assertion was relaxed. R1-02 is the newly weakened network rejection boundary. New tests do not exercise the GA transform, inode retention, legacy-key migration or all new browser layouts behaviorally.

**Documentation:** DEMO-20 0.12 and status board 0.9 correctly distinguish C1/C3 success/rejection passes from the pre-fix core run (3 passed, 8 failed, 1 error out of 12), and leave C2/C4/C5/C6 open. These are supplied run records, not an independent live rerun. The HMAC explanation matches the wiring. GA removal is correct for the expected build shape but its unconditional guarantee needs R1-03. Runs README 0.3 accurately limits committed runs to the three cited runs, but its no-secrets promise is contradicted by R1-01. Acceptance seed comments still say the browser types an email as password, while the new helper normally skips the hidden password field; update that explanation.

### Validation and limits

In the specified checkout, ran `PYTHONPATH=installer python3 -m unittest discover -s installer/tests`: 363 tests, OK, 10 skipped (acceptance conftest unavailable to this interpreter). `python3 tools/docs_check.py`: pass, 22 glossary warnings. `python3 tools/manifest_check.py`: pass, zero findings. `git diff --check`: clean. The untracked review record is checked separately because the normal docs checker enumerates tracked files. No installation, acceptance execution, Docker state changes, runtime secret inspection, commit, push, approval or merge. Only this review record and the requested single PR comment are deliverables. Remaining work: fixes and focused regression evidence for R1-01–03, followed by re-review; C2/C4/C5/C6 remain separate acceptance work.

---

<a id="japanese"></a>
## 日本語

[→ To English](#english)

### 判定と指摘

**Changes requested（要修正）。** P1 は公開証跡が秘密の基本対策に反するためマージ前の修正が必要な問題、P2 は修正が必要な正しさの問題。承認やマージは行っていない。

**R1-01 [P1] — 使い捨て資格情報も公開前にマスクする。** `docs/demo/runs/acc-20261109T131240Z-00dff9/pytest.log:166–167,237,369` と `junit.xml:130–131,198,321` の assertion 出力に、平文パスワードを含むユーザー辞書がある。値はここに転載しない。`installer/grdm_dev/accept.py:585,621,657–658` は環境ファイルからマスク対象を作るが、生成した試験ユーザーや派生した OSF パスワードを追加しない。使い捨て予定でも認証情報であり、削除失敗は警告だけである。追加された `osf_account_password()` は公開された識別子からパスワードを導出するため、辞書の password 欄だけを消しても足りない。SPEC-03 §3.1 はログ・報告の秘密を禁じ、runs README 0.3 も秘密を書かないと約束している。コミット済みの文字証跡をマスクし、seed エラーや報告を出す前に fakecas の識別子・資格情報と OSF パスワードをマスク対象へ追加すること。pytest・JUnit・collector の失敗出力を回帰検証すること。OSF パスワードは独立した乱数が望ましい。露出したアカウントの削除を確認し、公開済みコピーはリポジトリ方針に従って処理すること。使い捨てを秘密の例外にしない。

**R1-02 [P2] — 外部資産の一致範囲を実際の資産ルートに絞る。** `installer/acceptance/netguard.py:31–35,80–82` の無制限な `startswith` により、stylesheet の `https://fonts.googleapis.com/css-unlisted` が既知として中断・集計され、試験を失敗にしない。明記された `/css` 以外の `/css2` も暗黙に含む。CDN ライブラリのディレクトリも任意のファイル名・版に一致する。ホスト・種類・資格情報・ポート・scheme の確認は適切で、通信は遮断される。これは合否の偽陰性であり、外部流出を観測した指摘ではない。SPEC-04 は prefix を許すが、「一覧外は失敗する」という説明は現判定で保証できる範囲より広い。stylesheet は正確な endpoint、その他は境界のあるディレクトリ・ファイル条件を定め、意図した範囲を文書化し、似た prefix と未知パスをテストすること。API・画面遷移・WebSocket の拒否を維持すること。

**R1-03 [P2] — GA 設定は復号して検証する。** `installer/grdm_dev/templates/ember_osf_web.json:7` は HTML 置換の一致を必須にしていない。属性順・引用符の変更やタグ欠落で、何もしなくても成功する。後続の生文字列に対する `grep GoogleAnalytics` は URI 符号化された JSON の意味を検証しない。たとえば `%47oogleAnalytics` は復号後に `GoogleAnalytics` になるが grep には見えず、有効な meta タグの形式変更と組み合わさると両検査を通って adapter が残る。キャッシュ済みビルドでは検査全体を飛ばす。期待する設定タグが正確に一つあることと `metricsAdapters` の形を確認し、除去後も復号して不在を検証すること。キャッシュ時も含め、serve 前に必ず検証すること。正常形、タグ欠落・不一致、別の符号化、キャッシュ成果物の実行テストが必要。現テストはコマンド内の文字列確認だけで、安全側に停止する証明にならない。これはソース上の分析であり、固定イメージが現在その別形式を生成するという主張ではない。

### 指定された確認事項

**HMAC：** GitHub の読み取り API で固定された統合ソースを確認した。WaterButler の `core/utils.py` は server settings、`core/provider.py:891–898` は `providers/osfstorage/settings.py`、osf.io の `framework/auth/signing.py:84` は website の `DEFAULT_HMAC_SECRET` を使う。`wb`・`wb_worker` の両署名器の環境キーは `WATERBUTLER_HMAC_SECRET` に統一されている。生成した website `local.py` を mount する全サービス（`web`・`api`・`admin`・`worker`・`osf_init`）にも渡され、漏れはなかった。JWT fallback の削除は適切。HMAC キーが欠ければ compose render が拒否し、旧生成処理も同キーを生成していた。

旧キー二つを持つ環境でも、再 render 後は既存の WaterButler キーで揃い、旧 OSF storage キーは未使用になる。rotate は新しい共通鍵を生成し、render 済み設定でサービスを再作成する。**保守指摘 [P3]：** `SECRET_KEYS` からの削除で `run_init --force`・`run_rotate` は `OSFSTORAGE_HMAC_SECRET` を非秘密設定として残す（`secrets.py:300`）。削除も更新もしない。廃止した資格情報キーを明示的に消し、旧環境のテストを加えること。これは不要な秘密の残留であり、再 render 後の署名不一致ではない。rotate 自体は古い Compose を再 render しないので、更新手順には再作成・rotate 前の再 render を明記するとよい。実際の環境ファイルは読んでいない。

**その他：** `have_email=True` はメール設定への転送を解消する。fakecas の不可視パスワード欄を無条件に fill しなくなった。Chromium の追加パスは示された新しい macOS アプリと headless shell を対象にし、実行可能性の確認は維持するが、導入済み Playwright の版との互換性までは証明しない。既存ファイルへの上書きは mount の inode を保持し、同一内容は書かず、新規作成は原子的なまま。変更時の書込みは非原子的になり、同時に読む処理が途中の内容を見得る。並行 render を扱うなら、import 中の render 制限を文書化するか保護を設けること。指定された逐次の流れでの具体的な回帰は見つからなかった。

**拒否ケース：** C1 のログインへの redirect と匿名 API 401 は維持される。`follow_redirects=False` でも Location が loopback であることを確認してから最初の応答を返す。C3 の匿名 401/403 と認証済み非共同研究者 403 は変更されていない。fixture 循環の修正後も、既定 context を含め `new_context` で guard が付き、service worker を遮断する。権限拒否 assertion の緩和はない。ネットワーク拒否の新しい緩和は R1-02。追加テストは GA 変換・inode 保持・旧鍵移行・新ブラウザ配置全体の動作を検証していない。

**文書：** DEMO-20 0.12 と進捗表 0.9 は C1/C3 の成功・拒否合格と、修正前のコア実行（12 件中 3 passed・8 failed・1 error）を正しく区別し、C2/C4/C5/C6 を残件にしている。これは提供された実行記録で、独立した実機再試験ではない。HMAC の説明は配線に一致する。GA 除去は想定形式では正しいが、無条件の保証には R1-03 の修正が必要。runs README 0.3 の「引用した三実行のみを保持」は合っているが、「秘密を書かない」は R1-01 と矛盾する。seed のコメントはまだメールをパスワードとしてブラウザが入力すると述べるが、新 helper は通常不可視欄を飛ばすので説明を合わせること。

### 検証と限界

指定 checkout で `PYTHONPATH=installer python3 -m unittest discover -s installer/tests` を実行：363 件、OK、10 skip（この Python では acceptance conftest を import できない）。`python3 tools/docs_check.py` は合格、用語注の警告 22 件。`python3 tools/manifest_check.py` は合格、検出ゼロ。`git diff --check` は問題なし。通常の文書検査は追跡ファイルだけを列挙するため、未追跡のレビュー記録は別に検証する。install・accept・Docker 状態変更・runtime の秘密参照・commit・push・承認・マージは行っていない。成果物はこの記録と依頼された PR コメント一件だけ。残件は R1-01〜03 の修正と絞った回帰検証、その後の再レビュー。C2/C4/C5/C6 は別途残る受入作業である。

---

## Glossary / 用語

| Term | English note | 日本語注 |
|---|---|---|
| HMAC | A shared-key signature used to check who sent a message. | 共通の秘密鍵で送信元を確かめる署名。 |
| Fail closed | Stop when safety cannot be established. | 安全を確認できないときに停止すること。 |
| Inode | The file identity a mounted file continues to refer to. | mount が参照し続けるファイルの実体の識別情報。 |
| Masking | Replace sensitive values before saving or displaying them. | 保存・表示の前に秘密の値を伏せること。 |
| GA | Google Analytics, a browser analytics adapter. | ブラウザの利用状況を送る Google Analytics の部品。 |
