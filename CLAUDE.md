# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

TorTech is a single-page Streamlit app that displays a filterable database of top Toronto-based tech companies. Live at https://tortech.streamlit.app/.

## Commands

```bash
# Install dependencies (creates .venv from pyproject.toml + uv.lock)
uv sync

# Run the app locally
uv run streamlit run streamlit_app.py
```

Dependencies are managed with **uv**: `pyproject.toml` declares the direct deps, `uv.lock` pins the full resolved tree. Add a dependency with `uv add <pkg>`. There is no `requirements.txt`.

`LOG_LEVEL` (default `INFO`) is read via `python-decouple` from environment or a `.env` file.

There is no build step, test suite, or linter configured.

## Architecture

The entire app is `streamlit_app.py` (~130 lines). Data lives in `data/tortech_database.csv` — there is no database despite the name; the CSV *is* the database.

Key flow in `streamlit_app.py`:
1. Loads the CSV into a pandas DataFrame, renaming `LinkedIn URL`→`LinkedIn` and `Company URL`→`Website`.
2. Derives sortable numeric columns from string fields: `Followers` (e.g. `"790k"` → `790.0`) and two employee-count columns parsed from the `Employees` range string (e.g. `"10k+"`). `max_employees_for_sorting` expands `k`→`000` for correct numeric sort order; `max_employees` keeps the raw number.
3. Builds sidebar `multiselect` filters for `Employees` and `Tags`. Tag options are ranked by frequency across all rows (`Tags` is a comma-space–separated string per company). Both filters use a `'Select All'` sentinel as the default/no-filter state.
4. Sorts by `Followers` then `max_employees` descending and renders via `st.dataframe` with custom `column_config` (progress bar for followers, link columns for LinkedIn/Website using regex `display_text`).

## The data file

All data lives in `data/tortech_database.csv` (the CSV *is* the database). Columns:
`Company, LinkedIn URL, Company URL, Employees, Followers, Tags, Short Description, Long Description,` + a trailing empty 9th column (every row ends with a comma).

Format rules — the parser in `streamlit_app.py` is brittle; violating these crashes the app on load:
- **`Followers`**: a number followed by lowercase `k` (e.g. `8k`, `277k`, `1086k`). Required. `.str.replace('k','').astype(float)` will fail if the `k` is missing or the cell is non-numeric. Round to the nearest thousand; values under 1000 → `1k`.
- **`Employees`**: a LinkedIn company-size bucket whose last `-`-delimited segment is a number, optionally with `k` or `+`: `2-10`, `11-50`, `51-200`, `201-500`, `501-1k`, `1k-5k`, `5k-10k`, `10k+`.
- **`Tags`**: comma-**space** separated (`Finance, AI`). The code splits on `", "`, so a comma with no space (`Finance,AI`) becomes one broken tag and won't filter correctly. (Some legacy rows still have this; new rows should use `, `.)
- `LinkedIn URL` → `https://linkedin.com/company/<slug>/`; `Company URL` → `https://<domain>/`.

**The CSV is NOT one-line-per-row.** Long Description fields contain embedded newlines inside their quotes, so a single company spans multiple physical lines. Do not edit by physical line number or split on `\n`. To edit safely either:
- anchor on the company's unique `LinkedIn URL` (e.g. a regex that rewrites the `,<Employees>,<Followers>,` that follows it), or
- round-trip with Python's `csv` module (`QUOTE_MINIMAL` matches the existing style; write `""` for the trailing 9th field).

After any edit, verify the app's parse pipeline succeeds:
```bash
uv run python -c "
import pandas as pd
df = pd.read_csv('./data/tortech_database.csv').rename(columns={'LinkedIn URL':'LinkedIn','Company URL':'Website'})
df['Followers'].str.replace('k','').astype(float)
[int(x.split('-')[-1].replace('k','000').replace('+','')) for x in df['Employees']]
[t.split(', ') for t in df['Tags']]
print('rows:', len(df), '- parses OK')
"
```

## Updating / adding company data

The CSV fields map directly to a company's **LinkedIn company page header**: `Followers`, the `Employees` size bucket, and the tagline (→ `Short Description`). That page is the source of truth.

How to gather it accurately (lessons learned doing this at scale):
- **Fetch the live LinkedIn page; do NOT trust search-result snippets.** WebFetch on `https://linkedin.com/company/<slug>/` (and the `https://ca.linkedin.com/company/<slug>/` mirror) returns the live header. Search snippets are cached and almost always **stale/undercounted** — they were wrong (usually too low, sometimes by 2-3×) for the large majority of companies. Fetch both mirror URLs and confirm they agree.
- **One research agent per company, run in parallel.** Batching several companies into one agent produced a wrong figure; per-company agents that each fetch + cross-check are reliable. Have each return structured JSON (`followers`, `followers_exact`, `employees` bucket, `tagline`, `confidence`, `source_note`).
- **Round followers to the nearest thousand** and append `k`. Normalize `Employees` to one of the buckets above.
- Watch for: **name collisions** (multiple companies share a name, e.g. several "Lumi"/"Ideogram" — confirm the slug), **rebrands/redirects** (e.g. `/floatcard` 301-redirects to `/floatfinancial`), and **defunct companies** (e.g. Untether AI wound down in 2025 though its page persists) — flag these rather than silently trusting the page.
- The follower/employee numbers drift constantly, so treat any snapshot as point-in-time and re-verify when revisiting.

To add a new company, append a row with all 9 fields (trailing empty column) using the `csv` module for correct quoting, then run the verification snippet above.
