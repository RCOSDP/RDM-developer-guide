# PR36 Preflight and ownership review r1 / 事前検査と所有者設定のレビュー r1

> **Summary:** Changes are required at head `af2ea6ef96cde42efeff60df7e0a36cc8e91cd97`: deletion confinement and shared-volume permissions are not established, and the mandatory policy check fails.
> **概要:** head `af2ea6ef96cde42efeff60df7e0a36cc8e91cd97` は要修正。削除範囲の制限と共有領域の権限を保証できず、必須の方針検査も失敗する。

**Jump:** [English](#english) · [日本語](#japanese)

- Version / 版: 0.1 — 2026-11-10. **Learned:** a root process with capabilities removed is still subject to file permissions, and restricting a container path does not restrict the host path behind its bind mount. ／ capability を除いた root もファイル権限に従い、コンテナ内のパスを限定しても bind 元のホストパスを限定したことにはならない。
- Applies to: [PR #36](https://github.com/RCOSDP/RDM-developer-guide/pull/36), `feat/installer-preflight` → `develop`; REV（担当レビュワ, Codex Astra）.
- Related: [Review index](README.md) · [SPEC-02](../spec/02_installer_cli.md) · [SPEC-03 §3](../spec/03_security_gate.md#english) · [SPEC-06](../spec/06_documentation_conventions.md) · [Hardening exceptions](../../manifest/hardening.json).
- Used by: PR #36 remediation and re-review.

---

<a id="english"></a>
## English

[→ 日本語版へ](#japanese)

### Verdict and evidence boundary

**Changes required.** Read the specified contracts and the complete implementation changes against `origin/develop`. A container is an isolated process environment; Docker is the tool running it ([REF-01](../reference/REF-01_Glossary.md)). A bind mount makes a host directory visible inside that environment. Capability means a separately granted administrator permission. Findings below distinguish static conclusions from actual tests. No stack operation, real reset, container execution, credential access, commit or push was performed. The checkout's secret environment file was not read or modified. Unit tests use their own temporary fixtures.

### Findings

1. **R1-01 [HIGH] Validate the host deletion boundary before mounting it.** In [lifecycle.py](../../installer/grdm_dev/lifecycle.py), lines 153–171, `exists()` accepts `runtime/volumes` when it is a symbolic link to an unrelated directory. `wipe_argv` line 141 then supplies that path to Docker, which mounts the resolved target; `find /volumes -mindepth 1 -delete` deletes that target's contents. The later host `rmtree` rejection is too late. An independent temporary-directory probe with an injected, nonexecuting runner confirmed that the wipe is submitted for such a link and only the fallback returns 14; the sentinel remained intact because Docker was never run. Reject symlinked volume roots and escaping parent paths before any destructive action, and test both cases. Inner symlinks are different: the generated `find` does not request link following. Nested host mounts also need an explicit boundary policy. The same host-path issue affects ownership: [compose.py](../../installer/grdm_dev/compose.py) lines 577–582 and `_ensure_volume_dir` accept preexisting symlinked bind sources, so the new privileged owner step can change ownership outside the intended volume tree. Validate every bind source; do not rely on the `/volumes` container prefix.

2. **R1-02 [HIGH] Include the root writer when assigning `wb_tmp`.** `volume_owners` in compose.py lines 387–398 skips every service with a `user` exception. It assigns `wb_tmp` to `1000:1000` through wb/wb_worker/mfr, but [unoconv](../../installer/grdm_dev/templates/unoconv.json) mounts it writable as `/tmp`, uses it as HOME, and runs as root with only CHOWN restored. Fresh directories are mode 0755; uid 0 without DAC_OVERRIDE cannot create LibreOffice profile/temporary files in a uid-1000 directory. This affects Linux hosts with uid 1000 as well as other uids; root is not an automatic permission bypass. Unoconv also has no dependency on the owner step. Provide a compatible shared-directory/group or user arrangement and ordering, with documented bounded exceptions only if necessary. Verify real conversion as well as startup on Linux; the present tests only compare generated strings. macOS file sharing can mask this failure.

3. **R1-03 [MEDIUM] The ownership shortcut does not safely repair existing trees.** compose.py lines 401–407 checks only the top directory. If its owner is already correct, differently owned descendants remain unusable. If it differs and contains another user's 0700 directory, root with CHOWN alone cannot walk that directory; recursive chown can fail after partial changes. A subsequent attempt can skip the now-correct root, leaving the incomplete repair undetected. This contradicts the claimed handling of older trees and recovery by rerunning. Define a migration/recovery contract, avoid marking a partially repaired tree complete, and test private descendants, mixed ownership and retry after failure. Fresh ordinary 0755 trees work; this finding concerns existing/private trees. Do not fix this by silently weakening the blanket security baseline.

4. **R1-04 [MEDIUM] Path prefixes are not filesystem/share probes.** [host.py](../../installer/grdm_dev/host.py) lines 306–329 rejects all WSL paths under `/mnt` as Windows drives, including Linux filesystems mounted there, and misses Windows drives mounted elsewhere. On macOS it rejects shared paths outside HOME (except `/Volumes`) without inspecting the engine's sharing configuration. Thus a valid explicitly shared `/private/tmp` checkout is rejected, while an unshared external volume merely warns and passes. Use mount/filesystem facts for the WSL permission requirement and a safe engine visibility check or an explicit supported override for macOS. The Colima observation alone does not establish a universal Docker Desktop restriction. The current guards are useful conservative heuristics, not proof of mount availability or mode enforcement.

5. **R1-05 [MEDIUM] The required manifest/policy check fails on the new test fixture.** `python3 tools/manifest_check.py` exits 1: `installer/tests/test_preflight.py:25` contains a URL to the private integration repository. Manifest data itself has zero findings; the policy scan has one. Use a synthetic public/example target for the secret-output test without retaining a private-repository URL in tracked text. The fixture value is deliberately not reproduced here.

6. **R1-06 [LOW] Preserve the previous review verbatim.** The two link destinations in [PR34 r2](2026-11-06_RDM-developer-guide_PR34_Native_ES2_r2.md), lines 27 and 75, change to a commit-pinned URL. The link-only repair preserves meaning and is understandable after deleting the template, but SPEC-06 §8 says review records remain verbatim and provides no link-repair exception. Restore the record and preserve its target through a compatible pointer, or obtain an explicit policy resolution and record a separate correction. Do not silently reinterpret the historical reviewer’s record.

### Remaining requested checks

- **Baseline and mount ownership:** the generic step has explicit root, only CHOWN, read-only root, no-new-privileges, no restart, and the internal network. Its exception has a review date and removal milestone; replacing two exceptions with one does not itself weaken SPEC-03. The change expands the directories this privileged process can access, so source confinement still matters (R1-01). Derived owners are 999:999 for redis_data and 1000:1000 for elasticsearch_data, elasticsearch6_data, ember_osf_web_dist, wiki_static, osfstoragecache and wb_tmp. Postgres, Mongo and RabbitMQ retain their self-managed ownership. GNU recursive chown does not request `-L` or `-H`; no ordinary descendant-symlink traversal exploit was established. Unvalidated bind sources remain a separate problem. Current volume names are fixed templates; no user-controlled shell-name injection was established.
- **Host behavior:** a fresh uid-1000 Linux tree usually skips the 1000 owner operations; Redis still needs uid 999. Other host uids need the owner step. This does not solve R1-02 or R1-03. The blanket claim that macOS chown is always a no-op is not established across Docker Desktop and Colima sharing backends; no macOS runtime verification was performed here.
- **Reset ordering and results:** confirmation remains before `down`; noninteractive refusal is exit 2, interactive cancellation 0, and stop failure returns without wiping. The helper has no network, no image pull, a read-only root, and only DAC_OVERRIDE/FOWNER. Ignoring its status is acceptable only because successful host deletion establishes the result; failed host deletion returns 14. This does not mitigate deletion of a redirected target beforehand (R1-01).
- **Credentials and fail-open:** `ls-remote` uses a constructed token-free URL, `GIT_TERMINAL_PROMPT=0`, `GCM_INTERACTIVE=never`, and `LC_ALL=C`; its raw output is classified but not emitted. The output-secret regression test passes. Timeout/DNS/connectivity failures are deliberately warnings, so doctor exit 0 means access remains unverified, not proven. This can allow a long installation to begin offline; it is an availability/preflight gap, not a bypass of the later security scan, and the documented behavior is explicit. `--strict` makes warnings fatal. Build disables terminal prompts but does not additionally disable every helper GUI. No real token or Git helper configuration was inspected.
- **Memory and CPU:** the profile floor is sum(mem_min_mb)/1024/0.70, consistent with rendering. Calculated needs are about 4.821429, 22.678571 and 24.107143 GiB for minimum/core/full with default authentication; the independent 8 GiB host minimum still applies. Detection uses the smaller known host/engine memory; explicit memory is a knowing overcommit. Engine NCPU now precedes the host count for rendering; unknown engine CPU falls back to the host and is not a guarantee. Doctor itself does not verify CPU quota. Unknown memory, unreadable emulation state and an unreadable manifest can still skip proof with warnings. Linux emulation reads the client's binfmt state, which does not prove a remote engine's state. These limitations are not covered by the passing string/mock tests as runtime claims.

### Validation

Run from the PR checkout:

```sh
PYTHONPATH=installer python3 -m unittest discover -s installer/tests
python3 tools/docs_check.py
python3 tools/manifest_check.py
```

Unit tests: 437 run in 19.355 seconds, OK with 10 skipped. Documentation check: exit 0, 102 files checked, 8 exempt, 22 warnings. Manifest/policy check: exit 1, one policy finding (R1-05). The new untracked review was also checked directly with `tools.docs_check.check_file`; the ordinary command only enumerates tracked files. Linux permission analysis is static; no isolated Linux runtime reproduction was claimed. Required next work is remediation and re-review, including Linux shared-volume/migration tests and deletion-boundary regression tests.

---

<a id="japanese"></a>
## 日本語

[→ To English](#english)

### 判定と根拠の範囲

**要修正。** 指定仕様と `origin/develop` からの実装差分を確認した。コンテナは隔離された実行環境で、Docker はそれを動かす道具（[REF-01](../reference/REF-01_Glossary.md)）。bind mount はホストのディレクトリをその中へ見せる仕組み、capability は個別に付与する管理権限である。静的判断と実行した検査を区別する。スタック操作、実際の reset、コンテナ実行、資格情報へのアクセス、commit、push はしていない。この checkout の秘密環境ファイルは読み書きしていない。単体試験は専用の一時 fixture を使う。

### 指摘

1. **R1-01 [HIGH] mount 前にホストの削除境界を検証する。** [lifecycle.py](../../installer/grdm_dev/lifecycle.py) 153–171 行の `exists()` は、無関係のディレクトリへ向く `runtime/volumes` の symbolic link も受け入れる。141 行で Docker にそのパスを渡すと解決先が mount され、`find /volumes -mindepth 1 -delete` は解決先の内容を削除する。後段のホスト `rmtree` による拒否では遅い。一時ディレクトリと実行しない fake runner による独立検査で、このリンクでも wipe が発行され、fallback だけが14を返すことを確認した。Docker を実行していないため目印ファイルは残った。破壊操作前にリンク化したルートと親経路の逸脱を拒否し、両方を試験する。内部のリンクは別で、生成した `find` はリンク追跡を指定していない。入れ子のホスト mount にも境界方針が要る。所有者操作にも同じ問題があり、[compose.py](../../installer/grdm_dev/compose.py) 577–582 行と `_ensure_volume_dir` は既存のリンク化した bind 元を受け入れるため、新しい所有者初期化が対象外の所有者を変え得る。コンテナ内の `/volumes` という接頭辞でなく、各 bind 元を検証する。

2. **R1-02 [HIGH] `wb_tmp` の所有者決定に root の書き手を含める。** compose.py 387–398 行は `user` 例外のあるサービスを全て飛ばす。wb/wb_worker/mfr から `wb_tmp` を `1000:1000` にする一方、[unoconv](../../installer/grdm_dev/templates/unoconv.json) はそこを `/tmp` と HOME に使い、root に CHOWN だけを戻して動く。新規領域は0755なので、DAC_OVERRIDE のない uid 0 は uid 1000 の領域に LibreOffice の設定・一時ファイルを作れない。Linux ホストの uid が1000でも他の値でも該当する。root は自動的な権限回避ではない。unoconv は所有者初期化にも依存しない。共有ディレクトリ・グループまたは実行ユーザーと順序を整え、必要な例外だけを根拠付きで記録する。Linux で起動と実変換を試験する。現行試験は生成文字列の比較であり、macOS の共有実装では問題が隠れ得る。

3. **R1-03 [MEDIUM] 所有者の省略判定では既存ツリーを安全に修復できない。** compose.py 401–407 行は最上位だけを調べる。最上位が正しくても配下の異なる所有者は残る。最上位が異なり他ユーザーの0700領域があれば、CHOWN だけの root は中へ入れず、再帰操作が途中で失敗し得る。再試行では既に変更した最上位を見て省略し、不完全な修復を見逃し得る。旧ツリー対応と再実行による回復の主張に反する。移行・回復の契約を定め、部分変更を完了と判定せず、private な配下・混在所有者・失敗後再試行を試験する。新規の通常0755領域は扱えるが、既存/private ツリーは別である。基準全体を黙って緩和して直してはならない。

4. **R1-04 [MEDIUM] パスの接頭辞は filesystem・共有の検査ではない。** [host.py](../../installer/grdm_dev/host.py) 306–329 行は WSL の `/mnt` 以下を全て Windows ドライブと判定し、そこに mount した Linux filesystem まで拒否する一方、別の場所の Windows ドライブを見逃す。macOS はエンジンの共有設定を調べず HOME 外（`/Volumes` を除く）を拒否する。明示共有した有効な `/private/tmp` を拒否し、未共有の外付け領域は警告だけで通す。WSL は mount/filesystem の事実で権限要件を判断し、macOS は安全な可視性検査または明示的な対応 override を用意する。Colima での観測だけでは Docker Desktop 共通の制約を証明できない。現行 guard は保守的な目安であり、可視性・mode の証明ではない。

5. **R1-05 [MEDIUM] 必須の manifest/方針検査が追加 fixture で失敗する。** `python3 tools/manifest_check.py` は exit 1。`installer/tests/test_preflight.py:25` に非公開統合リポジトリの URL がある。manifest データの指摘は0件、方針検査が1件。秘密を出力しない試験には公開/example の架空対象を使い、追跡対象の文章に非公開 URL を残さない。fixture の値はここへ転載しない。

6. **R1-06 [LOW] 過去レビューの原文を保持する。** [PR34 r2](2026-11-06_RDM-developer-guide_PR34_Native_ES2_r2.md) 27・75 行のリンク先2箇所を commit 固定 URL へ変更している。削除した template へのリンク修復として意味を保つ合理性はあるが、SPEC-06 §8 はレビューを原文のまま残すと定め、リンク修復の例外はない。原文を戻し互換の誘導ファイルで対象を残すか、明示的な方針解決を得て別の訂正記録を残す。過去のレビュワ記録を黙って読み替えない。

### その他の指定確認

- **基準・所有者:** 汎用段は明示 root、CHOWN のみ、読み取り専用 root、no-new-privileges、再起動なし、内部ネットワーク。例外に期限と除去の節目があり、2例外を1例外にすること自体は SPEC-03 の弱体化ではない。ただし privileged な処理が触れる範囲は増えるため R1-01 が重要。導出した所有者は redis_data が999:999、elasticsearch_data・elasticsearch6_data・ember_osf_web_dist・wiki_static・osfstoragecache・wb_tmp が1000:1000。Postgres・Mongo・RabbitMQ は自身の所有者管理を保つ。GNU の再帰 chown に `-L`・`-H` はなく、通常の配下リンクをたどる攻撃は確認していない。bind 元の未検証とは別問題である。現行 volume 名は固定 template で、ユーザー指定名の shell 注入も確認していない。
- **ホスト差:** Linux の新規 uid-1000 領域では1000向け処理を通常省略するが Redis は999への設定が必要。他のホスト uid は所有者設定が必要。いずれも R1-02・R1-03 は解消しない。macOS の chown が常に無操作という説明は Docker Desktop・Colima の共有方式全体で証明されておらず、今回は macOS 実行検査をしていない。
- **reset と終了値:** 確認は down より前。非対話の拒否は2、対話の取消は0、停止失敗なら削除しない。helper はネットワークなし・pullなし・読み取り専用 root・DAC_OVERRIDE/FOWNER のみ。helper の終了値を無視しても、ホスト側削除の成功で結果を証明する構造は成立する。ホスト削除失敗は14。ただし先行して外部対象を消す R1-01 は防げない。
- **資格情報・fail-open:** `ls-remote` は組み立てたトークンなし URL、`GIT_TERMINAL_PROMPT=0`、`GCM_INTERACTIVE=never`、`LC_ALL=C` を使い、生出力を分類するだけで表示しない。秘密出力の回帰試験は合格。timeout・DNS・接続失敗は意図して警告なので、doctor の0は権限を証明した意味ではなく未確認も含む。offline で長い導入を始め得るが、これは可用性・事前検査の不足であり後段の security scan の迂回ではない。仕様にも明記され、`--strict` は警告を失敗にする。build は端末 prompt を止めるが全 helper の GUI まで追加で止めてはいない。実トークンや Git helper 設定は調べていない。
- **メモリ・CPU:** floor 合計/1024/0.70 は生成側と一致。既定認証で minimum/core/full の必要量は約4.821429・22.678571・24.107143 GiB。別途ホスト最低8 GiBが適用される。既知のホストとエンジンの小さい値を使い、明示 memory は承知の過剰割当。生成時の CPU はエンジン NCPU をホストより優先する。取得不能ならホストに戻るため保証ではない。doctor 自体は CPU quota を検証しない。メモリ不明・emulation 不明・manifest 読取失敗では警告等で証明を省く余地がある。Linux emulation はクライアント側の binfmt を読むため、remote engine の状態は証明しない。合格した mock・文字列試験からこれらの実行時保証を主張できない。

### 検証

PR checkout で次を実行した。

```sh
PYTHONPATH=installer python3 -m unittest discover -s installer/tests
python3 tools/docs_check.py
python3 tools/manifest_check.py
```

単体試験は437件、19.355秒、10件 skip で合格。文書検査は exit 0、102ファイル、8免除、警告22件。manifest/方針検査は exit 1、指摘1件（R1-05）。通常の文書検査は追跡済みファイルだけなので、未追跡の新規レビューも `tools.docs_check.check_file` で直接検査した。Linux の権限判断は静的解析であり、隔離 Linux での再現実行を主張しない。修正・再レビューと、Linux 共有領域/移行試験および削除境界の回帰試験が残る。

---

## Glossary / 用語

| Term | English note | 日本語注 |
|---|---|---|
| UID/GID | Numeric user/group identities used for filesystem permissions. | ファイル権限に使うユーザー・グループの番号。 |
| DAC_OVERRIDE | Permission to bypass ordinary file access checks. | 通常のファイルアクセス権限を越える権限。 |
| CHOWN | Permission to change file ownership; it does not grant directory access. | 所有者を変更する権限。ディレクトリへのアクセス権は与えない。 |
| Symbolic link | A filesystem reference to another path. | 別のパスを指すファイルシステム上の参照。 |
| Fail-open | Continuing when a check cannot establish its result. | 検査結果を確定できなくても処理を続けること。 |
