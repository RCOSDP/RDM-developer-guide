# REV PR4 Remove GA review r2 / GA削除レビュー r2

> **Summary:** Pass for the default-disabled acceptance scope; R1-01 is closed. Activation does not request external resources by default, and request parameters cannot enable the integration.
> **概要:** 既定で無効という受入範囲で合格、R1-01は解消です。既定では起動しても外部要求が発生せず、要求パラメーターで連携を有効にできません。

**Jump:** [English](#english) · [日本語](#japanese)

- Version / 版: 0.1 — 2026-11-10. **Learned:** Omitting the Hypothesis helper blocks activation even when a caller sends the start event; explicit server configuration retains compatibility. ／ Hypothesis補助スクリプトを含めなければ呼出元が起動イベントを送っても起動せず、サーバーの明示設定で互換性は保てると分かった。
- Applies to: RCOSDP/RDM-modular-file-renderer-dev2027 PR #4; delta from `2ff5e0282d1103f2bb1b94e56b6bbc8eea953f46` to `c20c0f9142d9fb1b26397dbeb266e9dc8b4f2c0e`.
- Related: [Review index](README.md) · [SPEC-06](../spec/06_documentation_conventions.md) · [r1](2026-11-10_RDM-modular-file-renderer-dev2027_PR4_Remove_GA_r1.md)
- Used by: [Acceptance review records](README.md)

---

<a id="english"></a>
## English

[→ 日本語版へ](#japanese)

### Verdict

**Pass. R1-01 closed for the assigned default-disabled scope.** The single new commit changes the default to False, documents explicit opt-in, and adds default-disabled and opt-in template tests. No new blocking finding was found. Hypothesis remains intentionally available for the RDM-ember-osf caller; deployments that explicitly enable it still request its external loader. This verdict does not assert zero external requests under explicit opt-in.

### Evidence

Independent review observations, not canonical manifest data:

```toon
checks[5]{check,result}:
  default_activation,zero external requests after startHypothesis and pagerendered
  opt_in_control,two hypothes.is/embed.js attempts captured and aborted
  PDF_render,both modes show first-page canvas 1019 x 1319 and 14 total pages
  browser_errors,zero in both modes
  GA_template_scan,16 templates scanned with no matches
```

The isolated Chromium harness renders the actual Mako template and serves checked-out assets and the bundled sample PDF through request interception. It derives False from the checked-out settings assignment, sends the start message and a synthetic page-rendered event in both modes, and aborts every external request. The viewer URL also contains `enable_hypothesis=true`, `ENABLE_HYPOTHESIS=1`, and `PDF_EXTENSION_CONFIG_ENABLE_HYPOTHESIS=1`; the default output still omits the activation helper.

The server-side parameter conclusion comes from code inspection, not a live HTTP integration test: `mfr/settings.py` SettingsDict reads environment or configuration dictionaries; `mfr/extensions/pdf/settings.py:11` supplies False when absent. Both branches in `mfr/extensions/pdf/render.py:36,53` pass only `settings.ENABLE_HYPOTHESIS`. `RenderHandler.get` passes metadata and URLs to the renderer, with no request-to-setting override. The template gates the helper at line 425. Query parameters therefore cannot enable this flag. The opt-in control confirms that the browser harness detects the remaining external path.

### Limits and reproduction

No full Python renderer dependency stack, new pytest tests, or deployed C5 stack was run locally. GitHub showed two build-image checks in progress when read; CI completion is not claimed. No Docker operations, runtime/.env access, commits, pushes, approvals, merges, or closures were performed. Review scope is the new commit; r1 evidence remains its own record.

Artifacts are under `/private/tmp/rev-pr4-r2-f660e758/`: detached clone `repo`, harness `check.py`, `results.txt`, and screenshots. Run from that directory using the existing r1 Python environment:

```sh
/private/tmp/rev-pr4-4100a030/venv/bin/python check.py
```

Expected output is zero default external requests and a detected Hypothesis request in the opt-in control. No code revision remains requested by REV; CI completion and acceptance remain with the coordinator.

---

<a id="japanese"></a>
## 日本語

[→ To English](#english)

### 判定

**Pass（合格）。指定された既定無効の範囲でR1-01を解消と判定します。** 新規1コミットは既定値をFalseに変更し、明示的な有効化を説明し、既定無効と有効化のテンプレート試験を追加しています。新たな阻害指摘はありません。RDM-ember-osfの呼出元向けにHypothesisは意図的に残り、配備で明示的に有効化すると外部ローダーを要求します。有効化した場合まで外部要求ゼロと判定したものではありません。

### 証拠

次は独立レビューの観測結果であり、正本のマニフェストではありません。

```toon
checks[5]{check,result}:
  既定での起動,startHypothesisとpagerendered後の外部要求ゼロ
  有効設定の対照,hypothes.is/embed.js要求2件を捕捉して遮断
  PDF描画,両設定で第1ページcanvas 1019 x 1319と全14ページを確認
  ブラウザーエラー,両設定でゼロ
  GAテンプレート走査,16テンプレートで一致なし
```

独立Chromiumハーネスで実際のMakoテンプレートを展開し、clone内の資産と同梱PDFを要求捕捉で配信しました。設定の代入式からFalseを取得し、両設定で起動メッセージと合成ページ描画イベントを送信し、すべての外部要求を遮断しました。ビューアーURLには `enable_hypothesis=true`、`ENABLE_HYPOTHESIS=1`、`PDF_EXTENSION_CONFIG_ENABLE_HYPOTHESIS=1` も付けましたが、既定の出力には起動用補助スクリプトが含まれません。

サーバー側でパラメーターが設定を変えられないという結論は、稼働HTTP統合試験ではなくコード確認に基づきます。`mfr/settings.py` のSettingsDictは環境変数または設定辞書を参照し、`mfr/extensions/pdf/settings.py:11` は値がなければFalseを使います。`mfr/extensions/pdf/render.py:36,53` の両分岐は `settings.ENABLE_HYPOTHESIS` だけを渡します。`RenderHandler.get` はメタデータとURLを渡し、要求から設定への上書き経路はありません。テンプレート425行目で補助スクリプトの出力を制御します。従ってクエリーパラメーターではこのフラグを有効化できません。有効設定の対照試験により、残存する外部経路をハーネスが検出できることも確認しました。

### 範囲と再現

Pythonレンダラーの依存一式、新規pytest試験、稼働中のC5スタックはローカルでは実行していません。取得時点のGitHubではbuild-image 2件が進行中であり、CI完了とは主張しません。Docker操作、runtime/.env参照、commit、push、approve、merge、closeは行っていません。対象は新規コミットであり、r1の証拠は元の記録に残します。

成果物は `/private/tmp/rev-pr4-r2-f660e758/` 配下のdetached clone `repo`、ハーネス `check.py`、`results.txt`、スクリーンショットです。同ディレクトリから既存のr1 Python環境で実行します。

```sh
/private/tmp/rev-pr4-4100a030/venv/bin/python check.py
```

期待結果は既定設定で外部要求ゼロ、有効設定の対照でHypothesis要求の検出です。REVから要求するコード修正は残っていません。CI完了確認と受入はコーディネーターに残ります。
