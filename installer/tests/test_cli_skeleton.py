import io
import unittest
from contextlib import redirect_stderr, redirect_stdout

from grdm_dev import cli, exit_codes, toon


class CliSkeletonTests(unittest.TestCase):
    def test_no_command_is_usage_error(self):
        with redirect_stdout(io.StringIO()):
            self.assertEqual(cli.main([]), exit_codes.USAGE)

    def test_unknown_flag_is_usage_error(self):
        with redirect_stderr(io.StringIO()), redirect_stdout(io.StringIO()):
            self.assertEqual(cli.main(["--no-such-flag"]), exit_codes.USAGE)

    def test_messages_table_matches_constants(self):
        table = exit_codes.messages()
        for code in (0, 2, 10, 11, 12, 20, 30, 40, 50, 51, 52, 53, 60):
            self.assertIn(code, table)
            self.assertTrue(table[code][0] and table[code][1])

    def test_toon_table_and_quoting(self):
        out = toon.encode({"rows": [{"a": 1, "b": "x,y"}, {"a": 2, "b": "z"}], "note": "a: b"}, name="r")
        self.assertIn('rows[2]{a,b}:', out)
        self.assertIn('1,"x,y"', out)
        self.assertIn('note: "a: b"', out)


if __name__ == "__main__":
    unittest.main()
