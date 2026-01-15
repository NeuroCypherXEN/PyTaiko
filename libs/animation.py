import time
from typing import Any, Optional

from libs.global_data import global_data

def get_current_ms() -> float:
    return time.time() * 1000


class BaseAnimation():
    def __init__(self, duration: float, delay: float = 0.0, loop: bool = False, lock_input: bool = False) -> None:
        """
        Initialize a base animation.

        Args:
            duration: Length of the animation in milliseconds
            delay: Time to wait before starting the animation
            reverse_delay: If provided, animation will play in reverse after this delay
        """
        self.duration = duration
        self.delay = delay
        self.delay_saved = delay
        self.start_ms = get_current_ms()
        self.is_finished = False
        self.attribute = 0
        self.is_started = False
        self.is_reversing = False
        self.unlocked = False
        self.loop = loop
        self.lock_input = lock_input

    def __repr__(self):
        return str(self.__dict__)

    def __str__(self):
        return str(self.__dict__)

    def update(self, current_time_ms: float) -> None:
        """Update the animation based on the current time."""
        if self.loop and self.is_finished:
            self.restart()
        if self.lock_input and self.is_finished and not self.unlocked:
            self.unlocked = True
            global_data.input_locked -= 1

    def restart(self) -> None:
        """Restarts the animation."""
        self.start_ms = get_current_ms()
        self.is_finished = False
        self.delay = self.delay_saved
        self.unlocked = False
        if self.lock_input:
            global_data.input_locked += 1

    def start(self) -> None:
        """Starts the animation. Functionally the same as
        restart() if it has been called before"""
        self.is_started = True
        self.restart()

    def pause(self):
        """Pauses the animation."""
        self.is_started = False
        if self.lock_input:
            global_data.input_locked -= 1

    def unpause(self):
        """Unpauses the animation."""
        self.is_started = True
        if self.lock_input:
            global_data.input_locked += 1

    def reset(self):
        """Resets the animation without starting it."""
        self.restart()
        self.pause()

    def copy(self):
        """Create a copy of the animation with reset state."""
        new_anim = self.__class__.__new__(self.__class__)
        new_anim.duration = self.duration
        new_anim.delay = self.delay_saved
        new_anim.delay_saved = self.delay_saved
        new_anim.start_ms = get_current_ms()
        new_anim.is_finished = False
        new_anim.attribute = 0
        new_anim.is_started = False
        new_anim.is_reversing = False
        new_anim.unlocked = False
        new_anim.loop = self.loop
        new_anim.lock_input = self.lock_input
        return new_anim

    def _ease_in(self, progress: float, ease_type: str) -> float:
        if ease_type == "quadratic":
            return progress * progress
        elif ease_type == "cubic":
            return progress * progress * progress
        elif ease_type == "exponential":
            return 0 if progress == 0 else pow(2, 10 * (progress - 1))
        return progress

    def _ease_out(self, progress: float, ease_type: str) -> float:
        if ease_type == "quadratic":
            return progress * (2 - progress)
        elif ease_type == "cubic":
            return 1 - pow(1 - progress, 3)
        elif ease_type == "exponential":
            return 1 if progress == 1 else 1 - pow(2, -10 * progress)
        return progress

    def _apply_easing(self, progress: float, ease_in: Optional[str] = None,
                         ease_out: Optional[str] = None) -> float:
        if ease_in:
            return self._ease_in(progress, ease_in)
        elif ease_out:
            return self._ease_out(progress, ease_out)
        return progress

