import logging
from typing import Any

from libs.audio import audio
from libs.texture import tex

logger = logging.getLogger(__name__)

class Screen:
    def __init__(self, name: str):
        self.screen_init = False
        self.screen_name = name

    def _load_resources(self) -> None:
        tex.load_screen_textures(self.screen_name)
        logger.info(f"Loaded textures for screen: {self.screen_name}")
        audio.load_screen_sounds(self.screen_name)
        logger.info(f"Loaded sounds for screen: {self.screen_name}")

    def _unload_resources(self, next_screen: str) -> None:
        audio.unload_all_sounds()
        audio.unload_all_music()
        logger.info(f"Unloaded sounds for screen: {next_screen}")
        tex.unload_textures()
        logger.info(f"Unloaded textures for screen: {next_screen}")

    def _do_screen_start(self) -> Any:
        if not self.screen_init:
            self.screen_init = True
            self.on_screen_start()
            logger.info(f"{self.__class__.__name__} initialized")
        return None

    def on_screen_start(self) -> Any:
        """Load screen resources."""
        self._load_resources()

    def on_screen_end(self, next_screen: str) -> str:
        """Unload resources and return the next screen name."""
        self.screen_init = False
        logger.info(f"{self.__class__.__name__} ended, transitioning to {next_screen} screen")
        self._unload_resources(next_screen)
        return next_screen

    def update(self) -> Any:
        return self._do_screen_start()

    def draw(self) -> None:
        pass

    def _do_draw(self) -> None:
        if self.screen_init:
            self.draw()
