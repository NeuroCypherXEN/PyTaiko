import copy
import logging
import random
import time
from enum import Enum
from pathlib import Path
from typing import Optional

import pyray as ray

from libs.animation import Animation
from libs.audio import audio
from libs.background import Background
from libs.chara_2d import Chara2D
from libs.global_data import Difficulty, Modifiers, PlayerNum, global_data
from libs.global_objects import Nameplate
from libs.texture import tex
from libs.parsers.tja import TJAParser
from libs.utils import get_current_ms, global_tex
from scenes.game import (
    DrumType,
    GameScreen,
    Gauge,
    Player,
    Side,
    SongInfo,
)

logger = logging.getLogger(__name__)

class AIDifficulty(Enum):
    LVL_1 = (0.90, 0.10)
    LVL_2 = (0.92, 0.08)
    LVL_3 = (0.94, 0.06)
    LVL_4 = (0.96, 0.04)
    LVL_5 = (0.98, 0.02)

    def __iter__(self):
        return iter(self.value)

class AIBattleGameScreen(GameScreen):
    def on_screen_start(self):
        super().on_screen_start()
        session_data = global_data.session_data[global_data.player_num]
        self.song_info = SongInfoAI(session_data.song_title, session_data.genre_index)
        self.background = AIBackground(session_data.selected_difficulty)
        self.section_board = SectionBoard()

    def global_keys(self):
        if ray.is_key_pressed(global_data.config["keys"]["restart_key"]):
            if self.song_music is not None:
                audio.stop_music_stream(self.song_music)
            self.init_tja(global_data.session_data[global_data.player_num].selected_song)
            audio.play_sound('restart', 'sound')
            self.song_started = False

        if ray.is_key_pressed(global_data.config["keys"]["back_key"]):
            if self.song_music is not None:
                audio.stop_music_stream(self.song_music)
            return self.on_screen_end('AI_SELECT')

        if ray.is_key_pressed(global_data.config["keys"]["pause_key"]):
            self.pause_song()

    def load_hitsounds(self):
        """Load the hit sounds"""
        sounds_dir = Path(f"Skins/{global_data.config["paths"]["skin"]}/Sounds")

        # Load hitsounds for 1P
        if global_data.hit_sound[global_data.player_num] == -1:
            audio.load_sound(Path('none.wav'), 'hitsound_don_1p')
            audio.load_sound(Path('none.wav'), 'hitsound_kat_1p')
            logger.info("Loaded default (none) hit sounds for 1P")
        elif global_data.hit_sound[global_data.player_num] == 0:
            audio.load_sound(sounds_dir / "hit_sounds" / str(global_data.hit_sound[global_data.player_num]) / "don.wav", 'hitsound_don_1p')
            audio.load_sound(sounds_dir / "hit_sounds" / str(global_data.hit_sound[global_data.player_num]) / "ka.wav", 'hitsound_kat_1p')
            logger.info("Loaded wav hit sounds for 1P")
        else:
            audio.load_sound(sounds_dir / "hit_sounds" / str(global_data.hit_sound[global_data.player_num]) / "don.ogg", 'hitsound_don_1p')
            audio.load_sound(sounds_dir / "hit_sounds" / str(global_data.hit_sound[global_data.player_num]) / "ka.ogg", 'hitsound_kat_1p')
            logger.info("Loaded ogg hit sounds for 1P")
        audio.set_sound_pan('hitsound_don_1p', 0.0)
        audio.set_sound_pan('hitsound_kat_1p', 0.0)

        # Load hitsounds for 2P
        if global_data.hit_sound[global_data.player_num] == -1:
            audio.load_sound(Path('none.wav'), 'hitsound_don_5p')
            audio.load_sound(Path('none.wav'), 'hitsound_kat_5p')
            logger.info("Loaded default (none) hit sounds for 5P")
        elif global_data.hit_sound[global_data.player_num] == 0:
            audio.load_sound(sounds_dir / "hit_sounds" / str(global_data.hit_sound[global_data.player_num]) / "don_2p.wav", 'hitsound_don_5p')
            audio.load_sound(sounds_dir / "hit_sounds" / str(global_data.hit_sound[global_data.player_num]) / "ka_2p.wav", 'hitsound_kat_5p')
            logger.info("Loaded wav hit sounds for 5P")
        else:
            audio.load_sound(sounds_dir / "hit_sounds" / str(global_data.hit_sound[global_data.player_num]) / "don.ogg", 'hitsound_don_5p')
            audio.load_sound(sounds_dir / "hit_sounds" / str(global_data.hit_sound[global_data.player_num]) / "ka.ogg", 'hitsound_kat_5p')
            logger.info("Loaded ogg hit sounds for 5P")
        audio.set_sound_pan('hitsound_don_5p', 1.0)
        audio.set_sound_pan('hitsound_kat_5p', 1.0)

    def init_tja(self, song: Path):
        """Initialize the TJA file"""
        self.tja = TJAParser(song, start_delay=self.start_delay)
        self.movie = None
        session_data = global_data.session_data[global_data.player_num]
        session_data.song_title = self.tja.metadata.title.get(global_data.config['general']['language'].lower(), self.tja.metadata.title['en'])
        if self.tja.metadata.wave.exists() and self.tja.metadata.wave.is_file() and self.song_music is None:
            self.song_music = audio.load_music_stream(self.tja.metadata.wave, 'song')

        tja_copy = copy.deepcopy(self.tja)
        self.player_1 = PlayerNoChara(self.tja, global_data.player_num, session_data.selected_difficulty, False, global_data.modifiers[global_data.player_num])
        self.player_1.gauge = AIGauge(self.player_1.player_num, self.player_1.difficulty, self.tja.metadata.course_data[self.player_1.difficulty].level, self.player_1.total_notes, self.player_1.is_2p)
        ai_modifiers = copy.deepcopy(global_data.modifiers[global_data.player_num])
        ai_modifiers.auto = True
        self.player_2 = AIPlayer(tja_copy, PlayerNum.AI, session_data.selected_difficulty, True, ai_modifiers, AIDifficulty.LVL_2)
        self.start_ms = (get_current_ms() - self.tja.metadata.offset*1000)
        self.precise_start = time.time() - self.tja.metadata.offset
        self.total_notes = len(self.player_1.don_notes) + len(self.player_1.kat_notes)
        logger.info(f"TJA initialized for two-player song: {song}")

    def update_scoreboards(self):
        section_notes = (self.total_notes // 5) if self.section_board.num < 3 else (self.total_notes // 5) + (self.total_notes % 5) - 1
        if self.player_1.good_count + self.player_1.ok_count + self.player_1.bad_count == section_notes:
            self.player_2.good_percentage = self.player_1.good_count / section_notes
            self.player_2.ok_percentage = self.player_1.ok_count / section_notes
            logger.info(f"AI Good Percentage: {self.player_2.good_percentage}, AI OK Percentage: {self.player_2.ok_percentage}")
            self.player_1.good_count, self.player_1.ok_count, self.player_1.bad_count = 0, 0, 0
            self.player_2.good_count, self.player_2.ok_count, self.player_2.bad_count = 0, 0, 0
            if self.background.contest_point >= 10:
                self.section_board.wins[self.section_board.num] = True
            else:
                self.section_board.wins[self.section_board.num] = False
            self.section_board.num += 1

    def update(self):
        super(GameScreen, self).update()
        current_time = get_current_ms()
        self.transition.update(current_time)
        self.current_ms = current_time - self.start_ms
        if self.transition.is_finished:
            self.start_song(self.current_ms)
        else:
            self.start_ms = current_time - self.tja.metadata.offset*1000
        self.update_background(current_time)

        self.update_audio(self.current_ms)

        self.player_1.update(self.current_ms, current_time, None)
        self.player_2.update(self.current_ms, current_time, None)
        self.update_scoreboards()
        self.section_board.update(current_time, self.player_1.good_count + self.player_1.ok_count + self.player_1.bad_count, self.total_notes)

        self.song_info.update(current_time)
        self.result_transition.update(current_time)
        if self.result_transition.is_finished and not audio.is_sound_playing('result_transition'):
            return self.on_screen_end('AI_SELECT')
        elif self.current_ms >= self.player_1.end_time:
            session_data = global_data.session_data[PlayerNum.P1]
            session_data.result_data.score, session_data.result_data.good, session_data.result_data.ok, session_data.result_data.bad, session_data.result_data.max_combo, session_data.result_data.total_drumroll = self.player_1.get_result_score()
            session_data.result_data.gauge_length = int(self.player_1.gauge.gauge_length)
            if self.end_ms != 0:
                if current_time >= self.end_ms + 1000:
                    if self.player_1.ending_anim is None:
                        self.spawn_ending_anims()
                        if self.player_1.modifiers.subdiff in [0, 1, 2, 3, 4, 5, 9, 13]:
                            self.write_score()
                if current_time >= self.end_ms + 8533.34:
                    if not self.result_transition.is_started:
                        self.result_transition.start()
                        audio.play_sound('result_transition', 'voice')
            else:
                self.end_ms = current_time

        return self.global_keys()

    def update_background(self, current_time):
        if self.player_1.don_notes == self.player_2.don_notes and self.player_1.kat_notes == self.player_2.kat_notes:
            self.background.update_values((self.player_1.good_count, self.player_1.ok_count), (self.player_2.good_count, self.player_2.ok_count))
        self.background.update(current_time)

    def draw(self):
        if self.movie is not None:
            self.movie.draw()
        elif self.background is not None:
            self.background.draw(self.player_1.chara, self.player_2.chara)
        self.section_board.draw()
        self.player_1.draw(self.current_ms, self.start_ms, self.mask_shader)
        self.player_2.draw(self.current_ms, self.start_ms, self.mask_shader)
        self.draw_overlay()

class SectionBoard:
    def __init__(self):
        self.num = 0
        self.wins: list[Optional[bool]] = [None] * 5
        self.current_progress = 0
        self.progress_bar_flash = Animation.create_fade(133, loop=True, reverse_delay=0)
        self.section_highlight_flash = Animation.create_fade(350, loop=True, reverse_delay=0)
        self.section_highlight_flash.start()
        self.progress_bar_flash.start()

    def update(self, current_time, player_notes, total_notes):
        self.current_progress = player_notes / (total_notes // 5) if self.num < 3 else player_notes / ((total_notes // 5) + (total_notes % 5))
        self.progress_bar_flash.update(current_time)
        self.section_highlight_flash.update(current_time)

    def draw(self):
        if self.current_progress < 0.75:
            color = ray.GREEN
            fade = 1.0
        else:
            color = ray.YELLOW
            fade = self.progress_bar_flash.attribute
        ray.draw_rectangle(int(177 * tex.screen_scale), int(160 * tex.screen_scale), int(148 * tex.screen_scale), int(20 * tex.screen_scale), ray.GRAY)
        ray.draw_rectangle(int(177 * tex.screen_scale), int(160 * tex.screen_scale), int(self.current_progress * (148 * tex.screen_scale)), int(20 * tex.screen_scale), ray.fade(color, fade))
        tex.draw_texture('ai_battle', 'progress_bar')
        if self.num < len(self.wins):
            tex.draw_texture('ai_battle', 'section_text', index=0, frame=self.num)
        if self.num < len(self.wins) - 1:
            tex.draw_texture('ai_battle', 'section_text', index=1, frame=self.num+1)

        tex.draw_texture('ai_battle', 'sections')
        if self.num < len(self.wins):
            tex.draw_texture('ai_battle', 'section_highlight_green', index=self.num)
            tex.draw_texture('ai_battle', 'section_highlight_white', index=self.num, fade=self.section_highlight_flash.attribute)

        for i in range(len(self.wins)):
            if self.wins[i] is not None:
                if self.wins[i]:
                    tex.draw_texture('ai_battle', 'section_win', index=i)
                else:
                    tex.draw_texture('ai_battle', 'section_lose', index=i)


class PlayerNoChara(Player):
    def __init__(self, tja: TJAParser, player_num: PlayerNum, difficulty: int, is_2p: bool, modifiers: Modifiers):
        super().__init__(tja, player_num, difficulty, is_2p, modifiers)
        self.stretch_animation = [tex.get_animation(5, is_copy=True) for _ in range(4)]

    def update(self, ms_from_start: float, current_time: float, background: Optional[Background]):
        good_count, ok_count, bad_count, total_drumroll = self.good_count, self.ok_count, self.bad_count, self.total_drumroll
        super().update(ms_from_start, current_time, background)
        for ani in self.stretch_animation:
            ani.update(current_time)
        if good_count != self.good_count:
            self.stretch_animation[0].start()
        if ok_count != self.ok_count:
            self.stretch_animation[1].start()
        if bad_count != self.bad_count:
            self.stretch_animation[2].start()
        if total_drumroll != self.total_drumroll:
            self.stretch_animation[3].start()

    def draw_overlays(self, mask_shader: ray.Shader):
        tex.draw_texture('lane', f'{self.player_num}p_lane_cover', index=self.is_2p)
        tex.draw_texture('lane', 'drum', index=self.is_2p)
        if self.ending_anim is not None:
            self.ending_anim.draw()

        for anim in self.draw_drum_hit_list:
            anim.draw()
        for anim in self.draw_arc_list:
            anim.draw(mask_shader)

        # Group 6: UI overlays
        self.combo_display.draw()
        tex.draw_texture('lane', 'lane_score_cover', index=self.is_2p)
        tex.draw_texture('lane', f'{self.player_num}p_icon', index=self.is_2p)
        tex.draw_texture('lane', 'lane_difficulty', frame=self.difficulty, index=self.is_2p)

        # Group 7: Player-specific elements
        if self.modifiers.auto:
            tex.draw_texture('lane', 'auto_icon', index=self.is_2p)
        else:
            if self.is_2p:
                self.nameplate.draw(tex.skin_config["game_nameplate_1p"].x, tex.skin_config["game_nameplate_1p"].y)
            else:
                self.nameplate.draw(tex.skin_config["game_nameplate_2p"].x, tex.skin_config["game_nameplate_2p"].y)
        self.draw_modifiers()

        tex.draw_texture('ai_battle', 'scoreboard')
        for j, counter in enumerate([self.good_count, self.ok_count, self.bad_count, self.total_drumroll]):
            margin = tex.textures["ai_battle"]["scoreboard_num"].width//2
            total_width = len(str(counter)) * margin
            for i, digit in enumerate(str(counter)):
                tex.draw_texture('ai_battle', 'scoreboard_num', frame=int(digit), x=-(total_width // 2) + (i * margin), y=-self.stretch_animation[j].attribute, y2=self.stretch_animation[j].attribute, index=j)

        # Group 8: Special animations and counters
        if self.drumroll_counter is not None:
            self.drumroll_counter.draw()
        if self.balloon_anim is not None:
            self.balloon_anim.draw()
        if self.kusudama_anim is not None:
            self.kusudama_anim.draw()
        self.score_counter.draw()
        for anim in self.base_score_list:
            anim.draw()


class AIPlayer(Player):
    def __init__(self, tja: TJAParser, player_num: PlayerNum, difficulty: int, is_2p: bool, modifiers: Modifiers, ai_difficulty: AIDifficulty):
        super().__init__(tja, player_num, difficulty, is_2p, modifiers)
        self.stretch_animation = [tex.get_animation(5, is_copy=True) for _ in range(4)]
        self.chara = Chara2D(player_num - 1, self.bpm)
        self.judge_counter = None
        self.gauge = None
        self.gauge_hit_effect = []
        plate_info = global_data.config[f'nameplate_{self.is_2p+1}p']
        self.nameplate = Nameplate(plate_info['name'], plate_info['title'], PlayerNum.AI, plate_info['dan'], plate_info['gold'], plate_info['rainbow'], plate_info['title_bg'])
        self.good_percentage, self.ok_percentage = ai_difficulty

    def update(self, ms_from_start: float, current_time: float, background: Optional[Background]):
        good_count, ok_count, bad_count, total_drumroll = self.good_count, self.ok_count, self.bad_count, self.total_drumroll
        super().update(ms_from_start, current_time, background)
        for ani in self.stretch_animation:
            ani.update(current_time)
        if good_count != self.good_count:
            self.stretch_animation[0].start()
        if ok_count != self.ok_count:
            self.stretch_animation[1].start()
        if bad_count != self.bad_count:
            self.stretch_animation[2].start()
        if total_drumroll != self.total_drumroll:
            self.stretch_animation[3].start()

    def autoplay_manager(self, ms_from_start: float, current_time: float, background: Optional[Background]):
        """Manages autoplay behavior with randomized accuracy"""
        if not self.modifiers.auto:
            return

        if self.is_drumroll or self.is_balloon:
            if self.bpm == 0:
                subdivision_in_ms = 0
            else:
                subdivision_in_ms = ms_from_start // ((60000 * 4 / self.bpm) / 24)
            if subdivision_in_ms > self.last_subdivision:
                self.last_subdivision = subdivision_in_ms
                hit_type = DrumType.DON
                self.autoplay_hit_side = Side.RIGHT if self.autoplay_hit_side == Side.LEFT else Side.LEFT
                self.spawn_hit_effects(hit_type, self.autoplay_hit_side)
                audio.play_sound(f'hitsound_don_{self.player_num}p', 'hitsound')
                self.check_note(ms_from_start, hit_type, current_time, background)
        else:
            if self.difficulty < Difficulty.NORMAL:
                good_window_ms = Player.TIMING_GOOD_EASY
                ok_window_ms = Player.TIMING_OK_EASY
                bad_window_ms = Player.TIMING_BAD_EASY
            else:
                good_window_ms = Player.TIMING_GOOD
                ok_window_ms = Player.TIMING_OK
                bad_window_ms = Player.TIMING_BAD

            self._adjust_timing(self.don_notes, DrumType.DON, 'don',
                                         ms_from_start, current_time, background,
                                         good_window_ms, ok_window_ms, bad_window_ms)
            self._adjust_timing(self.kat_notes, DrumType.KAT, 'kat',
                                         ms_from_start, current_time, background,
                                         good_window_ms, ok_window_ms, bad_window_ms)

    def _adjust_timing(self, notes, hit_type, sound_type, ms_from_start,
                                current_time, background, good_window_ms, ok_window_ms, bad_window_ms):
        """Process autoplay for a specific note type"""
        while notes and ms_from_start >= notes[0].hit_ms:
            note = notes[0]
            rand = random.random()
            if rand < (self.good_percentage):
                timing_offset = random.uniform(-good_window_ms * 0.5, good_window_ms * 0.5)
            elif rand < (self.good_percentage + self.ok_percentage):
                timing_offset = random.choice([
                    random.uniform(-ok_window_ms, -good_window_ms),
                    random.uniform(good_window_ms, ok_window_ms)
                ])
            else:
                timing_offset = random.choice([
                    random.uniform(-bad_window_ms * 1.5, -bad_window_ms),
                    random.uniform(bad_window_ms, bad_window_ms * 1.5)
                ])
            adjusted_ms = note.hit_ms + timing_offset
            self.autoplay_hit_side = Side.RIGHT if self.autoplay_hit_side == Side.LEFT else Side.LEFT
            self.spawn_hit_effects(hit_type, self.autoplay_hit_side)
            audio.play_sound(f'hitsound_{sound_type}_{self.player_num}p', 'hitsound')
            self.check_note(adjusted_ms, hit_type, current_time, background)

    def draw_overlays(self, mask_shader: ray.Shader):
        # Group 4: Lane covers and UI elements (batch similar textures)
        tex.draw_texture('lane', 'ai_lane_cover')
        tex.draw_texture('lane', 'drum', index=self.is_2p)
        if self.ending_anim is not None:
            self.ending_anim.draw()

        # Group 5: Hit effects and animations
        for anim in self.draw_drum_hit_list:
            anim.draw()
        for anim in self.draw_arc_list:
            anim.draw(mask_shader)

        # Group 6: UI overlays
        self.combo_display.draw()
        if self.judge_counter is not None:
            self.judge_counter.draw()

        # Group 7: Player-specific elements
        if self.is_2p:
            self.nameplate.draw(tex.skin_config["game_nameplate_1p"].x, tex.skin_config["game_nameplate_1p"].y)
        else:
            self.nameplate.draw(tex.skin_config["game_nameplate_2p"].x, tex.skin_config["game_nameplate_2p"].y)

        tex.draw_texture('ai_battle', 'scoreboard_ai')
        for j, counter in enumerate([self.good_count, self.ok_count, self.bad_count, self.total_drumroll]):
            margin = tex.textures["ai_battle"]["scoreboard_num"].width//2
            total_width = len(str(counter)) * margin
            for i, digit in enumerate(str(counter)):
                tex.draw_texture('ai_battle', 'scoreboard_num', frame=int(digit), x=-(total_width // 2) + (i * margin), y=-self.stretch_animation[j].attribute, y2=self.stretch_animation[j].attribute, index=j+4)

        # Group 8: Special animations and counters
        if self.drumroll_counter is not None:
            self.drumroll_counter.draw()
        if self.balloon_anim is not None:
            self.balloon_anim.draw()
        if self.kusudama_anim is not None:
            self.kusudama_anim.draw()

class AIGauge(Gauge):
    def draw(self):
        scale = 0.5
        x, y = 10 * tex.screen_scale, 15 * tex.screen_scale
        tex.draw_texture('gauge_ai', f'{self.player_num}p_unfilled' + self.string_diff, scale=scale, x=x, y=y)
        gauge_length = int(self.gauge_length)
        clear_point = self.clear_start[self.difficulty]
        bar_width = tex.textures["gauge_ai"][f"{self.player_num}p_bar"].width * scale
        tex.draw_texture('gauge_ai', f'{self.player_num}p_bar', x2=min(gauge_length*bar_width, (clear_point - 1)*bar_width)-bar_width, scale=scale, x=x, y=y)
        if gauge_length >= clear_point - 1:
            tex.draw_texture('gauge_ai', 'bar_clear_transition', x=((clear_point - 1)*bar_width)+x, scale=scale, y=y)
        if gauge_length > clear_point:
            tex.draw_texture('gauge_ai', 'bar_clear_top', x=((clear_point) * bar_width)+x, x2=(gauge_length-clear_point)*bar_width, scale=scale, y=y)
            tex.draw_texture('gauge_ai', 'bar_clear_bottom', x=((clear_point) * bar_width)+x, x2=(gauge_length-clear_point)*bar_width, scale=scale, y=y)

        # Rainbow effect for full gauge
        if gauge_length == self.gauge_max and self.rainbow_fade_in is not None:
            if 0 < self.rainbow_animation.attribute < 8:
                tex.draw_texture('gauge_ai', 'rainbow' + self.string_diff, frame=self.rainbow_animation.attribute-1, fade=self.rainbow_fade_in.attribute, scale=scale, x=x, y=y)
            tex.draw_texture('gauge_ai', 'rainbow' + self.string_diff, frame=self.rainbow_animation.attribute, fade=self.rainbow_fade_in.attribute, scale=scale, x=x, y=y)
        if self.gauge_update_anim is not None and gauge_length <= self.gauge_max and gauge_length > self.previous_length:
            if gauge_length == self.clear_start[self.difficulty]:
                tex.draw_texture('gauge_ai', 'bar_clear_transition_fade', x=(gauge_length*bar_width)+x, fade=self.gauge_update_anim.attribute, scale=scale, y=y)
            elif gauge_length > self.clear_start[self.difficulty]:
                tex.draw_texture('gauge_ai', 'bar_clear_fade', x=(gauge_length*bar_width)+x, fade=self.gauge_update_anim.attribute, scale=scale, y=y)
            else:
                tex.draw_texture('gauge_ai', f'{self.player_num}p_bar_fade', x=(gauge_length*bar_width)+x, fade=self.gauge_update_anim.attribute, scale=scale, y=y)
        tex.draw_texture('gauge_ai', 'overlay' + self.string_diff, fade=0.15, scale=scale, x=x, y=y)

        # Draw clear status indicators
        tex.draw_texture('gauge_ai', 'footer', scale=scale, x=x, y=y)
        if gauge_length >= clear_point-1:
            tex.draw_texture('gauge_ai', 'clear', index=min(2, self.difficulty), scale=scale, x=x, y=y)
            if self.is_rainbow:
                tex.draw_texture('gauge_ai', 'tamashii_fire', scale=0.75 * scale, center=True, frame=self.tamashii_fire_change.attribute, index=self.is_2p)
            tex.draw_texture('gauge_ai', 'tamashii', scale=scale, x=x, y=y)
            if self.is_rainbow and self.tamashii_fire_change.attribute in (0, 1, 4, 5):
                tex.draw_texture('gauge_ai', 'tamashii_overlay', fade=0.5, scale=scale, x=x, y=y)
        else:
            tex.draw_texture('gauge_ai', 'clear_dark', index=min(2, self.difficulty), scale=scale, x=x, y=y)
            tex.draw_texture('gauge_ai', 'tamashii_dark', scale=scale, x=x, y=y)

class SongInfoAI(SongInfo):
    """Displays the song name and genre"""
    def draw(self):
        y = 600 * tex.screen_scale
        tex.draw_texture('song_info', 'song_num', fade=self.fade.attribute, frame=global_data.songs_played % 4, y=y)

        text_x = tex.skin_config["song_info"].x - self.song_title.texture.width
        text_y = tex.skin_config["song_info"].y - self.song_title.texture.height//2
        self.song_title.draw(outline_color=ray.BLACK, x=text_x, y=text_y+y, color=ray.fade(ray.WHITE, 1 - self.fade.attribute))

        if self.genre < 9:
            tex.draw_texture('song_info', 'genre', fade=1 - self.fade.attribute, frame=self.genre, y=y)

class AIBackground:
    def __init__(self, difficulty: int):
        self.contest_point = 10
        self.total_tiles = 19
        self.difference = 0
        self.difficulty = min(difficulty, 3)
        self.multipliers = [
            [5, 3],
            [5, 3],
            [3, 2],
            [3, 1]
        ]

        self.contest_point_fade = Animation.create_fade(166, initial_opacity=0.0, final_opacity=1.0, reverse_delay=166, delay=166, loop=True)
        self.triangles_down = Animation.create_move(8500, total_distance=1152, loop=True)
        self.contest_point_fade.start()
        self.triangles_down.start()

    def update(self, current_ms: float):
        self.contest_point_fade.update(current_ms)
        self.triangles_down.update(current_ms)

    def update_values(self, player_judge: tuple[int, int], ai_judge: tuple[int, int]):
        player_total = (player_judge[0] * self.multipliers[self.difficulty][0]) + (player_judge[1] * self.multipliers[self.difficulty][1])
        ai_total = (ai_judge[0] * self.multipliers[self.difficulty][0]) + (ai_judge[1] * self.multipliers[self.difficulty][1])
        self.contest_point = ((player_total - ai_total) // 2) + 10
        self.contest_point = min(max(1, self.contest_point), self.total_tiles - 1)

    def unload(self):
        pass

    def draw_lower(self):
        tex.draw_texture('ai_battle', 'bg_lower')
        tile_width = tex.textures['ai_battle']['red_tile_lower'].width
        for i in range(self.contest_point):
            tex.draw_texture('ai_battle', 'red_tile_lower', frame=i, x=(i*tile_width))
        for i in range(self.total_tiles - self.contest_point):
            tex.draw_texture('ai_battle', 'blue_tile_lower', frame=i, x=(((self.total_tiles - 1) - i)*tile_width))

        tex.draw_texture('ai_battle', 'lower_triangles_1', y=self.triangles_down.attribute, fade=0.5)
        tex.draw_texture('ai_battle', 'lower_triangles_2', y=self.triangles_down.attribute, fade=0.5)
        tex.draw_texture('ai_battle', 'highlight_tile_lower', x=self.contest_point * tile_width, fade=self.contest_point_fade.attribute)

    def draw_upper(self, chara_1: Chara2D, chara_2: Chara2D):
        tex.draw_texture('ai_battle', 'bg_upper')
        for i in range(self.contest_point):
            tex.draw_texture('ai_battle', 'red_tile_upper', frame=i, index=i)
        for i in range(self.total_tiles - self.contest_point):
            tex.draw_texture('ai_battle', 'blue_tile_upper', frame=i, index=(self.total_tiles - 1) - i)
        tex.draw_texture('ai_battle', 'bg_outline_upper')
        if self.contest_point > 9:
            frame = self.total_tiles - self.contest_point
            mirror = 'horizontal'
        else:
            frame = self.contest_point - 1
            mirror = ''
        tex.draw_texture('ai_battle', 'highlight_tile_upper', frame=frame, index=self.contest_point-1, mirror=mirror, fade=self.contest_point_fade.attribute)
        tile_width = tex.textures['ai_battle']['red_tile_lower'].width
        offset = 60
        chara_1.draw(x=tile_width*self.contest_point - (global_tex.textures['chara_0']['normal'].width//2) - offset, y=40, scale=0.5)
        chara_2.draw(x=tile_width*self.contest_point - (global_tex.textures['chara_4']['normal'].width//2) + offset*1.3, y=40, scale=0.5, mirror=True)

    def draw(self, chara_1: Chara2D, chara_2: Chara2D):
        self.draw_lower()
        self.draw_upper(chara_1, chara_2)
