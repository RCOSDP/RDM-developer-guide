# REV PR #28 CAS prebuilt review r2 / CAS 配布イメージレビュー r2

> **Summary:** Both r1 findings are resolved. The corrected explanation matches the implementation, and all eight hosted checks pass on the reviewed revision.
> **概要:** r1 の指摘2件は解決した。修正した説明は実装と一致し、対象の版で遠隔検査8件すべての成功を確認した。

**Jump:** [English](#english) · [日本語](#japanese)

- Version / 版: 0.1 — 2026-11-06. **Learned:** a history scan can detect another fetched branch, so its failure must be traced to the scanned revision and exact exception before judging a change. ／ 履歴検査は取得した別ブランチも検出するため、変更を判定する前に検出した版と限定的な除外条件を追う必要がある。
- Applies to: [PR #28](https://github.com/RCOSDP/RDM-developer-guide/pull/28) (a proposed change / 変更提案), reviewed head (revision / 対象の版) `e2cd59d4662b81d9ebf653d6b99a7671821bf79f`.
- Reviewer: REV（担当レビュワ, Codex Astra）.
- Related: [Review index](README.md) · [r1](2026-11-06_RDM-developer-guide_PR28_Cas_Prebuilt_r1.md) · [SPEC-06](../spec/06_documentation_conventions.md) · [DEMO-20](../demo/20_core_install_mac_studio.md) · [Shared glossary](../reference/REF-01_Glossary.md).
- Used by: [Status board](../status/README.md).

---

<a id="english"></a>
## English

[→ 日本語版へ](#japanese)

### Verdict

**Accept — R1 and R2 resolved; no remaining blocking findings in this re-review.** This is a written verdict, not a GitHub approval. CI (automatic checks on a change; [glossary](../reference/REF-01_Glossary.md)) is 8/8 passing at the reviewed head.

### R1: implementation and wording agree

Both run-3 paragraphs in DEMO-20 now describe a prebuilt image (a program packaged beforehand) pulled for the component platform, a `prebuilt` build-report row, and the same reference written as Compose `image:` without local retagging. Compose is the tool that connects application containers; a container is a box holding a program and its dependencies.

In `installer/grdm_dev/build.py`, `component_platforms` selects the requested or configured platform, `pull_argv` builds the pull command, and the prebuilt branch of `run` records the original reference and skips the source-build branch. Its successful non-push status is `prebuilt`. In `installer/grdm_dev/manifest.py`, `Component.image_reference` returns `prebuilt_image` directly and `services_for_profile` assigns it to the service. In `installer/grdm_dev/compose.py`, `render_service` writes `svc.image` as `image:`. There is no retagging in that path. The English and Japanese corrections match this behavior.

### R2: history-scan explanation and correction confirmed

The historical finding recorded in r1 is `docs/guides/storage-addon/README.legacy.md:224` at `b8594c363a990a3b43119a0a29229766e24b4a59`. Fetching that file confirms the documented public reCAPTCHA test site key in the `recaptchaSiteKey` field. The value is not repeated here. The commit appears in [PR #27](https://github.com/RCOSDP/RDM-developer-guide/pull/27), whose source branch was `docs/port-legacy-prs`. Comparing that commit with the old PR #28 head `cc2e9c37fa891697e08e9ef24bf35a41308bb427` returns diverged histories; it was not an ancestor of that old head.

`.github/workflows/security.yml` checks out with `fetch-depth: 0` and runs gitleaks v8.21.2 (a possible-secret detector) with `detect --source . --config .gitleaks.toml --redact --exit-code 1`, without restricting `--log-opts`. The version's `sources/git.go`, fetched through `gh`, defaults to `git log -p -U0 --full-history --all`. Thus the scan covers all fetched refs (names pointing to revisions), not only the PR's changed files or its own ancestry. The old failed job reports 118 commits scanned and one finding. This supports the explanation that another fetched branch caused the earlier failure.

PR #27 merged at `2026-11-05T20:49:37Z` as `3b42699fdb7f237db641391297b7ec66c8744ce2`. That commit is the second parent of the reviewed PR #28 merge commit. Its `.gitleaks.toml` contains the exact test-value exception with `regexTarget = "line"`, start/end anchors, the named field, optional surrounding whitespace and an optional comma. Default rules remain enabled. The exception is line-specific, not path-scoped; it does not exempt a whole file, arbitrary keys, or extra fields on that line. The [PR #27 r3 record](2026-11-06_RDM-developer-guide_PR27_Legacy_Ports_r3.md) also records its positive and negative expression checks.

### Verification and limits

The eight passing checks are documentation build, links, manifest/private-URL policy, gitleaks, Semgrep, report-only Trivy, and unit tests on Python 3.11 and 3.12. The [security run](https://github.com/RCOSDP/RDM-developer-guide/actions/runs/42107195852) reports `success` for the exact reviewed head. Trivy passing remains report-only and does not assert that no vulnerabilities exist.

From any directory with authenticated `gh`, reproduce the hosted-check inspection:

```sh
gh pr checks 28 --repo RCOSDP/RDM-developer-guide
gh api repos/RCOSDP/RDM-developer-guide/actions/runs/42107195852 --jq '{head_sha,conclusion}'
```

Expected: eight `pass` rows and exit 0; the run reports the reviewed head and `success`. Repository content and hosted evidence were inspected with `gh`; local tests and installation were not rerun. The r1 registry verification and runtime limitations remain applicable. No Docker state was changed. Recording the review in version control and the integration decision remain with the coordinator.

---

<a id="japanese"></a>
## 日本語

[→ To English](#english)

### 判定

**受入可能 — R1・R2 は解決し、今回の再レビュー範囲に阻害指摘は残らない。** 文書上の判定であり、GitHub の承認操作ではない。対象の版で CI（変更に対する自動検査。[用語集](../reference/REF-01_Glossary.md)）8件すべての成功を確認した。

### R1: 実装と記述の一致

DEMO-20 の第3回の英和両段落は、prebuilt image（あらかじめ組み立てたプログラムの配布物）を部品の対象環境向けに取得し、ビルド報告を `prebuilt` とし、同じ参照を Compose の `image:` に書くと説明している。ローカルでタグを付け直すとはしていない。Compose はアプリのコンテナをつなぐ道具であり、コンテナはプログラムと必要な部品を入れた箱である。

`installer/grdm_dev/build.py` の `component_platforms` は指定または設定した対象環境を選び、`pull_argv` は取得コマンドを作る。`run` の prebuilt 分岐は元の参照を報告に記録し、ソースからのビルド分岐を通らない。push を指定しない成功時の状態は `prebuilt` である。`installer/grdm_dev/manifest.py` の `Component.image_reference` は `prebuilt_image` を直接返し、`services_for_profile` がサービスに設定する。`installer/grdm_dev/compose.py` の `render_service` は `svc.image` を `image:` に書く。この経路にタグ付け直しはなく、英和の修正文は動作と一致する。

### R2: 履歴検査の説明と修正を確認

r1 が記録した検出箇所は、`b8594c363a990a3b43119a0a29229766e24b4a59` の `docs/guides/storage-addon/README.legacy.md:224` である。その版のファイルを取得し、`recaptchaSiteKey` 欄に説明済みの公開 reCAPTCHA テスト用サイトキーがあると確認した。値は転載しない。このコミットは、元ブランチが `docs/port-legacy-prs` の [PR #27](https://github.com/RCOSDP/RDM-developer-guide/pull/27) に含まれる。PR #28 の旧 head `cc2e9c37fa891697e08e9ef24bf35a41308bb427` との比較は履歴の分岐を示し、その旧 head の祖先ではなかった。

`.github/workflows/security.yml` は `fetch-depth: 0` で取得し、gitleaks v8.21.2（秘密情報の疑いを探す道具）を `detect --source . --config .gitleaks.toml --redact --exit-code 1` で実行する。`--log-opts` による制限はない。`gh` で取得した同版の `sources/git.go` は既定で `git log -p -U0 --full-history --all` を使う。そのため PR の変更ファイルや祖先だけでなく、取得した全参照（版を指す名前）の履歴が走査対象になる。旧失敗ジョブも118コミット走査・1件検出を記録している。取得した別ブランチが以前の失敗を起こしたという説明と整合する。

PR #27 は `2026-11-05T20:49:37Z` に `3b42699fdb7f237db641391297b7ec66c8744ce2` として統合された。このコミットは、今回の PR #28 の対象マージコミットの第2親である。対象の `.gitleaks.toml` は `regexTarget = "line"`、行頭・行末の固定、欄名と公開テスト値の完全指定を持つ。前後の空白とカンマだけが任意であり、既定の検出規則も有効なままである。除外は行に限定され、パス限定ではない。ファイル全体、任意の鍵、同じ行の追加欄を除外しない。[PR #27 r3 記録](2026-11-06_RDM-developer-guide_PR27_Legacy_Ports_r3.md) にも、一致すべき行と一致すべきでない行の検証がある。

### 検証と限界

成功した8件は、文書ビルド、リンク、マニフェスト・非公開 URL 方針、gitleaks、Semgrep、報告専用の Trivy、Python 3.11・3.12 の単体テストである。[セキュリティ実行](https://github.com/RCOSDP/RDM-developer-guide/actions/runs/42107195852) は対象 head そのもので `success` となっている。Trivy は報告専用のままであり、成功は脆弱性がないという意味ではない。

認証済みの `gh` が使える任意のディレクトリから遠隔検査を確認できる。

```sh
gh pr checks 28 --repo RCOSDP/RDM-developer-guide
gh api repos/RCOSDP/RDM-developer-guide/actions/runs/42107195852 --jq '{head_sha,conclusion}'
```

期待結果は8行の `pass` と終了0、実行結果の対象 head 一致と `success` である。リポジトリの内容と遠隔の証拠は `gh` で確認し、ローカルテストや実機導入は再実行していない。r1 の配布先検証と実行時の未検証事項は引き続き適用される。Docker の状態変更は行っていない。レビューの版管理への記録と統合判断は調整者に残る。

## Glossary / 用語

| Term | English note | 日本語注 |
|---|---|---|
| Prebuilt image | A program packaged beforehand. | あらかじめ組み立てたプログラムの配布物。 |
| CI | Automatic checks on a proposed change. | 変更提案に対する自動検査。 |
| Ref | A name pointing to a revision. | 版を指す名前。 |
| Allowlist | Explicit exceptions to a check. | 検査から明示的に除く条件。 |
| Retagging | Attaching another image name. | イメージに別の名前を付けること。 |
