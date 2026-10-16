# Check a settings (.ini) file for mistakes

A small read-only Python tool built step by step. Give it an .ini settings file and it reads it with Python's `configparser` module. It reports the first reading problem with its line number, or lists the sections and how many settings each has. It also asks for every value the way a program would, so a value that Python's default reader cannot use (for example a lone `%`) is reported. It has no code that writes to a file.

## Run it

    python make_sample.py                   # makes four made-up settings files in sample/
    python inicheck.py sample/duplicate.ini # report on one file
    python -m unittest -v                   # 36 temporary-fixture tests

On Windows, if `python` is not found, use `py`.

## Files

- `inicheck.py` - the tool
- `make_sample.py` - makes four made-up files: a good one, one with no section header, one with a repeated setting, one with a lone `%`
- `test_inicheck.py` - tests

## Notes

- It uses Python's default reader rules (strict mode, `%` is special, names are not case sensitive). Settings files for other programs may follow other rules.
- Only the first reading problem is shown. The message wording comes from Python and may differ between versions. The tests check line numbers and the error type.
- A clean report only means Python's reader accepted the file. It does not mean the settings are right for your program.
- It checks that each value can be read. It does not check what the values mean.
- The file is read as UTF-8 (a leading byte order mark is allowed). Other encodings are reported as not valid UTF-8.
- Tests check that the file keeps the same bytes and modified time, and that no file is created.
- Tested only on small made-up files. Python 3.10 and 3.12 on Linux, and, by GitHub Actions, Python 3.12 on Windows and Ubuntu. Not tested on a Windows 10 or 11 desktop.
- Educational example, no warranty. Use at your own risk.
- Code is MIT licensed (see LICENSE). Python is a separate project with its own license; this repository does not include it.

## Private repair, not published yet

Setup now exclusively creates fictional files only in a NEW sample folder,
refusing existing paths, parent traversal and linked/reparse parents. Partial
new setup can remain after interruption: use a different new empty lesson folder
rather than deleting old work. The checker refuses filesystem links/reparse
points in input/ancestors, hardlinks, special entries and parent traversal before
opening bytes. Keep the tree still: no hostile-race guarantee.

The old checker missed DEFAULT-only interpolation failures. The private repair
now asks for DEFAULT values too; two regression tests cover invalid lone-percent
and valid escaped-percent defaults. Four setup and seven filesystem-input tests
bring the total to36. Windows skips the Unix FIFO case; links may skip where
unavailable. Local36tests and full replay pass; two Windows and two Ubuntu full replays pass36tests. Each platform pair
differs only in unittest time and the unique temporary path in the expected
duplicate-option error. Windows skips the Unix FIFO case; Ubuntu runs it.

Resource use is not bounded: parsing can use memory/time on large/complex files.
This is not a security sandbox. Error messages may expose source lines, values,
keys, sections and paths. Keep private reports private. The code does not upload
files, but cannot control cloud sync, telemetry or other software.

https://docs.python.org/3/library/configparser.html
https://docs.python.org/3/library/pathlib.html
https://docs.python.org/3/library/stat.html
