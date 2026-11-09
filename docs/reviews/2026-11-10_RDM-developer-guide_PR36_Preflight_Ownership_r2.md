# PR36 Preflight and ownership review r2 / 事前検査と所有者設定のレビュー r2

> **Summary:** Changes required at `4cf3a22`: reset confinement and ownership success still have gaps; all required automated checks pass.
> **概要:** `4cf3a22` は要修正。reset の範囲制限と所有者設定の成功判定に不足が残る。必須の自動検査はすべて合格。

**Jump:** [English](#english) · [日本語](#japanese)

- Version / 版: 0.1 — 2026-11-10. **Learned:** a path check expires when the path changes, and a successful command does not prove that ownership changed. ／ パスが変われば検証結果は古くなり、コマンドの成功だけでは所有者の変更を証明できない。
- Applies to: [PR #36](https://github.com/RCOSDP/RDM-developer-guide/pull/36), head `4cf3a22ea89ff428d4b4fe3228b21bd1029445f5`; REV（担当レビュワ, Codex Astra）.
- Related: [Review index](README.md) · [r1](2026-11-10_RDM-developer-guide_PR36_Preflight_Ownership_r1.md) · [SPEC-02](../spec/02_installer_cli.md) · [SPEC-03](../spec/03_security_gate.md) · [SPEC-06 §8](../spec/06_documentation_conventions.md#english).
- Used by: PR #36 remediation and the next review.

---

<a id="english"></a>
## English

[→ 日本語版へ](#japanese)

### Verdict and boundary

**Changes required.** Reviewed r1, the `af2ea6e..4cf3a22` diff, surrounding implementation and contracts, and the PR head through GitHub. No real Docker command, stack mutation, installation, credential-file access, commit, push, approval or merge was performed. Temporary fixtures and nonexecuting runners supplied independent probes; the ownership probe is a shell script running against the existing test filesystem model, not a Linux kernel test.

### Findings

1. **R2-01 [HIGH; R1-01 remains open] Revalidate at each destructive transition.** [lifecycle.py](../../installer/grdm_dev/lifecycle.py) lines 165–179 validates once, before `down --volumes`, and then passes the path to the root wipe and host deletion without rechecking. An independent temporary-directory probe replaced `volumes` with an outside symlink inside the fake `down` runner. The wipe was submitted for the substituted path; only host `rmtree` subsequently returned exit 14. The sentinel stayed intact because the runner never executed Docker. Revalidate after down and immediately before the wipe and host deletion, reject changed directory identities, and test substitutions at both transitions. Validation in render/up is also a snapshot, not an atomic guarantee across Docker's bind resolution. Document the residual time-of-check/time-of-use (TOCTOU) limit and a trusted, non-concurrently-mutated checkout assumption, or provide stronger confinement; repeated checks alone cannot eliminate every race.

2. **R2-02 [HIGH; R1-01 remains open] Preserve the mount boundary in the host fallback too.** [compose.py](../../installer/grdm_dev/compose.py) lines 1011–1027 examines only immediate volume entries and compares device numbers. [lifecycle.py](../../installer/grdm_dev/lifecycle.py) line 179 then calls ordinary `shutil.rmtree`, which has no filesystem boundary guard. Thus a writable nested mount skipped by the container's `find -xdev` is traversed by the fallback and its contents can be removed before removing the mountpoint itself fails. Same-filesystem bind mounts also evade a device-number comparison and `-xdev`; `runtime`/the volumes root being mounts is not checked either. This contradicts SPEC-02's claim that deeper mounts are not crossed. Refuse mounted sources/descendants using mount-aware evidence, including same-device bind mounts, or implement an equally bounded deletion path and retain the failure result instead of traversing skipped mounts. This is a static finding; no mount or destructive runtime reproduction was performed.

3. **R2-03 [MEDIUM; R1-03 partially open] Do not infer a safe filesystem from an ownership mismatch.** [compose.py](../../installer/grdm_dev/compose.py) lines 428–435 returns success for any top-level `chown` that exits zero without attaining the requested UID/GID. That does not establish a macOS share or prove that the actual non-root writers can use it. The final directory pass has no read-back either. In an independent extension of the existing fake filesystem, a final directory chown silently did nothing: the generated shell exited 0 and left a private directory at `0:0`, although its writer needs `1000:1000`. Restrict any no-ownership exception to an explicitly established backend with writer-access evidence; unexpected mismatches must fail. Verify directory hand-back as well as files and cover a silently ineffective chown. Normal nonzero chown failures do propagate through `set -e`; this finding is about ineffective operations reported as success. Changing to GNU tools improves the known image case but does not itself prove every mounted filesystem's result.

4. **R2-04 [MEDIUM; R1-04 partially open] A rejected bind mount must be a failed prerequisite.** [doctor.py](../../installer/grdm_dev/doctor.py) lines 122–139 treats every exit 125 as a warning, including a Docker engine response that explicitly denies the requested mount. With default non-strict doctor, that allows installation to proceed even when the engine has positively rejected sharing; `GRDM_DOCKER_SHARED=1` was not needed. Distinguish an explicit mount/sharing rejection from an unavailable image or an inconclusive probe, return exit 13 for the former, and test the denied-mount branch. Keep the explicit override visible in the report. The existing tests cover missing files and a pull failure, but not an engine-denied mount.

### Closure assessment and requested details

- **R1-01: partially addressed, not closed.** Existing root/runtime/volume symlinks and immediate different-device volumes are rejected before reset/up; render validates selected bind names. R2-01 and R2-02 remain.
- **R1-02: functional correction present; runtime evidence remains external.** Unoconv now waits for ownership and receives CHOWN plus DAC_OVERRIDE, with ALL otherwise dropped. The [exception](../../manifest/hardening.json) names the image, shared private files, a conversion observation, review date `2027-01-31`, and M4 replacement through unoserver. It meets SPEC-03's recorded-exception fields. DAC_OVERRIDE is sufficient for both reading private inputs and creating files in uid-1000 `/tmp`; a read-only bypass would not suffice. It is not a path-scoped permission: an exploited document converter can bypass discretionary access checks throughout its writable container filesystem and shared `wb_tmp`. The internal network and no-new-privileges do not remove that risk. The claim that a shared group is impossible is an assertion about the unchanged image/private-file arrangement, not proof that running the converter as the writer UID or preparing group permissions cannot work. Treat this as a transitional recorded exception, not proof of globally minimal privilege. Prefer a non-root converter during the recorded modernization. This reviewer did not repeat real conversion; the manifest's reported observation has no attached reproducible log in this diff.
- **R1-03: substantially improved, partially open.** Every run walks the tree; private directories are temporarily owned by root, files are assigned first, directories deepest-first, and retry does not trust the top directory. Model tests cover mixed owners, nested 0700, interruption, failure and retry, and 000 refusal. R2-03 remains. The initial ownership transfer also changes a directory's group to root temporarily; failure can leave this intermediate state until retry, as the documented recovery model allows. No broad new owner-step capability was added.
- **Image responsibility:** the manifest now assigns `volume_owner_init` to `postgres`, the template agrees, and rendering tests assert the same image as the postgres service. Its own exception remains root + CHOWN only, read-only root, no-new-privileges, no restart; postgres's broader service exception is not inherited. Selecting GNU tools instead of the observed ineffective uutils is explicitly explained. The actual image is `postgres:9.6` with `base_image_digest: null`, not digest-pinned; SPEC-01 permits null until pinning, but SPEC-02/doctor's “pinned image” wording overstates this. Record/pin the measured image before relying on reproducible GNU behavior across platforms; no claim of actual image inspection is made here.
- **R1-04: WSL correction closed; macOS partial.** WSL2 creates a temporary file in the checkout, performs chmod 0600, reads its mode back and removes it. This replaces path-prefix guessing. Unknown results warn; they do not prove permissions. macOS uses a read-only manifest bind, no network, dropped capabilities and no-new-privileges; the override skips it with a warning. R2-04 remains. The probe lists a known filename rather than proving file identity or all runtime mounts; a stale remote checkout could satisfy it. It may pull the mutable postgres tag, so the table's “read-only” label describes the bind, not all engine effects.
- **R1-05: closed.** The policy fixture is corrected; manifest/policy scan exits 0 with no findings.
- **R1-06: closed.** PR34 r2 is byte-for-byte unchanged relative to `origin/develop`; the relative links are restored. The retired [template pointer](../../installer/grdm_dev/templates/elasticsearch_data_init.json) explicitly explains its historical purpose, and no component lists it as a service. This preserves the review verbatim under SPEC-06 §8; the pointer is not the old runnable implementation.

### Validation

From the PR checkout:

```sh
PYTHONPATH=installer python3 -m unittest discover -s installer/tests
PYTHONPATH=installer python3 -m unittest discover -s tools/tests
python3 tools/docs_check.py
python3 tools/manifest_check.py
```

Installer: exit 0, 461 tests, 27.026 seconds, 10 skipped. Tools: exit 0, 92 tests, 3.691 seconds. Documentation: exit 0, 103 files checked, 8 exempt, 22 warnings. Manifest/policy: exit 0, zero findings, 595 scanned and 63 non-UTF-8 files skipped. The new untracked r2 record was additionally checked directly with `tools.docs_check.check_file`, because the ordinary checker enumerates tracked files. Passing model/string tests do not establish actual Linux conversion, macOS sharing or WSL2 runtime behavior. Fix the four findings, add the corresponding regressions, and obtain isolated OS/runtime evidence without using the live development stack.

---

<a id="japanese"></a>
## 日本語

[→ To English](#english)

### 判定と範囲

**要修正。** r1、`af2ea6e..4cf3a22` の差分、周辺実装と仕様、GitHub の PR head を確認した。実際の Docker コマンド、スタック変更、導入、資格情報ファイルへのアクセス、commit、push、approve、merge はしていない。独立検査は一時領域と実行しない runner を使用した。所有者検査は既存のファイルシステム模型上で生成シェルを動かしたもので、Linux カーネルの実行試験ではない。

### 指摘

1. **R2-01 [HIGH; R1-01 未解決] 破壊操作の各段階で再検証する。** [lifecycle.py](../../installer/grdm_dev/lifecycle.py) 165–179 行は `down --volumes` 前に一度だけ検証し、その後の root wipe とホスト削除には再検証せずパスを渡す。独立した一時領域検査で、fake down の中で volumes を外部へのリンクへ差し替えると、そのパスへの wipe が発行され、後段の rmtree だけが14を返した。Docker は実行していないため目印は無傷。down 後、wipe とホスト削除の直前に再検証し、ディレクトリの同一性の変化も拒み、各境界での差し替えを試験する。render/up の検証も一時点の確認で、Docker が bind 元を解決するまでの原子性は保証しない。検査から使用までに変わる競合（TOCTOU）の限界と、信頼された checkout を同時に変更しない前提を明記するか、より強い制限を設ける。再検証だけではすべての競合を消せない。

2. **R2-02 [HIGH; R1-01 未解決] ホスト側削除にも mount 境界を適用する。** [compose.py](../../installer/grdm_dev/compose.py) 1011–1027 行は直下の volume と device 番号だけを調べる。[lifecycle.py](../../installer/grdm_dev/lifecycle.py) 179 行の通常の `shutil.rmtree` はファイルシステム境界を守らない。コンテナの `find -xdev` が飛ばした書込可能な深い mount もホスト側は辿り、mount 点自体の削除に失敗する前に中身を消し得る。同じ filesystem の bind mount は device 番号と `-xdev` の両方を通過し、runtime/volumes ルート自体の mount も検査しない。SPEC-02 の「深い mount を越えない」と矛盾する。同じ device の bind を含め mount 情報で拒否するか、同じ境界を守る削除を実装し、飛ばした mount を後段で辿らず失敗として残す。静的指摘であり、mount 作成や破壊的な実機再現はしていない。

3. **R2-03 [MEDIUM; R1-03 一部未解決] 所有者の不一致から安全な filesystem と判定しない。** [compose.py](../../installer/grdm_dev/compose.py) 428–435 行は chown が0でも目標 UID/GID にならなければ成功で戻る。これだけでは macOS 共有とも、実際の非 root の書き手が使えるとも証明できない。最後のディレクトリ変更も読み返さない。既存模型を独立に拡張し、最後のディレクトリ chown が黙って無効になる場合を試すと、生成シェルは0で終わり、1000:1000 が必要な private ディレクトリが0:0に残った。所有者を保持しない例外は、確認した共有方式と書き手のアクセス証拠に限定し、予期しない不一致は失敗にする。ファイルだけでなくディレクトリの返却も確認し、成功を返す無効な変更を試験する。通常の非0の chown は set -e で停止する。GNU への変更は既知のイメージ問題を改善するが、各 mount の変更結果まで証明しない。

4. **R2-04 [MEDIUM; R1-04 一部未解決] bind mount の明示拒否は前提失敗にする。** [doctor.py](../../installer/grdm_dev/doctor.py) 122–139 行は exit 125 をすべて警告にするため、エンジンが mount を明示的に拒否した場合も通常の doctor は導入を続けさせる。`GRDM_DOCKER_SHARED=1` を明示する必要さえない。共有/mount の明示拒否とイメージ取得不能・判定不能を区別し、前者は13にして試験を追加する。override は報告に残す。既存試験はファイル不在と pull 失敗を扱うが、エンジンの mount 拒否は扱わない。

### r1 の判定と指定事項

- **R1-01: 一部修正、未解決。** 既存の runtime/ルート/volume のリンクと直下の別 device を reset/up 前に拒否し、render も対象 bind 名を検証する。R2-01・02 が残る。
- **R1-02: 機能修正あり、実行証拠は外部。** unoconv は所有者設定を待ち、CHOWN と DAC_OVERRIDE 以外を除去する。[例外](../../manifest/hardening.json) はイメージ、共有 private ファイル、変換の観測、見直し日2027-01-31、M4 の unoserver 置換を記録し、SPEC-03 の欄を満たす。DAC_OVERRIDE は private 入力の読取と uid1000 の /tmp への作成に十分で、読取専用の回避権限だけでは足りない。ただしパス限定の権限ではなく、文書変換器を侵害されれば書込可能なコンテナ filesystem と wb_tmp 全体で通常のアクセス検査を越え得る。内部ネットワークと no-new-privileges はその危険を除かない。「共有 group は不可能」は現イメージと private ファイル構成についての説明であり、書き手 UID で動かす方法や group 権限準備の不可能性までは証明していない。記録された暫定例外として扱い、全体で最小権限と断定しない。予定された近代化で非 root の変換器を優先する。今回実変換は再試験しておらず、manifest の観測に対応する再現ログは差分に添付されていない。
- **R1-03: 大きく改善、一部未解決。** 毎回全体を辿り、private ディレクトリを一時的に root 所有にし、ファイルを先に、ディレクトリを深い順に返す。最上位だけを信頼せず再試行する。模型は所有者混在、入れ子0700、中断、失敗と再試行、000拒否を試す。R2-03 が残る。一時的に group も root へ変えるため、失敗後は再試行まで中間状態が残り得るが、これは文書化した回復モデル内。所有者段に広い capability は増やしていない。
- **イメージの責務:** manifest は volume_owner_init を postgres に所属させ、template と生成試験も一致する。自身の例外は root＋CHOWN のみ、read-only、no-new-privileges、再起動なしで、postgres サービスの広い例外は継承しない。無効だった uutils から GNU を選んだ理由は明記されている。ただし実際は `postgres:9.6`、digest は null で固定 digest ではない。SPEC-01 は固定まで null を許すが、SPEC-02/doctor の「固定イメージ」は過大な表現。プラットフォーム間で GNU の実測挙動に依存する前に実測イメージを記録・固定する。今回イメージ実体は検査していない。
- **R1-04: WSL 修正は解決、macOS は一部。** checkout に一時ファイルを作り chmod 0600 を読み返して消す方式になり、接頭辞の推測を除いた。不明は警告であり証明ではない。macOS は manifest を read-only bind し、ネットワークなし・capability 除去・no-new-privileges で確認し、override は警告付きで省略する。R2-04 が残る。既知のファイル名の一覧だけなので、内容の同一性や全 runtime mount までは証明せず、古い remote checkout でも通り得る。mutable な postgres tag を pull し得るため、表の「読むだけ」は bind についてでありエンジンの全副作用についてではない。
- **R1-05: 解決。** fixture 修正済み、manifest/方針検査は0件・終了0。
- **R1-06: 解決。** PR34 r2 は origin/develop とバイト単位で同一で、相対リンクが復元された。廃止 [template pointer](../../installer/grdm_dev/templates/elasticsearch_data_init.json) は歴史的用途を説明し、どの部品もサービスに列挙しない。SPEC-06 §8 の原文保持を満たす。pointer は旧実行実装そのものではない。

### 検証

PR checkout で実行した。

```sh
PYTHONPATH=installer python3 -m unittest discover -s installer/tests
PYTHONPATH=installer python3 -m unittest discover -s tools/tests
python3 tools/docs_check.py
python3 tools/manifest_check.py
```

installer は終了0、461件、27.026秒、10 skip。tools は終了0、92件、3.691秒。文書は終了0、103件、8免除、22警告。manifest/方針は終了0、指摘0件、595走査、非UTF-8の63件を省略。通常の文書検査は追跡済みファイルを列挙するため、新規未追跡 r2 も tools.docs_check.check_file で直接検査した。模型・文字列試験の合格は実 Linux 変換、macOS 共有、WSL2 実行の証明ではない。4指摘の修正と回帰追加、および実機開発スタックを使わない隔離 OS/実行証拠が残る。
