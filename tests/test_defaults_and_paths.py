from __future__ import annotations

import os
import json
import sys
import tempfile
import unittest
from pathlib import Path

import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from oforge_cli import build_parser, config_from_args  # noqa: E402
from opool_workflow import (  # noqa: E402
    DATA_DIR,
    DEFAULT_INPUT_PATH,
    PoolAssigner,
    RunPaths,
    WorkflowConfig,
    _read_aa_input,
    _resolve_inventory,
)


class DefaultAndPathTests(unittest.TestCase):
    def test_cli_defaults_use_bundled_data(self) -> None:
        parser = build_parser()
        config = config_from_args(parser.parse_args([]))

        self.assertEqual(parser.prog, "oforge")
        self.assertEqual(config.input_path, DEFAULT_INPUT_PATH.resolve())
        self.assertEqual(
            _resolve_inventory(config.overhangs_path, "overhangs.csv"),
            (DATA_DIR / "overhangs.csv").resolve(),
        )
        self.assertEqual(
            _resolve_inventory(config.primers_path, "orthogonal_oligos.csv"),
            (DATA_DIR / "orthogonal_oligos.csv").resolve(),
        )
        self.assertEqual(config.opool_length, 250)
        self.assertEqual((config.vector_oh1, config.vector_oh2), ("GCTT", "AGTG"))
        self.assertIsNone(config.genes_per_subpool)
        self.assertIsNone(config.short_pool_max_size)
        self.assertFalse(config.force)
        self.assertEqual(RunPaths.from_config(config).run_dir, REPO_ROOT / "outputs")

    def test_repo_data_paths_work_outside_repository(self) -> None:
        previous_cwd = Path.cwd()
        with tempfile.TemporaryDirectory() as tempdir:
            try:
                os.chdir(tempdir)
                args = build_parser().parse_args([
                    "--input",
                    "data/AAseq_dTF001_dTF016.csv",
                    "--overhangs",
                    "data/overhangs.csv",
                    "--primers",
                    "data/orthogonal_oligos.csv",
                ])
                config = config_from_args(args)
                self.assertEqual(config.input_path, DEFAULT_INPUT_PATH.resolve())
                self.assertEqual(
                    _resolve_inventory(config.overhangs_path, "overhangs.csv"),
                    (DATA_DIR / "overhangs.csv").resolve(),
                )
                self.assertEqual(
                    _resolve_inventory(config.primers_path, "orthogonal_oligos.csv"),
                    (DATA_DIR / "orthogonal_oligos.csv").resolve(),
                )
            finally:
                os.chdir(previous_cwd)

    def test_relative_external_input_stays_relative_to_calling_directory(self) -> None:
        previous_cwd = Path.cwd()
        with tempfile.TemporaryDirectory() as tempdir:
            project_dir = Path(tempdir)
            input_path = project_dir / "amino_acids.csv"
            input_path.write_text("name,aa_seq\nexample,MKT\n")
            try:
                os.chdir(project_dir)
                config = config_from_args(
                    build_parser().parse_args(["--input", "amino_acids.csv"])
                )
                self.assertEqual(config.input_path, input_path.resolve())
                self.assertEqual(RunPaths.from_config(config).run_dir, project_dir.resolve())
            finally:
                os.chdir(previous_cwd)

    def test_public_interfaces_do_not_contain_project_or_machine_paths(self) -> None:
        public_files = [
            REPO_ROOT / "README.md",
            REPO_ROOT / "AI_WORKFLOW_SUMMARY.md",
            REPO_ROOT / "scripts" / "oforge_cli.py",
            REPO_ROOT / "scripts" / "opool_cli.py",
            REPO_ROOT / "notebooks" / "oPool_Cloning_Notebook_Simple.ipynb",
            REPO_ROOT / "notebooks" / "oPool_Cloning_Notebook_Fast_Pool_Assignment.ipynb",
            REPO_ROOT / "notebooks" / "oPool_Cloning_Colab.ipynb",
        ]
        forbidden_tokens = (
            "op" + "TF",
            "/" + "Users" + "/",
            "oPool" + "_" + "database",
        )
        for path in public_files:
            with self.subTest(path=path.name):
                contents = path.read_text()
                for token in forbidden_tokens:
                    self.assertNotIn(token, contents)

    def test_getset_guidance_counts_internal_and_vector_overhangs(self) -> None:
        documented_notebooks = (
            "oPool_Cloning_Notebook_Simple.ipynb",
            "oPool_Cloning_Notebook_Fast_Pool_Assignment.ipynb",
            "oPool_Cloning_Colab.ipynb",
        )
        for filename in documented_notebooks:
            with self.subTest(notebook=filename):
                contents = (REPO_ROOT / "notebooks" / filename).read_text().replace("`", "")
                self.assertIn("34 for 32 internal and two vector overhangs", contents)

        workflow_guide = (REPO_ROOT / "AI_WORKFLOW_SUMMARY.md").read_text()
        self.assertIn("enter `34` for 32 internal and two vector overhangs", workflow_guide)

    def test_colab_notebook_is_self_contained_and_output_free(self) -> None:
        notebook_path = REPO_ROOT / "notebooks" / "oPool_Cloning_Colab.ipynb"
        notebook = json.loads(notebook_path.read_text())
        code = "\n".join(
            "".join(cell.get("source", []))
            for cell in notebook["cells"]
            if cell["cell_type"] == "code"
        )
        markdown = "\n".join(
            "".join(cell.get("source", []))
            for cell in notebook["cells"]
            if cell["cell_type"] == "markdown"
        )

        self.assertEqual(notebook["nbformat"], 4)
        self.assertTrue(notebook["metadata"]["colab"]["include_colab_link"])
        self.assertIn("https://github.com/t-j-fryer/oFORGE.git", code)
        self.assertIn('PROJECT_ROOT = Path("/content/oFORGE")', code)
        self.assertIn("requirements-colab.txt", code)
        self.assertIn('PROJECT_ROOT / "data" / "AAseq_dTF001_dTF016.csv"', code)
        self.assertIn('PROJECT_ROOT / "data" / "fpbase_top500.csv"', code)
        self.assertIn('PROJECT_ROOT / "data" / "overhangs.csv"', code)
        self.assertIn('PROJECT_ROOT / "data" / "orthogonal_oligos.csv"', code)
        self.assertIn("files.upload()", code)
        self.assertIn("files.download", code)
        self.assertIn("SAVE_TO_GOOGLE_DRIVE = False", code)
        self.assertIn("USE_BUNDLED_DATASET = True", code)
        self.assertIn("USE_CUSTOM_OVERHANGS = False", code)
        self.assertIn('CUSTOM_OVERHANGS_TEXT = ""', code)
        self.assertIn("Select the custom GetSet overhang CSV/TXT", code)
        self.assertIn('BUNDLED_DATASET = "AAseq_dTF001_dTF016.csv"', code)
        self.assertIn('OPOOL_LENGTH = 250  # @param {type:"slider", min:250, max:350, step:10}', code)
        self.assertIn("GENES_PER_SUBPOOL = 0", code)
        self.assertIn('"Total order oligos"', code)
        self.assertIn("subpool_summary", code)
        self.assertIn("WorkflowConfig(", code)
        self.assertIn("docs/images/opool_computational_workflow.png", markdown)
        self.assertIn("docs/images/opool_wet_lab_workflow.png", markdown)
        self.assertIn("3 µL total oPool DNA", markdown)
        self.assertIn("https://ligasefidelity.neb.com/getset/run.cgi", markdown)
        self.assertIn("enter `34` for 32 internal and two vector overhangs", markdown)
        self.assertIn("# oFORGE Designer — Google Colab", markdown)
        self.assertIn("oFORGE assembly", markdown)

        for cell in notebook["cells"]:
            if cell["cell_type"] == "code":
                self.assertIsNone(cell["execution_count"])
                self.assertEqual(cell["outputs"], [])
                compile("".join(cell["source"]), str(notebook_path), "exec")

    def test_readme_workflow_images_and_shared_template_protocol(self) -> None:
        readme = (REPO_ROOT / "README.md").read_text()
        image_names = (
            "opool_computational_workflow.png",
            "opool_wet_lab_workflow.png",
            "pooled_library_cost_comparison.png",
        )

        for image_name in image_names:
            image_path = REPO_ROOT / "docs" / "images" / image_name
            with self.subTest(image=image_name):
                self.assertTrue(image_path.is_file())
                self.assertTrue(image_path.read_bytes().startswith(b"\x89PNG\r\n\x1a\n"))
                self.assertIn(f"docs/images/{image_name}", readme)

        self.assertIn("3 µL total", readme)
        self.assertIn("384 sub-pool PCRs", readme)
        self.assertIn("12.5 × N µL", readme)
        self.assertIn("10 × N − 3 µL", readme)
        self.assertIn("BsaI-HFv2", readme)
        self.assertIn("90 alternating cycles", readme)
        self.assertIn("sub-pool-specific transformation", readme.lower())
        self.assertIn("https://ligasefidelity.neb.com/getset/run.cgi", readme)
        self.assertIn("request `34` when you want 32 internal overhangs with 2 vector overhangs", readme)
        self.assertTrue(readme.startswith("# oFORGE\n"))
        self.assertIn("Scalable gene construction from oligonucleotide pools", readme)
        self.assertIn("**o**ligo-pool **F**ragmentation", readme)
        self.assertIn("oFORGE Designer", readme)
        self.assertIn("oFORGE assembly", readme)
        self.assertIn("t-j-fryer/oFORGE", readme)
        self.assertNotIn("t-j-fryer/oPool_Optimiser", readme)
        self.assertIn("name: oforge", (REPO_ROOT / "environment.yml").read_text())

        cost_png = (REPO_ROOT / "docs" / "images" / "pooled_library_cost_comparison.png").read_bytes()
        self.assertEqual(cost_png[12:16], b"IHDR")
        self.assertEqual(cost_png[25], 2, "Cost figure must be opaque RGB for GitHub dark mode")

    def test_custom_overhang_layout_accepts_and_excludes_vector_overhangs(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            overhangs_path = root / "getset_overhangs.csv"
            overhangs_path.write_text("Overhang\nGCTT\nAGTG\nCTAA\nCAGA\nGTGA\n")
            config = WorkflowConfig(
                input_path=DEFAULT_INPUT_PATH,
                output_dir=root / "outputs",
                overhangs_path=overhangs_path,
                vector_oh1="GCTT",
                vector_oh2="AGTG",
            )
            assigner = PoolAssigner(
                config,
                RunPaths.from_config(config),
                pd.DataFrame(columns=["name", "dna_seq_optimized"]),
                overhangs_path,
            )

            self.assertEqual(assigner.overhangs, ["GCTT", "AGTG", "CTAA", "CAGA", "GTGA"])
            self.assertEqual(assigner.excluded_vector_overhangs, ["GCTT", "AGTG"])
            self.assertEqual(assigner.internal_overhangs, ["CTAA", "CAGA", "GTGA"])

    def test_colab_requirements_exclude_notebook_environment_packages(self) -> None:
        requirements = (REPO_ROOT / "requirements-colab.txt").read_text().lower()
        self.assertIn("dnachisel", requirements)
        self.assertIn("biopython", requirements)
        self.assertNotIn("jupyterlab", requirements)
        self.assertNotIn("ipykernel", requirements)

    def test_repository_has_mit_license_and_canonical_example(self) -> None:
        license_text = (REPO_ROOT / "LICENSE").read_text()
        self.assertTrue(license_text.startswith("MIT License\n"))
        self.assertIn("MASSACHUSETTS INSTITUTE OF TECHNOLOGY", license_text)
        self.assertIn("Permission is hereby granted, free of charge", license_text)
        self.assertTrue(DEFAULT_INPUT_PATH.is_file())
        self.assertEqual(DEFAULT_INPUT_PATH.name, "AAseq_dTF001_dTF016.csv")
        self.assertFalse((DATA_DIR / "example_amino_acids.csv").exists())

    def test_fpbase_bundled_dataset_uses_friendly_sequence_header(self) -> None:
        fpbase_path = DATA_DIR / "fpbase_top500.csv"
        parsed = _read_aa_input(fpbase_path)

        self.assertEqual(len(parsed), 500)
        self.assertEqual(list(parsed.columns), ["name", "aa_seq"])
        self.assertEqual(parsed.iloc[0]["name"], "AausFP1")
        self.assertTrue(parsed["name"].is_unique)
        self.assertFalse(parsed["aa_seq"].isna().any())


if __name__ == "__main__":
    unittest.main()
