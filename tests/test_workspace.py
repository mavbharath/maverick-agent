import tempfile
import unittest
from pathlib import Path
from local_coder.tools import ToolRunner

class WorkspaceTests(unittest.TestCase):
    def test_rejects_path_escape(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "repo"
            root.mkdir()
            runner = ToolRunner(root, allow_shell=False, auto_approve=False)
            with self.assertRaises(ValueError):
                runner._path("../outside")

    def test_read_and_search(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "a.txt").write_text("hello world\n", encoding="utf-8")
            runner = ToolRunner(root, allow_shell=False, auto_approve=False)
            self.assertIn("hello world", runner.call("read_file", {"path": "a.txt"}))
            self.assertIn("a.txt:1", runner.call("search_text", {"query": "hello", "path": "."}))

if __name__ == "__main__":
    unittest.main()
