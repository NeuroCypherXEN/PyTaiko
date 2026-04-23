import json
import tempfile
import unittest
import zipfile
from types import SimpleNamespace
from pathlib import Path
from unittest.mock import Mock, patch

from libs.song_hash import build_song_hashes, process_tja_file, read_tjap3_score, safe_extract_zip
from libs.utils import global_data


class TestReadTjap3Score(unittest.TestCase):
    def test_read_tjap3_score_parses_numeric_ranges(self):
        ini_text = """
[HiScore.Drums]
HiScore1 = 100
HiScore2 = 200
HiScore3 = 300
HiScore4 = 400
HiScore5 = 500
Clear0 = 0
Clear1 = 1
Clear2 = 2
Clear3 = 0
Clear4 = 0
PerfectRange = 25
GoodRange = 75
PoorRange = 108
Perfect = 12
Great = 3
Miss = 1
"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            ini_path = Path(tmp_dir) / "sample.score.ini"
            ini_path.write_text(ini_text.strip(), encoding="utf-8")

            with patch("libs.song_hash.test_encodings", return_value="utf-8"):
                scores, clears, judges = read_tjap3_score(ini_path)

        self.assertEqual(scores, [100, 200, 300, 400, 500])
        self.assertEqual(clears, [0, 1, 2, 0, 0])
        self.assertEqual(judges, [12, 3, 1])

    def test_read_tjap3_score_rejects_incompatible_judge_window(self):
        ini_text = """
[HiScore.Drums]
HiScore1 = 100
HiScore2 = 200
HiScore3 = 300
HiScore4 = 400
HiScore5 = 500
PerfectRange = 26
GoodRange = 75
PoorRange = 108
Perfect = 9
"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            ini_path = Path(tmp_dir) / "sample.score.ini"
            ini_path.write_text(ini_text.strip(), encoding="utf-8")

            with patch("libs.song_hash.test_encodings", return_value="utf-8"):
                scores, clears, judges = read_tjap3_score(ini_path)

        self.assertEqual(scores, [0])
        self.assertEqual(clears, [0])
        self.assertIsNone(judges)


