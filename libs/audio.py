import logging
import platform
from pathlib import Path
from typing import Iterator

import cffi

from libs.config import VolumeConfig, get_config

ffi = cffi.FFI()

ffi.cdef("""
    typedef int PaHostApiIndex;
    // Forward declarations
    struct audio_buffer;

    // Type definitions
    typedef struct wave {
        unsigned int frameCount;
        unsigned int sampleRate;
        unsigned int sampleSize;
        unsigned int channels;
        void *data;
    } wave;

    typedef struct audio_stream {
        struct audio_buffer *buffer;
        unsigned int sampleRate;
        unsigned int sampleSize;
        unsigned int channels;
    } audio_stream;

    typedef struct sound {
        audio_stream stream;
        unsigned int frameCount;
    } sound;

    typedef struct music {
        audio_stream stream;
        unsigned int frameCount;
        void *ctxData;
    } music;

    void set_log_level(int level);

    // Device management
    void list_host_apis(void);
    const char* get_host_api_name(PaHostApiIndex hostApi);
    void init_audio_device(PaHostApiIndex host_api, double sample_rate, unsigned long buffer_size);
    void close_audio_device(void);
    bool is_audio_device_ready(void);
    void set_master_volume(float volume);
    float get_master_volume(void);

    // Wave management
    wave load_wave(const char* filename);
    bool is_wave_valid(wave wave);
    void unload_wave(wave wave);

    // Sound management
    sound load_sound_from_wave(wave wave);
    sound load_sound(const char* filename);
    bool is_sound_valid(sound sound);
    void unload_sound(sound sound);
    void play_sound(sound sound);
    void pause_sound(sound sound);
    void resume_sound(sound sound);
    void stop_sound(sound sound);
    bool is_sound_playing(sound sound);
    void set_sound_volume(sound sound, float volume);
    void set_sound_pitch(sound sound, float pitch);
    void set_sound_pan(sound sound, float pan);

    // Audio stream management
    audio_stream load_audio_stream(unsigned int sample_rate, unsigned int sample_size, unsigned int channels);
    void unload_audio_stream(audio_stream stream);
    void play_audio_stream(audio_stream stream);
    void pause_audio_stream(audio_stream stream);
    void resume_audio_stream(audio_stream stream);
    bool is_audio_stream_playing(audio_stream stream);
    void stop_audio_stream(audio_stream stream);
    void set_audio_stream_volume(audio_stream stream, float volume);
    void set_audio_stream_pitch(audio_stream stream, float pitch);
    void set_audio_stream_pan(audio_stream stream, float pan);
    void update_audio_stream(audio_stream stream, const void *data, int frame_count);

    // Music management
    music load_music_stream(const char* filename);
    bool is_music_valid(music music);
    void unload_music_stream(music music);
    void play_music_stream(music music);
    void pause_music_stream(music music);
    void resume_music_stream(music music);
    void stop_music_stream(music music);
    void seek_music_stream(music music, float position);
    bool music_stream_needs_update(music music);
    void update_music_stream(music music);
    bool is_music_stream_playing(music music);
    void set_music_volume(music music, float volume);
    void set_music_pitch(music music, float pitch);
    void set_music_pan(music music, float pan);
    float get_music_time_length(music music);
    float get_music_time_played(music music);

    // Memory management
    void free(void *ptr);
""")

logger = logging.getLogger(__name__)

try:
    if platform.system() == "Windows":
        lib = ffi.dlopen("libaudio.dll")
    elif platform.system() == "Darwin":
        lib = ffi.dlopen("./libaudio.dylib")
    else:  # Assume Linux/Unix
        lib = ffi.dlopen("./libaudio.so")
except OSError as e:
    logger.error(f"Failed to load shared library: {e}")
    raise

