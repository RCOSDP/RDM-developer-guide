# PR33 Startup fixes review r1 / 起動修正レビュー r1

> **Summary:** Changes requested: Linux volume ownership and persistent frontend cache invalidation need fixes; the security contract and evidence need reconciliation.
> **概要:** 修正要求。Linux のボリューム所有権と永続フロントエンドキャッシュの更新判定を修正し、安全性の規約と証跡の記述を整合させる必要がある。

**Jump:** [English](#english) · [日本語](#japanese)

- Version / 版: 0.1 — 2026-11-06. **Learned:** a successful warm install does not establish portable volume ownership or correct invalidation of persisted build output. ／ 準備済み環境での導入成功だけでは、別 OS のボリューム所有権や永続ビルド成果の更新判定の正しさは証明できない。
- Applies to: RCOSDP/RDM-developer-guide PR #33, head `38768abc620c1e8cc1908530ea72e6a3d5cff690`; REV（担当レビュワ, Codex Astra）.
- Related: [Review index](README.md) · [SPEC-02](../spec/02_installer_cli.md) · [SPEC-03](../spec/03_security_gate.md) · [SPEC-06](../spec/06_documentation_conventions.md) · [ADR-02](../decisions/ADR-02_Network_Model.md) · [ADR-03](../decisions/ADR-03_Staged_Security_Gate.md) · [ADR-06](../decisions/ADR-06_Wiki_Frontend_Overlay.md).
- Used by: [DEMO-20](../demo/20_core_install_mac_studio.md) · [Status board](../status/README.md).

---

<a id="english"></a>
## English

[→ 日本語版へ](#japanese)

### Verdict

**Changes requested.** R1-01 is P1; R1-02–R1-04 are P2; R1-05–R1-06 are P3. These are review findings, not a GitHub approval or merge action. The PR body and squashed commit message were read first; the local branch matches the remote head. No implementation files were changed and no installation or Docker state change was performed.

### Findings

**R1-01 — P1: prepare Elasticsearch's data directory for uid 101 before dropping root.** [elasticsearch.json](../../installer/grdm_dev/templates/elasticsearch.json), lines 10–14 and 22–23, now forces `101:101`, while [compose.py](../../installer/grdm_dev/compose.py), lines 854–869, creates its bind directory as the host user with mode 0755. A normal Linux/WSL developer with uid 1000 therefore gives uid 101 no write permission. The entrypoint's ownership step is deliberately bypassed and no owner-initialisation dependency replaces it. A fresh minimum/core install cannot initialise Elasticsearch, and `osf_init` then cannot finish its institution import. The template note acknowledges the problem but postpones it to M4; that does not preserve supported Linux startup. Add an idempotent, narrowly privileged ownership step before Elasticsearch, or an equivalent platform-aware preparation, and verify a fresh directory owned by a uid other than 101. This conclusion follows from the generated permissions; Linux runtime was not available for execution.

**R1-02 — P2: include the frontend image/build identity in the persisted fingerprint.** [ember_osf_web.json](../../installer/grdm_dev/templates/ember_osf_web.json), line 7, tests only eight environment values and `dist/index.html`. Updating `prebuilt_image` to a corrected digest with unchanged URLs leaves the named `ember_osf_web_dist` directory and `.grdm-build` unchanged, so the new container serves JavaScript from the old image indefinitely. Include the immutable image/source identity and a build-recipe version in the fingerprint, with a test that an image change rebuilds while an identical restart reuses output. Quoting and Compose dollar escaping are otherwise consistent: the renderer doubles dollars and the container shell receives the original quoted expressions.

**R1-03 — P2: reconcile the new root exception with the mandatory security contract.** [hardening.json](../../manifest/hardening.json), the new `cas` entry, relaxes `user` and `read_only`; generated CAS therefore uses the image's root default. The entry has a concrete reason, review date and M4 target, and adds no capability. However, SPEC-03 §3.3 still says every service is non-root and only explicitly permits read-only/capability exceptions, while ADR-03 §3.2 says non-root has no stage or allow-list and fails at every milestone. Extending the existing exception mechanism to another root service without aligning that contract makes a reported baseline pass ambiguous. Either preserve the written non-root requirement or explicitly document the bounded hardening-exception policy, its authority and enforcement in both SPEC-03 and ADR-03; keep it distinct from the CVE allow-list. This is a specification/implementation inconsistency, not a claim that the CAS container is privileged.

**R1-04 — P2: detect an infeasible memory floor before claiming a VM-capped budget.** [compose.py](../../installer/grdm_dev/compose.py), lines 309–334 and 935–951, correctly redistributes shares when floors fit, but silently emits all floors when they do not. With the actual core templates an 8 GiB VM produces 16,256 MiB of limits against a 5,734.4 MiB budget; Ember alone gets 8,192 MiB. A 16 GiB VM also produces 16,256 MiB against an 11,468.8 MiB budget. This is now likely with the new 8 GiB Ember floor, and the added 8 GiB VM test only asserts the reported `memory_gib`, not feasible allocation. Reject an infeasible profile before startup with the required VM memory, or require an explicit documented overcommit choice; add a sum-of-floors test. At 47 GiB the allocation is correct: 33,680 MiB ≤ 33,689.6 MiB. Explicit `--memory-gib` also bypasses VM detection, so describe it as an override rather than an unconditional cap.

**R1-05 — P3: correct the run history and distinguish scanner totals.** [DEMO-20](../demo/20_core_install_mac_studio.md), both run-15 sections, says the run timed out in `up`, and run 16 is labelled its first success. The supplied `install-run15.log` final table instead has `up,0,ok` and `health --network,40,failed`. Keep intermediate manual repairs separate from the final recorded result. The PR body and status board call 1835/8291/9772/3899 Trivy counts, but `scan_latest.json` contains combined counts: Trivy alone is 1835/8290/9763/3886; ZAP contributes HIGH 1, MEDIUM 9, LOW 13 and INFO 5. Also reconcile the claimed 352 installer tests with this exact head's observed 350 (10 skipped), and identify that the scan report's actual `milestone` is `M1` even though the work is an M2 deliverable. The successful run-18 exit 0, 22 Trivy targets and zero allow-list entries are confirmed. Correct both languages and the PR description.

**R1-06 — P3: update the authoritative status row and retain the unknown-owner qualification.** [Status board](../status/README.md) §1 still says runs 1–5 only and `up`/`health`/`scan` not reached in both languages, contradicting its updated §2b and its rule that §1 is authoritative. Update that row to run 18 while leaving acceptance pending. DEMO-20's run-16 decision also says only Docker-owned listeners fail; retain the additional owner-less wildcard failure explicitly. The implementation correctly still fails that case, so this is documentation drift, not a weakened runtime check.

### Verified behavior and limits

The hardening additions retain `cap_drop: [ALL]`, `no-new-privileges`, resource limits and loopback publishing. Unoconv adds only CHOWN for its recorded startup ownership operation. CAS remains internal-only by default. `osf_init` runs as uid 1000 with no added capabilities, read-only settings and explicit writable temporary paths; dependent services wait for successful completion. Sticky `mode=1777` allows the non-root writers without making the root filesystem writable. PostgreSQL's 500 connections is a bounded mitigation, not a repair for the recorded connection leak.

The iterative memory allocation terminates and honors floors without exceeding the 70% budget when floors fit. Default autodetection selects the smaller positive host/engine memory. In-memory checks covered 8, 16, 47 and 128 GiB; no Docker memory settings were changed. `AUTH_URL` resolves a remapped fakecas port (8081) and the web port (5050) for Shibboleth without requiring fakecas in that profile. Browser authentication acceptance was not rerun.

Network tests retain failures for unknown-owner wildcard listeners and Docker-owned wildcard listeners. Live project binding failures from `ps`/`inspect` remain fatal independently of the foreign-process warning. Trivy's filesystem-only `--offline-scan`, recorded prebuilt/assembled-overlay skips and repository exclusions match SPEC-03 §4.1; image scans remain included and tool failures remain incomplete. Offline Maven dependency resolution is reduced coverage, not evidence of zero vulnerabilities. Semgrep's PATH-first, interpreter-adjacent fallback is used for both its scan and version calls, and bootstrap installs the scan extra by default.

The EN/JA additions broadly correspond, including the erroneous history noted in R1-05–R1-06. SPEC-02 0.8, SPEC-03 0.5, ADR-06 0.3 and status 0.7 were inspected. Run 18 reuses `.env`, cached builds and persistent state: its success establishes completion on that host, not a fresh-volume or all-platform acceptance pass. The 900-second wait remains shorter than the documented worst-case 25-minute first Ember build; that cold-start scenario was not re-executed.

### Evidence and checks

Observed review data, not canonical manifest data. Commands were run from the supplied worktree root.

```toon
checks[5]{command,result}:
  "PYTHONPATH=installer python3 -m unittest discover -s installer/tests","PASS: 350 tests, 10 skipped"
  "python3 -m unittest discover -s tools/tests","PASS: 90 tests"
  "python3 tools/manifest_check.py","PASS: zero findings"
  "python3 tools/docs_check.py","PASS: 92 checked, 8 exempt, 20 non-failing glossary warnings"
  "gh pr checks 33 --repo RCOSDP/RDM-developer-guide","PASS: all 8 checks"
```

Evidence read: supplied scratchpad `install-run6.log` through `install-run18.log` (final results 40 for 6–16, 51 for 17, 0 for 18); main checkout `runtime/reports/scan_latest.json` dated `2026-11-06T03:13:00Z`, recorded commit `5bde10e`. Those historical logs/report are not a run of the reviewed squashed head. The new untracked review is additionally checked through `tools.docs_check.check_file`; the normal checker lists tracked files only. Fixes, fresh Linux/cold-start validation and C1–C6 acceptance remain for the author/QA.

---

<a id="japanese"></a>
## 日本語

[→ To English](#english)

### 判定

**修正要求。** R1-01 は P1、R1-02〜R1-04 は P2、R1-05〜R1-06 は P3。レビュー判定であり GitHub の承認・マージではない。最初に PR 本文と squash コミット本文を読み、指定 worktree とリモートの先端一致を確認した。実装ファイルの変更、導入の再実行、Docker の状態変更は行っていない。

### 指摘

**R1-01 — P1: uid 101 へ移行する前に Elasticsearch のデータ所有権を準備する。** [elasticsearch.json](../../installer/grdm_dev/templates/elasticsearch.json) 10〜14・22〜23 行は `101:101` を強制するが、[compose.py](../../installer/grdm_dev/compose.py) 854〜869 行は bind ディレクトリをホスト利用者の所有・0755 で作る。通常の Linux/WSL の uid 1000 利用者では uid 101 に書込権限がない。起動時の所有権修正を意図的に飛ばし、代替の初期化依存もないため、新規 minimum/core 導入で Elasticsearch が初期化できず、`osf_init` の機関投入も完了しない。テンプレート注は問題を認めて M4 に延期しているが、対応 OS の起動を維持できない。必要最小限の権限で冪等に所有権を準備する段か、同等の OS 別準備を追加し、101 以外の uid 所有の新規ディレクトリで検証すること。生成される権限からの結論であり、Linux 実機での再現実行はしていない。

**R1-02 — P2: 永続 fingerprint にフロントエンドのイメージ・ビルド識別子を含める。** [ember_osf_web.json](../../installer/grdm_dev/templates/ember_osf_web.json) 7 行は環境変数 8 個と `dist/index.html` しか検査しない。URL を変えずに修正版の `prebuilt_image` digest に更新しても、名前付き `ember_osf_web_dist` と `.grdm-build` は残り、新しいコンテナが古い JavaScript を配信し続ける。不変のイメージ／ソース識別子とビルド手順の版を fingerprint に含め、イメージ更新で再構築、同一条件の再起動では再利用する試験を追加すること。引用符と Compose の dollar escape は整合している。描画時にドルを二重化し、コンテナのシェルへ元の引用付き式が渡る。

**R1-03 — P2: root 例外追加と必須の安全性規約を整合させる。** [hardening.json](../../manifest/hardening.json) の新しい `cas` 項目は `user` と `read_only` を緩和し、生成 CAS はイメージ既定の root で動く。具体的理由、見直し日、M4 目標があり、capability は追加しない。しかし SPEC-03 §3.3 は全サービス非 root とし、明示的に許すのは read-only／capability の例外で、ADR-03 §3.2 は非 root に段階も許容リストもなく全節目で失敗すると定める。既存の例外機構をさらに root サービスへ広げるなら、baseline 合格の意味を明確にする必要がある。非 root 規則を維持するか、限定的な hardening 例外の方針・権限・検査を SPEC-03 と ADR-03 の両方へ明記し、CVE 許容リストと区別すること。仕様と実装の不一致であり、CAS が privileged だという指摘ではない。

**R1-04 — P2: 下限の合計がメモリ予算に収まらない場合を事前検出する。** [compose.py](../../installer/grdm_dev/compose.py) 309〜334・935〜951 行の配分は下限が収まる場合には正しいが、収まらないと全下限を黙って出力する。実際の core テンプレートでは 8 GiB VM に対して予算 5734.4 MiB、制限合計 16256 MiB、Ember 単独 8192 MiB となる。16 GiB VM でも予算 11468.8 MiB に対して合計 16256 MiB。今回の Ember 8 GiB 下限で起こりやすくなり、追加された 8 GiB VM 試験は報告の `memory_gib` しか確認しない。起動前に必要 VM メモリを示して拒否するか、明示的に記録する過剰割当の選択を要求し、下限合計の試験を追加すること。47 GiB では 33680 MiB ≤ 33689.6 MiB で正しい。明示的な `--memory-gib` は VM 検出を迂回するため、無条件の上限ではなく上書き指定として説明する必要もある。

**R1-05 — P3: 実行履歴とスキャナ別件数を修正する。** [DEMO-20](../demo/20_core_install_mac_studio.md) の英和第15回は `up` の時間切れ、第16回は初成功と書くが、指定 `install-run15.log` の末尾は `up,0,ok` と `health --network,40,failed`。途中の手動修正と最終記録を分けること。PR 本文と進捗ボードが Trivy 件数とする 1835/8291/9772/3899 は `scan_latest.json` の全体合計で、Trivy 単独は 1835/8290/9763/3886、ZAP は HIGH 1・MEDIUM 9・LOW 13・INFO 5。installer 352 件という記載も、同じ先端で観測した 350 件（10 skip）と整合させること。M2 作業であっても scan 報告の実際の `milestone` は `M1` と区別する必要がある。第18回の exit 0、Trivy 22 対象、許容リスト 0 件は確認できた。英和と PR 本文を修正すること。

**R1-06 — P3: 正本の進捗行を更新し、所有者不明の失敗条件を残す。** [進捗ボード](../status/README.md) §1 は両言語とも実行1〜5回のみ、`up`/`health`/`scan` 未到達のままで、更新した §2b および §1 を正本とする規則と矛盾する。受入未完了を維持して第18回へ更新すること。DEMO-20 第16回の決定も Docker 所有だけ失敗と書くため、所有者不明のワイルドカードも失敗する条件を明記すること。実装はその条件を維持しており、実行時の弱体化ではなく記述のずれである。

### 確認済みの挙動と限界

hardening 変更後も `cap_drop: [ALL]`、`no-new-privileges`、資源制限、ループバック公開を維持する。unoconv の追加は起動時所有権操作に必要な CHOWN のみ。CAS は既定で内部ネットワークのみ。`osf_init` は uid 1000、capability 追加なし、設定は読取専用、書込箇所は明示的な一時領域で、利用側は成功終了を待つ。sticky な `mode=1777` はルート全体を書込可能にせず非 root の書込を許す。PostgreSQL 500 接続は上限付きの緩和であり、接続漏れそのものの修正ではない。

反復的なメモリ配分は終了し、下限が収まれば 70% 予算内で下限を満たす。既定検出はホスト／engine の正の小さい値を採る。8・16・47・128 GiB をメモリ内で検査し、Docker 設定は変えていない。`AUTH_URL` は fakecas の変更後ポート 8081、Shibboleth 時は web の 5050 を解決し、後者に fakecas を要求しない。ブラウザの認証受入は再実行していない。

ネットワーク試験は、所有者不明と Docker 所有のワイルドカードの両方で失敗を維持する。`ps`/`inspect` の実際の公開違反も他プロセス警告とは独立して失敗する。Trivy の filesystem 限定 `--offline-scan`、理由を記録する prebuilt／組立 overlay の除外、repo 除外は SPEC-03 §4.1 と一致し、イメージ検査と道具失敗の未完了扱いは残る。Maven のオフライン依存解決は検査範囲を狭めるのであり、脆弱性ゼロの証明ではない。Semgrep の PATH 優先・実行中 Python の隣への fallback は scan と version の両方に使われ、bootstrap は既定で scan extra を入れる。

英和の追加部分は、R1-05〜R1-06 の誤記を含め概ね対応する。SPEC-02 0.8、SPEC-03 0.5、ADR-06 0.3、進捗0.7を確認した。第18回は `.env`、ビルドキャッシュ、永続状態を再利用しており、そのホストでの完走を示すが、新規ボリュームや全 OS の受入合格を示さない。900 秒の待機は、記録された最悪25分の初回 Ember ビルドより短く、その初回条件は再実行していない。

### 証跡と検証

指定 worktree のルートで実行した観測結果であり、manifest の正本データではない。

```toon
checks[5]{command,result}:
  "PYTHONPATH=installer python3 -m unittest discover -s installer/tests","合格: 350 件、10 skip"
  "python3 -m unittest discover -s tools/tests","合格: 90 件"
  "python3 tools/manifest_check.py","合格: 指摘 0"
  "python3 tools/docs_check.py","合格: 92 検査、8 除外、非失敗の用語警告 20"
  "gh pr checks 33 --repo RCOSDP/RDM-developer-guide","合格: 全 8 checks"
```

指定 scratchpad の `install-run6.log`〜`install-run18.log` を確認した（最終終了コードは6〜16回が40、17回が51、18回が0）。main checkout の `runtime/reports/scan_latest.json` は日時 `2026-11-06T03:13:00Z`、記録コミット `5bde10e`。これらは過去の証跡であり、レビューした squash 先端の実行ではない。通常の検査は追跡ファイルのみ列挙するため、新規未追跡レビューは `tools.docs_check.check_file` でも検査する。修正、新規 Linux／初回起動の検証、C1〜C6 受入は作者／QA の残件。

---

## Glossary / 用語

| Term | English note | 日本語注 |
|---|---|---|
| UID | The numeric identity that owns files and runs a program. | ファイルの所有者や実行者を示す番号。 |
| Fingerprint | A stored value used to decide whether saved output still matches its inputs. | 保存した成果が入力と一致するか判定する値。 |
| Capability | One specific operating-system permission given to a process. | プログラムへ与える OS 操作権限の一つ。 |
| Memory floor | The minimum memory assigned to a service. | サービスへ割り当てるメモリの下限。 |
| Warm install | An install that reuses existing data or build output. | 既存のデータやビルド成果を再利用する導入。 |
| P1 / P2 / P3 | High / medium / low review priority. | 高／中／低のレビュー優先度。 |

Shared terminology: [REF-01](../reference/REF-01_Glossary.md).