class TestSafeExtractZip(unittest.TestCase):
    def test_safe_extract_zip_blocks_path_traversal(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            zip_path = Path(tmp_dir) / "sample.osz"
            extract_dir = Path(tmp_dir) / "extracted"
            extract_dir.mkdir()

            with zipfile.ZipFile(zip_path, "w") as archive:
                archive.writestr("../escape.osu", "data")

            with zipfile.ZipFile(zip_path, "r") as archive:
                with self.assertRaises(ValueError):
                    safe_extract_zip(archive, extract_dir)

    def test_safe_extract_zip_extracts_valid_entries(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            zip_path = Path(tmp_dir) / "sample.osz"
            extract_dir = Path(tmp_dir) / "extracted"
            extract_dir.mkdir()

            with zipfile.ZipFile(zip_path, "w") as archive:
                archive.writestr("chart.osu", "osu content")

            with zipfile.ZipFile(zip_path, "r") as archive:
                safe_extract_zip(archive, extract_dir)

            self.assertTrue((extract_dir / "chart.osu").exists())


class TestBuildSongHashes(unittest.TestCase):
    def test_build_song_hashes_uses_configured_score_db_path(self):
        original_score_db = global_data.score_db
        original_song_hashes = global_data.song_hashes
        original_song_paths = global_data.song_paths
        original_total_songs = global_data.total_songs
        original_song_progress = global_data.song_progress

        try:
            with tempfile.TemporaryDirectory() as tmp_dir:
                tmp_path = Path(tmp_dir)
                output_dir = tmp_path / "cache"
                output_dir.mkdir()
                score_db_path = tmp_path / "custom_scores.db"
                score_db_path.touch()
                global_data.score_db = str(score_db_path)
                global_data.song_hashes = {}
                global_data.song_paths = {}
                global_data.total_songs = 0
                global_data.song_progress = 0.0

                song_hashes = {
                    "hash_a": [
                        {
                            "file_path": "Songs/a.tja",
                            "last_modified": 1.0,
                            "title": {"en": "Song A", "ja": "曲A"},
                            "subtitle": {"en": "", "ja": ""},
                            "diff_hashes": {"0": "diff0", "1": "diff1"},
                        }
                    ]
                }
                (output_dir / "song_hashes.json").write_text(
                    json.dumps(song_hashes, ensure_ascii=False),
                    encoding="utf-8",
                )
                (output_dir / "path_to_hash.json").write_text("{}", encoding="utf-8")
                (output_dir / "timestamp.txt").write_text("0.0", encoding="utf-8")

                mock_cursor = Mock()
                mock_cursor.fetchall.return_value = []
                mock_cursor.rowcount = 0
                mock_conn = Mock()
                mock_conn.cursor.return_value = mock_cursor

                with (
                    patch("libs.song_hash.get_config", return_value={"paths": {"tja_path": []}}),
                    patch("libs.song_hash.get_db_version", return_value=0),
                    patch("libs.song_hash.update_db_version"),
                    patch("libs.song_hash.sqlite3.connect", return_value=mock_conn) as mock_connect,
                ):
                    build_song_hashes(output_dir=output_dir)

                mock_connect.assert_called_once_with(score_db_path)
                self.assertEqual(mock_conn.commit.call_count, 1)
        finally:
            global_data.score_db = original_score_db
            global_data.song_hashes = original_song_hashes
            global_data.song_paths = original_song_paths
            global_data.total_songs = original_total_songs
            global_data.song_progress = original_song_progress

    def test_build_song_hashes_handles_invalid_timestamp_cache(self):
        original_score_db = global_data.score_db
        original_song_hashes = global_data.song_hashes
        original_song_paths = global_data.song_paths
        original_total_songs = global_data.total_songs
        original_song_progress = global_data.song_progress

        try:
            with tempfile.TemporaryDirectory() as tmp_dir:
                tmp_path = Path(tmp_dir)
                output_dir = tmp_path / "deep" / "cache"
                score_db_path = tmp_path / "custom_scores.db"
                score_db_path.touch()
                global_data.score_db = str(score_db_path)
                global_data.song_hashes = {}
                global_data.song_paths = {}
                global_data.total_songs = 0
                global_data.song_progress = 0.0

                output_dir.mkdir(parents=True, exist_ok=True)
                (output_dir / "song_hashes.json").write_text("{}", encoding="utf-8")
                (output_dir / "path_to_hash.json").write_text("{}", encoding="utf-8")
                (output_dir / "timestamp.txt").write_text("invalid-float", encoding="utf-8")

                with (
                    patch("libs.song_hash.get_config", return_value={"paths": {"tja_path": []}}),
                    patch("libs.song_hash.get_db_version", return_value=1),
                    patch("libs.song_hash.logger.warning") as mock_warning,
                ):
                    build_song_hashes(output_dir=output_dir)

                mock_warning.assert_any_call("Invalid timestamp cache detected, rebuilding song hash cache")
                self.assertTrue((output_dir / "song_hashes.json").exists())
        finally:
            global_data.score_db = original_score_db
            global_data.song_hashes = original_song_hashes
            global_data.song_paths = original_song_paths
            global_data.total_songs = original_total_songs
            global_data.song_progress = original_song_progress


class TestProcessTjaFile(unittest.TestCase):
    def test_process_tja_file_returns_empty_hash_when_note_list_is_empty(self):
        fake_parser = SimpleNamespace(
            metadata=SimpleNamespace(course_data={0: {}}),
            file_path=Path("dummy.tja"),
            hash_note_data=Mock(return_value="should_not_be_used"),
        )
        empty_notes = SimpleNamespace(play_notes=[], bars=[])

        with (
            patch("libs.song_hash.TJAParser", return_value=fake_parser),
            patch("libs.song_hash.TJAParser.notes_to_position", return_value=(empty_notes, None, None, None)),
        ):
            result = process_tja_file(Path("dummy.tja"))

        self.assertEqual(result, "")
        fake_parser.hash_note_data.assert_not_called()

    def test_process_tja_file_hashes_when_notes_exist(self):
        fake_parser = SimpleNamespace(
            metadata=SimpleNamespace(course_data={0: {}}),
            file_path=Path("dummy.tja"),
            hash_note_data=Mock(return_value="expected_hash"),
        )
        notes = SimpleNamespace(play_notes=[object()], bars=[])

        with (
            patch("libs.song_hash.TJAParser", return_value=fake_parser),
            patch("libs.song_hash.TJAParser.notes_to_position", return_value=(notes, None, None, None)),
        ):
            result = process_tja_file(Path("dummy.tja"))

        self.assertEqual(result, "expected_hash")
        fake_parser.hash_note_data.assert_called_once()


if __name__ == "__main__":
    unittest.main()
