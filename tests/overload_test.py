"""Tests for overload helpers."""

import unittest

from pydraw.overload import Variadic


class VariadicTest(unittest.TestCase):
    def test_accepts_types_and_non_empty_type_tuples(self):
        self.assertEqual(Variadic[int].variadic_type, (int,))
        self.assertEqual(Variadic[(int, str)].variadic_type, (int, str))

    def test_rejects_invalid_entries_consistently(self):
        for value in (None, 3, (), (int, 3), (int, None), 'int'):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    Variadic[value]


if __name__ == '__main__':
    unittest.main()
