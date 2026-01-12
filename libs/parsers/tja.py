import hashlib
import logging
import math
import random
from dataclasses import dataclass, field, fields
from enum import IntEnum
from functools import lru_cache
from pathlib import Path
from typing import Optional

from libs.global_data import Modifiers
from libs.utils import strip_comments


@lru_cache(maxsize=64)
def get_ms_per_measure(bpm_val: float, time_sig: float):
    """Calculate the number of milliseconds per measure."""
    #https://gist.github.com/KatieFrogs/e000f406bbc70a12f3c34a07303eec8b#measure
    if bpm_val == 0:
        return 0
    return 60000 * (time_sig * 4) / bpm_val

class NoteType(IntEnum):
    NONE = 0
    DON = 1
    KAT = 2
    DON_L = 3
    KAT_L = 4
    ROLL_HEAD = 5
    ROLL_HEAD_L = 6
    BALLOON_HEAD = 7
    TAIL = 8
    KUSUDAMA = 9

class ScrollType(IntEnum):
    NMSCROLL = 0
    BMSCROLL = 1
    HBSCROLL = 2

@dataclass()
class TimelineObject:
    hit_ms: float = field(init=False)
    load_ms: float = field(init=False)

    judge_pos_x: float = field(init=False)
    judge_pos_y: float = field(init=False)
    delta_x: float = field(init=False)
    delta_y: float = field(init=False)

    bpm: float = field(init=False)
    bpmchange: float = field(init=False)
    delay: float = field(init=False)
    gogo_time: bool = field(init=False)
    branch_params: str = field(init=False)
    is_branch_start: bool = False
    is_section_marker: bool = False
    lyric: str = ''

    def __lt__(self, other):
        """Allow sorting by load_ms"""
        return self.load_ms < other.load_ms


@dataclass()
class Note:
    """A note in a TJA file.

    Attributes:
        type (int): The type (color) of the note.
        hit_ms (float): The time at which the note should be hit.
        bpm (float): The beats per minute of the note.
        scroll_x (float): The horizontal scroll speed of the note.
        scroll_y (float): The vertical scroll speed of the note.
        display (bool): Whether the note should be displayed.
        index (int): The index of the note.
        moji (int): The text drawn below the note.
    """
    type: int = field(init=False)
    hit_ms: float = field(init=False)
    load_ms: float = field(init=False)
    unload_ms: float = field(init=False)
    bpm: float = field(init=False)
    scroll_x: float = field(init=False)
    scroll_y: float = field(init=False)
    sudden_appear_ms: float = field(init=False)
    sudden_moving_ms: float = field(init=False)
    display: bool = field(init=False)
    index: int = field(init=False)
    moji: int = field(init=False)
    branch_params: str = field(init=False)
    is_branch_start: bool = field(init=False)

    def __lt__(self, other):
        return self.hit_ms < other.hit_ms

    def __le__(self, other):
        return self.hit_ms <= other.hit_ms

    def __gt__(self, other):
        return self.hit_ms > other.hit_ms

    def __ge__(self, other):
        return self.hit_ms >= other.hit_ms

    def __eq__(self, other):
        return self.hit_ms == other.hit_ms

    def _get_hash_data(self) -> bytes:
        hash_fields = ['type', 'hit_ms', 'bpm', 'scroll_x', 'scroll_y']
        field_values = []

        for field_name in sorted(hash_fields):
            value = getattr(self, field_name, None)
            field_values.append((field_name, value))

        field_values.append(('__class__', self.__class__.__name__))
        hash_string = str(field_values)
        return hash_string.encode('utf-8')

    def get_hash(self, algorithm='sha256') -> str:
        """Generate hash of the note"""
        hash_obj = hashlib.new(algorithm)
        hash_obj.update(self._get_hash_data())
        return hash_obj.hexdigest()

    def __hash__(self) -> int:
        """Make instances hashable for use in sets/dicts"""
        return int(self.get_hash('md5')[:8], 16)  # Use first 8 chars of MD5 as int

    def __repr__(self):
        return str(self.__dict__)

@dataclass
class Drumroll(Note):
    """A drumroll note in a TJA file.

    Attributes:
        _source_note (Note): The source note.
        color (int): The color of the drumroll. (0-255 where 255 is red)
    """
    _source_note: Note
    color: int = field(init=False)

    def __repr__(self):
        return str(self.__dict__)

    def __eq__(self, other):
        return self.hit_ms == other.hit_ms

    def __post_init__(self):
        for field_name in [f.name for f in fields(Note)]:
            if hasattr(self._source_note, field_name):
                setattr(self, field_name, getattr(self._source_note, field_name))

@dataclass
class Balloon(Note):
    """A balloon note in a TJA file.

    Attributes:
        _source_note (Note): The source note.
        count (int): The number of hits it takes to pop.
        popped (bool): Whether the balloon has been popped.
        is_kusudama (bool): Whether the balloon is a kusudama.
    """
    _source_note: Note
    count: int = field(init=False)
    popped: bool = False
    is_kusudama: bool = False

    def __repr__(self):
        return str(self.__dict__)

    def __eq__(self, other):
        return self.hit_ms == other.hit_ms

    def __post_init__(self):
        for field_name in [f.name for f in fields(Note)]:
            if hasattr(self._source_note, field_name):
                setattr(self, field_name, getattr(self._source_note, field_name))

    def _get_hash_data(self) -> bytes:
        """Override to include source note and balloon-specific data"""
        hash_fields = ['type', 'hit_ms', 'load_ms', 'count']
        field_values = []

        for field_name in sorted(hash_fields):
            value = getattr(self, field_name, None)
            field_values.append((field_name, value))

        field_values.append(('__class__', self.__class__.__name__))
        hash_string = str(field_values)
        return hash_string.encode('utf-8')

@dataclass
class NoteList:
    """A collection of notes
    play_notes: A list of notes, drumrolls, and balloons that are played by the player
    draw_notes: A list of notes, drumrolls, and balloons that are drawn by the player
    bars: A list of bars"""
    play_notes: list[Note | Drumroll | Balloon] = field(default_factory=lambda: [])
    draw_notes: list[Note | Drumroll | Balloon] = field(default_factory=lambda: [])
    bars: list[Note] = field(default_factory=lambda: [])
    timeline: list[TimelineObject] = field(default_factory=lambda: [])

    def __add__(self, other: 'NoteList') -> 'NoteList':
        return NoteList(
            play_notes=self.play_notes + other.play_notes,
            draw_notes=self.draw_notes + other.draw_notes,
            bars=self.bars + other.bars,
            timeline=self.timeline + other.timeline
        )

    def __iadd__(self, other: 'NoteList') -> 'NoteList':
        self.play_notes += other.play_notes
        self.draw_notes += other.draw_notes
        self.bars += other.bars
        self.timeline += other.timeline
        return self

@dataclass
class CourseData:
    """A collection of course metadata
    level: number of stars
    balloon: list of balloon counts
    scoreinit: Unused
    scorediff: Unused
    is_branching: whether the course has branches
    """
    level: int = 0
    balloon: list[int] = field(default_factory=lambda: [])
    scoreinit: list[int] = field(default_factory=lambda: [])
    scorediff: int = 0
    is_branching: bool = False

