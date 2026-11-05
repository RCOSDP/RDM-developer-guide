# REV PR23 / PR24 review r1 / PR23・PR24 レビュー r1

> **Summary:** Both changes need revisions. Passing unit tests miss mirror retry behavior and several IdP contract mismatches.
> **概要:** 両変更とも修正が必要。単体試験は成功するが、ミラー再試行と IdP 契約の不一致を検出できていない。

**Jump:** [English](#english) · [日本語](#japanese)

- Version / 版: 0.1 — 2026-11-06. **Learned:** simulated commands and string-presence checks can pass while retries and attribute contracts remain broken. ／ コマンドの模擬と文字列の存在確認が成功しても、再試行と属性の契約は壊れたままになり得ると分かった。
- Applies to: PR #23 `80855952d8457f8d94e763ce4737afb0cb7ae652`; PR #24 `35ae779597c977156a4d8679519935741089d90a`; base `develop`.
- Reviewer: REV（担当レビュワ, Codex Astra）.
- Related: [Review index](README.md) · [SPEC-06](../spec/06_documentation_conventions.md) · [SPEC-05](../spec/05_upstream_tracking.md) · [SPEC-04](../spec/04_acceptance_tests.md) · [SPEC-02](../spec/02_installer_cli.md) · [ADR-01](../decisions/ADR-01_Integration_Repository_Placement.md).
- Used by: [Upstream status](../status/upstream/README.md).

---

<a id="english"></a>
## English

[→ 日本語版へ](#japanese)

### Verdict and validation

PR (a proposed code change) #23: **Changes requested**. PR #24: **Changes requested**, evaluated as M3 preparation, not completed acceptance. P1 means a high-priority functional failure; P2 means a contract or correctness issue to fix before accepting this proposal. SHA (a commit's identity), IdP (the service that checks a login), and SP (the service that consumes its answer) are used here ([shared glossary](../reference/REF-01_Glossary.md)). File:line evidence refers to the reviewed PR head, not the local develop checkout.

The following command ran in each supplied worktree (a separate checkout). It executes unit tests, not live containers:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=installer python3 -m unittest discover -s installer/tests
```

```toon
results[2]{pr,tests,skipped,result}:
  23,308,10,OK
  24,295,10,OK
```

No production fixes, commits, pushes, approvals, merges, or Docker (a tool that runs isolated programs) state changes were performed. S1–S5 remain skipped designs; these results do not prove working authentication.

### Ranked findings: PR #23

1. **U1 — P1: First dry-run prevents subsequent publication.** `installer/grdm_dev/upstream.py:194–220,229–235`: when the origin tracking branch is absent, `previous` falls back to the local branch. After dry-run has fetched that branch, a real run sees an unchanged local tip and never pushes it. The same problem follows a failed first push. Reproduced with the existing FakeGit and an origin containing only develop: dry-run exit 0, real run exit 0, zero push calls, origin still only develop. Compare publication against the remote's existence/SHA separately from the local fast-forward check. Add dry-run→real and failed-first-push→retry tests.
2. **U2 — P1: Rerun resets local integration work.** `installer/grdm_dev/upstream.py:370–379` checks only the remote branch, then uses `checkout -B`. A locally existing integration branch, including a manually committed conflict resolution after the documented abort workflow, is reset to the base. Reject an existing local branch too and use non-resetting branch creation. `installer/tests/test_upstream.py:479` covers only the remote case. This also means dry-run has persistent local side effects; it is not a side-effect-free preview.
3. **U3 — P1: Report publication checks out a branch over generated files.** `installer/grdm_dev/templates/workflows/upstream-mirror.yml:90–96,120–126`: reports are generated on develop before switching to the existing status branch. If that branch has reports absent from develop, the new untracked reports obstruct checkout; if develop has older reports, modified tracked files can obstruct it. Prepare the status checkout first or generate outside it and copy afterward. Also make failure-report publication explicit: line 113 lacks `always()`, so a failing mirror skips the public status push even though the artifact upload runs. Validate a second scheduled run and a failed fetch.
4. **U4 — P2: Exit 1 has no canonical CLI entry.** `installer/grdm_dev/upstream.py:68,303–305,482–484` returns 1 for operational failures. SPEC-05 now documents this, so it is not undocumented at module level; however SPEC-02 §6 (`docs/spec/02_installer_cli.md:135–152`) calls `messages.tsv` canonical and requires a distinct code for a new cause. Neither that table nor the shared messages are updated. Add an explicit bilingual upstream exception and canonical message/code, or adopt a new documented code consistently. A source comment alone does not reconcile the contracts.

### Ranked findings: PR #24

1. **I1 — P1: Japanese attributes have the wrong wire identifiers and no explicit IdP mapping.** `installer/grdm_dev/templates/idp/sp-attribute-map.xml:37–39` uses `1.3.6.1.4.1.32264.1.1.1` for jaOrganizationName, whereas the required GakuNin (Japan’s academic login federation) OID is `1.2.392.200453.100.20.1`. jaDisplayName is also placed under that unrelated namespace. `saml20-idp-hosted.php.tmpl:30` relies on the generic `name2oid` map; inspection of the [upstream map at a fixed commit](https://github.com/simplesamlphp/simplesamlphp/blob/f79834309f34d6aa0de3cf88ed39dda752f40138/attributemap/name2oid.php) found neither Japanese name. Supply an explicit verified GakuNin mapping on both sides and test emitted names against decoded names. Also verify pairwise-id conversion for the pinned release. A TODO does not make these templates a valid attribute contract.
2. **I2 — P2: Mock rule and test exceptions disagree.** `installer/acceptance/fixtures/idp/mock_users.json:24–27` contains `sn: USER` and bare `member`/`faculty`; other users do likewise. ADR-05 §3.5 and the bilingual fixtures README promise visibly mock-prefixed values, but `installer/tests/test_compose.py:504–506` silently exempts affiliations and `USER`. No real identity was found, but the requested all-values rule is not enforced. Use a visibly mock surname and reconcile controlled-vocabulary affiliations explicitly with the normative mock policy and rejection rule. Lines 498–503 only search values anywhere in PHP text, so swapping values between users can still pass; compare per-user/per-attribute structures.
3. **I3 — P2: S2 accepts HTTP 200 where SPEC-04 requires 403.** `installer/acceptance/test_s2_rdmcp.py:104–110` substitutes a JSON (structured text data) error's `http_status` for transport status 200. SPEC-04 §5's English and Japanese S2 rows require 403; unlike S3, they provide no alternative response form. Require actual HTTP 403 or amend both specification halves with the intended alternative before unskipping. Add a check that HTTP 200 carrying an embedded 403 is rejected under the present contract.

### Other checks and limits

PR #23 uses non-forced tracking fetch refspecs and explicit non-forced pushes. Public→private→adopted-PR order, candidate/COS (Center for Open Science) exclusion, private-only skip, identical-tip no-op, and conflict abort/exit 1 are covered by the fake runner. Report writers use selected names/SHAs/counts; grep and tests at `test_upstream.py:325–350,403–414` check URL absence. Raw subprocess output is streamed to stderr, so this assurance applies to stored mirror reports, not every execution log. SHA parsing (`upstream.py:126–129`) trusts the first output line without validating hexadecimal shape. Archive pruning (`244–255`) accepts every date-shaped stem, irrespective of suffix, and will fail on a date-named directory; narrow it to regular `.json`/`.toon` files and test the boundary. Existing tests cover normal archives, not those cases.

Workflow actions are pinned to 40-character SHAs; credentials are placeholders with separate source-read/integration-write and report-write scopes, and no actual secret is present. Each component writes the same latest/archive paths, so shared status publication also needs aggregation or per-component paths to preserve all repositories' reports. SPEC-05 explicitly allows local fetch/report/merge operations during dry-run; the narrower no-remote-write promise is implemented, while the task's literal no-side-effects criterion is not.

PR #24's ePPN, affiliation, targeted ID, mail, and organization OIDs match the supplied expected values. ADR-05 compares four options and records tradeoffs; English/Japanese decision content and SPEC-04 tables correspond. Numerical image-size/startup claims are estimates without measurements in this PR. Fixtures README is bilingual. Compose tests cover 127.0.0.1 publishing on grdm-edge, read-only mounts and existing hardening exceptions. Actual test_idp still lacks non-root/read_only enforcement because the old Java exception remains; F-3/F-4 explicitly defer exception removal and the separate image. This is disclosed preparation debt, not evidence that the proposed baseline already works. F-1/F-2/F-5 likewise defer rendering, secrets and institution setup. S1's 4401/zero-frame rejection, S3's explicit denial, S4's 401 and S5's SP 403/no-cookie/API 401 designs broadly match their table contracts; only S2 has the concrete mismatch above.

---

<a id="japanese"></a>
## 日本語

[→ To English](#english)

### 判定と検証

PR（コード変更の提案）#23 は **修正要求**。#24 も **修正要求**。#24 は M3 の準備として評価し、受入完了とは扱わない。P1 は優先度の高い機能障害、P2 は採用前に直す契約・正確性の問題。SHA はコミットを識別する値、IdP はログインを確認し、SP はその回答を利用する部品（[共通用語集](../reference/REF-01_Glossary.md)）。ファイル:行番号はレビュー対象の PR 先端に対応し、ローカル develop の行番号ではない。

指定の各 worktree（別の作業用チェックアウト）で英語節の単体試験コマンドを実行した。#23 は 308 件、#24 は 295 件で、各 10 件スキップ、いずれも OK。製品の修正、commit、push、承認、merge、Docker の状態変更はしていない。S1〜S5 はスキップ付き設計のままであり、この結果は認証の実動を証明しない。

### 優先順の指摘: PR #23

1. **U1 — P1: 初回 dry-run 後に公開されない。** `installer/grdm_dev/upstream.py:194–220,229–235` は、origin に追跡ブランチがないとローカル値を previous に使う。dry-run が一度取得すると、本実行は変更なしと判定して push しない。初回 push 失敗後も同じ。既存 FakeGit で origin を develop のみにして再現し、dry-run 0、本実行 0、push 0 回、origin は develop のみだった。リモートの存在/SHA とローカルの fast-forward 判定を分け、dry-run→本実行と初回 push 失敗→再試行を検査する。
2. **U2 — P1: 再実行がローカル統合作業をリセットする。** `upstream.py:370–379` はリモートだけ確認して `checkout -B` する。文書に従って衝突を手で解きコミットしたローカル統合ブランチも開始点へ戻る。ローカル既存ブランチも拒否し、リセットしない作成方法を使う。`test_upstream.py:479` はリモートしか検査しない。dry-run にも持続するローカル副作用がある。
3. **U3 — P1: 生成済み報告が status ブランチへの切替を妨げる。** `installer/grdm_dev/templates/workflows/upstream-mirror.yml:90–96,120–126` は develop 上で報告を書いてから切り替える。status にだけ既存報告があれば未追跡ファイル、develop に古い報告があれば変更済みファイルが切替を妨げ得る。status の作業場所を先に用意するか、外で生成して後から複写する。113 行に `always()` がないため、ミラー失敗時は成果物を保存しても公開 status は更新されない。二回目の日次実行と fetch 失敗で検証する。
4. **U4 — P2: 終了 1 が CLI 正本にない。** `upstream.py:68,303–305,482–484` の終了 1 は SPEC-05 には明記されたが、SPEC-02 §6（`docs/spec/02_installer_cli.md:135–152`）の正本 `messages.tsv` と番号規則には反映されていない。上流コマンドの例外と正本メッセージ/番号を英和で明記するか、新しい番号を一貫して割り当てる。ソースのコメントだけでは契約は整合しない。

### 優先順の指摘: PR #24

1. **I1 — P1: 日本語属性の識別子が誤り、IdP 側の明示対応表もない。** `installer/grdm_dev/templates/idp/sp-attribute-map.xml:37–39` の jaOrganizationName は `1.3.6.1.4.1.32264.1.1.1` だが、要求された GakuNin OID は `1.2.392.200453.100.20.1`。jaDisplayName も別系統の番号である。`saml20-idp-hosted.php.tmpl:30` が使う汎用 `name2oid` は、英語節に固定コミットで示した上流ファイルでは日本語二属性を含まない。双方に検証済みの明示対応表を置き、送出名と受信名の一致を検査する。固定するリリースで pairwise-id の変換も確認する。TODO では有効な属性契約にならない。
2. **I2 — P2: 模擬値規則と試験の例外が不一致。** `installer/acceptance/fixtures/idp/mock_users.json:24–27` に `sn: USER` と裸の `member`/`faculty` があり、他の利用者も同様。ADR-05 §3.5 と英和 README は模擬と分かる接頭辞を約束する一方、`test_compose.py:504–506` が所属と `USER` を黙って例外化する。実在の個人情報は見つからなかったが、全値規則は守られていない。姓を明白な模擬値にし、所属の標準語彙を使う例外は正本方針と拒否規則に明示的に整合させる。498〜503 行は PHP 全体から値を探すだけで、利用者間の入替を見逃すため、利用者・属性単位で構造比較する。
3. **I3 — P2: S2 が仕様の 403 に対して HTTP 200 を許す。** `installer/acceptance/test_s2_rdmcp.py:104–110` は HTTP 200 を JSON 内の `http_status` に置き換える。SPEC-04 §5 の英和 S2 行は 403 を要求し、S3 と違い代替形式を許していない。実際の HTTP 403 を要求するか、スキップ解除前に英和仕様を変更する。現契約では「HTTP 200 内に 403」は不合格になることを検査する。

### その他の確認と限界

#23 の追跡 fetch と push は強制指定なし。公開→非公開→採用 PR、候補/COS の除外、private 専用スキップ、先端一致の無操作、衝突時 abort/終了 1 は模擬実行器で検査される。報告は選んだ名前/SHA/件数から構築し、`test_upstream.py:325–350,403–414` と grep で URL 不在を確認した。ただし実コマンドの生出力は stderr に流れるので、保存ミラー報告への保証であり全ログの保証ではない。SHA 読取（`upstream.py:126–129`）は最初の行を16進形式検査なしで信頼する。アーカイブ削除（244〜255 行）は拡張子を問わず日付名を対象にし、日付名のディレクトリでは失敗する。通常の `.json`/`.toon` ファイルに限定し境界例を検査するとよい。

workflow の action は40桁 SHA 固定で、認証情報は取得元読取/統合先書込と報告先書込の別プレースホルダ。実秘密はない。各部品が同じ latest/archive を書くため、全リポジトリの報告を残すには集約または部品別の保存先も必要。SPEC-05 は dry-run 中のローカル fetch・報告・merge を明記しており、リモートを書かない狭い意味では実装されるが、依頼の文字どおりの「副作用なし」ではない。

#24 の ePPN、affiliation、targeted ID、mail、o の OID は指定の期待値と一致。ADR-05 は四案と代償を記録し、英和の決定内容と SPEC-04 表は対応する。容量・起動時間の数値は PR 内に測定根拠のない見積り。fixtures README は二言語。Compose 試験は grdm-edge 上の 127.0.0.1 公開、読取専用マウント、既存の強化例外を検査する。実際の test_idp は古い Java 例外のため非 root/read_only が未適用で、F-3/F-4 に例外解除と専用イメージを明示的に延期している。準備段階の未完事項であり、基本対策の実動証拠ではない。F-1/F-2/F-5 も描画・秘密・機関設定を延期。S1 の 4401/文書フレーム0、S3 の明示拒否、S4 の401、S5 の SP 403/cookie なし/API 401 は概ね表と一致し、具体的な不一致は前述の S2。

---

## Glossary / 用語

| Term | English note | 日本語注 |
|---|---|---|
| Fast-forward | Advancing a branch without replacing its history. | 履歴を置き換えず枝を先へ進めること。 |
| Mock | Invented data used for a test. | 試験用の作り物のデータ。 |
| OID | A numeric name identifying an attribute. | 属性を識別する数字の名前。 |
| SAML | The message format used to pass a login result. | ログイン結果を渡す文書形式。 |
| Dry-run | A preview; its permitted local writes must be stated. | 予行。許されるローカル書込を明記する必要がある。 |
