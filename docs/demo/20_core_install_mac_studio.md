# DEMO-20 Core Install on Mac Studio / Mac Studio でのコア導入記録

> **Summary:** What actually happened when `./installer/install.sh --yes --no-open --profile core` was run on the Mac Studio (Apple Silicon). One entry per run; nothing is edited after the fact.
> **概要:** Mac Studio（Apple Silicon）で `./installer/install.sh --yes --no-open --profile core` を実行したときに実際に起きたこと。実行ごとに 1 節。後から書き換えない。

**Jump:** [English](#english) · [日本語](#japanese)

- Version / 版: 0.1 — 2026-11-05. **Learned:** the first real run proved the stop-at-first-failure design and exposed that an EOL Python 3.5 image cannot be built for arm64, which the specifications had only predicted. ／ 最初の実行で「最初の失敗で止まる」設計が働くことと、EOL の Python 3.5 イメージは arm64 で組めないこと（仕様では予測だった）が実証された。
- Normative source: [SPEC-02 Installer CLI](../spec/02_installer_cli.md) · [SPEC-04 Acceptance Tests](../spec/04_acceptance_tests.md)
- Related: [docs/demo/README.md](README.md) · [docs/status/README.md](../status/README.md) · [ADR-03 Staged Security Gate](../decisions/ADR-03_Staged_Security_Gate.md)

---

<a id="english"></a>
## English

[→ 日本語版へ](#japanese)

### Run 1 — 2026-11-05, branch `feat/m2-installer` (PR #21, before review fixes)

Host (from `grdm-dev doctor`): macOS 27.2, arm64, 128 GiB memory, Docker 29.5.2, Compose 5.6.0, buildx present. Supported, Docker OK.

```toon
run1:
  command: ./installer/install.sh --yes --no-open --profile core
  env: GRDM_WITH_ACCEPT=1
  result: exit 30 (image build failed)
  steps[5]{step,code,status}:
    doctor,0,ok
    plan,0,ok
    "secrets init",0,ok
    "compose render",0,ok
    build,30,failed
  images[3]{component,platform,status,note}:
    osf.io,linux/arm64,built,"2.92 GB; Debian buster archive packages (EOL base)"
    waterbutler,linux/arm64,built,1.28 GB
    modular-file-renderer,linux/arm64,build-failed,"pip: no matching distribution for pandas==0.25.1 on Python 3.5 / arm64"
```

What this proves:

- The bootstrap (`install.sh` → `.venv/` → `grdm-dev install`) works end to end on a clean macOS shell.
- The sequence stops at the first failing step and returns that step's exit code (30), as [SPEC-02 §2.1](../spec/02_installer_cli.md) requires; nothing was started.
- The EOL base images (see [ADR-03](../decisions/ADR-03_Staged_Security_Gate.md)) are not only a security problem but a build problem on Apple Silicon.

Decision taken: components whose base cannot be built for arm64 (modular-file-renderer, ember-osf-web, cas-overlay) get `build_platform: linux/amd64` in the manifest ([SPEC-01](../spec/01_manifest.md)) and run under emulation until M4 modernizes them. Run 2 will be recorded below after the review fixes land.

Evidence: full log kept in the session scratchpad only (contains package download noise, no secrets). The `runtime/` directory on the Mac Studio holds `.env` (0600), the rendered Compose file and two built images; it is git-ignored.

---

<a id="japanese"></a>
## 日本語

[→ To English](#english)

### 第 1 回 — 2026-11-05、ブランチ `feat/m2-installer`（PR #21、レビュー修正前）

ホスト（`grdm-dev doctor` より）: macOS 27.2、arm64、メモリ 128 GiB、Docker 29.5.2、Compose 5.6.0、buildx あり。対応ホスト、Docker 正常。

```toon
run1:
  command: ./installer/install.sh --yes --no-open --profile core
  env: GRDM_WITH_ACCEPT=1
  result: "終了コード 30（イメージのビルド失敗）"
  steps[5]{step,code,status}:
    doctor,0,ok
    plan,0,ok
    "secrets init",0,ok
    "compose render",0,ok
    build,30,failed
  images[3]{component,platform,status,note}:
    osf.io,linux/arm64,built,"2.92 GB。Debian buster のアーカイブからパッケージ取得（EOL ベース）"
    waterbutler,linux/arm64,built,1.28 GB
    modular-file-renderer,linux/arm64,build-failed,"pip: Python 3.5 / arm64 向けの pandas==0.25.1 が存在しない"
```

これで分かったこと:

- ブートストラップ（`install.sh` → `.venv/` → `grdm-dev install`）は、素の macOS のシェルで端から端まで動く。
- 手順は最初に失敗した段階で止まり、その段階の終了コード（30）を返す。[SPEC-02 §2.1](../spec/02_installer_cli.md) のとおりで、サービスは何も起動していない。
- EOL のベースイメージ（[ADR-03](../decisions/ADR-03_Staged_Security_Gate.md)）は安全性の問題だけでなく、Apple Silicon ではビルドの問題でもある。

決めたこと: arm64 で組めない部品（modular-file-renderer、ember-osf-web、cas-overlay）は manifest に `build_platform: linux/amd64` を持たせ（[SPEC-01](../spec/01_manifest.md)）、M4 で近代化するまでエミュレーションで動かす。第 2 回はレビュー修正の反映後に下へ追記する。

証跡: 全ログはセッションの作業領域にのみ保管（パッケージ取得の出力が大半で、秘密は含まない）。Mac Studio の `runtime/` には `.env`（0600）、生成した Compose ファイル、ビルド済みイメージ 2 つがあり、git では無視される。

---

## Glossary / 用語

| Term | English note | 日本語注 |
|---|---|---|
| Emulation | Running a program built for one kind of CPU on another kind, slower but working. | ある種類の CPU 向けに作ったプログラムを別の CPU で動かすこと。遅いが動く。 |
| Wheel | A ready-made package of Python code for one CPU type; if none exists, pip must compile it. | ある CPU 向けにできあがった Python の部品の箱。無いと pip が自分で組み立てる。 |
