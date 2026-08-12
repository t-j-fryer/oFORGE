# oPool Optimiser

Fast, user-friendly workflows for optimizing genes and preparing pooled Golden Gate cloning oligos.

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/t-j-fryer/oPool_Optimiser/blob/main/notebooks/oPool_Cloning_Colab.ipynb)

For AI assistant handoff, settings, workflow conventions, and FAQ, see `AI_WORKFLOW_SUMMARY.md`.

## Repository Layout

- `notebooks/oPool_Cloning_Notebook_Fast_Pool_Assignment.ipynb`: modular notebook with the faster long-gene pool search
- `notebooks/oPool_Cloning_Notebook_Simple.ipynb`: edit one input cell, then choose **Run All**
- `notebooks/oPool_Cloning_Colab.ipynb`: one-click hosted workflow with file upload and ZIP download
- `scripts/opool_cli.py`: terminal command-line interface
- `scripts/opool_workflow.py`: shared implementation used by the CLI, simple notebook, and Colab notebook
- `requirements-colab.txt`: minimal dependencies installed by the hosted notebook
- `data/orthogonal_oligos.csv`: default primer inventory
- `data/overhangs.csv`: default overhang inventory
- `data/AAseq_dTF001_dTF016.csv`: bundled example amino-acid library
- `outputs/`: generated outputs from notebook runs

## Google Colab — no local installation

Click the **Open in Colab** badge above, edit the single **User settings** cell, and choose **Runtime → Run all**.

- Leave `USE_BUNDLED_EXAMPLE = True` to run the bundled amino-acid library.
- Set it to `False` to upload one amino-acid or optimized-DNA CSV when prompted.
- The tracked `data/overhangs.csv` and `data/orthogonal_oligos.csv` inventories are used automatically.
- `GENES_PER_SUBPOOL = 0` means automatic packing with no fixed gene-count limit.
- A standard CPU runtime is sufficient.
- Every run creates a ZIP containing all CSV and FASTA outputs and downloads it automatically.
- Optional Google Drive output is available but disabled by default, so the notebook does not request Drive access unless the user chooses it.

Colab runtimes are temporary. Download the ZIP before closing the runtime unless Google Drive output was enabled.

## Python Environment + Kernel

### Option A: `venv` (recommended)

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
python -m ipykernel install --user --name opool-cloning --display-name "Python 3 (opool-cloning)"
```

Then in Jupyter, choose kernel: `Python 3 (opool-cloning)`.

### Option B: Conda/Mamba

```bash
conda env create -f environment.yml
conda activate opool-cloning
python -m ipykernel install --user --name opool-cloning --display-name "Python 3 (opool-cloning)"
```

## Simplest notebook workflow

```bash
jupyter lab
```

Open `notebooks/oPool_Cloning_Notebook_Simple.ipynb`, edit its single **User inputs** cell, and choose **Run All**.

## Terminal workflow

After installing the environment, this command runs the complete workflow with the bundled files in `data/`:

```bash
python scripts/opool_cli.py
```

The example outputs are written to `outputs/`. Existing files are protected, so a second run will stop rather than silently replace them.

For a real project, only the input normally needs to change. The input can be either an amino-acid CSV or an existing optimized-DNA CSV; its format is detected automatically:

```bash
python scripts/opool_cli.py --input "/path/to/amino_acids.csv"
```

### Defaults

| Setting | Default |
| --- | --- |
| Input | `data/AAseq_dTF001_dTF016.csv` |
| Internal overhangs | `data/overhangs.csv` |
| Orthogonal primers | `data/orthogonal_oligos.csv` |
| Oligo length | 250 nt |
| Vector overhangs | `GCTT` / `AGTG` |
| Genes per sub-pool | automatic packing; no fixed limit |
| Primer mode | combinatorial |
| Type IIS enzyme settings | `GGTCTC` recognition site plus separate `A` N-base |
| Codon host | *E. coli* |
| Leading methionine | stripped |

The two inventory paths are resolved from the repository, even if the command is launched from another directory. Relative project input paths are resolved from the current directory; paths beginning with `data/` always refer to this repository's bundled data.

Override only the settings your assembly requires. For example:

```bash
python scripts/opool_cli.py \
  --input "/path/to/optimized_dna.csv" \
  --opool-length 350 \
  --vector-oh1 TATG \
  --vector-oh2 GGAT \
  --genes-per-subpool 1
