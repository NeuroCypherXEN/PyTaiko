import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from libs.video import TEMP_AUDIO_PATH, VideoPlayer, _compute_destination_rect


class TestVideoHelpers(unittest.TestCase):
    def test_compute_destination_rect_letterboxes_wider_texture(self):
        destination = _compute_destination_rect(1920, 1080, 1000, 1000)
        self.assertEqual(destination[0], 0)
        self.assertAlmostEqual(destination[1], 218.75, places=2)
        self.assertEqual(destination[2], 1000)
        self.assertAlmostEqual(destination[3], 562.5, places=2)

    def test_compute_destination_rect_letterboxes_taller_texture(self):
        destination = _compute_destination_rect(1080, 1920, 1000, 500)
        self.assertAlmostEqual(destination[0], 359.375, places=3)
        self.assertEqual(destination[1], 0)
        self.assertAlmostEqual(destination[2], 281.25, places=2)
        self.assertEqual(destination[3], 500)


class TestVideoPlayer(unittest.TestCase):
    @patch('libs.video.av.open')
    @patch('libs.video.ray.LoadTexture')
    def test_static_image_initialization(self, mock_load_texture, mock_av_open):
        texture = Mock()
        mock_load_texture.return_value = texture

        player = VideoPlayer(Path("dummy_image.png"))

        self.assertTrue(player.is_static)
        self.assertIs(player.texture, texture)
        mock_av_open.assert_not_called()

    @patch('libs.video.ray.DrawTexturePro')
    @patch('libs.video.ray.ClearBackground')
    def test_draw_uses_letterboxed_destination(self, mock_clear_background, mock_draw_texture):
        player = VideoPlayer.__new__(VideoPlayer)
        player.texture = Mock(width=1920, height=1080)

        with (
            patch('libs.video.tex.screen_width', 1000),
            patch('libs.video.tex.screen_height', 1000),
        ):
            player.draw()

        mock_clear_background.assert_called_once()
        args = mock_draw_texture.call_args[0]
        destination = args[2]
        self.assertEqual(destination[0], 0)
        self.assertAlmostEqual(destination[1], 218.75, places=2)
        self.assertEqual(destination[2], 1000)
        self.assertAlmostEqual(destination[3], 562.5, places=2)

    def test_stop_removes_temporary_audio_file(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            temp_audio = Path(tmp_dir) / "temp_audio.wav"
            temp_audio.write_bytes(b"audio")

            player = VideoPlayer.__new__(VideoPlayer)
            player.is_static = False
            player.container = Mock()
            player.texture = None
            player.audio = None

            with patch('libs.video.TEMP_AUDIO_PATH', temp_audio):
                player.stop()

            player.container.close.assert_called_once()
            self.assertFalse(temp_audio.exists())

    def test_temp_audio_path_constant(self):
        self.assertIsInstance(TEMP_AUDIO_PATH, Path)


if __name__ == '__main__':
    unittest.main()
