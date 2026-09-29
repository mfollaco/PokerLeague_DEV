LEGACY 1 FILE OUTPUT INSTRUCTIONS

Drop weekly log CSVs here.
Naming: mm.dd.yy log.csv
Example: 02.21.26 log.csv

NEW 2 FILE OUTPUT INSTRUCTIONS

# Fall 2026 Weekly Import Instructions

## Where to Put Weekly Files

In GitHub, go to:

`data/seasons/fall_2026/incoming/`

Weeks 1 and 2 used the old single-file format and should remain directly in that folder.

Starting with Week 3, create a NEW subfolder inside `incoming` using the tournament date in `mm.dd.yy` format.

Example structure:

```text
data/seasons/fall_2026/incoming/
├── 09.08.26 log.csv
├── 09.15.26 log.csv
└── 09.29.26/
    ├── players.csv
    └── log.csv
```

## Weeks 3 and Later

For each weekly tournament:

1. Go to `data/seasons/fall_2026/incoming/` in GitHub.
2. Create a folder named with the tournament date:
   `mm.dd.yy`
3. Inside that dated folder, upload the TWO files exported by the poker app:
   - `players.csv`
   - `log.csv`

Both files must come from the SAME tournament export.

### Important

- Do **not** rename `players.csv`.
- Do **not** rename `log.csv`.
- Do **not** combine the two files.
- Do **not** edit the Points column in `players.csv`.
- Do **not** edit the Payout column in `players.csv`.
- The website calculates official league points and payouts using its own rules.
- If the app exports `Sean`, leave it as `Sean`. The importer maps him to `Sean N`.
- Players who did not participate that week should simply be absent from the weekly export. They remain on the season roster.

## Weeks 1 and 2

Weeks 1 and 2 used the legacy single-file format:

`mm.dd.yy log.csv`

Those files should remain unchanged and directly inside:

`data/seasons/fall_2026/incoming/`

## Weekly Process

1. Export the tournament from the poker app.
2. In GitHub, open `data/seasons/fall_2026/incoming/`.
3. Create the dated folder using `mm.dd.yy`.
4. Upload `players.csv` and `log.csv` into that dated folder.
5. Confirm both files are from the same tournament.
6. Run the normal Fall 2026 import/build process.
7. Review the results before publishing.
