import hashlib
import math
import re
from pathlib import Path

from libs.parsers.tja import (
    Balloon,
    CourseData,
    Drumroll,
    Note,
    NoteList,
    NoteType,
    TJAEXData,
    TJAMetadata,
    TimelineObject,
)

SECTION_HEADER_PATTERN = re.compile(r"\[\w*\]")
NUMBER_PATTERN = re.compile(r"[-+]?\d*\.?\d+")
EVENT_BG_PATTERN = re.compile(
    r'\[Events\][\s\S]*?^[ \t]*(\d+),(\d+),"([^"]+)"',
    re.MULTILINE,
)

TAP_NOTE_OBJECT_TYPES = {1, 4, 5, 6}
KAT_HITSOUNDS = {2, 8}
BIG_KAT_HITSOUNDS = {6, 12}


class OsuParser:
    general: dict[str, str]
    editor: dict[str, str]
    osu_metadata: dict[str, str]
    difficulty: dict[str, str]
    events: list[list[float]]
    timing_points: list[list[float]]
    hit_objects: list[list[float]]
    bpm: list[float]

    def __init__(self, osu_file: Path):
        self.general = self.read_osu_data_dict(osu_file, target_header="General")
        self.editor = self.read_osu_data_dict(osu_file, target_header="Editor")
        self.osu_metadata = self.read_osu_data_dict(osu_file, target_header="Metadata")
        self.difficulty = self.read_osu_data_dict(osu_file, target_header="Difficulty")
        self.events = self.read_osu_data_list(osu_file, target_header="Events")
        self.timing_points = self.read_osu_data_list(osu_file, target_header="TimingPoints")
        self.hit_objects = self.read_osu_data_list(osu_file, target_header="HitObjects")
        self.slider_multiplier = float(self.difficulty["SliderMultiplier"])

        self.metadata = TJAMetadata()
        self.metadata.wave = osu_file.parent / self.general["AudioFilename"]
        self.metadata.demostart = float(self.general["PreviewTime"]) / 1000
        self.metadata.offset = -30 / 1000
        self.metadata.title["en"] = self.osu_metadata["Version"]
        self.metadata.subtitle["en"] = self.osu_metadata["Creator"]

        match = EVENT_BG_PATTERN.search(osu_file.read_text(encoding='utf-8'))
        if match:
            self.metadata.bgmovie = osu_file.parent / Path(match.group(3))

        self.metadata.course_data[0] = CourseData()
        self.ex_data = TJAEXData()

        self.bpm = [math.floor(1 / points[1] * 1000 * 60) for points in self.timing_points]
        self.osu_NoteList = self.note_data_to_NoteList(self.hit_objects)
        self._append_timeline_bpms(self.osu_NoteList[0])

    def _iter_section_lines(self, file_path: Path, target_header: str):
        current_header = None
        with file_path.open(mode='r', encoding='utf-8') as file:
            for raw_line in file:
                line = raw_line.rstrip("\n")
                if SECTION_HEADER_PATTERN.match(line):
                    current_header = line[1:-1]
                    continue
                if current_header == target_header:
                    yield line

    def read_osu_data_list(self, file_path: Path, target_header="HitObjects") -> list[list[float]]:
        data: list[list[float]] = []
        for line in self._iter_section_lines(file_path, target_header):
            if NUMBER_PATTERN.match(line):
                float_array = [float(num_str) for num_str in NUMBER_PATTERN.findall(line)]
                data.append(float_array)
        return data

    def read_osu_data_dict(self, file_path: Path, target_header="HitObjects") -> dict[str, str]:
        data: dict[str, str] = {}
        for line in self._iter_section_lines(file_path, target_header):
            if ':' in line:
                key, value = line.split(':', 1)
                data[key.strip()] = value.strip()
        return data

    def _append_timeline_bpms(self, note_list: NoteList) -> None:
        for points in self.timing_points:
            if 0 < points[1] < 60000:
                obj = TimelineObject()
                obj.hit_ms = points[0]
                obj.bpm = math.floor(1 / points[1] * 1000 * 60)
                note_list.timeline.append(obj)

    def get_scroll_multiplier(self, current_ms: float) -> float:
        base_scroll = (
            1.0 if 1.37 <= self.slider_multiplier <= 1.47
            else self.slider_multiplier / 1.40
        )
        current_scroll = 1.0

        for timing_point in self.timing_points:
            time = timing_point[0]
            beat_length = timing_point[1]
            if time > current_ms:
                break
            if beat_length < 0:
                current_scroll = -100.0 / beat_length

        return current_scroll * base_scroll

    def _create_note(
            self,
            note_type: NoteType,
            hit_ms: float,
            bpm: float,
            scroll_x: float,
            index: int,
            moji: int,
    ) -> Note:
        note = Note()
        note.type = note_type
        note.hit_ms = hit_ms
        note.bpm = bpm
        note.scroll_x = scroll_x
        note.scroll_y = 0
        note.display = True
        note.index = index
        note.moji = moji
        return note

    def _create_tap_note(self, line: list[float], scroll: float, counter: int):
        hit_sound = int(line[4])
        note_time = line[2]
        bpm = self.bpm[0]

        if hit_sound == 0:
            return self._create_note(NoteType.DON, note_time, bpm, scroll, counter, 1), counter + 1
        if hit_sound in KAT_HITSOUNDS:
            return self._create_note(NoteType.KAT, note_time, bpm, scroll, counter, 4), counter + 1
        if hit_sound == 4:
            return self._create_note(NoteType.DON_L, note_time, bpm, scroll, counter, 5), counter + 1
        if hit_sound in BIG_KAT_HITSOUNDS:
            return self._create_note(NoteType.KAT_L, note_time, bpm, scroll, counter, 6), counter + 1
        return None, counter

    def _calculate_slider_time(self, line: list[float]) -> float:
        if len(line) >= 9:
            slider_length = line[8]
        else:
            slider_length = line[6]
        return slider_length / (float(self.difficulty["SliderMultiplier"]) * 100) * self.timing_points[0][1]

    def _create_drumroll_pair(self, line: list[float], scroll: float, counter: int, head_type: NoteType,
                              source_moji: int):
        slider_time = self._calculate_slider_time(line)
        bpm = self.bpm[0]

        source = Note()
        source.type = NoteType.TAIL
        source.hit_ms = line[2] + slider_time
        source.bpm = bpm
        source.scroll_x = scroll
        source.scroll_y = 0
        source.display = True
        source.moji = source_moji

        slider = Drumroll(source)
        slider.color = 255
        slider.type = head_type
        slider.hit_ms = line[2]
        slider.bpm = bpm
        slider.scroll_x = scroll
        slider.scroll_y = 0
        slider.display = True
        slider.index = counter
        slider.moji = 10
        counter += 1

        source.index = counter
        counter += 1
        return slider, source, counter

    def _create_balloon_pair(self, line: list[float], scroll: float, counter: int):
        bpm = self.bpm[0]

        source = Note()
        source.type = NoteType.TAIL
        source.hit_ms = line[5]
        source.bpm = bpm
        source.scroll_x = scroll
        source.scroll_y = 0
        source.display = True
        source.moji = 9

        balloon = Balloon(source)
        balloon.type = NoteType.BALLOON_HEAD
        balloon.hit_ms = line[2]
        balloon.bpm = bpm
        balloon.scroll_x = scroll
        balloon.scroll_y = 0
        balloon.display = True
        balloon.index = counter
        balloon.moji = 10
        counter += 1

        # Keep legacy behavior.
        balloon.count = 20
        source.index = counter
        counter += 1
        return balloon, source, counter

    def note_data_to_NoteList(self, note_data) -> tuple[NoteList, list[NoteList], list[NoteList], list[NoteList]]:
        osu_note_list = NoteList()
        counter = 0

        for line in note_data:
            note_time = line[2]
            scroll = self.get_scroll_multiplier(note_time)
            object_type = int(line[3])
            hit_sound = int(line[4])

            if object_type in TAP_NOTE_OBJECT_TYPES:
                note, counter = self._create_tap_note(line, scroll, counter)
                if note is not None:
                    osu_note_list.play_notes.append(note)
                continue

            if object_type == 2 and hit_sound == 0:
                slider, source, counter = self._create_drumroll_pair(
                    line, scroll, counter, NoteType.ROLL_HEAD, source_moji=7
                )
                osu_note_list.play_notes.append(slider)
                osu_note_list.play_notes.append(source)
                continue

            if object_type == 2 and hit_sound == 4:
                slider, source, counter = self._create_drumroll_pair(
                    line, scroll, counter, NoteType.ROLL_HEAD_L, source_moji=8
                )
                osu_note_list.play_notes.append(slider)
                osu_note_list.play_notes.append(source)
                continue

            if object_type == 8:
                balloon, source, counter = self._create_balloon_pair(line, scroll, counter)
                osu_note_list.play_notes.append(balloon)
                osu_note_list.play_notes.append(source)

        osu_note_list.draw_notes = osu_note_list.play_notes.copy()
        return osu_note_list, [], [], []

    def notes_to_position(self, difficulty):
        return self.osu_NoteList

    def hash_note_data(self, notes: NoteList):
        """Hashes the note data for the given NoteList."""
        hash_builder = hashlib.sha256()
        play_notes = notes.play_notes
        bar_notes = notes.bars
        merged = []
        play_index = 0
        bar_index = 0
        while play_index < len(play_notes) and bar_index < len(bar_notes):
            if play_notes[play_index] <= bar_notes[bar_index]:
                merged.append(play_notes[play_index])
                play_index += 1
            else:
                merged.append(bar_notes[bar_index])
                bar_index += 1
        merged.extend(play_notes[play_index:])
        merged.extend(bar_notes[bar_index:])
        for item in merged:
            hash_builder.update(item.get_hash().encode('utf-8'))

        return hash_builder.hexdigest()
