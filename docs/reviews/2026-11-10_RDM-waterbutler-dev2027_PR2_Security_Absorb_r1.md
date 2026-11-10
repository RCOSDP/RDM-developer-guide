# REV RDM-waterbutler-dev2027 PR2 security absorption r1 / セキュリティ吸収レビュー r1

> **Summary:** Independent review of PR2 at `9ab2baa98b09be09358b1e6bb35bb2d409d8e679`. Verdict: Non-blocking / 非阻害.
> **概要:** PR2の対象head `9ab2baa98b09be09358b1e6bb35bb2d409d8e679` を独立レビューした。判定: Non-blocking / 非阻害。

**Jump:** [English](#english) · [日本語](#japanese)

- Version / 版: 0.1 — 2026-11-10. **Learned:** Both installer service templates supply all five required settings; fail-closed checks survive optimized Python. ／ 両サービスのテンプレートは必須設定5項目を供給し、最適化Pythonでも未設定時の拒否は有効。
- Applies to / 対象: RCOSDP/RDM-waterbutler-dev2027 PR2, exact head recorded above; review only.
- Related: [Review index / レビュー索引](README.md) · [SPEC-06](../spec/06_documentation_conventions.md)
- Used by / 利用先: [Documentation index / 文書索引](../README.md), coordinator's absorption decision / 調整担当の吸収判断。

---

<a id="english"></a>
## English

[→ 日本語版へ](#japanese)

### Verdict and findings

No blocking correctness or regression finding at the reviewed head. DEBUG and Tornado debug now default to false. RuntimeError replaces assertions, so Python -O cannot silently restore development secrets. Boolean parsing preserves old values and accepts trimmed, case-insensitive true/false.

[P3, test improvement] tests/test_settings.py:40–70 checks absence of all secrets, but its positive case covers only OSF auth; it does not remove each secret individually or use -O. Add these cases to retained CI coverage. This is not a demonstrated product defect.

### Installer compatibility

installer/grdm_dev/templates/wb.json:12–16 and wb_worker.json:10–14 both supply SERVER_CONFIG_HMAC_SECRET, OSFSTORAGE_PROVIDER_CONFIG_HMAC_SECRET, OSF_AUTH_CONFIG_JWE_SALT, OSF_AUTH_CONFIG_JWE_SECRET and OSF_AUTH_CONFIG_JWT_SECRET. The two HMAC settings share WATERBUTLER_HMAC_SECRET. installer/grdm_dev/secrets.py:77–80 generates the four underlying values, and compose.py:616–619 maps the same values to OSF. compose.py:740–741 emits empty DEBUG and SERVER_CONFIG_DEBUG, which the parser treats as false.

With nonempty synthetic values substituted for those template references, all three settings modules load with DEBUG off. This verifies the secret gate, not complete server/worker startup or network dependencies. No runtime secret was read.

### Evidence and test validity

Compared the exact head against e9b1ac266374d4f477083b327d9620badfc15ad9 in a fresh scratch clone. gh pr checks reports build-image and tests (wb) passing. Local full pytest collection stopped at missing aiohttpretty; it is not reported as a local pass. A separate subprocess harness loaded actual settings files with normal Python and -O, both template key sets, all values present, and each key absent: 24 checks passed. Package handler/provider initialization was bypassed with runpy; no server was started. The harness is /private/tmp/rev-security-PreTii/check_wb.py.

### Remaining work

Optionally retain the extra negative and optimized-mode cases in CI. Validate actual service startup during installer acceptance; no deployment, approval, merge, push or commit was performed.

---

<a id="japanese"></a>
## 日本語

[→ To English](#english)

### 判定と指摘

対象headに阻害する正当性・回帰の指摘はない。DEBUGとTornado debugの既定がfalseになる。assertをRuntimeErrorに置き換えたため、Python -Oでも開発用秘密値へ黙って戻らない。真偽値の解析は既存値を保ち、前後の空白と大文字小文字を許容したtrue/falseを受け付ける。

[P3・テスト改善] tests/test_settings.py:40–70は秘密値が全部ない場合を確認するが、正常系はOSF authだけで、各秘密値の単独欠落と-Oは検査しない。継続実行するCIへの追加を推奨する。製品不具合を示すものではない。

### インストーラーとの適合

installer/grdm_dev/templates/wb.json:12–16とwb_worker.json:10–14はともにSERVER_CONFIG_HMAC_SECRET、OSFSTORAGE_PROVIDER_CONFIG_HMAC_SECRET、OSF_AUTH_CONFIG_JWE_SALT、OSF_AUTH_CONFIG_JWE_SECRET、OSF_AUTH_CONFIG_JWT_SECRETを供給する。HMACの2設定はWATERBUTLER_HMAC_SECRETを共有する。installer/grdm_dev/secrets.py:77–80が元の4値を生成し、compose.py:616–619がOSFにも同じ値を渡す。compose.py:740–741の空のDEBUGとSERVER_CONFIG_DEBUGはfalseとして読まれる。

テンプレート参照を空でない合成値に置換すると、DEBUG offで3つの設定モジュールを読み込めた。これは秘密値検査の通過であり、サーバー・worker全体の起動や通信依存の確認ではない。実行時の秘密値は読んでいない。

### 根拠とテストの妥当性

新しいscratch cloneで対象headをe9b1ac266374d4f477083b327d9620badfc15ad9と比較した。gh pr checksではbuild-imageとtests (wb)が成功している。ローカルの通常pytestはaiohttpretty不足で収集が停止し、成功とは扱わない。別の子プロセス検査で実際の設定ファイルを通常Pythonと-O、両テンプレートのキー、全値あり・各値欠落で読み込み、24件が成功した。runpyでhandler/providerのパッケージ初期化を迂回し、サーバーは起動していない。検査コードは/private/tmp/rev-security-PreTii/check_wb.pyにある。

### 残作業

任意改善として単独欠落と最適化モードのケースをCIに残す。実サービスの起動はインストーラー受入で確認する。デプロイ、承認、マージ、push、commitは行っていない。

---

## Glossary / 用語

| Term | English note | 日本語注 |
|---|---|---|
| PR / head | Proposed change / exact version reviewed. | 変更案／調べた正確な版。 |
| P1 / P2 / P3 | High / medium / low review priority. | 高／中／低の修正優先度。 |
| Secret / token | A private value used to prove identity or sign data. | 本人確認や署名に使う秘密の値。 |
| Regression | A change that breaks previously working behavior. | 以前動いた機能が変更で壊れること。 |
| CI / mock | Automated checks / a substitute used in a test. | 自動検査／試験用の代役。 |
| Secure cookie | A browser value restricted to secure transport. | 安全な通信経路に送信を限定するブラウザーの値。 |
