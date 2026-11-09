# REV PR37 Image vulnerability reduction r1 / イメージ脆弱性削減レビュー r1

> **Summary:** Changes requested at a08e364. The selected y-websocket source has no JWT enforcement, rebuild inputs drift, and upgrade recovery and image smoke coverage remain incomplete.
> **概要:** a08e364 は要修正。選択された y-websocket のソースには JWT 認証が無く、再ビルドの入力が変動し、更新時の復旧手順とイメージ起動試験が不足している。

**Jump:** [English](#english) · [日本語](#japanese)

- Version / 版: 0.1 — 2026-11-10. **Learned:** an authenticated integration branch does not secure an image built from an older pinned commit, and pinned base images do not freeze application dependencies. ／ 統合ブランチに認証があっても古い固定コミットから組むイメージは保護されず、ベースイメージの固定だけではアプリケーション依存は固定されない。
- Applies to: PR #37, head `a08e364e56ace461754033775e756978c268c4bd`, base `fc5eb5bae5a2a531b23dd50ac52247c8329149df`; REV（担当レビュワ, Codex Astra）.
- Related: [Review index](README.md) · [SPEC-01](../spec/01_manifest.md) · [SPEC-03](../spec/03_security_gate.md) · [SPEC-06](../spec/06_documentation_conventions.md) · [ADR-07](../decisions/ADR-07_Native_Builds_of_EOL_Middleware.md)
- Used by: [PR #37](https://github.com/RCOSDP/RDM-developer-guide/pull/37).

---

<a id="english"></a>
## English

[→ 日本語版へ](#japanese)

### Verdict and scope

**Changes requested.** Read the specifications and ADR before reviewing the complete change. Reviewed pinned integration sources through read-only GitHub API calls; private source text and private URLs are not reproduced here. No Docker operation, live-stack change, or access to `runtime/.env` was performed. No build, migration, login, or vulnerability scan was independently repeated. Only this review file is added locally, without a commit; one Japanese PR comment records the verdict.

### Findings

1. **R1-01 — P1: select and verify the authenticated y-websocket source.** [Manifest](../../manifest/upstreams.json) lines 579–580 still select `93251589af25bb65a1397d55a9e787d55d56e9aa`; the [new recipe](../../installer/images/y-websocket/Dockerfile) lines 19–23 copies and executes that source. Its `bin/server.cjs` upgrades every connection without authorization, and `bin/utils.cjs` contains no JWT gate. The integration repository's current `develop`, `bf2cd67051025416de028f6edd16c83d3fc8ba79`, instead loads `auth.cjs`, requires a secret, and enforces token/document authorization. Merely supplying `JWT_SECRET` through Compose cannot enable code absent from the pinned source. The old pin predates this PR, but adopting a rebuilt image with “JWT unverified” does not prove the authenticated client path required by SPEC-03's new version note. Update to a reviewed authentication-bearing pin and test the exact image: valid token and two-client convergence; absent, invalid, expired and wrong-document tokens rejected before document frames; missing secret fails startup. Correct the PR/ADR evidence to identify the tested SHA.

2. **R1-02 — P2: freeze fakecas module upgrades.** [Dockerfile](../../installer/images/fakecas/Dockerfile) line 19 runs `go get` on four `@latest` modules, followed by `go mod tidy`. The source archive and builder digest are fixed, but the module graph is not. A fresh build can change its binary, toolchain requirements and vulnerability count while retaining tag `9a9ddd73b225-1`. Commit exact upgraded module versions and checksums, build in read-only module mode, and record the resolved versions with the scan evidence. The upstream commit was confirmed through GitHub as an actual CenterForOpenScience/fakecas commit dated 2024-05-22; the provenance problem is the additional unpinned dependencies, not an invented source commit.

3. **R1-03 — P2: use y-websocket's dependency lock.** [Dockerfile](../../installer/images/y-websocket/Dockerfile) lines 12–13 copy only `package.json` and execute `npm install --omit=dev`; the pinned checkout already has `package-lock.json`. Production and peer dependencies use ranges. The later `COPY . .` can place the original lockfile into the image even though the installed modules were resolved without it. Copy the reviewed lock alongside the package manifest and use `npm ci --omit=dev`; scan and authenticate that exact result. Removing npm/yarn from the final stage is useful, but does not make the runtime dependencies reproducible.

4. **R1-04 — P2: document and demonstrate ES rollback before switching an existing volume.** [Manifest](../../manifest/upstreams.json) lines 829–852 and the unchanged data-volume mount switch existing 6.3.1 data to 6.8.23. ADR-07 §5 records forward recovery of three documents, but contains no pre-upgrade snapshot, restore instructions, or rollback verification. Elastic supports a 6.x-to-later-6.y upgrade but requires a backup for rollback; reverting the image reference is not a recovery procedure ([Elastic 6.8 upgrade guide](https://www.elastic.co/guide/en/elasticsearch/reference/6.8/setup-upgrade.html)). Add an operator procedure that stops writers, takes and verifies a pre-upgrade snapshot, upgrades a disposable copy, validates templates/documents/aggregations, and restores the pre-upgrade snapshot to a clean 6.3.1 cluster on failure. Record the distribution and any X-Pack metadata/plugins present in the old cluster. Keep this test separate from the live grdm-dev stack.

5. **R1-05 — P2: close the declared image smoke-test gap.** [Image workflow](../../.github/workflows/images.yml) lines 48–64 builds the new `image_build` recipes, but its runtime case handles only `elasticsearch2`. Elasticsearch6 and fakecas therefore receive no startup or client smoke check; `build_dockerfile` y-websocket is outside the recipe enumeration entirely. The PR acknowledges only the ES6 branch gap. Add isolated hardened ES6 and fakecas checks and an authenticated y-websocket check, with the required database fixture and both platform build coverage. A credential limitation explains why the workflow was omitted but does not verify the omitted behavior. The existing image build check was still pending when inspected; no CI success is claimed for it.

### Checks that passed and remaining evidence limits

MC-16 enforces the declared checkout, note, exclusion and path rules. Its build tests verify that `-f` changes while the checkout stays the context and the base digest becomes a label. Additional temporary-directory probes accepted a normal recipe and rejected a symlink escaping the root, traversal, absolute path, directory, empty string and null (exit 0). No MC-16 defect was reproduced. Recipe identity remaining only the integration SHA is an explicit current specification choice; it makes recording the recipe revision especially important.

All explicit base references in the three recipes are digest-pinned. Elasticsearch verifies the upstream archive with SHA-512 before extraction, and fakecas verifies the commit archive with SHA-256. Fetch/cross-compilation stages use the build platform; the ES final stage copies the pre-created keystore and sets uid 1000. These are source-level checks, not independent download/hash or multi-architecture build results. Fakecas uses uid 65534, consistent with its service template, although ADR-07's generic rule still says uid 1000 and official release artifacts; clarify the documented exception for a source build.

An in-memory rendering of the real service templates confirmed ES6 and y-websocket as uid 1000, fakecas as uid 65534, all with read-only root, `cap_drop: ALL` and `no-new-privileges`. ES6 logs and `/tmp` are writable tmpfs; data remains a named volume handled by the generic owner initializer. Removing the ES6 exception is structurally consistent. RabbitMQ and unoconv retain their recorded user/read-only/capability exceptions; sharejs retains the default non-root/read-only baseline. None was dynamically proven by this review.

The pinned osf.io requirements use `elasticsearch==6.3.1` and `django-elasticsearch-metrics==5.0.0`, separately from `elasticsearch2==2.5.0`. The claimed template/write/aggregation operations do not inherently require X-Pack, so OSS is a plausible fit for that limited usage. The forward data recovery and complete client-path compatibility remain author-reported evidence, not an independently reproduced guarantee for arbitrary 6.3.1 cluster metadata.

ADR-07's English/Japanese counts agree with the PR: ES6 37/236 → 2/50, fakecas 1/57 → 0/2, y-websocket 1/12 → 0/0, RabbitMQ 0/7 → 0/7, unoconv 147/1140 unchanged, sharejs 394/1588 unchanged (CRITICAL/HIGH). They correctly distinguish rejected candidate results and disclose the database date and architecture difference. No raw scan report/image digest supporting these measurements is attached in the changed files, so this review verifies transcription only. Preserve raw reports, exact image IDs/digests, resolved dependencies and probe commands, particularly after R1-01–03. ADR-07 should explicitly state the JWT evidence gap; it currently reports only convergence. Its old `elasticsearch_data_init` wording should also be reconciled with the generic `volume_owner_init`. SPEC-01 has two separate 0.10 header entries; consolidate them on revision.

### Executed validation

Commands ran from the reviewed checkout root. The following is a review observation record, not a canonical manifest excerpt.

```toon
checks[5]{command,result,exit}:
  "PYTHONPATH=installer python3 -m unittest discover -s installer/tests","493 tests; 10 skipped",0
  "python3 -m unittest discover -s tools/tests","93 tests",0
  "python3 tools/docs_check.py","107 files; 8 exempt; 23 warnings before adding this review",0
  "python3 tools/manifest_check.py","manifest 0 findings; policy 605 scanned, 63 skipped, 0 findings",0
  "in-memory service render and temporary MC-16 path probes","expected controls and path rejections",0
```

The initial installer test invocation without `PYTHONPATH=installer` exited 1 with import errors (27 discovered, 20 errors); rerunning with the repository CI command produced the passing result recorded here. The ten skips were reported, not counted as executed successes. No commit, push, approval, merge or close was performed.

---

<a id="japanese"></a>
## 日本語

[→ To English](#english)

### 判定と範囲

**Changes requested（要修正）。** 仕様と ADR を読んでから差分全体を確認した。固定された統合ソースは GitHub API の読取で確認し、非公開ソースの本文や非公開 URL はここに転載しない。Docker 操作、稼働スタックの変更、`runtime/.env` の参照は行っていない。ビルド、移行、ログイン、脆弱性走査の独立再実行はしていない。ローカルにはレビュー文書だけを追加し、コミットせず、日本語の PR コメント1件で判定を記録する。

### 指摘

1. **R1-01 — P1: 認証を含む y-websocket のソースを選び、検証する。** [manifest](../../manifest/upstreams.json) 579–580行は依然として `93251589af25bb65a1397d55a9e787d55d56e9aa` を選び、[新レシピ](../../installer/images/y-websocket/Dockerfile) 19–23行はそのソースをコピーして起動する。その `bin/server.cjs` は認可せず全接続を upgrade し、`bin/utils.cjs` にも JWT の検査はない。一方、統合リポジトリの現在の `develop`、`bf2cd67051025416de028f6edd16c83d3fc8ba79` は `auth.cjs` を読み、秘密鍵を必須にしてトークンと文書の認可を実施している。Compose で `JWT_SECRET` を渡すだけでは、固定ソースに無い機能は有効にならない。古い固定値は本 PR より前から存在するが、「JWT 未検証」の組み直したイメージを採用しても SPEC-03 の新版が求める認証込みの実経路は証明できない。レビュー済みの認証実装を含むコミットへ更新し、そのイメージで有効トークンによる2クライアントの収束、トークン無し・不正・期限切れ・別文書の拒否と文書フレーム非送信、秘密鍵無しの起動拒否を確認する。PR/ADR に検証した SHA を明記する。

2. **R1-02 — P2: fakecas の依存更新を固定する。** [Dockerfile](../../installer/images/fakecas/Dockerfile) 19行は4モジュールを `@latest` で取得して `go mod tidy` する。ソースアーカイブとビルダーの digest が固定でも、モジュール構成は固定されない。新規ビルドでバイナリ、必要な Go の版、脆弱性件数が変わっても tag は `9a9ddd73b225-1` のままである。更新後の厳密な版とチェックサムを管理し、モジュール変更を禁止してビルドし、解決した版を走査証跡に残す。指定コミットは CenterForOpenScience/fakecas に実在する2024-05-22のコミットと確認した。問題は架空の出自ではなく、その上に加える未固定の依存である。

3. **R1-03 — P2: y-websocket の依存ロックを使う。** [Dockerfile](../../installer/images/y-websocket/Dockerfile) 12–13行は `package.json` だけをコピーして `npm install --omit=dev` を実行するが、固定 checkout には既に `package-lock.json` がある。実行時依存と peer 依存に範囲指定がある。後段の `COPY . .` は、実際のインストールに使わなかった元のロックをイメージへ入れうる。レビュー済みのロックを package manifest と一緒にコピーし、`npm ci --omit=dev` を使い、その結果を走査・認証試験する。最終段から npm/yarn を除くことは有効だが、実行時依存の再現性は保証しない。

4. **R1-04 — P2: 既存ボリューム切替前の ES 復旧手順を記録・実証する。** [manifest](../../manifest/upstreams.json) 829–852行と従来のデータマウントは、既存の6.3.1データを6.8.23へ切り替える。ADR-07 §5 は3文書の前進移行を記録するが、更新前 snapshot、復元手順、復旧検証が無い。Elastic は6.xから後の6.yへの更新を認めるが、戻すにはバックアップを必要とする。イメージ参照を戻すだけでは復旧手順にならない（[Elastic 6.8 更新ガイド](https://www.elastic.co/guide/en/elasticsearch/reference/6.8/setup-upgrade.html)）。書込停止、更新前 snapshot の取得と確認、使い捨てコピーの更新、template・文書・集計の検証、失敗時に空の6.3.1クラスタへ更新前 snapshot を復元する手順を追加する。旧クラスタの配布形態と X-Pack のメタデータ・プラグインの有無も記録する。稼働中の grdm-dev とは別に検証する。

5. **R1-05 — P2: 起動試験の不足を閉じる。** [イメージ workflow](../../.github/workflows/images.yml) 48–64行は新しい `image_build` レシピを組むが、実行時の分岐は `elasticsearch2` だけである。ES6 と fakecas の起動・クライアント試験は無く、`build_dockerfile` の y-websocket は列挙対象外である。PR は ES6 の分岐不足だけを明記している。必要なデータベースを含む隔離環境で、堅牢化した ES6・fakecas、認証した y-websocket の試験と両アーキテクチャのビルド検証を追加する。認証権限の制限は workflow を含めなかった理由にはなるが、その挙動の検証にはならない。確認時の image build check は pending であり、CI 成功とは扱っていない。

### 確認できた点と証跡の限界

MC-16 は仕様にある checkout、note、併用禁止、パス制限を検査している。ビルド試験は context を固定 checkout のまま保って `-f` だけを替え、base digest をラベルへ渡すことを確認する。追加の一時ディレクトリでの検査では通常のレシピを許可し、root 外への symlink、親への遡上、絶対パス、ディレクトリ、空文字、null を拒否した（終了0）。MC-16 の不具合は再現していない。レシピの識別が統合 SHA の tag のままなのは現仕様の明示的な選択であり、レシピ版を証跡へ残すことが特に重要になる。

3レシピの明示的なベース参照はすべて digest 固定である。ES は展開前に upstream archive を SHA-512 で、fakecas はコミット archive を SHA-256 で検証する。取得・クロスコンパイル段は build platform を使い、ES 最終段は作成済み keystore をコピーして uid 1000 を設定する。これはソース上の確認で、独立したダウンロード・ハッシュ照合や複数アーキテクチャのビルド結果ではない。fakecas の uid 65534 はサービス定義と一致するが、ADR-07 の一般則はまだ uid 1000 と公式リリース成果物を指定しているため、ソースビルドに対する例外を文書化したい。

実テンプレートをメモリ内で描画し、ES6 と y-websocket は uid 1000、fakecas は uid 65534、すべて読み取り専用 root・`cap_drop: ALL`・`no-new-privileges` になると確認した。ES6 のログと `/tmp` は tmpfs、データは汎用所有者初期化の対象である名前付きボリュームに残る。ES6 の堅牢化例外削除は構造上整合する。RabbitMQ と unoconv は記録済みの user/read-only/capability 例外を維持し、sharejs は非 root・read-only の既定を維持する。今回これらの実行時動作は実証していない。

固定された osf.io の requirements は `elasticsearch==6.3.1` と `django-elasticsearch-metrics==5.0.0` を使い、`elasticsearch2==2.5.0` は別に存在する。主張される template・書込・集計自体に X-Pack は必要でなく、限定された用途には OSS の選択は妥当と考えられる。ただし前進移行とクライアント全経路の互換性は作者の報告であり、任意の6.3.1クラスタのメタデータへの独立した保証ではない。

ADR-07 の英和の件数は PR と一致する。ES6 37/236 → 2/50、fakecas 1/57 → 0/2、y-websocket 1/12 → 0/0、RabbitMQ 0/7 → 0/7、unoconv 147/1140 据置、sharejs 394/1588 据置（CRITICAL/HIGH）。不採用候補の結果も区別し、DB の日付とアーキテクチャ差を明記している。変更ファイルには測定を裏付ける raw scan report とイメージ digest が添付されておらず、今回確認できるのは転記の一致までである。特に R1-01–03 の修正後、raw report、厳密なイメージ ID/digest、解決した依存、検証コマンドを残す。ADR-07 は収束だけでなく JWT の証跡不足を明示する必要がある。また古い `elasticsearch_data_init` の記述を汎用 `volume_owner_init` と整合させたい。SPEC-01 の0.10ヘッダが2つある点も改版時に統合したい。

### 実行した検証

作業ディレクトリは対象 checkout のルート。次はレビューの観測記録であり、正本 manifest の抄録ではない。

```toon
checks[5]{command,result,exit}:
  "PYTHONPATH=installer python3 -m unittest discover -s installer/tests","493件、うち10件スキップ",0
  "python3 -m unittest discover -s tools/tests","93件",0
  "python3 tools/docs_check.py","レビュー追加前107ファイル、8除外、23警告",0
  "python3 tools/manifest_check.py","manifest 0件、policy 605走査・63除外・指摘0件",0
  "メモリ内サービス描画と一時領域のMC-16パス検査","期待する統制とパス拒否",0
```

最初に `PYTHONPATH=installer` を付けずに実行した installer 試験は import error で終了1（27件検出、20エラー）だった。リポジトリの CI と同じコマンドで再実行して記載の合格結果を得た。10件のスキップは実行済みの合格として数えていない。commit・push・approve・merge・close は行っていない。