class FadeAnimation(BaseAnimation):
    def __init__(self, duration: float, initial_opacity: float = 1.0, loop: bool = False,
                     lock_input: bool = False, final_opacity: float = 0.0, delay: float = 0.0,
                     ease_in: Optional[str] = None, ease_out: Optional[str] = None,
                     reverse_delay: Optional[float] = None) -> None:
        super().__init__(duration, delay=delay, loop=loop, lock_input=lock_input)
        self.initial_opacity = initial_opacity
        self.attribute = initial_opacity
        self.final_opacity = final_opacity
        self.initial_opacity_saved = initial_opacity
        self.final_opacity_saved = final_opacity
        self.ease_in = ease_in
        self.ease_out = ease_out
        self.reverse_delay = reverse_delay
        self.reverse_delay_saved = reverse_delay

    def restart(self) -> None:
        super().restart()
        self.reverse_delay = self.reverse_delay_saved
        self.initial_opacity = self.initial_opacity_saved
        self.final_opacity = self.final_opacity_saved
        self.attribute = self.initial_opacity

    def copy(self):
        """Create a copy of the fade animation with reset state."""
        new_anim = super().copy()
        new_anim.initial_opacity = self.initial_opacity_saved
        new_anim.initial_opacity_saved = self.initial_opacity_saved
        new_anim.final_opacity = self.final_opacity_saved
        new_anim.final_opacity_saved = self.final_opacity_saved
        new_anim.ease_in = self.ease_in
        new_anim.ease_out = self.ease_out
        new_anim.reverse_delay = self.reverse_delay_saved
        new_anim.reverse_delay_saved = self.reverse_delay_saved
        new_anim.attribute = self.initial_opacity_saved
        return new_anim

    def update(self, current_time_ms: float) -> None:
        if not self.is_started:
            return
        super().update(current_time_ms)
        elapsed_time = current_time_ms - self.start_ms

        if elapsed_time <= self.delay:
            self.attribute = self.initial_opacity
        elif elapsed_time >= self.delay + self.duration:
            self.attribute = self.final_opacity

            if self.reverse_delay is not None:
                self.start_ms = current_time_ms
                self.delay = self.reverse_delay
                self.initial_opacity, self.final_opacity = self.final_opacity, self.initial_opacity
                self.reverse_delay = None
                self.is_reversing = True
            else:
                self.is_finished = True
        else:
            animation_time = elapsed_time - self.delay
            progress = animation_time / self.duration
            progress = max(0.0, min(1.0, progress))
            progress = self._apply_easing(progress, self.ease_in, self.ease_out)
            self.attribute = self.initial_opacity + progress * (self.final_opacity - self.initial_opacity)

class MoveAnimation(BaseAnimation):
    def __init__(self, duration: float, total_distance: int = 0, loop: bool = False,
                      lock_input: bool = False, start_position: int = 0, delay: float = 0.0,
                      reverse_delay: Optional[float] = None,
                      ease_in: Optional[str] = None, ease_out: Optional[str] = None) -> None:
        super().__init__(duration, delay=delay, loop=loop, lock_input=lock_input)
        self.reverse_delay = reverse_delay
        self.reverse_delay_saved = reverse_delay
        self.total_distance = total_distance
        self.start_position = start_position
        self.total_distance_saved = total_distance
        self.start_position_saved = start_position
        self.ease_in = ease_in
        self.ease_out = ease_out

    def restart(self) -> None:
        super().restart()
        self.reverse_delay = self.reverse_delay_saved
        self.total_distance = self.total_distance_saved
        self.start_position = self.start_position_saved
        self.attribute = self.start_position

    def copy(self):
        """Create a copy of the move animation with reset state."""
        new_anim = super().copy()
        new_anim.reverse_delay = self.reverse_delay_saved
        new_anim.reverse_delay_saved = self.reverse_delay_saved
        new_anim.total_distance = self.total_distance_saved
        new_anim.total_distance_saved = self.total_distance_saved
        new_anim.start_position = self.start_position_saved
        new_anim.start_position_saved = self.start_position_saved
        new_anim.ease_in = self.ease_in
        new_anim.ease_out = self.ease_out
        new_anim.attribute = self.start_position_saved
        return new_anim

    def update(self, current_time_ms: float) -> None:
        if not self.is_started:
            return
        super().update(current_time_ms)
        elapsed_time = current_time_ms - self.start_ms
        if elapsed_time < self.delay:
            self.attribute = self.start_position

        elif elapsed_time >= self.delay + self.duration:
            self.attribute = self.start_position + self.total_distance
            if self.reverse_delay is not None:
                self.start_ms = current_time_ms
                self.delay = self.reverse_delay
                self.start_position = self.start_position + self.total_distance
                self.total_distance = -(self.total_distance)
                self.reverse_delay = None
            else:
                self.is_finished = True
        else:
            progress = (elapsed_time - self.delay) / self.duration
            progress = self._apply_easing(progress, self.ease_in, self.ease_out)
            self.attribute = self.start_position + (self.total_distance * progress)

