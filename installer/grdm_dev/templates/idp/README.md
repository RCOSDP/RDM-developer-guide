# Test IdP Templates / テスト IdP テンプレート

> **Summary:** Configuration templates of the bundled test IdP (SimpleSAMLphp) and of the Shibboleth SP that trusts it, used only with `compose render --profile full --auth shibboleth`. Placeholders are filled from `runtime/.env` at render time; the mock users are MOCK by construction.
> **概要:** 同梱のテスト IdP（SimpleSAMLphp）と、それを信頼する Shibboleth SP の設定テンプレート。`compose render --profile full --auth shibboleth` のときだけ使う。プレースホルダは描画時に `runtime/.env` から埋め、模擬利用者は作りからして MOCK である。

**Jump:** [English](#english) · [日本語](#japanese)

- Version / 版: 0.1 — 2026-11-06. **Learned:** the acceptance guard allows only `http://127.0.0.1`, so an IdP and an SP that normally insist on TLS must be configured for plain HTTP on loopback, and every URL in both configurations has to be rendered from the chosen host ports rather than written by hand. ／ 受入の監視は `http://127.0.0.1` しか通さないため、本来 TLS を求める IdP と SP をループバック上の平文 HTTP に合わせる必要があり、両方の設定に出てくる URL は手書きでなく選ばれたホスト側ポートから描画しなければならないと分かった。
- Normative source: [ADR-05 Test IdP for Shibboleth](../../../../docs/decisions/ADR-05_Test_IdP_for_Shibboleth.md) · [SPEC-04 §5](../../../../docs/spec/04_acceptance_tests.md#english) · [SPEC-03 §3](../../../../docs/spec/03_security_gate.md#english) · [ADR-02](../../../../docs/decisions/ADR-02_Network_Model.md)
- Related: [installer/README.md](../../../README.md) · [fixtures/idp/README.md](../../../acceptance/fixtures/idp/README.md) · `templates/test_idp.json` · `templates/shibboleth_sp.json`

---

<a id="english"></a>
## English

[→ 日本語版へ](#japanese)

### Files and where they are rendered

```toon
templates[7]{file,rendered_to,mounted_in,purpose}:
  config.php.tmpl,runtime/config/idp/config/config.php,test_idp:/var/simplesamlphp/config,SimpleSAMLphp main settings (plain HTTP on loopback; secrets from .env)
  authsources.php.tmpl,runtime/config/idp/config/authsources.php,test_idp:/var/simplesamlphp/config,"MOCK users and their SAML attributes (exampleauth:UserPass)"
  saml20-idp-hosted.php.tmpl,runtime/config/idp/metadata/saml20-idp-hosted.php,test_idp:/var/simplesamlphp/metadata,the IdP this container hosts (entityID + key pair + authproc)
  saml20-sp-remote.php.tmpl,runtime/config/idp/metadata/saml20-sp-remote.php,test_idp:/var/simplesamlphp/metadata,the one SP the IdP trusts (shibboleth_sp)
  sp-shibboleth2.xml.tmpl,runtime/config/shibboleth_sp/shibboleth2.xml,shibboleth_sp:/etc/shibboleth/shibboleth2.xml,SP settings: entityID; trusted IdP; cookie flags; RequestMap affiliation rule
  sp-attribute-map.xml,runtime/config/shibboleth_sp/attribute-map.xml,shibboleth_sp:/etc/shibboleth/attribute-map.xml,"SAML attribute OIDs -> header names (GakuNin set); copied, no placeholders"
  sp-idp-metadata.xml.tmpl,runtime/config/shibboleth_sp/idp-metadata.xml,shibboleth_sp:/etc/shibboleth/idp-metadata.xml,metadata of the test IdP as the SP trusts it
```

A *template* here is a text file whose `${KEY}` placeholders are replaced with values from `runtime/.env`. The service templates `test_idp.json` and `shibboleth_sp.json` mount the rendered directories read-only.

### Placeholders

```toon
placeholders[9]{key,kind,source,used_by}:
  GRDM_PORT_TEST_IDP,port,"compose render (template host_port 8081; remapped on collision)","every URL of the IdP; SP trust"
  GRDM_PORT_SHIBBOLETH_SP,port,"compose render (template host_port 8082)","SP entityID; ACS and SLO locations; IdP trust"
  GRDM_PORT_WEB,port,compose render,"trusted redirect targets"
  SP_REQUIRED_AFFILIATION,setting,"shibboleth_sp.json environment (member)","RequestMap rule; S5 rejection"
  SP_COOKIE_PROPS,setting,"shibboleth_sp.json environment (HttpOnly; SameSite=Lax; no Secure)",session cookie flags
  IDP_METADATA_FILE,setting,shibboleth_sp.json environment,MetadataProvider path
  TEST_IDP_SECRET_SALT,secret,"secrets init (follow-up F-2)",SimpleSAMLphp secretsalt
  TEST_IDP_ADMIN_PASSWORD,secret,"secrets init (follow-up F-2)",SimpleSAMLphp admin page
  "TEST_IDP_IDP_CERT_BASE64, TEST_IDP_SP_CERT_BASE64",derived,"secrets init writes idp.crt / sp.crt; render strips the PEM armour",metadata of each side
```

Secrets never enter a rendered file except through these placeholders, and the two `.key` files are mounted from `runtime/config/idp/cert/` with mode `0600` (`runtime/` itself is `0700`). Nothing here has a default value.

### Follow-ups (not implemented in this change)

```toon
followups[5]{id,where,what}:
  F-1,installer/grdm_dev/compose.py,"render templates/idp/*.tmpl into runtime/config/idp/{config,metadata}/ and runtime/config/shibboleth_sp/ when auth is shibboleth; copy sp-attribute-map.xml; create runtime/config/idp/cert/; record GRDM_AUTH in runtime/.env so `accept` can select S5"
  F-2,installer/grdm_dev/secrets.py,"add TEST_IDP_SECRET_SALT and TEST_IDP_ADMIN_PASSWORD to SECRET_KEYS; generate self-signed RSA-2048 pairs idp.key/idp.crt and sp.key/sp.crt (CN=127.0.0.1, 10 years, 0600 for keys) into runtime/config/idp/cert/ at init and rotate; add GRDM_PORT_TEST_IDP=8081 and GRDM_PORT_SHIBBOLETH_SP=8082 to DEFAULT_PORTS (plan.py, secrets.py, acceptance/conftest.py)"
  F-3,manifest/hardening.json,"remove the test_idp exception once the non-root test-idp image is built (ADR-05); keep the shibboleth_sp exception until M4"
  F-4,manifest/upstreams.json,"component `test-idp` (services [test_idp], profile full, both platforms, no upstream) so compose render gives the service its own image; move test_idp out of the Shibboleth-SP services list; add the two ports to the SPEC-02 §4 ports table"
  F-5,installer/grdm_dev/accept.py,"--seed --auth shibboleth creates an OSF institution whose login matches the test IdP entityID and the mock users' institution (MOCK Institution); --only S5 refuses to run when GRDM_AUTH is not shibboleth"
```

---

<a id="japanese"></a>
## 日本語

[→ To English](#english)

### ファイルと描画先

```toon
templates[7]{file,rendered_to,mounted_in,purpose}:
  config.php.tmpl,runtime/config/idp/config/config.php,test_idp:/var/simplesamlphp/config,SimpleSAMLphp の主設定（ループバックの平文 HTTP。秘密は .env から）
  authsources.php.tmpl,runtime/config/idp/config/authsources.php,test_idp:/var/simplesamlphp/config,"MOCK 利用者とその SAML 属性（exampleauth:UserPass）"
  saml20-idp-hosted.php.tmpl,runtime/config/idp/metadata/saml20-idp-hosted.php,test_idp:/var/simplesamlphp/metadata,このコンテナが提供する IdP（entityID・鍵対・authproc）
  saml20-sp-remote.php.tmpl,runtime/config/idp/metadata/saml20-sp-remote.php,test_idp:/var/simplesamlphp/metadata,IdP が信頼する唯一の SP（shibboleth_sp）
  sp-shibboleth2.xml.tmpl,runtime/config/shibboleth_sp/shibboleth2.xml,shibboleth_sp:/etc/shibboleth/shibboleth2.xml,SP の設定。entityID・信頼する IdP・cookie 属性・RequestMap の所属規則
  sp-attribute-map.xml,runtime/config/shibboleth_sp/attribute-map.xml,shibboleth_sp:/etc/shibboleth/attribute-map.xml,"SAML 属性の OID -> ヘッダ名（GakuNin の属性集合）。複写のみでプレースホルダなし"
  sp-idp-metadata.xml.tmpl,runtime/config/shibboleth_sp/idp-metadata.xml,shibboleth_sp:/etc/shibboleth/idp-metadata.xml,SP が信頼する形のテスト IdP メタデータ
```

ここでの「テンプレート」は、`${KEY}` のプレースホルダを `runtime/.env` の値で置き換えるテキストファイルです。サービステンプレート `test_idp.json` と `shibboleth_sp.json` が、描画後のディレクトリを読み取り専用でマウントします。

### プレースホルダ

```toon
placeholders[9]{key,kind,source,used_by}:
  GRDM_PORT_TEST_IDP,ポート,"compose render（テンプレートの host_port 8081。衝突時は付け替え）","IdP の全 URL。SP 側の信頼"
  GRDM_PORT_SHIBBOLETH_SP,ポート,"compose render（テンプレートの host_port 8082）","SP の entityID。ACS と SLO の場所。IdP 側の信頼"
  GRDM_PORT_WEB,ポート,compose render,"転送を許す先"
  SP_REQUIRED_AFFILIATION,設定,"shibboleth_sp.json の environment（member）","RequestMap の規則。S5 の拒否"
  SP_COOKIE_PROPS,設定,"shibboleth_sp.json の environment（HttpOnly。SameSite=Lax。Secure なし）",セッション cookie の属性
  IDP_METADATA_FILE,設定,shibboleth_sp.json の environment,MetadataProvider のパス
  TEST_IDP_SECRET_SALT,秘密,"secrets init（後続 F-2）",SimpleSAMLphp の secretsalt
  TEST_IDP_ADMIN_PASSWORD,秘密,"secrets init（後続 F-2）",SimpleSAMLphp の管理画面
  "TEST_IDP_IDP_CERT_BASE64, TEST_IDP_SP_CERT_BASE64",派生,"secrets init が idp.crt / sp.crt を書き、描画が PEM の枠を外す",双方のメタデータ
```

秘密はこれらのプレースホルダを通してしか描画結果に入らず、二つの `.key` ファイルは `runtime/config/idp/cert/` からモード `0600` でマウントします（`runtime/` 自体は `0700`）。ここに既定値を持つものはありません。

### 後続作業（この変更では実装しない）

```toon
followups[5]{id,where,what}:
  F-1,installer/grdm_dev/compose.py,"auth が shibboleth のとき templates/idp/*.tmpl を runtime/config/idp/{config,metadata}/ と runtime/config/shibboleth_sp/ に描画し、sp-attribute-map.xml を複写し、runtime/config/idp/cert/ を作り、`accept` が S5 を選べるよう GRDM_AUTH を runtime/.env に記録する"
  F-2,installer/grdm_dev/secrets.py,"TEST_IDP_SECRET_SALT と TEST_IDP_ADMIN_PASSWORD を SECRET_KEYS に加え、init と rotate で自己署名の RSA-2048 鍵対 idp.key/idp.crt と sp.key/sp.crt（CN=127.0.0.1、10 年、鍵は 0600）を runtime/config/idp/cert/ に生成する。GRDM_PORT_TEST_IDP=8081 と GRDM_PORT_SHIBBOLETH_SP=8082 を DEFAULT_PORTS（plan.py、secrets.py、acceptance/conftest.py）に加える"
  F-3,manifest/hardening.json,"非 root の test-idp イメージができたら test_idp の例外を外す（ADR-05）。shibboleth_sp の例外は M4 まで残す"
  F-4,manifest/upstreams.json,"部品 `test-idp`（services [test_idp]、profile full、両プラットフォーム、上流なし）を追加し、compose render がこのサービスに専用イメージを与えるようにする。test_idp を Shibboleth-SP の services から外す。二つのポートを SPEC-02 §4 のポート表に加える"
  F-5,installer/grdm_dev/accept.py,"--seed --auth shibboleth がテスト IdP の entityID と模擬利用者の機関（MOCK Institution）に対応する OSF の機関を作る。GRDM_AUTH が shibboleth でないとき --only S5 は実行を拒む"
```

---

## Glossary / 用語

| Term | English note | 日本語注 |
|---|---|---|
| IdP / SP | The server that checks who you are / the service that trusts that answer. | 「あなたが誰か」を確かめるサーバ／その答えを信頼するサービス。 |
| SAML | The message format an IdP and an SP use to pass a login result. | IdP と SP がログイン結果を渡し合うための文書の形式。 |
| Template | A text file with placeholders that are filled in at render time. | 描画時に埋めるプレースホルダを持つテキストファイル。 |
| entityID | The unique name of an IdP or SP in SAML, usually a URL. | SAML における IdP や SP の一意な名前。たいてい URL。 |
| RequestMap | The part of the Shibboleth SP configuration that says which paths need a session and which attributes. | Shibboleth SP の設定のうち、どのパスにセッションとどの属性が要るかを定める部分。 |
