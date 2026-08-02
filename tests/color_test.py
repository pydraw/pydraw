"""
Color Test: Tests methods in the Color class
"""

import unittest
from pydraw import Color


class ColorTest(unittest.TestCase):
    def test_named_color(self):
        color = Color('red')
        self.assertEqual(color.red(), 255)
        self.assertEqual(color.green(), 0)
        self.assertEqual(color.blue(), 0)
        self.assertEqual(color.rgb(), (255, 0, 0))
        self.assertEqual(color.__value__(), 'red')
        self.assertEqual(color.name(), 'red')

    def test_hex_color_expands_shorthand(self):
        color = Color('#f6f')
        self.assertEqual(color, Color('#ff66ff'))
        self.assertEqual(color.rgb(), (255, 102, 255))
        self.assertEqual(color.hex(), '#f6f')

    def test_rgb_constructors_and_clone(self):
        positional = Color(12, 34, 56)
        tuple_form = Color((12, 34, 56))
        clone = positional.clone()

        self.assertEqual(positional, tuple_form)
        self.assertEqual(clone, positional)
        self.assertIsNot(clone, positional)
        self.assertEqual(positional.__value__(), (12, 34, 56))
        self.assertEqual(hash(positional), hash(tuple_form))

    def test_invalid_arity_and_types(self):
        for arguments in ((), ('red', 'blue'), (1, 2, 3, 4), ('1', 2, 3)):
            with self.subTest(arguments=arguments):
                with self.assertRaises(NameError):
                    Color(*arguments)

    def test_str_is_the_plain_form(self):
        """
        An rgb color used to come out as '((255, 0, 0))'. The f-string held three
        values, so it interpolated a tuple, and the tuple brought its own brackets.
        """
        self.assertEqual(str(Color('red')), 'red')
        self.assertEqual(str(Color('#ff8800')), '#ff8800')
        self.assertEqual(str(Color(255, 0, 0)), '(255, 0, 0)')

    def test_repr_says_what_it_is(self):
        """__str__ is for a person; __repr__ has to be unambiguous."""
        self.assertEqual(repr(Color('red')), "Color('red')")
        self.assertEqual(repr(Color('#ff8800')), "Color('#ff8800')")
        self.assertEqual(repr(Color(255, 0, 0)), 'Color(255, 0, 0)')

    def test_repr_rebuilds_the_color(self):
        for color in (Color('red'), Color('#ff8800'), Color(12, 34, 56)):
            with self.subTest(color=color):
                self.assertEqual(eval(repr(color)), color)      # noqa: S307


if __name__ == '__main__':
    unittest.main()
