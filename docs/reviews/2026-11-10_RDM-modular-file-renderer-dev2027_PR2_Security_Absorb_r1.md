# REV RDM-modular-file-renderer-dev2027 PR2 security absorption r1 / セキュリティ吸収レビュー r1

> **Summary:** Independent review of PR2 at `288d2390f8d48fed6574e543395725f6ea6ae19e`. Verdict: Non-blocking / 非阻害.
> **概要:** PR2の対象head `288d2390f8d48fed6574e543395725f6ea6ae19e` を独立レビューした。判定: Non-blocking / 非阻害。

**Jump:** [English](#english) · [日本語](#japanese)

- Version / 版: 0.1 — 2026-11-10. **Learned:** The existing XLS parser already rejects dimensions over 10000; the PR adds useful mocked boundary coverage without changing production code. ／ 既存XLSパーサーは10000を超える寸法を拒否し、PRは製品コードを変えず境界値のモック検査を追加する。
- Applies to / 対象: RCOSDP/RDM-modular-file-renderer-dev2027 PR2, exact head recorded above; review only.
- Related: [Review index / レビュー索引](README.md) · [SPEC-06](../spec/06_documentation_conventions.md)
- Used by / 利用先: [Documentation index / 文書索引](../README.md), coordinator's absorption decision / 調整担当の吸収判断。

---

<a id="english"></a>
## English

[→ 日本語版へ](#japanese)

### Verdict and findings

No blocking finding. The change is one test file only. tests/extensions/tabular/test_xlrd_size_limit.py:28–41 verifies .xls selects xlsx_xlrd, checks TableTooBigError with HTTP code 400 and exact dimensions for 10001 rows or columns, and accepts 10000 rows with 9999 data rows after the header. mfr/extensions/tabular/libs/xlrd_tools.py:20–23 already has the strict greater-than check, and settings.py:17 maps .xls to that function.

[P3, coverage limitation] open_workbook is mocked and accepted rows have no cells. These tests establish parser dispatch and dimension rejection, not real BIFF decoding, populated-cell rendering or resistance to memory exhaustion during workbook loading. A 10001-row .xls fixture and an at-limit column case would strengthen coverage; the existing test-only change need not be blocked on them. A 10001-column case is synthetic, not a valid legacy XLS workbook.

### Evidence and threat boundary

Compared the exact head against dac70e2209f9b4104ee2d190d7462cf18eef3c9f. gh pr checks reports build-image and tests (mfr) passing. Local pytest could not collect: the legacy [pytest] configuration is unsupported by the installed pytest; bypassing that file exposed missing humanfriendly. Do not treat this as a product-test failure or a local pass.

Four isolated boundary checks passed for (10001,2), (2,10001), (10000,2) and (2,10000). The harness used real xlrd and the actual parser, exception and header function bodies, but stubbed the unrelated RendererError base and bypassed package initialization. It is /private/tmp/rev-security-PreTii/check_mfr.py. This supplemental check is not the PR's full pytest run or a real XLS decoding test.

The size check occurs after open_workbook and is per sheet, not an aggregate cell/workbook memory cap. Those are existing scope limits, not regressions introduced by this PR. The exception's .xlsx label for .xls is also pre-existing.

### Remaining work

Optional real-file and column-boundary coverage. No runtime code changes, deployment, approval, merge, push or commit were made.

---

<a id="japanese"></a>
## 日本語

[→ To English](#english)

### 判定と指摘

阻害する指摘はない。変更はテストファイル1個だけ。tests/extensions/tabular/test_xlrd_size_limit.py:28–41は.xlsがxlsx_xlrdを選ぶこと、10001行・列でHTTPコード400と正確な寸法を持つTableTooBigErrorになること、10000行では見出しを除く9999データ行を受け付けることを確認する。mfr/extensions/tabular/libs/xlrd_tools.py:20–23には既に厳密な「超える」検査があり、settings.py:17が.xlsを同関数へ割り当てる。

[P3・検査範囲] open_workbookはモックで、正常系の行にはセルがない。この試験が保証するのはパーサー選択と寸法の拒否であり、実BIFF読込み、値入りセルの表示、ブック読込み時のメモリ枯渇耐性ではない。10001行の実.xlsと列数の上限一致ケースがあると強くなるが、現行のテストのみの変更を阻害しない。10001列は合成ケースで、旧形式XLSとして有効なブックではない。

### 根拠と脅威の境界

対象headをdac70e2209f9b4104ee2d190d7462cf18eef3c9fと比較した。gh pr checksではbuild-imageとtests (mfr)が成功している。ローカルpytestは旧[pytest]設定をサポートせず収集できず、設定ファイルを迂回するとhumanfriendly不足になった。製品テスト失敗ともローカル成功とも扱わない。

(10001,2)、(2,10001)、(10000,2)、(2,10000)の隔離した境界値4件は成功した。実xlrdと実際のパーサー・例外・見出し関数の本体を使うが、無関係なRendererError基底を代替しパッケージ初期化を迂回した。検査コードは/private/tmp/rev-security-PreTii/check_mfr.py。この補助検査はPRのpytest全体でも実XLSの読込み試験でもない。

寸法検査はopen_workbookの後で、シート単位であり、全セル・ブック全体のメモリ上限ではない。PRによる回帰ではなく既存の範囲制限である。.xlsでも例外に.xlsxと付く点も既存動作。

### 残作業

実ファイルと列数上限一致の検査は任意改善。製品コード変更、デプロイ、承認、マージ、push、commitは行っていない。

---

## Glossary / 用語

| Term | English note | 日本語注 |
|---|---|---|
| PR / head | Proposed change / exact version reviewed. | 変更案／調べた正確な版。 |
| P1 / P2 / P3 | High / medium / low review priority. | 高／中／低の修正優先度。 |
| Secret / token | A private value used to prove identity or sign data. | 本人確認や署名に使う秘密の値。 |
| Regression | A change that breaks previously working behavior. | 以前動いた機能が変更で壊れること。 |
| CI / mock | Automated checks / a substitute used in a test. | 自動検査／試験用の代役。 |
| Secure cookie | A browser value restricted to secure transport. | 安全な通信経路に送信を限定するブラウザーの値。 |