class TextureChangeAnimation(BaseAnimation):
    def __init__(self, duration: float, textures: list[tuple[float, float, int]],
                       loop: bool = False, lock_input: bool = False, delay: float = 0.0) -> None:
        super().__init__(duration, loop=loop, lock_input=lock_input)
        self.textures = textures
        self.delay = delay
        self.delay_saved = delay
        self.attribute = textures[0][2]

    def reset(self):
        super().reset()
        self.attribute = self.textures[0][2]

    def copy(self):
        """Create a copy of the texture change animation with reset state."""
        new_anim = super().copy()
        new_anim.textures = self.textures  # List of tuples, can be shared
        new_anim.attribute = self.textures[0][2]
        return new_anim

    def update(self, current_time_ms: float) -> None:
        if not self.is_started:
            return
        super().update(current_time_ms)
        elapsed_time = current_time_ms - self.start_ms
        if elapsed_time < self.delay:
            return

        animation_time = elapsed_time - self.delay
        if animation_time <= self.duration:
            for start, end, index in self.textures:
                if start < animation_time <= end:
                    self.attribute = index
        else:
            self.is_finished = True

class TextStretchAnimation(BaseAnimation):
    def copy(self):
        """Create a copy of the text stretch animation with reset state."""
        return super().copy()

    def update(self, current_time_ms: float) -> None:
        if not self.is_started:
            return
        super().update(current_time_ms)
        elapsed_time = current_time_ms - self.start_ms
        if elapsed_time < self.delay:
            return

        animation_time = elapsed_time - self.delay
        if animation_time <= self.duration:
            self.attribute = 2 + 5 * (animation_time // 25)
        elif animation_time <= self.duration + 116:
            frame_time = (animation_time - self.duration) // 16.57
            self.attribute = 2 + 10 - (2 * (frame_time + 1))
        else:
            self.attribute = 0
            self.is_finished = True

class TextureResizeAnimation(BaseAnimation):
    def __init__(self, duration: float, initial_size: float = 1.0,
                     loop: bool = False, lock_input: bool = False,
                     final_size: float = 0.0, delay: float = 0.0,
                     reverse_delay: Optional[float] = None,
                     ease_in: Optional[str] = None, ease_out: Optional[str] = None) -> None:
        super().__init__(duration, delay=delay, loop=loop, lock_input=lock_input)
        self.initial_size = initial_size
        self.final_size = final_size
        self.reverse_delay = reverse_delay
        self.initial_size_saved = initial_size
        self.final_size_saved = final_size
        self.reverse_delay_saved = reverse_delay
        self.ease_in = ease_in
        self.ease_out = ease_out
        self.attribute = self.initial_size

    def restart(self) -> None:
        super().restart()
        self.reverse_delay = self.reverse_delay_saved
        self.initial_size = self.initial_size_saved
        self.final_size = self.final_size_saved

    def copy(self):
        """Create a copy of the texture resize animation with reset state."""
        new_anim = super().copy()
        new_anim.initial_size = self.initial_size_saved
        new_anim.initial_size_saved = self.initial_size_saved
        new_anim.final_size = self.final_size_saved
        new_anim.final_size_saved = self.final_size_saved
        new_anim.reverse_delay = self.reverse_delay_saved
        new_anim.reverse_delay_saved = self.reverse_delay_saved
        new_anim.ease_in = self.ease_in
        new_anim.ease_out = self.ease_out
        new_anim.attribute = self.initial_size_saved
        return new_anim


    def update(self, current_time_ms: float) -> None:
        if not self.is_started:
            return
        else:
            self.is_started = not self.is_finished
        super().update(current_time_ms)
        elapsed_time = current_time_ms - self.start_ms

        if elapsed_time <= self.delay:
            self.attribute = self.initial_size
        elif elapsed_time >= self.delay + self.duration:
            self.attribute = self.final_size

            if self.reverse_delay is not None:
                self.start_ms = current_time_ms
                self.delay = self.reverse_delay
                self.initial_size, self.final_size = self.final_size, self.initial_size
                self.reverse_delay = None
            else:
                self.is_finished = True
        else:
            animation_time = elapsed_time - self.delay
            progress = animation_time / self.duration
            progress = self._apply_easing(progress, self.ease_in, self.ease_out)
            self.attribute = self.initial_size + ((self.final_size - self.initial_size) * progress)


class Animation:
    """Factory for creating different types of animations."""

    @staticmethod
    def create_fade(duration: float, **kwargs) -> FadeAnimation:
        """Create a fade animation.

        Args:
            duration: Length of the fade in milliseconds
            delay: Time to wait before starting the fade
            initial_opacity: Default is 1.0
            final_opacity: Default is 0.0
            reverse_delay: If provided, fade will play in reverse after this delay
            ease_in: Control ease into the fade
            ease_out: Control ease out of the fade

        Easing options:
            quadratic,
            cubic,
            exponential
        """
        return FadeAnimation(duration, **kwargs)

    @staticmethod
    def create_move(duration: float, **kwargs) -> MoveAnimation:
        """Create a movement animation.

        Args:
            duration: Length of the move in milliseconds
            start_position: The coordinates of the object before the move
            total_distance: The distance travelled from the start to end position
            reverse_delay: If provided, move will play in reverse after this delay
            delay: Time to wait before starting the move
            ease_in: Control ease into the move
            ease_out: Control ease out of the move

        Easing options:
            quadratic,
            cubic,
            exponential
        """
        return MoveAnimation(duration, **kwargs)


    @staticmethod
    def create_texture_change(duration: float, **kwargs) -> TextureChangeAnimation:
        """Create a texture change animation

        Args:
            duration: Length of the change in milliseconds
            textures: Passed in as a tuple of the starting millisecond, ending millisecond, and texture index
            delay: Time to wait before starting the change
        """
        return TextureChangeAnimation(duration, **kwargs)

    @staticmethod
    def create_text_stretch(duration: float, **kwargs) -> TextStretchAnimation:
        """Create a text stretch animation.

        Args:
            duration: Length of the stretch in milliseconds
            delay: Time to wait before starting the stretch
        """
        return TextStretchAnimation(duration, **kwargs)

    @staticmethod
    def create_texture_resize(duration: float, **kwargs) -> TextureResizeAnimation:
        """Create a texture resize animation.

        Args:
            duration: Length of the change in milliseconds
            initial_size: Default is 1.0
            final_size: Default is 0.0
            delay: Time to wait before starting the resize
            reverse_delay: If provided, resize will play in reverse after this delay
        """
        return TextureResizeAnimation(duration, **kwargs)

ANIMATION_CLASSES = {
    "fade": FadeAnimation,
    "move": MoveAnimation,
    "texture_change": TextureChangeAnimation,
    "text_stretch": TextStretchAnimation,
    "texture_resize": TextureResizeAnimation
}

def parse_animations(animation_json):
    """Processes animations from a json file, including
    ones with references to other animations, returns a dictionary"""
    raw_anims = {}
    for item in animation_json:
        if "id" not in item:
            raise Exception("Animation requires id")
        if "type" not in item:
            raise Exception("Animation requires type")

        raw_anims[item["id"]] = item.copy()

    def find_refs(anim_id: int, visited: Optional[set] = None):
        if visited is None:
            visited = set()

        if anim_id in visited:
            raise Exception(f"Circular reference detected involving animation {anim_id}")

        visited.add(anim_id)
        animation = raw_anims[anim_id].copy()

        for key, value in animation.items():
            if isinstance(value, dict) and "reference_id" in value:
                animation[key] = resolve_value(value, visited.copy())

        visited.remove(anim_id)
        return animation

    def resolve_value(ref_obj: dict[str, Any], visited: set):
        if "property" not in ref_obj:
            raise Exception("Reference requires 'property' field")

        ref_id = ref_obj["reference_id"]
        ref_property = ref_obj["property"]

        if ref_id not in raw_anims:
            raise Exception(f"Referenced animation {ref_id} not found")

        resolved_ref_animation = find_refs(ref_id, visited)

        if ref_property not in resolved_ref_animation:
            raise Exception(f"Property '{ref_property}' not found in animation {ref_id}")

        base_value = resolved_ref_animation[ref_property]

        if "init_val" in ref_obj:
            init_val = ref_obj["init_val"]

            if isinstance(init_val, dict) and "reference_id" in init_val:
                init_val = resolve_value(init_val, visited)

            try:
                return base_value + init_val
            except TypeError:
                raise Exception(f"Cannot add init_val {init_val} to referenced value {base_value}")

        return base_value

    anim_dict = dict()

    for id in raw_anims:
        absolute_anim = find_refs(id)
        type = absolute_anim.pop("type")
        id_val = absolute_anim.pop("id")
        if "comment" in absolute_anim:
            absolute_anim.pop("comment")
        if type not in ANIMATION_CLASSES:
            raise Exception(f"Unknown Animation type: {type}")

        anim_class = ANIMATION_CLASSES[type]

        anim_object = anim_class(**absolute_anim)
        anim_dict[id_val] = anim_object

    return anim_dict
