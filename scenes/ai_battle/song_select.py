import logging

import pyray as ray

from libs.audio import audio
from libs.chara_2d import Chara2D
from libs.file_navigator import SongFile
from libs.global_data import Difficulty, PlayerNum, global_data
from libs.texture import tex
from libs.utils import (
    is_l_don_pressed,
    is_l_kat_pressed,
    is_r_don_pressed,
    is_r_kat_pressed,
)
from scenes.song_select import (
    ModifierSelector,
    NeiroSelector,
    SongSelectPlayer,
    SongSelectScreen,
    State,
)

logger = logging.getLogger(__name__)

class AISongSelectScreen(SongSelectScreen):
    def on_screen_start(self):
        super().on_screen_start()
        self.player_1 = AISongSelectPlayer(global_data.player_num, self.text_fade_in)
        global_data.modifiers[global_data.player_num].subdiff = 0
        self.ai_chara = Chara2D(PlayerNum.AI-1)

    def update_players(self, current_time) -> str:
        self.player_1.update(current_time)
        self.ai_chara.update(current_time)
        if self.text_fade_out.is_finished:
            self.player_1.selected_song = True
        next_screen = "AI_GAME"
        return next_screen

    def draw_background(self):
        tex.draw_texture('ai_battle', 'background')
        tex.draw_texture('ai_battle', 'background_overlay')
        tex.draw_texture('ai_battle', 'background_overlay_2')

    def draw(self):
        self.draw_background()

        if self.navigator.genre_bg is not None and self.state == State.BROWSING:
            self.navigator.genre_bg.draw(tex.skin_config["boxes"].y)

        self.navigator.draw_boxes(self.move_away.attribute, self.player_1.is_ura, self.diff_fade_out.attribute)

        if self.state == State.BROWSING:
            tex.draw_texture('global', 'arrow', index=0, x=-(self.blue_arrow_move.attribute*2), fade=self.blue_arrow_fade.attribute)
            tex.draw_texture('global', 'arrow', index=1, mirror='horizontal', x=self.blue_arrow_move.attribute*2, fade=self.blue_arrow_fade.attribute)
        tex.draw_texture('global', 'footer')

        self.ura_switch_animation.draw()

        if self.diff_sort_selector is not None:
            self.diff_sort_selector.draw()

        if self.search_box is not None:
            self.search_box.draw()

        if (self.player_1.selected_song and self.state == State.SONG_SELECTED):
            tex.draw_texture('global', 'difficulty_select', fade=self.text_fade_in.attribute)
        elif self.state == State.DIFF_SORTING:
            tex.draw_texture('global', 'difficulty_select', fade=self.text_fade_in.attribute)
        else:
            tex.draw_texture('global', 'song_select', fade=self.text_fade_out.attribute)

        self.draw_players()
        self.ai_chara.draw(x=tex.skin_config["song_select_chara_2p"].x, y=tex.skin_config["song_select_chara_2p"].y, mirror=True)

        if self.state == State.BROWSING and self.navigator.items != []:
            curr_item = self.navigator.get_current_item()
            if isinstance(curr_item, SongFile):
                curr_item.box.draw_score_history()

        if self.player_1.subdiff_selector is not None and self.player_1.subdiff_selector.is_selected:
            ray.draw_rectangle(0, 0, tex.screen_width, tex.screen_height, ray.fade(ray.BLACK, 0.5))
            self.player_1.subdiff_selector.draw()

        self.draw_overlay()

