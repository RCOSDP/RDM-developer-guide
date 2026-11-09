# SPEC-01 Upstream Manifest / 上流マニフェスト

> **Summary:** The manifest is the single source of truth for what the installer builds: every component, its upstream repositories pinned to exact commits, the pull requests we adopt, the base and target images, and the profiles and platforms. This page defines its schema, its rules, and the checks that `grdm-dev manifest check` runs.
> **概要:** マニフェストは「インストーラーが何を組むか」の唯一の正本です。全部品、固定したコミットの上流、採用する PR、現行と目標のイメージ、プロファイルと対応アーキテクチャを持ちます。この文書はその形、規則、`grdm-dev manifest check` の検査項目を定めます。

**Jump:** [English](#english) · [日本語](#japanese)

- Version / 版: 0.10 — 2026-11-10. **Learned:** per-volume init containers multiplied hardening exceptions and still missed redis and the other uid-1000 volumes, so one generic owner step, derived from each volume's writers, replaces them (cross-OS audit, 2026-11-10). Also, a built component's image can need a change that its integration commit does not carry (npm in the running y-websocket image), so this repository may supply the recipe over the same pinned checkout (`build_dockerfile`, MC-16). ／ ボリュームごとの init コンテナは堅牢化の例外を増やすだけで redis や他の uid 1000 のボリュームを取りこぼしていた。各ボリュームの書き手から導く一つの汎用の所有者設定の段に置き換えると分かった（OS 横断の監査、2026-11-10）。また、組む部品のイメージには、統合コミットに無い変更が要ることがある（動作中の y-websocket イメージの npm）。そこで同じ固定 checkout に対し本リポジトリがレシピを与えられるようにした（`build_dockerfile`、MC-16）。
  0.9 — 2026-11-06. **Learned:** an infra component may need an image this repository builds itself when the official one is amd64-only and unusable under emulation (`image_build`, MC-15, ADR-07; real install run 19). ／ 公式イメージが amd64 のみでエミュレーションでは使えないとき、infra の部品には本リポジトリ自身が組むイメージが要る（`image_build`、MC-15、ADR-07。実機第 19 回）。
  0.8 — 2026-11-06. **Learned:** a third-party infra image can be single-architecture too; `build_platform` is therefore allowed on `infra` with a note, so `compose render` pins the platform and `up` does not fail on Apple Silicon (real install run 6). ／ 第三者の基盤イメージも単一アーキテクチャのことがある。`infra` にも `note` 付きで `build_platform` を認め、`compose render` がプラットフォームを固定して Apple Silicon の `up` が失敗しないようにした（実機第 6 回）。
  0.7 — 2026-11-06. **Learned:** a repository with a Dockerfile is not necessarily a component that can be built from its own checkout (wiki-frontend's Dockerfile is osf.io's and its image holds only a webpack bundle), so the manifest needs `overlay_of`, the overlay image is tagged with both commits (`<base_sha12>-<overlay_sha12>`), and its services are one-shot copiers into a named volume (MC-14, [ADR-06](../decisions/ADR-06_Wiki_Frontend_Overlay.md)); and, independently, a glossary term is only explained for the reader when its note and REF-01 link sit at the first prose use, counting lower-case and plural forms, so first-use notes with links were added in both halves (SPEC-06 §3). ／ Dockerfile があるリポジトリが必ず自分の checkout から組める部品とは限らない（wiki-frontend の Dockerfile は osf.io のもので、そのイメージは webpack の束しか持たない）ため、manifest には `overlay_of` が要り、オーバーレイのイメージは両コミット（`<ベース sha12>-<オーバーレイ sha12>`）をタグに持ち、そのサービスは名前付きボリュームへ写す一回限りのものになる（MC-14、[ADR-06](../decisions/ADR-06_Wiki_Frontend_Overlay.md)）。また別に、用語注と REF-01 へのリンクは、小文字や複数形も含めた本文の初出に置かなければ読者に届かないと分かったため、英和両方の初出にリンク付きの用語注を補った（SPEC-06 §3）。
- Version / 版: 0.6 — 2026-11-06. **Learned:** the fourth real install on Apple Silicon showed that a repository with a Dockerfile is not necessarily a component that can be built from its own checkout: the wiki-frontend Dockerfile is osf.io's with the Python steps removed and COPYs paths only the osf.io tree has, and the image it produces holds a webpack bundle, not a runtime. So the manifest needs `overlay_of` ("built from the base's checkout plus my files"), the overlay image is tagged with both commits (`<base_sha12>-<overlay_sha12>`), and its services are one-shot copiers of the bundle into a named volume (MC-14, [ADR-06](../decisions/ADR-06_Wiki_Frontend_Overlay.md)). ／ Apple Silicon での第 4 回実導入で、Dockerfile があるリポジトリが必ず自分の checkout から組める部品とは限らないと分かった。wiki-frontend の Dockerfile は osf.io のものから Python 手順を除いた写しで、osf.io の木にしか無いパスを COPY し、できるイメージは実行環境でなく webpack の束を持つだけである。だから manifest には「ベースの checkout に自分のファイルを重ねて組む」を表す `overlay_of` が要り、オーバーレイのイメージは両コミット（`<ベース sha12>-<オーバーレイ sha12>`）をタグに持ち、そのサービスは束を名前付きボリュームへ写す一回限りのものになる（MC-14、[ADR-06](../decisions/ADR-06_Wiki_Frontend_Overlay.md)）。
- Version / 版: 0.6 — 2026-11-06. **Learned:** a glossary term is only explained for the reader when its note and REF-01 link sit at the first prose use, counting lower-case and plural forms, so first-use notes with links were added in both halves (SPEC-06 §3). ／ 用語注と REF-01 へのリンクは、小文字や複数形も含めた本文の初出に置かなければ読者に届かないと分かったため、英和両方の初出にリンク付きの用語注を補った（SPEC-06 §3）。
  0.5 — 2026-11-05. **Learned:** the second real install on Apple Silicon showed that a Dockerfile whose base image is a schema-1 manifest cannot be built by current Docker at all, so a digest-pinned `prebuilt_image` fallback is needed per component, with a note and an M4 removal date, because it bypasses the build-from-pinned-source guarantee. ／ Apple Silicon での二度目の実導入で、ベースイメージが schema 1 のマニフェストである Dockerfile は現行 Docker ではまったく組めないと分かった。だから「固定した元から組む」保証を外す代わりに、理由と M4 での撤去を書いた `note` を伴うダイジェスト固定の `prebuilt_image` が部品ごとに要る。
  0.4 — 2026-11-05. **Learned:** the first real build on Apple Silicon showed that an EOL Python 3.5 base cannot install pandas 0.25.1 for arm64, so a per-component `build_platform` is needed until M4 modernizes those images. ／ Apple Silicon での最初の実ビルドで、EOL の Python 3.5 ベースは arm64 向け pandas 0.25.1 を入れられないと分かった。M4 で近代化するまで部品ごとの `build_platform` が要る。
  0.3 — 2026-11-05. **Learned:** building from "the tip of develop" is not reproducible unless the manifest pins that tip, so each component needs an `integration_sha` (nullable until the first strict merge). ／ 「develop の先端」から組むのでは再現できないため、各部品に `integration_sha`（最初の厳密マージまでは null 可）が要ると分かった。
  0.2 — 2026-11-05. **Learned:** a TOON block that is only an example must say so, or readers and the checker treat it as data that has to stay in step with the JSON. ／ 例にすぎない TOON ブロックはそう明記しないと、読者も検査も JSON と一致させるべきデータとして扱ってしまうと分かった。
- Version / 版: 0.1 — 2026-11-05. **Learned:** the public osf.io `develop` (2026-11-05) is already newer than its `-private` twin (2026-11-02), so "the latest" is not one answer; only a file that pins each upstream to a SHA can say what "consistent" means. ／ 公開 osf.io の `develop`（2026-11-05）は `-private`（2026-11-02）より既に新しく、「最新」は一つに決まらない。各上流を SHA で固定したファイルがあってこそ「矛盾なく」を定義できると分かった。
- Normative for: `manifest/upstreams.json` (canonical), `manifest/upstreams.toon` (excerpt), `manifest/README.md`, the `manifest` subcommand of `grdm-dev` ([SPEC-02](02_installer_cli.md)), and every document that quotes the manifest.
- Related: [SPEC-00 Overview](00_overview.md) · [SPEC-05 Upstream tracking](05_upstream_tracking.md) · [SPEC-06 Documentation conventions](06_documentation_conventions.md) · [POL-01 Position](../policy/POL-01_Developer_Environment_2027_Position.md) · [ADR-01 Integration repository placement](../decisions/ADR-01_Integration_Repository_Placement.md) · [ADR-03 Staged security gate](../decisions/ADR-03_Staged_Security_Gate.md) · [docs/README.md](../README.md)

---

<a id="english"></a>
## English

[→ 日本語版へ](#japanese)

### 1. What the manifest is

A *manifest* is a packing list: it says exactly what goes into the box. Ours says, for every component of the environment ([SPEC-00 §2](00_overview.md#2-component-map)), which *upstream* repositories (the original places we copy code from) are combined, at which *SHA* (the 40-character fingerprint of one commit), and which pull requests (*PRs*, proposed changes waiting to be merged; see [REF-01](../reference/REF-01_Glossary.md)) we add on top.

The installer reads the manifest and nothing else to decide what to build. If a fact is not in the manifest, the installer does not know it.

### 2. Files

| File | Role |
|---|---|
| `manifest/upstreams.json` | **Canonical.** The only file machines trust. JSON, UTF-8, two-space indent, keys sorted. |
| `manifest/upstreams.toon` | **Excerpt** in TOON (a compact text form of JSON that people read easily; [SPEC-06 §4](06_documentation_conventions.md#4-diagrams-and-data)). Generated from the JSON by `grdm-dev manifest toon`. Must always equal the JSON. |
| `manifest/README.md` | Explains the two files for readers, bilingual. |

The excerpt contains the top-level fields and, for every component, `id`, `role`, `integration_repo`, `profile`, every field of `upstreams[]`, and `adopted_prs[]` reduced to `repo`, `number`, `status`. It omits `candidate_prs`, images, services, and platforms. Other files under `manifest/` (`allowlist.json`, `allowlist.baseline.json`, `milestone.json`, `hardening.json`, `redteam-targets.json`) are defined by [SPEC-03](03_security_gate.md); their file list is in [SPEC-02 §9](02_installer_cli.md#english).

> **Warning:** This repository is public. The manifest contains **repository names and SHAs only**. It never contains URLs to private repositories, access tokens, or code fragments from `-private` repositories. The CI (continuous integration: automatic checks on every change; see [REF-01](../reference/REF-01_Glossary.md)) secret scan fails the PR (pull request: a proposed change waiting for review; see [REF-01](../reference/REF-01_Glossary.md)) if it finds any.

### 3. Schema

The top level has `schema_version` (integer, currently `1`), `generated_at` (ISO date), an optional `note` (free text), and `components[]`. Infrastructure images (databases, queues, `fakecas`) are components with `role: infra`. Each component has:

| Field | Type | Meaning |
|---|---|---|
| `id` | string | Short name, same as in [SPEC-00 §2](00_overview.md#2-component-map). Unique. |
| `role` | `core` \| `infra` \| `subsystem` | What kind of component. COS repositories are not components; they appear as `upstreams[]` entries with `kind: cos`. |
| `services[]` | list | The Compose service names the component provides, as used in [SPEC-02 §4](02_installer_cli.md#english) (for example `web`, `api`, `admin`, `worker` for `osf.io`; `wiki_assets` for the overlay `wiki-frontend`). Never empty. |
| `integration_repo` | string or `null` | Name of the private integration repository, `RDM-<name>-dev2027`. Name only, never a URL. `null` for `infra`. |
| `integration_branch` | string or `null` | Always `develop`; `null` for `infra`. |
| `integration_sha` | string (40 hex) or null | The commit at the tip of the integration branch `develop` that this manifest pins. `grdm-dev build` and `compose render` use it for image tags. May be `null` until the strict reconstruction PRs are merged; required for M2 acceptance. |
| `build_platform` | string or absent | Platform used to build and run this component's image, for example `linux/amd64`. Absent means the host platform. `grdm-dev build --platform` overrides it. Components whose EOL base has no arm64 wheels (modular-file-renderer, ember-osf-web, cas-overlay until M4) set `linux/amd64`; Compose then runs them under emulation. An `infra` component may set it too, together with a `note`, when its pinned image has no manifest for the other host platform (sharejs and unoconv are linux/amd64 only, real install run 6; elasticsearch2, elasticsearch6 and fakecas now use `image_build`); `compose render` then writes `platform:` for that service so Compose pulls and runs the amd64 image under emulation instead of failing at `up`. |
| `prebuilt_image` | string or absent | A registry image reference pinned by digest (`name@sha256:<64 hex>`, for example `niicloudoperation/rdm-ember-osf-web@sha256:…`) that is run **instead of** building from the integration repository. Allowed only together with a `note` that says why the build is impossible and until which milestone the fallback stays; never a URL or a private-repository reference; not allowed for `infra`. `grdm-dev build` records the component as `prebuilt`, pulls the reference and does not clone or build; `compose render` writes it as `image:` (with `platform:` from `build_platform`); `scan` treats it like any other compose image. **A prebuilt image bypasses the "build from pinned source" guarantee of this specification: nobody can show which commits are inside it.** It is a temporary measure for M2 and must be removed by M4. Current use: `ember-osf-web`, whose Dockerfile base `quay.io/centerforopenscience/ember-base` is a Docker image manifest v2 schema 1 image that current Docker refuses to pull. |
| `overlay_of` | string or absent | Names the *base* component whose checkout is the build context. The overlay cannot be built from its own checkout (its Dockerfile COPYs the base's paths). After both checkouts are synced at their pinned commits, the overlay's files are copied over a copy of the base checkout (`.git` of both left out; the overlay's version wins where both have a file) in `runtime/src/_overlay/<overlay id>/`, and the **overlay's** image is built from that directory with the **overlay's** Dockerfile, tagged with both commits: `grdm-dev/<overlay id>:<base_sha12>-<overlay_sha12>` (with `--push`, `ghcr.io/rcosdp/<overlay id>:<same tag>`). The base component is built normally with its own Dockerfile and tag. The overlay image is a *bundle builder*, not a runtime, so its `services[]` are **one-shot** (template `one_shot: true`, Compose `restart: "no"`): they copy the build output into a named volume and exit; the base's services mount that volume read-only and depend on them with `condition: service_completed_successfully`; `health` accepts them as `exited` with code 0. The base must exist, must not be `infra`, must not be an overlay itself and must not have `prebuilt_image`; the overlay must not be `infra` and must not have `prebuilt_image`; one overlay per base (MC-14; the one-shot template flag is checked by the installer). `plan` and `compose render` show the overlay's services with origin `overlay`. Current use: `wiki-frontend` is an overlay of `osf.io` ([ADR-06](../decisions/ADR-06_Wiki_Frontend_Overlay.md)): its Dockerfile is osf.io's with `node:21-alpine`, webpack 5 and no Python steps, its tree holds only the wiki editor sources, and `wiki_assets` copies `/code/website/static/public/js/` (the webpack `output.path`: `wiki-edit-page.<chunkhash>.js`, `vendor.<hash>.js`, `webpack-assets.json`) into the volume `wiki_static`, mounted at `/code/website/static/public/js/wiki/` in `web`, `api`, `admin` and `worker`. |
| `image_build` | object or absent | `{"context": "<repo-relative directory>", "tag": "<recipe version>"}` on an `infra` component whose image this repository builds itself from the upstream's official release artefact on a digest-pinned base ([ADR-07](../decisions/ADR-07_Native_Builds_of_EOL_Middleware.md)): the directory holds the Dockerfile, the tag names the recipe, `base_image`/`base_image_digest` name the base. Exclusive with `prebuilt_image` and `build_platform`; requires a `note`. `grdm-dev build` tags the result `grdm-dev/<id>:<tag>` for the host platform. First use: `elasticsearch2` (`installer/images/elasticsearch2`, tag `2.4.6-1`). |
| `build_dockerfile` | string or absent | Repo-relative path of a Dockerfile in this repository, used with `-f` instead of the integration repository's own Dockerfile; the build context stays the checkout at the pinned commit and the tag stays its `sha12`. Requires `integration_repo` and a `note`; exclusive with `prebuilt_image` and `overlay_of` (MC-16). `base_image`/`base_image_digest` name the recipe's base and the digest is recorded as an image label. Current use: `y-websocket` (`installer/images/y-websocket/Dockerfile`), whose running image has no npm or yarn. |
| `upstreams[]` | list | Each: `repo` (name), `branch`, `kind` (`public` \| `private` \| `cos`), `tracking_branch` (named by rule 7), `status` (`merged` \| `reference` \| `candidate`), `sha` (40 lowercase hex), `fetched_at` (ISO date). Empty for `infra`. |
| `adopted_prs[]` | list | Each: `repo`, `number`, `title`, `reason`, `status` (`adopted`). PRs applied on top of the merged upstreams. |
| `candidate_prs[]` | list | Same shape; `status` is `candidate` or `rejected`. Not built. |
| `base_image` | string | The image the component builds from today (for example `python:3.6-slim`). For `infra`, the image that is run. |
| `base_image_digest` | string or `null` | The `sha256:` digest of `base_image` once pinned ([SPEC-03 §3.4](03_security_gate.md#english)); `null` until then. |
| `target_image` | object | Keys `M4` and `M5`, each the image planned at that milestone (a *milestone* is a checkpoint; [SPEC-00 §5](00_overview.md#5-milestone-ladder)), or `null` when nothing changes at that milestone. |
| `profile` | `minimum` \| `core` \| `full` | The smallest installer profile that includes the component ([SPEC-02 §4](02_installer_cli.md#english)). |
| `platforms[]` | list | Subset of `linux/arm64`, `linux/amd64`. |
| `note` | string or `null` | Optional free text (for example "mutually exclusive with fakecas"). |

Example for one component, in TOON:

```toon
schema_version: 1
generated_at: 2026-11-05
note: "Names and SHAs only."
components[1]:
  - id: waterbutler
    role: core
    services[2]: wb,wb_worker
    integration_repo: RDM-waterbutler-dev2027
    integration_branch: develop
    upstreams[3]{repo,branch,kind,tracking_branch,status,sha,fetched_at}:
      RDM-waterbutler,develop,public,upstream/public-develop,merged,0000000000000000000000000000000000000000,2026-11-05
      RDM-waterbutler-develop-private,develop,private,upstream/private-develop,merged,0000000000000000000000000000000000000000,2026-11-05
      CenterForOpenScience/waterbutler,develop,cos,upstream/cos-develop,reference,0000000000000000000000000000000000000000,2026-11-05
    adopted_prs[1]{repo,number,title,reason,status}:
      RDM-waterbutler,101,"Python 3.13, dependency update, multi-stage image (WIP)","vulnerability remediation (M4)",adopted
    candidate_prs[1]{repo,number,title,reason,status}:
      RDM-waterbutler,93,"S3 SigV4",feature,candidate
    base_image: python:3.6-slim-buster
    base_image_digest: null
    target_image:
      M4: "python:3.13-slim multi-stage, non-root"
      M5: null
    profile: core
    platforms[2]: linux/arm64,linux/amd64
    note: null
```

The all-zero SHAs above are placeholders for the example only; a real manifest never contains them. The block is an illustrative example, not a mirror of `manifest/upstreams.json`, so it carries no `<!-- canonical: ... -->` declaration ([SPEC-06 §4](06_documentation_conventions.md#4-diagrams-and-data)); blocks that do mirror the manifest (for example in [SPEC-00 §2](00_overview.md#english)) declare it.

### 4. Rules

1. **SHAs are pinned.** Every `upstreams[].sha` is a real 40-character commit that exists on the named branch at `fetched_at`. Branch (a separate line of work in a repository; see [REF-01](../reference/REF-01_Glossary.md)) names alone are never enough.
2. **A change to the manifest is a PR.** Nobody edits `upstreams.json` on `develop` directly. The weekly integration PR ([SPEC-05 §3](05_upstream_tracking.md#3-weekly-integration-pr)) is the normal way SHAs move. Adopting or rejecting a PR is also a manifest PR, with the `reason` filled in.
3. **Integration order is fixed:** merge the `public` upstream with `status: merged`, then the `private` one, then apply `adopted_prs` in list order. A component that has no `public` upstream (the private subsystems) starts from its `private` upstream. The `cos` upstream (`status: reference`) is never merged; it is compared.
4. **"Consistent" (矛盾なく) means all of the following:**
   - No two components reference two different SHAs of the same upstream repository and branch.
   - Every `adopted_prs[]` entry applies cleanly (no conflict) on the integration branch built from the pinned upstreams.
   - `upstreams.toon` is byte-for-byte what `grdm-dev manifest toon` produces from `upstreams.json`.
   - Every `integration_repo` named exists and has the branch `develop` plus one tracking branch per `upstreams[]` entry, named exactly as its `tracking_branch`.
5. **Names only.** `repo` and `integration_repo` are bare names (`RDM-osf.io-dev2027`). A value starting with `http`, `git@`, or containing `github.com` is invalid.
6. **Undecided upstreams are listed with `status: candidate`.** They are mirrored to their tracking branch but not merged. Example: `RDM-osf.io-private` (branch `fix/sec-test`, tracking branch `upstream/private-sec-test-fix-sec-test`) is a candidate until the owner decides (plan §7).
7. **Tracking branches are named by one rule:** `upstream/<kind>-<branch>`, where `<branch>` is the upstream branch name with every `/` replaced by `-`. When one component lists two upstreams of the same `kind`, the second inserts a short tag after the kind: `upstream/<kind>-<tag>-<branch>`. Examples: `RDM-ember-osf-web` (`master`) → `upstream/public-master`; `RDM-ember-osf-web-master-private` → `upstream/private-master`; `RDM-OASys-main-private` → `upstream/private-main`; `CenterForOpenScience/osf.io` → `upstream/cos-develop`; `RDM-osf.io-private` (`fix/sec-test`) → `upstream/private-sec-test-fix-sec-test`. The same rule is stated in [SPEC-05 §1](05_upstream_tracking.md#english) and [ADR-01 §3](../decisions/ADR-01_Integration_Repository_Placement.md#english).

### 5. Validation: `grdm-dev manifest check`

Run from the repository root. Exit code `0` means pass; any failure prints one line per finding and exits `20` (manifest invalid, [SPEC-02 §6](02_installer_cli.md#english)).

```sh
grdm-dev manifest check
```

Checks, in order:

```toon
checks[16]{id,rule,severity}:
  MC-01,"upstreams.json parses as JSON and matches schema_version 1",error
  MC-02,"every component id is unique and matches ^[A-Za-z0-9_.-]+$",error
  MC-03,"role is one of core|infra|subsystem; services is a non-empty list",error
  MC-04,"integration_repo matches ^RDM-[A-Za-z0-9_.-]+-dev2027$ or is null for infra",error
  MC-05,"integration_branch is develop, or null for infra",error
  MC-06,"every sha matches ^[0-9a-f]{40}$; base_image_digest is null or sha256:<64 hex>; fetched_at is an ISO date not in the future; prebuilt_image, when present, is name@sha256:<64 hex>, has a non-empty note, is not a URL or private-repository reference, and is not on infra",error
  MC-07,"no value anywhere contains http, git@, github.com, or a token-like string",error
  MC-08,"the same (repo, branch) pair has one sha across all components",error
  MC-09,"adopted_prs status is adopted; candidate_prs status is candidate|rejected; upstreams status is merged|reference|candidate and cos upstreams are reference; number is a positive integer",error
  MC-10,"profile and platforms use only the allowed values; core components list both platforms",error
  MC-11,"upstreams.toon equals the output of grdm-dev manifest toon",error
  MC-12,"with --remote: each integration_repo has develop plus every tracking_branch listed, and each sha is reachable from its tracking_branch",error
  MC-13,"every tracking_branch follows rule 7 (upstream/<kind>[-<tag>]-<branch with / replaced by ->)",error
  MC-14,"overlay_of, when present, names an existing component that is not infra, not an overlay and not prebuilt; the overlay is not infra and not prebuilt; one overlay per base (its services must be one-shot: checked by the installer against the service template)",error
  MC-15,"image_build {context, tag} only on infra; context is a repo-relative directory holding a Dockerfile; tag is a valid image tag; note required; exclusive with prebuilt_image and build_platform (ADR-07)",error
  MC-16,"build_dockerfile only with integration_repo; a plain repo-relative file in this repository; note required; exclusive with prebuilt_image and overlay_of",error
```

`--remote` needs network and credentials and is run in the private `-dev2027` CI, not in this public repository's CI. The documentation check in [SPEC-06 §8](06_documentation_conventions.md#8-checks) reuses MC-11 for TOON blocks quoted in documents.

### 6. Who changes it

| Change | Opened by | Reviewed by | Merged by |
|---|---|---|---|
| Weekly SHA advance | AID agent (weekly job, [SPEC-05](05_upstream_tracking.md)) | REV (Codex Astra), check by QAE (Claude Code Fable) | Owner |
| Adopt / reject a PR | AID or QAE, with `reason` | REV | Owner |
| Change `target_image` | QAE, referencing the milestone plan | REV | Owner |

---

<a id="japanese"></a>
## 日本語

[→ To English](#english)

### 1. マニフェストとは

「マニフェスト」は荷物の明細書です。箱に何が入るかを正確に書きます。私たちのマニフェストは、環境の全部品（[SPEC-00 §2](00_overview.md#2-部品の地図)）について、どの上流（コードを写してくる元のリポジトリ）を、どの SHA（一つのコミットを指す 40 文字の指紋）で重ね、どの PR（プルリクエスト。マージを待っている変更の提案。[REF-01](../reference/REF-01_Glossary.md)）をその上に足すかを書きます。

インストーラーは何を組むかをマニフェストだけから決めます。マニフェストに無いことは、インストーラーは知りません。

### 2. ファイル

| ファイル | 役割 |
|---|---|
| `manifest/upstreams.json` | **正本。** 機械が信じる唯一のファイル。JSON、UTF-8、字下げ 2 つ、キーは並べ替え済み。 |
| `manifest/upstreams.toon` | TOON（JSON を人が読みやすい短い文字形式にしたもの。[SPEC-06 §4](06_documentation_conventions.md#4-図とデータ)）の **抄録**。`grdm-dev manifest toon` が JSON から生成する。常に JSON と一致していなければならない。 |
| `manifest/README.md` | 二つのファイルを読者向けに二言語で説明する。 |

抄録には、最上位の項目と、各部品の `id`・`role`・`integration_repo`・`profile`、`upstreams[]` の全項目、そして `repo`・`number`・`status` に絞った `adopted_prs[]` を載せます。`candidate_prs`、イメージ、サービス、platform は載せません。`manifest/` の下のほかのファイル（`allowlist.json`、`allowlist.baseline.json`、`milestone.json`、`hardening.json`、`redteam-targets.json`）は [SPEC-03](03_security_gate.md) が定め、一覧は [SPEC-02 §9](02_installer_cli.md#japanese) にあります。

> **Warning:** このリポジトリは公開です。マニフェストには **リポジトリ名と SHA だけ** を書きます。非公開リポジトリの URL、アクセストークン、`-private` 由来のコード断片は決して書きません。CI（continuous integration。変更ごとに自動で走る検査。[REF-01](../reference/REF-01_Glossary.md)）の秘密スキャンが見つけたら PR（プルリクエスト。レビュー待ちの変更の提案。[REF-01](../reference/REF-01_Glossary.md)）は不合格です。

### 3. 形（スキーマ）

最上位は `schema_version`（整数。今は `1`）、`generated_at`（ISO 日付）、任意の `note`（自由記述）、`components[]` です。基盤のイメージ（データベース、キュー、`fakecas`）も `role: infra` の部品として載せます。各部品は次を持ちます。

| 項目 | 型 | 意味 |
|---|---|---|
| `id` | 文字列 | 短い名前。[SPEC-00 §2](00_overview.md#2-部品の地図) と同じ。重複しない。 |
| `role` | `core` \| `infra` \| `subsystem` | 部品の種類。COS のリポジトリは部品ではなく、`kind: cos` の `upstreams[]` 要素として現れる。 |
| `services[]` | 配列 | その部品が提供する Compose のサービス名。[SPEC-02 §4](02_installer_cli.md#japanese) と同じ名前（例: `osf.io` は `web`、`api`、`admin`、`worker`。オーバーレイ `wiki-frontend` は `wiki_assets`）。空にしない。 |
| `integration_repo` | 文字列または `null` | 非公開の統合リポジトリの名前 `RDM-<name>-dev2027`。名前だけで URL は書かない。`infra` は `null`。 |
| `integration_branch` | 文字列または `null` | 常に `develop`。`infra` は `null`。 |
| `integration_sha` | 文字列（40 桁の 16 進）または `null` | このマニフェストが固定する統合ブランチ `develop` の先端のコミット。`grdm-dev build` と `compose render` はこの値をイメージのタグに使う。厳密再構築 PR のマージ前は `null` でよいが、M2 の受入では必須。 |
| `build_platform` | 文字列または省略 | この部品のイメージを組んで動かすプラットフォーム。例: `linux/amd64`。省略時はホストと同じ。`grdm-dev build --platform` が優先する。EOL ベースで arm64 の wheel がない部品（M4 までの modular-file-renderer・ember-osf-web・cas-overlay）は `linux/amd64` を指定し、Compose はエミュレーションで動かす。`infra` の部品も、固定したイメージにもう一方のホスト向けのマニフェストがないときは `note` と一緒に指定できる（sharejs・unoconv は linux/amd64 のみ。実機第 6 回。elasticsearch2・elasticsearch6・fakecas は現在 `image_build` を使う）。`compose render` はそのサービスに `platform:` を書き、Compose は `up` で失敗せず amd64 のイメージをエミュレーションで取得・実行する。 |
| `prebuilt_image` | 文字列または省略 | 統合リポジトリから組む **代わりに** 動かす、ダイジェストで固定したレジストリのイメージ参照（`name@sha256:<16 進 64 文字>`。例: `niicloudoperation/rdm-ember-osf-web@sha256:…`）。なぜ組めないか、どの節目までこの代替を続けるかを書いた `note` と一緒にしか書けない。URL や非公開リポジトリの参照は不可。`infra` には使えない。`grdm-dev build` はその部品を `prebuilt` として記録し、参照を pull するだけで clone も build もしない。`compose render` はそれを `image:` に書き（`platform:` は `build_platform` から）、`scan` はほかの Compose イメージと同じに扱う。**事前ビルド済みイメージは、この仕様の「固定した元から組む」保証を外す。中にどのコミットが入っているかを誰も示せない。** M2 のための一時措置であり、M4 までに必ず外す。現在の使用: `ember-osf-web`。その Dockerfile のベース `quay.io/centerforopenscience/ember-base` は Docker image manifest v2 schema 1 のイメージで、現行の Docker は pull を拒否する。 |
| `overlay_of` | 文字列または省略 | ビルドの文脈（context）となる checkout を持つ「ベース」部品の名前。オーバーレイは自分の checkout だけでは組めない（その Dockerfile がベースのパスを COPY する）。両 checkout を固定コミットで同期した後、`runtime/src/_overlay/<オーバーレイ id>/` にベース checkout の写し（両方の `.git` は除く）を作り、その上にオーバーレイのファイルを重ね（両方にあるファイルはオーバーレイ側が勝つ）、その場所から **オーバーレイ側の** Dockerfile で **オーバーレイの** イメージを組む。タグは両コミット: `grdm-dev/<オーバーレイ id>:<ベース sha12>-<オーバーレイ sha12>`（`--push` では `ghcr.io/rcosdp/<オーバーレイ id>:<同じタグ>`）。ベース部品は自分の Dockerfile とタグで通常どおり組む。オーバーレイのイメージは実行環境でなく「束を組む道具」なので、その `services[]` は **一回限り**（テンプレートの `one_shot: true`、Compose の `restart: "no"`）: ビルド成果を名前付きボリュームへ写して終了する。ベースのサービスはそのボリュームを読み取り専用で mount し、`condition: service_completed_successfully` で待つ。`health` は終了コード 0 の `exited` を健康とみなす。ベースは存在し、`infra` でなく、オーバーレイでなく、`prebuilt_image` を持たない。オーバーレイは `infra` でなく、`prebuilt_image` を持たない。ベース一つにオーバーレイは一つ（MC-14。一回限りのテンプレート印はインストーラーが検査）。`plan` と `compose render` はオーバーレイのサービスを origin `overlay` で示す。現在の使用: `wiki-frontend` は `osf.io` のオーバーレイ（[ADR-06](../decisions/ADR-06_Wiki_Frontend_Overlay.md)）。その Dockerfile は osf.io のものに `node:21-alpine` と webpack 5 を入れ Python 手順を除いた写しで、木には Wiki エディタのソースしか無い。`wiki_assets` は `/code/website/static/public/js/`（webpack の `output.path`: `wiki-edit-page.<chunkhash>.js`、`vendor.<hash>.js`、`webpack-assets.json`）をボリューム `wiki_static` に写し、`web`・`api`・`admin`・`worker` はそれを `/code/website/static/public/js/wiki/` に mount する。 |
| `image_build` | オブジェクトまたは省略 | `{"context": "<リポジトリ相対のディレクトリ>", "tag": "<レシピの版>"}`。上流の公式リリース成果物からダイジェスト固定のベース上に本リポジトリ自身がイメージを組む `infra` 部品に書く（[ADR-07](../decisions/ADR-07_Native_Builds_of_EOL_Middleware.md)）。ディレクトリに Dockerfile があり、tag はレシピの版、`base_image`/`base_image_digest` がベースを指す。`prebuilt_image`・`build_platform` と併用不可。`note` 必須。`grdm-dev build` は結果に `grdm-dev/<id>:<tag>` を付けてホスト向けに組む。初出: `elasticsearch2`（`installer/images/elasticsearch2`、tag `2.4.6-1`）。 |
| `build_dockerfile` | 文字列または省略 | 本リポジトリ内の Dockerfile のリポジトリ相対パス。統合リポジトリ自身の Dockerfile の代わりに `-f` で使う。ビルドの文脈は固定コミットの checkout のままで、tag もその `sha12` のまま。`integration_repo` と `note` が必須で、`prebuilt_image`・`overlay_of` と併用不可（MC-16）。`base_image`/`base_image_digest` はレシピのベースを指し、ダイジェストはイメージのラベルに記録する。現在の使用: `y-websocket`（`installer/images/y-websocket/Dockerfile`）。動作中のイメージに npm も yarn も無い。 |
| `upstreams[]` | 配列 | 各要素: `repo`（名前）、`branch`、`kind`（`public` \| `private` \| `cos`）、`tracking_branch`（規則 7 で命名）、`status`（`merged` \| `reference` \| `candidate`）、`sha`（小文字 16 進 40 文字）、`fetched_at`（ISO 日付）。`infra` は空。 |
| `adopted_prs[]` | 配列 | 各要素: `repo`、`number`、`title`、`reason`、`status`（`adopted`）。上流をマージした上に適用する PR。 |
| `candidate_prs[]` | 配列 | 同じ形。`status` は `candidate` か `rejected`。組まない。 |
| `base_image` | 文字列 | その部品が今日組む元のイメージ（例 `python:3.6-slim`）。`infra` では実行するイメージ。 |
| `base_image_digest` | 文字列または `null` | `base_image` を固定したときの `sha256:` ダイジェスト（[SPEC-03 §3.4](03_security_gate.md#japanese)）。固定するまでは `null`。 |
| `target_image` | オブジェクト | キー `M4` と `M5`。各節目（合否の試験がある関門。[SPEC-00 §5](00_overview.md#5-節目のはしご)）で予定するイメージ。その節目で変えないなら `null`。 |
| `profile` | `minimum` \| `core` \| `full` | その部品を含む最小のインストーラープロファイル（[SPEC-02 §4](02_installer_cli.md#japanese)）。 |
| `platforms[]` | 配列 | `linux/arm64`、`linux/amd64` の部分集合。 |
| `note` | 文字列または `null` | 任意の自由記述（例:「fakecas と排他」）。 |

一部品の例を TOON で示します。

```toon
schema_version: 1
generated_at: 2026-11-05
note: "Names and SHAs only."
components[1]:
  - id: waterbutler
    role: core
    services[2]: wb,wb_worker
    integration_repo: RDM-waterbutler-dev2027
    integration_branch: develop
    upstreams[3]{repo,branch,kind,tracking_branch,status,sha,fetched_at}:
      RDM-waterbutler,develop,public,upstream/public-develop,merged,0000000000000000000000000000000000000000,2026-11-05
      RDM-waterbutler-develop-private,develop,private,upstream/private-develop,merged,0000000000000000000000000000000000000000,2026-11-05
      CenterForOpenScience/waterbutler,develop,cos,upstream/cos-develop,reference,0000000000000000000000000000000000000000,2026-11-05
    adopted_prs[1]{repo,number,title,reason,status}:
      RDM-waterbutler,101,"Python 3.13, dependency update, multi-stage image (WIP)","vulnerability remediation (M4)",adopted
    candidate_prs[1]{repo,number,title,reason,status}:
      RDM-waterbutler,93,"S3 SigV4",feature,candidate
    base_image: python:3.6-slim-buster
    base_image_digest: null
    target_image:
      M4: "python:3.13-slim multi-stage, non-root"
      M5: null
    profile: core
    platforms[2]: linux/arm64,linux/amd64
    note: null
```

上の全部ゼロの SHA は例のための仮の値です。本物のマニフェストには現れません。このブロックは説明のための例であって `manifest/upstreams.json` の写しではないので、`<!-- canonical: ... -->` の宣言は付けません（[SPEC-06 §4](06_documentation_conventions.md#4-図とデータ)）。マニフェストを写すブロック（たとえば [SPEC-00 §2](00_overview.md#japanese)）には宣言を付けます。

### 4. 規則

1. **SHA を固定する。** すべての `upstreams[].sha` は、`fetched_at` の時点でそのブランチに実在する 40 文字のコミットです。ブランチ（リポジトリの中の別の作業の道。[REF-01](../reference/REF-01_Glossary.md)）名だけでは足りません。
2. **マニフェストの変更は PR で行う。** `develop` 上の `upstreams.json` を直接編集する人はいません。SHA が進む通常の経路は週次の統合 PR（[SPEC-05 §3](05_upstream_tracking.md#3-週次の統合-pr)）です。PR の採用・却下もマニフェストの PR で、`reason` を書きます。
3. **統合の順番は固定:** `status: merged` の `public` の上流をマージ、次に `private` の上流をマージ、最後に `adopted_prs` を並び順に適用。`public` の上流がない部品（非公開サブシステム）は `private` の上流から始めます。`cos` の上流（`status: reference`）はマージせず、比較だけに使います。
4. **「矛盾なく」とは次のすべてを満たすこと:**
   - 同じ上流リポジトリの同じブランチについて、二つの部品が異なる SHA を参照していない。
   - すべての `adopted_prs[]` が、固定した上流から組んだ統合ブランチにきれいに（衝突なく）当たる。
   - `upstreams.toon` が、`grdm-dev manifest toon` が `upstreams.json` から出す結果と 1 バイトも違わない。
   - 名前を書いた `integration_repo` がすべて存在し、`develop` と、`upstreams[]` の各要素につき一本の追跡ブランチ（名前はその `tracking_branch` と完全に同じ）を持つ。
5. **名前だけを書く。** `repo` と `integration_repo` は裸の名前（`RDM-osf.io-dev2027`）です。`http` や `git@` で始まる値、`github.com` を含む値は不正です。
6. **決まっていない上流は `status: candidate` で載せる。** 追跡ブランチにはミラーするが、マージはしない。例: `RDM-osf.io-private`（ブランチ `fix/sec-test`、追跡ブランチ `upstream/private-sec-test-fix-sec-test`）は所有者が決めるまで候補です（計画書 §7）。
7. **追跡ブランチの名前は一つの規則で決める:** `upstream/<kind>-<branch>`。`<branch>` は上流のブランチ名の `/` をすべて `-` に置き換えたもの。一つの部品に同じ `kind` の上流が二つあるときは、二つ目は kind の後ろに短いタグを挟む: `upstream/<kind>-<tag>-<branch>`。例: `RDM-ember-osf-web`（`master`）→ `upstream/public-master`、`RDM-ember-osf-web-master-private` → `upstream/private-master`、`RDM-OASys-main-private` → `upstream/private-main`、`CenterForOpenScience/osf.io` → `upstream/cos-develop`、`RDM-osf.io-private`（`fix/sec-test`）→ `upstream/private-sec-test-fix-sec-test`。同じ規則を [SPEC-05 §1](05_upstream_tracking.md#japanese) と [ADR-01 §3](../decisions/ADR-01_Integration_Repository_Placement.md#japanese) にも書いています。

### 5. 検査: `grdm-dev manifest check`

リポジトリのルートで実行します。終了コード `0` が合格。不合格なら指摘ごとに一行出して `20`（manifest が不正。[SPEC-02 §6](02_installer_cli.md#japanese)）で終わります。

```sh
grdm-dev manifest check
```

検査は次の順で行います。

```toon
checks[16]{id,rule,severity}:
  MC-01,"upstreams.json が JSON として読め、schema_version 1 の形に合う",error
  MC-02,"部品の id が重複せず ^[A-Za-z0-9_.-]+$ に合う",error
  MC-03,"role が core|infra|subsystem のいずれか。services が空でない配列",error
  MC-04,"integration_repo が ^RDM-[A-Za-z0-9_.-]+-dev2027$ に合う。infra は null",error
  MC-05,"integration_branch が develop。infra は null",error
  MC-06,"sha が ^[0-9a-f]{40}$ に合う。base_image_digest は null か sha256:<16 進 64 文字>。fetched_at が未来でない ISO 日付。prebuilt_image があるときは name@sha256:<16 進 64 文字> で、空でない note を伴い、URL や非公開リポジトリの参照でなく、infra に無い",error
  MC-07,"どの値にも http、git@、github.com、トークンらしい文字列が含まれない",error
  MC-08,"同じ (repo, branch) の組は全部品で一つの sha",error
  MC-09,"adopted_prs の status は adopted。candidate_prs は candidate|rejected。upstreams の status は merged|reference|candidate で cos は reference。number は正の整数",error
  MC-10,"profile と platforms が許された値だけ。core の部品は両 platform を持つ",error
  MC-11,"upstreams.toon が grdm-dev manifest toon の出力と一致",error
  MC-12,"--remote 付き: 各 integration_repo が develop と列挙した全 tracking_branch を持ち、各 sha がその tracking_branch から到達できる",error
  MC-13,"すべての tracking_branch が規則 7（upstream/<kind>[-<tag>]-<branch の / を - に置換>）に合う",error
  MC-14,"overlay_of があるときは、存在して infra でもオーバーレイでも prebuilt でもない部品を指す。オーバーレイ自身は infra でなく prebuilt_image を持たない。ベース一つにオーバーレイは一つ（サービスが一回限りであることはインストーラーがテンプレートで検査）",error
  MC-15,"image_build {context, tag} は infra だけ。context は Dockerfile を含むリポジトリ相対のディレクトリ、tag は有効なイメージタグ、note 必須、prebuilt_image・build_platform と併用不可（ADR-07）",error
  MC-16,"build_dockerfile は integration_repo があるときだけ。本リポジトリ内のファイルを指すリポジトリ相対パス、note 必須、prebuilt_image・overlay_of と併用不可",error
```

`--remote` はネットワークと認証情報が要るので、公開であるこのリポジトリの CI ではなく、非公開の `-dev2027` 側の CI で実行します。[SPEC-06 §8](06_documentation_conventions.md#8-検査) の文書検査は、文書内に引用した TOON ブロックに MC-11 を使い回します。

### 6. 誰が変えるか

| 変更 | 起票 | レビュー | マージ |
|---|---|---|---|
| 週次の SHA 前進 | AID エージェント（週次ジョブ。[SPEC-05](05_upstream_tracking.md)） | REV（Codex Astra）。検査は QAE（Claude Code Fable） | 所有者 |
| PR の採用・却下 | AID または QAE。`reason` 付き | REV | 所有者 |
| `target_image` の変更 | QAE。節目の計画を参照 | REV | 所有者 |

---

## Glossary / 用語

| Term | English note | 日本語注 |
|---|---|---|
| Manifest | A packing list that says exactly what goes into the build. | ビルドに何が入るかを正確に書いた明細書。 |
| Upstream | The original repository we copy code from. | コードを写してくる元のリポジトリ。 |
| SHA | The 40-character fingerprint that names one commit. | 一つのコミットを指す 40 文字の指紋。 |
| Pull request (PR) | A proposed change waiting to be reviewed and merged. | レビューとマージを待つ変更の提案。 |
| Schema | The agreed shape of a data file: which fields, which types. | データファイルの決まった形。どの項目がどの型か。 |
| Profile | A named set of components the installer starts together. | インストーラーがまとめて起動する部品の組に付けた名前。 |
| Token | A secret string that proves who you are to a computer. | コンピュータに「自分は誰か」を示す秘密の文字列。 |
