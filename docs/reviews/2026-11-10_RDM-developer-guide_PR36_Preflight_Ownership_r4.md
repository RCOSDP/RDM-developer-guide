# PR36 Preflight and ownership review r4 / 事前検査と所有者設定のレビュー r4

> **Summary:** Changes requested: the two r3 examples are fixed, but a failed traversal is still reported as usable.
> **概要:** 要修正。r3の2例は解消したが、走査失敗を使用可能と報告する。

**Jump:** [English](#english) · [日本語](#japanese)

- Version / 版: 0.1 — 2026-11-10. **Learned:** A successful final pipeline command does not prove that the directory traversal succeeded. ／ パイプライン末尾の成功はディレクトリ走査の成功を証明しない。
- Applies to: RDM-developer-guide PR #36, head `e7eb684209bc740d991da99c9e2832e2c2e11573`; REV（担当レビュワ, Codex Astra）.
- Related: [Review index](README.md) · [SPEC-06](../spec/06_documentation_conventions.md) · [r3](2026-11-10_RDM-developer-guide_PR36_Preflight_Ownership_r3.md) · [SPEC-02](../spec/02_installer_cli.md).
- Used by: the coordinator's source-absorption decision and follow-up verification. ／ 調整担当のソース吸収判断と後続検証。

---

<a id="english"></a>
## English

[→ 日本語版へ](#japanese)

### Verdict and finding

**Changes requested. R4-01 [P2]: propagate traversal failures before releasing writers.** In [compose.py](../../installer/grdm_dev/compose.py), line 470 assigns `bad=$(find ... -print | head -n 1)`. POSIX `sh` takes the pipeline status from `head`, so `set -e` does not reject a failed `find`. A directory read/stat failure such as an I/O error can produce only stderr and exit 1; `bad` is empty and line 472 prints `usable`, allowing dependent writers to start despite an incomplete check. This especially matters on the ownership-ignoring filesystem fallback, where this walk is the evidence for access to existing data.

An independent fault-injection probe executed the unchanged generated shell with its volume prefix redirected into a temporary directory. Only `find` was replaced with a program printing `find: existing-child: Input/output error` to stderr and exiting 1. Real `mktemp` and `rm` ran. The overall exit was **0**, stdout reported `usable by 501`, and no probe file remained. This demonstrates the shell's error propagation, not a measured fault in a particular VM filesystem. No concurrent path mutation is needed. Collect/check the traversal status independently of truncating its output, refuse on failure, and add a regression for failed traversal with no matching stdout; account for intentional early termination if retaining `head`.

### r3 closure and regression review

**R3-01: the reported inaccessible-child case is fixed, but R4-01 prevents full closure of fail-closed access verification.** The generated check runs as uid 1000 or 999 with capabilities dropped, after owner initialization; writers wait on successful completion. GNU `find` now checks read/search/write access on directories and readability on non-symlink files, pruning denied directories. The writable-root/private-child, unreadable-file, read-only-directory and usable-tree model tests pass. The walk does not follow symlinks or cross filesystem boundaries. Read-only regular files are intentionally accepted; this is the documented access contract, not a guarantee that every file can be modified. The test model is not an actual uid-1000 kernel execution on this Mac.

**R3-02: closed.** `mktemp "$v/.grdm-write-probe.XXXXXX"` creates exclusively and cleanup removes only its returned pathname. Tests using actual temporary files confirm preservation of a pre-existing fixed-name regular file, a symlink and its target, and removal of only the new probe. The earlier fixed-name truncation is gone. The documented no-concurrent-mutation boundary still applies.

Read r3 and the r3-to-head patch plus surrounding owner/dependency logic. The earlier reset identity, mount-table rejection and mount-denial exit handling remain covered by the full tests; no further regression was identified in that scope.

### Validation and limits

In a fresh private scratch clone at the exact head, ran:

```sh
PYTHONPATH=installer python3 -m unittest discover -s installer/tests
PYTHONPATH=installer python3 -m unittest discover -s tools/tests
python3 tools/docs_check.py
python3 tools/manifest_check.py
```

Observed results, not author claims:

```toon
checks[4]{name,exit,result}:
  installer,0,486 tests / 10 skipped / 33.316 seconds
  tools,0,92 tests / 3.016 seconds
  docs_check,0,105 checked / 8 exempt / 22 warnings
  manifest_check,0,599 scanned / 63 non-UTF-8 skipped / zero findings
```

`git diff --check` passed. The separate fault-injection result is a review finding despite the passing suite. Scratch evidence is `/private/tmp/rev-8275-oBBpKc/`, including `probe_pr36.py` and the four check logs. This new untracked record is checked directly with `tools.docs_check.check_file`; the normal checker lists tracked files. Real Linux/WSL2/Docker Desktop startup is still a later hardware prerequisite, not the reason for changes requested. No Docker command, stack mutation, runtime credential-file access, source edit, commit, push, approval, merge or closure was performed. Only the uncommitted record and one PR comment are delivered.

GitHub checks were all passing at review time.

---

<a id="japanese"></a>
## 日本語

[→ To English](#english)

### 判定と指摘

**要修正（changes requested）。R4-01 [P2]: 走査失敗を伝播してから書き手を起動すること。** [compose.py](../../installer/grdm_dev/compose.py) 470行は `bad=$(find ... -print | head -n 1)` としている。POSIX `sh` のパイプライン終了値は `head` の値になるため、`set -e` は `find` の失敗を拒否しない。ディレクトリ読取り/statのI/Oエラーなどで標準エラーだけを出して1終了すると、`bad` は空のまま472行で `usable` を表示し、不完全な検査でも依存する書き手が起動する。所有者変更を保持しないfilesystemの例外では、この走査が既存データへのアクセスを確認する根拠なので特に重要である。

独立した障害注入で、生成シェルのvolume接頭辞だけを一時ディレクトリへ変更した。`find` だけを `find: existing-child: Input/output error` を標準エラーへ出して1終了するプログラムに置換し、`mktemp` と `rm` は実物を使った。全体は **0終了**、標準出力は `usable by 501`、検査ファイルは残らなかった。特定VMの実障害を測定したものではなく、シェルの失敗伝播を実証したもの。同時パス変更は不要である。走査の終了値を出力の切詰めとは独立して検査し、失敗時は拒否すること。標準出力に該当パスが出ない走査失敗の回帰試験を追加し、`head` を残す場合は意図した早期終了も扱うこと。

### r3の解決状況と回帰確認

**R3-01: 報告されたアクセス不能な子の例は解消したが、失敗時拒否の確認はR4-01が残る。** 生成検査は所有者初期化後、capabilityを除去したuid1000/999で実行し、書き手は成功を待つ。GNU `find` はディレクトリの読取り・検索・書込みと、symlink以外のファイルの読取りを調べ、拒否したディレクトリをpruneする。直下書込可/private子、読取不能ファイル、読取専用ディレクトリ、使用可能ツリーの模型試験が合格した。symlinkを辿らずfilesystem境界を越えない。読取専用の通常ファイルは意図的に許す文書上の契約であり、全ファイルの変更可能性を保証するものではない。Mac上の模型試験はuid1000での実kernel検査ではない。

**R3-02: 解決。** `mktemp "$v/.grdm-write-probe.XXXXXX"` で排他的に作成し、返されたパスだけを削除する。実際の一時ファイルによる試験で、既存固定名の通常ファイル、symlinkとリンク先の保存、新規検査ファイルだけの削除を確認した。以前の固定名による切詰めはなくなった。文書化された同時変更なしの境界は引き続き適用される。

r3、r3からheadの差分、周辺の所有者設定と依存関係を確認した。以前のreset同一性検査、mount表による拒否、mount拒否時の終了処理は全体試験で引き続き確認され、この範囲では追加の退行を認めなかった。

### 検証と限界

正確なheadの専用scratch cloneで英語側の4コマンドを実行し、すべて0終了した。installerは486件・10 skip・33.316秒、toolsは92件・3.016秒、docs_checkは105件・8免除・22警告、manifest_checkは599走査・非UTF-8の63件省略・指摘0件だった。著者の報告ではなく独立実行結果である。`git diff --check` も成功した。試験合格とは別に、障害注入結果を指摘として残す。

証跡は `/private/tmp/rev-8275-oBBpKc/` の `probe_pr36.py` と4検査のログにある。通常のdocs_checkは追跡済みファイルを列挙するため、新規未追跡の記録は `tools.docs_check.check_file` でも直接検査する。実Linux/WSL2/Docker Desktop起動は後続の実機前提条件であり、要修正の理由ではない。Dockerコマンド、スタック変更、runtime資格情報ファイル参照、ソース修正、commit、push、approve、merge、closeは行わず、未コミット記録とPRコメント1件だけを成果物とする。

レビュー時のGitHubチェックはすべて成功していた。
