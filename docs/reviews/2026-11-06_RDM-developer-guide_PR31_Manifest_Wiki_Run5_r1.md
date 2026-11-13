# PR31 Manifest and run 5 review r1 / マニフェスト・第5回導入レビュー r1

> **Summary:** Pass with three non-blocking documentation corrections. The pinned integration commit is correct, policy checks pass, and the run log supports the recorded failure and remaining work.
> **概要:** 文書の軽微な訂正3件を付して合格。固定した統合コミットは正しく、ポリシー検査は合格し、実行ログは記録された失敗と残件を裏付ける。

**Jump:** [English](#english) · [日本語](#japanese)

- Version / 版: 0.1 — 2026-11-06. **Learned:** passing automated checks does not establish the accuracy of step counts, warning categories or translated completion claims; those need comparison with the logs. ／ 自動検査の合格だけでは段数・警告の分類・翻訳の完了表現の正しさは分からず、ログとの照合が必要である。
- Applies to: RCOSDP/RDM-developer-guide PR #31; REV（担当レビュワ, Codex Astra）.
- Related: [Review index](README.md) · [SPEC-01](../spec/01_manifest.md) · [SPEC-06](../spec/06_documentation_conventions.md) · [Wiki PR #2 review](2026-11-06_RDM-wiki-frontend-dev2027_PR2_JS_Deps_Sync_r1.md).
- Used by: [DEMO-20](../demo/20_core_install_mac_studio.md) · [Status board](../status/README.md).

---

<a id="english"></a>
## English

[→ 日本語版へ](#japanese)

### Verdict and scope

**Pass with non-blocking documentation nits R1-01–R1-03; no blocking findings.** This verdict is not a GitHub approval. Reviewed head `06684b2f5f75dccd149431f8211e9f0f8cecca16`; all four changed local files match that head byte for byte. Scope covers the manifest pin/note, DEMO-20 run 5, the status board and the imported wiki PR #2 review. The git-ignored `runtime` symlink was not inspected and Docker state was not changed.

### Findings

- **R1-01 — low:** DEMO-20 lines 162/318 say 85 of 86 Dockerfile steps passed. `install-run5.log` line 1601 identifies the failing instruction as `[85/86]`; step 85 did not pass. Change both languages to “failed at step 85 of 86”.
- **R1-02 — low:** DEMO-20 lines 170/326 classify all four successful-build warnings as performance warnings. `wiki-overlay-test-build.log` lines 320–342 show one missing `mode` configuration warning and three performance warnings. The imported wiki PR #2 review already records this distinction. Correct both languages to “four webpack warnings: one mode configuration warning and three performance warnings”; no code change is needed.
- **R1-03 — low, EN/JA parity:** DEMO-20 line 170 says run 6 “is recorded below”, but no run 6 entry exists. Japanese line 326 describes a future addition, and the status board says run 6 is next. Change the English to “run 6 will be recorded after it is executed” and keep the Japanese future tense.

### Evidence and checks

GitHub's develop-branch API returns `cd96330f01e2e4b719912350487f3290f7b3b24a`, exactly matching `wiki-frontend.integration_sha`; wiki PR #2 reports the same merge commit and is merged. Repository references remain names only, with no private-repository URLs introduced. The manifest note correctly leaves editor-template/browser verification pending.

The run 5 log supports exit 30 at `build`, successful preceding steps, three built components with the recorded commit prefixes, two prebuilt components, fakecas remapping from 8080 to 8081, and two missing `linkify-html` errors in `comment.js` and `osfHelpers.js`. The separate overlay test log supports successful webpack output and image export. Logs alone do not independently attest every historical date, the exact test-build input commits, its requested platform or final image filesystem; no runtime/browser acceptance is claimed by this review.

Both edited document versions are 0.6 with bilingual learned notes. Anchors, Jump links, relative links and the imported review format pass SPEC-06 checks; substantive new EN/JA content agrees except R1-03. The status board correctly keeps M2 in progress, moves the editor-template item into its M2 table and leaves startup, health, scanning and acceptance pending. GitHub confirms PRs #21–#30 are merged.

Observed results, not canonical manifest data; commands ran from the review worktree root:

```toon
checks[5]{command,result}:
  "python3 tools/manifest_check.py","PASS; zero findings"
  "python3 tools/docs_check.py","PASS; 90 files checked, 8 exempt, 19 non-failing glossary warnings"
  "PYTHONPATH=installer python3 -m unittest discover -s installer/tests","OK; 345 tests, 10 skipped"
  "python3 -m unittest discover -s tools/tests","OK; 89 tests"
  "gh pr checks 31 --repo RCOSDP/RDM-developer-guide","PASS; all 8 checks"
```

The new untracked review is also checked directly through the documentation checker's `check_file` function, because its normal file enumeration includes tracked files only. Remaining work is the three prose corrections, then the already-open run 6 and M2 acceptance work; no merge, approval, closure, commit or push was performed.

---

<a id="japanese"></a>
## 日本語

[→ To English](#english)

### 判定と範囲

**軽微な文書指摘 R1-01〜R1-03 を付して合格。阻害指摘なし。** GitHub の承認操作ではない。対象 head は `06684b2f5f75dccd149431f8211e9f0f8cecca16` で、変更4ファイルのローカル内容はすべてその head とバイト単位で一致する。manifest の固定値・注記、DEMO-20 第5回、進捗表、取り込まれた wiki PR #2 レビューを確認した。git 無視対象の `runtime` シンボリックリンクは調査せず、Docker の状態も変更していない。

### 指摘

- **R1-01 — 軽微:** DEMO-20 の162/318行は86段中85段を通過したと書くが、`install-run5.log` の1601行で失敗した命令は `[85/86]`。85段目は通過していない。英和とも「86段中85段目で失敗」に訂正する。
- **R1-02 — 軽微:** DEMO-20 の170/326行は成功ビルドの警告4件すべてを性能関連とする。`wiki-overlay-test-build.log` の320〜342行では `mode` 未設定が1件、性能関連が3件。取り込んだ wiki PR #2 レビューもこの区別を記録している。英和とも「webpack 警告4件（mode 未設定1件、性能関連3件）」に訂正する。コード変更は不要。
- **R1-03 — 軽微・英和対応:** DEMO-20 の英語170行は第6回を既に記録したと読めるが、第6回の節はない。日本語326行は今後の追記を述べ、進捗表も第6回を次の作業としている。英語を「第6回は実行後に記録する」に直し、日本語の未来表現を保つ。

### 証跡と検査

GitHub の develop ブランチ API は `cd96330f01e2e4b719912350487f3290f7b3b24a` を返し、`wiki-frontend.integration_sha` と完全一致する。wiki PR #2 も同じマージコミットを持ち、マージ済み。リポジトリ参照は名前のみで、非公開リポジトリの URL は追加されていない。manifest の注記はエディタのテンプレートとブラウザ検証を正しく未完としている。

第5回ログは `build` での終了30、それ以前の手順成功、記載のコミット接頭辞を持つ3部品のビルド、2部品の配布済みイメージ利用、fakecas の8080から8081への変更、`comment.js` と `osfHelpers.js` における `linkify-html` 不足のエラー2件を裏付ける。別のオーバーレイ試験ログは webpack 出力とイメージ export の成功を裏付ける。ログだけでは過去の日付のすべて、試験ビルドの入力コミット、指定プラットフォーム、最終イメージのファイル内容を独立には証明できない。本レビューは実行時・ブラウザ受入の成功を主張しない。

変更した両文書は版0.6で、学びの記載は英和対応している。アンカー、Jump、相対リンク、取り込んだレビューの形式は SPEC-06 検査に合格し、新規本文の内容も R1-03 を除き対応する。進捗表は M2 を進行中に保ち、エディタのテンプレート項目を M2 表に移し、起動・稼働確認・検査・受入を未完としている。PR #21〜#30 のマージ済み状態を GitHub で確認した。

英語部の TOON は正本でなく、レビュー作業ツリーのルートで実行した検査結果。manifest 検査は指摘0、docs 検査は90ファイル確認・8除外・非失敗の用語注警告19件で合格。installer は345テスト中10スキップで成功、tools は89テスト成功、PR の8チェックもすべて成功した。

通常の文書検査は追跡済みファイルだけを列挙するため、新規未追跡のレビューは検査器の `check_file` 関数でも直接確認する。残件は文章の訂正3件と、既に未完とされる第6回・M2受入の作業。merge・approve・close・commit・push は行っていない。

---

## Glossary / 用語

| Term | English note | 日本語注 |
|---|---|---|
| Integration SHA | Exact commit fingerprint selected for a combined component. | 統合した部品に使うコミットを特定する指紋。 |
| Overlay | Files placed over another source tree before building. | ビルド前に別のソースの木へ重ねるファイル。 |
| Non-blocking finding | A correction that does not prevent accepting the change. | 変更の採用を妨げない訂正事項。 |
| Acceptance | Checking that the working system meets its intended use. | 動くシステムが目的を満たすか確かめること。 |
