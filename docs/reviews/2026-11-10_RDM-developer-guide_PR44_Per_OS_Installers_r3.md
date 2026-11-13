# PR44 Per-OS installers review r3 / OS 別インストーラーレビュー r3

> **Summary:** REV passes the scoped revision: both r2 findings are closed, with no new regression found in the exercised cases.
> **概要:** REV は今回の差分を合格とする。r2 の二件は解決し、検証した範囲で新たな回帰は見つからなかった。

**Jump:** [English](#english) · [日本語](#japanese)

- Version / 版: 0.1 — 2026-11-10. **Learned:** retaining decoded paths in a variable preserves trailing newlines, and nonblocking opens allow file-type checks to reject FIFOs before reading or writing. ／ 復号したパスを変数に保持すれば末尾改行を保て、nonblocking で開けば読み書きの前に FIFO を種別検査で拒否できる。
- Applies to: [PR #44](https://github.com/RCOSDP/RDM-developer-guide/pull/44), diff `237387f..f789be9`, head `f789be9abb17c2ea172987ca83d3bb1ba13b74ac`.
- Reviewer / レビュワ: REV（担当レビュワ, Codex Astra）.
- Parent index / 親索引: [Reviews](README.md).
- Related: [r2](2026-11-10_RDM-developer-guide_PR44_Per_OS_Installers_r2.md) · [SPEC-02](../spec/02_installer_cli.md) · [SPEC-03](../spec/03_security_gate.md) · [SPEC-06](../spec/06_documentation_conventions.md).
- Used by / 利用先: [PR #44 revision and coordinator review / 修正と統括レビュー](https://github.com/RCOSDP/RDM-developer-guide/pull/44).

---

<a id="english"></a>
## English

[→ 日本語版へ](#japanese)

### Verdict and closure evidence

**Pass.** A clean detached clone was reviewed; no required changes were found in the scoped revision.

**R2-01 closed.** Direct assignment through `DECODED_MOUNT` avoids the command substitution that stripped trailing newlines. The original non-dry probe now exits 10 before stub sudo for all six filesystems: virtiofs, 9p, fuse.sshfs, vboxsf, fuse.vmhgfs-fuse and fuse.virtiofsd. The new repository test exercises one trailing newline, two trailing newlines and a literal backslash followed by `012` on each filesystem. The original space, tab, interior-newline, literal-backslash and repeated-trailing-newline probes also pass; the synthetic bind-table fixture still exits 10.

**R2-02 closed.** `_SAFE_OPEN` combines `O_NOFOLLOW` and `O_NONBLOCK`; `_regular_fd` checks the opened descriptor before reading or truncating/writing. The original reader probe returns a regular-file refusal within its two-second limit. Additional bounded subprocess probes reject writing a FIFO both without a reader and with a reader; no bytes reach the reader. The repository integration test checks exit 51 when a FIFO occupies the masked ZAP report destination. Regular-file creation, shorter UTF-8 overwrite/truncation and symlink-write refusal preserve expected behavior.

The original absolute, relative, nested, dangling and open-time replacement symlink probes still refuse reports. Nested WSL path aliases still exit 10, and replacing the logical alias after validation still reaches the original safe checkout. Runtime mode 0755 remains refused. The same-owner chmod gap still exists as recorded in r2; SPEC-03 now states the owner/ancestor stability precondition and does not claim race-proof isolation. This is not a new finding.

### Validation and limits

System `/usr/bin/python3` 3.9.6 on Darwin was used. Results are observed runs, not a canonical dataset mirror. Full logs and the added write probe are in `/tmp/pr44-rev-r3-r2SOON/`; the clean clone is `/tmp/pr44-rev-r3-r2SOON/repo`. The two original probe scripts remain in `/tmp/pr44-rev-r2-RXhzlP/` and were run from the new clone. Their exit 0 means the observation harness completed; their printed product results were inspected separately.

```toon
checks[8]{command,result,exit}:
  "PYTHONPATH=installer /usr/bin/python3 -m unittest discover -s installer/tests","643 tests; 10 skipped; OK",0
  "/usr/bin/python3 -m unittest discover -s tools/tests","93 tests; OK",0
  "/usr/bin/python3 tools/docs_check.py","153 files; 8 exempt; 38 warnings; passed before review",0
  "/usr/bin/python3 tools/manifest_check.py","695 tracked text files; 63 skipped; zero findings",0
  "bash -n installer/install-ubuntu.sh installer/install-macos.sh installer/prereq-lib.sh installer/install.sh","passed",0
  "/usr/bin/python3 /tmp/pr44-rev-r2-RXhzlP/variants.py","all targeted refusals observed; FIFO returned within 2 seconds",0
  "/usr/bin/python3 /tmp/pr44-rev-r2-RXhzlP/mount_variants.py","six filesystems exit 10 before sudo; bind-table fixture exit 10",0
  "/usr/bin/python3 /tmp/pr44-rev-r3-r2SOON/write_probes.py","FIFO refusal with/without reader; regular writes and symlink refusal passed",0
```

The tracked-file documentation check also passed after writing the record; a direct `check_file` call validates this untracked review separately (zero errors, exit 0).

No real platform install, native PowerShell/WSL execution or actual Linux bind mount was performed. Tests used temporary fixtures and stub runners; the grdm-dev stack and real runtime environment file were not touched. No commit, push, approval, merge or close was performed; the only GitHub write is one review comment. The review file is intentionally uncommitted and its index entry is left to the coordinator when incorporating the record. No further code changes are required for the two scoped findings; real-platform validation remains outside this review.

---

<a id="japanese"></a>
## 日本語

[→ To English](#english)

### 判定と解決の証拠

**Pass（合格）。** クリーンな detached clone で指定差分を確認し、修正必須の指摘はなかった。

**R2-01 解決。** `DECODED_MOUNT` への直接代入により、末尾改行を消すコマンド置換を回避している。元の非 dry-run プローブは、virtiofs・9p・fuse.sshfs・vboxsf・fuse.vmhgfs-fuse・fuse.virtiofsd の全六種類で sudo スタブに到達せず終了 10 となった。追加されたリポジトリ試験は、各 filesystem で末尾改行一つ・二つ・文字どおりのバックスラッシュと `012` を検証する。元の空白・タブ・途中の改行・バックスラッシュ・連続末尾改行のプローブも合格し、bind 行を模した fixture も引き続き終了 10 となる。

**R2-02 解決。** `_SAFE_OPEN` は `O_NOFOLLOW` と `O_NONBLOCK` を組み合わせ、`_regular_fd` は読込み・切詰め・書込みより前に開いた記述子を検査する。元の読込みプローブは二秒以内に通常ファイルでない旨を返す。追加の時間制限付き子プロセス試験では、読み手がいない FIFO と読み手がいる FIFO の両方への書込みを拒否し、読み手には一バイトも渡らなかった。リポジトリの統合試験は、マスク済み ZAP 報告の保存先が FIFO の場合の終了 51 を確認する。通常ファイルの新規作成、短い UTF-8 内容への上書きと切詰め、symlink への書込み拒否も正常だった。

元の絶対・相対・多段・リンク先なし・open 直前差替えの報告 symlink は引き続き拒否される。WSL の多段別名は終了 10、検証後の論理別名差替えも元の安全な checkout に到達する。runtime の 0755 は拒否される。同一所有者による chmod の競合は r2 の記録どおり残るが、SPEC-03 は所有者と祖先の安定性を前提として明記し、競合に耐える隔離とは主張していない。新たな指摘ではない。

### 検証と制限

Darwin のシステム `/usr/bin/python3` 3.9.6 を使った。結果は実行時の観測であり、正本データの写しではない。全ログと追加書込みプローブは `/tmp/pr44-rev-r3-r2SOON/`、clone は `/tmp/pr44-rev-r3-r2SOON/repo` にある。元の二つのスクリプトは `/tmp/pr44-rev-r2-RXhzlP/` にあり、新しい clone を作業ディレクトリとして実行した。終了 0 は観測用スクリプトの完了を表し、出力された製品側の結果も別途確認した。

```toon
checks[8]{command,result,exit}:
  "PYTHONPATH=installer /usr/bin/python3 -m unittest discover -s installer/tests","643 tests; 10 skipped; OK",0
  "/usr/bin/python3 -m unittest discover -s tools/tests","93 tests; OK",0
  "/usr/bin/python3 tools/docs_check.py","153 files; 8 exempt; 38 warnings; passed before review",0
  "/usr/bin/python3 tools/manifest_check.py","695 tracked text files; 63 skipped; zero findings",0
  "bash -n installer/install-ubuntu.sh installer/install-macos.sh installer/prereq-lib.sh installer/install.sh","passed",0
  "/usr/bin/python3 /tmp/pr44-rev-r2-RXhzlP/variants.py","all targeted refusals observed; FIFO returned within 2 seconds",0
  "/usr/bin/python3 /tmp/pr44-rev-r2-RXhzlP/mount_variants.py","six filesystems exit 10 before sudo; bind-table fixture exit 10",0
  "/usr/bin/python3 /tmp/pr44-rev-r3-r2SOON/write_probes.py","FIFO refusal with/without reader; regular writes and symlink refusal passed",0
```

文書作成後の追跡ファイル検査も合格し、未追跡のレビュー文書自体は `check_file` を直接呼んで別途検証した（エラーゼロ・終了 0）。

実プラットフォームのインストール、ネイティブ PowerShell・WSL、Linux の実 bind mount は未実施。一時 fixture とスタブを使い、grdm-dev スタックと実環境の runtime 環境ファイルには触れていない。commit・push・承認・merge・close は行わず、GitHub への書込みはレビューコメント一件だけである。レビュー文書は意図どおり未コミットで、索引への追加は記録を取り込む統括側に委ねる。対象二件について追加のコード修正は不要であり、実プラットフォームの検証は今回のレビュー範囲外として残る。
