import hashlib
import math
from pathlib import Path

from libs.parsers.tja import CourseData, Note, NoteType, Drumroll, Balloon, NoteList, TJAMetadata

import re

class OsuParser:
    general: dict[str, str]
    editor: dict[str, str]
    osu_metadata: dict[str, str]
    difficulty: dict[str, str]
    events: list[int]
    timing_points: list[int]
    hit_objects: list[int]

    bpm: list[int]

    def __init__(self, osu_file: Path):
        self.general = self.read_osu_data(osu_file, target_header="General", is_dict=True)
        self.editor = self.read_osu_data(osu_file, target_header="Editor", is_dict=True)
        self.osu_metadata = self.read_osu_data(osu_file, target_header="Metadata", is_dict=True)
        self.difficulty = self.read_osu_data(osu_file, target_header="Difficulty", is_dict=True)
        self.events = self.read_osu_data(osu_file, target_header="Events")
        self.timing_points = self.read_osu_data(osu_file, target_header="TimingPoints")
        #self.general = self.read_osu_data(osu_file, target_header="Colours", is_dict=True)
        self.hit_objects = self.read_osu_data(osu_file, target_header="HitObjects")
        self.bpm = []
        self.metadata = TJAMetadata()
        self.metadata.wave = osu_file.parent / self.general["AudioFilename"]
        self.metadata.course_data[0] = CourseData()
        for points in self.timing_points:
            self.bpm.append(math.floor(1 / points[1] * 1000 * 60))
        self.osu_NoteList = self.note_data_to_NoteList(self.hit_objects)

    def read_osu_data(self, file_path: Path, target_header="HitObjects", is_dict = False):
        data = []
        if is_dict:
            data = {}
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

                    if re.match(r'(\w*)\:\s?(\w*.?\w*)', line): # General, Editor, Metadata, Difficulty
                        match = re.search(r'(\w*)\:\s?(\w*.?\w*)', line)
                        if match:
                            data[match.group(1)] = match.group(2)

                else:
                    continue

        return data

    def note_data_to_NoteList(self, note_data) -> tuple[NoteList, list[NoteList], list[NoteList], list[NoteList]]:
        osu_NoteList = NoteList()
        counter = 0

        for line in note_data:

            if (line[3] == 1 or line[3] == 4 or line[3] == 5 or line[3] == 6) and line[4] == 0: # DON
                don = Note()
                don.type = NoteType(1)
                don.hit_ms = line[2]
                don.bpm = self.bpm[0]
                don.scroll_x = 1
                don.scroll_y = 0
                don.display = True
                don.index = counter
                counter = counter + 1
                don.moji = 0

                osu_NoteList.play_notes.append(don)

            if (line[3] == 1 or line[3] == 4 or line[3] == 5 or line[3] == 6) and (line[4] == 2 or line[4] == 8): # KAT
                kat = Note()
                kat.type = NoteType(2)
                kat.hit_ms = line[2]
                kat.bpm = self.bpm[0]
                kat.scroll_x = 1
                kat.scroll_y = 0
                kat.display = True
                kat.index = counter
                counter = counter + 1
                kat.moji = 1

                osu_NoteList.play_notes.append(kat)

            if (line[3] == 1 or line[3] == 4 or line[3] == 5 or line[3] == 6) and line[4] == 4: # L-DON
                don = Note()
                don.type = NoteType(3)
                don.hit_ms = line[2]
                don.bpm = self.bpm[0]
                don.scroll_x = 1
                don.scroll_y = 0
                don.display = True
                don.index = counter
                counter = counter + 1
                don.moji = 0

                osu_NoteList.play_notes.append(don)

            if (line[3] == 1 or line[3] == 4 or line[3] == 5 or line[3] == 6) and (line[4] == 6 or line[4] == 12): # L-KAT
                kat = Note()
                kat.type = NoteType(4)
                kat.hit_ms = line[2]
                kat.bpm = self.bpm[0]
                kat.scroll_x = 1
                kat.scroll_y = 0
                kat.display = True
                kat.index = counter
                counter = counter + 1
                kat.moji = 1

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
                source.scroll_x = 1
                source.scroll_y = 0
                source.display = True
                # this is where the index would be if it wasn't a tail note
                source.moji = 0

                slider = Drumroll(source)
                slider.color = 255
                slider.type = NoteType(5)
                slider.hit_ms = line[2]
                slider.bpm = self.bpm[0]
                slider.scroll_x = 1
                slider.scroll_y = 0
                slider.display = True
                slider.index = counter
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
                source.scroll_x = 1
                source.scroll_y = 0
                source.display = True
                # this is where the index would be if it wasn't a tail note
                source.moji = 0

                slider = Drumroll(source)
                slider.color = 255
                slider.type = NoteType(6)
                slider.hit_ms = line[2]
                slider.bpm = self.bpm[0]
                slider.scroll_x = 1
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
                source.scroll_x = 1
                source.scroll_y = 0
                source.display = True
                #source.index = counter
                #counter = counter + 1
                source.moji = 0

                balloon = Balloon(source)
                balloon.type = NoteType(7)
                balloon.hit_ms = line[2]
                balloon.bpm = self.bpm[0]
                balloon.scroll_x = 1
                balloon.scroll_y = 0
                balloon.display = True
                balloon.index = counter
                counter = counter + 1
                balloon.moji = 0

                od = int(self.difficulty["OverallDifficulty"])
                # thank you https://github.com/IepIweidieng/osu2tja/blob/dev-iid/osu2tja/osu2tja.py
                hit_multiplyer = (5 - 2 * (5 - od) / 5 if od < 5
                                else 5 + 2.5 * (od - 5) / 5 if od > 5
                                else 5) * 1.65
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
