"""Makes four small made-up settings files to practise on.

Run: python make_sample.py
"""
from pathlib import Path

FILES = {
    "good.ini": "[app]\nname = Notes\nlanguage = en\n\n[backup]\nfolder = C:/Notes/backup\nkeep = 5\n",
    "nosection.ini": "name = Notes\n\n[app]\nlanguage = en\n",
    "duplicate.ini": "[app]\nname = Notes\nlanguage = en\nName = Notes 2\n",
    "percent.ini": "[shop]\nsale = 50% off\nitem = tea\n",
}


def make(folder):
    folder = Path(folder)
    folder.mkdir(exist_ok=True)
    for name, text in FILES.items():
        (folder / name).write_bytes(text.encode("utf-8"))
    return folder


if __name__ == "__main__":
    make("sample")
    print("Made sample/good.ini, nosection.ini, duplicate.ini and percent.ini")
