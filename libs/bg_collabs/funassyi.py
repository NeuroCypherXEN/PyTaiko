from libs.bg_objects.bg_fever import BGFeverBase
from libs.bg_objects.bg_normal import BGNormalBase
from libs.bg_objects.chibi import ChibiController
from libs.bg_objects.dancer import BaseDancer, BaseDancerGroup
from libs.bg_objects.don_bg import DonBG4
from libs.bg_objects.renda import RendaController
from libs.bg_objects.fever import Fever0
from libs.bg_objects.footer import Footer
from libs.global_data import PlayerNum
from libs.texture import TextureWrapper


class Background:
    def __init__(self, tex: TextureWrapper, player_num: PlayerNum, bpm: float, path: str, max_dancers: int):
        self.tex_wrapper = tex
        self.max_dancers = max_dancers
        self.don_bg = DonBG4(tex, 0, player_num, path)
        self.bg_normal = BGNormalBase(self.tex_wrapper, 0, path)
        self.bg_fever = BGFever(self.tex_wrapper, 0, path)
        self.footer = Footer(self.tex_wrapper, 2)
        self.fever = Fever0(self.tex_wrapper, 0, bpm)
        self.dancer = DancerGroup(self.tex_wrapper, 0, bpm, max_dancers, path)
        self.renda = RendaController(self.tex_wrapper, 0)
        self.chibi = ChibiController(self.tex_wrapper, 0, bpm, path)

class DancerGroup(BaseDancerGroup):
    def __init__(self, tex: TextureWrapper, index: int, bpm: float, max_dancers: int, path: str):
        self.name = 'dancer_' + str(index)
        self.active_count = 0
        tex.load_zip(path, f'dancer/{self.name}')
        self.spawn_positions = [2, 1, 3, 0, 4]
        self.active_dancers = [None] * max_dancers
        self.dancers = [BaseDancer(self.name, 0, bpm, tex),
                        BaseDancer(self.name, 1, bpm, tex),
                        BaseDancer(self.name, 2, bpm, tex),
                        BaseDancer(self.name, 3, bpm, tex),
                        BaseDancer(self.name, 4, bpm, tex)]
        self.add_dancer()


class BGFever(BGFeverBase):
    def __init__(self, tex: TextureWrapper, index: int, path: str):
        super().__init__(tex, index, path)
        self.horizontal_move = tex.get_animation(16)
        self.bg_texture_move_down = tex.get_animation(17)
        self.bg_texture_move_up = tex.get_animation(18)

    def start(self):
        self.bg_texture_move_down.start()
        self.bg_texture_move_up.start()

    def update(self, current_time_ms: float):
        self.bg_texture_move_down.update(current_time_ms)

        self.bg_texture_move_up.update(current_time_ms)
        if self.bg_texture_move_up.is_finished and not self.transitioned:
            self.transitioned = True
            self.horizontal_move.restart()

        if self.transitioned:
            self.horizontal_move.update(current_time_ms)
    def draw(self, tex: TextureWrapper):
        y = self.bg_texture_move_down.attribute - self.bg_texture_move_up.attribute
        tex.draw_texture(self.name, 'background', y=y)
        tex.draw_texture(self.name, 'overlay', x=-self.horizontal_move.attribute, y=y)
        tex.draw_texture(self.name, 'overlay', x=tex.textures[self.name]['overlay'].width - self.horizontal_move.attribute, y=y)
