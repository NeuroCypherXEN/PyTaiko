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

osu_file = Path("./Renatus.osu")
contents = osu_file.open(mode='r', encoding='utf-8').read()

class OsuParser:
    def __init__(self):

    def read_osu_data(self, file_path, target_header="HitObjects"):
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

                    if re.match(r'\w*\:\s(\w*.?\w*)', line): # General, Editor, Metadata, Difficulty
                        match = re.search(r'\w*\:\s(\w*.?\w*)', line)
                        if match:
                            data.append(match.group(1))

                else:
                    continue

        return data

    def note_data_to_NoteList(self, note_data):
        osu_NoteList = NoteList()
        counter = 0
        for line in note_data:
            if line[3] == 1 and line[4] == 0: # DON
                don = Note()
                don.type = NoteType(1)
                don.hit_ms = line[2]
                don.bpm = 207
                don.scroll_x = 1
                don.scroll_y = 0
                don.display = True
                don.index = counter
                counter = counter + 1
                don.moji = 0
                osu_NoteList.play_notes.append(don)
            if line[3] == 1 and line[4] != 0: # KAT
                kat = Note()
                kat.type = NoteType(2)
                kat.hit_ms = line[2]
                kat.bpm = 207
                kat.scroll_x = 1
                kat.scroll_y = 0
                kat.display = True
                kat.index = counter
                counter = counter + 1
                kat.moji = 1
                osu_NoteList.play_notes.append(kat)
        osu_NoteList.draw_notes = osu_NoteList.play_notes.copy()
        return osu_NoteList


myparse = OsuParser()

print(myparse.read_osu_data(osu_file, target_header="TimingPoints"))


