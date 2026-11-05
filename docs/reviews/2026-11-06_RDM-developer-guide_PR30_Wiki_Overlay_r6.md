# PR30 Wiki Overlay Review r6 / Wiki オーバーレイレビュー r6

> **Summary:** R5-01 is resolved by a justified, single-rule exception on one temporary test fixture line. All eight CI checks pass; no blocking findings remain in this re-review.
> **概要:** 一時的な試験準備の一行に対する根拠付きの単一規則例外で R5-01 は解消。CI 全8件が成功し、今回の再レビューに阻害指摘は残らない。

**Jump:** [English](#english) · [日本語](#japanese)

- Version / 版: 0.1 — 2026-11-06. **Learned:** an owner-only directory fixture can justify a line-local scanner exception while retaining the permission-preservation regression test. ／ 所有者だけが使う試験用ディレクトリには、権限維持の回帰試験を残したまま、一行限定の検査例外を正当化できる。
- Applies to: [PR #30](https://github.com/RCOSDP/RDM-developer-guide/pull/30), head `3bb0d88762ec78105f7465b5325afbe0cb4b96a7`; REV（担当レビュワ, Codex Astra）.
- Related: [Review index](README.md) · [r5](2026-11-06_RDM-developer-guide_PR30_Wiki_Overlay_r5.md) · [SPEC-06](../spec/06_documentation_conventions.md) · [ADR-06](../decisions/ADR-06_Wiki_Frontend_Overlay.md).
- Used by: [DEMO-20](../demo/20_core_install_mac_studio.md) · [Status board](../status/README.md).

---

<a id="english"></a>
## English

[→ 日本語版へ](#japanese)

### Verdict and scope

**Pass — R5-01 closed; no blocking findings.** This is the reviewer's verdict, not a GitHub approval or merge. The reviewed change from r5 head `b9a26c707b3798f1d569ba659826f4d689ee8c2b` consists of the r5 record and one comment replacement at `installer/tests/test_compose.py:926`. Product code and test execution behavior are unchanged.

The inline `nosemgrep` annotation names only `python.lang.security.audit.insecure-file-permissions.insecure-file-permissions`. It applies to the single `os.chmod(vol, 0o700)` fixture statement, with a reason explaining the simulated mode after ownership transfer. There is no blanket suppression or scanner configuration change. `vol` is created inside `tempfile.TemporaryDirectory()`; 0700 permits only the owner to read, write and traverse it. The test still asserts that rerender never calls chmod for an existing directory and preserves 0700. The fixture simulates the lifecycle; it does not actually transfer ownership to another user. The rationale is therefore accurate within that stated simulation.

### Validation

Commands executed from the review worktree root:

```sh
PYTHONPATH=installer python3 -m unittest discover -s installer/tests
python3 -m unittest discover -s tools/tests
python3 tools/manifest_check.py
python3 tools/docs_check.py
PYTHONPATH=installer:installer/tests python3 -m unittest -v test_compose.ComposeRenderTests.test_docker_compose_config_accepts_the_rendered_file test_compose.ComposeRenderTests.test_idempotent_rerun_reports_unchanged test_compose.VolumeDirOwnershipTests
git diff --check
gh pr checks 30 --repo RCOSDP/RDM-developer-guide
gh run view 42127071522 --repo RCOSDP/RDM-developer-guide --json headSha,conclusion,status
```

Observed review results, not canonical manifest data:

```toon
validation[7]{check,result,detail}:
  installer,pass,345 tests; 10 skipped
  tools,pass,89 tests
  manifest_check,pass,zero findings
  docs_check,pass,88 checked; 8 exempt; 19 warnings
  targeted_tests,pass,4 tests; none skipped; read-only compose config included
  whitespace,pass,git diff --check
  CI,pass,all 8 checks on reviewed head; Semgrep included
```

The eight passing checks are Build MkDocs Site, Check Links, Manifest validation and private-URL policy, Secret scan (gitleaks), Semgrep static analysis, Trivy filesystem scan (report only at M1), and Unit tests (installer, tools) on Python 3.11 and 3.12. The [security run](https://github.com/RCOSDP/RDM-developer-guide/actions/runs/42127071522) completed successfully with the reviewed head; its [Semgrep job](https://github.com/RCOSDP/RDM-developer-guide/actions/runs/42127071522/job/127593858516) passed. The [test run](https://github.com/RCOSDP/RDM-developer-guide/actions/runs/42127071518) and [documentation run](https://github.com/RCOSDP/RDM-developer-guide/actions/runs/42127071544) supply the other checks. The untracked r6 record is checked separately using `tools.docs_check.check_file`.

### Limits

The r5 acceptance limits remain: no real Linux ownership-transfer test, concurrent provisioning, container startup or browser/C4 acceptance was performed. Read-only Compose parsing changes no Docker state. This comment-only fix does not reopen the resolved normal sequential lifecycle finding R2-01. The 19 existing documentation warnings remain non-failing. Only this review record and the requested PR comment are written; no approve, merge, close, commit or push is performed.

---

<a id="japanese"></a>
## 日本語

[→ To English](#english)

### 判定と範囲

**合格 — R5-01 解消、阻害指摘なし。** これはレビュワの判定であり、GitHub の承認・マージ操作ではない。r5 の head `b9a26c707b3798f1d569ba659826f4d689ee8c2b` からの変更は、r5 記録の追加と `installer/tests/test_compose.py:926` のコメント一箇所の置換だけ。本体コードと試験の実行動作は変わっていない。

行内の `nosemgrep` は `python.lang.security.audit.insecure-file-permissions.insecure-file-permissions` だけを指定する。対象は試験準備の `os.chmod(vol, 0o700)` 一文で、所有権移転後のモードを模擬する理由が付いている。一括抑制や検査設定の変更はない。`vol` は `tempfile.TemporaryDirectory()` 内に作られ、0700 は所有者だけに読取り・書込み・探索を許す。既存ディレクトリの再 render では chmod を呼ばず、0700 を維持する検証も残っている。試験はライフサイクルを模擬するもので、実際に別利用者へ所有権を移転してはいない。注記の理由は、その模擬という範囲で正確である。

### 検証

実行コマンドと結果一覧は英語部に記載。installer は345件実行・成功（10件 skip）、tools は89件成功。manifest は指摘0、docs は88件検査・8例外・19警告で成功。個別4試験は skip なしで成功し、読取り専用 compose config を含む。空白検査も成功し、未追跡の r6 記録は `tools.docs_check.check_file` で別途検査する。

CI は対象 head の全8件が成功。内訳は MkDocs 構築、リンク検査、manifest・非公開 URL 方針、gitleaks、Semgrep、Trivy（M1 では報告のみ）、Python 3.11 と3.12 の単体試験。[セキュリティ実行](https://github.com/RCOSDP/RDM-developer-guide/actions/runs/42127071522) の head 一致と成功終了、および [Semgrep ジョブ](https://github.com/RCOSDP/RDM-developer-guide/actions/runs/42127071522/job/127593858516) の成功を確認した。他の検査は[試験実行](https://github.com/RCOSDP/RDM-developer-guide/actions/runs/42127071518)と[文書実行](https://github.com/RCOSDP/RDM-developer-guide/actions/runs/42127071544)に対応する。

### 限界

r5 の受入範囲の限界は継続する。Linux 上の実際の所有権移転、同時準備処理、コンテナ起動、ブラウザ/C4 受入は実施していない。読取り専用の Compose 構文検査は Docker の状態を変更しない。コメントだけの修正であり、通常の逐次実行について解決済みの R2-01 を再開する理由はない。既存の文書警告19件は失敗扱いではない。指定のレビュー記録と PR コメントだけを書き、approve・merge・close・commit・push は行わない。

---

## Glossary / 用語

| Term | English note | 日本語注 |
|---|---|---|
| CI | Automatic checks for each change. | 変更ごとに走る自動検査。 |
| Semgrep / nosemgrep | Source-code scanner / a comment suppressing a specified finding. | ソース検査器／指定した指摘を抑制するコメント。 |
| Fixture | Temporary setup used by a test. | 試験のための一時的な準備。 |
| Mode 0700 / chmod | Owner-only directory permissions / the operation setting permissions. | 所有者専用のディレクトリ権限／権限を設定する操作。 |
| Regression test | A test that catches a previously fixed bug returning. | 修正済み不具合の再発を検知する試験。 |
| C4 | Wiki collaborative-editing acceptance scenario. | Wiki 共同編集の受入試験。 |
