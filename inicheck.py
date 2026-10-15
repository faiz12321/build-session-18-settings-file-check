"""Checks a settings (.ini) file for mistakes without changing it.

Run: python inicheck.py FILE.ini
Exit code: 0 = no problem found, 1 = problem found, 2 = could not read.
"""
import configparser
import sys


def first_line(exc):
    line = getattr(exc, "lineno", None)
    if line is None and getattr(exc, "errors", None):
        line = exc.errors[0][0]
    return line


def check(path):
    parser = configparser.ConfigParser()
    try:
        with open(path, encoding="utf-8-sig") as f:
            parser.read_file(f, source=path)
    except UnicodeDecodeError:
        return {"error": {"kind": "UnicodeDecodeError", "line": None,
                          "message": "The file is not valid UTF-8 text."}}
    except configparser.Error as e:
        return {"error": {"kind": type(e).__name__, "line": first_line(e),
                          "message": (getattr(e, "message", str(e)).strip().splitlines() or [""])[0]}}
    # Reading can pass while a value still cannot be used. The default reader
    # treats % as special, so ask for every value the way a program would.
    bad_values = []
    for section in parser.sections():
        for key in parser.options(section):
            try:
                parser.get(section, key)
            except configparser.Error as e:
                bad_values.append((section, key, type(e).__name__))
    sections = {s: len(parser.options(s)) for s in parser.sections()}
    return {"error": None, "sections": sections, "bad_values": bad_values,
            "defaults": len(parser.defaults())}


def report(r):
    e = r["error"]
    if e:
        where = f" on line {e['line']}" if e["line"] else ""
        print(f"Could not read it: {e['kind']}{where}")
        print("Message:", e["message"])
        print("Only the first problem is shown. Fix it and run again.")
        return 1
    print("Sections:", len(r["sections"]))
    for name, count in r["sections"].items():
        print(f"  [{name}] {count} settings")
    if r["defaults"]:
        print("Shared settings in [DEFAULT]:", r["defaults"])
    for section, key, kind in r["bad_values"][:5]:
        print(f"Cannot use the value of {key} in [{section}]: {kind}")
    if len(r["bad_values"]) > 5:
        print("... and", len(r["bad_values"]) - 5, "more. Showing the first 5.")
    if r["bad_values"]:
        print("A % in a value needs to be written as %% for Python's default reader.")
        return 1
    print("No problems found by Python's reader. The file was not changed.")
    print("That does not mean the settings are right for your program.")
    return 0


def main(argv):
    if len(argv) != 2:
        print("Usage: python inicheck.py FILE.ini")
        return 2
    try:
        result = check(argv[1])
    except OSError as e:
        print("Could not read the file:", e)
        return 2
    return report(result)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
