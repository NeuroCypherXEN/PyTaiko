import json
import logging

import pyray as ray

from libs.animation import Animation
from libs.audio import audio
from libs.config import get_key_string, save_config
from libs.global_objects import AllNetIcon, CoinOverlay, Indicator
from libs.screen import Screen
from libs.texture import tex
from libs.utils import (
    OutlinedText,
    get_current_ms,
    global_data,
    is_l_don_pressed,
    is_l_kat_pressed,
    is_r_don_pressed,
    is_r_kat_pressed,
)

logger = logging.getLogger(__name__)

class BaseOptionBox:
    def __init__(self, name: str, description: str, path: str, values: dict):
        self.name = OutlinedText(name, 30, ray.WHITE)
        self.setting_header, self.setting_name = path.split('/')
        self.description = description
        self.is_highlighted = False
        self.value = global_data.config[self.setting_header][self.setting_name]

    def update(self, current_time):
        pass

    def move_left(self):
        pass

    def move_right(self):
        pass

    def confirm(self):
        global_data.config[self.setting_header][self.setting_name] = self.value

    def __repr__(self):
        return str(self.__dict__)

    def draw(self):
        tex.draw_texture('background', 'overlay', scale=0.70)
        if self.is_highlighted:
            tex.draw_texture('background', 'title_highlight')
        else:
            tex.draw_texture('background', 'title')
        text_x = tex.textures['background']['title'].x[0] + (tex.textures['background']['title'].width//2) - (self.name.texture.width//2)
        text_y = tex.textures['background']['title'].y[0] + self.name.texture.height//4
        self.name.draw(outline_color=ray.BLACK, x=text_x, y=text_y)
        ray.draw_text_ex(global_data.font, self.description, (450 * tex.screen_scale, 270 * tex.screen_scale), 25 * tex.screen_scale, 1, ray.BLACK)

class BoolOptionBox(BaseOptionBox):
    def __init__(self, name: str, description: str, path: str, values: dict):
        super().__init__(name, description, path, values)
        language = global_data.config["general"]["language"]
        self.on_value = OutlinedText(values["true"].get(language, values["true"]["en"]), int(30 * tex.screen_scale), ray.WHITE)
        self.off_value = OutlinedText(values["false"].get(language, values["false"]["en"]), int(30 * tex.screen_scale), ray.WHITE)

    def move_left(self):
        self.value = False

    def move_right(self):
        self.value = True

    def draw(self):
        super().draw()
        if not self.value:
            tex.draw_texture('option', 'button_on', index=0)
        else:
            tex.draw_texture('option', 'button_off', index=0)
        text_x = tex.textures["option"]["button_on"].x[0] + (tex.textures["option"]["button_on"].width//2) - (self.off_value.texture.width//2)
        text_y = tex.textures["option"]["button_on"].y[0] + (tex.textures["option"]["button_on"].height//2) - (self.off_value.texture.height//2)
        self.off_value.draw(outline_color=ray.BLACK, x=text_x, y=text_y)
        if self.value:
            tex.draw_texture('option', 'button_on', index=1)
        else:
            tex.draw_texture('option', 'button_off', index=1)
        text_x = tex.textures["option"]["button_on"].x[1] + (tex.textures["option"]["button_on"].width//2) - (self.on_value.texture.width//2)
        text_y = tex.textures["option"]["button_on"].y[1] + (tex.textures["option"]["button_on"].height//2) - (self.on_value.texture.height//2)
        self.on_value.draw(outline_color=ray.BLACK, x=text_x, y=text_y)

class IntOptionBox(BaseOptionBox):
    def __init__(self, name: str, description: str, path: str, values: dict):
        super().__init__(name, description, path, values)
        self.value_text = OutlinedText(str(self.value), int(30 * tex.screen_scale), ray.WHITE)
        self.flicker_fade = Animation.create_fade(400, initial_opacity=0.0, final_opacity=1.0, reverse_delay=0, loop=True)
        self.flicker_fade.start()
        language = global_data.config["general"]["language"]
        self.value_list = []
        if values != dict():
            self.value_list = list(values.keys())
            self.value_index = 0
            self.values = values
            self.value_text = OutlinedText(self.values[str(self.value)].get(language, self.values[str(self.value)]["en"]), int(30 * tex.screen_scale), ray.WHITE)

    def update(self, current_time):
        self.flicker_fade.update(current_time)

    def move_left(self):
        if self.value_list:
            self.value_index = max(self.value_index - 1, 0)
            self.value = int(self.value_list[self.value_index])
            self.value_text = OutlinedText(self.values[str(self.value)].get(global_data.config["general"]["language"], self.values[str(self.value)]["en"]), int(30 * tex.screen_scale), ray.WHITE)
        else:
            self.value -= 1
            self.value_text = OutlinedText(str(self.value), int(30 * tex.screen_scale), ray.WHITE)

    def move_right(self):
        if self.value_list:
            self.value_index = min(self.value_index + 1, len(self.value_list) - 1)
            self.value = int(self.value_list[self.value_index])
            self.value_text = OutlinedText(self.values[str(self.value)].get(global_data.config["general"]["language"], self.values[str(self.value)]["en"]), int(30 * tex.screen_scale), ray.WHITE)
        else:
            self.value += 1
            self.value_text = OutlinedText(str(self.value), int(30 * tex.screen_scale), ray.WHITE)

    def draw(self):
        super().draw()
        tex.draw_texture('option', 'button_off', index=2)
        if self.is_highlighted:
            tex.draw_texture('option', 'button_on', index=2, fade=self.flicker_fade.attribute)
        text_x = tex.textures["option"]["button_on"].x[2] + (tex.textures["option"]["button_on"].width//2) - (self.value_text.texture.width//2)
        text_y = tex.textures["option"]["button_on"].y[2] + (tex.textures["option"]["button_on"].height//2) - (self.value_text.texture.height//2)
        self.value_text.draw(outline_color=ray.BLACK, x=text_x, y=text_y)

class StrOptionBox(BaseOptionBox):
    def __init__(self, name: str, description: str, path: str, values: dict):
        super().__init__(name, description, path, values)
        self.flicker_fade = Animation.create_fade(400, initial_opacity=0.0, final_opacity=1.0, reverse_delay=0, loop=True)
        self.flicker_fade.start()
        self.value_list = []
        if values != dict():
            self.value_list = list(values.keys())
            self.value_index = 0
            self.values = values
            language = global_data.config["general"]["language"]
            self.value_text = OutlinedText(self.values[self.value].get(language, self.values[self.value]["en"]), int(30 * tex.screen_scale), ray.WHITE)
        else:
            self.string = self.value
            self.value_text = OutlinedText(self.value, int(30 * tex.screen_scale), ray.WHITE)

    def update(self, current_time):
        self.flicker_fade.update(current_time)
        if self.is_highlighted and self.value_list == []:
            if ray.is_key_pressed(ray.KeyboardKey.KEY_BACKSPACE):
                self.string = self.string[:-1]
                self.value_text = OutlinedText(self.string, int(30 * tex.screen_scale), ray.WHITE)
            elif ray.is_key_pressed(ray.KeyboardKey.KEY_ENTER):
                self.value = self.string
                self.is_highlighted = False
            key = ray.get_char_pressed()
            if key > 0:
                self.string += chr(key)
                self.value_text = OutlinedText(self.string, int(30 * tex.screen_scale), ray.WHITE)

    def move_left(self):
        if self.value_list:
            self.value_index = max(self.value_index - 1, 0)
            self.value = self.value_list[self.value_index]
            self.value_text = OutlinedText(self.values[self.value].get(global_data.config["general"]["language"], self.values[self.value]["en"]), int(30 * tex.screen_scale), ray.WHITE)

    def move_right(self):
        if self.value_list:
            self.value_index = min(self.value_index + 1, len(self.value_list) - 1)
            self.value = self.value_list[self.value_index]
            self.value_text = OutlinedText(self.values[self.value].get(global_data.config["general"]["language"], self.values[self.value]["en"]), int(30 * tex.screen_scale), ray.WHITE)

    def draw(self):
        super().draw()
        tex.draw_texture('option', 'button_off', index=2)
        if self.is_highlighted:
            tex.draw_texture('option', 'button_on', index=2, fade=self.flicker_fade.attribute)
        text_x = tex.textures["option"]["button_on"].x[2] + (tex.textures["option"]["button_on"].width//2) - (self.value_text.texture.width//2)
        text_y = tex.textures["option"]["button_on"].y[2] + (tex.textures["option"]["button_on"].height//2) - (self.value_text.texture.height//2)
        self.value_text.draw(outline_color=ray.BLACK, x=text_x, y=text_y)

class KeybindOptionBox(BaseOptionBox):
    def __init__(self, name: str, description: str, path: str, values: dict):
        super().__init__(name, description, path, values)
        if isinstance(self.value, list):
            text = ', '.join([get_key_string(key) for key in self.value])
        else:
            text = get_key_string(self.value)
        self.value_text = OutlinedText(text, int(30 * tex.screen_scale), ray.WHITE)
        self.flicker_fade = Animation.create_fade(400, initial_opacity=0.0, final_opacity=1.0, reverse_delay=0, loop=True)
        self.flicker_fade.start()

    def update(self, current_time):
        self.flicker_fade.update(current_time)
        if self.is_highlighted:
            key = ray.get_key_pressed()
            if key > 0:
                self.value = key
                audio.play_sound('don', 'sound')
                self.value_text = OutlinedText(get_key_string(self.value), int(30 * tex.screen_scale), ray.WHITE)
                self.is_highlighted = False

    def draw(self):
        super().draw()
        tex.draw_texture('option', 'button_off', index=2)
        if self.is_highlighted:
            tex.draw_texture('option', 'button_on', index=2, fade=self.flicker_fade.attribute)
        text_x = tex.textures["option"]["button_on"].x[2] + (tex.textures["option"]["button_on"].width//2) - (self.value_text.texture.width//2)
        text_y = tex.textures["option"]["button_on"].y[2] + (tex.textures["option"]["button_on"].height//2) - (self.value_text.texture.height//2)
        self.value_text.draw(outline_color=ray.BLACK, x=text_x, y=text_y)

class KeyBindControllerOptionBox(BaseOptionBox):
    def __init__(self, name: str, description: str, path: str, values: dict):
        super().__init__(name, description, path, values)
        if isinstance(self.value, list):
            text = ', '.join([str(key) for key in self.value])
        else:
            text = str(self.value)
        self.value_text = OutlinedText(text, int(30 * tex.screen_scale), ray.WHITE)
        self.flicker_fade = Animation.create_fade(400, initial_opacity=0.0, final_opacity=1.0, reverse_delay=0, loop=True)
        self.flicker_fade.start()

    def update(self, current_time):
        self.flicker_fade.update(current_time)
        if self.is_highlighted:
            key = ray.get_gamepad_button_pressed()
            if key > 0:
                self.value = key
                audio.play_sound('don', 'sound')
                self.value_text = OutlinedText(str(self.value), int(30 * tex.screen_scale), ray.WHITE)
                self.is_highlighted = False

    def draw(self):
        super().draw()
        tex.draw_texture('option', 'button_off', index=2)
        if self.is_highlighted:
            tex.draw_texture('option', 'button_on', index=2, fade=self.flicker_fade.attribute)
        text_x = tex.textures["option"]["button_on"].x[2] + (tex.textures["option"]["button_on"].width//2) - (self.value_text.texture.width//2)
        text_y = tex.textures["option"]["button_on"].y[2] + (tex.textures["option"]["button_on"].height//2) - (self.value_text.texture.height//2)
        self.value_text.draw(outline_color=ray.BLACK, x=text_x, y=text_y)

class FloatOptionBox(BaseOptionBox):
    def __init__(self, name: str, description: str, path: str, values: dict):
        super().__init__(name, description, path, values)
        self.value_text = OutlinedText(str(int(self.value*100)) + "%", int(30 * tex.screen_scale), ray.WHITE)
        self.flicker_fade = Animation.create_fade(400, initial_opacity=0.0, final_opacity=1.0, reverse_delay=0, loop=True)
        self.flicker_fade.start()

    def update(self, current_time):
        self.flicker_fade.update(current_time)

    def move_left(self):
        self.value = ((self.value*100) - 1) / 100
        self.value_text = OutlinedText(str(int(self.value*100))+"%", int(30 * tex.screen_scale), ray.WHITE)

    def move_right(self):
        self.value = ((self.value*100) + 1) / 100
        self.value_text = OutlinedText(str(int(self.value*100))+"%", int(30 * tex.screen_scale), ray.WHITE)

    def draw(self):
        super().draw()
        tex.draw_texture('option', 'button_off', index=2)
        if self.is_highlighted:
            tex.draw_texture('option', 'button_on', index=2, fade=self.flicker_fade.attribute)
        text_x = tex.textures["option"]["button_on"].x[2] + (tex.textures["option"]["button_on"].width//2) - (self.value_text.texture.width//2)
        text_y = tex.textures["option"]["button_on"].y[2] + (tex.textures["option"]["button_on"].height//2) - (self.value_text.texture.height//2)
        self.value_text.draw(outline_color=ray.BLACK, x=text_x, y=text_y)

class Box:
    """Box class for the entry screen"""
    OPTION_BOX_MAP = {
        "int": IntOptionBox,
        "bool": BoolOptionBox,
        "string": StrOptionBox,
        "keybind": KeybindOptionBox,
        "keybind_controller": KeyBindControllerOptionBox,
        "float": FloatOptionBox
    }
    def __init__(self, name: str, text: str, box_options: dict):
        self.name = name
        self.text = OutlinedText(text, tex.skin_config["entry_box_text"].font_size - int(5*tex.screen_scale), ray.WHITE, outline_thickness=5)
        self.x = 10 * tex.screen_scale
        self.y = -50 * tex.screen_scale
        self.move = tex.get_animation(0)
        self.blue_arrow_fade = tex.get_animation(1)
        self.blue_arrow_move = tex.get_animation(2)
        self.is_selected = False
        self.in_box = False
        self.outline_color = ray.Color(109, 68, 24, 255)
        self.direction = 1
        self.target_position = float('inf')
        self.start_position = self.y
        self.option_index = 0
        language = global_data.config["general"]["language"]
        self.options = [Box.OPTION_BOX_MAP[
            box_options[option]["type"]](box_options[option]["name"].get(language, box_options[option]["name"]["en"]),
            box_options[option]["description"].get(language, box_options[option]["description"]["en"]), box_options[option]["path"],
            box_options[option]["values"]) for option in box_options]

    def __repr__(self):
        return str(self.__dict__)

    def move_left(self):
        """Move the box left"""
        if self.y != self.target_position and self.target_position != float('inf'):
            return False
        self.move.start()
        self.direction = 1
        self.start_position = self.y
        self.target_position = self.y + (100 * tex.screen_scale * self.direction)

        if self.target_position >= 650:
            self.target_position = -50 + (self.target_position - 650)

        return True

    def move_right(self):
        """Move the box right"""
        if self.y != self.target_position and self.target_position != float('inf'):
            return False
        self.move.start()
        self.start_position = self.y
        self.direction = -1
        self.target_position = self.y + (100 * tex.screen_scale * self.direction)

        if self.target_position < -50:
            self.target_position = 650 + (self.target_position + 50)

        return True

    def move_option_left(self):
        if self.options[self.option_index].is_highlighted:
            self.options[self.option_index].move_left()
            return True
        else:
            if self.option_index == 0:
                self.in_box = False
                return False
            self.option_index -= 1
            return True

    def move_option_right(self):
        if self.options[self.option_index].is_highlighted:
            self.options[self.option_index].move_right()
        else:
            self.option_index = min(self.option_index + 1, len(self.options) - 1)

    def select_option(self):
        self.options[self.option_index].is_highlighted = not self.options[self.option_index].is_highlighted
        self.options[self.option_index].confirm()

    def select(self):
        self.in_box = True

    def update(self, current_time_ms: float, is_selected: bool):
        self.move.update(current_time_ms)
        self.blue_arrow_fade.update(current_time_ms)
        self.blue_arrow_move.update(current_time_ms)
        self.is_selected = is_selected
        if self.move.is_finished:
            self.y = self.target_position
        else:
            self.y = self.start_position + (self.move.attribute * self.direction)
        for option in self.options:
            option.update(current_time_ms)

    def _draw_highlighted(self):
        tex.draw_texture('box', 'box_highlight', x=self.x, y=self.y)

    def _draw_text(self):
        text_x = self.x + (tex.textures['box']['box'].width//2) - (self.text.texture.width//2)
        text_y = self.y + (tex.textures['box']['box'].height//2) - (self.text.texture.height//2)
        if self.is_selected:
            self.text.draw(outline_color=ray.BLACK, x=text_x, y=text_y)
        else:
            if self.name == 'exit':
                self.text.draw(outline_color=ray.RED, x=text_x, y=text_y)
            else:
                self.text.draw(outline_color=self.outline_color, x=text_x, y=text_y)

    def draw(self):
        tex.draw_texture('box', 'box', x=self.x, y=self.y)
        if self.is_selected:
            self._draw_highlighted()
        if self.in_box:
            self.options[self.option_index].draw()
            if not self.options[self.option_index].is_highlighted:
                tex.draw_texture('background', 'blue_arrow', index=0, x=-self.blue_arrow_move.attribute, fade=self.blue_arrow_fade.attribute)
                if self.option_index != len(self.options) - 1:
                    tex.draw_texture('background', 'blue_arrow', index=1, x=self.blue_arrow_move.attribute, fade=self.blue_arrow_fade.attribute, mirror='horizontal')
        self._draw_text()

class BoxManager:
    """BoxManager class for the entry screen"""
    def __init__(self, settings_template: dict):
        language = global_data.config["general"]["language"]
        self.boxes = [Box(config_name, settings_template[config_name]["name"].get(language, settings_template[config_name]["name"]["en"]), settings_template[config_name]["options"]) for config_name in settings_template]
        self.num_boxes = len(self.boxes)
        self.selected_box_index = 3
        self.box_selected = False

        for i, box in enumerate(self.boxes):
            box.y += 100*i
            box.start_position += 100*i

    def move_left(self):
        """Move the cursor to the left"""
        if self.box_selected:
            box = self.boxes[self.selected_box_index]
            self.box_selected = box.move_option_left()
        else:
            moved = True
            for box in self.boxes:
                if not box.move_left():
                    moved = False

            if moved:
                self.selected_box_index = (self.selected_box_index - 1) % self.num_boxes

    def move_right(self):
        """Move the cursor to the right"""
        if self.box_selected:
            box = self.boxes[self.selected_box_index]
            box.move_option_right()
        else:
            moved = True
            for box in self.boxes:
                if not box.move_right():
                    moved = False

            if moved:
                self.selected_box_index = (self.selected_box_index + 1) % self.num_boxes

    def select_box(self):
        if self.boxes[self.selected_box_index].name == "exit":
            return "exit"
        if self.box_selected:
            box = self.boxes[self.selected_box_index]
            box.select_option()
        else:
            self.box_selected = True
            self.boxes[self.selected_box_index].in_box = True

    def update(self, current_time_ms: float):
        for i, box in enumerate(self.boxes):
            is_selected = i == self.selected_box_index and not self.box_selected
            box.update(current_time_ms, is_selected)

    def draw(self):
        for box in self.boxes:
            box.draw()

class SettingsScreen(Screen):
    def on_screen_start(self):
        super().on_screen_start()
        self.indicator = Indicator(Indicator.State.SELECT)
        self.template = json.loads((tex.graphics_path / "settings_template.json").read_text(encoding='utf-8'))
        self.box_manager = BoxManager(self.template)
        self.coin_overlay = CoinOverlay()
        self.allnet_indicator = AllNetIcon()
        audio.play_sound('bgm', 'music')

    def on_screen_end(self, next_screen: str):
        save_config(global_data.config)
        audio.close_audio_device()
        audio.device_type = global_data.config["audio"]["device_type"]
        audio.target_sample_rate = global_data.config["audio"]["sample_rate"]
        audio.buffer_size = global_data.config["audio"]["buffer_size"]
        audio.volume_presets = global_data.config["volume"]
        audio.init_audio_device()
        logger.info("Settings saved and audio device re-initialized")
        return super().on_screen_end(next_screen)

    def handle_input(self):
        if is_l_kat_pressed():
            audio.play_sound('kat', 'sound')
            self.box_manager.move_left()
        elif is_r_kat_pressed():
            audio.play_sound('kat', 'sound')
            self.box_manager.move_right()
        elif is_l_don_pressed() or is_r_don_pressed():
            audio.play_sound('don', 'sound')
            box_name = self.box_manager.select_box()
            if box_name == 'exit':
                return self.on_screen_end("ENTRY")

    def update(self):
        super().update()

        current_time = get_current_ms()
        self.indicator.update(current_time)
        self.box_manager.update(current_time)
        return self.handle_input()

    def draw(self):
        tex.draw_texture('background', 'background')
        self.box_manager.draw()
        tex.draw_texture('background', 'footer')
        self.indicator.draw(tex.skin_config['song_select_indicator'].x, tex.skin_config['song_select_indicator'].y)
        self.coin_overlay.draw()
        self.allnet_indicator.draw()
