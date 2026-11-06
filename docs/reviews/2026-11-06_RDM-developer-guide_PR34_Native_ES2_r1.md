# PR34 Native Elasticsearch 2 review r1 / ネイティブ Elasticsearch 2 レビュー r1

> **Summary:** Request changes: the native recipe improves cold starts, but volume ownership, manifest validation, provenance labels and recipe CI need fixes.
> **概要:** 要修正。ネイティブ化はコールドスタートを改善するが、ボリューム所有権、manifest 検証、出自ラベル、レシピ CI に修正が必要。

**Jump:** [English](#english) · [日本語](#japanese)

- Version / 版: 0.1 — 2026-11-06. **Learned:** a successful fresh Docker Desktop run does not validate Linux volume ownership or malformed manifest inputs. ／ Docker Desktop の新規起動成功では Linux のボリューム所有権や不正な manifest 入力を検証できない。
- Applies to: RCOSDP/RDM-developer-guide PR #34, head `340eca174f0582d1d178038f2546a4aa58b8ec86`, base `f37a02933394e9fbb3e4bf83b5d114117bfaa92e`.
- Reviewer: REV（担当レビュワ, Codex Astra）.
- Related: [Review index](README.md) · [ADR-07](../decisions/ADR-07_Native_Builds_of_EOL_Middleware.md) · [SPEC-01](../spec/01_manifest.md) · [SPEC-03](../spec/03_security_gate.md) · [SPEC-06](../spec/06_documentation_conventions.md).
- Used by: [Status board](../status/README.md) · [DEMO-20](../demo/20_core_install_mac_studio.md).

---

<a id="english"></a>
## English

[→ 日本語版へ](#japanese)

### Verdict and findings

**Request changes.** No P1 finding. R1-01 through R1-04 are P2; R1-05 is P3. No approval, merge, commit, push or running-stack change was performed.

#### R1-01 (P2): Preserve write access when changing the data owner

[elasticsearch.json](../../installer/grdm_dev/templates/elasticsearch.json), lines 10–23, removes the owner-init dependency and switches to uid 1000. However, `compose.py::_ensure_volume_dir` creates host-owned directories with mode 0755 and leaves existing directories untouched. On Linux, an existing PR #33 data tree owned by uid 101 cannot be written by uid 1000; a fresh install by a host user other than uid 1000 also fails. Image-layer `COPY --chown` cannot change the bind-mounted tree. This regresses the ownership fix that PR #33 supplied, regardless of the similar existing ES6 assumption. Provide safe provisioning/migration for the actual mounted data and verify both existing uid-101 data and fresh non-1000 host ownership without deleting data. Run 21 on Docker Desktop does not exercise Linux ownership enforcement; no Linux runtime reproduction was attempted here.

#### R1-02 (P2): Validate presence and resolved containment of image_build

[manifest_check.py](../../tools/manifest_check.py), lines 522–536, accepts these independently reproduced invalid inputs with **zero findings**:

- `image_build: {}` skips MC-15 entirely. `manifest.parse(...).component('elasticsearch2').image_reference()` then returns the Temurin base image, and the component is no longer built as Elasticsearch.
- A tag containing a trailing newline (`"valid\n"`) passes `re.match(...$)` and produces an invalid image reference.
- A context named `escape` that is a symlink to a temporary directory outside the repository, containing a Dockerfile, passes the lexical path check and `is_file()`. This defeats the promised repository-local context boundary; the same issue applies to a symlinked Dockerfile.

Check key presence rather than truthiness, use full-string tag validation, and resolve both context and Dockerfile against the actual repository root before accepting them. Add negative tests for these cases, absolute/parent paths, prebuilt exclusivity and missing notes. The symlink reproduction used isolated temporary directories and a patched checker root; no repository symlink or Docker build was created.

#### R1-03 (P2): Record the base digest in the resulting image

[Dockerfile](../../installer/images/elasticsearch2/Dockerfile), lines 32–40, and `build.py::buildx_argv` set no base-image digest label. SPEC-03 §3.4 explicitly requires locally built images to carry it. Read-only `docker image inspect grdm-dev/elasticsearch2:2.4.6-1` confirms that the image has component/recipe labels and inherited Ubuntu labels, but no Temurin base digest. Put the actual pinned base digest in an image label and test/inspect the resulting value; the manifest entry alone does not satisfy the image provenance requirement.

#### R1-04 (P2): Implement the recipe build checks promised by ADR-07

[ADR-07 §4](../decisions/ADR-07_Native_Builds_of_EOL_Middleware.md#english) requires CI builds of `image_build` components on amd64 and arm64. The repository workflows only run Python/package checks, docs and security filesystem checks; all eight PR checks can pass without building this Dockerfile. The build unit tests use a fake runner and a `FROM scratch` fixture, so they cannot catch a broken download, digest or architecture-specific recipe. Add CI execution of the actual recipe for both targets with recorded results, or explicitly record an approved temporary deferral and its gate/owner. The PR body's manual dual-architecture build claim is not an automated regression check; this review did not rebuild either target.

#### R1-05 (P3): Separate image findings from Dockerfile findings

[DEMO-20 run 21](../demo/20_core_install_mac_studio.md#english) and the PR body call 59 findings (2 HIGH, 52 MEDIUM, 5 LOW) findings of the native image itself. In the supplied `scan_latest.json`, the image location `grdm-dev/elasticsearch2:2.4.6-1` accounts for **58** (2 HIGH, 52 MEDIUM, 4 LOW); the remaining LOW belongs to the repository Dockerfile scan (`component: installer/images/elasticsearch2/Dockerfile`). Correct both language halves and the PR body, or explicitly label 59 as image-plus-recipe findings. Overall Trivy totals are correct.

### Validation and scope

The required commands were run from the reviewed worktree:

```sh
PYTHONPATH=installer python3 -m unittest discover -s installer/tests
python3 -m unittest discover -s tools/tests
python3 tools/manifest_check.py
python3 tools/docs_check.py
gh pr checks 34 --repo RCOSDP/RDM-developer-guide
```

```toon
checks[5]{check,result}:
  installer,"361 run; OK; 10 skipped"
  tools,"91 run; OK"
  manifest_check,"PASSED; zero manifest/policy findings"
  docs_check,"PASSED; 22 non-failing glossary warnings"
  github,"8 checks pass"
```

A separate fake-runner failure of the native image build returned exit **30**. Local/registry tagging and `--push` behavior match ADR-07. Component image references and service origin `image` are wired correctly for valid inputs. Compose uses uid 1000, read-only root, logs tmpfs and the host platform, without an amd64 override. Active installer/manifest/spec references to the deleted one-shot are removed; remaining mentions describe history or assert its absence.

The Dockerfile pins both FROM bases, verifies the official tarball SHA-256 before extraction, fetches on `$BUILDPLATFORM`, and has no final-stage RUN or plugin installation. The final stage uses uid 1000 and explicit writable mounts. The fetch-stage apt packages and Dockerfile syntax frontend are not themselves content-pinned, so this is not a claim of completely immutable build tooling. No private code, private URL or secret was found in the new recipe/configuration; the public-repository policy scan passed. JNA arm64 limitations are disclosed. ADR-07 English/Japanese decisions agree and its anchors, Jump, version and glossary are present.

The supplied `install-run21-coldstart-native-es.log` starts at 04:53:51 UTC and ends at 05:24:34 with all nine steps and overall exit 0: 30 minutes 43 seconds. The scan report is dated 05:24:33, baseline/gate pass, tools successful with 22/4/1/3 targets, and Trivy totals 1769/8030/9550/3676 for CRITICAL/HIGH/MEDIUM/LOW. Its commit field is `5bde10e`, not this PR head; it is run evidence, not independent proof of an exact-head rerun. Fresh-volume preparation and six-second ES startup are documented operator observations, not independently reproduced here.

The checked status board is **0.8**, not the requested 0.9; its cold-start row agrees with the supplied log and acceptance remains open. SPEC-02 §4 and SPEC-03 §3.3 remove the obsolete service/exception in both languages; both README indexes link ADR-07. Minor editorial cleanup remains: the decisions index adds a fourth status cell to a three-column table and still reserves ADR-07 for a future branching decision; modified root README/SPEC-02/SPEC-03 headers were not version-bumped as SPEC-06 §6 requests. Historical review references should remain historical rather than being erased.

---

<a id="japanese"></a>
## 日本語

[→ To English](#english)

### 判定と指摘

**要修正。** P1 はなし。R1-01〜R1-04 は P2、R1-05 は P3。承認・マージ・コミット・push・稼働スタックの変更は行っていない。

#### R1-01 (P2): データ所有者変更後も書込可能にする

[elasticsearch.json](../../installer/grdm_dev/templates/elasticsearch.json) 10〜23 行は所有者初期化への依存を削除し、uid 1000 に切り替える。しかし `compose.py::_ensure_volume_dir` はホスト所有・0755 のディレクトリを作り、既存ディレクトリには手を加えない。Linux では PR #33 で uid 101 所有になったデータへ uid 1000 は書き込めず、新規導入でもホストの uid が 1000 以外なら失敗する。イメージの `COPY --chown` では bind mount の所有権は直らない。ES6 に同様の前提があっても、PR #33 の所有権修正を失う点は変わらない。実際のマウント先を安全に準備・移行し、uid 101 の既存データと uid 1000 以外のホストによる新規導入を、データ削除なしで検証すること。Docker Desktop の第21回では Linux の所有権強制を検証できず、本レビューでも Linux 実機再現はしていない。

#### R1-02 (P2): image_build の存在と解決後のパス境界を検証する

[manifest_check.py](../../tools/manifest_check.py) 522〜536 行に対し、次の不正入力を個別に与えて**指摘ゼロ**になることを再現した。

- `image_build: {}` は MC-15 を通らない。`manifest.parse(...).component('elasticsearch2').image_reference()` は Temurin ベースを返し、Elasticsearch をビルドしなくなる。
- 末尾に改行があるタグ `"valid\n"` は `re.match(...$)` を通り、不正なイメージ参照になる。
- リポジトリ外の Dockerfile を含む一時ディレクトリへの symlink `escape` は文字列検査と `is_file()` を通る。リポジトリ内 context という境界が守られず、Dockerfile 自体の symlink も同様。

真偽値でなくキーの存在を検査し、タグを全文一致で検査し、context と Dockerfile の解決後パスが実際のリポジトリ内にあることを確認すること。これらと絶対・親パス、prebuilt 併用、note 欠落の拒否試験を追加すること。symlink 再現は一時ディレクトリと検査器 root の差し替えだけで行い、リポジトリ内 symlink 作成や Docker build はしていない。

#### R1-03 (P2): 生成イメージにベース digest を記録する

[Dockerfile](../../installer/images/elasticsearch2/Dockerfile) 32〜40 行と `build.py::buildx_argv` はベース digest のラベルを設定しない。SPEC-03 §3.4 はローカルビルドイメージへの記録を要求する。読み取り専用の `docker image inspect grdm-dev/elasticsearch2:2.4.6-1` でも、component/recipe と継承した Ubuntu ラベルだけで Temurin のベース digest がないことを確認した。実際の固定ベース digest をラベルに入れ、生成値を試験・inspect で確認すること。manifest に書くだけではイメージの出自要件を満たさない。

#### R1-04 (P2): ADR-07 が約束するレシピの CI ビルドを実装する

[ADR-07 §4](../decisions/ADR-07_Native_Builds_of_EOL_Middleware.md#japanese) は `image_build` の amd64/arm64 両方の CI ビルドを要求する。現行 workflow は Python/package、文書、ファイルシステムのセキュリティ検査だけで、Dockerfile を一度も組まずに PR の8検査が通る。単体試験は fake runner と `FROM scratch` を使うため、取得先・digest・アーキテクチャ固有の破損を検出できない。実際のレシピを両対象で組む CI と結果記録を追加するか、承認された一時延期と担当・解除条件を明記すること。PR 本文の手動両アーキテクチャビルドの記載は自動回帰検査ではなく、本レビューでは再ビルドしていない。

#### R1-05 (P3): イメージの指摘と Dockerfile の指摘を分ける

[DEMO-20 第21回](../demo/20_core_install_mac_studio.md#japanese) と PR 本文は59件（HIGH 2・MEDIUM 52・LOW 5）をネイティブイメージ自体の指摘としている。提供された `scan_latest.json` では location が `grdm-dev/elasticsearch2:2.4.6-1` のものは **58件**（HIGH 2・MEDIUM 52・LOW 4）。残りの LOW 1件はリポジトリの Dockerfile 検査（`component: installer/images/elasticsearch2/Dockerfile`）である。英和と PR 本文を直すか、59件はイメージとレシピの合計だと明記すること。Trivy 全体の集計値は正しい。

### 検証と範囲

レビュー対象 worktree のルートで指定コマンドを実行した。

```sh
PYTHONPATH=installer python3 -m unittest discover -s installer/tests
python3 -m unittest discover -s tools/tests
python3 tools/manifest_check.py
python3 tools/docs_check.py
gh pr checks 34 --repo RCOSDP/RDM-developer-guide
```

```toon
checks[5]{check,result}:
  installer,"361件実行・OK・10件skip"
  tools,"91件実行・OK"
  manifest_check,"PASSED・manifest/policy指摘ゼロ"
  docs_check,"PASSED・用語注の非阻害警告22件"
  github,"8検査合格"
```

追加の fake runner 試験でネイティブビルド失敗が終了 **30** になることを確認した。ローカル/registry のタグと `--push` は ADR-07 に合う。正常入力での Component の参照と Service の origin `image` は正しく接続されている。Compose は uid 1000・read_only・logs tmpfs・ホストの platform を使い、amd64 強制指定はない。削除した one-shot の現行 installer/manifest/spec 参照は除かれ、残る言及は履歴か不在の検査である。

Dockerfile は両 FROM の digest を固定し、公式 tarball の SHA-256 を展開前に検証し、取得を `$BUILDPLATFORM` で行う。最終段の RUN やプラグイン導入はなく、uid 1000 と明示した書込マウントを使う。取得段の apt パッケージと Dockerfile syntax frontend 自体は内容固定されておらず、ビルド用ツール全体の完全固定を確認したという意味ではない。追加レシピ・設定に非公開コード・非公開 URL・秘密は見つからず、公開リポジトリの policy 検査も合格。JNA の arm64 制約は明記されている。ADR-07 の英和の決定は対応し、anchors・Jump・版・用語集もある。

提供された `install-run21-coldstart-native-es.log` は UTC 04:53:51 から05:24:34までの30分43秒で、9段階すべてと全体が終了0。scan 報告は05:24:33、baseline/gate pass、各ツール成功、対象数22/4/1/3、Trivy は CRITICAL/HIGH/MEDIUM/LOW の順に1769/8030/9550/3676で一致する。ただし報告の commit 欄は本 PR head でなく `5bde10e`。実行証跡として扱い、head そのものの独立再実行証明とはしない。空ボリュームの準備と ES の6秒起動は操作者の記録であり、ここで独立再現はしていない。

確認した進捗ボードは指定の0.9でなく **0.8**。コールドスタート行はログと一致し、受入試験は未完のまま。SPEC-02 §4 と SPEC-03 §3.3 は英和とも不要なサービス・例外を除き、両 README 索引は ADR-07 にリンクしている。軽微な編集残件として、decisions 索引の3列の表に4列目の状態を足していること、将来の分岐方針にも ADR-07 を予約していること、変更した root README/SPEC-02/SPEC-03 の版を SPEC-06 §6どおり更新していないことがある。過去のレビューの言及は消さず履歴として保つべきである。

---

## Glossary / 用語

| Term | English note | 日本語注 |
|---|---|---|
| UID | Numeric identity used to decide who may write files. | ファイルに書ける人を判定する番号。 |
| Bind mount | A host directory shown inside a container. | ホストのディレクトリをコンテナ内に見せる仕組み。 |
| Digest | Fingerprint naming exact image content. | イメージの内容を特定する指紋。 |
| CI | Automated checks on proposed changes. | 変更案に対して自動実行する検査。 |
| Symlink | A filesystem entry pointing to another path. | 別のパスを指すファイルシステム上の項目。 |
| P2 / P3 | Normal-priority fix / lower-priority correction. | 通常優先度の修正／低優先度の訂正。 |
