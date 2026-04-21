import logging
import random

import libs.bg_collabs
from libs.bg_objects.bg_fever import BGFever
from libs.bg_objects.bg_normal import BGNormal
from libs.bg_objects.chibi import ChibiController
from libs.bg_objects.dancer import Dancer
from libs.bg_objects.don_bg import DonBG
from libs.bg_objects.fever import Fever
from libs.bg_objects.footer import Footer
from libs.bg_objects.renda import RendaController
from libs.global_data import Difficulty, PlayerNum
from libs.texture import TextureWrapper

logger = logging.getLogger(__name__)


class Background:
    """The background class for the game."""
    COLLABS = {
        "A3": (libs.bg_collabs.a3.Background, 'background/collab/a3', 4),
        "ANIMAL": (libs.bg_collabs.animal.Background, 'background/collab/animal', 5),
        "BUTTOBURST": (libs.bg_collabs.buttoburst.Background, 'background/collab/buttoburst', 4),
        "OSHIRI": (libs.bg_collabs.oshiri.Background, 'background/collab/oshiri', 5),
        "IMAS": (libs.bg_collabs.imas.Background, 'background/collab/imas', 5),
        "IMAS_CG": (libs.bg_collabs.imas.Background, 'background/collab/imas_cg', 3),
        "IMAS_ML": (libs.bg_collabs.imas.Background, 'background/collab/imas_ml', 3),
        "IMAS_SIDEM": (libs.bg_collabs.imas_sidem.Background, 'background/collab/imas_sidem', 3),
        "FUNASSYI": (libs.bg_collabs.funassyi.Background, 'background/collab/funassyi', 5),
        "DAN": (libs.bg_collabs.dan.Background, 'background/collab/dan', 1),
        "PRACTICE": (libs.bg_collabs.practice.Background, 'background/collab/practice', 1)
    }

    def _set_shared_none_components(self) -> None:
        self.bg_normal = None
        self.bg_fever = None
        self.footer = None
        self.fever = None
        self.dancer = None

    def _init_two_player_default(self, bpm: float) -> None:
        self.max_dancers = 5
        don_bg_num = random.randint(0, 5)
        self.don_bg = DonBG.create(self.tex_wrapper, don_bg_num, PlayerNum.P1)
        self.don_bg_2 = DonBG.create(self.tex_wrapper, don_bg_num, PlayerNum.P2)
        self.renda = RendaController(self.tex_wrapper, random.randint(0, 2))
        self.chibi = ChibiController(self.tex_wrapper, random.randint(0, 13), bpm)
        self._set_shared_none_components()

    def _init_single_default(self, player_num: PlayerNum, bpm: float) -> None:
        self.max_dancers = 5
        self.don_bg = DonBG.create(self.tex_wrapper, random.randint(0, 5), player_num)
        self.don_bg_2 = None
        self.bg_normal = BGNormal.create(self.tex_wrapper, random.randint(0, 4))
        self.bg_fever = BGFever.create(self.tex_wrapper, random.randint(0, 3))
        self.footer = Footer(self.tex_wrapper, random.randint(0, 2))
        self.fever = Fever.create(self.tex_wrapper, random.randint(0, 3), bpm)
        self.dancer = Dancer.create(self.tex_wrapper, random.randint(0, 20), bpm)
        self.renda = RendaController(self.tex_wrapper, random.randint(0, 2))
        self.chibi = ChibiController(self.tex_wrapper, random.randint(0, 13), bpm)

    def _init_collab(self, scene_preset: str, bpm: float, is_two_player: bool) -> None:
        bg_obj, path, max_dancers = Background.COLLABS[scene_preset]
        collab_bg = bg_obj(self.tex_wrapper, PlayerNum.P1, bpm, path, max_dancers)
        self.max_dancers = max_dancers
        self.don_bg = collab_bg.don_bg
        self.don_bg_2 = collab_bg.don_bg if is_two_player else None
        if is_two_player:
            self._set_shared_none_components()
        else:
            self.bg_normal = collab_bg.bg_normal
            self.bg_fever = collab_bg.bg_fever
            self.footer = collab_bg.footer
            self.fever = collab_bg.fever
            self.dancer = collab_bg.dancer
        self.renda = collab_bg.renda
        self.chibi = collab_bg.chibi

    def __init__(self, player_num: PlayerNum, bpm: float, scene_preset: str = ''):
        """
        Initialize the background class.

        Args:
            player_num (int): The player number.
            bpm (float): The beats per minute.
            scene_preset (str): The scene preset.
        """
        self.tex_wrapper = TextureWrapper()
        self.tex_wrapper.load_animations('background')
        if player_num == PlayerNum.TWO_PLAYER:
            if scene_preset == '':
                self._init_two_player_default(bpm)
            else:
                self._init_collab(scene_preset, bpm, is_two_player=True)
        elif scene_preset == '':
            self._init_single_default(player_num, bpm)
        else:
            self._init_collab(scene_preset, bpm, is_two_player=False)
        self.is_clear = False
        self.is_rainbow = False
        self.last_milestone = 1
        logger.info(f"Background initialized for player {player_num}, bpm={bpm}, scene_preset={scene_preset}")

    def add_chibi(self, bad: bool, player_num: int):
        """
        Add a chibi to the background.

        Args:
            player_num (int): The player number.
            bad (bool): Whether the chibi is bad.
        """
        if self.chibi is not None:
            self.chibi.add_chibi(player_num, bad)

    def add_renda(self):
        """
        Add a renda to the background.
        """
        if self.renda is not None:
            self.renda.add_renda()

    def update(self, current_time_ms: float, bpm: float, gauge_1p=None, gauge_2p=None):
        """
        Update the background.

        Args:
            current_time_ms (float): The current time in milliseconds.
            bpm (float): The beats per minute.
            gauge_1p (Gauge): The gauge object for player 1.
            gauge_2p (Gauge): The gauge object for player 2.
        """
        if self.dancer is not None and gauge_1p is not None:
            clear_threshold = gauge_1p.clear_start[min(gauge_1p.difficulty, Difficulty.ONI)]
            if gauge_1p.gauge_length < clear_threshold:
                current_milestone = min(self.max_dancers - 1,
                                        int(gauge_1p.gauge_length / (clear_threshold / self.max_dancers)))
            else:
                current_milestone = self.max_dancers

            if current_milestone > self.last_milestone and current_milestone <= self.max_dancers:
                self.dancer.add_dancer()
                self.last_milestone = current_milestone
                logger.info(f"Dancer milestone reached: {current_milestone}/{self.max_dancers}")
            elif current_milestone < self.last_milestone:
                dancers_to_remove = self.last_milestone - current_milestone
                for _ in range(dancers_to_remove):
                    self.dancer.remove_dancer()
                self.last_milestone = current_milestone
                logger.info(
                    f"Dancer milestones lost: {current_milestone}/{self.max_dancers} (removed {dancers_to_remove})")
        if self.bg_fever is not None and gauge_1p is not None:
            if not self.is_clear and gauge_1p.is_clear:
                self.bg_fever.start()
                logger.info("Fever started")
            if not self.is_rainbow and gauge_1p.is_rainbow and self.fever is not None:
                self.fever.start()
                logger.info("Rainbow fever started")
        if gauge_1p is not None:
            self.is_clear = gauge_1p.is_clear
            self.is_rainbow = gauge_1p.is_rainbow
        self.don_bg.update(current_time_ms, self.is_clear)
        if self.don_bg_2 is not None and gauge_2p is not None:
            self.don_bg_2.update(current_time_ms, gauge_2p.is_clear)
        if self.bg_normal is not None:
            self.bg_normal.update(current_time_ms)
        if self.bg_fever is not None:
            self.bg_fever.update(current_time_ms)
        if self.fever is not None:
            self.fever.update(current_time_ms, bpm)
        if self.dancer is not None:
            self.dancer.update(current_time_ms, bpm)
        if self.renda is not None:
            self.renda.update(current_time_ms)
        if self.chibi is not None:
            self.chibi.update(current_time_ms, bpm)

    def draw(self):
        """
        Draw the background.
        """
        if self.bg_normal is not None:
            if self.bg_fever is not None:
                if self.is_clear and not self.bg_fever.transitioned:
                    self.bg_normal.draw(self.tex_wrapper)
                    self.bg_fever.draw(self.tex_wrapper)
                elif self.is_clear:
                    self.bg_fever.draw(self.tex_wrapper)
                else:
                    self.bg_normal.draw(self.tex_wrapper)
            else:
                self.bg_normal.draw(self.tex_wrapper)
        self.don_bg.draw(self.tex_wrapper)
        if self.don_bg_2 is not None:
            self.don_bg_2.draw(self.tex_wrapper, y=self.tex_wrapper.skin_config["game_2p_offset"].y)
        if self.renda is not None:
            self.renda.draw()
        if self.dancer is not None:
            self.dancer.draw(self.tex_wrapper)
        if self.footer is not None:
            self.footer.draw(self.tex_wrapper)
        if self.is_rainbow and self.fever is not None:
            self.fever.draw(self.tex_wrapper)
        if self.chibi is not None:
            self.chibi.draw()

    def unload(self):
        """
        Unload the background.
        """
        self.tex_wrapper.unload_textures()
        logger.info("Background textures unloaded")
