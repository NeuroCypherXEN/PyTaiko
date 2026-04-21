import unittest
from unittest.mock import Mock, patch

from libs.background import Background
from libs.global_data import Difficulty, PlayerNum


class TestBackgroundInitialization(unittest.TestCase):
    @patch('libs.background.random.randint', side_effect=[4, 1, 7])
    @patch('libs.background.ChibiController')
    @patch('libs.background.RendaController')
    @patch('libs.background.DonBG')
    @patch('libs.background.TextureWrapper')
    def test_two_player_default_initialization(
        self,
        mock_texture_wrapper,
        mock_don_bg,
        mock_renda_controller,
        mock_chibi_controller,
        _mock_randint,
    ):
        wrapper = Mock()
        mock_texture_wrapper.return_value = wrapper
        don_bg_1 = Mock()
        don_bg_2 = Mock()
        mock_don_bg.create.side_effect = [don_bg_1, don_bg_2]
        renda = Mock()
        chibi = Mock()
        mock_renda_controller.return_value = renda
        mock_chibi_controller.return_value = chibi

        background = Background(PlayerNum.TWO_PLAYER, 120.0, '')

        wrapper.load_animations.assert_called_once_with('background')
        mock_don_bg.create.assert_any_call(wrapper, 4, PlayerNum.P1)
        mock_don_bg.create.assert_any_call(wrapper, 4, PlayerNum.P2)
        self.assertIs(background.don_bg, don_bg_1)
        self.assertIs(background.don_bg_2, don_bg_2)
        self.assertIsNone(background.bg_normal)
        self.assertIsNone(background.bg_fever)
        self.assertIsNone(background.footer)
        self.assertIsNone(background.fever)
        self.assertIsNone(background.dancer)
        self.assertIs(background.renda, renda)
        self.assertIs(background.chibi, chibi)
        self.assertEqual(background.max_dancers, 5)

    @patch('libs.background.TextureWrapper')
    def test_single_player_collab_initialization(self, mock_texture_wrapper):
        wrapper = Mock()
        mock_texture_wrapper.return_value = wrapper
        collab_bg = Mock(
            don_bg=Mock(),
            bg_normal=Mock(),
            bg_fever=Mock(),
            footer=Mock(),
            fever=Mock(),
            dancer=Mock(),
            renda=Mock(),
            chibi=Mock(),
        )
        collab_factory = Mock(return_value=collab_bg)

        with patch.dict(Background.COLLABS, {"TEST": (collab_factory, "background/collab/test", 3)}, clear=False):
            background = Background(PlayerNum.P1, 150.0, "TEST")

        collab_factory.assert_called_once_with(wrapper, PlayerNum.P1, 150.0, "background/collab/test", 3)
        self.assertEqual(background.max_dancers, 3)
        self.assertIs(background.don_bg, collab_bg.don_bg)
        self.assertIsNone(background.don_bg_2)
        self.assertIs(background.bg_normal, collab_bg.bg_normal)
        self.assertIs(background.bg_fever, collab_bg.bg_fever)
        self.assertIs(background.footer, collab_bg.footer)
        self.assertIs(background.fever, collab_bg.fever)
        self.assertIs(background.dancer, collab_bg.dancer)
        self.assertIs(background.renda, collab_bg.renda)
        self.assertIs(background.chibi, collab_bg.chibi)


class TestBackgroundUpdate(unittest.TestCase):
    def test_update_handles_dancer_milestones_and_fever_flags(self):
        background = Background.__new__(Background)
        background.max_dancers = 5
        background.last_milestone = 1
        background.is_clear = False
        background.is_rainbow = False
        background.don_bg = Mock()
        background.don_bg_2 = None
        background.bg_normal = None
        background.bg_fever = Mock(start=Mock(), update=Mock(), transitioned=False)
        background.footer = None
        background.fever = Mock(start=Mock(), update=Mock())
        background.dancer = Mock(add_dancer=Mock(), remove_dancer=Mock(), update=Mock())
        background.renda = None
        background.chibi = None

        gauge_high = Mock(
            clear_start=[0.3, 0.4, 0.6, 0.8, 1.0],
            difficulty=Difficulty.HARD,
            gauge_length=0.5,
            is_clear=True,
            is_rainbow=True,
        )
        gauge_low = Mock(
            clear_start=[0.3, 0.4, 0.6, 0.8, 1.0],
            difficulty=Difficulty.HARD,
            gauge_length=0.1,
            is_clear=False,
            is_rainbow=False,
        )

        background.update(1000.0, 140.0, gauge_high)
        background.update(2000.0, 140.0, gauge_low)

        background.bg_fever.start.assert_called_once()
        background.fever.start.assert_called_once()
        background.dancer.add_dancer.assert_called_once()
        background.dancer.remove_dancer.assert_called()
        background.don_bg.update.assert_called()


if __name__ == '__main__':
    unittest.main()
