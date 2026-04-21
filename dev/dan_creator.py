import json
import sys
from pathlib import Path


def create_dan(cache_path: Path):
    dan_data = {}
    dan_data["title"] = input("Enter the title: ")
    dan_data["color"] = int(
        input("Enter the color (0 10th Kyuu, 1 5th Kyuu, 2 Shodan, 3 6th Dan, 4 Kurouto, 5 Tatsujin, 6 Gaidan): "))
    exam_num = int(input("Enter the number of exams: "))
    dan_data["exams"] = []
    for i in range(exam_num):
        exam = dict()
        exam["type"] = input(f"Enter exam type {i + 1}: ")
        exam["red_value"] = int(input(f"Enter exam red value {i + 1}: "))
        exam["gold_value"] = int(input(f"Enter exam gold value {i + 1}: "))
        exam["range"] = input(f"Enter exam range {i + 1}: ")
        exam["value"] = [exam["red_value"], exam["gold_value"]]
        exam.pop("red_value")
        exam.pop("gold_value")
        dan_data["exams"].append(exam)
    dan_data["charts"] = []
    for i in range(3):
        chart = dict()
        chart_path = Path(input(f"Enter chart path {i + 1}: "))
        with open(f"{cache_path}/path_to_hash.json", encoding='utf-8') as path_hash_file:
            hash_directory = json.load(path_hash_file)
            chart["hash"] = hash_directory.get(chart_path)
        with open(f"{cache_path}/song_hashes.json", encoding='utf-8') as song_hash_file:
            hash_directory = json.load(song_hash_file)
            chart["title"] = hash_directory[chart["hash"]][0]["title"]["en"]
            chart["subtitle"] = hash_directory[chart["hash"]][0]["subtitle"]["en"]
        chart["difficulty"] = int(input(f"Enter chart difficulty {i + 1}: "))
        dan_data["charts"].append(chart)
    with open("dan.json", "w", encoding="utf-8") as output_file:
        json.dump(dan_data, output_file, indent=4, ensure_ascii=False)
        print("Dan data saved successfully.")


def main():
    create_dan(Path(sys.argv[1]))


if __name__ == "__main__":
    main()
