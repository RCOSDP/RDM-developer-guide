# REV PR #28 CAS prebuilt review r1 / CAS 配布イメージレビュー r1

> **Summary:** The pinned image and manifest checks pass, and the revised tests pass. Hold acceptance for a factual wording correction and the failing secret scan.
> **概要:** 固定したイメージとマニフェスト検査、修正後のテストは成功。事実に関する文言修正と秘密情報走査の失敗解消まで受入を保留する。

**Jump:** [English](#english) · [日本語](#japanese)

- Version / 版: 0.1 — 2026-11-06. **Learned:** a successful prebuilt pull does not prove retagging, and passing manifest checks does not establish a clean history scan. ／ 配布イメージの取得成功はタグ付けの実施を証明せず、マニフェスト検査の成功は履歴の秘密情報走査の成功を意味しない。
- Applies to: [PR #28](https://github.com/RCOSDP/RDM-developer-guide/pull/28), `fix/manifest-cas-prebuilt` → `develop`, head (reviewed revision / 検査した版) `cc2e9c37fa891697e08e9ef24bf35a41308bb427`.
- Reviewer: REV（担当レビュワ, Codex Astra）.
- Related: [Review index](README.md) · [SPEC-01](../spec/01_manifest.md) · [SPEC-06](../spec/06_documentation_conventions.md) · [DEMO-20](../demo/20_core_install_mac_studio.md) · [Shared glossary](../reference/REF-01_Glossary.md).
- Used by: [Status board](../status/README.md).

---

<a id="english"></a>
## English

[→ 日本語版へ](#japanese)

### Verdict and findings

**Hold — R1 wording correction and R2 security-check disposition required.** This is a written verdict, not GitHub approval. The manifest (component configuration) change itself satisfies SPEC-01.

**R1 / P2 — Correct the claimed retagging in both languages.** DEMO-20 lines 103 and 199 say “image tagged for Compose” and “Compose 用のタグ付け”. The prebuilt branch in `installer/grdm_dev/build.py` pulls the digest reference and records that same reference; it does not run a tag operation. Compose (the tool that connects the application containers) uses the reference directly, as specified in SPEC-01. Replace the wording with “digest reference used by Compose” and its Japanese equivalent. The run log supports a successful pull and a `prebuilt` report row, not retagging. P2 means an ordinary correction needed before acceptance.

**R2 / gate — Secret scan is red.** Latest CI (automatic checks on a proposed change; [glossary](../reference/REF-01_Glossary.md)) has seven passing checks and one failure: [gitleaks job](https://github.com/RCOSDP/RDM-developer-guide/actions/runs/42105829745/job/127520265415). Its report identifies `generic-api-key` at `docs/guides/storage-addon/README.legacy.md:224`, historical commit `b8594c363a990a3b43119a0a29229766e24b4a59`. The offending value is deliberately not reproduced. This is outside the PR's changed files; the report alone does not establish whether it is a live secret or a false positive. Resolve or document an evidence-based disposition and obtain a successful check; do not describe CI as fully passing.

### Verification

The three changed files and `manifest/upstreams.toon` matched bytes fetched with `gh` at the reviewed head. The supplied `wt-cas` checkout was used for local checks. TOON is compact structured text; the following block records observations rather than mirroring canonical JSON.

```toon
checks[5]{check,result}:
  manifest_check,"PASS; MC-11 parity and private-reference policy included"
  manifest_toon_check,"PASS; byte-for-byte generated excerpt unchanged"
  docs_check,"PASS; 73 files checked; 197 warnings"
  installer_tests,"PASS; 320 tests; 10 skipped"
  latest_ci,"7 PASS; secret scan FAIL"
```

A digest (content fingerprint) pins `niicloudoperation/rdm-cas-overlay` to `sha256:d2f018a957162c4bcaeefdd1645ec7516d0a670199e1813712d91b9e676fa661`. Read-only registry inspection confirmed it is the `linux/amd64` image manifest, not the parent index (`sha256:7644e519dbd9393527257df7f4703cc67e7e52c141eaf831740696177f2a9b17`) or the `unknown/unknown` attestation. The public image reference contains no private repository reference. Its note explains the emulated Maven hang and explicitly requires removal at M4 (the modernization milestone). The TOON excerpt does not project the changed note or `prebuilt_image`, so leaving it unchanged is correct.

Run 3 in both languages agrees on the command, five steps, five images, ember prebuilt success, CAS cancellation with buildx exit 130, and installer exit 30. The local session evidence `scratchpad/install-run3.log` confirms the prebuilt report, cancellation, failure at build, and `INSTALL_EXIT=30`; no later startup step is recorded. The supplied operator observation of 8 h 08 m at 0% CPU is consistently translated, but the log has no independent wall-clock/CPU measurement establishing those exact values. Those remain operator-reported observations, not measurements reproduced by this review. The version increases from 0.2 to 0.3 with bilingual Learned text and preserves prior entries.

The new membership assertions correctly remove the assumption that ember is the only prebuilt component while retaining checks that ember switches back to a source build when its fallback is removed. Both hosted Python 3.11/3.12 test jobs now pass; the two earlier failures at head `86dfd11` are resolved.

From the reviewed checkout root, reproduce the local checks and inspect the registry/CI with:

```sh
python3 tools/manifest_check.py
PYTHONPATH=installer python3 -m grdm_dev.cli manifest toon --check
python3 tools/docs_check.py
PYTHONPATH=installer python3 -m unittest discover -s installer/tests
docker buildx imagetools inspect niicloudoperation/rdm-cas-overlay:latest
gh pr checks 28 --repo RCOSDP/RDM-developer-guide
```

Expect the local checks to pass and the image platform/digest to match the recorded observation; the last command currently exits nonzero for the secret scan. No real installation or Docker state change was performed. Ten skipped tests, exact CPU/time telemetry, and CAS application behavior remain unverified. The coordinator owns corrections, recording the review in version control, and later integration.

---

<a id="japanese"></a>
## 日本語

[→ To English](#english)

### 判定と指摘

**保留 — R1 の文言修正と R2 のセキュリティ検査の処置が必要。** 文書上の判定であり、GitHub の承認送信ではありません。マニフェスト（部品の構成表）の変更自体は SPEC-01 を満たします。

**R1 / P2 — 両言語のタグ付け実施の記述を修正してください。** DEMO-20 の103行目と199行目は “image tagged for Compose”／「Compose 用のタグ付け」としています。`installer/grdm_dev/build.py` の prebuilt 分岐は digest 参照を取得し、同じ参照を記録します。タグ操作は行いません。Compose（アプリの各コンテナをつなぐ道具）は SPEC-01 のとおり参照を直接使用します。「Compose が digest 参照を使用」に相当する表現へ英和とも直してください。実行ログが裏付けるのは取得成功と `prebuilt` 報告行であり、タグ付けではありません。P2 は受入前に必要な通常優先度の修正です。

**R2 / ゲート — 秘密情報走査が失敗しています。** 最新 CI（変更提案の自動検査。[用語集](../reference/REF-01_Glossary.md)）は7件成功・1件失敗です。[gitleaks ジョブ](https://github.com/RCOSDP/RDM-developer-guide/actions/runs/42105829745/job/127520265415) の報告は、履歴上のコミット `b8594c363a990a3b43119a0a29229766e24b4a59` の `docs/guides/storage-addon/README.legacy.md:224` に `generic-api-key` を検出しています。検出値は転載していません。PR の変更ファイル外ですが、報告だけでは実際の秘密か誤検知かを確定できません。解消するか根拠ある処置を記録し、検査成功を確認してください。CI 全件成功とは扱えません。

### 検証

変更3ファイルと `manifest/upstreams.toon` を、対象 head から `gh` で取得した内容とバイト単位で照合しました。ローカル検査は指定された `wt-cas` の作業用コピーで行いました。TOON は短い構造化テキストです。次の値は実測結果であり、正本 JSON の写しではありません。

```toon
checks[5]{check,result}:
  manifest_check,"成功; MC-11 一致と非公開参照ポリシーを含む"
  manifest_toon_check,"成功; 生成した抄録とバイト単位で一致"
  docs_check,"成功; 73 ファイル; 警告 197 件"
  installer_tests,"成功; 320 テスト; 10 skip"
  latest_ci,"7 成功; 秘密情報走査 失敗"
```

digest（内容の指紋）は `niicloudoperation/rdm-cas-overlay` を `sha256:d2f018a957162c4bcaeefdd1645ec7516d0a670199e1813712d91b9e676fa661` に固定しています。配布先への読み取り専用の照会で、これは `linux/amd64` のイメージマニフェストであり、親インデックス（`sha256:7644e519dbd9393527257df7f4703cc67e7e52c141eaf831740696177f2a9b17`）や `unknown/unknown` の証明用データではないと確認しました。公開イメージの参照に非公開リポジトリ参照はありません。note はエミュレーション下の Maven ハングと、M4（近代化の節目）での撤去を明記しています。TOON 抄録には変更した note と `prebuilt_image` を含めないため、抄録を変更しないことは正しい対応です。

第3回の英和は、コマンド、5手順、5イメージ、ember の prebuilt 成功、buildx 終了130による CAS 中断、installer 終了30が一致します。セッション内の `scratchpad/install-run3.log` で prebuilt 報告、中断、build での失敗、`INSTALL_EXIT=30` を確認しました。後続の起動手順の記録はありません。依頼で提供された「8時間08分・CPU 0%」の操作者観察は英和で一致しますが、ログにはその正確な値を独立に証明する経過時刻・CPU 測定がありません。この値は操作者からの報告であり、本レビューで再測定した値ではありません。版は0.2から0.3へ上がり、英和の Learned と以前の版の記録を保持しています。

新しい所属検証は「ember だけが prebuilt」という前提を取り除き、ember の代替設定を外すと元から組み立てることの検査を維持しています。ホスト側の Python 3.11/3.12 の両テストジョブは成功し、旧 head `86dfd11` の2件の失敗は解消しています。

対象作業コピーのルートから、次のコマンドでローカル検査と配布先・CI の照会を再現できます。

```sh
python3 tools/manifest_check.py
PYTHONPATH=installer python3 -m grdm_dev.cli manifest toon --check
python3 tools/docs_check.py
PYTHONPATH=installer python3 -m unittest discover -s installer/tests
docker buildx imagetools inspect niicloudoperation/rdm-cas-overlay:latest
gh pr checks 28 --repo RCOSDP/RDM-developer-guide
```

ローカル検査の成功と、記録したイメージの対象環境・digest との一致が期待結果です。最後のコマンドは現在、秘密情報走査の失敗で非ゼロ終了します。実機導入と Docker の状態変更は行っていません。skip 10件、正確な CPU・経過時間の計測、CAS アプリの動作は未検証です。修正、レビューの版管理への記録、その後の統合判断は連携調整側に残ります。

## Glossary / 用語

| Term | English note | 日本語注 |
|---|---|---|
| Prebuilt image | A packaged program built beforehand. | あらかじめ組み立てたプログラムの配布物。 |
| Digest | Fingerprint identifying exact content. | 同じ内容を特定する指紋。 |
| Manifest | Configuration or image description. | 構成やイメージの説明表。 |
| CI | Automatic checks on a change. | 変更に対する自動検査。 |
| TOON | Compact structured text. | 短い構造化テキスト。 |
| Tag | A name attached to an image. | イメージに付ける名前。 |
