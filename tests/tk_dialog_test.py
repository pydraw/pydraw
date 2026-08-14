import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from pydraw.backends.tk import TkBackend


class TkDialogTest(unittest.TestCase):
    def result(self, selected):
        dialog = SimpleNamespace(go=lambda: selected)
        module = SimpleNamespace(SimpleDialog=lambda *args, **kwargs: dialog)
        backend = object.__new__(TkBackend)
        backend.root = object()

        with patch.dict(sys.modules, {"tkinter.simpledialog": module}):
            return backend.alert("text", "title", "yes", "no")

    def test_alert_returns_true_for_accept(self):
        self.assertIs(self.result(0), True)

    def test_alert_returns_false_for_cancel(self):
        self.assertIs(self.result(1), False)


if __name__ == "__main__":
    unittest.main()
