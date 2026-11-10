# PR40 Acceptance review r2 / 受入全件合格のレビュー r2

> **Summary:** Pass for the reviewed revision: R1-01–R1-03 are resolved for the installer-provisioned development stack. The refreshed evidence and local checks support the recorded acceptance result.
> **概要:** 対象版は合格。インストーラーが構築する開発スタックについて R1-01〜R1-03 は解決した。更新証跡とローカル検査は記録された受入結果を裏付ける。

**Jump:** [English](#english) · [日本語](#japanese)

- Version / 版: 0.1 — 2026-11-10. **Learned:** a fake listing must exercise both the ordinary list and the targeted search, because either path can lose its institution filter independently. ／ 一覧と個別検索では機関フィルターが別々に失われうるため、偽の一覧による検証は両方の経路を試す必要がある。
- Applies to: RCOSDP/RDM-developer-guide PR #40, head `ca2bf1b8be416406bf3b77860785014c7407b36e`, diff `2998b52..ca2bf1b`; REV（担当レビュワ, Codex Astra）.
- Related: [Review index](README.md) · [Review r1](2026-11-10_RDM-developer-guide_PR40_Acceptance_All_Pass_r1.md) · [SPEC-02](../spec/02_installer_cli.md) · [SPEC-04](../spec/04_acceptance_tests.md) · [SPEC-06](../spec/06_documentation_conventions.md).
- Used by: [DEMO-20](../demo/20_core_install_mac_studio.md) · [Status board](../status/README.md).

---

<a id="english"></a>
## English

[→ 日本語版へ](#japanese)

### Verdict and resolution

**Pass. No blocking findings in the reviewed delta.** Reviewed in the clean clone `/tmp/rdm-pr40-rev-r2-20261110`. This record is uncommitted. No application changes, commits, pushes, approvals, merges, closures, Docker state changes, or live `runtime/.env` access were performed. One Japanese PR comment accompanies the review.

**R1-01 resolved for the provisioned stack.** The seed assigns the administrator and the member only the first non-deleted institution (`[0:1]`), and the other member only the second (`[1:2]`); the administrator remains staff and not superuser. The separate fixture and environment variable reach C6. The ordinary list requires the own member and excludes both the unaffiliated user and the other member. E-mail search positively finds the own member and excludes the other member. I ran the actual imported C6 success function through its fake-page helper: the correctly filtered listing passed, a list containing the other member failed with “a user of another institution is in the institution's list”, and a list that leaked only on the other member's explicit search failed with “searching for a user of another institution lists it”. The exact 403 API rejection remains unchanged.

The institution seed relies on the installer initialization, rather than creating new institutions itself. `osf_init.json` runs `scripts.populate_institutions -e test -a` before the dependent services. A read through the GitHub API of that script at the pinned osf.io `fe90e5c3` found 68 distinct test entries, including `a2jlab` and `asu`. The two slices therefore select distinct institutions in the provisioned stack. The snippet does not assert the selected count: an independently altered database with fewer than two non-deleted institutions is outside this verified prerequisite. This is a nonblocking hardening opportunity, not proof of the live database's contents.

**R1-02 resolved.** SPEC-02 now explains in English and Japanese that `--insecure` serves static assets with `DEBUG = False`, is only for development, and requires loopback host publication; production must serve static assets through its own server. The existing loopback renderer and unit checks remain. The operating contract is now explicit; repeating the full explanation in DEMO-20 is unnecessary.

**R1-03 resolved.** Both board halves close the old `edit.mako` item and cite C4 2/2 in `acc-20261110T015520Z-ab4cc7`. GitHub read data confirms integration PR #4 merged on 2026-11-09 with `7acc9abf9e9e73b62c5882323ef4d5bcaefd6dc9`. Both DEMO-20 halves and both board halves cite the refreshed run and agree with its twelve passes.

### Suppressions, unit-test import and evidence

The delta adds exactly two line-scoped, rule-specific `nosemgrep` annotations in C4 for `javascript.lang.security.detect-insecure-websocket.detect-insecure-websocket`. One is on a comment quoting upstream JavaScript, and one is on the local `ws://` URL. The following assertion checks the parsed origin against exactly `127.0.0.1` before socket use. Both annotations explain their reason and add no blanket exclusion. They are minimal and justified; Semgrep itself was not rerun in this review.

Commit `ca2bf1b` replaces AST compilation plus `exec()` in the C6 unit helper with `importlib.import_module` of the real acceptance module. Temporary pytest/conftest stubs provide only decorators and the unused API dependency. The actual test and helper bodies are unchanged, module state is scoped by `mock.patch.dict`, and the fake-page checks demonstrate that assertions are still effective. There is no suppression of the removed exec finding.

The canonical [results.json](../demo/runs/acc-20261110T015520Z-ab4cc7/results.json), collector and JUnit agree on 12 passed, zero failures/errors/skips; TOON and pytest log agree. Rejection statuses C1–C6 are 401/403/403/4401/401/403. There are 98 known external requests blocked, not zero attempted requests. The run reports seeded core execution and pytest exit 0. Evidence parity was independently checked with assertions. Live acceptance was not rerun, and running image digests and actual database affiliations are not attested by results.json. The DEMO-20 prose is slightly broader for unaffiliated users: their exclusion is asserted in the ordinary list, while explicit searches cover the own and other-institution members. This does not weaken the requested cross-institution test.

### Local validation

Run from the scratch clone root; tests use disposable fixtures, including synthetic credential files. The Docker Compose parser test is read-only.

```sh
PYTHONPATH=installer python3 -m unittest discover -s installer/tests
python3 -m unittest discover -s tools/tests
python3 tools/docs_check.py
python3 tools/manifest_check.py
```

```toon
validation[6]{check,exit_code,result}:
  installer_unit,0,537 tests; 10 skipped
  tools_unit,0,93 tests
  docs_check,0,139 tracked files; 8 exempt; 25 warnings
  manifest_check,0,zero manifest and policy findings
  independent_fake_listing,0,filtered passes; list leak and search-only leak rejected
  evidence_parity,0,12 passing cases and rejection statuses agree
```

Logs: `/tmp/rdm-pr40-r2-check-0.log` through `/tmp/rdm-pr40-r2-check-3.log`, in command order. The untracked review was separately checked with `tools.docs_check.check_file`: zero errors. No required revision remains for this reviewed scope; this verdict is not a merge operation.

---

<a id="japanese"></a>
## 日本語

[→ To English](#english)

### 判定と解決状況

**Pass（合格）。対象差分にブロッカーなし。** クリーンクローン `/tmp/rdm-pr40-rev-r2-20261110` で確認し、記録は未コミットとした。アプリ変更、commit、push、approve、merge、close、Docker の状態変更、稼働環境の `runtime/.env` 参照はしていない。日本語の PR コメント一件を添える。

**R1-01 は構築済みスタックを前提に解決。** 管理者と自機関の利用者を最初の未削除機関だけ（`[0:1]`）、他機関の利用者を二番目だけ（`[1:2]`）へ所属させる。管理者は staff かつ非 superuser のまま。他機関の fixture と環境変数は C6 に届く。一覧は自機関の利用者の存在、無所属と他機関の利用者の不在を要求する。メール検索は自機関を見つけ、他機関を除外する。実際に import した C6 成功関数を偽ページで実行し、正常な絞り込みは合格、一覧に他機関を混ぜる場合は「a user of another institution is in the institution's list」で失敗、他機関の明示検索だけが漏れる場合も「searching for a user of another institution lists it」で失敗した。API の厳密な 403 拒否は維持している。

種データ作成は機関を新設せず、インストーラーの初期化に依存する。`osf_init.json` は依存サービスの起動前に `scripts.populate_institutions -e test -a` を実行する。固定した osf.io `fe90e5c3` のスクリプトを GitHub API で読むと、`a2jlab` と `asu` を含む異なる 68 件の test データがあった。この構築手順では二つのスライスは別機関を選ぶ。一方、snippet は選択件数を assert しないため、独自に変更され未削除機関が二件未満となった DB は確認済みの前提外となる。これは非ブロッカーの堅牢化余地であり、稼働 DB の内容を実証したという意味ではない。

**R1-02 解決。** SPEC-02 の英和で、`DEBUG = False` で静的資産を配信するための `--insecure`、開発専用・ホスト公開はループバック限定という制約、本番では自前のサーバーで配信することを説明した。既存のループバック描画と単体検査も維持した。運用契約が明記されたため、説明全文を DEMO-20 に重複させる必要はない。

**R1-03 解決。** ボード両言語で古い `edit.mako` 項目を完了とし、`acc-20261110T015520Z-ab4cc7` の C4 2/2 を引用した。GitHub の読取結果で、統合 PR #4 は 2026-11-09 に `7acc9abf9e9e73b62c5882323ef4d5bcaefd6dc9` としてマージ済みと確認した。DEMO-20 とボードの英和すべてが更新実行を引用し、十二件合格と一致する。

### 抑止・単体試験の import・証跡

差分の `nosemgrep` 追加は C4 の二行だけで、どちらも `javascript.lang.security.detect-insecure-websocket.detect-insecure-websocket` の指定付き。一方は上流 JavaScript を引用したコメント、他方はローカル `ws://` URL で、直後の assert が socket 使用前に解析した起点を厳密に `127.0.0.1` へ限定する。理由を併記し、包括的な除外を増やしていないため、最小限で妥当。今回 Semgrep 自体は再実行していない。

`ca2bf1b` は C6 単体試験 helper の AST コンパイルと `exec()` を、実際の受入モジュールの `importlib.import_module` に置き換えた。一時的な pytest/conftest stub は decorator と未使用の API 依存だけを提供し、試験と helper 本体はそのまま。モジュール状態は `mock.patch.dict` の範囲で扱い、偽ページで assert が有効なことも確認した。除去した exec 指摘への抑止は加えていない。

正本の [results.json](../demo/runs/acc-20261110T015520Z-ab4cc7/results.json)、collector、JUnit は 12 件合格・失敗／エラー／スキップゼロで一致し、TOON と pytest log も一致する。C1〜C6 の拒否値は 401/403/403/4401/401/403。既知の外部要求を 98 件遮断しており、要求試行ゼロではない。seeded の core 実行、pytest 終了 0 が記録され、証跡間の一致は独立した assert でも確認した。実受入は再実行せず、実行イメージ digest と稼働 DB の所属そのものは results.json が証明しない。DEMO-20 は無所属利用者について少し広く述べているが、無所属の除外は通常一覧で確認し、明示検索は自機関と他機関の利用者を対象とする。この表現差は依頼された機関間の試験を弱めない。

### ローカル検証

scratch クローン直下で、合成した資格情報ファイルを含む使い捨て fixture により英語節の四コマンドを実行した。Docker Compose の構文試験は読取専用。installer は 537 件（10 件スキップ）、tools は 93 件で、ともに終了 0。docs_check は追跡済み 139 ファイル・対象外 8・警告 25 で終了 0、manifest_check も manifest と policy の指摘ゼロで終了 0。独立した偽一覧検証と証跡整合検証も終了 0。

ログはコマンド順に `/tmp/rdm-pr40-r2-check-0.log`〜`/tmp/rdm-pr40-r2-check-3.log`。未追跡の記録は `tools.docs_check.check_file` で別途検査しエラーゼロ。対象範囲の必須修正は残っていない。この判定自体はマージ操作ではない。
