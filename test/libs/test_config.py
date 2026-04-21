import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pyray as ray
import tomlkit

import libs.config as config_module


class TestConfigKeyConversion(unittest.TestCase):
    def test_get_key_code_alnum(self):
        self.assertEqual(config_module.get_key_code('a'), ord('A'))
        self.assertEqual(config_module.get_key_code('5'), ord('5'))

    def test_get_key_code_named_key(self):
        self.assertEqual(config_module.get_key_code('space'), ray.KEY_SPACE)
        self.assertEqual(config_module.get_key_code('f11'), ray.KEY_F11)

    def test_get_key_code_invalid_raises(self):
        with self.assertRaises(ValueError):
            config_module.get_key_code('definitely_invalid_key')

    def test_get_key_string_alnum(self):
        self.assertEqual(config_module.get_key_string(ord('A')), 'A')
        self.assertEqual(config_module.get_key_string(ord('9')), '9')

    def test_get_key_string_named_key(self):
        self.assertEqual(config_module.get_key_string(ray.KEY_SPACE), 'space')

    def test_get_key_string_invalid_raises(self):
        with self.assertRaises(ValueError):
            config_module.get_key_string(987654321)


class TestConfigReadWrite(unittest.TestCase):
    def test_get_config_path_prefers_dev_config(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            dev_path = tmp_path / 'dev-config.toml'
            default_path = tmp_path / 'config.toml'
            default_path.write_text('', encoding='utf-8')

            with (
                patch.object(config_module, 'DEV_CONFIG_PATH', dev_path),
                patch.object(config_module, 'DEFAULT_CONFIG_PATH', default_path),
            ):
                self.assertEqual(config_module._get_config_path(), default_path)
                dev_path.write_text('', encoding='utf-8')
                self.assertEqual(config_module._get_config_path(), dev_path)

    def test_get_config_converts_key_bindings_to_codes(self):
        config_text = """
[keys]
exit_key = "q"
fullscreen_key = "f11"
borderless_key = "f10"
pause_key = "space"
back_key = "escape"
restart_key = "f1"

[keys_1p]
left_kat = ["q", "w"]
left_don = ["a", "s"]
right_don = ["j", "k"]
right_kat = ["u", "i"]

[keys_2p]
left_kat = ["z"]
left_don = ["x"]
right_don = ["c"]
right_kat = ["v"]
"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            config_path = Path(tmp_dir) / 'config.toml'
            config_path.write_text(config_text.strip(), encoding='utf-8')

            with patch.object(config_module, '_get_config_path', return_value=config_path):
                loaded = config_module.get_config()

        self.assertEqual(loaded['keys']['exit_key'], ord('Q'))
        self.assertEqual(loaded['keys']['fullscreen_key'], ray.KEY_F11)
        self.assertEqual(loaded['keys_1p']['left_kat'], [ord('Q'), ord('W')])
        self.assertEqual(loaded['keys_2p']['right_kat'], [ord('V')])

    def test_save_config_converts_key_bindings_to_strings(self):
        config_data = {
            'keys': {
                'exit_key': ord('Q'),
                'fullscreen_key': ray.KEY_F11,
                'borderless_key': ray.KEY_F10,
                'pause_key': ray.KEY_SPACE,
                'back_key': ray.KEY_ESCAPE,
                'restart_key': ray.KEY_F1,
            },
            'keys_1p': {
                'left_kat': [ord('Q'), ord('W')],
                'left_don': [ord('A'), ord('S')],
                'right_don': [ord('J'), ord('K')],
                'right_kat': [ord('U'), ord('I')],
            },
            'keys_2p': {
                'left_kat': [ord('Z')],
                'left_don': [ord('X')],
                'right_don': [ord('C')],
                'right_kat': [ord('V')],
            },
        }

        with tempfile.TemporaryDirectory() as tmp_dir:
            config_path = Path(tmp_dir) / 'config.toml'
            with patch.object(config_module, '_get_config_path', return_value=config_path):
                config_module.save_config(config_data)

            with open(config_path, "r", encoding="utf-8") as f:
                saved = tomlkit.load(f)

        self.assertEqual(saved['keys']['exit_key'], 'Q')
        self.assertEqual(saved['keys']['pause_key'], 'space')
        self.assertEqual(saved['keys_1p']['left_kat'], ['Q', 'W'])
        self.assertEqual(saved['keys_2p']['right_kat'], ['V'])
        self.assertEqual(config_data['keys']['pause_key'], ray.KEY_SPACE)


if __name__ == '__main__':
    unittest.main()
