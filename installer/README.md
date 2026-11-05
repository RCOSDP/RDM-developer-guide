# grdm-dev Installer / インストーラー

> **Summary:** The Python package behind `./installer/install.sh`. One subcommand per module; standard library only. Normative text is [SPEC-02](../docs/spec/02_installer_cli.md).
> **概要:** `./installer/install.sh` の裏側にある Python パッケージ。モジュールごとに 1 サブコマンド、標準ライブラリのみ。規範は [SPEC-02](../docs/spec/02_installer_cli.md)。

**Jump:** [English](#english) · [日本語](#japanese)

- Version / 版: 0.2 — 2026-11-06. **Learned:** a glossary term is only explained for the reader when its note and REF-01 link sit at the first prose use, counting lower-case and plural forms, so first-use notes with links were added in both halves (SPEC-06 §3). ／ 用語注と REF-01 へのリンクは、小文字や複数形も含めた本文の初出に置かなければ読者に届かないと分かったため、英和両方の初出にリンク付きの用語注を補った（SPEC-06 §3）。
- Version / 版: 0.1 — 2026-11-05. **Learned:** the module contract (`register`/`run`, injectable runner) had to be fixed before several people could implement subcommands in parallel without stepping on each other. ／ 複数人が同時にサブコマンドを実装してもぶつからないよう、モジュールの契約（`register`/`run`、差し替え可能な runner）を先に固定する必要があると分かった。
- Related: [docs/README.md](../docs/README.md) · [SPEC-02](../docs/spec/02_installer_cli.md) · [SPEC-04](../docs/spec/04_acceptance_tests.md)

---

<a id="english"></a>
## English

[→ 日本語版へ](#japanese)

### Layout

See [SPEC-02 §9](../docs/spec/02_installer_cli.md). Shared parts: `cli.py` (parsing, dispatch), `context.py` (root, runtime/, `--yes`, confirm), `exit_codes.py` + `messages.tsv` (one table for bash and Python), `toon.py` (report encoder), `report.py` (`emit`, `error`).

### Module contract

```python
def register(subparsers): ...   # add a sub-parser; call set_defaults(_module=sys.modules[__name__])
def run(ctx, args) -> int: ...  # return a code from grdm_dev.exit_codes
```

Modules that call external tools take an injectable `runner` so unit tests never need Docker (the tool that builds images and runs containers; see [REF-01](../docs/reference/REF-01_Glossary.md)). Run tests with `python3 -m unittest discover -s installer/tests` from the repository root (set `PYTHONPATH=installer` or `pip install -e installer`).

---

<a id="japanese"></a>
## 日本語

[→ To English](#english)

### 構成

[SPEC-02 §9](../docs/spec/02_installer_cli.md) を参照。共通部品: `cli.py`（解析と振り分け）、`context.py`（ルート、runtime/、`--yes`、確認）、`exit_codes.py` と `messages.tsv`（bash と Python が同じ表を使う）、`toon.py`（報告の符号化）、`report.py`（`emit`、`error`）。

### モジュールの契約

```python
def register(subparsers): ...   # サブパーサを追加し set_defaults(_module=sys.modules[__name__]) を呼ぶ
def run(ctx, args) -> int: ...  # grdm_dev.exit_codes の値を返す
```

外部の道具を呼ぶモジュールは差し替え可能な `runner` を受け取り、単体テストで Docker（イメージを作りコンテナを動かす道具。[REF-01](../docs/reference/REF-01_Glossary.md)）を要らなくする。テストはリポジトリのルートで `python3 -m unittest discover -s installer/tests`（`PYTHONPATH=installer` か `pip install -e installer`）。

---

## Glossary / 用語

| Term | English note | 日本語注 |
|---|---|---|
| Subcommand | A word after the command that picks what to do, like `doctor` in `grdm-dev doctor`. | コマンドの後ろに付けて何をするか選ぶ言葉。`grdm-dev doctor` の `doctor`。 |
| Runner | A small function that runs another program; tests swap it for a fake. | 別のプログラムを実行する小さな関数。テストでは偽物に差し替える。 |
