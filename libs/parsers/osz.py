import hashlib
import math
from pathlib import Path

from libs.parsers.tja import CourseData, Note, NoteType, Drumroll, Balloon, NoteList, TJAEXData, TJAMetadata, TimelineObject

import re

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
        #self.general = self.read_osu_data(osu_file, target_header="Colours", is_dict=True)
        self.hit_objects = self.read_osu_data_list(osu_file, target_header="HitObjects")
        self.slider_multiplier = float(self.difficulty["SliderMultiplier"])
        self.metadata = TJAMetadata()
        self.metadata.wave = osu_file.parent / self.general["AudioFilename"]
        self.metadata.demostart = float(self.general["PreviewTime"]) / 1000
        self.metadata.offset = -30/1000
        self.metadata.title["en"] = self.osu_metadata["Version"]
        self.metadata.subtitle["en"] = self.osu_metadata["Creator"]
        match = re.search(r'\[Events\][\s\S]*?^[ \t]*(\d+),(\d+),"([^"]+)"', osu_file.read_text(encoding='utf-8'), re.MULTILINE)
        if match:
            self.metadata.bgmovie = osu_file.parent / Path(match.group(3))
        self.metadata.course_data[0] = CourseData()
        self.ex_data = TJAEXData()
        self.bpm = []
        for points in self.timing_points:
            self.bpm.append(math.floor(1 / points[1] * 1000 * 60))
        self.osu_NoteList = self.note_data_to_NoteList(self.hit_objects)
        for points in self.timing_points:
            if 0 < points[1] < 60000:
                obj = TimelineObject()
                obj.hit_ms = points[0]
                obj.bpm = math.floor(1 / points[1] * 1000 * 60)
                self.osu_NoteList[0].timeline.append(obj)

    def read_osu_data_list(self, file_path: Path, target_header="HitObjects") -> list[list[float]]:
        data = []
        current_header = None

        with file_path.open(mode='r', encoding='utf-8') as f:

            for line in f:
                line = line.rstrip("\n")

                if re.match(r"\[\w*\]", line): # header pattern
                    current_header = line[1:-1]

                if current_header == target_header:

                    if re.match(r"[-+]?\d*\.?\d+" , line): # Events, TimingPoints, HitObjects
                        string_array = re.findall(r"[-+]?\d*\.?\d+" , line) # search for floats
                        int_array = [float(num_str) for num_str in string_array]
                        data.append(int_array)

                else:
                    continue

        return data

    def read_osu_data_dict(self, file_path: Path, target_header="HitObjects") -> dict[str, str]:
        data = dict()
        current_header = None

        with file_path.open(mode='r', encoding='utf-8') as f:

            for line in f:
                line = line.rstrip("\n")

                if re.match(r"\[\w*\]", line): # header pattern
                    current_header = line[1:-1]

                if current_header == target_header:
                    if ':' in line and not line.startswith('['):
                        key, value = line.split(':', 1)
                        data[key.strip()] = value.strip()

                else:
                    continue

        return data

    def get_scroll_multiplier(self, ms: float) -> float:
        base_scroll = (1.0 if 1.37 <= self.slider_multiplier <= 1.47
                       else self.slider_multiplier / 1.40)
        current_scroll = 1.0

        for tp in self.timing_points:
            time = tp[0]
            beat_length = tp[1]  # positive for BPM, negative for scroll

            if time > ms:
                break

            if beat_length < 0:  # This is an inherited (green) timing point
                current_scroll = -100.0 / beat_length

        return current_scroll * base_scroll

    def note_data_to_NoteList(self, note_data) -> tuple[NoteList, list[NoteList], list[NoteList], list[NoteList]]:
        osu_NoteList = NoteList()
        counter = 0

        for line in note_data:
            note_time = line[2]
            scroll = self.get_scroll_multiplier(note_time)

            if (line[3] == 1 or line[3] == 4 or line[3] == 5 or line[3] == 6) and line[4] == 0: # DON
                don = Note()
                don.type = NoteType(1)
                don.hit_ms = line[2]
                don.bpm = self.bpm[0]
                don.scroll_x = scroll
                don.scroll_y = 0
                don.display = True
                don.index = counter
                counter = counter + 1
                don.moji = 1

                osu_NoteList.play_notes.append(don)

            if (line[3] == 1 or line[3] == 4 or line[3] == 5 or line[3] == 6) and (line[4] == 2 or line[4] == 8): # KAT
                kat = Note()
                kat.type = NoteType(2)
                kat.hit_ms = line[2]
                kat.bpm = self.bpm[0]
                kat.scroll_x = scroll
                kat.scroll_y = 0
                kat.display = True
                kat.index = counter
                counter = counter + 1
                kat.moji = 4

                osu_NoteList.play_notes.append(kat)

            if (line[3] == 1 or line[3] == 4 or line[3] == 5 or line[3] == 6) and line[4] == 4: # L-DON
                don = Note()
                don.type = NoteType(3)
                don.hit_ms = line[2]
                don.bpm = self.bpm[0]
                don.scroll_x = scroll
                don.scroll_y = 0
                don.display = True
                don.index = counter
                counter = counter + 1
                don.moji = 5

                osu_NoteList.play_notes.append(don)

            if (line[3] == 1 or line[3] == 4 or line[3] == 5 or line[3] == 6) and (line[4] == 6 or line[4] == 12): # L-KAT
                kat = Note()
                kat.type = NoteType(4)
                kat.hit_ms = line[2]
                kat.bpm = self.bpm[0]
                kat.scroll_x = scroll
                kat.scroll_y = 0
                kat.display = True
                kat.index = counter
                counter = counter + 1
                kat.moji = 6

                osu_NoteList.play_notes.append(kat)

            if (line[3] == 2) and (line[4] == 0): # Drum Roll
                if len(line) >= 9:
                    slider_time = line[8] / (float(self.difficulty["SliderMultiplier"])  * 100) * self.timing_points[0][1]
                else:
                    slider_time = line[6] / (float(self.difficulty["SliderMultiplier"])  * 100) * self.timing_points[0][1]

                source = Note()
                source.type = NoteType(8)
                source.hit_ms = line[2] + slider_time
                source.bpm = self.bpm[0]
                source.scroll_x = scroll
                source.scroll_y = 0
                source.display = True
                # this is where the index would be if it wasn't a tail note
                source.moji = 7

                slider = Drumroll(source)
                slider.color = 255
                slider.type = NoteType(5)
                slider.hit_ms = line[2]
                slider.bpm = self.bpm[0]
                slider.scroll_x = scroll
                slider.scroll_y = 0
                slider.display = True
                slider.index = counter
                slider.moji = 10
                counter = counter + 1

                source.index = counter
                counter = counter + 1

                osu_NoteList.play_notes.append(slider)
                osu_NoteList.play_notes.append(source)

            if (line[3] == 2) and (line[4] == 4): # L-Drum Roll
                if len(line) >= 9:
                    slider_time = line[8] / (float(self.difficulty["SliderMultiplier"])  * 100) * self.timing_points[0][1]
                else:
                    slider_time = line[6] / (float(self.difficulty["SliderMultiplier"])  * 100) * self.timing_points[0][1]

                source = Note()
                source.type = NoteType(8)
                source.hit_ms = line[2] + slider_time
                source.bpm = self.bpm[0]
                source.scroll_x = scroll
                source.scroll_y = 0
                source.display = True
                # this is where the index would be if it wasn't a tail note
                source.moji = 8

                slider = Drumroll(source)
                slider.color = 255
                slider.type = NoteType(6)
                slider.hit_ms = line[2]
                slider.bpm = self.bpm[0]
                slider.scroll_x = scroll
                slider.scroll_y = 0
                slider.display = True
                slider.index = counter
                counter = counter + 1

                source.index = counter
                counter = counter + 1

                osu_NoteList.play_notes.append(slider)
                osu_NoteList.play_notes.append(source)

            if (line[3] == 8): # Balloon
                source = Note()
                source.type = NoteType(8)
                source.hit_ms = line[5]
                source.bpm = self.bpm[0]
                source.scroll_x = scroll
                source.scroll_y = 0
                source.display = True
                #source.index = counter
                #counter = counter + 1
                source.moji = 9

                balloon = Balloon(source)
                balloon.type = NoteType(7)
                balloon.hit_ms = line[2]
                balloon.bpm = self.bpm[0]
                balloon.scroll_x = scroll
                balloon.scroll_y = 0
                balloon.display = True
                balloon.index = counter
                counter = counter + 1
                balloon.moji = 10

                '''
                od = int(self.difficulty["OverallDifficulty"])
                # thank you https://github.com/IepIweidieng/osu2tja/blob/dev-iid/osu2tja/osu2tja.py
                hit_multiplier = (5 - 2 * (5 - od) / 5 if od < 5
                                else 5 + 2.5 * (od - 5) / 5 if od > 5
                                else 5) * 1.65
                '''
                balloon.count = 20#int(max(1, (ret[-1][1] - ret[-2][1]) / 1000 * hit_multiplier))
                # end of 'stolen' code
                source.index = counter
                counter = counter + 1

                osu_NoteList.play_notes.append(balloon)
                osu_NoteList.play_notes.append(source)

        osu_NoteList.draw_notes = osu_NoteList.play_notes.copy()

        return osu_NoteList, [], [], []

    def notes_to_position(self, difficulty):
        return self.osu_NoteList

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