@dataclass
class TJAMetadata:
    """Metadata for a TJA file
    title: dictionary for song titles, accessed by language code
    subtitle: dictionary for song subtitles, accessed by language code
    genre: genre of the song
    wave: path to the song's audio file
    demostart: start time of the preview
    offset: offset of the song's audio file
    bpm: beats per minute of the song
    bgmovie: path to the song's background movie file
    movieoffset: offset of the song's background movie file
    scene_preset: background for the song
    course_data: dictionary of course metadata, accessed by diff number
    """
    title: dict[str, str] = field(default_factory= lambda: {'en': ''})
    subtitle: dict[str, str] = field(default_factory= lambda: {'en': ''})
    genre: str = ''
    wave: Path = Path()
    demostart: float = 0.0
    offset: float = 0.0
    bpm: float = 120.0
    bgmovie: Path = Path()
    movieoffset: float = 0.0
    scene_preset: str = ''
    course_data: dict[int, CourseData] = field(default_factory=dict)

@dataclass
class TJAEXData:
    """Extra data for TJA files
    new_audio: Contains the word "-New Audio-" in any song title
    old_audio: Contains the word "-Old Audio-" in any song title
    limited_time: Contains the word "限定" in any song title or subtitle
    new: If the TJA file has been created or modified in the last week"""
    new_audio: bool = False
    old_audio: bool = False
    limited_time: bool = False
    new: bool = False


def calculate_base_score(notes: NoteList) -> int:
    """Calculate the base score for a song based on the number of notes, balloons, and drumrolls.

    Args:
        notes (NoteList): The list of notes in the song.

    Returns:
        int: The base score for the song.
    """
    total_notes = 0
    balloon_count = 0
    drumroll_msec = 0
    for i in range(len(notes.play_notes)):
        note = notes.play_notes[i]
        if i < len(notes.play_notes)-1:
            next_note = notes.play_notes[i+1]
        else:
            next_note = notes.play_notes[len(notes.play_notes)-1]
        if isinstance(note, Drumroll):
            drumroll_msec += (next_note.hit_ms - note.hit_ms)
        elif isinstance(note, Balloon):
            balloon_count += min(100, note.count)
        elif note.type == 8:
            continue
        else:
            total_notes += 1
    if total_notes == 0:
        return 1000000
    return math.ceil((1000000 - (balloon_count * 100) - (16.920079999994086 * drumroll_msec / 1000 * 100)) / total_notes / 10) * 10

def test_encodings(file_path: Path):
    """Test the encoding of a file by trying different encodings.

    Args:
        file_path (Path): The path to the file to test.

    Returns:
        str: The encoding that successfully decoded the file.
    """
    encodings = ['utf-8-sig', 'shift-jis', 'utf-8', 'utf-16', 'mac_roman']
    final_encoding = None

    for encoding in encodings:
        try:
            _ = file_path.read_text(encoding=encoding).splitlines()
            final_encoding = encoding
            break
        except UnicodeDecodeError:
            continue
    return final_encoding

logger = logging.getLogger(__name__)

@dataclass
class ParserState:
    time_signature: float = 4/4
    bpm: float = 120
    bpmchange_last_bpm: float = 120
    scroll_x_modifier: float = 1
    scroll_y_modifier: float = 0
    scroll_type: ScrollType = ScrollType.NMSCROLL
    barline_display: bool = True
    curr_note_list: list[Note | Drumroll | Balloon] = field(default_factory=lambda: [])
    curr_draw_list: list[Note | Drumroll | Balloon] = field(default_factory=lambda: [])
    curr_bar_list: list[Note] = field(default_factory=lambda: [])
    curr_timeline: list[TimelineObject] = field(default_factory=lambda: [])
    index: int = 0
    balloons: list[int] = field(default_factory=lambda: [])
    balloon_index: int = 0
    prev_note: Optional[Note] = None
    barline_added: bool = False
    sudden_appear: float = 0.0
    sudden_moving: float = 0.0
    judge_pos_x: float = 0.0
    judge_pos_y: float = 0.0
    delay_current: float = 0.0
    delay_last_note_ms: float = 0.0
    is_branching: bool = False
    is_section_start: bool = False
    start_branch_ms: float = 0.0
    start_branch_bpm: float = 120
    start_branch_time_sig: float = 4/4
    start_branch_x_scroll: float = 1.0
    start_branch_y_scroll: float = 0.0
    start_branch_barline: bool = False
    branch_balloon_index: int = 0
    section_bar: Optional[Note] = None

