# Acceptance Run Records / 受入実行の記録

> **Summary:** Each run of `grdm-dev accept` writes its evidence into a folder here, named by run id. Only runs cited by DEMO-20 are committed.
> **概要:** `grdm-dev accept` を実行するたびに、その証跡が実行 ID 名のフォルダとしてここに書かれます。リポジトリには DEMO-20 が引用する実行だけを置きます。

**Jump:** [English](#english) · [日本語](#japanese)

- Version / 版: 0.4 — 2026-11-10. **Learned:** failure output of a committed run (`acc-20261109T131240Z-00dff9`) printed disposable test identities and passwords, because the masking set held only `runtime/.env` values; all three committed run folders were put through the same masking logic once (only that run changed, and no result changed), and these records are otherwise never edited (PR #35 review r1, R1-01). ／ マスク対象が `runtime/.env` の値だけだったため、コミット済みの実行 `acc-20261109T131240Z-00dff9` の失敗出力に、使い捨て試験アカウントの識別子とパスワードが含まれていた。コミット済みの三実行すべてに同じマスク処理を一度だけ適用し（変わったのはこの実行のみで、結果は不変）、それ以外の編集は行わない（PR #35 レビュー r1、R1-01）。
- Version / 版: 0.3 — 2026-11-10. **Learned:** only the runs a record cites are kept in the repository; the others stay local. ／ リポジトリに残すのは記録が引用する実行だけで、他は手元に置く。
  0.2 — 2026-11-05. **Learned:** traces are raw and may hold secrets, so the public evidence folder keeps only screenshots and masked text (PR #21 review r2). ／ トレースは生で秘密を含み得るため、公開の証跡フォルダにはスクリーンショットとマスク済みの文字だけを置く（PR #21 レビュー r2）。
  0.1 — 2026-11-05. **Learned:** the evidence folder must exist with a stated layout before the first run, so that SPEC-04 and the demo index can link to it. ／ 最初の実行の前に、証跡フォルダと決まった中身をここに書いておく必要があると分かった。SPEC-04 と実証の索引がリンクできるようにするためである。
- Normative source: [SPEC-04 Acceptance Tests](../../spec/04_acceptance_tests.md)
- Related: [docs/demo/README.md](../README.md) · [docs/status/README.md](../../status/README.md)

---

<a id="english"></a>
## English

[→ 日本語版へ](#japanese)

### What is stored here

Every run of the acceptance tests (automated browser tests that check the environment works, see [SPEC-04](../../spec/04_acceptance_tests.md)) creates one folder `runs/<run_id>/` with:

| File | Meaning |
|---|---|
| `results.toon` | Human- and AI-readable summary (TOON: a compact text form of JSON) |
| `results.json` | The same data for machines (canonical) |
| `junit.xml` | Test results in the format CI tools read |
| `screenshots/` | Only when a test failed: what the browser saw. Browser traces are not kept here; with `--trace` they go to `runtime/reports/quarantine/<run_id>/`, which is private and git-ignored |

Records are written by `grdm-dev accept`; do not edit them by hand. No secrets are ever written here: seeded test identities and passwords count as secrets and are masked too.

### Current state

Runs cited by [DEMO-20](../20_core_install_mac_studio.md#english) are kept here.

---

<a id="japanese"></a>
## 日本語

[→ To English](#english)

### ここに置くもの

受入試験（環境が動くことを確かめる自動のブラウザ試験。[SPEC-04](../../spec/04_acceptance_tests.md) 参照）を実行するたびに、`runs/<run_id>/` というフォルダが一つ作られ、次が入ります。

| ファイル | 意味 |
|---|---|
| `results.toon` | 人と AI が読む要約（TOON: JSON を短い文字で表した形） |
| `results.json` | 機械が読む同じデータ（正本） |
| `junit.xml` | CI の道具が読む形式の試験結果 |
| `screenshots/` | 試験が失敗したときだけ: ブラウザが見ていた画面。ブラウザのトレースはここには置かない。`--trace` のときは `runtime/reports/quarantine/<run_id>/`（非公開、git 管理外）へ |

記録は `grdm-dev accept` が書きます。手で編集しないでください。秘密情報はここに書かれません。試験用に作るアカウントの識別子とパスワードも秘密情報として伏せます。

### いまの状態

[DEMO-20](../20_core_install_mac_studio.md#japanese) が引用する実行をここに置いています。

---

## Glossary / 用語

| Term | English note | 日本語注 |
|---|---|---|
| Run id | A short unique name for one test run, like a receipt number. | 一回の試験実行につける短い名前。レシート番号のようなもの。 |
| JUnit XML | A standard file format that test tools use to report pass/fail. | 試験の道具が合否を報告するときの標準の形式。 |
