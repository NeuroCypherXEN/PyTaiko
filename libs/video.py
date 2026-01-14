import logging
from pathlib import Path

import av
import raylib as ray

from libs.audio import audio
from libs.texture import tex
from libs.utils import get_current_ms

logger = logging.getLogger(__name__)

class VideoPlayer:
    def __init__(self, path: Path):
        """Initialize a video player instance"""
        self.is_finished_list = [False, False]
        self.is_static = False
        if path.suffix == '.png' or path.suffix == '.jpg':
            self.texture = ray.LoadTexture(str(path).encode('utf-8'))
            self.is_static = True
            return

        self.container = av.open(str(path))
        self.video_stream = self.container.streams.video[0]

        self.audio = None
        if self.container.streams.audio:
            # Extract audio to temporary file
            audio_container = av.open(str(path))
            audio_stream = audio_container.streams.audio[0]

            output = av.open("cache/temp_audio.wav", 'w')
            output_stream = output.add_stream('pcm_s16le', rate=audio_stream.rate)

            for frame in audio_container.decode(audio=0):
                for packet in output_stream.encode(frame):
                    output.mux(packet)

            for packet in output_stream.encode():
                output.mux(packet)

            output.close()
            audio_container.close()

            self.audio = audio.load_music_stream(Path("cache/temp_audio.wav"), 'video')

        self.texture = None
        self.current_frame_data = None

        # Get video properties
        if self.video_stream.average_rate is not None:
            self.fps = float(self.video_stream.average_rate)
        else:
            self.fps = 0
        self.duration = float(self.container.duration) / av.time_base if self.container.duration else 0
        self.width = self.video_stream.width
        self.height = self.video_stream.height

        # Calculate frame timestamps
        frame_count = int(self.duration * self.fps) + 1
        self.frame_timestamps: list[float] = [(i * 1000) / self.fps for i in range(frame_count)]

        self.start_ms = None
        self.frame_index = 0
        self.frame_duration = 1000 / self.fps
        self.audio_played = False

        # Cache for decoded frames
        self.frame_generator = None
        self.current_decoded_frame = None

    def _audio_manager(self):
        if self.audio is None:
            return
        if self.is_finished_list[1]:
            return
        if not self.audio_played:
            audio.play_music_stream(self.audio, 'attract_mode')
            self.audio_played = True
        audio.update_music_stream(self.audio)
        self.is_finished_list[1] = audio.get_music_time_length(self.audio) <= audio.get_music_time_played(self.audio)

    def _init_frame_generator(self):
        """Initialize the frame generator for sequential decoding"""
        self.container.seek(0)
        self.frame_generator = self.container.decode(video=0)

    def _get_next_frame_bytes(self):
        """Get the next frame as raw RGB bytes"""
        try:
            if self.frame_generator is None:
                self._init_frame_generator()

            if self.frame_generator is not None:
                frame = next(self.frame_generator)
            else:
                raise Exception("Frame generator is not initialized")
            # Convert frame to RGB24 format
            frame = frame.reformat(format='rgb24')

            # Get raw bytes from the frame planes
            # For RGB24, all data is in plane 0
            plane = frame.planes[0]
            frame_bytes = bytes(plane)

            return frame_bytes, frame.width, frame.height
        except StopIteration:
            return None, None, None
        except Exception as e:
            logger.error(f"Error getting next frame: {e}")
            return None, None, None

    def _load_frame(self, index: int):
        """Load a specific frame and update the texture"""
        if index >= len(self.frame_timestamps) or index < 0:
            return False

        try:
            # For sequential playback, just get the next frame
            frame_bytes, width, height = self._get_next_frame_bytes()

            if frame_bytes is None:
                return False

            if self.texture is None:
                pixels_ptr = ray.ffi.cast('void *', ray.ffi.from_buffer('unsigned char[]', frame_bytes))

                image = ray.ffi.new('Image *', {
                    'data': pixels_ptr,
                    'width': width,
                    'height': height,
                    'mipmaps': 1,
                    'format': ray.PIXELFORMAT_UNCOMPRESSED_R8G8B8
                })
                self.texture = ray.LoadTextureFromImage(image[0])
                ray.SetTextureFilter(self.texture, ray.TEXTURE_FILTER_TRILINEAR)
            else:
                pixels_ptr = ray.ffi.cast('void *', ray.ffi.from_buffer('unsigned char[]', frame_bytes))
                ray.UpdateTexture(self.texture, pixels_ptr)

            self.current_frame_data = frame_bytes
            return True
        except Exception as e:
            logger.error(f"Error loading frame at index {index}: {e}")
            return False

    def is_started(self) -> bool:
        """Returns boolean value if the video has begun"""
        return self.start_ms is not None

    def start(self, current_ms: float) -> None:
        """Start video playback at call time"""
        if self.is_static:
            return
        self.start_ms = current_ms
        self._init_frame_generator()
        self._load_frame(0)

    def is_finished(self) -> bool:
        """Check if video is finished playing"""
        return all(self.is_finished_list)

    def set_volume(self, volume: float) -> None:
        """Set video volume, takes float value from 0.0 to 1.0"""
        if self.is_static:
            return
        if self.audio is not None:
            audio.set_music_volume(self.audio, volume)

    def update(self):
        """Updates video playback, advancing frames and audio"""
        if self.is_static:
            return
        self._audio_manager()

        if self.frame_index >= len(self.frame_timestamps):
            self.is_finished_list[0] = True
            return

        if self.start_ms is None:
            return

        elapsed_time = get_current_ms() - self.start_ms

        # Check if we need to advance frames
        target_frame = 0
        for i, timestamp in enumerate(self.frame_timestamps):
            if elapsed_time >= timestamp:
                target_frame = i
            else:
                break

        # Load frames sequentially until we reach the target
        while self.frame_index <= target_frame and self.frame_index < len(self.frame_timestamps):
            self._load_frame(self.frame_index)
            self.frame_index += 1

    def draw(self):
        """Draw video frames to the raylib canvas"""
        if self.texture is not None:
            ray.DrawTexturePro(
                self.texture,
                (0, 0, self.texture.width, self.texture.height),
                (0, 0, tex.screen_width, tex.screen_height),
                (0, 0),
                0,
                ray.WHITE
            )

    def stop(self):
        """Stops the video, audio, and clears its buffer"""
        if self.is_static:
            if self.texture is not None:
                ray.UnloadTexture(self.texture)
                self.texture = None
            return
        if self.container:
            self.container.close()

        if self.texture is not None:
            ray.UnloadTexture(self.texture)
            self.texture = None

        if self.audio is not None:
            if audio.is_music_stream_playing(self.audio):
                audio.stop_music_stream(self.audio)
            audio.unload_music_stream(self.audio)

        if Path("cache/temp_audio.wav").exists():
            Path("cache/temp_audio.wav").unlink()
