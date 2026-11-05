# REV PR24 M3 preparation review r2 / PR24 M3 準備レビュー r2

> **Summary:** The three previous findings are resolved, and the author's Japanese attribute identifiers are correct. One new automated security-check failure still needs revision.
> **概要:** 前回の三指摘は解消し、日本語属性の識別子は著者の訂正が正しい。新たな自動セキュリティ検査の不合格一件は修正が必要。

**Jump:** [English](#english) · [日本語](#japanese)

- Version / 版: 0.1 — 2026-11-06. **Learned:** primary sources must settle identifier disputes, including errors introduced by a reviewer; a passing regression test can still fail the security gate. ／ 識別子の争いはレビュワ自身の誤りも含め一次資料で決着すべきで、回帰試験が成功してもセキュリティ検査には失敗し得ると分かった。
- Applies to: [PR #24](https://github.com/RCOSDP/RDM-developer-guide/pull/24), `feat/m3-idp-prep`, SHA (commit identity / コミット識別子) `ae883a457e1815848edbace846bd02d836827fce`.
- Reviewer: REV（担当レビュワ, Codex Astra）.
- Related: [Review index](README.md) · [r1](2026-11-06_RDM-developer-guide_PR23_PR24_r1.md) · [SPEC-06](../spec/06_documentation_conventions.md) · [SPEC-04](../spec/04_acceptance_tests.md) · [Shared glossary / 共通用語集](../reference/REF-01_Glossary.md).
- Used by: [Upstream status](../status/upstream/README.md).

---

<a id="english"></a>
## English

[→ 日本語版へ](#japanese)

### Verdict

**Needs revision: R2-01, a failing CI (automated checks) gate.** I1–I3 are resolved for M3 preparation. This is a review judgment, not a GitHub approval. S1–S5 remain skipped acceptance designs; no live authentication or container execution was validated.

### Independent source check and correction to r1

I independently searched and read the official [GakuNin technical application standard Ver. 2.6, Annex 1](https://www.gakunin.jp/sites/default/files/2024-03/gakunin_technical_application_standard_v2.6.pdf). Items 2, 4, 11, 13 and 15 identify the suffixes under `1.3.6.1.4.1.32264.1.1` as jaOrganizationName `.4` (friendlyName `jao`), jaOrganizationalUnitName `.5` (`jaou`), jaSurname `.1` (`jasn`), jaGivenName `.2`, and jaDisplayName `.3`. The OID (numeric attribute identifier) `1.2.392.200453.100.20.1` proposed in r1 is not supported by that standard and does not occur in its extracted text. **I retract that r1 recommendation.** The author's correction and ADR-05 §3.7 evidence are correct; r1's original `.1`/`.5` mapping was also incorrect.

### Resolution of I1–I3

- **I1 resolved.** The IdP (login provider) explicitly maps all fixture attributes to wire names; the SP (receiver of the login result) has the matching 14 names. `saml20-idp-hosted.php.tmpl` generates identifiers before mapping, then applies `AttributeLimit` with `default => false`; `uid` is excluded. The targeted identifier uses `nameId => true` and `attributeencodings` set to `raw`, paired with `NameIDAttributeDecoder`. The pairwise identifier retains its own standard name and uses a scoped decoder. The test parses both configuration files, compares the name sets, checks the Japanese OIDs, encodings and decoder types, and verifies the intended filter configuration. This is a static contract check, not a captured SAML (login message) exchange.
- **I2 resolved.** Surnames are visibly `MOCK-USER`. ADR-05 §3.5, both fixture README language sections, and the fixture explicitly restrict the affiliation exception to four values. The test compares user/password keys and every attribute/value list structurally; swapped users' attributes no longer pass. It checks that the rejection user lacks `member` and the success user has it. This local test vocabulary is not a claim that every value is in the Ver. 2.6 GakuNin subset: Annex 1 item 7 lists faculty/staff/student/member; `affiliate` is used here to exercise rejection.
- **I3 resolved functionally.** S2 now requires actual HTTP (web response) status 401 and 403. The regression test rejects HTTP 200 with an embedded 403, ordinary 200, and 404. Its method of loading the helper creates R2-01.

I additionally read upstream SimpleSAMLphp tag `v2.5.3.1` through the GitHub API: `AttributeMap` preserves unmapped attributes; `AttributeLimit` removes attributes outside its explicit list; `TargetedID` creates the NameID-valued attribute; `SubjectID` extracts the domain after `@`; `PairwiseID` writes `ATTR_PAIRWISE_ID`. The [hosted IdP reference](https://github.com/simplesamlphp/simplesamlphp/blob/v2.5.3.1/docs/simplesamlphp-reference-idp-hosted.md) documents the raw encoding. The tag is the inspected source version, not proof that the future image has been pinned or run.

### Remaining finding

**R2-01 — P2 (fix before acceptance): new S2 regression test fails the security gate.** `installer/tests/test_compose.py:649` executes an extracted syntax-tree function with `exec(compile(...), ns)`. [Semgrep job 127494009322](https://github.com/RCOSDP/RDM-developer-guide/actions/runs/42098283699/job/127494009322) reports `python.lang.security.audit.exec-detected.exec-detected` at this exact line and exits 1. This is a real failing check, not evidence of attacker-controlled execution: the input is the repository's own acceptance module. Move the dependency-free status helper into an importable module shared by acceptance and unit tests, and import it normally. Preserve the negative tests and rerun the unit suite and CI. Do not weaken the global security gate.

### Validation and limits

Run from the supplied `scratchpad/wt-m3` root; its branch reference matched the reviewed SHA. Both commands exited 0:

```sh
PYTHONPATH=installer python3 -m unittest discover -s installer/tests
python3 tools/docs_check.py
```

The unit suite ran 298 tests with 10 skipped. The documentation checker passed 62 files, exempted 8 and reported 166 warnings. These are results for the supplied PR worktree, before adding this review record to the coordinator checkout.

The post-push check used:

```sh
 gh pr checks 24 --repo RCOSDP/RDM-developer-guide
```

Its final result was five passed checks (links, documentation build, manifest/private-URL policy, secret scan and report-only filesystem scan), with Semgrep failed. The failure log was retrieved with `gh run view 42098283699 --repo RCOSDP/RDM-developer-guide --log-failed`.

Follow-ups F-1–F-5, actual attribute exchange with the built SP, the image/version pin, rendering, secrets, institution login routing and removal of existing hardening exceptions remain M3 work. No production files, commits, pushes, approvals, merges, issue closures or Docker state changes were made by this review.

---

<a id="japanese"></a>
## 日本語

[→ To English](#english)

### 判定

**修正要求: R2-01、CI（自動検査）の不合格。** I1〜I3 は M3 準備として解消した。これはレビュー判定であり GitHub の承認操作ではない。S1〜S5 はスキップ付き受入設計であり、認証やコンテナの実動は検証していない。

### 一次資料の独立確認と r1 の訂正

公式の[学認技術運用基準 Ver. 2.6 別添1](https://www.gakunin.jp/sites/default/files/2024-03/gakunin_technical_application_standard_v2.6.pdf)を独立に検索し読んだ。項目2・4・11・13・15では、`1.3.6.1.4.1.32264.1.1` 配下で jaOrganizationName は `.4`（friendlyName `jao`）、jaOrganizationalUnitName は `.5`（`jaou`）、jaSurname は `.1`（`jasn`）、jaGivenName は `.2`、jaDisplayName は `.3`。r1 で提案した OID（属性を識別する番号）`1.2.392.200453.100.20.1` は基準に根拠がなく、抽出テキストにも出現しない。**r1 の当該推奨を撤回する。** 著者の訂正と ADR-05 §3.7 の根拠は正しく、修正前の `.1`/`.5` の割当ても誤りだった。

### I1〜I3 の解消

- **I1 解消。** IdP（ログイン提供側）が模擬属性を送信名へ明示的に変換し、SP（ログイン結果を受け取る側）も同じ14名を定義する。`saml20-idp-hosted.php.tmpl` は識別子生成→名前変換→`default => false` の `AttributeLimit` の順で、`uid` を除外する。targeted identifier は `nameId => true` と `raw` の `attributeencodings`、受信側は `NameIDAttributeDecoder`。pairwise identifier は標準の名前を保持し、scope を扱う decoder を使う。試験は両設定を構文解析して送受信名集合、日本語 OID、符号化、decoder 型、フィルタ設定を検査する。これは静的な契約検査で、SAML（ログイン結果の文書）の実送受信ではない。
- **I2 解消。** 姓は `MOCK-USER`。ADR-05 §3.5、英和の fixture README、fixture の全てが所属語彙の例外を四値に明示限定する。試験は利用者/パスワードのキーと属性・値の一覧を構造比較し、利用者間の属性入替を見逃さない。拒否用利用者に `member` がなく、成功用にあることも検査する。このローカル試験用語彙を Ver. 2.6 学認の部分集合と同一視しない。別添1項目7は faculty/staff/student/member を列挙し、ここでの `affiliate` は拒否試験に使う。
- **I3 は機能上解消。** S2 は HTTP（Web 応答）の実ステータス401・403を要求する。回帰試験は内部データに403を含む200、通常の200、404を拒否する。ただし補助関数の読み込み方法が R2-01 を発生させた。

さらに GitHub API で SimpleSAMLphp のタグ `v2.5.3.1` を確認した。`AttributeMap` は未対応属性を保持し、`AttributeLimit` は明示一覧以外を除外する。`TargetedID` は NameID 型属性を生成し、`SubjectID` は `@` 後のドメインを抽出、`PairwiseID` は `ATTR_PAIRWISE_ID` に出力する。[IdP 設定リファレンス](https://github.com/simplesamlphp/simplesamlphp/blob/v2.5.3.1/docs/simplesamlphp-reference-idp-hosted.md)にも raw 符号化が記載される。これは確認したソースの版であり、将来のイメージが固定・実行済みという意味ではない。

### 残る指摘

**R2-01 — P2（採用前に修正）: S2 回帰試験がセキュリティ検査を失敗させる。** `installer/tests/test_compose.py:649` が抽出した構文木の関数を `exec(compile(...), ns)` で実行する。[Semgrep job 127494009322](https://github.com/RCOSDP/RDM-developer-guide/actions/runs/42098283699/job/127494009322) は同じ行で `python.lang.security.audit.exec-detected.exec-detected` を報告し終了1となった。実際の検査不合格であるが、入力はリポジトリ自身の受入モジュールであり、攻撃者による実行の証拠ではない。依存のないステータス検査関数を受入・単体試験で共有する通常 import 可能なモジュールへ移し、否定例を維持して単体試験と CI を再実行する。全体の検査規則は弱めない。

### 検証と限界

指定された `scratchpad/wt-m3` のルートで英語節の二コマンドを実行した。ブランチ参照はレビュー対象 SHA と一致した。いずれも終了0で、単体試験298件・スキップ10件、文書検査は62ファイル成功・8除外・166警告だった。これはコーディネータ側へレビュー記録を追加する前の PR 作業場所での結果である。

push 後の `gh pr checks 24 --repo RCOSDP/RDM-developer-guide` は最終的に5件成功（リンク、文書ビルド、manifest/非公開URL方針、秘密検査、報告専用のファイル検査）、Semgrep が不合格。英語節の `gh run view` コマンドで失敗ログも取得した。

後続 F-1〜F-5、構築した SP との実送受信、イメージ/版固定、設定生成、秘密情報、機関ログイン経路、既存の強化例外解除は M3 の作業として残る。このレビューでは製品ファイルの変更、commit、push、承認、merge、Issue の終了、Docker の状態変更は行っていない。

---

## Glossary / 用語

| Term | English note | 日本語注 |
|---|---|---|
| Fixture | Invented input for a repeatable test. | 繰り返せる試験に使う作り物の入力。 |
| Wire name | The attribute name actually sent between services. | サービス間で実際に送る属性名。 |
| Decoder | A component that reads a received value. | 受け取った値を読み取る部品。 |
| Semgrep | A tool that searches source code for suspect patterns. | ソースコードから注意が必要な形を探す道具。 |
| Regression test | A test preventing a fixed error from returning. | 修正済みの誤りが戻らないようにする試験。 |
