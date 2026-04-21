import json
from pathlib import Path
from typing import Callable, TypedDict

import pyray as ray
import tomlkit


class GeneralConfig(TypedDict):
    fps_counter: bool
    audio_offset: int
    visual_offset: int
    language: str
    hard_judge: int
    touch_enabled: bool
    timer_frozen: bool
    judge_counter: bool
    nijiiro_notes: bool
    log_level: int
    fake_online: bool
    practice_mode_bar_delay: int
    score_method: str


class NameplateConfig(TypedDict):
    name: str
    title: str
    title_bg: int
    dan: int
    gold: bool
    rainbow: bool


class PathsConfig(TypedDict):
    tja_path: list[Path]
    skin: Path


class KeysConfig(TypedDict):
    exit_key: int
    fullscreen_key: int
    borderless_key: int
    pause_key: int
    back_key: int
    restart_key: int


class Keys1PConfig(TypedDict):
    left_kat: list[int]
    left_don: list[int]
    right_don: list[int]
    right_kat: list[int]


class Keys2PConfig(TypedDict):
    left_kat: list[int]
    left_don: list[int]
    right_don: list[int]
    right_kat: list[int]


class GamepadConfig(TypedDict):
    left_kat: list[int]
    left_don: list[int]
    right_don: list[int]
    right_kat: list[int]


class AudioConfig(TypedDict):
    device_type: int
    sample_rate: int
    buffer_size: int


class VolumeConfig(TypedDict):
    sound: float
    music: float
    voice: float
    hitsound: float
    attract_mode: float


class VideoConfig(TypedDict):
    fullscreen: bool
    borderless: bool
    target_fps: int
    vsync: bool


class Config(TypedDict):
    general: GeneralConfig
    nameplate_1p: NameplateConfig
    nameplate_2p: NameplateConfig
    paths: PathsConfig
    keys: KeysConfig
    keys_1p: Keys1PConfig
    keys_2p: Keys2PConfig
    gamepad: GamepadConfig
    audio: AudioConfig
    volume: VolumeConfig
    video: VideoConfig


KEY_PREFIX = 'KEY_'
DEV_CONFIG_PATH = Path('dev-config.toml')
DEFAULT_CONFIG_PATH = Path('config.toml')


def _get_config_path() -> Path:
    """Return the active config path."""
    # In development mode, prefer dev-config.toml to avoid overwriting production settings.
    return DEV_CONFIG_PATH if DEV_CONFIG_PATH.exists() else DEFAULT_CONFIG_PATH


def _to_plain_dict(data: tomlkit.TOMLDocument | Config) -> Config:
    """Convert tomlkit objects to plain Python dict/list/scalar values."""
    return json.loads(json.dumps(data))


def _convert_single_key_bindings(
        bindings: dict[str, int | str],
        converter: Callable[[int | str], int | str],
) -> None:
    """Convert single-value key bindings in-place."""
    for key in bindings:
        bindings[key] = converter(bindings[key])


def _convert_multi_key_bindings(
        bindings: dict[str, list[int] | list[str]],
        converter: Callable[[int | str], int | str],
) -> None:
    """Convert list-based key bindings in-place."""
    for key in bindings:
        values = bindings[key]
        for index, value in enumerate(values):
            values[index] = converter(value)


def _build_key_name_lookup() -> dict[int, str]:
    """Build key-code -> key-name mapping once for faster reverse lookups."""
    lookup: dict[int, str] = {}
    for attr_name in dir(ray):
        if not attr_name.startswith(KEY_PREFIX):
            continue
        key_code = getattr(ray, attr_name)
        if isinstance(key_code, int) and key_code not in lookup:
            # Keep first match to preserve the original `dir(ray)` lookup behavior.
            lookup[key_code] = attr_name[len(KEY_PREFIX):].lower()
    return lookup


_KEY_NAME_LOOKUP = _build_key_name_lookup()


def get_key_string(key_code: int) -> str:
    """Convert a key code back to its string representation."""
    if 65 <= key_code <= 90:
        return chr(key_code)
    if 48 <= key_code <= 57:
        return chr(key_code)

    key_name = _KEY_NAME_LOOKUP.get(key_code)
    if key_name is not None:
        return key_name

    raise ValueError(f"Unknown key code: {key_code}")


def get_key_code(key: str) -> int:
    """Convert a key name (e.g. `f11`, `space`, `A`) to a key code."""
    if len(key) == 1 and key.isalnum():
        return ord(key.upper())

    key_code = getattr(ray, f"{KEY_PREFIX}{key.upper()}", None)
    if key_code is None:
        raise ValueError(f"Invalid key: {key}")
    return key_code


def get_config() -> Config:
    """Load TOML config and convert keyboard bindings into key codes."""
    config_path = _get_config_path()

    with open(config_path, "r", encoding="utf-8") as config_stream:
        config_file: tomlkit.TOMLDocument = tomlkit.load(config_stream)

    config: Config = _to_plain_dict(config_file)
    _convert_single_key_bindings(config['keys'], get_key_code)
    _convert_multi_key_bindings(config['keys_1p'], get_key_code)
    _convert_multi_key_bindings(config['keys_2p'], get_key_code)
    return config


def save_config(config: Config) -> None:
    """Save config to TOML after converting key codes to key names."""
    config_to_save = _to_plain_dict(config)

    _convert_single_key_bindings(config_to_save['keys'], get_key_string)
    _convert_multi_key_bindings(config_to_save['keys_1p'], get_key_string)
    _convert_multi_key_bindings(config_to_save['keys_2p'], get_key_string)

    config_path = _get_config_path()
    with open(config_path, "w", encoding="utf-8") as config_stream:
        tomlkit.dump(config_to_save, config_stream)
