# REV-45-r1 Python 3.13 pin review / Python 3.13 固定版レビュー

> **Summary:** Changes requested: the current exceptions cover only no-fix Debian findings, but their wildcard matching also suppresses future fixable findings. The pinned commits, acceptance result, and reported scan totals were verified.
> **概要:** 要修正。現在の例外は修正版の無い Debian の検出だけに対応するが、ワイルドカードの照合は将来の修正版ありの検出も隠す。固定コミット、受入結果、スキャン集計は確認できた。

**Jump:** [English](#english) · [日本語](#japanese)

- Version / 版: 0.1 — 2026-11-11. **Learned:** a no-fix snapshot does not make an exception safe for future scans unless package identity and fix availability remain part of matching. ／ 現時点で修正版が無いことだけでは将来の検査も安全にならず、パッケージの同一性と修正版の有無を照合に残す必要がある。
- Applies to: RCOSDP/RDM-developer-guide PR #45, head `3c5dd0c31944b9b3450ff34eb0808ad1e26f8728`, base `eb8c4e96977b06bd3bb0fd42b03f0872806be08a`.
- Reviewer: REV（担当レビュワ, Codex Astra）.
- Posted review / 投稿: [PR comment](https://github.com/RCOSDP/RDM-developer-guide/pull/45#issuecomment-6797756385).
- Related: [review index](README.md), [SPEC-03](../spec/03_security_gate.md), [SPEC-06](../spec/06_documentation_conventions.md), [DEMO-20](../demo/20_core_install_mac_studio.md), [status board](../status/README.md).
- Used by: coordinator's PR #45 revision and re-review decision.

---

<a id="english"></a>
## English

[→ 日本語版へ](#japanese)

### Verdict and scope

**Changes requested.** R1-01 is a security-gate blocker. R1-02 corrects misleading milestone status; R1-03 records smaller evidence corrections. This is a review comment, not a GitHub approval or request-changes review submission.

Reviewed a fresh scratch clone detached at the stated head. No source edits, commits, pushes, merges, approvals, or issue closures were made. No Docker command or live acceptance run was executed, and the live `runtime/.env` was not read. Existing dated JSON reports in the main checkout were read only. The owner authorization to remove freecad and accept remaining no-fix OS packages is accepted from the task; approval was not requested again.

### R1-01 — High: wildcard exceptions also accept future fixable packages

Locations: `manifest/allowlist.json:15` and all other entries; `installer/grdm_dev/scan.py:210–226,248–258`.

All 58 entries use `component: "*"`. `image` correctly rejects `postgres:...`, a sibling name such as `grdm-dev/waterbutler-extra:...`, and the ordinary Python package path tested in the PR. However, after image and CVE match, the wildcard immediately accepts every component in that image, on every tag or digest. The package list in `reason` is never checked. `normalize_trivy` discards `FixedVersion`, `Status`, and OS/language package class, so the matcher cannot restrict the exception to no-fix Debian packages.

Reproduced with the first real entry, `CVE-2025-69720` / `grdm-dev/waterbutler`: a synthetic Trivy finding at `grdm-dev/waterbutler:future (debian 13.2)` with `Status: fixed`, `FixedVersion: 2`, and either `libncursesw6@1` or `unrelated-package@1` is still allow-listed. A later security database update can therefore leave a fixable finding invisible until expiry, even without a rebuild. An `apt-get upgrade` in the Dockerfile does not repair the gate's decision for an already-built image. The same matcher is used at stricter milestones.

Required: replace wildcard components with explicit package scope; compare exact package identity, not the existing raw prefix (which also matches sibling package names and ignores an `@version` suffix); preserve and enforce no-fix status and OS/image identity for these exceptions. Keep findings open when a fix appears or classification is unknown. Add regressions for an unrelated package, a package-name prefix collision, a fixed version on the same package and image, a sibling image, and a language-package result. A deliberately fixed historical artifact exception would need separate explicit semantics and approval; it is not the no-fix acceptance authorized here.

### R1-02 — Medium: status board still marks a zero-entry ceiling as satisfied

Locations: `docs/status/README.md:68,134`.

The updated board still marks the M2 Trivy/allow-list row complete and cites “allow-list 0 entries (M1: 0).” That was true of runs 18/21, but this PR adds 58 active entries; the latest report confirms 58 and the unchanged baseline is 0. With M2's count-not-growing gate, that is not a completed condition. Preserve the historical measurements, append the current counts and scan reference, and mark the baseline/owner milestone decision outstanding. The M1 report-only pass must not be presented as M2 gate completion. Do not silently raise the baseline to make the row green.

### R1-03 — Low: correct provenance and summary details

- `docs/demo/20_core_install_mac_studio.md:489,1033` calls both osf.io and wiki-frontend `8fc45de4`. The wiki source pin is `5985d18b75da4105a610ac041b838c45f295de7d`; `8fc45de4` is its osf.io overlay base. The build report records the combined image tag `8fc45de461fd-5985d18b75da`.
- DEMO-20 version 0.17 says the scan totals are the same. The body correctly reports 10,983 → 10,984, with one additional ZAP MEDIUM; qualify the header as unchanged Trivy totals.
- `manifest/upstreams.json:327` and the allow-list reasons date the owner decision 2026-11-11, whereas the authorized decision supplied for this review is 2026-11-10. Separate the decision date from the legitimate 2026-11-11 entry-addition date.
- The PR description still describes MFR `f9da1db3`, 11/12, and unresolved C5/ZAP. Update it to the reviewed head and final evidence.

### Verified evidence

Every one of the 58 entries has a corresponding finding in the raw Trivy reports from `20261111T132241Z`: WaterButler 11 entries / 47 HIGH, MFR 47 entries / 3 CRITICAL + 127 HIGH. All 177 matched findings have empty `FixedVersion` and `Class: os-pkgs`, `Type: debian`. Statuses are 174 `affected`, one `will_not_fix`, and two `fix_deferred`; every package is named in its entry's reason. No current fixable match or unmatched entry was found. All entries have owner `AID`, valid dates, addition date 2026-11-11, and expiry 2026-12-31; validation returns no errors. SPEC-03's additional requirement that expiry be no later than the next milestone start cannot be established from a calendar date alone: M1 remains the configured gate and M2 is already described as in progress. Record the milestone boundary when closing it; the existing baseline was not changed.

The audit JSON (`pr45-allowlist-audit.json`) records all matches, source SHA-256 hashes, and both fixable reproductions. The audit script (`pr45-audit.py`) can be rerun from the scratch clone with `PYTHONPATH=installer python3 ../reviews/pr45-audit.py`; it should currently report 58 entries, 177 matches, zero fixed matches in the stored reports, and two incorrect `allowlisted: true` reproductions.

GitHub reads confirm WaterButler PR #3 merged at `3319c10679165b421c0425771779d068f19b9724` and MFR PR #7 at `9771b8cfb352f6c9907a6733a4205f9e62f4142d`. Both pinned Dockerfiles use base digest `sha256:e48f59cdba69a3cbd9ed2cf0f348d90d45a8d350d98134cf1070bc106ee9ed90`. MFR head `2c4a88a6` and merge `9771b8cf` have identical Git tree `e5c8c0a3d0f5e9263d72edc01fc5b9dfc0b349d8`. MFR defaults to `MFR_DEBIAN_TOOLS=pspp`; its build record is native `linux/arm64`, consistent with removing `build_platform`. This review did not independently rebuild either architecture or query registry contents.

Committed `acc-20261111T132104Z-530071/results.json`, collector, TOON, JUnit, and pytest log agree: 12 passed, no failures/errors/skips, C5 success 200 and rejection 401, 24 healthy precheck services. The earlier committed run records 11/12 and C5 success 400. Manual inspection and separate `gitleaks dir ... --redact --no-banner` executions found no exposed credentials in either run directory; both scanner exit codes were 0. No trace archive is committed.

The dated main-checkout `db_upgrade_20261111T111110Z.json` confirms 9.6 → 18, a 4,844,586-byte dump, 531 compared objects, and retention of `postgres_data.pg9.6-20261111T111040Z`. `build_20261111T132028Z.json` confirms the reviewed MFR/WB tags; `up_20261111T132103Z.json` records all 24 service checks successful. These are stored evidence, not a new live-stack validation.

`scan_20261111T132607Z.json` agrees with DEMO-20: total 10,984, CRITICAL/HIGH/MEDIUM/LOW/INFO 726/3782/4148/2322/6, plus 177 allow-listed; Trivy 726/3769/4139/2310, Semgrep HIGH 12, gitleaks zero, ZAP HIGH/MEDIUM/LOW/INFO 1/9/12/6. All four scanners are `ok`, baseline pass, exit 0, M1 report-only. The intermediate report has one fewer ZAP MEDIUM; the first report exits 51, as documented. C5 covers the classic page only; the board explicitly keeps the API v2/ember preview issue open.

### Independent checks

Run from `scratchpad/pr45-rev` with the system PATH `python3` (`/opt/homebrew/bin/python3`, 3.15.2), without a virtual environment:

```sh
PYTHONPATH=installer python3 -m unittest discover -s installer/tests
python3 -m unittest discover -s tools/tests
python3 tools/docs_check.py
python3 tools/manifest_check.py
```

| Check | Result | Exit |
|---|---|---:|
| Installer tests | 647 tests, OK, 10 skipped | 0 |
| Tools tests | 93 tests, OK | 0 |
| docs_check | 154 checked, 8 exempt, 38 warnings | 0 |
| manifest_check | Passed; no manifest/policy findings | 0 |
| Audit script | 58/58 current entries verified; future-fix over-match reproduced | 0 |
| gitleaks, each new run directory | No leaks found | 0 |

An initial independent run with Apple's `/usr/bin/python3` 3.9.6 also passed all four requested checks (647/93 tests, 10 installer skips, same docs warnings). The installer tests emit an existing foreign-listener warning for Control Center on port 5000; Python 3.15 also emits a fork deprecation warning. Logs are adjacent as `pr45-*-python3.log` and `pr45-*-tests.log` / `pr45-*-check.log`. The clone remains clean.

---

<a id="japanese"></a>
## 日本語

[→ To English](#english)

### 判定と範囲

**要修正（changes requested）。** R1-01 はセキュリティゲートの阻害事項。R1-02 は節目の状態の誤解を直すもの、R1-03 は証跡の小さな記述修正である。GitHub の承認・変更要求レビューではなく、レビューコメント1件として報告する。

指定先頭コミットに固定した新しい scratch クローンで調べた。ソース編集、コミット、push、マージ、承認、Issue の終了は行っていない。Docker コマンドや実スタックの受入は実行せず、実スタックの `runtime/.env` も読んでいない。本体チェックアウトの日付付き JSON 報告だけを読み取った。freecad 廃止と残る修正版無し OS パッケージの許容は、タスクで示された所有者の承認を前提とし、再承認は求めていない。

### R1-01 — 高: ワイルドカードが将来の修正版ありも許容する

対象: `manifest/allowlist.json:15` と全項目、`installer/grdm_dev/scan.py:210–226,248–258`。

58項目すべてが `component: "*"` を使う。`image` は postgres、似た別イメージ名、通常の Python パッケージのパスを拒否する。しかしイメージ名と CVE が一致すると、すべてのタグ・ダイジェストのすべての部品を許容する。理由欄のパッケージ一覧は照合されない。正規化処理は `FixedVersion`、`Status`、OS/言語パッケージの分類を捨てるため、修正版の無い Debian パッケージだけに制限できない。

先頭の実項目 `CVE-2025-69720` / `grdm-dev/waterbutler` を使い、`grdm-dev/waterbutler:future (debian 13.2)` の `libncursesw6@1` または `unrelated-package@1` に `Status: fixed`、`FixedVersion: 2` を与えた。どちらも許容された。将来 DB が更新されても、修正版ありの検出が期限まで隠れうる。既存イメージの判定は Dockerfile の `apt-get upgrade` では直らない。この照合は厳しい節目でも使われる。

修正要求: ワイルドカードを明示的なパッケージ指定へ置き換え、名前を厳密に照合する。現行の前方一致は似た別パッケージも通し、`@version` も無視するので、そのままでは不十分。これらの例外には修正版の有無、OS 分類、イメージの同一性を保持して適用し、修正版あり・分類不明は未許容にする。別パッケージ、名前の前方一致、同一パッケージの修正版あり、別イメージ、言語パッケージを回帰試験する。修正版のある過去の成果物をあえて許容するなら別の明示的な意味と承認が必要で、今回承認された「修正版無し」の扱いとは異なる。

### R1-02 — 中: 進捗表が0件の上限を達成済みのままにする

対象: `docs/status/README.md:68,134`。

更新した進捗表の M2 Trivy/許容リスト行は完了のまま「許容リスト0件（M1: 0）」を示す。第18・21回の履歴としては正しいが、この PR の現行項目数は58件で、最新報告も58、未変更の上限は0である。M2 の件数増加禁止では達成済みではない。履歴を残しつつ最新件数・報告への参照を追記し、節目終了時の上限判断を残件にする。M1 の報告のみ合格を M2 の門の達成と混同せず、見かけを合わせるため上限を無断変更しない。

### R1-03 — 低: 来歴と概要の細部を直す

- DEMO-20 の489・1033行は osf.io と wiki-frontend をともに `8fc45de4` とする。wiki のソース固定版は `5985d18b75da4105a610ac041b838c45f295de7d` で、`8fc45de4` は osf.io の基底。ビルド報告の結合タグは `8fc45de461fd-5985d18b75da`。
- 0.17 の版ヘッダは検査件数が同じとするが、本文のとおり 10,983 → 10,984、ZAP MEDIUM が1件増えている。「Trivy の件数は同じ」と限定する。
- `manifest/upstreams.json:327` と許容理由の所有者判断日は2026-11-11だが、タスクで示された承認日は2026-11-10。正当な追加日2026-11-11と判断日を分ける。
- PR 本文は MFR `f9da1db3`、11/12、C5/ZAP 未解決のまま。現行先頭と最終証跡に合わせる。

### 確認済み証跡

`20261111T132241Z` の Trivy 生報告で58項目すべてを照合した。WB は11項目で HIGH 47件、MFR は47項目で CRITICAL 3件・HIGH 127件。全177件の `FixedVersion` は空、分類は `os-pkgs` / `debian`。状態は `affected` 174件、`will_not_fix` 1件、`fix_deferred` 2件。全パッケージが理由欄に記載され、現時点の修正版ありの誤許容や対応する検出の無い項目は無かった。全件 owner は AID、追加日は2026-11-11、期限は2026-12-31で形式検証は正常。ただし SPEC-03 の「次の節目開始以前」は日付単独では証明できない。設定は M1、進捗表の M2 は既に進行中なので、節目を閉じる時点で境界を明記する。上限は未変更。

audit JSON (`pr45-allowlist-audit.json`) に全対応、入力の SHA-256、修正版ありの再現を記録した。スクリプト (`pr45-audit.py`) は scratch クローンで `PYTHONPATH=installer python3 ../reviews/pr45-audit.py` と実行する。現状では58項目・177件・保存報告内の修正版あり0件・誤った許容の再現2件を出す。

GitHub で WB PR #3 のマージ `3319c10679165b421c0425771779d068f19b9724` と MFR PR #7 のマージ `9771b8cfb352f6c9907a6733a4205f9e62f4142d` を確認した。両 Dockerfile の基底ダイジェストは manifest と同じ `sha256:e48f59cdba69a3cbd9ed2cf0f348d90d45a8d350d98134cf1070bc106ee9ed90`。MFR の先頭 `2c4a88a6` とマージ `9771b8cf` の Git tree は `e5c8c0a3d0f5e9263d72edc01fc5b9dfc0b349d8` で同一。既定 `MFR_DEBIAN_TOOLS=pspp`、ビルド報告は native `linux/arm64` で、`build_platform` 削除と整合する。両アーキテクチャの再ビルドやレジストリ照会はしていない。

コミット済み `acc-20261111T132104Z-530071` の results.json、collector、TOON、JUnit、pytest log は一致する。12合格、失敗・エラー・skip なし、C5 は200/401、事前健全性は24サービス。前のコミット済み実行は11/12、C5成功ケース400。両実行フォルダを目視し、各々 `gitleaks dir ... --redact --no-banner` を実行して秘密の検出なし、いずれも終了0。トレース書庫の追加はない。

本体の `db_upgrade_20261111T111110Z.json` は9.6→18、dump 4,844,586バイト、531オブジェクト比較、旧ディレクトリ保持を裏付ける。`build_20261111T132028Z.json` は対象 WB/MFR タグ、`up_20261111T132103Z.json` は24サービス正常を記録する。保存証跡の照合であり、新たな実機検証ではない。

`scan_20261111T132607Z.json` と DEMO-20 は一致する。合計10,984、CRITICAL/HIGH/MEDIUM/LOW/INFO は726/3782/4148/2322/6、別途177件許容。Trivy は726/3769/4139/2310、Semgrep HIGH 12、gitleaks 0、ZAP は1/9/12/6。全スキャナー ok、基本対策合格、終了0、M1報告のみ。中間報告は ZAP MEDIUM が1件少なく、最初の報告は記述どおり終了51。C5 は旧来の画面の範囲で、API v2/ember のプレビューは進捗表で未解決としている。

### 独立検査

scratch クローンで仮想環境を使わず PATH の `python3`（`/opt/homebrew/bin/python3`、3.15.2）を使い、英語版に示した4コマンドを実行した。

| 検査 | 結果 | 終了 |
|---|---|---:|
| installer 単体試験 | 647件、OK、skip 10件 | 0 |
| tools 単体試験 | 93件、OK | 0 |
| docs_check | 154件検査、8件免除、38警告 | 0 |
| manifest_check | 合格、manifest/policy 指摘なし | 0 |
| audit スクリプト | 58/58照合、将来の修正版の誤許容を再現 | 0 |
| gitleaks、各追加実行フォルダ | 検出なし | 0 |

最初に Apple の `/usr/bin/python3` 3.9.6 でも同じ4検査を実行し、647/93件、skip 10、同じ文書警告で全て終了0だった。installer 試験は既存の Control Center の5000番ポート警告、Python 3.15 は fork 非推奨警告を出す。隣に `pr45-*-python3.log` と `pr45-*-tests.log` / `pr45-*-check.log` を保存した。クローンは変更なし。
