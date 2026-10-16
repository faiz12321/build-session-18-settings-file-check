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



class DefaultValueChecks(Base):
    def test_default_only_bad_percent_is_reported(self):
        p = self.write('default.ini', '[DEFAULT]\nsale = 50% off\n')
        code, out = run(p)
        self.assertEqual(code, 1)
        self.assertIn('Cannot use the value of sale in [DEFAULT]', out)

    def test_default_only_valid_value_passes(self):
        p = self.write('default.ini', '[DEFAULT]\nsale = 50%% off\n')
        code, out = run(p)
        self.assertEqual(code, 0)


class SafeSetup(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.sample = self.root / 'sample'

    def test_existing_folder_preserves_nested_bytes_and_mtime(self):
        (self.sample / 'nested').mkdir(parents=True)
        keep = self.sample / 'nested' / 'keep'
        keep.write_bytes(b'KEEP')
        before = keep.read_bytes(), keep.stat().st_mtime_ns
        with self.assertRaises(FileExistsError):
            make_sample.make(self.sample)
        self.assertEqual(before, (keep.read_bytes(), keep.stat().st_mtime_ns))

    def test_existing_file_preserved(self):
        self.sample.write_bytes(b'KEEP')
        before = self.sample.read_bytes(), self.sample.stat().st_mtime_ns
        with self.assertRaises(FileExistsError):
            make_sample.make(self.sample)
        self.assertEqual(before, (self.sample.read_bytes(), self.sample.stat().st_mtime_ns))

    def test_repeat_preserves_every_output(self):
        make_sample.make(self.sample)
        before = {p.name:(p.read_bytes(),p.stat().st_mtime_ns) for p in self.sample.iterdir()}
        with self.assertRaises(FileExistsError):
            make_sample.make(self.sample)
        self.assertEqual(before, {p.name:(p.read_bytes(),p.stat().st_mtime_ns) for p in self.sample.iterdir()})

    def test_cli_repeat_preserves_every_output(self):
        import subprocess, sys
        script = self.root / 'make_sample.py'
        shutil.copyfile(Path(make_sample.__file__).resolve(), script)
        make_sample.make(self.sample)
        before = {p.name:(p.read_bytes(),p.stat().st_mtime_ns) for p in self.sample.iterdir()}
        result = subprocess.run([sys.executable, str(script)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 1)
        self.assertIn('sample already exists', result.stderr)
        self.assertEqual(before, {p.name:(p.read_bytes(),p.stat().st_mtime_ns) for p in self.sample.iterdir()})


class InputSafety(Base):
    def test_hardlink_refused_preserves_target(self):
        target = self.sample / 'good.ini'
        before = target.read_bytes(), target.stat().st_mtime_ns
        link = self.dir / 'hard.ini'
        os.link(target, link)
        code, out = run(link)
        self.assertEqual(code, 2)
        self.assertIn('singly linked', out)
        self.assertEqual(before, (target.read_bytes(), target.stat().st_mtime_ns))

    def test_directory_refused(self):
        code, out = run(self.sample)
        self.assertEqual(code, 2)
        self.assertIn('regular file', out)

    def test_fifo_refused_without_blocking(self):
        if not hasattr(os, 'mkfifo'):
            self.skipTest('Unix named pipes unavailable')
        import subprocess, sys
        pipe = self.dir / 'pipe.ini'
        os.mkfifo(pipe)
        result = subprocess.run([sys.executable, str(Path(inicheck.__file__).resolve()), str(pipe)],
                                capture_output=True, text=True, timeout=5)
        self.assertEqual(result.returncode, 2)
        self.assertIn('regular file', result.stdout)

    def test_existing_and_dangling_file_symlinks_refused(self):
        target = self.sample / 'good.ini'
        before = target.read_bytes(), target.stat().st_mtime_ns
        link = self.dir / 'link.zip'
        try:
            link.symlink_to(target)
        except OSError:
            self.skipTest('Symlink creation unavailable')
        code, out = run(link)
        self.assertEqual(code, 2)
        self.assertIn('Links/reparse', out)
        link.unlink()
        missing = self.dir / 'absent.ini'
        link.symlink_to(missing)
        code, out = run(link)
        self.assertEqual(code, 2)
        self.assertFalse(missing.exists())
        self.assertEqual(before, (target.read_bytes(), target.stat().st_mtime_ns))

    def test_parent_directory_symlink_refused(self):
        link = self.dir / 'linked'
        try:
            link.symlink_to(self.sample, target_is_directory=True)
        except OSError:
            self.skipTest('Symlink creation unavailable')
        code, out = run(link / 'good.ini')
        self.assertEqual(code, 2)
        self.assertIn('Links/reparse', out)

    def test_parent_traversal_refused(self):
        path = self.sample / '..' / 'sample' / 'good.ini'
        code, out = run(path)
        self.assertEqual(code, 2)
        self.assertIn('Parent-traversal', out)

    def test_self_loop_symlink_refused(self):
        link = self.dir / 'loop'
        try:
            link.symlink_to(link)
        except OSError:
            self.skipTest('Symlink creation unavailable')
        code, out = run(link)
        self.assertEqual(code, 2)
        self.assertIn('Links/reparse', out)



if __name__ == "__main__":
    unittest.main()
