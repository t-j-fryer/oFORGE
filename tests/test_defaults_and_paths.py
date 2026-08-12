from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from opool_cli import build_parser, config_from_args  # noqa: E402
from opool_workflow import (  # noqa: E402
    DATA_DIR,
    DEFAULT_INPUT_PATH,
    RunPaths,
    _resolve_inventory,
)


class DefaultAndPathTests(unittest.TestCase):
    def test_cli_defaults_use_bundled_data(self) -> None:
        config = config_from_args(build_parser().parse_args([]))

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
                    "data/example_amino_acids.csv",
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
            REPO_ROOT / "scripts" / "opool_cli.py",
            REPO_ROOT / "notebooks" / "oPool_Cloning_Notebook_Simple.ipynb",
            REPO_ROOT / "notebooks" / "oPool_Cloning_Notebook_Fast_Pool_Assignment.ipynb",
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


if __name__ == "__main__":
    unittest.main()
