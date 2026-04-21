import json
import logging
import sys
from pathlib import Path
from typing import Any, Optional

import raylib as ray
from pyray import Color, Rectangle, Vector2

from libs.animation import BaseAnimation, parse_animations
from libs.config import get_config

logger = logging.getLogger(__name__)


def _configure_texture(texture: Any) -> None:
    """Apply common texture setup after loading."""
    ray.GenTextureMipmaps(ray.ffi.addressof(texture))
    ray.SetTextureFilter(texture, ray.TEXTURE_FILTER_TRILINEAR)
    ray.SetTextureWrap(texture, ray.TEXTURE_WRAP_CLAMP)


class SkinInfo:
    def __init__(self, x: float, y: float, font_size: int, width: float, height: float, text: dict[str, str]):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.font_size = font_size
        self.text = text

    def __repr__(self):
        return f"{self.__dict__}"

class Texture:
    """Texture class for managing textures and animations."""
    def __init__(self, name: str, texture: Any, init_vals: dict[str, int]):
        self.name = name
        self.texture = texture
        self.init_vals = init_vals
        self.width = self.texture.width
        self.height = self.texture.height
        _configure_texture(self.texture)

        self.x: list[int] = [0]
        self.y: list[int] = [0]
        self.x2: list[int] = [self.width]
        self.y2: list[int] = [self.height]
        self.controllable: list[bool] = [False]
        self.crop_data: Optional[list[tuple[float, float, float, float]]] = None

    def __repr__(self):
        return f"{self.__dict__}"

class FramedTexture:
    def __init__(self, name: str, texture: list[Any], init_vals: dict[str, int]):
        self.name = name
        self.texture = texture
        self.init_vals = init_vals
        self.width = self.texture[0].width
        self.height = self.texture[0].height
        for texture_data in self.texture:
            _configure_texture(texture_data)
        self.x: list[int] = [0]
        self.y: list[int] = [0]
        self.x2: list[int] = [self.width]
        self.y2: list[int] = [self.height]
        self.controllable: list[bool] = [False]
        self.crop_data: Optional[list[tuple[float, float, float, float]]] = None

