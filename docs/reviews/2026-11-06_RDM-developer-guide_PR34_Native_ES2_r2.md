# PR34 Native Elasticsearch 2 review r2 / ネイティブ Elasticsearch 2 レビュー r2

> **Summary:** The four implementation findings are resolved and all nine checks pass; the PR description still needs the R1-05 correction.
> **概要:** 実装の4指摘は解消し、9検査すべて合格。PR 本文には R1-05 の訂正が残る。

**Jump:** [English](#english) · [日本語](#japanese)

- Version / 版: 0.1 — 2026-11-06. **Learned:** correcting repository evidence does not also correct the PR description, and an image smoke test does not exercise migration of an existing bind-mounted tree. ／ リポジトリの証跡を訂正しても PR 本文は直らず、イメージの起動試験だけでは既存 bind マウントの移行を検証できない。
- Applies to: RCOSDP/RDM-developer-guide PR #34, head `1a8102de7c1d150daefdd931bbbb4cf6c5572b97`.
- Reviewer: REV（担当レビュワ, Codex Astra）.
- Related: [Review index](README.md) · [r1](2026-11-06_RDM-developer-guide_PR34_Native_ES2_r1.md) · [SPEC-06](../spec/06_documentation_conventions.md) · [ADR-07](../decisions/ADR-07_Native_Builds_of_EOL_Middleware.md).
- Used by: [Status board](../status/README.md) · [DEMO-20](../demo/20_core_install_mac_studio.md).

---

<a id="english"></a>
## English

[→ 日本語版へ](#japanese)

### Verdict

**Request changes, documentation only (P3).** R1-01 through R1-04 are resolved at code-review scope. No new P1/P2 finding. R1-05 is partially resolved: both DEMO-20 language halves are corrected, but the current PR description still reports 59 findings on the image itself. This is a review verdict, not a GitHub approval or merge.

### Re-review evidence

- **R1-01 — resolved in implementation.** [The init template](https://github.com/RCOSDP/RDM-developer-guide/blob/4f70cfa6acf3d837e7f33a0ebb4b9369718fe4d4/installer/grdm_dev/templates/elasticsearch_data_init.json) runs the native image with explicit `run_as: "0:0"`; [compose.py](../../installer/grdm_dev/compose.py) applies that user only under the recorded user exception. [hardening.json](../../manifest/hardening.json) grants only `CHOWN`, with a review date and removal milestone. The root filesystem stays read-only, capabilities are otherwise dropped, and no-new-privileges stays enabled. The command recursively assigns the data tree to `1000:1000`, and Elasticsearch waits for successful completion. Rendering tests confirm the image, root user, capability, restart policy and dependency. This addresses fresh host-owned 0755 directories and ordinary uid-101 trees without deleting contents. No Linux migration runtime test was run here; the new image workflow uses a fresh Docker-managed volume and does not test the owner-init service or an existing uid-101 bind mount.
- **R1-02 — resolved.** [MC-15](../../tools/manifest_check.py) checks key presence, rejects empty/malformed objects, uses full-string tag matching, and resolves both context and Dockerfile within the repository. Escaping symlinks are refused; in-repository symlinks are not categorically forbidden. [manifest.parse](../../installer/grdm_dev/manifest.py) rejects an empty or incomplete object instead of silently selecting the base image. Added negative tests pass. Independent temporary-directory probes also confirmed rejection of an escaping Dockerfile symlink and `prebuilt_image` coexistence; those two cases are not explicit additions in the committed tests.
- **R1-03 — resolved.** [Dockerfile](../../installer/images/elasticsearch2/Dockerfile) declares OCI base name, base digest and version labels. Its default base digest matches the manifest. [build.py](../../installer/grdm_dev/build.py) passes `base_image_digest` through `--label`; the unit test asserts the actual argument. The image workflow also checks that the built image carries a `sha256:` base label. That smoke assertion checks presence, not equality with the manifest; equality was checked statically for this head.
- **R1-04 — resolved.** [Image recipes](../../.github/workflows/images.yml) uses SHA-pinned actions, enumerates declared recipes, builds `linux/amd64` and `linux/arm64` without pushing, then loads and smoke-tests Elasticsearch on amd64. [Run 42198484299](https://github.com/RCOSDP/RDM-developer-guide/actions/runs/42198484299) passed in 51 seconds. Its logs show both target stages, successful tarball verification/build, and the successful amd64 smoke step. All nine PR checks pass. arm64 runtime startup is outside this workflow's evidence.
- **R1-05 — partially resolved.** [DEMO-20](../demo/20_core_install_mac_studio.md) lines 439 and 866 now separate 58 image findings (2 HIGH, 52 MEDIUM, 4 LOW) from one LOW Dockerfile finding. SPEC-02, SPEC-03 and ADR-07 now describe the retained owner-init service and exception consistently in both languages.

### Remaining correction: R2-01 (P3)

Update the [PR #34 description](https://github.com/RCOSDP/RDM-developer-guide/pull/34): its measurement section still says “59” image findings (HIGH 2 / MEDIUM 52 / LOW 5), and its change list still says `elasticsearch_data_init` and both exceptions were removed. Report 58 image findings plus one Dockerfile LOW, retain the owner-init service and its exception, and remove only the Elasticsearch service's exception. Refresh the test counts to 362 installer / 92 tools. This completes R1-05 and makes the summary match the reviewed change.

Non-blocking editorial remnants: the Dockerfile introductory comment still says “no owner-init container”, the Elasticsearch template note ends by claiming replacement of its owner-init one-shot, and SPEC-02 still describes Elasticsearch as emulated in the `osf_init` paragraph. These should be aligned with the corrected normative paragraphs. The r1 editorial notes about index formatting/version headers were not the implementation acceptance gate for r2.

### Validation and limits

Executed from the reviewed worktree root:

```sh
PYTHONPATH=installer python3 -m unittest discover -s installer/tests
python3 -m unittest discover -s tools/tests
python3 tools/manifest_check.py
python3 tools/docs_check.py
gh pr checks 34 --repo RCOSDP/RDM-developer-guide
```

```toon
checks[5]{check,result}:
  installer,"362 run; OK; 10 skipped"
  tools,"92 run; OK"
  manifest_check,"PASSED; zero findings"
  docs_check,"PASSED; 22 existing non-failing glossary warnings"
  github,"9 checks pass; Image recipes included"
```

The newly written, untracked r2 file was additionally checked directly with `tools.docs_check.check_file`, because the normal command only enumerates tracked files. No running-stack change, local Docker build, commit, push, approval, merge or close was performed. The earlier run-21 cold-start evidence was not rerun and remains evidence for its recorded revision, not an exact-head full installation.

---

<a id="japanese"></a>
## 日本語

[→ To English](#english)

### 判定

**要修正。ただし文書のみ（P3）。** R1-01〜R1-04 はコードレビューの範囲で解消。新たな P1/P2 はない。R1-05 は部分解消で、DEMO-20 の英和は直ったが、現在の PR 本文は依然としてイメージ自体の指摘を59件としている。これはレビューの判定であり、GitHub 上の承認やマージではない。

### 再レビューの根拠

- **R1-01 — 実装修正を確認。** [初期化テンプレート](https://github.com/RCOSDP/RDM-developer-guide/blob/4f70cfa6acf3d837e7f33a0ebb4b9369718fe4d4/installer/grdm_dev/templates/elasticsearch_data_init.json) はネイティブイメージを明示の `run_as: "0:0"` で実行する。[compose.py](../../installer/grdm_dev/compose.py) は記録された user 例外がある場合だけそのユーザーを適用する。[hardening.json](../../manifest/hardening.json) は `CHOWN` のみを許し、見直し日と除去する節目を持つ。ルートは読み取り専用、他の capability は除去、no-new-privileges は有効のまま。データの木を再帰的に `1000:1000` にし、Elasticsearch は正常終了を待つ。生成試験でイメージ・root・capability・再起動方針・依存関係を確認した。ホスト所有の新規0755ディレクトリと通常の uid-101 の木を、内容を削除せず扱える実装になった。ただし Linux 上の移行実行試験はしていない。新 workflow は Docker 管理の新規ボリュームを使い、所有者初期化サービスや既存 uid-101 の bind マウントは試さない。
- **R1-02 — 解消。** [MC-15](../../tools/manifest_check.py) はキーの存在を見て空・不正な object を拒否し、タグを全文一致で検査し、context と Dockerfile の両方を解決してリポジトリ境界を確認する。外部へ出る symlink は拒否するが、内部への symlink まで一律禁止する仕様ではない。[manifest.parse](../../installer/grdm_dev/manifest.py) は空または不完全な object を拒否し、黙ってベースイメージを選ばない。追加の負例試験は合格。一時ディレクトリによる独立検査でも、外へ出る Dockerfile symlink と `prebuilt_image` 併用の拒否を確認した。この2ケースはコミット済み試験には明示的に追加されていない。
- **R1-03 — 解消。** [Dockerfile](../../installer/images/elasticsearch2/Dockerfile) に OCI の base name・base digest・version ラベルがある。既定のベース digest は manifest と一致する。[build.py](../../installer/grdm_dev/build.py) は `base_image_digest` を `--label` に渡し、単体試験が実際の引数を検査する。イメージ workflow も生成物に `sha256:` の base ラベルがあることを確かめる。この起動試験の assertion は存在確認であり manifest との一致までは見ない。一致は今回の head の静的確認で検証した。
- **R1-04 — 解消。** [Image recipes](../../.github/workflows/images.yml) は SHA 固定の action を使い、宣言されたレシピを列挙し、push せず `linux/amd64` と `linux/arm64` を組み、amd64 の Elasticsearch をロードして起動試験する。[実行42198484299](https://github.com/RCOSDP/RDM-developer-guide/actions/runs/42198484299) は51秒で成功。ログで両対象段、tarball 検証・ビルド、amd64 の起動試験成功を確認した。PR の9検査すべて合格。arm64 の実行時起動はこの workflow の証明範囲外。
- **R1-05 — 部分解消。** [DEMO-20](../demo/20_core_install_mac_studio.md) の439・866行はイメージ58件（HIGH 2・MEDIUM 52・LOW 4）と Dockerfile の LOW 1件を分けた。SPEC-02・SPEC-03・ADR-07 も所有者初期化サービスと例外の維持を英和で対応して記載している。

### 残る訂正: R2-01（P3）

[PR #34 本文](https://github.com/RCOSDP/RDM-developer-guide/pull/34)を更新すること。計測節はまだイメージ「59件」（HIGH 2・MEDIUM 52・LOW 5）で、変更一覧も `elasticsearch_data_init` と両例外を削除したとしている。イメージ58件＋Dockerfile の LOW 1件に分け、所有者初期化サービスとその例外は維持し、Elasticsearch サービス自身の例外だけを除去したとする。試験数も installer 362件／tools 92件へ更新する。これで R1-05 が完了し、要約がレビュー対象の変更と一致する。

非阻害の編集残件: Dockerfile 冒頭の “no owner-init container”、Elasticsearch テンプレートの note 末尾の初期化サービスを置き換えたという記述、SPEC-02 の `osf_init` 段落で Elasticsearch をエミュレーション下とする記述も、訂正済みの規範的段落に合わせたい。r1 の索引整形・版ヘッダーの編集注は、r2 の実装受入ゲートとはしていない。

### 検証と限界

レビュー対象 worktree のルートで実行した。

```sh
PYTHONPATH=installer python3 -m unittest discover -s installer/tests
python3 -m unittest discover -s tools/tests
python3 tools/manifest_check.py
python3 tools/docs_check.py
gh pr checks 34 --repo RCOSDP/RDM-developer-guide
```

```toon
checks[5]{check,result}:
  installer,"362件実行・OK・10件skip"
  tools,"92件実行・OK"
  manifest_check,"PASSED・指摘ゼロ"
  docs_check,"PASSED・既存の非阻害用語警告22件"
  github,"9検査合格・Image recipes を含む"
```

新規の未追跡 r2 ファイルは `tools.docs_check.check_file` で直接追加検査した。通常コマンドは追跡済みファイルだけを列挙するためである。稼働スタック変更・ローカル Docker build・commit・push・承認・merge・close は行っていない。第21回のコールドスタートは再実行しておらず、記録された版の証跡であって今回の head での完全インストールの証明ではない。

---

## Glossary / 用語

| Term | English note | 日本語注 |
|---|---|---|
| UID | Number identifying a file owner. | ファイル所有者を表す番号。 |
| Bind mount | A host directory made visible inside a container. | ホストのディレクトリをコンテナ内に見せる仕組み。 |
| Digest | Fingerprint identifying exact image content. | イメージの内容を特定する指紋。 |
| Symlink | A filesystem entry that points to another path. | 別のパスを指す項目。 |
| Smoke test | A short check that a program starts and responds. | 起動して応答することを見る短い試験。 |
| P3 | Lower-priority correction. | 低優先度の訂正。 |
