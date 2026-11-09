# PR36 Preflight and ownership review r5 / 事前検査と所有者設定のレビュー r5

> **Summary:** Pass for R4-01 and regressions introduced by its fix. Failed walks now stop both checks.
> **概要:** R4-01の修正とその回帰確認は合格。走査失敗は両検査を停止する。

**Jump:** [English](#english) · [日本語](#japanese)

- Version / 版: 0.1 — 2026-11-10. **Learned:** Capturing a walk without a pipeline and checking its status preserves failure even when stdout is empty. ／ パイプなしで走査結果を取得して終了値を確認すると、標準出力が空でも失敗を伝播できる。
- Applies to: PR #36, `e7eb684..ccb1159`, head `ccb1159a2fb492a90987f41c00dd551740abca67`; REV（担当レビュワ, Codex Astra）.
- Related: [Review index](README.md) · [SPEC-06](../spec/06_documentation_conventions.md) · [r4](2026-11-10_RDM-developer-guide_PR36_Preflight_Ownership_r4.md) · [SPEC-02](../spec/02_installer_cli.md).
- Used by: the coordinator's source-absorption decision and subsequent platform verification. ／ 調整担当のソース吸収判断と後続の実機検証。

---

<a id="english"></a>
## English

[→ 日本語版へ](#japanese)

### Verdict and scope

**Pass. R4-01 is closed; no new finding in this fix and its regressions.** Reviewed the r4 finding, the exact patch, and surrounding generated shell and test harness in [compose.py](../../installer/grdm_dev/compose.py) and [test_preflight.py](../../installer/tests/test_preflight.py). This verdict is scoped to the requested round, not a fresh review of all PR changes.

The access walk and both owner listing walks no longer pipe through `head`. Each command substitution explicitly exits 1 on failure. The opening walk is in the loop body, so the loop-condition exception to `set -e` cannot hide its failure. The remaining modifying walks are standalone commands under `set -e`, and `fix` is invoked directly, outside conditional/AND/OR contexts. The root `stat` is now a standalone assignment under `set -e`; its failure cannot select the ownership-ignoring filesystem fallback. Existing directory read-back rejects an empty failed `stat` result as unequal to the required owner. No additional success-masking path was identified in this scope.

Whole output is retained instead of truncating at one path. Output is used as quoted diagnostic/comparison text, not reinterpreted as path arguments. This removes early-pipe termination concerns; storage now scales with the matching output. No large-tree performance claim is made.

### Independent verification

The four new fault tests execute the generated shell, with only filesystem tools modeled. Their selectors distinguish opening, verification and access listings; the injected failure emits stderr and exits 1 with empty stdout. Loading the two old generator functions from `e7eb684` into memory made **all four tests fail with actual shell exit 0**, without harness errors. Restoring the head functions made **all four pass**. This includes the failed-root-stat case on virtiofs.

A separate counter-based injection failed each of six owner `find` invocations independently: opening listing, opening mutation, repeated listing, file mutation, file verification and directory hand-back. Every run exited 1 and contained the injected diagnostic. A separate access probe used real `mktemp` and `rm` in a temporary directory and replaced only `find`: exit 1, empty stdout, no `usable by`, and no probe left behind. These are shell/model tests on macOS, not Linux permission or VM filesystem measurements.

From the designated checkout root, independently ran:

```sh
PYTHONPATH=installer python3 -m unittest discover -s installer/tests
PYTHONPATH=installer python3 -m unittest discover -s tools/tests
python3 tools/docs_check.py
python3 tools/manifest_check.py
git diff --check e7eb684..ccb1159
```

Observed results:

```toon
checks[5]{name,exit,result}:
  installer,0,490 tests / 10 skipped / 33.209 seconds
  tools,0,92 tests / 2.959 seconds
  docs_check,0,106 checked / 8 exempt / 22 warnings
  manifest_check,0,600 scanned / 63 non-UTF-8 skipped / zero findings
  diff_check,0,no whitespace errors
```

Evidence: `/tmp/pr36-r5-rfBLb5/` contains four check logs and `probe.py` / `probe.log`. The new untracked review record is checked separately with `tools.docs_check.check_file`, since the normal checker lists tracked files. GitHub head matched the requested head and all reported checks were successful. Real Linux/WSL2/Docker Desktop startup remains subsequent platform verification. No Docker command or stack mutation, runtime credential-file access, source edit, commit, push, approval, merge or closure was performed. Deliverables are this uncommitted record and one PR comment.

---

<a id="japanese"></a>
## 日本語

[→ To English](#english)

### 判定と範囲

**合格（pass）。R4-01は解決。この修正とその回帰範囲で新規指摘なし。** r4の指摘、指定差分、[compose.py](../../installer/grdm_dev/compose.py)の生成シェルと[test_preflight.py](../../installer/tests/test_preflight.py)の試験基盤を確認した。今回の判定は指定された範囲に限り、PR全体の新規全面レビューではない。

アクセス走査と所有者設定の2つの列挙走査から `head` へのパイプが除去され、各コマンド置換は失敗時に明示的に1終了する。開放走査はループ本体に入り、条件式では `set -e` が無効になる問題も解消した。残る変更用走査は `set -e` 下の独立したコマンドで、`fix` 呼出しも条件式やAND/ORリストの外にある。直下の `stat` は独立した代入になり、失敗して所有者を保持しないfilesystemの例外へ進むことはない。既存のディレクトリ読戻しでも、失敗した `stat` の空出力は必要な所有者と不一致になって拒否される。この範囲で追加の成功への誤変換は認めなかった。

最初の1パスに切り詰めず全出力を保持するが、引用された診断・比較文字列として使い、パス引数として再解釈しない。パイプの早期終了問題はなくなり、保持量は一致した出力の量に応じる。大規模ツリーの性能を測定したという主張はしない。

### 独立検証

追加4テストは、filesystemコマンドを模型に置換して生成シェルを実行する。開放・検証・アクセスの列挙を区別して障害を注入し、標準エラーだけを出して1終了する。`e7eb684` の旧生成関数2つをメモリ内に読み込むと、**シェルが実際に0終了して4件すべて失敗**し、試験基盤のエラーはなかった。headの関数に戻すと**4件すべて成功**した。virtiofsでの直下 `stat` 失敗も含む。

別の呼出し回数による障害注入で、所有者設定の6回の `find`（開放列挙、開放変更、再列挙、ファイル変更、ファイル検証、ディレクトリ返却）を個別に失敗させ、すべて1終了と注入した診断を確認した。別のアクセス試験では一時ディレクトリで実際の `mktemp` と `rm` を使用し、`find` だけを失敗させた。1終了、標準出力は空、`usable by` 表示なし、検査ファイルの残存なしだった。macOS上のシェルと模型の試験であり、Linuxの権限やVM filesystemの実測ではない。

指定checkoutのルートで英語側の5コマンドを独立実行し、すべて0終了した。installerは490件・10 skip・33.209秒、toolsは92件・2.959秒、docs_checkは106件・8免除・22警告、manifest_checkは600走査・非UTF-8の63件省略・指摘0件、差分の空白検査も成功した。

証跡は `/tmp/pr36-r5-rfBLb5/` の4検査ログと `probe.py` / `probe.log`。通常のdocs_checkは追跡済みファイルを列挙するため、新規未追跡のレビュー記録は `tools.docs_check.check_file` でも個別検査する。GitHubのheadは指定値と一致し、表示されたチェックはすべて成功していた。実Linux/WSL2/Docker Desktop起動は後続の実機検証として残る。Dockerコマンド・スタック変更、runtime資格情報ファイル参照、ソース修正、commit、push、approve、merge、closeは行っていない。成果物は未コミットの本記録とPRコメント1件。
