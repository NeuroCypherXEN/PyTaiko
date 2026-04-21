import pyray as ray

from libs.utils import OutlinedText, global_tex


class Transition:
    """Transition class for the game."""
    def __init__(self, title: str, subtitle: str, is_second: bool = False) -> None:
        """Initialize the transition object.
        title: str - The title of the chart.
        subtitle: str - The subtitle of the chart.
        is_second: bool - Whether this is the second half of the transition."""
        self.is_finished = False
        self.rainbow_up = global_tex.get_animation(0, is_copy=True)
        self.mini_up = global_tex.get_animation(1, is_copy=True)
        self.chara_down = global_tex.get_animation(2, is_copy=True)
        self.song_info_fade = global_tex.get_animation(3, is_copy=True)
        self.song_info_fade_out = global_tex.get_animation(4, is_copy=True)
        self._animations = [
            self.rainbow_up,
            self.mini_up,
            self.chara_down,
            self.song_info_fade,
            self.song_info_fade_out,
        ]
        if title == '' and subtitle == '':
            self.title = ''
            self.subtitle = ''
        else:
            self.title = OutlinedText(title, global_tex.skin_config['transition_title'].font_size, ray.WHITE)
            self.subtitle = OutlinedText(subtitle, global_tex.skin_config['transition_subtitle'].font_size, ray.WHITE)
        self.is_second = is_second

    def _has_song_info(self) -> bool:
        return not (self.title == '' and self.subtitle == '')

    def _song_info_colors(self):
        if not self.is_second:
            alpha = self.song_info_fade.attribute
        else:
            alpha = self.song_info_fade_out.attribute
        primary = ray.fade(ray.WHITE, alpha)
        secondary = ray.fade(ray.WHITE, min(0.70, alpha))
        return primary, secondary

    def _song_info_offset(self) -> float:
        if self.is_second:
            return global_tex.skin_config['transition_offset'].y - self.rainbow_up.attribute
        return 0

    def start(self):
        """Start the transition effect."""
        for animation in self._animations:
            animation.start()

    def update(self, current_time_ms: float):
        """Update the transition effect."""
        for animation in self._animations:
            animation.update(current_time_ms)
        self.is_finished = self.song_info_fade.is_finished

    def _draw_song_info(self):
        color_1, color_2 = self._song_info_colors()
        offset = self._song_info_offset()
        global_tex.draw_texture('rainbow_transition', 'text_bg', y=-self.rainbow_up.attribute - offset, color=color_2)

        if isinstance(self.title, OutlinedText):
            texture = self.title.texture
            x = global_tex.screen_width//2 - texture.width//2
            y = global_tex.skin_config['transition_title'].y - texture.height//2 - int(self.rainbow_up.attribute) - offset
            self.title.draw(outline_color=ray.BLACK, x=x, y=y, color=color_1)

        if isinstance(self.subtitle, OutlinedText):
            texture = self.subtitle.texture
            x = global_tex.screen_width//2 - texture.width//2
            y = global_tex.skin_config['transition_subtitle'].y - texture.height//2 - int(self.rainbow_up.attribute) - offset
            self.subtitle.draw(outline_color=ray.BLACK, x=x, y=y, color=color_1)

    def draw(self):
        """Draw the transition effect."""
        total_offset = 0
        if self.is_second:
            total_offset = global_tex.skin_config['transition_offset'].y
        global_tex.draw_texture('rainbow_transition', 'rainbow_bg_bottom', y=-self.rainbow_up.attribute - total_offset)
        global_tex.draw_texture('rainbow_transition', 'rainbow_bg_top', y=-self.rainbow_up.attribute - total_offset)
        global_tex.draw_texture('rainbow_transition', 'rainbow_bg', y=-self.rainbow_up.attribute - total_offset)
        offset = self.chara_down.attribute
        chara_offset = 0
        if self.is_second:
            offset = self.chara_down.attribute - self.mini_up.attribute//3
            chara_offset = global_tex.skin_config['transition_chara_offset'].y
        if not self._has_song_info():
            return
        global_tex.draw_texture('rainbow_transition', 'chara_left', x=-self.mini_up.attribute//2 - chara_offset, y=-self.mini_up.attribute + offset - total_offset)
        global_tex.draw_texture('rainbow_transition', 'chara_right', x=self.mini_up.attribute//2 + chara_offset, y=-self.mini_up.attribute + offset - total_offset)
        global_tex.draw_texture('rainbow_transition', 'chara_center', y=-self.rainbow_up.attribute + offset - total_offset)

        self._draw_song_info()
