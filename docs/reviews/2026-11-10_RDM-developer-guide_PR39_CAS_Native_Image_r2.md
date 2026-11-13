# REV PR39 CAS native image review r2 / CAS ネイティブイメージのレビュー r2

> **Summary:** Pass. R1-01 is closed; no regression requiring changes was found in the scoped diff.
> **概要:** 合格。R1-01 は解消し、対象差分に修正を要する回帰は見つからなかった。

**Jump:** [English](#english) · [日本語](#japanese)

- Version / 版: 0.1 — 2026-11-10. **Learned:** Canonical decoding and published-key fingerprints can reject unusable keys before rendering without exposing their values. ／ 正準な復号と公開鍵値の指紋照合により、値を露出せず生成前に使えない鍵を拒否できる。
- Applies to: PR #39, diff `bfa031c8b22b4504a9d370f8edbfac7515c158b0..aa48404f71481cf181c618b78593324f91bea19f`; REV（担当レビュワ, Codex Astra）.
- Related: [Reviews](README.md) · [Review r1](2026-11-10_RDM-developer-guide_PR39_CAS_Native_Image_r1.md) · [SPEC-02](../spec/02_installer_cli.md) · [SPEC-06](../spec/06_documentation_conventions.md) · [ADR-07](../decisions/ADR-07_Native_Builds_of_EOL_Middleware.md).
- Used by: [PR #39](https://github.com/RCOSDP/RDM-developer-guide/pull/39).

---

<a id="english"></a>
## English

[→ 日本語版へ](#japanese)

### Verdict and evidence

**Pass — R1-01 closed.** Review was limited to its fix and regressions introduced by the specified diff. No new required change was found.

- All four CAS keys are checked for length and the unpadded base64url alphabet. Whitespace, literal quotes, punctuation outside that alphabet, and forbidden defaults are rejected. Existing dotenv syntax removes surrounding quotes before validation; a quoted valid value remains valid, while quoted spaces are rejected.
- Only `TGC_ENCRYPTION_KEY` is decoded. Its 43-character alphabet-checked input safely decodes to 32 bytes; re-encoding rejects noncanonical trailing bits. Signing and institution keys retain raw-string semantics. The added tests cover this distinction and padding rejection; 100 independently generated key sets also passed validation.
- Read-only GitHub API retrieval of `etc/cas.properties` at CAS PR #3 base `c4a7666364aebf58880fed44a304a21d29d3c29b` independently confirmed that all four published values match the SHA-256 denylist. Each value was rejected by validation and rendering; values were not printed or copied into this report.
- Independent temporary-root probes covered those four published values and 20 further invalid inputs across the four keys: wrong-alphabet values, both quote styles around spaces, trailing punctuation and `changeme`. Every render returned 2, named the affected key without its value in stdout/stderr, and left a byte-for-byte file inventory unchanged. This verifies no output file was created or overwritten, beyond the added unit tests' Compose-file assertion. Docker calls were mocked.
- The render guard remains before generated files and port updates. SPEC-02 and ADR-07 describe the same alphabet, digest and decoding rules. No unrelated implementation change was introduced in this diff.

### Verification and limits

Commands ran from the specified checkout. Results are review observations, not canonical manifest data.

```toon
checks[4]{command,result,exit_code}:
  "PYTHONPATH=installer python3 -m unittest discover -s installer/tests","531 tests; 10 skipped",0
  "python3 -m unittest discover -s tools/tests","93 tests",0
  "python3 tools/docs_check.py","pass; 24 glossary warnings",0
  "python3 tools/manifest_check.py","manifest and policy: zero findings",0
```

The independent probes exited 0. The untracked r2 report was checked separately through `docs_check.check_file`, since the main checker enumerates tracked files. No production code was modified, and this report is uncommitted. The checkout's real `runtime/.env` was not read or modified; no Docker stack state was changed. No image build or real CAS/institution-login execution was repeated. No required review finding remains in scope; runtime evidence retains r1's limits.

---

<a id="japanese"></a>
## 日本語

[→ To English](#english)

### 判定と根拠

**Pass（合格）— R1-01 解消。** 指定差分の修正と、それによる回帰に限定して確認した。新しい必須修正はない。

- CAS の全 4 キーで長さとパディングなしの base64url 文字集合を検査する。空白、値に含まれる引用符、集合外の記号、禁止既定値を拒否する。既存の dotenv 構文では外側の引用符を検証前に除くため、引用符で囲んだ正常値は有効で、引用符で囲んだ空白は拒否される。
- 復号は `TGC_ENCRYPTION_KEY` のみ。文字集合を検査した 43 文字は安全に 32 バイトへ復号でき、再符号化との比較で末尾の非正準ビットを拒否する。署名鍵と機関鍵は生文字列として扱う。追加試験はこの違いとパディング拒否を確認し、独立に生成した 100 組の鍵も検証を通過した。
- 読み取り専用 GitHub API で CAS PR #3 の base `c4a7666364aebf58880fed44a304a21d29d3c29b` の `etc/cas.properties` を取得し、公開済みの 4 値すべてが SHA-256 拒否リストに一致することを独立確認した。各値は検証・render とも拒否された。値は出力せず、記録にも転記していない。
- 独立した一時ルートの試験で、その公開済み 4 値と、全 4 キーに対する異常入力 20 件を確認した。集合外文字、両形式の引用符で囲んだ空白、末尾の記号、`changeme` が対象。全件で render は終了 2、標準出力・標準エラーには値を出さず対象キー名を示し、ファイル一覧と全内容は実行前後で一致した。追加単体試験の Compose ファイル未生成だけでなく、他の出力ファイルの作成・上書きもないことを確かめた。Docker 呼び出しはモック化した。
- render の検査は生成ファイルの書込・ポート更新より前にある。SPEC-02 と ADR-07 は同じ文字集合・指紋・復号規則を説明する。差分に無関係な実装変更はない。

### 検証と限界

指定 checkout で実行した。次はレビュー実測であり、manifest の正本データではない。

```toon
checks[4]{command,result,exit_code}:
  "PYTHONPATH=installer python3 -m unittest discover -s installer/tests","531 件、10 件 skip",0
  "python3 -m unittest discover -s tools/tests","93 件",0
  "python3 tools/docs_check.py","合格、用語注の警告 24 件",0
  "python3 tools/manifest_check.py","manifest と policy の指摘 0",0
```

独立試験は終了 0。主検査は追跡済みファイルを列挙するため、未追跡の r2 記録は `docs_check.check_file` で別途検査した。実装コードは変更せず、この記録も未コミット。checkout の実 `runtime/.env` は読み書きせず、Docker スタックの状態も変更していない。イメージビルド、実 CAS・機関ログイン実行は再実施していない。対象範囲の必須指摘は残らず、実行時証跡の限界は r1 と同じ。
