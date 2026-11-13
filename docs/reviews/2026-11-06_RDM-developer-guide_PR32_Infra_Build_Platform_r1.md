# PR32 Infra build platform review r1 / 基盤イメージのプラットフォーム指定レビュー r1

> **Summary:** Pass with one non-blocking validation gap. All five selected images lack arm64, and every other current infra image supports it.
> **概要:** 検証の軽微な不足1件を付して合格。指定5イメージには arm64 がなく、現在の他の基盤イメージはすべて対応する。

**Jump:** [English](#english) · [日本語](#japanese)

- Version / 版: 0.1 — 2026-11-06. **Learned:** selecting amd64 fixes image acquisition, but a successful pull does not establish successful startup. ／ amd64 指定でイメージ取得は解決するが、取得成功だけでは起動成功を証明しない。
- Applies to: RCOSDP/RDM-developer-guide PR #32; REV（担当レビュワ, Codex Astra）.
- Related: [Review index](README.md) · [SPEC-01](../spec/01_manifest.md) · [SPEC-06](../spec/06_documentation_conventions.md) · [PR #32](https://github.com/RCOSDP/RDM-developer-guide/pull/32).
- Used by: [DEMO-20](../demo/20_core_install_mac_studio.md) · [Status board](../status/README.md).

---

<a id="english"></a>
## English

[→ 日本語版へ](#japanese)

### Verdict and finding

**Pass with non-blocking R1-01; no blocking findings.** Reviewed local and remote head `1bcc1a783ee3db82c7c498b4d2d62b746d412097`, branch `fix/infra-amd64-platform`. This is a review verdict, not GitHub approval. No merge, approval, commit, push or Docker state change was performed.

**R1-01 — low:** `tools/manifest_check.py:160,499–507` accepts `build_platform` as string/null and does not prohibit it on infra, so MC-10 does not contradict the newly allowed configuration. However, the new SPEC-01 requirement to accompany an infra pin with a `note` is not enforced. An in-memory copy with `elasticsearch2.note = None` still returns zero findings from `validate_manifest`. Add a missing/blank-note rejection and regression test in a follow-up. All five actual entries include meaningful reasons and M4/M5 exit milestones, so this gap does not invalidate this PR's manifest.

### Registry and rendering evidence

Read-only `docker manifest inspect --verbose <image>` succeeded for all nine current `role: infra` base images. These are observations of current tags on 2026-11-06, not immutable digest guarantees; target M4/M5 images were not the scope. The observations are not canonical manifest data.

```toon
images[9]{component,image,linux_amd64,linux_arm64}:
  postgres,postgres:9.6,yes,yes
  elasticsearch2,elasticsearch:2,yes,no
  elasticsearch6,docker.elastic.co/elasticsearch/elasticsearch:6.3.1,yes,no
  mongo,mongo:3.4,yes,yes
  rabbitmq,rabbitmq:3-management,yes,yes
  redis,redis:7,yes,yes
  sharejs,quay.io/centerforopenscience/sharejs:develop,yes,no
  unoconv,centerforopenscience/unoconv,yes,no
  fakecas,quay.io/centerforopenscience/fakecas:master,yes,no
```

`installer/grdm_dev/compose.py:812–816` collects component pins for all selected services without excluding infra; lines 364–366 use that value before the host platform and emit `platform:`. `installer/tests/test_compose.py:72–75,95–113` derives expected values from the repository manifest and checks every rendered core service, covering all five changed services, including the `elasticsearch2` → `elasticsearch` name mapping. SPEC-01 version 0.8 and both language rows agree on the note requirement, affected images, emulation and Compose behavior. No unrelated manifest fields changed.

The supplied local `install-run7.log` records successful pulls at lines 1068 (fakecas), 2342 (ES6), 2623 (ES2), 2766 (sharejs) and 2817 (unoconv); lines 2983–2990 report their `linux/amd64` pins. Lines 2876–2878 then report a missing host directory for `rabbitmq_data`. This supports the pull fix, not complete startup, health or acceptance. The reviewer did not rerun installation.

### Checks

Commands ran from the review worktree root. Results are observed review data.

```toon
checks[5]{command,result}:
  "python3 tools/manifest_check.py","PASS; zero manifest/policy findings"
  "python3 tools/docs_check.py","PASS; 91 checked, 8 exempt, 19 non-failing warnings"
  "PYTHONPATH=installer python3 -m unittest discover -s installer/tests","OK; 345 tests, 10 skipped"
  "python3 -m unittest discover -s tools/tests","OK; 89 tests"
  "gh pr checks 32 --repo RCOSDP/RDM-developer-guide","PASS; all 8 checks"
```

The new untracked review is checked separately through `tools.docs_check.check_file`, because the command enumerates tracked files. Startup after the volume-path repair and the optional R1-01 follow-up remain outside this review's completed verification.

---

<a id="japanese"></a>
## 日本語

[→ To English](#english)

### 判定と指摘

**軽微な R1-01 を付して合格。阻害指摘なし。** ローカルとリモートの先端 `1bcc1a783ee3db82c7c498b4d2d62b746d412097`、ブランチ `fix/infra-amd64-platform` を確認した。これはレビュー判定であり GitHub の承認ではない。マージ・承認・コミット・push・Docker の状態変更は行っていない。

**R1-01 — 軽微:** `tools/manifest_check.py:160,499–507` は `build_platform` を文字列/null として受理し、infra で禁止していないため、MC-10 は今回許可された設定に矛盾しない。ただし、SPEC-01 が新たに求める infra 指定時の `note` 併記は検査しない。メモリ上のコピーで `elasticsearch2.note = None` にしても `validate_manifest` の指摘はゼロだった。後続で未指定・空の注記を拒否する検査と回帰試験を追加するとよい。実際の5件には理由と M4/M5 の解消時期があるため、この不足は今回のマニフェストを不合格にするものではない。

### レジストリと描画の証拠

読み取り専用の `docker manifest inspect --verbose <image>` は、現在の `role: infra` の全9ベースイメージで成功した。2026-11-06 時点のタグの観測であり、不変のダイジェストを保証するものではない。将来の M4/M5 向けイメージは対象外とした。次は観測値であり、マニフェストの正本ではない。

```toon
images[9]{component,image,linux_amd64,linux_arm64}:
  postgres,postgres:9.6,yes,yes
  elasticsearch2,elasticsearch:2,yes,no
  elasticsearch6,docker.elastic.co/elasticsearch/elasticsearch:6.3.1,yes,no
  mongo,mongo:3.4,yes,yes
  rabbitmq,rabbitmq:3-management,yes,yes
  redis,redis:7,yes,yes
  sharejs,quay.io/centerforopenscience/sharejs:develop,yes,no
  unoconv,centerforopenscience/unoconv,yes,no
  fakecas,quay.io/centerforopenscience/fakecas:master,yes,no
```

`installer/grdm_dev/compose.py:812–816` は infra を除外せず全選択サービスの指定を集め、364–366 行はホストより優先して `platform:` に出力する。`installer/tests/test_compose.py:72–75,95–113` はリポジトリのマニフェストから期待値を取り、core の全出力サービスを検査するため、変更5件と `elasticsearch2` → `elasticsearch` の名前対応も対象になる。SPEC-01 の版 0.8 と英和両方の行は、注記必須・対象イメージ・エミュレーション・Compose の挙動で一致する。無関係なマニフェスト項目の変更はない。

提供されたローカルの `install-run7.log` は、1068 行（fakecas）、2342 行（ES6）、2623 行（ES2）、2766 行（sharejs）、2817 行（unoconv）に取得成功を記録し、2983–2990 行に各 `linux/amd64` 指定を記録する。その後の 2876–2878 行は `rabbitmq_data` 用ホストディレクトリの不足を報告する。取得修正の証拠にはなるが、起動・健康状態・受入の完了を示すものではない。レビュワによる導入再実行は行っていない。

### 検査

コマンドはレビュー用作業ツリーのルートで実行した。結果はレビュー時の観測値である。

```toon
checks[5]{command,result}:
  "python3 tools/manifest_check.py","合格; manifest/policy 指摘ゼロ"
  "python3 tools/docs_check.py","合格; 91件検査, 8件除外, 非失敗警告19件"
  "PYTHONPATH=installer python3 -m unittest discover -s installer/tests","OK; 345試験, 10件スキップ"
  "python3 -m unittest discover -s tools/tests","OK; 89試験"
  "gh pr checks 32 --repo RCOSDP/RDM-developer-guide","全8件合格"
```

文書検査コマンドは追跡済みファイルを列挙するため、新規の未追跡レビューは `tools.docs_check.check_file` で別途検査する。ボリュームのパス修復後の起動検証と、任意の R1-01 対応は今回完了した検証の範囲外として残る。

---

## Glossary / 用語

| Term | English note | 日本語注 |
|---|---|---|
| Platform | The operating system and processor family an image targets. | イメージが動く OS と CPU の種類。 |
| Manifest | A list describing components or the image variants a registry offers. | 部品の設定、または配布されるイメージの種類を記した一覧。 |
| Emulation | Running instructions intended for another processor family. | 別の CPU 向けの命令を読み替えて動かすこと。 |
| Pull | Downloading an image; it does not prove the service started. | イメージの取得。サービスの起動成功は意味しない。 |