class AISongSelectPlayer(SongSelectPlayer):
    def __init__(self, player_num: PlayerNum, text_fade_in):
        super().__init__(player_num, text_fade_in)
        self.subdiff_selector = None

    def update(self, current_time):
        super().update(current_time)
        if self.subdiff_selector is not None:
            self.subdiff_selector.update(current_time, self.selected_difficulty)

    def on_song_selected(self, selected_song: SongFile):
        """Called when a song is selected"""
        super().on_song_selected(selected_song)
        self.subdiff_selector = SubdiffSelector(self.player_num, min(selected_song.parser.metadata.course_data))

    def handle_input_selected(self, current_item):
        """Handle input for selecting difficulty. Returns 'cancel', 'confirm', or None"""
        if self.neiro_selector is not None:
            if is_l_kat_pressed(self.player_num):
                self.neiro_selector.move_left()
            elif is_r_kat_pressed(self.player_num):
                self.neiro_selector.move_right()
            if is_l_don_pressed(self.player_num) or is_r_don_pressed(self.player_num):
                audio.play_sound('don', 'sound')
                self.neiro_selector.confirm()
            return None

        if self.modifier_selector is not None:
            if is_l_kat_pressed(self.player_num):
                audio.play_sound('kat', 'sound')
                self.modifier_selector.left()
            elif is_r_kat_pressed(self.player_num):
                audio.play_sound('kat', 'sound')
                self.modifier_selector.right()
            if is_l_don_pressed(self.player_num) or is_r_don_pressed(self.player_num):
                audio.play_sound('don', 'sound')
                self.modifier_selector.confirm()
            return None

        if self.subdiff_selector is not None and self.subdiff_selector.is_selected:
            if is_l_kat_pressed(self.player_num):
                audio.play_sound('kat', 'sound')
                self.subdiff_selector.move_left(self.selected_difficulty)
            elif is_r_kat_pressed(self.player_num):
                audio.play_sound('kat', 'sound')
                self.subdiff_selector.move_right(self.selected_difficulty)
            if is_l_don_pressed(self.player_num) or is_r_don_pressed(self.player_num):
                audio.play_sound('don', 'sound')
                self.subdiff_selector.confirm()
                self.is_ready = True
                return "confirm"
            return None

        if is_l_don_pressed(self.player_num) or is_r_don_pressed(self.player_num):
            if self.selected_difficulty == -3:
                self.subdiff_selector = None
                return "cancel"
            elif self.selected_difficulty == -2:
                audio.play_sound('don', 'sound')
                self.modifier_selector = ModifierSelector(self.player_num)
                return None
            elif self.selected_difficulty == -1:
                audio.play_sound('don', 'sound')
                self.neiro_selector = NeiroSelector(self.player_num)
                return None
            else:
                audio.play_sound('don', 'sound')
                if self.subdiff_selector is not None:
                    self.subdiff_selector.is_selected = True

        if is_l_kat_pressed(self.player_num) or is_r_kat_pressed(self.player_num):
            audio.play_sound('kat', 'sound')
            selected_song = current_item
            diffs = sorted(selected_song.parser.metadata.course_data)
            prev_diff = self.selected_difficulty
            ret_val = None

            if is_l_kat_pressed(self.player_num):
                ret_val = self._navigate_difficulty_left(diffs)
            elif is_r_kat_pressed(self.player_num):
                ret_val = self._navigate_difficulty_right(diffs)

            if Difficulty.EASY <= self.selected_difficulty <= Difficulty.URA and self.selected_difficulty != prev_diff:
                self.selected_diff_bounce.start()
                self.selected_diff_fadein.start()


            return ret_val

        if (ray.is_key_pressed(ray.KeyboardKey.KEY_TAB) and
            self.selected_difficulty in [Difficulty.ONI, Difficulty.URA]):
            return self._toggle_ura_mode()

        return None

    def draw(self, state: int, is_half: bool = False):
        if (self.selected_song and state == State.SONG_SELECTED):
            self.draw_selector(is_half)

        offset = 0
        if self.subdiff_selector is not None:
            offset = -self.subdiff_selector.move.attribute*1.05
        self.nameplate.draw(tex.skin_config["song_select_nameplate_1p"].x, tex.skin_config["song_select_nameplate_1p"].y)
        self.chara.draw(x=tex.skin_config["song_select_chara_1p"].x, y=tex.skin_config["song_select_chara_1p"].y + (offset*0.6))

        if self.subdiff_selector is not None:
            self.subdiff_selector.draw()

        if self.neiro_selector is not None:
            self.neiro_selector.draw()

        if self.modifier_selector is not None:
            self.modifier_selector.draw()

class SubdiffSelector:
    def __init__(self, player_num: PlayerNum, lowest_difficulty: int):
        self.player_num = player_num
        self.move = tex.get_animation(28, is_copy=True)
        self.blue_arrow_fade = tex.get_animation(29, is_copy=True)
        self.blue_arrow_move = tex.get_animation(30, is_copy=True)
        self.move.start()
        self.is_selected = False
        self.selected_index = 0
        subdiffs_easy = [('subdiff_easy', 0), ('subdiff_normal', 0), ('subdiff_normal', 1), ('subdiff_normal', 2)]
        subdiffs_normal = [('subdiff_normal', 0), ('subdiff_normal', 1), ('subdiff_normal', 2), ('subdiff_normal', 3)]
        subdiffs_hard = [('subdiff_hard', 0), ('subdiff_hard', 1), ('subdiff_hard', 2), ('subdiff_hard', 3)]
        subdiffs_oni = [('subdiff_oni', 0), ('subdiff_oni', 1), ('subdiff_oni', 2), ('subdiff_oni', 3)]
        self.levels = [
            [1, 2, 3, 4],
            [2, 3, 4, 5],
            [6, 7, 8, 9],
            [10, 11, 12, 13],
            [10, 11, 12, 13]
        ]
        self.selected_level = 1

        self.diff_map = {
            Difficulty.EASY: subdiffs_easy,
            Difficulty.NORMAL: subdiffs_normal,
            Difficulty.HARD: subdiffs_hard,
            Difficulty.ONI: subdiffs_oni,
            Difficulty.URA: subdiffs_oni
        }
        self.selected_subdiff = self.diff_map[Difficulty(lowest_difficulty)]

    def update(self, current_ms: float, current_difficulty: int):
        self.move.update(current_ms)
        if current_difficulty in self.diff_map:
            self.selected_subdiff = self.diff_map[Difficulty(current_difficulty)]

    def move_left(self, difficulty: int):
        self.selected_index = max(0, self.selected_index - 1)
        self.selected_level = self.levels[difficulty][self.selected_index]

    def move_right(self, difficulty: int):
        self.selected_index = min(3, self.selected_index + 1)
        self.selected_level = self.levels[difficulty][self.selected_index]

    def confirm(self):
        global_data.modifiers[self.player_num].subdiff = self.selected_level

    def draw(self):
        y = -self.move.attribute*1.05
        if self.is_selected:
            tex.draw_texture('ai_battle', 'box_bg_blur', y=y)
            tex.draw_texture('ai_battle', 'box_2', y=y)
            tex.draw_texture('ai_battle', 'subdiff_select_text', y=y)
        else:
            tex.draw_texture('ai_battle', 'box_1', y=y)

        tex.draw_texture('ai_battle', 'subdiff_selector', x=self.selected_index*tex.textures['ai_battle']['subdiff_easy'].width, y=y)
        for i, subdiff in enumerate(self.selected_subdiff):
            name, frame = subdiff
            tex.draw_texture('ai_battle', name, frame=frame, x=i*tex.textures['ai_battle'][name].width, y=y)

        tex.draw_texture('ai_battle', 'bottom_text', y=y)
