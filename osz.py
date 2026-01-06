import hashlib
import logging
import math
import random
from collections import deque
from dataclasses import dataclass, field, fields
from enum import IntEnum
from functools import lru_cache
from pathlib import Path
from typing import Optional

from libs.global_data import Modifiers
from libs.utils import strip_comments
from libs.tja import TimelineObject, Note, NoteType, Drumroll, Balloon, NoteList, CourseData, ParserState

import re

osu_file = Path("./PNames.osu")
contents = osu_file.open(mode='r', encoding='utf-8').read()

class OsuParser:
    general: dict[str, str]
    editor: dict[str, str]
    metadata: dict[str, str]
    difficulty: dict[str, str]
    events: list[int]
    timing_points: list[int]
    hit_objects: list[int]

    bpm: int

    def __init__(self, osu_file):
        self.general = self.read_osu_data(osu_file, target_header="General", is_dict=True)
        self.editor = self.read_osu_data(osu_file, target_header="Editor", is_dict=True)
        self.metadata = self.read_osu_data(osu_file, target_header="Metadata", is_dict=True)
        self.difficulty = self.read_osu_data(osu_file, target_header="Difficulty", is_dict=True)
        self.events = self.read_osu_data(osu_file, target_header="Events")
        self.timing_points = self.read_osu_data(osu_file, target_header="TimingPoints")
        #self.general = self.read_osu_data(osu_file, target_header="Colours", is_dict=True)
        self.hit_objects = self.read_osu_data(osu_file, target_header="HitObjects")

        self.bpm = math.floor(1 / self.timing_points[0][1] * 1000 * 60)
        self.osu_NoteList = self.note_data_to_NoteList(self.hit_objects)


    def read_osu_data(self, file_path, target_header="HitObjects", is_dict = False):
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

    def note_data_to_NoteList(self, note_data):
        osu_NoteList = NoteList()
        counter = 0

        for line in note_data:

            if (line[3] == 1 or line[3] == 4 or line[3] == 5 or line[3] == 6) and line[4] == 0: # DON
                don = Note()
                don.type = NoteType(1)
                don.hit_ms = line[2]
                don.bpm = self.bpm
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
                kat.bpm = self.bpm
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
                don.bpm = self.bpm
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
                kat.bpm = self.bpm
                kat.scroll_x = 1
                kat.scroll_y = 0
                kat.display = True
                kat.index = counter
                counter = counter + 1
                kat.moji = 1

                osu_NoteList.play_notes.append(kat)

            if (line[3] == 2) and (line[4] == 0): # Drum Roll
                source = Note()
                source.type = NoteType(5)
                source.hit_ms = line[2]
                source.bpm = self.bpm
                source.scroll_x = 1
                source.scroll_y = 0
                source.display = True
                source.index = counter
                counter = counter + 1
                #kat.moji = 1

                slider = Drumroll(source)

            if (line[3] == 8): # Balloon
                source = Note()
                source.type = NoteType(7)
                source.hit_ms = line[2]
                source.bpm = self.bpm
                source.scroll_x = 1
                source.scroll_y = 0
                source.display = True
                source.index = counter
                counter = counter + 1
                #kat.moji = 1

                balloon = Balloon(source)
                balloon.type = NoteType(8)
                balloon.hit_ms = line[5]
                balloon.bpm = self.bpm
                balloon.scroll_x = 1
                balloon.scroll_y = 0
                balloon.display = True
                balloon.index = counter
                counter = counter + 1
                #kat.moji = 1
                balloon.count = 999

                osu_NoteList.play_notes.append(balloon)

        osu_NoteList.draw_notes = osu_NoteList.play_notes.copy()

        return osu_NoteList


myparse = OsuParser(osu_file)

print(myparse.bpm)


