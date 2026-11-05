# MOCK IdP Fixtures / 模擬 IdP フィクスチャ

> **Summary:** The invented users and SAML attributes that the bundled test IdP releases in acceptance scenario S5. Everything here is MOCK: `mock-` prefixes, the reserved `.test` domain, no real person, institution, or e-mail, ever — with one written exception, the `eduPersonAffiliation` vocabulary.
> **概要:** 受入シナリオ S5 で同梱のテスト IdP が送る、作り物の利用者と SAML 属性。ここにあるものはすべて MOCK（模擬）である。`mock-` の接頭辞、予約ドメイン `.test` を使い、実在の人・機関・メールは決して置かない。明文化した例外は `eduPersonAffiliation` の語彙だけ。

**Jump:** [English](#english) · [日本語](#japanese)

- Version / 版: 0.2 — 2026-11-06. **Learned:** a rule that says "every value" while the test quietly exempts a surname and a vocabulary is not a rule; the surname became `MOCK-USER`, the vocabulary exception is written here and in ADR-05 §3.5 and encoded as an allow-list of exactly its four values, and the comparison with `authsources.php.tmpl` is per user and per attribute so swapped values no longer pass. ／ 「全値」と言いながら試験が姓と語彙を黙って除外する規則は規則ではない。姓は `MOCK-USER` にし、語彙の例外はここと ADR-05 §3.5 に明記して正確に四値の許可一覧として符号化し、`authsources.php.tmpl` との比較を利用者・属性単位にして値の入替が通らないようにした。
  - 0.1 — 2026-11-06. **Learned:** a mock attribute that merely looks plausible (`Test User 01`, `test01@idp.test`) can still be mistaken for a real record in a screenshot or a log; a visible `mock-` prefix on every value and a `MOCK` label in the file itself remove the doubt (POL-05 §4 separation of mock and real data). ／ もっともらしいだけの模擬属性（`Test User 01`、`test01@idp.test`）は、スクリーンショットやログの中で実データと見分けにくい。全値に見える `mock-` 接頭辞と、ファイル自身の `MOCK` 表示が疑いをなくすと分かった（POL-05 §4 の模擬と実データの分離）。
- Normative source: [SPEC-04 §5](../../../../docs/spec/04_acceptance_tests.md#english) · [ADR-05 Test IdP for Shibboleth](../../../../docs/decisions/ADR-05_Test_IdP_for_Shibboleth.md) · [POL-01](../../../../docs/policy/POL-01_Developer_Environment_2027_Position.md)
- Related: [installer/acceptance/README.md](../../README.md) · [templates/idp/README.md](../../../grdm_dev/templates/idp/README.md) · `test_s5_shibboleth.py`

---

<a id="english"></a>
## English

[→ 日本語版へ](#japanese)

### What is here

`mock_users.json` is the canonical list of *IdP* users (an IdP, identity provider, is the server that checks who you are when you log in). The test IdP ([ADR-05](../../../../docs/decisions/ADR-05_Test_IdP_for_Shibboleth.md)) is configured from `installer/grdm_dev/templates/idp/authsources.php.tmpl`, which carries the same users; `installer/tests/test_compose.py` fails when the two drift apart.

```toon
mock_users[3]{username,role,eduPersonAffiliation,expected}:
  mock-user-01,success,"member faculty","SP accepts; GRDM dashboard with institution MOCK Institution"
  mock-user-02,success-second,"member student","SP accepts; second person for two-user checks"
  mock-user-noaff,rejection,affiliate,"SP RequestMap denies (403 error page); no GRDM session cookie"
```

The stored attributes are the ones GakuNin (the Japanese academic access federation) commonly releases: `uid` (login key, never released), `eduPersonPrincipalName`, `mail`, `displayName`, `jaDisplayName`, `givenName`, `sn`, `o`, `jaOrganizationName`, `eduPersonAffiliation`, `eduPersonScopedAffiliation`, `eduPersonEntitlement`, `isMemberOf`. Two more are *derived* at login from `uid` and are therefore not stored per user (`derived_identifiers`): `eduPersonTargetedID` (a persistent NameID) and `pairwise-id`. The wire names (OIDs) each attribute travels under are the explicit map of ADR-05 §3.7.

### Rules (POL-05 §4, SPEC-04 §3.5)

1. Every scalar value starts with `mock-`, `MOCK`, `モック` or `https://idp.mock.test/`, or ends in `@idp.mock.test`; surnames are `MOCK-USER`, given names `mock-…`. A reviewer can tell a mock from a real record at a glance.
   **Exception (ADR-05 §3.5):** `eduPersonAffiliation` is a controlled vocabulary and the rule of the SP (service provider, the GRDM-side part that trusts the login) can only be exercised with real values, so exactly `member`, `faculty`, `student`, `affiliate` are allowed there and nowhere else. The fixture records this under `affiliation_vocabulary_exception`; `installer/tests/test_compose.py` encodes it as an allow-list of exactly those four values (`AFFILIATION_ALLOW_LIST`) and compares the fixture with `authsources.php.tmpl` per user and per attribute.
2. No real name, e-mail, institution, group, or entitlement URI. `https://idp.mock.test/...` is not a registered name.
3. Passwords here protect nothing: they are the exampleauth passwords of a container that only answers on `127.0.0.1`. They still never appear in `runtime/.env`, reports, or screenshots (the `accept` masking covers `mock-pass-*` as token-like strings).
4. Adding a user means editing `mock_users.json` *and* `authsources.php.tmpl` in the same commit, then bumping this version line.
5. Real institution attributes, if ever needed for a manual check, live outside this repository and never in `installer/`.

---

<a id="japanese"></a>
## 日本語

[→ To English](#english)

### ここにあるもの

`mock_users.json` が、*IdP*（アイデンティティプロバイダ。ログインのときに「あなたが誰か」を確かめるサーバ）の利用者一覧の正本です。テスト IdP（[ADR-05](../../../../docs/decisions/ADR-05_Test_IdP_for_Shibboleth.md)）は `installer/grdm_dev/templates/idp/authsources.php.tmpl` から設定され、そこにも同じ利用者が書かれています。二つがずれると `installer/tests/test_compose.py` が失敗します。

```toon
mock_users[3]{username,role,eduPersonAffiliation,expected}:
  mock-user-01,success,"member faculty","SP が受け入れ、機関 MOCK Institution 付きで GRDM ダッシュボード"
  mock-user-02,success-second,"member student","SP が受け入れ。二人目の確認に使う"
  mock-user-noaff,rejection,affiliate,"SP の RequestMap が拒む（403 のエラー画面）。GRDM のセッション cookie は作られない"
```

保持する属性は GakuNin（日本の学術認証フェデレーション）がよく送るものです。`uid`（ログインの鍵。送出しない）、`eduPersonPrincipalName`、`mail`、`displayName`、`jaDisplayName`、`givenName`、`sn`、`o`、`jaOrganizationName`、`eduPersonAffiliation`、`eduPersonScopedAffiliation`、`eduPersonEntitlement`、`isMemberOf`。さらに二つはログイン時に `uid` から*導出*されるので利用者ごとには保持しません（`derived_identifiers`）。`eduPersonTargetedID`（永続 NameID）と `pairwise-id` です。各属性がワイヤ上で使う名前（OID）は ADR-05 §3.7 の明示的な対応表です。

### 規則（POL-05 §4、SPEC-04 §3.5）

1. すべてのスカラー値は `mock-`・`MOCK`・`モック`・`https://idp.mock.test/` で始まるか、`@idp.mock.test` で終わる。姓は `MOCK-USER`、名は `mock-…`。レビュワが一目で模擬と分かる。
   **例外（ADR-05 §3.5）:** `eduPersonAffiliation` は語彙が統制されており、SP の規則は実在の値でしか試せないため、この属性に限り正確に `member`・`faculty`・`student`・`affiliate` を許し、ほかでは許さない。フィクスチャは `affiliation_vocabulary_exception` にこれを記録し、`installer/tests/test_compose.py` はこの四値だけの許可一覧（`AFFILIATION_ALLOW_LIST`）として符号化し、`authsources.php.tmpl` との比較を利用者・属性単位で行う。
2. 実在の名前・メール・機関・グループ・entitlement の URI を置かない。`https://idp.mock.test/...` は登録されていない名前である。
3. ここのパスワードは何も守らない。`127.0.0.1` にしか応えないコンテナの exampleauth のパスワードにすぎない。それでも `runtime/.env`・報告・スクリーンショットには出さない（`accept` の伏せ字は `mock-pass-*` をトークンらしい文字列として隠す）。
4. 利用者を足すときは、同じコミットで `mock_users.json` **と** `authsources.php.tmpl` を直し、この版の行を上げる。
5. 手作業の確認で実在の機関属性が要るときは、このリポジトリの外に置き、`installer/` には決して入れない。

---

## Glossary / 用語

| Term | English note | 日本語注 |
|---|---|---|
| IdP / SP | The server that checks who you are / the service that trusts that answer. | 「あなたが誰か」を確かめるサーバ／その答えを信頼するサービス。 |
| SAML | The message format an IdP and an SP use to pass a login result. | IdP と SP がログイン結果を渡し合うための文書の形式。 |
| GakuNin | The Japanese academic access federation that GRDM logs in through. | GRDM がログインに使う、日本の学術認証フェデレーション。 |
| Mock | Invented data that stands in for the real thing in a test. | 試験で本物の代わりに使う、作り物のデータ。 |
