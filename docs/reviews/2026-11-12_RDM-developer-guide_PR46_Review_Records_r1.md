# REV PR46 Review records review r1 / レビュー記録公開レビュー r1

> **Summary:** The twelve committed review records match REV's issued publication versions byte for byte, and the change adds no other files. Two minor corrections are needed in the PR description; the CI result is recorded in the verification section.
> **概要:** 追加されたレビュー記録12件は REV 発行の公開版とバイト単位で一致し、ほかのファイル変更はない。PR 本文には軽微な訂正2点があり、CI の結果は検証節に記録する。

**Jump:** [English](#english) · [日本語](#japanese)

- Version / 版: 0.1 — 2026-11-12. **Learned:** A publication copy can preserve the review exactly while its PR description still understates the checked files and the publication transformations. ／ 公開版がレビュー原文を正確に保持していても、PR 本文が検査対象件数や公開用変換の範囲を過小に説明することがある。
- Applies to / 対象: [PR #46](https://github.com/RCOSDP/RDM-developer-guide/pull/46), head `ce24a453a4f6d797045a84d847f92db9bb4a26a6`, base `eb8c4e96977b06bd3bb0fd42b03f0872806be08a`.
- Reviewer / 担当: REV（担当レビュワ, Codex Astra）.
- Related: [Review index / レビュー索引](README.md) · [SPEC-06](../spec/06_documentation_conventions.md) · [ADR-04](../decisions/ADR-04_AI_Autonomy_and_Roles.md).
- Used by / 利用先: PR #46 publication review / 公開レビュー.

---

<a id="english"></a>
## English

[→ 日本語版へ](#japanese)

### Verdict and scope

**Pass with two non-blocking documentation nits.** The publication artifacts have no blocking finding. The two P3 findings concern the PR description only. This is a review verdict, not GitHub approval or authorization to merge.

A fresh isolated clone was inspected at the full head above. The diff against the merge base contains exactly twelve added Markdown files under `docs/reviews/`, with no modification, deletion, or other addition. Each committed blob was compared directly with the corresponding issued publication file; all twelve match byte for byte and match the SHA-256 values in `publication-validation.json`. Every file is publication version 0.2 dated 2026-11-12. Historical application tests were not rerun for this publication-only review.

### Findings

**R1-01 / P3 — Correct the documented check count.** The PR verification section says `154` files were checked. Running `python3 tools/docs_check.py` at this head checks **166** files, exempts 8, and reports 38 existing warnings, with no errors or warnings in the twelve added records. The checker enumerates tracked files with `git ls-files`; 154 does not demonstrate coverage of the twelve additions. Replace the count and state that the committed additions were included.

**R1-02 / P3 — Describe all publication transformations.** The PR method section says that REV only replaced URLs and paths with names and numbers in plain text. The issued records also convert local guide references into repository-relative links and add version/provenance metadata; some command references use quoted placeholders. Describe these publication-only reference and metadata changes explicitly. The unchanged judgments, findings, and numerical results are supported by the publication validation and byte identity.

### Verification

The twelve files passed the documentation checker and the repository manifest/private-URL checker. Direct URL/path inspection found no private-repository URL, reviewer-machine path, or local-path link. The retained `/home/node/app` is a documented container working directory, not a reviewer-machine location. Gitleaks scanned all twelve files (212804 bytes) with zero findings; the whitespace check also passed. No secret was detected.

At 2026-11-11 16:02 UTC, all eight checks on the reviewed head completed successfully: Check Links, Build MkDocs Site, Manifest validation and private-URL policy, Secret scan (gitleaks), Semgrep static analysis, Trivy filesystem scan (report only at M1), and Unit tests for Python 3.11 and 3.12. Runs: [Documentation Build and Check](https://github.com/RCOSDP/RDM-developer-guide/actions/runs/43050442902), [Security Checks](https://github.com/RCOSDP/RDM-developer-guide/actions/runs/43050443092), [Unit Tests](https://github.com/RCOSDP/RDM-developer-guide/actions/runs/43050442763). Trivy retains its report-only role; a green job is not a separate vulnerability acceptance decision.

The inventory in the PR description is correct: osf.io #8 r4/r5, #10 r2, #11 r4, #12 r2/r3, #13 r2; y-websocket #5 r1/r2/r3; ember-osf-web #2 r2; modular-file-renderer #7 r1. The stated pass verdicts for osf.io #11/#13 and y-websocket #5 r3 agree with the retained records and keep their original scopes and remaining integration conditions.

The missing-earlier-record list is exact: osf.io #8 r1–r3, #10 r1, #11 r1–r3, #12 r1, and #13 r1 (nine records). None is present in the supplied original-review directory; each corresponding REV comment remains on its PR. Loss during scratch cleanup is the supplied provenance account; this review verifies the present absence and retained comments, not the past deletion event.

PR #45 head `7d0ba60a8a72f38595680ba0b49cc1d89405b023` added REV's r3 publication version `docs/reviews/2026-11-12_RDM-developer-guide_PR45_Pin_Py313_r3.md`, byte-identical to the issued copy (SHA-256 `762969614e37c65ad40b41cb69f52904d2fd45cea0bd8f0bf3c356bb335b51ca`); no comment was posted on PR #45.

### Byte-identity evidence

The following SHA-256 values identify the committed and issued copies equally; paths are relative to `docs/reviews/`.

```toon
files[12]:
  - file: 2026-11-10_RDM-osf.io-dev2027_PR8_Mandatory_Auth_r4.md
    sha256: baf5a5141f880065f82fca595a25b1b2c18357e1792b8bcf74df33341d58904e
  - file: 2026-11-11_RDM-ember-osf-web-dev2027_PR2_Static_Build_r2.md
    sha256: de75e15ae4f6acad3e6450f809d7395b0739fdafaeb3ae1e832b2b7c37e369f6
  - file: 2026-11-11_RDM-modular-file-renderer-dev2027_PR7_Render_Redirect_r1.md
    sha256: c666eee3133049b265c774f2d43e79f0fc0007eae12d1b0ccf3b9c9be93503bf
  - file: 2026-11-11_RDM-osf.io-dev2027_PR12_File_Editor_Yjs_r2.md
    sha256: bbf9382ddaa7acd995a5940e7fb5bbaf1e7a9e026f8fd554d9d9fbbb161544ee
  - file: 2026-11-11_RDM-osf.io-dev2027_PR12_File_Editor_Yjs_r3.md
    sha256: 4a087cc84ef4ea65310d8baac2f321f3dc593d9f33b7d9bab24b8f1a882a8afe
  - file: 2026-11-11_RDM-osf.io-dev2027_PR13_Django22_r2.md
    sha256: d89602cc93f16e407a97492114d9c5c55247ad252d9eb98816a3a02b0f7b691c
  - file: 2026-11-11_RDM-osf.io-dev2027_PR8_Mandatory_Auth_r5.md
    sha256: 4e269a34f069738b8e4df19e7cde343306faed11feb4026f1c94d38320969b59
  - file: 2026-11-11_RDM-y-websocket-dev2027_PR5_Revocation_Persistence_r1.md
    sha256: 434f37786ca539d9b7eb44fe031f5fa091b575c04ff06ac8dbf49c34c5703099
  - file: 2026-11-11_RDM-y-websocket-dev2027_PR5_Revocation_Persistence_r2.md
    sha256: 1a4a5a200ddbcafce4618aeb3c1ed4196318634dcacc95a6dd7849a12b254ea6
  - file: 2026-11-12_RDM-osf.io-dev2027_PR10_Admin_2FA_r2.md
    sha256: 543034ee9ce5dca26c7079ed31af36bfc626329f56dccd8b1b0bb6ca2c961966
  - file: 2026-11-12_RDM-osf.io-dev2027_PR11_Search_ES8_r4.md
    sha256: d26a1a45b71b640a63346b53d1be706edaf427e4fb3c604115c4f49742cad5d9
  - file: 2026-11-12_RDM-y-websocket-dev2027_PR5_Revocation_Persistence_r3.md
    sha256: 8ecd0c27ea064a9cd4417d6376cdb75e53a319da516dfa6f5fed06c9d64acd37
```

---

<a id="japanese"></a>
## 日本語

[→ To English](#english)

### 判定と範囲

**pass（本文の軽微な訂正2件、非阻害）。** 公開版のファイルに阻害指摘はない。P3 の2件は PR 本文だけを対象とする。これはレビュー判定であり、GitHub の approve やマージ許可ではない。

新規の独立クローンで指定の完全な head を確認した。共通祖先との差分は `docs/reviews/` の Markdown 12件の追加だけで、変更・削除・別ファイルの追加はない。コミット内の各ファイルを対応する発行済み公開版と直接比較し、12件すべてがバイト単位で一致し、`publication-validation.json` の SHA-256 とも一致した。全件が2026-11-12発行の公開版0.2である。公開記録のみのレビューのため、過去のアプリケーション試験は再実行していない。

### 指摘

**R1-01 / P3 — 記載する検査件数を訂正する。** PR 本文の検証節は検査対象を `154` 件としている。この head で `python3 tools/docs_check.py` を実行すると、検査 **166** 件、除外8件、既存の警告38件、エラー0件で、新規レビュー12件の警告は0件となる。検査は `git ls-files` で追跡対象ファイルを列挙するため、154件では追加12件の検査を示せない。件数を訂正し、コミット済みの追加ファイルを検査対象に含めたことを明記する。

**R1-02 / P3 — 公開用変換の範囲を正確に説明する。** PR 本文の方法節は、REV の変更が URL とパスを名前・番号の平文に置き換えたことだけ、としている。実際の発行版にはローカルのガイド参照のリポジトリ相対リンク化、版・来歴メタデータの追記もあり、一部のコマンド参照には引用符付きの代替表示を使う。これらの公開用参照・メタデータの変更を明記する。判定・指摘・数値の保持は、公開版の検証結果とバイト一致により裏付けられている。

### 検証

12件は文書検査とリポジトリの manifest・非公開 URL 検査に合格した。URL・パスの直接確認でも、非公開リポジトリ URL、レビュワの端末のパス、ローカルパスへのリンクは見つからなかった。残る `/home/node/app` は説明対象のコンテナ内作業ディレクトリであり、レビュワの端末の場所ではない。Gitleaks は12件すべて（212804 bytes）を検査して検出0件、空白差分検査も合格した。秘密情報は検出されなかった。

2026-11-11 16:02 UTC 時点で、対象 head の8検査がすべて成功した。対象は Check Links、Build MkDocs Site、Manifest validation and private-URL policy、Secret scan (gitleaks)、Semgrep static analysis、Trivy filesystem scan (report only at M1)、Python 3.11・3.12 の Unit tests である。実行記録: [Documentation Build and Check](https://github.com/RCOSDP/RDM-developer-guide/actions/runs/43050442902), [Security Checks](https://github.com/RCOSDP/RDM-developer-guide/actions/runs/43050443092), [Unit Tests](https://github.com/RCOSDP/RDM-developer-guide/actions/runs/43050442763)。Trivy は報告のみの役割を保持し、ジョブ成功は別途の脆弱性受容判定ではない。

PR 本文の収録一覧は正確で、osf.io #8 r4/r5、#10 r2、#11 r4、#12 r2/r3、#13 r2、y-websocket #5 r1/r2/r3、ember-osf-web #2 r2、modular-file-renderer #7 r1 を含む。osf.io #11/#13 と y-websocket #5 r3 の pass 表示も保存された記録と一致し、元の判定範囲や残る統合条件を変更しない。

過去の欠落一覧も正確で、osf.io #8 r1〜r3、#10 r1、#11 r1〜r3、#12 r1、#13 r1 の9件である。指定の原本レビュー保管先にいずれもなく、各回に対応する REV コメントは各 PR に残っている。scratch 整理で失われたという説明は提供された来歴であり、今回は現時点の不在と残存コメントを確認したもので、過去の削除操作を検証したものではない。

PR #45 head `7d0ba60a8a72f38595680ba0b49cc1d89405b023` は REV の r3 公開版 `docs/reviews/2026-11-12_RDM-developer-guide_PR45_Pin_Py313_r3.md` を追加しており、発行済み版とバイト単位で一致した（SHA-256 `762969614e37c65ad40b41cb69f52904d2fd45cea0bd8f0bf3c356bb335b51ca`）。PR #45 にはコメントしていない。

### バイト一致の証跡

[英語節の SHA-256 一覧](#byte-identity-evidence)は、コミット内と発行済み版の双方に共通する値である。ファイル名は `docs/reviews/` からの相対名である。