class TJAParser:
    """Parse a TJA file and extract metadata and data.

    Args:
        path (Path): The path to the TJA file.
        start_delay (int): The delay in milliseconds before the first note.
        distance (int): The distance between notes.

    Attributes:
        metadata (TJAMetadata): The metadata extracted from the TJA file.
        ex_data (TJAEXData): The extended data extracted from the TJA file.
        data (list): The data extracted from the TJA file.
    """
    DIFFS = {0: "easy", 1: "normal", 2: "hard", 3: "oni", 4: "edit", 5: "tower", 6: "dan"}
    def __init__(self, path: Path, start_delay: int = 0):
        """
        Initialize a TJA object.

        Args:
            path (Path): The path to the TJA file.
            start_delay (int): The delay in milliseconds before the first note.
        """
        self.file_path: Path = path

        encoding = test_encodings(self.file_path)
        lines = self.file_path.read_text(encoding=encoding).splitlines()
        self.data = [cleaned for line in lines
                     if (cleaned := strip_comments(line).strip())]

        self.metadata = TJAMetadata()
        self.ex_data = TJAEXData()
        logger.debug(f"Parsing TJA file: {self.file_path}")
        self.get_metadata()

        self.current_ms: float = start_delay

        self.master_notes = NoteList()
        self.branch_m: list[NoteList] = []
        self.branch_e: list[NoteList] = []
        self.branch_n: list[NoteList] = []

    def _build_command_registry(self):
        """Auto-discover command handlers based on naming convention."""
        registry = {}
        for name in dir(self):
            if name.startswith('handle_'):
                cmd_name = '#' + name[7:].upper()
                registry[cmd_name] = getattr(self, name)
        return registry

    def get_metadata(self):
        """
        Extract metadata from the TJA file.
        """
        current_diff = None  # Track which difficulty we're currently processing

        for item in self.data:
            if item.startswith('#BRANCH') and current_diff is not None:
                self.metadata.course_data[current_diff].is_branching = True
            elif item.startswith("#") or item[0].isdigit():
                continue
            elif item.startswith('SUBTITLE'):
                region_code = 'en'
                if item[len('SUBTITLE')] != ':':
                    region_code = (item[len('SUBTITLE'):len('SUBTITLE')+2]).lower()
                self.metadata.subtitle[region_code] = ''.join(item.split(':')[1:]).replace('--', '')
                if 'ja' in self.metadata.subtitle and '限定' in self.metadata.subtitle['ja']:
                    self.ex_data.limited_time = True
            elif item.startswith('TITLE'):
                region_code = 'en'
                if item[len('TITLE')] != ':':
                    region_code = (item[len('TITLE'):len('TITLE')+2]).lower()
                self.metadata.title[region_code] = ''.join(item.split(':')[1:])
            elif item.startswith('BPM'):
                data = item.split(':')[1]
                if not data:
                    logger.warning(f"Invalid BPM value: {data} in TJA file {self.file_path}")
                    self.metadata.bpm = 0.0
                else:
                    self.metadata.bpm = float(data)
            elif item.startswith('WAVE'):
                data = item.split(':')[1]
                if not Path(self.file_path.parent / data.strip()).exists():
                    logger.error(f'{data}, {self.file_path}')
                    logger.warning(f"Invalid WAVE value: {data} in TJA file {self.file_path}")
                    self.metadata.wave = Path()
                else:
                    self.metadata.wave = self.file_path.parent / data.strip()
            elif item.startswith('OFFSET'):
                data = item.split(':')[1]
                if not data:
                    logger.warning(f"Invalid OFFSET value: {data} in TJA file {self.file_path}")
                    self.metadata.offset = 0.0
                else:
                    self.metadata.offset = float(data)
            elif item.startswith('DEMOSTART'):
                data = item.split(':')[1]
                if not data:
                    logger.warning(f"Invalid DEMOSTART value: {data} in TJA file {self.file_path}")
                    self.metadata.demostart = 0.0
                else:
                    self.metadata.demostart = float(data)
            elif item.startswith('BGMOVIE'):
                data = item.split(':')[1]
                if not data:
                    logger.warning(f"Invalid BGMOVIE value: {data} in TJA file {self.file_path}")
                    self.metadata.bgmovie = Path()
                else:
                    self.metadata.bgmovie = self.file_path.parent / data.strip()
            elif item.startswith('MOVIEOFFSET'):
                data = item.split(':')[1]
                if not data:
                    logger.warning(f"Invalid MOVIEOFFSET value: {data} in TJA file {self.file_path}")
                    self.metadata.movieoffset = 0.0
                else:
                    self.metadata.movieoffset = float(data)
            elif item.startswith('SCENEPRESET'):
                self.metadata.scene_preset = item.split(':')[1]
            elif item.startswith('COURSE'):
                course = str(item.split(':')[1]).lower().strip()

                if course == '6' or course == 'dan':
                    current_diff = 6
                elif course == '5' or course == 'tower':
                    current_diff = 5
                elif course == '4' or course == 'edit' or course == 'ura':
                    current_diff = 4
                elif course == '3' or course == 'oni':
                    current_diff = 3
                elif course == '2' or course == 'hard':
                    current_diff = 2
                elif course == '1' or course == 'normal':
                    current_diff = 1
                elif course == '0' or course == 'easy':
                    current_diff = 0
                else:
                    logger.error(f"Course level empty in {self.file_path}")
                if current_diff is not None:
                    self.metadata.course_data[current_diff] = CourseData()
            elif current_diff is not None:
                if item.startswith('LEVEL'):
                    data = item.split(':')[1]
                    if not data:
                        self.metadata.course_data[current_diff].level = 0
                        logger.warning(f"Invalid LEVEL value: {data} in TJA file {self.file_path}")
                    else:
                        self.metadata.course_data[current_diff].level = int(float(data))
                elif item.startswith('BALLOONNOR'):
                    balloon_data = item.split(':')[1]
                    if balloon_data == '':
                        logger.debug(f"Invalid BALLOONNOR value: {balloon_data} in TJA file {self.file_path}")
                        continue
                    self.metadata.course_data[current_diff].balloon.extend([int(x) for x in balloon_data.replace('.', ',').split(',') if x != ''])
                elif item.startswith('BALLOONEXP'):
                    balloon_data = item.split(':')[1]
                    if balloon_data == '':
                        logger.debug(f"Invalid BALLOONEXP value: {balloon_data} in TJA file {self.file_path}")
                        continue
                    self.metadata.course_data[current_diff].balloon.extend([int(x) for x in balloon_data.replace('.', ',').split(',') if x != ''])
                elif item.startswith('BALLOONMAS'):
                    balloon_data = item.split(':')[1]
                    if balloon_data == '':
                        logger.debug(f"Invalid BALLOONMAS value: {balloon_data} in TJA file {self.file_path}")
                        continue
                    self.metadata.course_data[current_diff].balloon = [int(x) for x in balloon_data.replace('.', ',').split(',') if x != '']
                elif item.startswith('BALLOON'):
                    if item.find(':') == -1:
                        self.metadata.course_data[current_diff].balloon = []
                        continue
                    balloon_data = item.split(':')[1]
                    if balloon_data == '':
                        continue
                    self.metadata.course_data[current_diff].balloon = [int(x) for x in balloon_data.replace('.', ',').split(',') if x != '']
                elif item.startswith('SCOREINIT'):
                    score_init = item.split(':')[1]
                    if score_init == '':
                        continue
                    try:
                        self.metadata.course_data[current_diff].scoreinit = [int(x) for x in score_init.replace('.', ',').split(',') if x != '']
                    except Exception as e:
                        logger.error(f"Failed to parse SCOREINIT: {e} in TJA file {self.file_path}")
                        self.metadata.course_data[current_diff].scoreinit = [0, 0]
                elif item.startswith('SCOREDIFF'):
                    score_diff = item.split(':')[1]
                    if score_diff == '':
                        continue
                    self.metadata.course_data[current_diff].scorediff = int(float(score_diff))
        for region_code in self.metadata.title:
            if '-New Audio-' in self.metadata.title[region_code] or '-新曲-' in self.metadata.title[region_code]:
                self.metadata.title[region_code] = self.metadata.title[region_code].replace('-New Audio-', '')
                self.metadata.title[region_code] = self.metadata.title[region_code].replace('-新曲-', '')
                self.ex_data.new_audio = True
            elif '-Old Audio-' in self.metadata.title[region_code] or '-旧曲-' in self.metadata.title[region_code]:
                self.metadata.title[region_code] = self.metadata.title[region_code].replace('-Old Audio-', '')
                self.metadata.title[region_code] = self.metadata.title[region_code].replace('-旧曲-', '')
                self.ex_data.old_audio = True
            elif '限定' in self.metadata.title[region_code]:
                self.ex_data.limited_time = True

    def data_to_notes(self, diff) -> list[list[str]]:
        """
        Convert the data to notes.

        Args:
            diff (int): The difficulty level.

        Returns:
            list[list[str]]: The notes.
        """
        diff_name = self.DIFFS.get(diff, "").lower()

        # Use enumerate for single iteration
        note_start = note_end = -1
        target_found = False
        scroll_type = ScrollType.NMSCROLL

        # Find the section boundaries
        for i, line in enumerate(self.data):
            if line.startswith("COURSE:"):
                course_value = line[7:].strip().lower()
                target_found = (course_value.isdigit() and int(course_value) == diff) or course_value == diff_name
            elif target_found:
                if note_start == -1 and line in ("#START", "#START P1"):
                    note_start = i + 1
                elif line == "#END" and note_start != -1:
                    note_end = i
                    break
                elif '#NMSCROLL' in line:
                    scroll_type = ScrollType.NMSCROLL
                    continue
                elif '#BMSCROLL' in line:
                    scroll_type = ScrollType.BMSCROLL
                    continue
                elif '#HBSCROLL' in line:
                    scroll_type = ScrollType.HBSCROLL
                    continue

        if note_start == -1 or note_end == -1:
            return []

        # Process the section with minimal string operations
        notes = []
        bar = []
        section_data = self.data[note_start:note_end]

        # Prepend scroll type
        if scroll_type == ScrollType.NMSCROLL:
            bar.append('#NMSCROLL')
        elif scroll_type == ScrollType.BMSCROLL:
            bar.append('#BMSCROLL')
        elif scroll_type == ScrollType.HBSCROLL:
            bar.append('#HBSCROLL')

        for line in section_data:
            if line.startswith("#"):
                bar.append(line)
            elif line == ',':
                if not bar or all(item.startswith('#') for item in bar):
                    bar.append('')
                notes.append(bar)
                bar = []
            else:
                if line.endswith(','):
                    bar.append(line[:-1])
                    notes.append(bar)
                    bar = []
                else:
                    bar.append(line)

        if bar:  # Add remaining items
            notes.append(bar)

        return notes

    def get_moji(self, play_note_list: list[Note], ms_per_measure: float) -> None:
        """
        Assign 口唱歌 (note phoneticization) to notes.
        Args:
            play_note_list (list[Note]): The list of notes to process.
            ms_per_measure (float): The duration of a measure in milliseconds.
        Returns:
            None
        """
        se_notes = {
            1: 0,
            2: 3,
            3: 5,
            4: 6,
            5: 7,
            6: 8,
            7: 9,
            8: 10,
            9: 11
        }
        if len(play_note_list) <= 1:
            return
        current_note = play_note_list[-1]
        if current_note.type == 1:
            current_note.moji = 0
        elif current_note.type == 2:
            current_note.moji = 3
        else:
            current_note.moji = se_notes[current_note.type]
        prev_note = play_note_list[-2]
        if prev_note.type == 1:
            timing_threshold = ms_per_measure / 8 - 1
            if current_note.hit_ms - prev_note.hit_ms <= timing_threshold:
                prev_note.moji = 1
            else:
                prev_note.moji = 0
        elif prev_note.type == 2:
            timing_threshold = ms_per_measure / 8 - 1
            if current_note.hit_ms - prev_note.hit_ms <= timing_threshold:
                prev_note.moji = 4
            else:
                prev_note.moji = 3
        else:
            prev_note.moji = se_notes[prev_note.type]
        if len(play_note_list) > 3:
            notes_minus_4 = play_note_list[-4]
            notes_minus_3 = play_note_list[-3]
            notes_minus_2 = play_note_list[-2]
            consecutive_ones = (
                notes_minus_4.type == 1 and
                notes_minus_3.type == 1 and
                notes_minus_2.type == 1
            )
            if consecutive_ones:
                rapid_timing = (
                    notes_minus_3.hit_ms - notes_minus_4.hit_ms < (ms_per_measure / 8) and
                    notes_minus_2.hit_ms - notes_minus_3.hit_ms < (ms_per_measure / 8)
                )
                if rapid_timing:
                    if len(play_note_list) > 5:
                        spacing_before = play_note_list[-4].hit_ms - play_note_list[-5].hit_ms >= (ms_per_measure / 8)
                        spacing_after = play_note_list[-1].hit_ms - play_note_list[-2].hit_ms >= (ms_per_measure / 8)
                        if spacing_before and spacing_after:
                            play_note_list[-3].moji = 2
                    else:
                        play_note_list[-3].moji = 2

    def apply_easing(self, t, easing_point, easing_function):
        """Apply easing function to normalized time value t (0 to 1)"""
        if easing_point == 'IN':
            pass  # t stays as is
        elif easing_point == 'OUT':
            t = 1 - t
        elif easing_point == 'IN_OUT':
            if t < 0.5:
                t = t * 2
            else:
                t = (1 - t) * 2

        if easing_function == 'LINEAR':
            result = t
        elif easing_function == 'CUBIC':
            result = t ** 3
        elif easing_function == 'QUARTIC':
            result = t ** 4
        elif easing_function == 'QUINTIC':
            result = t ** 5
        elif easing_function == 'SINUSOIDAL':
            import math
            result = 1 - math.cos((t * math.pi) / 2)
        elif easing_function == 'EXPONENTIAL':
            result = 0 if t == 0 else 2 ** (10 * (t - 1))
        elif easing_function == 'CIRCULAR':
            import math
            result = 1 - math.sqrt(1 - t ** 2)
        else:
            result = t

        if easing_point == 'OUT':
            result = 1 - result
        elif easing_point == 'IN_OUT':
            if t >= 0.5:
                result = 1 - result

        return result

    def handle_measure(self, part: str, state: ParserState):
        numerator, denominator = part.split('/')
        state.time_signature = float(numerator) / float(denominator)

    def handle_scroll(self, part: str, state: ParserState):
        if state.scroll_type != ScrollType.BMSCROLL:
            if 'i' in part:
                normalized = part.replace('.i', 'j').replace('i', 'j')
                normalized = normalized.replace(',', '')
                c = complex(normalized)
                state.scroll_x_modifier = c.real
                state.scroll_y_modifier = c.imag
            else:
                state.scroll_x_modifier = float(part)
                state.scroll_y_modifier = 0.0

    def handle_bpmchange(self, part: str, state: ParserState):
        parsed_bpm = float(part)
        if state.scroll_type == ScrollType.BMSCROLL or state.scroll_type == ScrollType.HBSCROLL:
            # Do not modify bpm, it needs to be changed live by bpmchange
            bpmchange = parsed_bpm / state.bpmchange_last_bpm
            state.bpmchange_last_bpm = parsed_bpm

            bpmchange_timeline = TimelineObject()
            bpmchange_timeline.hit_ms = self.current_ms
            bpmchange_timeline.bpmchange = bpmchange
            state.curr_timeline.append(bpmchange_timeline)
        else:
            timeline_obj = TimelineObject()
            timeline_obj.hit_ms = self.current_ms
            timeline_obj.bpm = parsed_bpm
            state.bpm = parsed_bpm
            state.curr_timeline.append(timeline_obj)

    def handle_section(self, part: str, state: ParserState):
        state.is_section_start = True

    def handle_branchstart(self, part: str, state: ParserState):
        state.start_branch_ms = self.current_ms
        state.start_branch_bpm = state.bpm
        state.start_branch_time_sig = state.time_signature
        state.start_branch_x_scroll = state.scroll_x_modifier
        state.start_branch_y_scroll = state.scroll_y_modifier
        state.start_branch_barline = state.barline_display
        state.branch_balloon_index = state.balloon_index
        branch_params = part

        def set_branch_params(bar_list: list[Note], branch_params: str, section_bar: Optional[Note]):
            if bar_list and len(bar_list) > 1:
                section_index = -2
                if section_bar and section_bar.hit_ms < self.current_ms:
                    if section_bar in bar_list:
                        section_index = bar_list.index(section_bar)
                bar_list[section_index].branch_params = branch_params
            elif bar_list:
                section_index = -1
                bar_list[section_index].branch_params = branch_params
            elif bar_list == []:
                bar_line = Note()

                bar_line.hit_ms = self.current_ms
                bar_line.type = 0
                bar_line.display = False
                bar_line.branch_params = branch_params
                bar_list.append(bar_line)

        for bars in [state.curr_bar_list,
                        self.branch_m[-1].bars if self.branch_m else None,
                        self.branch_e[-1].bars if self.branch_e else None,
                        self.branch_n[-1].bars if self.branch_n else None]:
            set_branch_params(bars, branch_params, state.section_bar)
        if state.section_bar:
            state.section_bar = None

    def handle_branchend(self, part: str, state: ParserState):
        state.curr_note_list = self.master_notes.play_notes
        state.curr_draw_list = self.master_notes.draw_notes
        state.curr_bar_list = self.master_notes.bars
        state.curr_timeline = self.master_notes.timeline

    def handle_lyric(self, part: str, state: ParserState):
        timeline_obj = TimelineObject()
        timeline_obj.hit_ms = self.current_ms
        timeline_obj.lyric = part
        state.curr_timeline.append(timeline_obj)

    def handle_jposscroll(self, part: str, state: ParserState):
        parts = part.split()
        duration_ms = float(parts[0]) * 1000
        distance_str = parts[1]
        direction = int(parts[2])
        delta_x = 0
        delta_y = 0
        if 'i' in distance_str:
            normalized = distance_str.replace('.i', 'j').replace('i', 'j')
            normalized = normalized.replace(',', '')
            c = complex(normalized)
            delta_x = c.real
            delta_y = c.imag
        else:
            distance = float(distance_str)
            delta_x = distance
            delta_y = 0
        if direction == 0:
            delta_x = -delta_x
            delta_y = -delta_y

        for obj in reversed(state.curr_timeline):
            if hasattr(obj, 'delta_x') and hasattr(obj, 'delta_y'):
                if obj.hit_ms > self.current_ms:
                    available_time = self.current_ms - obj.load_ms
                    total_duration = obj.hit_ms - obj.load_ms
                    ratio = min(1.0, available_time / total_duration) if total_duration > 0 else 1.0
                    obj.delta_x *= ratio
                    obj.delta_y *= ratio
                    obj.hit_ms = self.current_ms
                    break

        jpos_scroll = TimelineObject()
        jpos_scroll.load_ms = self.current_ms
        jpos_scroll.hit_ms = self.current_ms + duration_ms
        jpos_scroll.judge_pos_x = state.judge_pos_x
        jpos_scroll.judge_pos_y = state.judge_pos_y
        jpos_scroll.delta_x = delta_x
        jpos_scroll.delta_y = delta_y
        state.curr_timeline.append(jpos_scroll)

        state.judge_pos_x += delta_x
        state.judge_pos_y += delta_y

    def handle_nmscroll(self, part: str, state: ParserState):
        state.scroll_type = ScrollType.NMSCROLL

    def handle_bmscroll(self, part: str, state: ParserState):
        state.scroll_type = ScrollType.BMSCROLL

    def handle_hbscroll(self, part: str, state: ParserState):
        state.scroll_type = ScrollType.HBSCROLL

    def handle_barlineon(self, part: str, state: ParserState):
        state.barline_display = True

    def handle_barlineoff(self, part: str, state: ParserState):
        state.barline_display = False

    def handle_gogostart(self, part: str, state: ParserState):
        timeline_obj = TimelineObject()
        timeline_obj.hit_ms = self.current_ms
        timeline_obj.gogo_time = True
        state.curr_timeline.append(timeline_obj)

    def handle_gogoend(self, part: str, state: ParserState):
        timeline_obj = TimelineObject()
        timeline_obj.hit_ms = self.current_ms
        timeline_obj.gogo_time = False
        state.curr_timeline.append(timeline_obj)

    def handle_delay(self, part: str, state: ParserState):
        delay_ms = float(part) * 1000
        if state.scroll_type == ScrollType.BMSCROLL or state.scroll_type == ScrollType.HBSCROLL:
            if delay_ms > 0:
                # Do not modify current_ms, it will be modified live
                state.delay_current += delay_ms

                # Delays will be combined between notes, and attached to previous note
        else:
            self.current_ms += delay_ms

    def handle_sudden(self, part: str, state: ParserState):
        parts = part.split()
        if len(parts) >= 2:
            appear_duration = float(parts[0])
            moving_duration = float(parts[1])

            state.sudden_appear = appear_duration * 1000
            state.sudden_moving = moving_duration * 1000

            if state.sudden_appear == 0:
                state.sudden_appear = float('inf')
            if state.sudden_moving == 0:
                state.sudden_moving = float('inf')

    def handle_m(self, part: str, state: ParserState):
        self.branch_m.append(NoteList())
        state.curr_note_list = self.branch_m[-1].play_notes
        state.curr_draw_list = self.branch_m[-1].draw_notes
        state.curr_bar_list = self.branch_m[-1].bars
        state.curr_timeline = self.branch_m[-1].timeline
        self.current_ms = state.start_branch_ms
        state.bpm = state.start_branch_bpm
        state.time_signature = state.start_branch_time_sig
        state.scroll_x_modifier = state.start_branch_x_scroll
        state.scroll_y_modifier = state.start_branch_y_scroll
        state.barline_display = state.start_branch_barline
        state.balloon_index = state.branch_balloon_index
        state.is_branching = True

    def handle_e(self, part: str, state: ParserState):
        self.branch_e.append(NoteList())
        state.curr_note_list = self.branch_e[-1].play_notes
        state.curr_draw_list = self.branch_e[-1].draw_notes
        state.curr_bar_list = self.branch_e[-1].bars
        state.curr_timeline = self.branch_e[-1].timeline
        self.current_ms = state.start_branch_ms
        state.bpm = state.start_branch_bpm
        state.time_signature = state.start_branch_time_sig
        state.scroll_x_modifier = state.start_branch_x_scroll
        state.scroll_y_modifier = state.start_branch_y_scroll
        state.barline_display = state.start_branch_barline
        state.balloon_index = state.branch_balloon_index
        state.is_branching = True

    def handle_n(self, part: str, state: ParserState):
        self.branch_n.append(NoteList())
        state.curr_note_list = self.branch_n[-1].play_notes
        state.curr_draw_list = self.branch_n[-1].draw_notes
        state.curr_bar_list = self.branch_n[-1].bars
        state.curr_timeline = self.branch_n[-1].timeline
        self.current_ms = state.start_branch_ms
        state.bpm = state.start_branch_bpm
        state.time_signature = state.start_branch_time_sig
        state.scroll_x_modifier = state.start_branch_x_scroll
        state.scroll_y_modifier = state.start_branch_y_scroll
        state.barline_display = state.start_branch_barline
        state.balloon_index = state.branch_balloon_index
        state.is_branching = True

    def add_bar(self, state: ParserState):
        bar_line = Note()

        bar_line.hit_ms = self.current_ms
        bar_line.type = 0
        bar_line.display = state.barline_display
        bar_line.bpm = state.bpm
        bar_line.scroll_x = state.scroll_x_modifier
        bar_line.scroll_y = state.scroll_y_modifier

        if state.barline_added:
            bar_line.display = False

        if state.is_branching:
            bar_line.is_branch_start = True
            state.is_branching = False

        if state.is_section_start:
            state.section_bar = bar_line
            state.is_section_start = False

        return bar_line

    def add_note(self, item: str, state: ParserState):
        note = Note()
        note.hit_ms = self.current_ms
        state.delay_last_note_ms = self.current_ms
        note.display = True
        note.type = int(item)
        note.index = state.index
        note.bpm = state.bpm
        note.scroll_x = state.scroll_x_modifier
        note.scroll_y = state.scroll_y_modifier

        if state.sudden_appear > 0 or state.sudden_moving > 0:
            note.sudden_appear_ms = state.sudden_appear
            note.sudden_moving_ms = state.sudden_moving

        if item in ('5', '6'):
            note = Drumroll(note)
            note.color = 255
        elif item in ('7', '9'):
            state.balloon_index += 1
            note = Balloon(note, is_kusudama=item == '9')
            note.count = 1 if not state.balloons else state.balloons.pop(0)
        elif item == '8':
            if state.prev_note is None:
                raise ValueError("No previous note found")

        return note

    def notes_to_position(self, diff: int):
        """Parse a TJA's notes into a NoteList."""
        commands = self._build_command_registry()
        notes = self.data_to_notes(diff)

        state = ParserState()
        state.bpm = self.metadata.bpm
        state.bpmchange_last_bpm = self.metadata.bpm
        state.balloons = self.metadata.course_data[diff].balloon.copy()
        state.curr_note_list = self.master_notes.play_notes
        state.curr_draw_list = self.master_notes.draw_notes
        state.curr_bar_list = self.master_notes.bars
        state.curr_timeline = self.master_notes.timeline

        init_bpm = TimelineObject()
        init_bpm.hit_ms = self.current_ms
        init_bpm.bpm = state.bpm
        state.curr_timeline.append(init_bpm)

        state.bpmchange_last_bpm = state.bpm
        state.delay_last_note_ms = self.current_ms

        for bar in notes:
            bar_length = sum(len(part) for part in bar if '#' not in part)
            state.barline_added = False

            for part in bar:
                if part.startswith('#'):
                    for cmd_prefix, handler in sorted(commands.items(), key=lambda x: len(x[0]), reverse=True):
                        if part.startswith(cmd_prefix):
                            value = part[len(cmd_prefix):].strip()
                            handler(value, state)
                            break
                    continue
                elif len(part) > 0 and not part[0].isdigit():
                    logger.warning(f"Unrecognized command: {part} in TJA {self.file_path}")
                    continue

                ms_per_measure = get_ms_per_measure(state.bpm, state.time_signature)

                bar = self.add_bar(state)
                state.curr_bar_list.append(bar)
                state.barline_added = True

                if len(part) == 0:
                    self.current_ms += ms_per_measure
                    increment = 0
                else:
                    increment = ms_per_measure / bar_length

                for item in part:
                    if item == '0' or (not item.isdigit()):
                        state.delay_last_note_ms = self.current_ms
                        self.current_ms += increment
                        continue
                    if item == '9' and state.curr_note_list and state.curr_note_list[-1].type == 9:
                        state.delay_last_note_ms = self.current_ms
                        self.current_ms += increment
                        continue
                    if state.delay_current != 0:
                        delay_timeline = TimelineObject()
                        delay_timeline.hit_ms = state.delay_last_note_ms
                        delay_timeline.delay = state.delay_current
                        state.curr_timeline.append(delay_timeline)

                        state.delay_current = 0

                    note = self.add_note(item, state)

                    self.current_ms += increment
                    state.curr_note_list.append(note)
                    state.curr_draw_list.append(note)
                    self.get_moji(state.curr_note_list, ms_per_measure)
                    state.index += 1
                    state.prev_note = note

        return self.master_notes, self.branch_m, self.branch_e, self.branch_n

    def hash_note_data(self, notes: NoteList):
        """Hashes the note data for the given NoteList."""
        n = hashlib.sha256()
        list1 = notes.play_notes
        list2 = notes.bars
        merged: list[Note | Drumroll | Balloon] = []
        i = 0
        j = 0
        while i < len(list1) and j < len(list2):
            if list1[i] <= list2[j]:
                merged.append(list1[i])
                i += 1
            else:
                merged.append(list2[j])
                j += 1
        merged.extend(list1[i:])
        merged.extend(list2[j:])
        for item in merged:
            n.update(item.get_hash().encode('utf-8'))

        return n.hexdigest()

