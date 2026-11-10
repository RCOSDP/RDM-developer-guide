# REV PR4 Remove GA review r1 / GA削除レビュー r1

> **Summary:** GA removal and PDF rendering pass, but an external Hypothesis request remains. The verdict is changes requested against the assigned no-other-external-request criterion.
> **概要:** GA削除とPDF描画は合格ですが、Hypothesisへの外部要求が残ります。指定された「他の外部要求も残さない」基準では changes requested です。

**Jump:** [English](#english) · [日本語](#japanese)

- Version / 版: 0.1 — 2026-11-10. **Learned:** Removing GA eliminates the unconditional tracker but does not eliminate the optional Hypothesis network path. ／ GA削除で無条件の追跡通信は消えるが、Hypothesis起動時の通信経路は残ると分かった。
- Applies to: RCOSDP/RDM-modular-file-renderer-dev2027 PR #4, head `2ff5e0282d1103f2bb1b94e56b6bbc8eea953f46`.
- Related: [Review index](README.md) · [SPEC-06](../spec/06_documentation_conventions.md)
- Used by: [Acceptance review records](README.md)

---

<a id="english"></a>
## English

[→ 日本語版へ](#japanese)

### Verdict and finding

**Changes requested.** GA removal itself passes. P2 / R1-01: `mfr/server/static/js/mfr.child.hypothesis.js:58–62` still appends `https://hypothes.is/embed.js`. With the default `ENABLE_HYPOTHESIS=True`, the template includes this helper. Sending `startHypothesis` and then emitting a `pagerendered` event reaches this external request. This is an existing path, explicitly disclosed by the PR author, rather than a newly introduced regression; it nevertheless fails the assigned requirement to leave no other external request in the PDF viewer.

Remove or serve the integration locally, or explicitly narrow the acceptance requirement to initial PDF display before accepting this PR. Add a browser regression check covering the Hypothesis activation path and rejecting external origins; the added HTML substring test alone cannot detect requests from linked JavaScript.

### Evidence

The following results were independently observed at the reviewed head; they are review data, not a canonical manifest.

```toon
checks[5]{check,result}:
  renderer_templates,16 scanned and no GA references
  pdf_template_hypothesis_on,first page rendered with 14 total pages
  pdf_template_hypothesis_off,first page rendered with 14 total pages
  normal_external_requests,zero in both configurations
  hypothesis_activation,https://hypothes.is/embed.js attempted and blocked
```

The scan covered every file under renderer `templates` directories and looked for GA domains, GoogleAnalyticsObject, GA_TRACKING identifiers and quoted ga calls. The changed renderer/settings/helper were also inspected. Both render configurations produced a 1019 × 1319 canvas with no page errors; the screenshot visibly contains the sample paper. All four reported GitHub checks (two build-image and two tests (mfr)) passed when read.

The isolated harness rendered the actual Mako template and served the unchanged checked-out PDF.js assets and bundled sample PDF through Playwright request interception. All nonlocal requests were captured and aborted. After normal rendering, a start message and a synthetic pagerendered event exercised the remaining helper branch; two embed attempts were observed during that run. This proves the external path exists, not that every real user action triggers it.

### Boundaries and reproduction

The local harness does not run the full Python PdfRenderer dependency stack or the deployed C5 integration. The added pytest test was not independently run locally; the CI status is separate evidence. No Docker operations, runtime/.env reads, commits, pushes, merges, approvals or closure were performed.

Review artifacts are in `/private/tmp/rev-pr4-4100a030/`: the detached clone in `repo`, harness `check.py`, `results.txt`, and viewer screenshots. To repeat with the already prepared environment, run from that scratch directory:

```sh
./venv/bin/python check.py
```

Expected: 16 templates without GA, successful rendering in both modes, no normal external requests, and an intercepted Hypothesis embed request after activation. The remaining work is to resolve R1-01 or explicitly change the acceptance scope, then rerun the affected checks.

---

<a id="japanese"></a>
## 日本語

[→ To English](#english)

### 判定と指摘

**Changes requested（修正要求）。** GA削除自体は合格です。P2 / R1-01: `mfr/server/static/js/mfr.child.hypothesis.js:58–62` に `https://hypothes.is/embed.js` の追加処理が残ります。既定の `ENABLE_HYPOTHESIS=True` ではテンプレートがこの補助スクリプトを読み込みます。`startHypothesis` の送信後に `pagerendered` イベントを発生させると外部要求に到達します。PR作成者も明記した既存経路であり、今回新たに導入した不具合ではありません。ただし、指定された「PDFビューアに他の外部要求も残さない」条件を満たしません。

この連携を削除またはローカル配信するか、受入条件を初期PDF表示だけに限定すると明示してから受け入れてください。Hypothesis起動経路も実行し、外部オリジンへの要求を検出するブラウザー回帰試験が必要です。追加されたHTML文字列の試験だけでは、読み込んだJavaScriptからの要求を検出できません。

### 検証結果

次は対象headで独立に確認したレビュー結果であり、正本のマニフェストではありません。

```toon
checks[5]{check,result}:
  レンダラーテンプレート,16個を走査しGA参照なし
  Hypothesis有効のPDFテンプレート,全14ページ中の第1ページ描画成功
  Hypothesis無効のPDFテンプレート,全14ページ中の第1ページ描画成功
  通常表示時の外部要求,両設定でゼロ
  Hypothesis起動,https://hypothes.is/embed.jsへの要求を検出し遮断
```

レンダラーの全templates配下のファイルを対象に、GAドメイン、GoogleAnalyticsObject、GA_TRACKING識別子、引用符付きga呼び出しを走査しました。変更されたrenderer、settings、補助スクリプトも確認しました。両設定で1019 × 1319のcanvasが生成され、ページエラーはありませんでした。スクリーンショットでサンプル論文の描画も確認しました。取得時点のGitHubチェック4件（build-image 2件、tests (mfr) 2件）はすべて成功でした。

独立ハーネスは実際のMakoテンプレートを展開し、チェックアウトした未変更のPDF.js資産と同梱PDFをPlaywrightの要求捕捉で配信しました。ローカル以外の要求は記録して遮断しました。通常描画後に起動メッセージと合成pagerenderedイベントを送信し、残る補助スクリプトの経路を実行したところ、embed要求を2回観測しました。これは外部経路の存在を示し、すべての利用者操作で発生すると主張するものではありません。

### 検証範囲と再現方法

ローカルハーネスではPython PdfRendererの依存一式や稼働中のC5統合試験は実行していません。追加されたpytest試験もローカルでは独立実行しておらず、CIの成功は別の証拠です。Docker操作、runtime/.envの参照、commit、push、merge、approve、closeは行っていません。

成果物は `/private/tmp/rev-pr4-4100a030/` にあり、`repo` がdetached状態のclone、`check.py` がハーネス、`results.txt` が結果で、ビューアーのスクリーンショットも保存しました。準備済みの環境で再実行する場合、このscratchディレクトリで次を実行します。

```sh
./venv/bin/python check.py
```

期待結果は、16テンプレートにGAがないこと、両設定での描画成功、通常表示時の外部要求ゼロ、起動後のHypothesis embed要求の捕捉です。残作業はR1-01の解消、または受入範囲変更の明示と、該当検証の再実行です。
