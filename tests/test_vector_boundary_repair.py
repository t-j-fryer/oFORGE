from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

import pandas as pd
from Bio.Seq import Seq


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from opool_workflow import (  # noqa: E402
    GeneRecord,
    PoolAssigner,
    RunPaths,
    WorkflowConfig,
    run_workflow,
)


class VectorBoundaryRepairTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.input_path = self.root / "input.csv"
        self.input_path.write_text("name,aa_seq,dna_seq_optimized\n")
        self.overhangs_path = self.root / "overhangs.csv"
        # GetSet-style inventories may include the required vector overhangs.
        self.overhangs_path.write_text("GCTT,AGTG,CTAA,CAGA,GTGA\n")

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def make_assigner(
        self,
        typeiis_site: str,
        vector_oh1: str,
        vector_oh2: str,
    ) -> PoolAssigner:
        config = WorkflowConfig(
            input_path=self.input_path,
            input_kind="optimized",
            output_dir=self.root,
            run_name="unit",
            overhangs_path=self.overhangs_path,
            opool_length=100,
            vector_oh1=vector_oh1,
            vector_oh2=vector_oh2,
            strip_nterm_met=False,
            typeiis_site=typeiis_site,
            typeiis_n="A",
            skip_primer_assignment=True,
            show_progress=False,
        )
        optimized = pd.DataFrame(columns=["name", "aa_seq", "dna_seq_optimized"])
        return PoolAssigner(
            config,
            RunPaths.from_config(config),
            optimized,
            self.overhangs_path,
        )

    def test_repairs_bsai_site_at_three_prime_boundary_without_changing_overhangs(self) -> None:
        assigner = self.make_assigner("GGTCTC", "TAGT", "TCGG")
        sequence = "AAACCCGGGTTTATGGTC"
        first_fragment = sequence[:12]
        second_fragment = sequence[8:]
        assigned = pd.DataFrame([{
            "Block": 1,
            "Length Distribution": "Long-2part",
            "Sequence Name": "bsai_boundary",
            "VectorOH1": "TAGT",
            "VectorOH1_Source": "Fixed",
            "VectorOH2": "TCGG",
            "Overhang1": "GTTT",
            "DNA Fragment 1": first_fragment,
            "DNA Fragment 2": second_fragment,
            "Full Sequence": sequence,
        }])

        repaired, corrections = assigner._repair_vector_boundaries(assigned)
        row = repaired.iloc[0]

        self.assertEqual(row["VectorOH1"], "TAGT")
        self.assertEqual(row["VectorOH2"], "TCGG")
        self.assertEqual(row["DNA Fragment 1"], first_fragment)
        self.assertTrue(row["DNA Fragment 2"].startswith("GTTT"))
        self.assertEqual(
            row["DNA Fragment 1"] + row["DNA Fragment 2"][4:],
            row["Full Sequence"],
        )
        self.assertEqual(str(Seq(row["Full Sequence"]).translate()), str(Seq(sequence).translate()))
        self.assertFalse(assigner._boundary_site_occurrences(row["Full Sequence"], "TAGT", "TCGG"))
        self.assertEqual(len(corrections), 1)
        self.assertEqual(corrections.iloc[0]["Boundary"], "3_prime")
        self.assertEqual(corrections.iloc[0]["Configured_TypeIIS_Recognition_Site"], "GGTCTC")
        self.assertEqual(corrections.iloc[0]["Forbidden_Site_Observed"], "GGTCTC")
        self.assertEqual(corrections.iloc[0]["Old_Codon"], "GTC")
        self.assertEqual(corrections.iloc[0]["Amino_Acid"], "V")
        assigner._validate(repaired, [GeneRecord("bsai_boundary", sequence)])

    def test_uses_custom_typeiis_site_and_repairs_reverse_complement_at_five_prime_boundary(self) -> None:
        assigner = self.make_assigner("CGTCTC", "GAGA", "TCGG")
        sequence = "CGTAAA"
        assigned = pd.DataFrame([{
            "Block": 1,
            "Length Distribution": "Short",
            "Sequence Name": "bsmbi_reverse_boundary",
            "VectorOH1": "GAGA",
            "VectorOH1_Source": "Fixed",
            "VectorOH2": "TCGG",
            "Overhang1": "N/A",
            "DNA Fragment 1": sequence,
            "Full Sequence": sequence,
        }])

        repaired, corrections = assigner._repair_vector_boundaries(assigned)
        row = repaired.iloc[0]

        self.assertEqual(row["VectorOH1"], "GAGA")
        self.assertEqual(row["VectorOH2"], "TCGG")
        self.assertNotEqual(row["Full Sequence"][:3], "CGT")
        self.assertEqual(str(Seq(row["Full Sequence"]).translate()), "RK")
        self.assertFalse(assigner._boundary_site_occurrences(row["Full Sequence"], "GAGA", "TCGG"))
        self.assertEqual(corrections.iloc[0]["Configured_TypeIIS_Recognition_Site"], "CGTCTC")
        self.assertEqual(corrections.iloc[0]["Forbidden_Site_Observed"], "GAGACG")
        self.assertEqual(corrections.iloc[0]["Boundary"], "5_prime")

    def test_fails_instead_of_changing_vector_when_no_synonymous_repair_exists(self) -> None:
        assigner = self.make_assigner("GCTAAT", "GCTA", "TCGG")
        with self.assertRaisesRegex(ValueError, "without changing the configured vector overhang"):
            assigner._repair_boundary_sequence(
                "methionine_only",
                "ATGAAA",
                "GCTA",
                "TCGG",
            )

    def test_end_to_end_workflow_repairs_before_primer_assembly(self) -> None:
        sequence = "TTTATGGTC"
        pd.DataFrame([{
            "name": "end_to_end",
            "aa_seq": str(Seq(sequence).translate()),
            "dna_seq_optimized": sequence,
        }]).to_csv(self.input_path, index=False)
        primers_path = self.root / "primers.csv"
        primers_path.write_text(
            "1,ACATAAGCGATCCCAAGGTC\n"
            "2,AAACCGGAGCCATACAGTAC\n"
        )
        config = WorkflowConfig(
            input_path=self.input_path,
            input_kind="optimized",
            output_dir=self.root,
            run_name="end_to_end",
            overhangs_path=self.overhangs_path,
            primers_path=primers_path,
            opool_length=100,
            vector_oh1="TAGT",
            vector_oh2="TCGG",
            strip_nterm_met=False,
            typeiis_site="GGTCTC",
            typeiis_n="A",
            primer_mode="unique_pairs",
            show_progress=False,
        )

        result = run_workflow(config)
        assigned = pd.read_csv(result.paths.assigned)
        corrections = pd.read_csv(result.paths.boundary_repairs)
        order = pd.read_csv(result.paths.fragments)
        oligo = order.iloc[0]["Sequence"]
        cut_prefix = "GGTCTCA"
        cut_suffix = "TGAGACC"
        insert_start = oligo.index(cut_prefix) + len(cut_prefix)
        insert_end = oligo.index(cut_suffix, insert_start)
        insert = oligo[insert_start:insert_end]

        self.assertEqual(result.assigned_genes, 1)
        self.assertEqual(len(corrections), 1)
        self.assertEqual(assigned.iloc[0]["VectorOH1"], "TAGT")
        self.assertEqual(assigned.iloc[0]["VectorOH2"], "TCGG")
        self.assertTrue(insert.startswith("TAGT"))
        self.assertTrue(insert.endswith("TCGG"))
        self.assertEqual(len(oligo), 100)
        self.assertEqual(oligo.count("GGTCTC"), 1)
        self.assertEqual(oligo.count("GAGACC"), 1)
        self.assertEqual(
            str(Seq(assigned.iloc[0]["Full Sequence"]).translate()),
            str(Seq(sequence).translate()),
        )


if __name__ == "__main__":
    unittest.main()
