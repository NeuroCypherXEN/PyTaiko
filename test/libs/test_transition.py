import unittest
from unittest.mock import Mock, patch

from libs.transition import Transition


def _make_animation(attribute=0.0, is_finished=False):
    return Mock(attribute=attribute, is_finished=is_finished, start=Mock(), update=Mock())


class DummyOutlinedText:
    def __init__(self, *_args, **_kwargs):
        self.texture = Mock(width=100, height=20)
        self.draw = Mock()


class TestTransition(unittest.TestCase):
    @patch('libs.transition.global_tex')
    def test_start_and_update_forward_to_all_animations(self, mock_global_tex):
        animations = [
            _make_animation(attribute=1.0),
            _make_animation(attribute=2.0),
            _make_animation(attribute=3.0),
            _make_animation(attribute=0.4, is_finished=True),
            _make_animation(attribute=0.6),
        ]
        mock_global_tex.get_animation.side_effect = animations
        mock_global_tex.skin_config = {
            'transition_title': Mock(font_size=20, y=100),
            'transition_subtitle': Mock(font_size=16, y=120),
            'transition_offset': Mock(y=30),
            'transition_chara_offset': Mock(y=10),
        }

        with patch('libs.transition.OutlinedText', DummyOutlinedText):
            transition = Transition("Title", "Subtitle")
        transition.start()
        transition.update(1234.0)

        for animation in animations:
            animation.start.assert_called_once()
            animation.update.assert_called_once_with(1234.0)
        self.assertTrue(transition.is_finished)

    @patch('libs.transition.global_tex')
    def test_draw_without_song_info_only_draws_background_layers(self, mock_global_tex):
        mock_global_tex.get_animation.side_effect = [
            _make_animation(attribute=10.0),
            _make_animation(attribute=6.0),
            _make_animation(attribute=4.0),
            _make_animation(attribute=0.8),
            _make_animation(attribute=0.2),
        ]
        mock_global_tex.skin_config = {
            'transition_offset': Mock(y=30),
            'transition_chara_offset': Mock(y=10),
        }
        mock_global_tex.draw_texture = Mock()

        transition = Transition("", "")
        transition.draw()

        self.assertEqual(mock_global_tex.draw_texture.call_count, 3)

    @patch('libs.transition.global_tex')
    def test_draw_with_song_info_draws_characters_and_text(self, mock_global_tex):
        mock_global_tex.screen_width = 1280
        mock_global_tex.get_animation.side_effect = [
            _make_animation(attribute=10.0),
            _make_animation(attribute=6.0),
            _make_animation(attribute=4.0),
            _make_animation(attribute=0.8),
            _make_animation(attribute=0.2),
        ]
        mock_global_tex.skin_config = {
            'transition_title': Mock(font_size=20, y=100),
            'transition_subtitle': Mock(font_size=16, y=140),
            'transition_offset': Mock(y=30),
            'transition_chara_offset': Mock(y=10),
        }
        mock_global_tex.draw_texture = Mock()

        with patch('libs.transition.OutlinedText', DummyOutlinedText):
            transition = Transition("Title", "Subtitle")
            transition.draw()

            self.assertGreaterEqual(mock_global_tex.draw_texture.call_count, 7)
            transition.title.draw.assert_called_once()
            transition.subtitle.draw.assert_called_once()


if __name__ == '__main__':
    unittest.main()
