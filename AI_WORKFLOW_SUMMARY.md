# AI Workflow Summary

Last updated: 2026-08-11

This is the concise handoff guide for contributors and coding assistants working on `oPool_Optimiser`. The public examples must remain generic: do not add experiment names, local database paths, or user-specific absolute paths.

## Canonical entry points

- `notebooks/oPool_Cloning_Notebook_Simple.ipynb`: primary notebook; edit one cell and choose **Run All**.
- `notebooks/oPool_Cloning_Colab.ipynb`: hosted public workflow; upload one CSV and download one result ZIP.
- `scripts/opool_cli.py`: primary terminal interface.
- `scripts/opool_workflow.py`: shared implementation used by the simple notebook and CLI.
- `notebooks/oPool_Cloning_Notebook_Fast_Pool_Assignment.ipynb`: advanced modular notebook.

The simple notebook and CLI should behave consistently. New core behavior belongs in `scripts/opool_workflow.py`, with tests under `tests/`, rather than being independently reimplemented in each entry point.

The Colab notebook is also a thin front end over `scripts/opool_workflow.py`. It must clone the public repository before importing code because opening an `.ipynb` from GitHub does not place the rest of the repository in the Colab runtime. Keep its dependency set in `requirements-colab.txt`, its Google Drive integration optional, and its final ZIP download enabled by default.

## Bundled defaults

```yaml
input: data/AAseq_dTF001_dTF016.csv
alternative_bundled_input: data/fpbase_top500.csv
overhang_inventory: data/overhangs.csv
primer_inventory: data/orthogonal_oligos.csv
output_directory_for_bundled_input: outputs/
oligo_length_nt: 250
vector_overhang_1: GCTT
vector_overhang_2: AGTG
genes_per_subpool: null  # automatic packing; no fixed gene limit
short_pool_max_size: null
primer_mode: combinatorial
typeiis_recognition_site: GGTCTC
typeiis_n_base: A
codon_species: e_coli
strip_n_terminal_methionine: true
overwrite_existing: false
```

These defaults are deliberately repository-owned. Do not replace them with files from an experiment directory. A user may explicitly override any of them for a run.

## Path and output policy

- Bundled inventories always resolve from the repository `data/` directory, independent of the current working directory.
- An explicit absolute path is used as supplied.
- A relative project input path is resolved from the current working directory.
- A path beginning with `data/` refers to the repository's bundled data.
- Bundled example input writes to `outputs/`; external input writes beside that input unless `output_dir` is supplied.
- Existing outputs are protected unless the user explicitly enables overwrite/`--force`.
- Generated files in `outputs/` remain git-ignored.
- Never commit machine-specific paths or experiment-specific names in public examples.

## Input contracts

### Amino-acid CSV

Accepted forms:

1. Headered CSV with `name` and either `aa_seq` or `amino_acid_sequence`.
2. Headerless two-column CSV containing sequence name then amino-acid sequence.

Names must be unique. Sequences use standard one-letter amino-acid codes; whitespace is removed and letters are normalized to uppercase.

### Optimized-DNA CSV

Must contain `name` and `dna_seq_optimized`. An optional `aa_seq` column is retained. DNA must contain only A/C/G/T and have a length divisible by three.

### Overhang inventory

`data/overhangs.csv` supplies unique 4-nt A/C/G/T overhangs. Custom CSV/TXT files may be comma-separated or contain one value per row or column. Generate compatible sets with [NEB GetSet](https://ligasefidelity.neb.com/getset/run.cgi), using the configured 5′ and 3′ vector overhangs as **Required Overhangs**. Vector overhangs present in the file are accepted and automatically excluded from internal assignment.

### Primer inventory

`data/orthogonal_oligos.csv` is read without a header. The first column is the primer name/ID and the last column is its 5′→3′ sequence.

## Workflow behavior

1. Detect amino-acid versus optimized-DNA input.
2. For amino-acid input, reverse-translate and optimize codons with DnaChisel.
3. Split each coding sequence into fragments no longer than the available insert length.
4. Use native 4-nt overhangs or translation-preserving synonymous edits to create valid overhangs.
5. Keep internal overhangs unique within each sub-pool.
6. Check the configured Type IIS recognition sequence and reverse complement inside coding DNA and across vector/coding boundaries.
7. Repair boundary-created sites only with synonymous coding changes; never change a configured vector overhang or protein sequence.
8. Add primers, Type IIS elements, vector overhangs, and optional sequence-safe stuffer.
9. Validate final oligo lengths and motif safety, then write outputs.

## Core outputs

For a run prefix `<run>`:

- `<run>_Optimised.csv`
- `<run>_Assigned.csv`
- `<run>_FULL_INFO.csv`
- `<run>_references.fasta`
- `<run>_oPool_Order_Fragments.csv`
- `<run>_overhangs_used.csv`
- `<run>_orthogonal_oligos_unused.csv`
- `<run>_stripped_ATG_log.csv`
- `<run>_vector_boundary_synonymous_corrections.csv`
- `<run>_unassigned.csv` when assignment failures occur
- combinatorial primer-pair inventory files when that mode is used

## Contributor guardrails

1. Keep README, CLI help, notebook inputs, and `WorkflowConfig` defaults synchronized.
2. Preserve public examples as generic repo-relative paths.
3. Keep the Type IIS recognition sequence and its N-base as separate settings.
4. Never alter vector overhangs or protein translation as part of motif repair.
5. Keep automatic packing represented by `genes_per_subpool=None`.
6. Add regression tests for path handling and biology-critical behavior.
7. Do not stage local primer-consumption files or generated outputs unless explicitly requested.
8. Run `python -m unittest discover -s tests -v`, compilation checks, and `git diff --check` before publishing.
9. Keep the Colab notebook free of stored outputs and ensure every code cell is valid Python rather than relying on local-only notebook state.
10. Keep the README acknowledgements synchronized when a direct scientific dependency or external design service is added or removed.

## Setup and smoke test

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python scripts/opool_cli.py --help
python -m unittest discover -s tests -v
```

See `README.md` for the end-user quick start and complete CLI examples.
