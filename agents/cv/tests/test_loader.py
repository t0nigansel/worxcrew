from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

from agents.cv.loader import list_available_people, load_source_bundle


FIXTURE_BASE_DIR = Path(__file__).resolve().parents[1]


def make_temp_base_dir() -> Path:
    temp_dir = Path(tempfile.mkdtemp(prefix="cv-loader-test-"))
    shutil.copytree(FIXTURE_BASE_DIR / "people", temp_dir / "people")
    shutil.copytree(FIXTURE_BASE_DIR / "template", temp_dir / "template")
    return temp_dir


class LoaderTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = make_temp_base_dir()

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir)

    def test_lists_available_people(self) -> None:
        people = list_available_people(self.temp_dir)
        self.assertIn("toni", people)

    def test_loads_person_scoped_bundle(self) -> None:
        bundle = load_source_bundle(self.temp_dir, "toni")
        self.assertEqual(bundle.person_id, "toni")
        self.assertTrue(bundle.profile_path.exists())
        self.assertTrue(bundle.projects_path.exists())
        self.assertTrue(bundle.certifications_path.exists())
        self.assertTrue(bundle.portrait_path.exists())

    def test_loads_portrait_with_uppercase_extension(self) -> None:
        person_dir = self.temp_dir / "people" / "john-smith"
        portraits = sorted(path for path in person_dir.glob("portrait.*") if path.is_file())
        self.assertTrue(portraits)
        original = portraits[0]
        renamed = person_dir / "portrait.JPG"
        if original.name != "portrait.JPG":
            original.replace(renamed)

        bundle = load_source_bundle(self.temp_dir, "john-smith")
        self.assertEqual(bundle.portrait_path.name, "portrait.JPG")


if __name__ == "__main__":
    unittest.main()
