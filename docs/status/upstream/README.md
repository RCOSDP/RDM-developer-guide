# Upstream Tracking Status / 上流追従状況

> **Summary:** Daily mirror and diff reports: `latest.toon`/`latest.json` are overwritten every day, and archives older than 90 days are deleted. These records show which upstreams changed and whether integration is needed.
> **概要:** 日次ミラーと差分報告：`latest.toon`/`latest.json` は毎日上書きされ、90 日より古い保管分は削除されます。これらの記録はどの上流が変更されたか、統合が必要かどうかを示します。

**Jump:** [English](#english) · [日本語](#japanese)

- Version / 版: 0.3 — 2026-11-06. **Learned:** once `grdm-dev upstream mirror` existed, the report needed more than the SHA per branch: the previous SHA, the source name, whether `develop` already contains the tip, and a per-row status, or a refused (non-fast-forward) fetch would be indistinguishable from an unchanged branch. ／ `grdm-dev upstream mirror` ができると、報告にはブランチごとの SHA だけでは足りないと分かった。前回の SHA、元の名前、`develop` が先端を既に含むか、行ごとの状態が無いと、拒まれた（non-fast-forward の）fetch と変化なしのブランチが見分けられない。
- Version / 版: 0.2 — 2026-11-05. **Learned:** an example data block must itself parse: a declared row count with an ellipsis in place of rows is a syntax error, not an example. ／ 例として置くデータブロックもそれ自体が解析できなければならない。行数を宣言して省略記号を置いたものは例ではなく構文エラーだと分かった。
- Version / 版: 0.1 — 2026-11-05. **Learned:** the daily job's outputs need a fixed place and a fixed name before the job exists, or SPEC-05 and the status board would point at nothing. The files named here do not exist yet; the daily job (SPEC-05) will create them. ／ 日次ジョブの出力には、ジョブが存在する前から置き場と名前を決めておく必要があると分かった。さもないと SPEC-05 と進捗ボードの参照先が無くなる。ここに書いたファイルはまだ存在せず、日次ジョブ（SPEC-05）が作る。
- Normative for: [SPEC-05 Upstream Tracking](../../spec/05_upstream_tracking.md).
- Related: [../README.md](../README.md) · [status/README.md](../README.md) · [spec/05_upstream_tracking.md#2-daily-job-mirror-and-diff-report](../../spec/05_upstream_tracking.md#english)

---

<a id="english"></a>
## English

[→ 日本語版へ](#japanese)

### 1. Files written by the daily job

The `upstream-mirror` workflow (or `grdm-dev upstream mirror`, default `--report-dir docs/status/upstream`) writes:

| File | Behavior |
|---|---|
| `latest.json` | Overwritten every run; canonical JSON of the daily report. |
| `latest.toon` | Overwritten every run; the same report in TOON. |
| `archive/YYYY-MM-DD.json`, `archive/YYYY-MM-DD.toon` | One copy per run date; same content as `latest.*`. |

> **Note:** Archives older than 90 days are deleted by the daily job; the run report lists them under `archives_pruned`. Files in `archive/` whose name is not a date are left alone.

> **Warning:** The files are public. They contain repository names, branch names, SHAs, and commit counts only — never an address, a commit message, an author, or a file path. The tests of `grdm-dev upstream` assert this.

### 2. Report structure

The report format is defined in [SPEC-05 §2](../../spec/05_upstream_tracking.md#english); one repository is shown (a real report lists all eleven, `repositories[11]`), and the repeated digits stand for real SHAs:

```toon
report:
  generated_at: "2026-11-06T03:00:12+09:00"
  dry_run: false
  repositories[1]:
    - component: osf.io
      integration_repo: RDM-osf.io-dev2027
      develop_sha: 1111111111111111111111111111111111111111
      upstreams[3]{branch,kind,source_repo,source_branch,previous_sha,sha,ahead_of_develop,behind_develop,develop_contains,manifest_sha_matches,moved_since_yesterday,status}:
        upstream/public-develop,public,RDM-osf.io,develop,2222222222222222222222222222222222222222,3333333333333333333333333333333333333333,14,0,false,false,true,updated
        upstream/private-develop,private,RDM-osf.io-develop-private,develop,4444444444444444444444444444444444444444,4444444444444444444444444444444444444444,0,0,true,true,false,unchanged
        upstream/cos-develop,cos,CenterForOpenScience/osf.io,develop,5555555555555555555555555555555555555555,6666666666666666666666666666666666666666,310,0,false,false,true,updated
      pushed[2]:
        - upstream/public-develop
        - upstream/cos-develop
      action: integrate
      errors[0]:
  summary:
    repositories: 1
    repositories_needing_integration: 1
    force_push_detected: 0
    branches_moved: 2
    branches_pushed: 2
    errors: 0
```

Per upstream row, `status` is:

| Value | Meaning |
|---|---|
| `created` | The integration repository had no such tracking branch yet; it was created from the source. |
| `updated` | Fast-forwarded to a newer source commit. |
| `unchanged` | The source tip equals the mirrored one. |
| `non-fast-forward` | The source is not a descendant of the mirrored branch (force push upstream); the old branch is kept. |
| `fetch-failed` | The source could not be fetched. |

Per repository, `action` is:

| Value | Meaning |
|---|---|
| `integrate` | A merged `public` or `private` upstream is ahead of `develop`; open an integration PR. |
| `none` | Nothing ahead of `develop`; no action needed. |
| `halt` | A `non-fast-forward` row exists; stop and investigate before anything is merged. |
| `error` | A fetch or push failed and nothing is ahead of `develop`. |

### 3. Open items (no entries yet / まだありません)

| Date | Repository | Action |
|---|---|---|
| — | — | — |

---

<a id="japanese"></a>
## 日本語

[→ To English](#english)

### 1. 日次ジョブが書くファイル

`upstream-mirror` ワークフロー（または `grdm-dev upstream mirror`。既定は `--report-dir docs/status/upstream`）が次を書きます：

| ファイル | 振る舞い |
|---|---|
| `latest.json` | 毎回上書きされる。日次報告の正本 JSON。 |
| `latest.toon` | 毎回上書きされる。同じ報告の TOON。 |
| `archive/YYYY-MM-DD.json`、`archive/YYYY-MM-DD.toon` | 実行日ごとに一組。`latest.*` と同じ内容。 |

> **Note:** 90 日より古い保管分は日次ジョブが削除し、実行時の報告の `archives_pruned` に列挙します。`archive/` の中で名前が日付でないファイルには触れません。

> **Warning:** ファイルは公開です。中身はリポジトリ名、ブランチ名、SHA、コミット数だけで、アドレス、コミットメッセージ、作者、ファイルパスは決して含めません。`grdm-dev upstream` のテストがこれを確認します。

### 2. 報告の構造

報告形式は [SPEC-05 §2](../../spec/05_upstream_tracking.md#japanese) に定められています。例はリポジトリ 1 本だけ（本物の報告は 11 本すべて、`repositories[11]`）で、同じ数字の並びは本物の SHA の代わりです：

```toon
report:
  generated_at: "2026-11-06T03:00:12+09:00"
  dry_run: false
  repositories[1]:
    - component: osf.io
      integration_repo: RDM-osf.io-dev2027
      develop_sha: 1111111111111111111111111111111111111111
      upstreams[3]{branch,kind,source_repo,source_branch,previous_sha,sha,ahead_of_develop,behind_develop,develop_contains,manifest_sha_matches,moved_since_yesterday,status}:
        upstream/public-develop,public,RDM-osf.io,develop,2222222222222222222222222222222222222222,3333333333333333333333333333333333333333,14,0,false,false,true,updated
        upstream/private-develop,private,RDM-osf.io-develop-private,develop,4444444444444444444444444444444444444444,4444444444444444444444444444444444444444,0,0,true,true,false,unchanged
        upstream/cos-develop,cos,CenterForOpenScience/osf.io,develop,5555555555555555555555555555555555555555,6666666666666666666666666666666666666666,310,0,false,false,true,updated
      pushed[2]:
        - upstream/public-develop
        - upstream/cos-develop
      action: integrate
      errors[0]:
  summary:
    repositories: 1
    repositories_needing_integration: 1
    force_push_detected: 0
    branches_moved: 2
    branches_pushed: 2
    errors: 0
```

上流の行ごとの `status`：

| 値 | 意味 |
|---|---|
| `created` | 統合リポジトリにまだその追跡ブランチが無く、元から作った。 |
| `updated` | 元の新しいコミットへ fast-forward した。 |
| `unchanged` | 元の先端がミラー済みのものと同じ。 |
| `non-fast-forward` | 元がミラー済みブランチの子孫でない（上流で force push）。古いブランチを残す。 |
| `fetch-failed` | 元を取得できなかった。 |

リポジトリごとの `action`：

| 値 | 意味 |
|---|---|
| `integrate` | `merged` の `public` か `private` の上流が `develop` より進んでいる。統合 PR を開く。 |
| `none` | `develop` より進んだものがない。何もする必要なし。 |
| `halt` | `non-fast-forward` の行がある。何かをマージする前に停止して調査する。 |
| `error` | fetch か push が失敗し、`develop` より進んだものはない。 |

### 3. 未解決項目（まだありません / no entries yet）

| 日付 | リポジトリ | アクション |
|---|---|---|
| — | — | — |

---

## Glossary / 用語

| Term | English note | 日本語注 |
|---|---|---|
| Mirror | A copy that is kept identical to the original. | 元と同じ中身に保たれる写し。 |
| Diff report | A record of changes between branches. | ブランチ間の変更記録。 |
| Fast-forward | Moving a branch straight ahead to a newer commit without creating a merge. | マージを作らずにブランチを新しいコミットへまっすぐ進めること。 |
| Force-push | Overwriting a branch's history on the server. Forbidden here. | サーバ上のブランチの履歴を上書きすること。ここでは禁止。 |
| Archive | Old reports kept for reference, deleted after 90 days. | 参照のために保管する古い報告。90 日後に削除される。 |
| Action | The decision on whether to open an integration PR. | 統合 PR を開くかどうかの判断。 |