class TextureWrapper:
    """Texture wrapper class for managing textures and animations."""
    def __init__(self):
        self.textures: dict[str, dict[str, Texture | FramedTexture]] = dict()
        self.animations: dict[int, BaseAnimation] = dict()
        self.skin_config: dict[str, SkinInfo] = dict()
        skin_name = get_config()['paths']['skin']
        self.graphics_path = Path(f"Skins/{skin_name}/Graphics")
        if not self.graphics_path.exists():
            logger.error("No skin has been configured")
            self.screen_width = 1280
            self.screen_height = 720
            self.screen_scale = 1.0
            self.skin_config = dict()
            return
        self.parent_graphics_path = self.graphics_path
        if not (self.graphics_path / "skin_config.json").exists():
            raise Exception("skin is missing a skin_config.json")

        data = json.loads((self.graphics_path / "skin_config.json").read_text(encoding='utf-8'))
        self.skin_config: dict[str, SkinInfo] = {
            k: SkinInfo(v.get('x', 0), v.get('y', 0), v.get('font_size', 0), v.get('width', 0), v.get('height', 0), v.get('text', dict())) for k, v in data.items()
        }
        self.screen_width = int(self.skin_config["screen"].width)
        self.screen_height = int(self.skin_config["screen"].height)
        self.screen_scale = self.screen_width / 1280
        if "parent" in data["screen"]:
            parent = data["screen"]["parent"]
            # Support both parent="SkinName" and parent="SkinName/Graphics" formats.
            parent_path = Path(f"Skins/{parent}")
            if (parent_path / "Graphics").exists():
                parent_path = parent_path / "Graphics"
            self.parent_graphics_path = parent_path

            parent_cfg = self.parent_graphics_path / "skin_config.json"
            if parent_cfg.exists():
                parent_data = json.loads(parent_cfg.read_text(encoding='utf-8'))
                for k, v in parent_data.items():
                    self.skin_config[k] = SkinInfo(
                        v.get('x', 0) * self.screen_scale,
                        v.get('y', 0) * self.screen_scale,
                        v.get('font_size', 0) * self.screen_scale,
                        v.get('width', 0) * self.screen_scale,
                        v.get('height', 0) * self.screen_scale,
                        v.get('text', dict()),
                    )
            else:
                logger.warning(f"Parent skin config not found: {parent_cfg}")

    def unload_textures(self):
        """Unload all textures and animations."""
        ids = {}  # Map ID to texture name
        for subset_name in self.textures:
            for texture_name in self.textures[subset_name]:
                tex_object = self.textures[subset_name][texture_name]
                if isinstance(tex_object.texture, list):
                    for i, texture in enumerate(tex_object.texture):
                        if texture.id in ids:
                            logger.warning(
                                f"Duplicate texture ID {texture.id}: "
                                f"{ids[texture.id]} and {subset_name}/{texture_name}[{i}]"
                            )
                        else:
                            ids[texture.id] = f"{subset_name}/{texture_name}[{i}]"
                            ray.UnloadTexture(texture)
                else:
                    if tex_object.texture.id in ids:
                        logger.warning(
                            f"Duplicate texture ID {tex_object.texture.id}: "
                            f"{ids[tex_object.texture.id]} and {subset_name}/{texture_name}"
                        )
                    else:
                        ids[tex_object.texture.id] = f"{subset_name}/{texture_name}"
                        ray.UnloadTexture(tex_object.texture)

        self.textures.clear()
        self.animations.clear()

        logger.info("All textures unloaded")

    def get_animation(self, index: int, is_copy: bool = False):
        """Get an animation by ID and returns a reference.
        Returns a copy of the animation if is_copy is True."""
        if index not in self.animations:
            raise Exception(f"Unable to find id {index} in loaded animations")
        if is_copy:
            new_anim = self.animations[index].copy()
            if self.animations[index].loop:
                new_anim.start()
            return new_anim
        if self.animations[index].loop:
            self.animations[index].start()
        return self.animations[index]

    def _read_tex_obj_data(self, tex_mapping: dict | list, tex_object: Texture | FramedTexture):
        if isinstance(tex_mapping, list):
            if not tex_mapping:
                return
            for i, mapping in enumerate(tex_mapping):
                if i == 0:
                    tex_object.x[i] = mapping.get("x", 0)
                    tex_object.y[i] = mapping.get("y", 0)
                    tex_object.x2[i] = mapping.get("x2", tex_object.width)
                    tex_object.y2[i] = mapping.get("y2", tex_object.height)
                    tex_object.controllable[i] = mapping.get("controllable", False)
                else:
                    tex_object.x.append(mapping.get("x", 0))
                    tex_object.y.append(mapping.get("y", 0))
                    tex_object.x2.append(mapping.get("x2", tex_object.width))
                    tex_object.y2.append(mapping.get("y2", tex_object.height))
                    tex_object.controllable.append(mapping.get("controllable", False))

                if "frame_order" in mapping and isinstance(tex_object, FramedTexture):
                    tex_object.texture = [tex_object.texture[j] for j in mapping["frame_order"]]

            if "crop" in tex_mapping[0]:
                tex_object.crop_data = tex_mapping[0]["crop"]
                for i in range(len(tex_object.x2)):
                    tex_object.x2[i] = tex_object.crop_data[0][2]
                    tex_object.y2[i] = tex_object.crop_data[0][3]
        else:
            tex_object.x = [tex_mapping.get("x", 0)]
            tex_object.y = [tex_mapping.get("y", 0)]
            tex_object.x2 = [tex_mapping.get("x2", tex_object.width)]
            tex_object.y2 = [tex_mapping.get("y2", tex_object.height)]
            tex_object.controllable = [tex_mapping.get("controllable", False)]
            if "frame_order" in tex_mapping and isinstance(tex_object, FramedTexture):
                tex_object.texture = [tex_object.texture[i] for i in tex_mapping["frame_order"]]
            if "crop" in tex_mapping:
                tex_object.crop_data = tex_mapping["crop"]
                tex_object.x2 = [tex_object.crop_data[0][2]]
                tex_object.y2 = [tex_object.crop_data[0][3]]

    def load_animations(self, screen_name: str):
        """Load animations for a screen, falling back to parent if not found."""
        screen_path = self.graphics_path / screen_name
        parent_screen_path = self.parent_graphics_path / screen_name

        if (screen_path / 'animation.json').exists():
            with open(screen_path / 'animation.json') as json_file:
                self.animations = parse_animations(json.loads(json_file.read()))
            logger.info(f"Animations loaded for screen: {screen_name}")
        elif self.parent_graphics_path != self.graphics_path and (parent_screen_path / 'animation.json').exists():
            with open(parent_screen_path / 'animation.json') as json_file:
                anim_json = json.loads(json_file.read())
                for anim in anim_json:
                    if "total_distance" in anim and not isinstance(anim["total_distance"], dict):
                        anim["total_distance"] = anim["total_distance"] * self.screen_scale
                self.animations = parse_animations(anim_json)
            logger.info(f"Animations loaded for screen: {screen_name} (from parent)")

    # TODO: rename to load_folder
    def load_zip(self, screen_name: str, subset: str, root_graphics_path: Optional[Path] = None):
        base_path = root_graphics_path or self.graphics_path
        folder = base_path / screen_name / subset
        if folder.stem in self.textures:
            return
        try:
            if not (folder / 'texture.json').exists():
                raise Exception(f"texture.json file missing from {folder}")

            with open(folder / 'texture.json') as json_file:
                tex_mapping_data: dict[str, dict] = json.load(json_file)
                self.textures[folder.stem] = dict()

            encoding = sys.getfilesystemencoding()
            for tex_name in tex_mapping_data:
                tex_dir = folder / tex_name
                tex_file = folder / f"{tex_name}.png"
                tex_mapping = tex_mapping_data[tex_name]

                if tex_dir.is_dir():
                    frames = [ray.LoadTexture(str(frame).encode(encoding)) for frame in sorted(tex_dir.iterdir(),
                                key=lambda x: int(x.stem)) if frame.is_file()]
                    self.textures[folder.stem][tex_name] = FramedTexture(tex_name, frames, tex_mapping)
                    self._read_tex_obj_data(tex_mapping, self.textures[folder.stem][tex_name])
                elif tex_file.is_file():
                    tex = ray.LoadTexture(str(tex_file).encode(encoding))
                    self.textures[folder.stem][tex_name] = Texture(tex_name, tex, tex_mapping)
                    self._read_tex_obj_data(tex_mapping, self.textures[folder.stem][tex_name])
                else:
                    logger.error(f"Texture {tex_name} was not found in {folder}")
            logger.info(f"Textures loaded from folder: {folder}")
        except Exception as e:
            logger.error(f"Failed to load textures from folder {folder}: {e}")

    def load_screen_textures(self, screen_name: str) -> None:
        """Load textures for a screen."""
        screen_path = self.graphics_path / screen_name
        parent_screen_path = self.parent_graphics_path / screen_name

        if not screen_path.exists():
            if self.parent_graphics_path != self.graphics_path and parent_screen_path.exists():
                logger.info(f"Textures for screen {screen_name} loaded from parent skin")
            else:
                logger.warning(f"Textures for Screen {screen_name} do not exist")
                return

        # Load animations
        self.load_animations(screen_name)

        # Load child skin subsets first, then fill missing subsets from the parent skin.
        if screen_path.exists():
            for subset_dir in screen_path.iterdir():
                if subset_dir.is_dir():
                    self.load_zip(screen_name, subset_dir.stem, self.graphics_path)
        if self.parent_graphics_path != self.graphics_path and parent_screen_path.exists():
            for subset_dir in parent_screen_path.iterdir():
                if subset_dir.is_dir():
                    self.load_zip(screen_name, subset_dir.stem, self.parent_graphics_path)

        logger.info(f"Screen textures loaded for: {screen_name}")

    def control(self, tex_object: Texture | FramedTexture, index: int = 0):
        '''debug function'''
        distance = 1
        if ray.IsKeyDown(ray.KEY_LEFT_SHIFT):
            distance = 10
        if ray.IsKeyPressed(ray.KEY_LEFT):
            tex_object.x[index] -= distance
            logger.info(f"{tex_object.name}: {tex_object.x[index]}, {tex_object.y[index]}")
        if ray.IsKeyPressed(ray.KEY_RIGHT):
            tex_object.x[index] += distance
            logger.info(f"{tex_object.name}: {tex_object.x[index]}, {tex_object.y[index]}")
        if ray.IsKeyPressed(ray.KEY_UP):
            tex_object.y[index] -= distance
            logger.info(f"{tex_object.name}: {tex_object.x[index]}, {tex_object.y[index]}")
        if ray.IsKeyPressed(ray.KEY_DOWN):
            tex_object.y[index] += distance
            logger.info(f"{tex_object.name}: {tex_object.x[index]}, {tex_object.y[index]}")

    def clear_screen(self, color: Color):
        if isinstance(color, tuple):
            clear_color = [color[0], color[1], color[2], color[3]]
        else:
            clear_color = [color.r, color.g, color.b, color.a]
        ray.ClearBackground(clear_color)

    def _draw_texture_untyped(self, subset: str, texture: str, color: tuple[int, int, int, int], frame: int, scale: float, center: bool,
                            mirror: str, x: float, y: float, x2: float, y2: float,
                            origin: tuple[float, float], rotation: float, fade: float,
                            index: int, src: Optional[tuple[float, float, float, float]], controllable: bool) -> None:
        if subset not in self.textures:
            return
        if texture not in self.textures[subset]:
            return
        mirror_x = -1 if mirror == 'horizontal' else 1
        mirror_y = -1 if mirror == 'vertical' else 1
        if fade != 1.1:
            final_color = ray.Fade(color, fade)
        else:
            final_color = color
        tex_object = self.textures[subset][texture]
        if src is not None:
            source_rect = src
        elif tex_object.crop_data is not None:
            source_rect = tex_object.crop_data[frame]
        else:
            source_rect = (0, 0, tex_object.width * mirror_x, tex_object.height * mirror_y)
        if center:
            dest_rect = (tex_object.x[index] + (tex_object.width//2) - ((tex_object.width * scale)//2) + x, tex_object.y[index] + (tex_object.height//2) - ((tex_object.height * scale)//2) + y, tex_object.x2[index]*scale + x2, tex_object.y2[index]*scale + y2)
        else:
            dest_rect = (tex_object.x[index] + x, tex_object.y[index] + y, tex_object.x2[index]*scale + x2, tex_object.y2[index]*scale + y2)
        if isinstance(tex_object, FramedTexture):
            if frame >= len(tex_object.texture):
                raise Exception(f"Frame {frame} not available in iterable texture {tex_object.name}")
            ray.DrawTexturePro(tex_object.texture[frame], source_rect, dest_rect, origin, rotation, final_color)
        else:
            ray.DrawTexturePro(tex_object.texture, source_rect, dest_rect, origin, rotation, final_color)
        if tex_object.controllable[index] or controllable:
            self.control(tex_object, index)

    def draw_texture(self, subset: str, texture: str, color: Color = Color(255, 255, 255, 255), frame: int = 0, scale: float = 1.0, center: bool = False,
                            mirror: str = '', x: float = 0, y: float = 0, x2: float = 0, y2: float = 0,
                            origin: Vector2 = Vector2(0,0), rotation: float = 0, fade: float = 1.1,
                            index: int = 0, src: Optional[Rectangle] = None, controllable: bool = False) -> None:
        """
        Wrapper function for raylib's draw_texture_pro().
        Parameters:
            subset (str): The subset of textures to use.
            texture (str): The name of the texture to draw.
            color (ray.Color): The color to tint the texture.
            frame (int): The frame of the texture to draw. Only used if the texture is animated.
            scale (float): The scale factor to apply to the texture.
            center (bool): Whether to center the texture.
            mirror (str): The direction to mirror the texture, either 'horizontal' or 'vertical'.
            x (float): An x-value added to the top-left corner of the texture.
            y (float): The y-value added to the top-left corner of the texture.
            x2 (float): The x-value added to the bottom-right corner of the texture.
            y2 (float): The y-value added to the bottom-right corner of the texture.
            origin (ray.Vector2): The origin point of the texture.
            rotation (float): The rotation angle of the texture.
            fade (float): The fade factor to apply to the texture.
            index (int): The index of the position data for the texture. Only used if the texture has multiple positions.
            src (Optional[ray.Rectangle]): The source rectangle of the texture.
            controllable (bool): Whether the texture is controllable.
        """
        if src is not None:
            src_data = (src.x, src.y, src.width, src.height)
        else:
            src_data = None
        if isinstance(color, tuple):
            color_data = (color[0], color[1], color[2], color[3])
        else:
            color_data = (color.r, color.g, color.b, color.a)
        self._draw_texture_untyped(subset, texture, color_data, frame, scale, center, mirror, x, y, x2, y2, (origin.x, origin.y), rotation, fade, index, src_data, controllable)

tex = TextureWrapper()
