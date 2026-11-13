# Review r2: Acceptance and HMAC / 受入試験と HMAC の再レビュー

> **Summary:** The r1 code findings are resolved; squash merge is acceptable with the explicitly recorded local-credential residual and live-container validation limit.
> **概要:** r1 のコード指摘は解決。ローカル資格情報の残留と実コンテナ未検証を明示したうえで、squash merge を許容する。

**Jump:** [English](#english) · [日本語](#japanese)

- Version / 版: 0.1 — 2026-11-10. **Learned:** sanitizing the current evidence does not revoke credentials already published in history, and executable guard tests do not replace validation in the pinned container. ／ 現在の証跡のマスクは履歴に公開済みの資格情報を失効させず、guard の実行テストも固定コンテナでの検証の代わりにはならない。
- Applies to: RCOSDP/RDM-developer-guide PR #35, `fix/accept-chromium-paths` → `develop`; review delta `4f70cfa..e4ad66e`, head `e4ad66e00e5cfb256a66a2b8e56239347671d6bb`.
- Reviewer / レビュワ: REV（担当レビュワ, Codex Astra）.
- Related: [Review index](README.md) · [r1 record](2026-11-10_RDM-developer-guide_PR35_Acceptance_HMAC_r1.md) · [SPEC-06](../spec/06_documentation_conventions.md) · [SPEC-03](../spec/03_security_gate.md) · [SPEC-04](../spec/04_acceptance_tests.md).
- Used by / 利用先: [DEMO-20](../demo/20_core_install_mac_studio.md) · [Status board](../status/README.md) · [Run records](../demo/runs/README.md).

---

<a id="english"></a>
## English

[→ 日本語版へ](#japanese)

### Verdict

**Merge acceptable for the reviewed head, with the residual and limits recorded below.** No new merge-blocking regression was found. This is a review verdict, not a GitHub approval or merge. The updated PR body corrects its earlier deletion claim: 33 disposable accounts remain in the local database, and their deletion is deferred until the current acceptance work finishes. That statement is acknowledged, not independently verified against the database.

### Resolution of r1

**R1-01 [P1]: code and current evidence resolved; historical exposure accepted as a bounded residual.** `seed_users()` now generates an independent `secrets.token_urlsafe(24)` OSF password for each user. `seed_secret_values()` joins the masking set before any seed call, including identities, fakecas credentials and OSF passwords; raw, lower-case, XML/JSON-escaped and URL-quoted values are covered. Failure tests exercise seed errors, pytest output, JUnit, collector and result artifacts. The two changed historical text artifacts exactly equal the current sanitizer applied to their old contents; no unmasked disposable mailbox was found in the tracked run text. No credential values are reproduced here. The cleanup query now uses `username__icontains`, matching OSF's lower-cased usernames; its test checks the generated query, not deletion against a real database. The seed explanation now matches the login helper.

**R1-02 [P2]: resolved.** Full-path matching replaces unrestricted prefixes: exact `/css` and `/css2`, a three-component numeric version and the named es6-shim/MathJax file, or a 32-character hexadecimal gravatar hash / exact `placeholder`. Versions and query parameters are intentionally not pinned by this rule; it bounds the asset route and does not permit network access. Unknown files, suffixes, prefix lookalikes, wrong resource types, ports and credentials remain rejected. API, navigation and WebSocket requests remain outside the exception. SPEC-04 0.8 describes the scope. A read-only GitHub check of `RDM-osf.io-dev2027` at `389415a473361fdaa3c347e84d95639b9096a9e9`, `addons/wiki/templates/edit.mako:4`, confirms the Material Symbols stylesheet uses `/css2`; making it explicit preserves a real pinned dependency rather than adding an unrelated endpoint.

**R1-03 [P2]: resolved at source and local execution level.** The Node guard requires exactly one matching config tag, parses URI-decoded JSON, validates the adapter list, removes GA and reloads the result to verify absence. Missing/duplicate tags, malformed encoding/config, alternative attribute ordering/quotes, encoded adapter names and cached output have executable coverage. The shell runs the guard after the build conditional and before every serve, with `set -e`; failed verification prevents serving and recording a fresh successful fingerprint. Recipe `3` is part of that fingerprint. An additional temporary-directory shell check changing recipe `2` to `3` observed `build`, then `serve`. This is not a general HTML security parser; the relevant generated-page cases pass, and unsupported representations stop startup. Execution in the real pinned container is still unverified and is not claimed here.

**r1 maintenance [P3]: resolved.** `OBSOLETE_SECRET_KEYS` removes `OSFSTORAGE_HMAC_SECRET` in both `init --force` and successful `rotate`, with a legacy-environment regression test retaining an unrelated port setting. SPEC-02 0.9 explicitly requires `compose render` before rotation or recreation after upgrade. Rollback on failed rotation retains the original environment as designed. No HMAC consumer wiring changed in this delta, so the r1 wiring conclusion stands.

### Historical credentials and remaining work

The plaintext in pushed commit `4f70cfa` remains available in history and copies; force-push is forbidden. Squash merge places the sanitized final tree on `develop`, but does **not** erase the old commit, PR references or existing copies. Nevertheless, accepting that residual for this merge is reasonable on the stated facts: these are disposable credentials valid only on one Mac's loopback-bound development stack, not shared or production credentials; current evidence and future OSF password generation have been corrected; and the PR openly tracks the 33 remaining accounts. This is a contextual risk acceptance, not an exception declaring disposable credentials non-secret or a claim that they have been revoked. Delete and verify removal of the remaining accounts after the active acceptance work, as the PR promises; do not carry those exposed accounts into a shared or externally reachable environment. That operational cleanup remains open and was not performed by this review.

C2/C4/C5/C6 remain separate acceptance work. The new GA guard still needs a real-container check. The r1 note about non-atomic writes during concurrent rendering remains unchanged; this delta does not introduce a new demonstrated regression in the stated sequential workflow.

### Validation and scope

In the specified checkout: `PYTHONPATH=installer python3 -m unittest discover -s installer/tests` passed, 384 tests with 10 skips (acceptance conftest dependencies unavailable to this interpreter); the 15 Node guard/command tests ran rather than skipping. `python3 -m unittest discover -s tools/tests` also passed, 92 tests. `python3 tools/docs_check.py` passed with 101 files checked, 8 exempt and 22 glossary warnings. `python3 tools/manifest_check.py` passed with zero findings. `git diff --check` was clean. The untracked r2 record was checked separately with the docs checker's `check_file` function, because the normal command enumerates tracked files.

Only the uncommitted r2 record and one requested Japanese PR comment were written. No install, acceptance run, Docker state change, real runtime environment-file access, commit, push, approval, close or merge was performed. Tests used temporary fixtures and stub runners; those do not establish real-container behavior or real-account deletion.

---

<a id="japanese"></a>
## 日本語

[→ To English](#english)

### 判定

**下記の残余リスクと検証限界を明記したうえで、対象 head はマージ可。** 新しいマージ阻害回帰は見つからなかった。これはレビュー判定であり、GitHub の approve や merge は行っていない。PR 本文は以前の削除済みという説明を訂正し、使い捨てアカウント33件がローカルDBに残り、進行中の受入作業終了後に削除するとしている。この申告を確認したが、DBへの独立検証はしていない。

### r1 指摘の解決

**R1-01 [P1]：コードと現在の証跡は解決。履歴の露出は限定された残余リスクとして受容。** `seed_users()` は利用者ごとに独立した `secrets.token_urlsafe(24)` の OSF パスワードを生成する。`seed_secret_values()` は seed 呼出し前に識別子・fakecas資格情報・OSFパスワードをマスク対象へ加え、生値・小文字・XML/JSONエスケープ・URL符号化を扱う。失敗テストは seed エラー、pytest、JUnit、collector、結果成果物を検証する。変更された過去の文字証跡2件は、旧内容に現在のマスク処理を適用した結果と完全一致し、追跡中の実行文字証跡に未マスクの試験メールアドレスはなかった。値は転載しない。cleanup は `username__icontains` となり、OSFの小文字化と整合する。テストは生成クエリを検証するもので、実DBでの削除は検証していない。seed の説明もログイン helper と一致した。

**R1-02 [P2]：解決。** 無制限な先頭一致をパス全体の一致へ変更した。対象は正確な `/css`・`/css2`、数値3成分の版と指定された es6-shim / MathJax のファイル名、32桁の16進gravatarハッシュまたは正確な `placeholder` に限る。この規則は版とqueryを固定せず、資産ルートの範囲を制限するもので、通信は許可しない。未知ファイル・suffix・似たprefix・異なる資産種類・port・資格情報は拒否し、API・画面遷移・WebSocketも例外にしない。SPEC-04 0.8 の説明と整合する。GitHubの読み取りで `RDM-osf.io-dev2027` の固定SHA `389415a473361fdaa3c347e84d95639b9096a9e9`、`addons/wiki/templates/edit.mako:4` に Material Symbols の `/css2` があることを確認した。無関係なendpointの追加ではなく、実在する固定依存の明示化である。

**R1-03 [P2]：ソースとローカル実行の水準で解決。** Node guard は対象設定タグが一つだけであることを求め、URI復号後のJSONとadapter一覧を検証し、GAを除いて再読込し、不在を確認する。タグ欠落・重複、不正符号化・設定、属性順・引用符の変更、符号化されたadapter名、キャッシュ済み出力に実行テストがある。shell はビルド条件分岐の後、毎回の serve 前に guard を実行し、`set -e` により失敗時は配信と新しい成功fingerprintの記録を止める。recipe `3` もfingerprintに入る。別途、一時ディレクトリでrecipe `2`→`3`のshell実行を確認し、`build`→`serve`を観測した。汎用HTMLセキュリティパーサではないが、対象の生成ページ形式を検証し、未対応の表現は起動を止める。固定された実コンテナでの実行は未検証であり、合格とは主張しない。

**r1 保守指摘 [P3]：解決。** `OBSOLETE_SECRET_KEYS` により `init --force` と成功した `rotate` の両方で `OSFSTORAGE_HMAC_SECRET` が消える。旧環境の回帰テストは無関係なport設定が保持されることも確認する。SPEC-02 0.9 は更新後のrotate・再作成前に `compose render` が必要と明記する。rotate失敗時のrollbackは設計どおり元の環境を保持する。今回の差分でHMAC利用側の配線は変わらず、r1の配線結論を維持する。

### 履歴の資格情報と残件

push済みの `4f70cfa` の平文は履歴・複製に残り、force-pushは禁止されている。squash mergeはマスク済みの最終treeを `develop` に載せるが、旧commit・PR参照・既存の複製を消さない。それでも、申告された条件下では今回のマージに対して残余リスクの受容は妥当である。対象は一台のMacのloopback限定開発環境だけで有効な使い捨て資格情報で、共有環境・本番の秘密ではなく、現在の証跡と以後のOSFパスワード生成は修正され、残存33件もPRに明示されている。これは状況に限定したリスク受容であり、使い捨て資格情報を秘密の例外とする判断でも、失効済みとの主張でもない。PRの約束どおり、進行中の受入作業後に残存アカウントを削除して削除結果を確認し、露出したアカウントを共有環境や外部到達可能な環境へ持ち込まないこと。この運用上の削除は残件で、本レビューでは実施していない。

C2/C4/C5/C6は別途の受入作業として残る。新しいGA guardも実コンテナでの確認が必要。並行render時の非原子的な書込みというr1の注意点は変わらず、今回の差分では想定された逐次実行に新しい具体的回帰を認めなかった。

### 検証と範囲

指定checkoutで `PYTHONPATH=installer python3 -m unittest discover -s installer/tests` は384件合格、10件skip（このPythonではacceptance conftestの依存が不足）。Node guard / commandの15テストはskipせず実行された。`python3 -m unittest discover -s tools/tests` も92件合格。`python3 tools/docs_check.py` は101ファイル検査・8件免除・用語警告22件で合格。`python3 tools/manifest_check.py` は検出ゼロで合格。`git diff --check` は問題なし。通常の文書検査は追跡ファイルのみを列挙するため、未追跡のr2記録は文書チェッカーの `check_file` で別途検証した。

書込みは未コミットのr2記録と指定された日本語PRコメント一件のみ。install・accept実行・Docker状態変更・実runtime環境ファイル参照・commit・push・approve・close・mergeは行っていない。テストは一時fixtureとstub実行器を使用しており、実コンテナ動作や実アカウント削除を証明しない。
