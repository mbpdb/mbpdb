# Reference examples — not linked to the app

**Nothing in this directory is served or referenced by the application.**
`peptide/templates/peptide/data_transformation.html` and
`peptide/templates/peptide/data_analysis.html` only link to files in the
parent `static/peptide/examples/` directory (the "Download example
file"/"Load example" buttons). Everything here is a reference/provenance
archive only — real, unmodified engine exports and prior versions of the
shipped example dataset, kept for documentation and to exercise the
Data Transformation loader's column-mapping in tests
(`peptide/data_transformation/services/data_loader.py`:
`get_comprehensive_column_mapping`, `extract_protein_id`,
`strip_inline_modifications`, `detect_long_format`, `pivot_long_to_wide`; and
`peptide/data_transformation/services/data_combiner.py`:
`create_unique_id`, `_collapse_multiprotein_duplicate_rows`).

All five per-engine files below are covered end-to-end by
`tests/test_data_transformation.py` (`TestRealData_MaxQuant`,
`TestRealData_SkylineExample`, `TestRealData_PepexInput`,
`TestRealData_PeaksLongFormat`, `TestRealData_SpectronautLongFormat`) — each
is loaded, run through `get_filtered_columns` to detect abundance/sample
columns, and pushed through the full `data_combiner.process_data` pipeline
to confirm the merged output matches the same core schema as the shipped
`../example_merged_dataframe.csv` reference (one row per `Unique Peptide
ID`, with `Sequence`/`Protein`/`protein_species`/`protein_name` present and,
once grouped, `Avg_*` columns).

## Per-engine format examples

| File | Software | Peptide column | Protein column | Layout | Verified (rows in → rows out) |
|---|---|---|---|---|---|
| `max_quant.csv` | **MaxQuant** | `Sequence` | `Proteins` (`sp\|ACC\|NAME`) | wide; separate `Start/End position` cols | 25 → 25 |
| `Skyline example.csv` | **Skyline** | `Peptide` / `Peptide Modified Sequence` | `Protein` (`sp\|ACC\|NAME`) | wide (one `… Normalized Area` column per sample); **one row per (peptide, protein) pair** | 13,078 → 11,989 (multi-protein rows collapsed) |
| `PEPEX_input.tsv` | **Skyline-based ("PepEx")** | `Peptide` / `Peptide Modified Sequence` | `Protein` (`sp\|ACC\|NAME`) | wide (one `… Total Area` column per sample) | 993 → 993 |
| `PEAKS_example.csv` | **PEAKS** | `Peptide` (inline mods, e.g. `PEP(+57.02)TIDE`) | `Accession` (`ACC\|NAME` pairs) | long / per-PSM → **auto-pivoted** | 3,900 PSM rows → 684 peptides × 8 samples |
| `spectronaut.tsv` | **Spectronaut** | `PEP.StrippedSequence` / `EG.ModifiedPeptide` | `PG.ProteinGroups` | long (one row per precursor × run) → **auto-pivoted** | 8,760 rows → 954 peptides × 8 samples |

These five previously lived in `notebooks/examples/additional_peptidomic_input_formats/`
(gitignored, dev-only) — PEAKS and Spectronaut under a further
`needs_transformation/` subfolder, because the app could not yet ingest their
long/per-run layout at all. As of 2026-08-06 the loader auto-pivots that
layout (see "Format quirks" below); the whole set has since been relocated
here so it's tracked in git rather than dev-local, while staying explicitly
unlinked from the app per the note at the top of this file.

### Format quirks the loader handles

- **UniProt pipe accessions** `sp|P02666|CASB_BOVIN` (3-part) → `P02666`.
- **PEAKS 2-part** `A0A087WWV8|A0A087WWV8_HUMAN` → accession `A0A087WWV8`
  (the accession is the *first* field here, unlike UniProt's 3-part form).
- **Multi-protein cells** are split on `;`, `/`, and `,` (Proteome Discoverer,
  MaxQuant, PEAKS, and Spectronaut all use one of these).
- **Multi-protein *rows*** — Skyline reports a peptide mapped to several
  proteins as separate rows with otherwise-identical data (same abundances
  repeated per row) rather than one row with a joined protein list.
  `_collapse_multiprotein_duplicate_rows` merges these back into one row per
  peptide (proteins joined `'; '`-separated) once every other column in the
  group is confirmed identical — 1,089 of `Skyline example.csv`'s 13,078 rows
  are this kind of duplicate.
- **Inline modifications** embedded in the peptide string — PEAKS `(+57.02)`,
  bracketed `[DN]`, or enzymatic flanks `K.PEPTIDE.R` — are stripped so the
  sequence stays a clean amino-acid string for BLAST / exact matching.
- **Long/per-run layout** (PEAKS, Spectronaut) — a row per peptide per run
  rather than one abundance column per sample is detected (`Source File` /
  `R.FileName` + a single quantity column like `Area` /
  `EG.TotalQuantity (Settings)`) and pivoted to the peptide × sample matrix
  automatically; see `detect_long_format`/`pivot_long_to_wide`.

## Case-study provenance / legacy files

These are not format-compatibility examples — they document the history of
the case-study dataset that ships as `../example_peptidomic_data.csv` /
`../example_merged_dataframe.csv`.

| File | What it is |
|---|---|
| `Kuhfeld_Bitter_Peptide_Reprocess-(1)_PeptideGroups.txt` | The raw, unmodified Proteome Discoverer export of the case-study bitter-peptide dataset — the actual source file `../example_peptidomic_data.csv` was derived from. Real tab-delimited PD "PeptideGroups" export, original column names and quoting intact. |
| `example_peptidomic_data - original.csv` | The *previous* version of the shipped `../example_peptidomic_data.csv`, from before it was replaced with the raw PD export above. Abundance columns had already been renamed to short study-variable codes (`E_7_2`, `L_3_3`, …) before upload — the manual reformatting step the current example specifically avoids. Kept for reference only. |
| `merged_dataframe_splitA1A2.csv` + `protein_mapping_key_splitA1A2.json` | An alternate worked example of the Data Transformation output, generated with the β-casein A1/A2 variants (and a few other multi-accession groups) explicitly kept **split** (protein-mapping decision `"action": "SPLIT"`) rather than merged into one canonical protein — contrast with the shipped `../example_merged_dataframe.csv`, which merges them. Demonstrates the other branch of the Merge/Rename Protein Sources control (Data Transformation Step 3). |

## Provenance

The file layouts above are verified from the example exports themselves. The exact
repository or publication source has **not yet been conclusively identified** for
most third-party examples. Internet searches found strong evidence for the file
formats, but not enough to assign a DOI without risk of misattribution.

| File | Format status | Current provenance assessment |
|---|---|---|
| `max_quant.csv` | Verified | Representative MaxQuant peptide export from a yeast example dataset; exact repository/publication unknown. |
| `Skyline example.csv` | Verified | Standard Skyline report containing Normalized Area columns from a human cohort example; exact repository/publication unknown. |
| `PEPEX_input.tsv` | Verified | Appears to be the lab's own Skyline-based "PepEx" pipeline export (Library Name `PeptidesInHumanMilk`); not a third-party file. |
| `PEAKS_example.csv` | Verified | Standard PEAKS peptide export from an immunopeptidomics/MAPPs-style example; column set (`-10lgP`, `1/k0 Range`) matches PEAKS's own documented naming (bioinfor.com), consistent with a timsTOF PASEF run; exact source unknown. |
| `spectronaut.tsv` | Verified | Standard Spectronaut DIA "Normal Report" using HYE mix conditions; `R./PG./PEP./EG./FG.` prefix convention matches Spectronaut's documented schema (used by third-party tools SpectroPipeR, MSstats, alphastats); exact source unknown. |
| `Kuhfeld_Bitter_Peptide_Reprocess-(1)_PeptideGroups.txt` | Own data | Lab's own Proteome Discoverer export from the case-study dataset. |
| `example_peptidomic_data - original.csv` | Own data | Derived from the lab's own case-study dataset; kept as a legacy reference only. |
| `merged_dataframe_splitA1A2.csv` / `protein_mapping_key_splitA1A2.json` | Own data | Generated from the lab's own case-study dataset via the app's own export. |

### Literature and repository search status

- **Spectronaut:** Format closely matches Spectronaut tutorial/benchmark reports used by downstream tools such as SpectroPipeR and protti.
- **Skyline:** Column layout matches Skyline report exports, but the sample identifiers (AD/HC/PDD/PD-noMCI) did not uniquely identify a Panorama Public project.
- **MaxQuant:** Column layout matches canonical MaxQuant peptide exports used by many software packages; no unique originating repository identified.
- **PEAKS:** Column layout and metadata are consistent with immunopeptidomics/MAPPs workflows, but no unique publication or repository could be verified.

Until the original download locations are identified, the third-party files
above should be described as **format examples** rather than cited as
originating from specific publications.