```

Run this for all options and their defaults:

```bash
python scripts/opool_cli.py --help
```

For external inputs, outputs are written beside the input file by default. Choose a different `--run-name`/`--output-dir`, or explicitly pass `--force` to replace existing outputs.

### Type IIS vector-boundary safety

Pool assignment checks the configured Type IIS recognition sequence and its reverse complement across both vector-overhang/coding-sequence boundaries. If a boundary creates a site, the workflow searches for the smallest synonymous coding change, rebuilds the affected fragments, and leaves both vector overhangs unchanged. It fails with an explicit error when no synonymous repair is possible rather than altering an overhang or protein sequence.

Repairs are recorded in `<run_name>_vector_boundary_synonymous_corrections.csv`; the file is written with headers even when no repair is needed.

### Codon-optimization species

For amino-acid inputs, set `CODON_SPECIES` in the simple or fast notebook, or pass `--codon-species` to the CLI. The default is `e_coli`. The built-in species keywords supplied by `python_codon_tables` are:

| Species | Short keyword | Full table name |
| --- | --- | --- |
| *Bacillus subtilis* | `b_subtilis` | `b_subtilis_1423` |
| *Caenorhabditis elegans* | `c_elegans` | `c_elegans_6239` |
| *Drosophila melanogaster* | `d_melanogaster` | `d_melanogaster_7227` |
| *Escherichia coli* | `e_coli` | `e_coli_316407` |
| *Gallus gallus* | `g_gallus` | `g_gallus_9031` |
| *Homo sapiens* | `h_sapiens` | `h_sapiens_9606` |
| *Mus musculus* | `m_musculus` | `m_musculus_10090` |
| *Mus musculus domesticus* | `m_musculus_domesticus` | `m_musculus_domesticus_10092` |
| *Saccharomyces cerevisiae* | `s_cerevisiae` | `s_cerevisiae_4932` |

Either the short keyword or full table name is accepted. Alternatively, use a numeric NCBI taxonomy ID; DnaChisel will then need internet access to retrieve its codon table. This setting is ignored when the input already contains optimized DNA.

## Notes

- Notebook defaults use the bundled files in `data/` and write example outputs into `outputs/`.
- If you switch to your own datasets, update the single user-input cell in the simple notebook or the top configuration cell in the fast notebook.

## Acknowledgements and references

oPool Optimiser builds on the open-source scientific Python ecosystem. In particular:

- Gene optimization uses [DnaChisel](https://github.com/Edinburgh-Genome-Foundry/DnaChisel): Zulkower V, Rosser S. “DNA Chisel, a versatile sequence optimizer.” *Bioinformatics* 36(16), 4508–4509 (2020). [doi:10.1093/bioinformatics/btaa558](https://doi.org/10.1093/bioinformatics/btaa558).
- Sequence representation, translation, and reverse-complement operations use [Biopython](https://biopython.org/): Cock PJA et al. “Biopython: freely available Python tools for computational molecular biology and bioinformatics.” *Bioinformatics* 25(11), 1422–1423 (2009). [doi:10.1093/bioinformatics/btp163](https://doi.org/10.1093/bioinformatics/btp163).
- Codon-usage tables are supplied by [python-codon-tables](https://github.com/Edinburgh-Genome-Foundry/python_codon_tables).
- Data handling and numerical operations use [pandas](https://pandas.pydata.org/) and [NumPy](https://numpy.org/).
- The hosted notebook runs on [Google Colab](https://colab.research.google.com/).
- The bundled overhang inventory is intended for use with experimentally informed Golden Gate overhang selection. [NEB’s Ligase Fidelity tools](https://www.neb.com/en-us/applications/cloning-and-synthetic-biology/dna-assembly-and-cloning/golden-gate-assembly/ligase-fidelity) are a useful source for evaluating or generating compatible high-fidelity junction sets.

These projects and services retain their own licenses and trademarks. oPool Optimiser is not affiliated with or endorsed by their maintainers or providers.

## License

oPool Optimiser is released under the [MIT License](LICENSE).