def modifier_speed(notes: NoteList, value: float):
    """Modifies the speed of the notes in the given NoteList."""
    modded_notes = notes.draw_notes.copy()
    modded_bars = notes.bars.copy()
    for note in modded_notes:
        note.scroll_x *= value
    for bar in modded_bars:
        bar.scroll_x *= value
    return modded_notes, modded_bars

def modifier_display(notes: NoteList):
    """Modifies the display of the notes in the given NoteList."""
    modded_notes = notes.draw_notes.copy()
    for note in modded_notes:
        note.display = False
    return modded_notes

def modifier_inverse(notes: NoteList):
    """Inverts the type of the notes in the given NoteList."""
    modded_notes = notes.play_notes.copy()
    type_mapping = {1: 2, 2: 1, 3: 4, 4: 3}
    for note in modded_notes:
        if note.type in type_mapping:
            note.type = type_mapping[note.type]
    return modded_notes

def modifier_random(notes: NoteList, value: int):
    """Randomly modifies the type of the notes in the given NoteList.
    value: 1 == kimagure, 2 == detarame"""
    modded_notes = notes.play_notes.copy()
    percentage = int(len(modded_notes) / 5) * value
    selected_notes = random.sample(range(len(modded_notes)), percentage)
    type_mapping = {1: 2, 2: 1, 3: 4, 4: 3}
    for i in selected_notes:
        if modded_notes[i].type in type_mapping:
            modded_notes[i].type = type_mapping[modded_notes[i].type]
    return modded_notes

