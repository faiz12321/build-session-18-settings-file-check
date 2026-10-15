import io
import os
import shutil
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

import inicheck
import make_sample


def run(path):
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = inicheck.main(["inicheck.py", str(path)])
    return code, buf.getvalue()


class Base(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.dir, True)
        self.sample = make_sample.make(self.dir / "sample")

    def write(self, name, text, raw=None):
        p = self.dir / name
        p.write_bytes(raw if raw is not None else text.encode("utf-8"))
        return p


class Samples(Base):
    def test_good(self):
        code, out = run(self.sample / "good.ini")
        self.assertEqual(code, 0)
        self.assertIn("Sections: 2", out)
        self.assertIn("[app] 2 settings", out)
        self.assertIn("[backup] 2 settings", out)
        self.assertIn("No problems found", out)

    def test_no_section(self):
        code, out = run(self.sample / "nosection.ini")
        self.assertEqual(code, 1)
        self.assertIn("MissingSectionHeaderError on line 1", out)

    def test_duplicate_key_any_case(self):
        code, out = run(self.sample / "duplicate.ini")
        self.assertEqual(code, 1)
        self.assertIn("DuplicateOptionError on line 4", out)

    def test_percent(self):
        code, out = run(self.sample / "percent.ini")
        self.assertEqual(code, 1)
        self.assertIn("Cannot use the value of sale in [shop]", out)
        self.assertIn("%%", out)

    def test_sample_files(self):
        self.assertEqual(sorted(p.name for p in self.sample.iterdir()),
                         ["duplicate.ini", "good.ini", "nosection.ini", "percent.ini"])


class Errors(Base):
    def test_duplicate_section(self):
        p = self.write("a.ini", "[a]\nx=1\n[a]\ny=2\n")
        code, out = run(p)
        self.assertEqual(code, 1)
        self.assertIn("DuplicateSectionError on line 3", out)

    def test_line_without_equals(self):
        p = self.write("b.ini", "[a]\nx = 1\njust some words\n")
        code, out = run(p)
        self.assertEqual(code, 1)
        self.assertIn("ParsingError on line 3", out)

    def test_first_error_only(self):
        p = self.write("c.ini", "[a]\nx = 1\nx = 2\n[a]\n")
        code, out = run(p)
        self.assertIn("on line 3", out)
        self.assertNotIn("on line 4", out)

    def test_not_utf8(self):
        p = self.write("d.ini", "", raw=b"[a]\nname = caf\xe9\n")
        code, out = run(p)
        self.assertEqual(code, 1)
        self.assertIn("not valid UTF-8", out)

    def test_missing_file(self):
        code, out = run(self.dir / "none.ini")
        self.assertEqual(code, 2)
        self.assertIn("Could not read the file", out)

    def test_usage(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            self.assertEqual(inicheck.main(["inicheck.py"]), 2)

    def test_folder_instead_of_file(self):
        code, out = run(self.dir)
        self.assertEqual(code, 2)


class Passes(Base):
    def test_empty_file(self):
        code, out = run(self.write("e.ini", ""))
        self.assertEqual(code, 0)
        self.assertIn("Sections: 0", out)

    def test_comments_only(self):
        code, out = run(self.write("f.ini", "# nothing here\n; or here\n"))
        self.assertEqual(code, 0)

    def test_byte_order_mark_ok(self):
        code, out = run(self.write("g.ini", "", raw=b"\xef\xbb\xbf[a]\nx = 1\n"))
        self.assertEqual(code, 0)
        self.assertIn("[a] 1 settings", out)

    def test_windows_line_endings(self):
        code, out = run(self.write("h.ini", "", raw=b"[a]\r\nx = 1\r\ny = 2\r\n"))
        self.assertEqual(code, 0)
        self.assertIn("[a] 2 settings", out)

    def test_default_section_counted_separately(self):
        code, out = run(self.write("i.ini", "[DEFAULT]\nlang = en\n[a]\nx = 1\n"))
        self.assertEqual(code, 0)
        self.assertIn("Shared settings in [DEFAULT]: 1", out)

    def test_double_percent_is_fine(self):
        code, out = run(self.write("j.ini", "[a]\nsale = 50%% off\n"))
        self.assertEqual(code, 0)

    def test_references_to_other_settings(self):
        code, out = run(self.write("k.ini", "[a]\nhome = /x\nfolder = %(home)s/y\n"))
        self.assertEqual(code, 0)

    def test_reference_to_missing_setting(self):
        code, out = run(self.write("l.ini", "[a]\nfolder = %(nope)s/y\n"))
        self.assertEqual(code, 1)
        self.assertIn("Cannot use the value of folder", out)

    def test_more_than_five_bad_values(self):
        text = "[a]\n" + "".join("b" + str(i) + " = 5% off\n" for i in range(7))
        code, out = run(self.write("m.ini", text))
        self.assertEqual(code, 1)
        self.assertEqual(out.count("Cannot use the value"), 5)
        self.assertIn("and 2 more", out)


class ReadOnly(Base):
    def test_bytes_and_time_unchanged(self):
        for name in ("good", "nosection", "duplicate", "percent"):
            p = self.sample / (name + ".ini")
            b, t = p.read_bytes(), os.stat(p).st_mtime_ns
            run(p)
            self.assertEqual(p.read_bytes(), b)
            self.assertEqual(os.stat(p).st_mtime_ns, t)

    def test_no_new_files(self):
        before = sorted(p.name for p in self.dir.rglob("*"))
        for p in self.sample.iterdir():
            run(p)
        self.assertEqual(sorted(p.name for p in self.dir.rglob("*")), before)


if __name__ == "__main__":
    unittest.main()
