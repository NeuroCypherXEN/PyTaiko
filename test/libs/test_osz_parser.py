import tempfile
import unittest
from pathlib import Path

from libs.parsers.osz import OsuParser
from libs.parsers.tja import NoteType


OSU_CONTENT = """osu file format v14

[General]
AudioFilename: song.mp3
PreviewTime: 1000

[Editor]
DistanceSpacing: 1

[Metadata]
Version: Test Version
Creator: Test Creator

[Difficulty]
SliderMultiplier: 1.4
OverallDifficulty: 5

[Events]
0,0,"bg.jpg",0,0

[TimingPoints]
0,500,4,2,0,100,1,0
1000,-50,4,2,0,100,0,0

[HitObjects]
256,192,1500,1,0,0:0:0:0:
256,192,2000,2,0,B|300:192,1,140
"""


class TestOsuParser(unittest.TestCase):
    def _create_osu_file(self) -> Path:
        tmp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(tmp_dir.cleanup)
        osu_path = Path(tmp_dir.name) / "test.osu"
        osu_path.write_text(OSU_CONTENT, encoding="utf-8")
        return osu_path

    def test_parser_initialization_and_metadata(self):
        osu_path = self._create_osu_file()
        parser = OsuParser(osu_path)

        self.assertEqual(parser.metadata.title["en"], "Test Version")
        self.assertEqual(parser.metadata.subtitle["en"], "Test Creator")
        self.assertEqual(parser.metadata.wave, osu_path.parent / "song.mp3")
        self.assertEqual(parser.metadata.bgmovie, osu_path.parent / "bg.jpg")
        self.assertIn(0, parser.metadata.course_data)

    def test_scroll_multiplier_uses_inherited_timing_point(self):
        parser = OsuParser(self._create_osu_file())

        self.assertAlmostEqual(parser.get_scroll_multiplier(500), 1.0, places=5)
        self.assertAlmostEqual(parser.get_scroll_multiplier(1500), 2.0, places=5)

    def test_note_conversion_and_hash(self):
        parser = OsuParser(self._create_osu_file())
        notes, _, _, _ = parser.notes_to_position(0)

        self.assertEqual(len(notes.play_notes), 3)
        self.assertEqual(notes.play_notes[0].type, NoteType.DON)
        self.assertEqual(notes.play_notes[1].type, NoteType.ROLL_HEAD)
        self.assertEqual(notes.play_notes[2].type, NoteType.TAIL)
        self.assertEqual(len(notes.timeline), 1)

        note_hash = parser.hash_note_data(notes)
        self.assertIsInstance(note_hash, str)
        self.assertEqual(len(note_hash), 64)
        self.assertEqual(note_hash, parser.hash_note_data(notes))


if __name__ == '__main__':
    unittest.main()