def apply_modifiers(notes: NoteList, modifiers: Modifiers):
    """Applies all selected modifiers from global_data to the given NoteList."""
    if modifiers.display:
        draw_notes = modifier_display(notes)
    if modifiers.inverse:
        play_notes = modifier_inverse(notes)
    play_notes = modifier_random(notes, modifiers.random)
    draw_notes, bars = modifier_speed(notes, modifiers.speed)
    play_notes = modifier_difficulty(notes, modifiers.subdiff)
    draw_notes = modifier_difficulty(notes, modifiers.subdiff)
    return play_notes, draw_notes, bars

class Interval(IntEnum):
    UNKNOWN = 0
    QUARTER = 1
    EIGHTH = 2
    TWELFTH = 3
    SIXTEENTH = 4
    TWENTYFOURTH = 6
    THIRTYSECOND = 8

def modifier_difficulty(notes: NoteList, level: int):
    """Modifies notes based on difficulty level according to the difficulty table.

    Args:
        notes: The NoteList to modify
        level: The numerical difficulty level (1-13)

    Returns:
        Modified list of notes
    """
    # Levels with no changes: Easy (1), Normal (2-5), Hard (9), Oni (13)
    if level in [0, 1, 2, 3, 4, 5, 9, 13]:
        return notes.play_notes

    modded_notes = notes.play_notes.copy()

    # Helper function to calculate note interval category
    def get_note_interval_type(interval_ms: float, bpm: float, time_sig: float = 4.0) -> Interval:
        """Classify note interval as 1/8, 1/16, 1/12, or 1/24 note."""
        if bpm == 0:
            return Interval.UNKNOWN

        ms_per_measure = get_ms_per_measure(bpm, time_sig) / time_sig
        tolerance = 15  # ms tolerance for timing classification

        eighth_note = ms_per_measure / 8
        sixteenth_note = ms_per_measure / 16
        twelfth_note = ms_per_measure / 12
        twentyfourth_note = ms_per_measure / 24
        thirtysecond_note = ms_per_measure / 32
        quarter_note = ms_per_measure / 4

        if abs(interval_ms - eighth_note) < tolerance:
            return Interval.EIGHTH
        elif abs(interval_ms - sixteenth_note) < tolerance:
            return Interval.SIXTEENTH
        elif abs(interval_ms - twelfth_note) < tolerance:
            return Interval.TWELFTH
        elif abs(interval_ms - twentyfourth_note) < tolerance:
            return Interval.TWENTYFOURTH
        elif abs(interval_ms - thirtysecond_note) < tolerance:
            return Interval.THIRTYSECOND
        elif abs(interval_ms - quarter_note) < tolerance:
            return Interval.QUARTER
        return Interval.UNKNOWN

    # Helper function to make notes single-color
    def make_single_color(note_indices: list[int]):
        """Convert notes to single color (auto-detects majority color if not specified)."""
        don_count = 0
        kat_count = 0

        for idx in note_indices:
            if idx < len(modded_notes):
                note_type = modded_notes[idx].type
                if note_type in [NoteType.DON, NoteType.DON_L]:
                    don_count += 1
                elif note_type in [NoteType.KAT, NoteType.KAT_L]:
                    kat_count += 1

        # Use majority color, defaulting to DON if tied or no valid notes
        color = NoteType.DON if don_count >= kat_count else NoteType.KAT

        # Convert all notes to the determined color
        for idx in note_indices:
            if idx < len(modded_notes):
                if modded_notes[idx].type in [NoteType.DON, NoteType.KAT]:
                    modded_notes[idx].type = color
                elif modded_notes[idx].type in [NoteType.DON_L, NoteType.KAT_L]:
                    modded_notes[idx].type = NoteType.DON_L if color == NoteType.DON else NoteType.KAT_L

    # Helper function to find note streams
    def find_streams(interval_type: Interval) -> list[tuple[int, int]]:
        """Find consecutive notes with the given interval type.
        Returns list of (start_index, length) tuples."""
        streams = []
        i = 0
        while i < len(modded_notes) - 1:
            if isinstance(modded_notes[i], (Drumroll, Balloon)):
                i += 1
                continue

            stream_start = i
            stream_length = 1

            while i < len(modded_notes) - 1:
                if isinstance(modded_notes[i + 1], (Drumroll, Balloon)):
                    break

                interval = modded_notes[i + 1].hit_ms - modded_notes[i].hit_ms
                note_type = get_note_interval_type(interval, modded_notes[i].bpm)

                if note_type == interval_type:
                    stream_length += 1
                    i += 1
                else:
                    break

            if stream_length >= 2:  # At least 2 notes to form a stream
                streams.append((stream_start, stream_length))

            i += 1

        return streams

    def find_2plus2_patterns(interval_type: Interval) -> list[int]:
        """Find 2+2 patterns with the given interval type.
        A 2+2 pattern consists of:
        - 2 notes with the specified interval between them
        - A gap (size of the interval)
        - 2 more notes with the specified interval between them
        - A gap after (at least the size of the interval)

        Returns list of starting indices for 2+2 patterns."""
        patterns = []
        i = 0

        while i < len(modded_notes) - 3:
            if isinstance(modded_notes[i], (Drumroll, Balloon)):
                i += 1
                continue

            # Check if we have at least 4 notes ahead
            valid_notes_ahead = 0
            for j in range(i, min(i + 4, len(modded_notes))):
                if not isinstance(modded_notes[j], (Drumroll, Balloon)):
                    valid_notes_ahead += 1

            if valid_notes_ahead < 4:
                i += 1
                continue

            # Get the next 3 valid note indices (total 4 notes including current)
            note_indices = [i]
            j = i + 1
            while len(note_indices) < 4 and j < len(modded_notes):
                if not isinstance(modded_notes[j], (Drumroll, Balloon)):
                    note_indices.append(j)
                j += 1

            if len(note_indices) < 4:
                i += 1
                continue

            # Check intervals between the 4 notes
            interval1 = modded_notes[note_indices[1]].hit_ms - modded_notes[note_indices[0]].hit_ms
            interval2 = modded_notes[note_indices[2]].hit_ms - modded_notes[note_indices[1]].hit_ms
            interval3 = modded_notes[note_indices[3]].hit_ms - modded_notes[note_indices[2]].hit_ms

            type1 = get_note_interval_type(interval1, modded_notes[note_indices[0]].bpm)
            type3 = get_note_interval_type(interval3, modded_notes[note_indices[2]].bpm)

            # Check for 2+2 pattern:
            # - First interval matches our target type (between notes 0 and 1)
            # - Second interval is ~2x the target type (the gap, between notes 1 and 2)
            # - Third interval matches our target type (between notes 2 and 3)
            # - After the last note, there should be a gap (check next note)
            if type1 == interval_type and type3 == interval_type:
                # Check if middle interval is approximately 2x the note interval (represents the gap)
                ms_per_measure = get_ms_per_measure(modded_notes[note_indices[0]].bpm, 4.0) / 4.0
                target_interval = 0
                if interval_type == Interval.SIXTEENTH:
                    target_interval = ms_per_measure / 16
                elif interval_type == Interval.EIGHTH:
                    target_interval = ms_per_measure / 8
                elif interval_type == Interval.TWELFTH:
                    target_interval = ms_per_measure / 12
                elif interval_type == Interval.TWENTYFOURTH:
                    target_interval = ms_per_measure / 24

                # The gap should be approximately 2x the note interval (with tolerance)
                expected_gap = target_interval * 2
                tolerance = 20  # ms tolerance for gap detection

                if abs(interval2 - expected_gap) < tolerance:
                    # Check if there's a gap after the 4th note
                    if note_indices[3] + 1 < len(modded_notes):
                        if not isinstance(modded_notes[note_indices[3] + 1], (Drumroll, Balloon)):
                            interval_after = modded_notes[note_indices[3] + 1].hit_ms - modded_notes[note_indices[3]].hit_ms
                            type_after = get_note_interval_type(interval_after, modded_notes[note_indices[3]].bpm)
                            # Gap after should be at least the size of the interval
                            if interval_after >= target_interval * 1.5 or type_after != interval_type:
                                patterns.append(i)
                    else:
                        # End of notes, so pattern is valid
                        patterns.append(i)

            i += 1

        return patterns

    # Level 6 (Hard): 1/8 note streams become single-color; 1/8 note triplets become 1/4 notes
    if level == 6:
        streams = find_streams(Interval.EIGHTH)
        for start, length in streams:
            if length == 3:
                modded_notes[start + 1].type = NoteType.NONE
            elif length > 3:
                make_single_color(list(range(start, start + length)))

    # Level 7 (Hard): 1/8 note 5-hit streams become 3-1 pattern; 7+ hits repeat 3-1-1 pattern
    elif level == 7:
        streams = find_streams(Interval.EIGHTH)
        for start, length in streams:
            if length == 5:
                modded_notes[start + 3].type = NoteType.NONE
            elif length >= 7:
                idx = start
                while idx < start + length:
                    idx += 3
                    if idx < start + length and idx < len(modded_notes):
                        modded_notes[idx].type = NoteType.NONE
                        idx += 1

    # Level 8 (Hard): 1/16 note triplets become 1/8 notes; 1/16 note 5-hit streams become 3+1 or 2+2
    elif level == 8:
        streams = find_streams(Interval.SIXTEENTH)
        for start, length in streams:
            if length == 3:
                modded_notes[start + 1].type = NoteType.NONE
            elif length == 5:
                #3+1 if start with don, 2+2 if start with kat
                if modded_notes[start].type in [NoteType.DON, NoteType.DON_L]:
                    modded_notes[start + 3].type = NoteType.NONE
                else:
                    modded_notes[start + 2].type = NoteType.NONE

    # Level 10 (Oni):
    # 1/16 note 5-hit streams become 3+1
    # 1/16 note doubles become single-color
    # 2+2 hits become 2+1 hits (annoying)
    # 1/16 4+ hits become 8th doubles
    # 1/24ths are removed
    # 1/16th streams become triplet followed by interval below
    elif level == 10:
        streams = find_streams(Interval.THIRTYSECOND)
        for start, length in streams:
            idx = start + 1
            while idx < start + length:
                if idx < start + length and idx < len(modded_notes):
                    modded_notes[idx].type = NoteType.NONE
                    idx += 2

        streams = find_streams(Interval.TWENTYFOURTH)
        for start, length in streams:
            idx = start + 1
            while idx < start + length - 1:
                if idx < len(modded_notes) and idx + 1 < len(modded_notes):
                    modded_notes[idx].type = NoteType.NONE
                    modded_notes[idx + 1].type = NoteType.NONE
                idx += 3
        streams = find_streams(Interval.SIXTEENTH)
        for start, length in streams:
            if length == 2:
                modded_notes[start].type = modded_notes[start + 1].type
            if length == 3:
                modded_notes[start + 1].type = NoteType.NONE
            if length == 4 or length == 5:
                modded_notes[start + 3].type = NoteType.NONE
                make_single_color(list(range(start, start + length)))
            elif length > 5:
                modded_notes[start + 3].type = NoteType.NONE
                idx = start + 5
                while idx < start + length:
                    if idx < start + length and idx < len(modded_notes):
                        modded_notes[idx].type = NoteType.NONE
                        idx += 2

        streams_2_2 = find_2plus2_patterns(Interval.SIXTEENTH)
        for index in streams_2_2:
            modded_notes[index + 2].type = NoteType.NONE

    # Level 11 (Oni):
    # Level 10 variation
    elif level == 11:
        streams = find_streams(Interval.THIRTYSECOND)
        for start, length in streams:
            idx = start + 1
            while idx < start + length:
                if idx < start + length and idx < len(modded_notes):
                    modded_notes[idx].type = NoteType.NONE
                    idx += 2

        streams = find_streams(Interval.TWENTYFOURTH)
        for start, length in streams:
            idx = start + 1
            while idx < start + length - 1:
                if idx < len(modded_notes) and idx + 1 < len(modded_notes):
                    modded_notes[idx].type = NoteType.NONE
                    modded_notes[idx + 1].type = NoteType.NONE
                idx += 3

        streams = find_streams(Interval.TWELFTH)
        for start, length in streams:
            idx = start + 1
            while idx < start + length - 1:
                if idx < len(modded_notes) and idx + 1 < len(modded_notes):
                    modded_notes[idx].type = NoteType.NONE
                idx += 3

        streams = find_streams(Interval.SIXTEENTH)
        for start, length in streams:
            if length == 2:
                modded_notes[start].type = modded_notes[start + 1].type
            if length == 3:
                modded_notes[start + 1].type = NoteType.NONE
            if length == 4 or length == 5:
                modded_notes[start + 3].type = NoteType.NONE
                make_single_color(list(range(start, start + length)))
            elif length > 5:
                idx = start
                while idx < start + length:
                    triplet_end = min(idx + 3, start + length)
                    if triplet_end - idx >= 2:
                        make_single_color(list(range(idx, triplet_end)))
                    idx += 3
                    if idx < start + length and idx < len(modded_notes):
                        modded_notes[idx].type = NoteType.NONE
                        idx += 2
                    if idx < start + length and idx < len(modded_notes):
                        modded_notes[idx].type = NoteType.NONE
                        idx += 1
    # Level 12 (Oni):
    # Level 10 variation
    elif level == 12:
        streams = find_streams(Interval.THIRTYSECOND)
        for start, length in streams:
            idx = start + 1
            while idx < start + length:
                if idx < start + length and idx < len(modded_notes):
                    modded_notes[idx].type = NoteType.NONE
                    idx += 2

        streams = find_streams(Interval.TWENTYFOURTH)
        for start, length in streams:
            idx = start + 1
            while idx < start + length - 1:
                if idx < len(modded_notes) and idx + 1 < len(modded_notes):
                    modded_notes[idx].type = NoteType.NONE
                    modded_notes[idx + 1].type = NoteType.NONE
                idx += 3

        streams = find_streams(Interval.TWELFTH)
        for start, length in streams:
            if length <= 4:
                make_single_color(list(range(start, start + length)))
            else:
                idx = start + 1
                while idx < start + length - 1:
                    if idx < len(modded_notes) and idx + 1 < len(modded_notes):
                        modded_notes[idx].type = NoteType.NONE
                    idx += 3

        streams = find_streams(Interval.SIXTEENTH)
        for start, length in streams:
            if length == 3:
                make_single_color(list(range(start, start + length)))
            if length == 4 or length == 5:
                modded_notes[start + 3].type = NoteType.NONE
                make_single_color(list(range(start, start + length)))
            elif length > 5:
                idx = start
                while idx < start + length:
                    triplet_end = min(idx + 3, start + length)
                    if triplet_end - idx >= 2:
                        make_single_color(list(range(idx, triplet_end)))
                    idx += 3
                    if idx < start + length and idx < len(modded_notes):
                        modded_notes[idx].type = NoteType.NONE
                        idx += 2
                    if idx < start + length and idx < len(modded_notes):
                        modded_notes[idx].type = NoteType.NONE
                        idx += 1

    filtered_notes = [note for note in modded_notes if note.type != NoteType.NONE]

    return filtered_notes