class AudioEngine:
    """Initialize an audio engine for playing sounds and music."""
    def __init__(self, device_type: int, sample_rate: float, buffer_size: int,
                 volume_presets: VolumeConfig, sounds_path: Path | None = None):
        self.device_type = max(device_type, 0)
        if sample_rate < 0:
            self.target_sample_rate = 44100
        else:
            self.target_sample_rate = sample_rate
        self.buffer_size = buffer_size
        self.sounds = {}
        self.music_streams = {}
        self.audio_device_ready = False
        self.volume_presets = volume_presets
        self.don = None
        self.kat = None

        if sounds_path is None:
            self.sounds_path = Path(f"Skins/{get_config()['paths']['skin']}/Sounds")
        else:
            self.sounds_path = sounds_path

    # Centralized path encoding helper for platform-specific filename handling.
    def _encode_path(self, file_path: Path) -> bytes:
        if platform.system() == 'Windows':
            return str(file_path).encode('cp932', errors='replace')
        return str(file_path).encode('utf-8')

    def _load_sound_with_fallback(self, file_path: Path):
        sound = lib.load_sound(self._encode_path(file_path))  # type: ignore
        if not lib.is_sound_valid(sound):  # type: ignore
            sound = lib.load_sound(str(file_path).encode('utf-8'))  # type: ignore
        return sound

    def _load_music_with_fallback(self, file_path: Path):
        music = lib.load_music_stream(self._encode_path(file_path))  # type: ignore
        if not lib.is_music_valid(music):  # type: ignore
            music = lib.load_music_stream(str(file_path).encode('utf-8'))  # type: ignore
        return music

    def _resolve_volume(self, volume_preset: str) -> float | None:
        if not volume_preset:
            return None
        if volume_preset not in self.volume_presets:
            logger.warning(f"Unknown volume preset: {volume_preset}")
            return None
        return self.volume_presets[volume_preset]

    def _get_sound(self, name: str, warn: bool = True):
        if name == 'don':
            if self.don is None and warn:
                logger.warning("Sound don not initialized")
            return self.don
        if name == 'kat':
            if self.kat is None and warn:
                logger.warning("Sound kat not initialized")
            return self.kat
        sound = self.sounds.get(name)
        if sound is None and warn:
            logger.warning(f"Sound {name} not found")
        return sound

    def _get_music(self, name: str, warn: bool = True):
        music = self.music_streams.get(name)
        if music is None and warn:
            logger.warning(f"Music stream {name} not found")
        return music

    def _iter_sound_files(self, root: Path) -> Iterator[tuple[Path, str]]:
        for sound in root.iterdir():
            if sound.is_dir():
                for file in sound.iterdir():
                    if file.is_file():
                        yield file, f"{sound.stem}_{file.stem}"
            elif sound.is_file():
                yield sound, sound.stem

    def set_log_level(self, level: int):
        lib.set_log_level(level) # type: ignore

    def list_host_apis(self):
        """Prints a list of available host APIs to the console"""
        lib.list_host_apis() # type: ignore

    def get_host_api_name(self, api_id: int) -> str:
        """Returns the name of the host API with the given ID"""
        result = lib.get_host_api_name(api_id) # type: ignore
        if result == ffi.NULL:
            return ""
        result = ffi.string(result)
        if isinstance(result, bytes):
            result = result.decode('utf-8')
        return result

    def init_audio_device(self) -> bool:
        """Initialize the audio device"""
        try:
            lib.init_audio_device(self.device_type, self.target_sample_rate, self.buffer_size) # type: ignore
            self.audio_device_ready = lib.is_audio_device_ready() # type: ignore
            self.don = self._load_sound_with_fallback(self.sounds_path / 'don.wav')
            self.kat = self._load_sound_with_fallback(self.sounds_path / 'ka.wav')
            if self.audio_device_ready:
                logger.info("Audio device initialized successfully")
            return self.audio_device_ready
        except Exception as e:
            logger.error(f"Failed to initialize audio device: {e}")
            return False

    def close_audio_device(self) -> None:
        """Close the audio device"""
        try:
            # Clean up all sounds and music
            for sound_id in list(self.sounds.keys()):
                self.unload_sound(sound_id)
            for music_id in list(self.music_streams.keys()):
                self.unload_music_stream(music_id)

            if self.don is not None:
                lib.unload_sound(self.don)  # type: ignore
                self.don = None
            if self.kat is not None:
                lib.unload_sound(self.kat)  # type: ignore
                self.kat = None
            lib.close_audio_device() # type: ignore
            self.audio_device_ready = False
            logger.info("Audio device closed")
        except Exception as e:
            logger.error(f"Error closing audio device: {e}")

    def is_audio_device_ready(self) -> bool:
        """Check if audio device is ready"""
        return lib.is_audio_device_ready() # type: ignore

    def set_master_volume(self, volume: float) -> None:
        """Set master volume (0.0 to 1.0)"""
        lib.set_master_volume(max(0.0, min(1.0, volume))) # type: ignore

    def get_master_volume(self) -> float:
        """Get master volume"""
        return lib.get_master_volume() # type: ignore

    # Sound management
    def load_sound(self, file_path: Path, name: str) -> str:
        """Load a sound file and return sound ID"""
        try:
            sound = self._load_sound_with_fallback(file_path)
            if lib.is_sound_valid(sound): # type: ignore
                self.sounds[name] = sound
                return name
            logger.error(f"Failed to load sound: {file_path}")
            return ""
        except Exception as e:
            logger.error(f"Error loading sound {file_path}: {e}")
            return ""

    def unload_sound(self, name: str) -> None:
        """Unload a sound by name"""
        if name in self.sounds:
            lib.unload_sound(self.sounds[name]) # type: ignore
            del self.sounds[name]
        else:
            logger.warning(f"Sound {name} not found")

    def load_screen_sounds(self, screen_name: str) -> None:
        """Load sounds for a given screen"""
        path = self.sounds_path / screen_name
        if not path.exists():
            logger.warning(f"Sounds for screen {screen_name} not found")
            return
        for file, sound_id in self._iter_sound_files(path):
            self.load_sound(file, sound_id)

        path = self.sounds_path / 'global'
        if path.exists():
            for file, sound_id in self._iter_sound_files(path):
                self.load_sound(file, sound_id)
        else:
            logger.info("Global sounds directory not found, skipping")

    def unload_all_sounds(self):
        """Unload all sounds"""
        for name in list(self.sounds.keys()):
            self.unload_sound(name)

    def play_sound(self, name: str, volume_preset: str) -> None:
        """Play a sound"""
        sound = self._get_sound(name)
        if sound is None:
            return
        volume = self._resolve_volume(volume_preset)
        if volume is not None:
            lib.set_sound_volume(sound, volume)  # type: ignore
        lib.play_sound(sound)  # type: ignore

    def stop_sound(self, name: str) -> None:
        """Stop a sound"""
        sound = self._get_sound(name)
        if sound is None:
            return
        lib.stop_sound(sound)  # type: ignore

    def is_sound_playing(self, name: str) -> bool:
        """Check if a sound is playing"""
        sound = self._get_sound(name)
        if sound is None:
            return False
        return lib.is_sound_playing(sound)  # type: ignore

    def set_sound_volume(self, name: str, volume: float) -> None:
        """Set the volume of a specific sound"""
        sound = self._get_sound(name)
        if sound is None:
            return
        lib.set_sound_volume(sound, volume)  # type: ignore

    def set_sound_pan(self, name: str, pan: float) -> None:
        """Set the pan of a specific sound"""
        sound = self._get_sound(name)
        if sound is None:
            return
        lib.set_sound_pan(sound, pan)  # type: ignore

    # Music management
    def load_music_stream(self, file_path: Path, name: str) -> str:
        """Load a music stream and return music ID"""
        music = self._load_music_with_fallback(file_path)
        if lib.is_music_valid(music): # type: ignore
            self.music_streams[name] = music
            logger.info(f"Loaded music stream from {file_path} as {name}")
            return name
        logger.error(f"Failed to load music: {file_path}")
        return ""

    def play_music_stream(self, name: str, volume_preset: str) -> None:
        """Play a music stream"""
        music = self._get_music(name)
        if music is None:
            return
        lib.seek_music_stream(music, 0)  # type: ignore
        volume = self._resolve_volume(volume_preset)
        if volume is not None:
            lib.set_music_volume(music, volume)  # type: ignore
        lib.play_music_stream(music)  # type: ignore

    def music_stream_needs_update(self, name: str) -> bool:
        """Check if a music stream needs updating (buffers need refilling)"""
        music = self._get_music(name, warn=False)
        if music is None:
            return False
        return lib.music_stream_needs_update(music)  # type: ignore

    def update_music_stream(self, name: str) -> None:
        """Update a music stream (only if buffers need refilling)"""
        music = self._get_music(name)
        if music is None:
            return
        if lib.music_stream_needs_update(music):  # type: ignore
            lib.update_music_stream(music)  # type: ignore

    def get_music_time_length(self, name: str) -> float:
        """Get the time length of a music stream"""
        music = self._get_music(name)
        if music is None:
            return 0.0
        return lib.get_music_time_length(music)  # type: ignore

    def get_music_time_played(self, name: str) -> float:
        """Get the time played of a music stream"""
        music = self._get_music(name)
        if music is None:
            return 0.0
        return lib.get_music_time_played(music)  # type: ignore

    def set_music_volume(self, name: str, volume: float) -> None:
        """Set the volume of a music stream"""
        music = self._get_music(name)
        if music is None:
            return
        lib.set_music_volume(music, volume)  # type: ignore

    def is_music_stream_playing(self, name: str) -> bool:
        """Check if a music stream is playing"""
        music = self._get_music(name)
        if music is None:
            return False
        return lib.is_music_stream_playing(music)  # type: ignore

    def stop_music_stream(self, name: str) -> None:
        """Stop a music stream"""
        music = self._get_music(name)
        if music is None:
            return
        lib.stop_music_stream(music)  # type: ignore

    def unload_music_stream(self, name: str) -> None:
        """Unload a music stream"""
        music = self._get_music(name)
        if music is None:
            return
        lib.unload_music_stream(music)  # type: ignore
        del self.music_streams[name]

    def unload_all_music(self) -> None:
        """Unload all music streams"""
        for music_id in list(self.music_streams.keys()):
            self.unload_music_stream(music_id)

    def seek_music_stream(self, name: str, position: float) -> None:
        """Seek a music stream to a specific position"""
        music = self._get_music(name)
        if music is None:
            return
        lib.seek_music_stream(music, position)  # type: ignore

# Create the global audio instance
audio = AudioEngine(get_config()["audio"]["device_type"], get_config()["audio"]["sample_rate"], get_config()["audio"]["buffer_size"], get_config()["volume"])
audio.set_master_volume(0.75)
