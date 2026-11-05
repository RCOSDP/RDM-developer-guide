# Upstream Tracking Status / 上流追従状況

> **Summary:** Daily mirror and diff reports: `latest.toon`/`latest.json` are overwritten every day, and archives older than 90 days are deleted. These records show which upstreams changed and whether integration is needed.
> **概要:** 日次ミラーと差分報告：`latest.toon`/`latest.json` は毎日上書きされ、90 日より古い保管分は削除されます。これらの記録はどの上流が変更されたか、統合が必要かどうかを示します。

**Jump:** [English](#english) · [日本語](#japanese)

- Version / 版: 0.2 — 2026-11-05. **Learned:** an example data block must itself parse: a declared row count with an ellipsis in place of rows is a syntax error, not an example. ／ 例として置くデータブロックもそれ自体が解析できなければならない。行数を宣言して省略記号を置いたものは例ではなく構文エラーだと分かった。
- Version / 版: 0.1 — 2026-11-05. **Learned:** the daily job's outputs need a fixed place and a fixed name before the job exists, or SPEC-05 and the status board would point at nothing. The files named here do not exist yet; the daily job (SPEC-05) will create them. ／ 日次ジョブの出力には、ジョブが存在する前から置き場と名前を決めておく必要があると分かった。さもないと SPEC-05 と進捗ボードの参照先が無くなる。ここに書いたファイルはまだ存在せず、日次ジョブ（SPEC-05）が作る。
- Normative for: [SPEC-05 Upstream Tracking](../../spec/05_upstream_tracking.md).
- Related: [../README.md](../README.md) · [status/README.md](../README.md) · [spec/05_upstream_tracking.md#2-daily-job-mirror-and-diff-report](../../spec/05_upstream_tracking.md#english)

---

<a id="english"></a>
## English

[→ 日本語版へ](#japanese)

### 1. Files written by the daily job

The `upstream-mirror` workflow (or `grdm-dev upstream mirror`) writes:

| File | Behavior |
|---|---|
| `latest.toon` | Overwritten every day; TOON excerpt of the daily report. |
| `latest.json` | Overwritten every day; canonical JSON of the daily report. |
| `archive/` | Subdirectory with daily reports dated `YYYY-MM-DD.toon` and `.json`. |

> **Note:** Archives older than 90 days are deleted by the daily job to keep storage reasonable.

### 2. Report structure

The report format is defined in [SPEC-05 §2](../../spec/05_upstream_tracking.md):

```toon
report:
  generated_at: 2026-11-05T03:00:12+09:00
  repositories[1]:
    - integration_repo: RDM-osf.io-dev2027
      develop_sha: 1111111111111111111111111111111111111111
      upstreams[3]{branch,kind,sha,ahead_of_develop,behind_develop,manifest_sha_matches,moved_since_yesterday}:
        upstream/public-develop,public,2222222222222222222222222222222222222222,14,0,false,true
        upstream/private-develop,private,3333333333333333333333333333333333333333,0,0,true,false
        upstream/cos-develop,cos,4444444444444444444444444444444444444444,310,0,true,true
      action: integrate
  summary:
    repositories_needing_integration: 1
    force_push_detected: 0
```

The example shows one of the eleven integration repositories; a real report lists all eleven (`repositories[11]`), and the repeated digits stand for real SHAs.

The `action` field is:

| Value | Meaning |
|---|---|
| `integrate` | Any merged upstream is ahead of develop; open an integration PR. |
| `none` | No changes since yesterday; no action needed. |
| `halt` | Force-push detected on an upstream branch; stop and investigate. |

### 3. Open items (no entries yet / まだありません)

| Date | Repository | Action |
|---|---|---|
| — | — | — |

---

<a id="japanese"></a>
## 日本語

[→ To English](#english)

### 1. 日次ジョブが書くファイル

`upstream-mirror` ワークフロー（または `grdm-dev upstream mirror`）が次を書きます：

| ファイル | 振る舞い |
|---|---|
| `latest.toon` | 毎日上書きされる。日次報告の TOON 抄録。 |
| `latest.json` | 毎日上書きされる。日次報告の正本 JSON。 |
| `archive/` | 日付付きの日次報告 `YYYY-MM-DD.toon` と `.json` のサブディレクトリ。 |

> **Note:** 90 日より古い保管分は、ストレージを適切に保つため日次ジョブが削除します。

### 2. 報告の構造

報告形式は [SPEC-05 §2](../../spec/05_upstream_tracking.md) に定められています：

```toon
report:
  generated_at: 2026-11-05T03:00:12+09:00
  repositories[1]:
    - integration_repo: RDM-osf.io-dev2027
      develop_sha: 1111111111111111111111111111111111111111
      upstreams[3]{branch,kind,sha,ahead_of_develop,behind_develop,manifest_sha_matches,moved_since_yesterday}:
        upstream/public-develop,public,2222222222222222222222222222222222222222,14,0,false,true
        upstream/private-develop,private,3333333333333333333333333333333333333333,0,0,true,false
        upstream/cos-develop,cos,4444444444444444444444444444444444444444,310,0,true,true
      action: integrate
  summary:
    repositories_needing_integration: 1
    force_push_detected: 0
```

例は統合リポジトリ 11 本のうち 1 本だけを示しています。本物の報告は 11 本すべてを載せ（`repositories[11]`）、同じ数字の並びは本物の SHA の代わりです。

`action` フィールドは：

| 値 | 意味 |
|---|---|
| `integrate` | マージ対象の上流のどれかが develop より進んでいる。統合 PR を開く。 |
| `none` | 昨日からの変更なし。何もする必要なし。 |
| `halt` | 上流ブランチで force-push を検出。停止して調査する。 |

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
