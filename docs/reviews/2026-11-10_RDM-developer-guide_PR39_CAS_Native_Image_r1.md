# REV PR39 CAS native image review r1 / CAS ネイティブイメージのレビュー r1

> **Summary:** Changes requested: generated keys are usable, but validation accepts manually supplied keys that CAS cannot use.
> **概要:** 修正要求。生成する鍵は使えるが、手動で設定した CAS が使えない鍵を検証が受理する。

**Jump:** [English](#english) · [日本語](#japanese)

- Version / 版: 0.1 — 2026-11-10. **Learned:** A byte count alone does not establish that a key is usable by its consumer. ／ バイト数だけでは、鍵を使う側で利用可能とは保証できない。
- Applies to: PR #39, head `bfa031c8b22b4504a9d370f8edbfac7515c158b0`, base `021dce68a334750ac249c6f94e8f86074db7a369`; REV（担当レビュワ, Codex Astra）.
- Related: [Reviews](README.md) · [SPEC-01](../spec/01_manifest.md) · [SPEC-02](../spec/02_installer_cli.md) · [SPEC-03](../spec/03_security_gate.md) · [SPEC-06](../spec/06_documentation_conventions.md) · [ADR-07](../decisions/ADR-07_Native_Builds_of_EOL_Middleware.md).
- Used by: [PR #39](https://github.com/RCOSDP/RDM-developer-guide/pull/39).

---

<a id="english"></a>
## English

[→ 日本語版へ](#japanese)

### Verdict and required change

**Changes requested — R1-01 (P2): validate usable keys before rendering.** In `installer/grdm_dev/secrets.py:230–238`, `cas_key_problems` checks only UTF-8 byte lengths. The documented manual migration can therefore supply an encryption key consisting of 43 exclamation marks, or quoted institution JWE/JWT keys consisting of 32 spaces. All three independently return no validation findings and `compose render` exits 0. I reproduced this using temporary test roots, synthetic inputs, and the existing mocked render helper; no real credentials or running stack were used.

CAS 4.1.5's `DefaultCipherExecutor` interprets the TGC encryption key as the base64url octet value of a JWK; 43 arbitrary characters do not guarantee a 32-byte encryption key. The pinned integration's institution-secret setters explicitly reject blank values, including the accepted 32-space examples. This defeats the new pre-start check and permits a stopped CAS or a failure when issuing its cookie after a manual upgrade. Validate the TGC encryption alphabet and decoded byte count, reject blank institution keys, and add negative render tests that require exit 2, no generated Compose file, and diagnostics containing key names only. Keep the valid generated keys passing. Do not incorrectly decode the TGC signing key when matching CAS: that implementation consumes its raw string bytes for signing.

### Checks completed

- Generation uses `token_urlsafe`: TGC encryption is 43 ASCII characters encoding 32 random bytes; signing is 86 ASCII characters from 64 random bytes (CAS uses the 86 raw bytes); institution JWE is exactly 32 ASCII bytes from 24 random bytes; JWT is 43 ASCII bytes, satisfying the 32-byte minimum. Generated values meet the consumer requirements.
- Checked CAS integration commit `22610b7681a29241365108e5129bcd43ade4610e` and osf.io integration commit `389415a473361fdaa3c347e84d95639b9096a9e9` through read-only GitHub API calls. The same institution variables feed CAS and all five osf.io service templates; generated `api_local.py` assigns UTF-8 bytes to `JWE_SECRET` and `JWT_SECRET`, loaded after API defaults. The institution authentication consumer decrypts and verifies with those settings.
- New secrets appear as environment references, not literals in command arguments, properties, Python settings, service JSON, or reports. Secret writes use mode 0600 under a 0700 runtime directory; generated config files use 0644 and contain no secret values. Both forced init and rotate remove the four retired CAS keys. This is a static assessment of the new path, not an assertion about every pre-existing secret-handling path.
- The service regex escapes the loopback address and fixes the scheme, port, and following slash. It cannot accept a different hostname, user-info authority, or port suffix; allowing all paths on that one web origin is intentional. The missing terminal `$` does not broaden the permitted origin. The Secure overrides are in the generated loopback HTTP development configuration; the pinned image defaults remain secure. CAS has no published host port and osf.io continues to use fakecas.
- CAS waits for successful `osf_init`; its root is read-only, uid/gid is 1000, capabilities are dropped, no-new-privileges is set, and only `/tmp` is writable. Its hardening exception is removed without adding another.
- The pinned Dockerfile runs Maven and Jetty setup in BUILDPLATFORM stages and only copies in the target stage. Both base digests are pinned; the manifest runtime base digest matches the Dockerfile and is passed as a build label. The prebuilt and amd64 override are removed. Manifest MC checks and policy checks pass.

### Verification and limits

Commands were run from the reviewed checkout. These are review-run results, not canonical manifest data.

```toon
checks[4]{command,result,exit_code}:
  "PYTHONPATH=installer python3 -m unittest discover -s installer/tests","525 tests; 10 skipped",0
  "python3 -m unittest discover -s tools/tests","93 tests",0
  "python3 tools/docs_check.py","pass; glossary warnings only",0
  "python3 tools/manifest_check.py","manifest and policy: zero findings",0
```

No image build, real CAS startup, institution-login round trip, TOTP, ORCiD, or native amd64 execution was performed in this review. ADR-07's arm64 runtime results are author evidence, not independently repeated results. The checkout's real `runtime/.env` was not read or modified, and no Docker stack state was changed. R1-01 remains for the implementer; no production code was modified.

---

<a id="japanese"></a>
## 日本語

[→ To English](#english)

### 判定と必須修正

**Changes requested（修正要求）— R1-01（P2）：使える鍵であることを生成前に検証する。** `installer/grdm_dev/secrets.py:230–238` の `cas_key_problems` は UTF-8 バイト数だけを検査する。文書の手動移行手順では、感嘆符 43 個の TGC 暗号鍵、または引用符で囲んだ空白 32 個の機関 JWE/JWT 鍵を設定できる。各ケースとも検証指摘は空で、`compose render` は終了 0 になった。一時テストルート、合成入力、既存のモック付き render ヘルパーで再現し、実際の認証情報や稼働スタックは使っていない。

CAS 4.1.5 の `DefaultCipherExecutor` は TGC 暗号鍵を JWK の base64url オクテット値として扱うため、任意の 43 文字では 32 バイトの暗号鍵を保証できない。固定された統合版の機関秘密 setter は空白のみを明示的に拒否し、今回受理された空白 32 個も該当する。起動前検査を通過しても、手動移行後に CAS が止まるか Cookie 発行時に失敗する。TGC 暗号鍵の文字集合と復号後バイト数を検査し、機関鍵の空白のみを拒否してほしい。異常入力で終了 2、Compose ファイル未生成、鍵名だけの診断を確かめる負例試験を加え、正しい生成鍵は引き続き受理すること。CAS の署名側は文字列の生バイトを使うため、TGC 署名鍵まで復号する検証にはしないこと。

### 確認した事項

- 生成は `token_urlsafe` を使う。TGC 暗号鍵は乱数 32 バイトを表す ASCII 43 文字、署名鍵は乱数 64 バイトからの ASCII 86 文字（CAS は生の 86 バイトを使う）、機関 JWE は乱数 24 バイトからの ASCII 32 バイト、JWT は ASCII 43 バイトで最小 32 バイトを満たす。生成値自体は利用側の条件に合う。
- 読み取り専用 GitHub API で CAS 統合コミット `22610b7681a29241365108e5129bcd43ade4610e` と osf.io 統合コミット `389415a473361fdaa3c347e84d95639b9096a9e9` を確認した。同一の機関変数を CAS と osf.io の 5 サービステンプレートに渡し、生成 `api_local.py` が `JWE_SECRET` と `JWT_SECRET` を UTF-8 バイトにして既定設定の後で読み込む。機関認証の実装もこれらで復号・署名検証する。
- 新しい秘密は環境変数参照であり、引数・properties・Python 設定・サービス JSON・レポートに値を埋め込まない。秘密ファイルは 0700 の runtime ディレクトリ内に 0600 で書き、生成設定は 0644 で秘密値を含まない。強制 init と rotate の双方で旧 CAS 4 キーを除く。これは新経路の静的確認であり、既存の全秘密処理の保証ではない。
- サービス正規表現はループバックをエスケープし、scheme・port・直後のスラッシュを固定する。別ホスト、ユーザー情報付き authority、port の接尾辞は許可しない。同一 web origin の全パス許可は意図された範囲で、末尾 `$` が無くても origin は広がらない。Secure の解除は生成されるループバック HTTP 開発設定にあり、固定イメージの既定は secure のまま。CAS はホストにポートを公開せず、osf.io は引き続き fakecas を使う。
- CAS は `osf_init` 成功を待つ。読み取り専用ルート、uid/gid 1000、capability 除去、no-new-privileges、書込可能場所は `/tmp` のみ。CAS の堅牢化例外を除き、新しい例外はない。
- 固定 Dockerfile は Maven と Jetty 設定を BUILDPLATFORM 段で行い、対象アーキテクチャの最終段はコピーのみ。両ベースの digest を固定し、manifest の実行時ベース digest は Dockerfile と一致して build label に渡る。prebuilt と amd64 固定を除去。manifest の MC 検査と policy 検査は合格した。

### 検証と限界

実行場所は対象 checkout。次はレビュー実行結果で、manifest の正本データではない。

```toon
checks[4]{command,result,exit_code}:
  "PYTHONPATH=installer python3 -m unittest discover -s installer/tests","525 件、10 件 skip",0
  "python3 -m unittest discover -s tools/tests","93 件",0
  "python3 tools/docs_check.py","合格、用語注の警告のみ",0
  "python3 tools/manifest_check.py","manifest と policy の指摘 0",0
```

本レビューではイメージビルド、実 CAS 起動、機関ログイン往復、TOTP、ORCiD、実機 amd64 実行は行っていない。ADR-07 の arm64 実行結果は作者の証跡であり、独立再実行ではない。checkout の実 `runtime/.env` は読み書きせず、Docker スタックの状態も変更していない。R1-01 の修正は実装担当に残る。実装コードは変更していない。
