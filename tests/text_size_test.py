"""
Text Size Test: width()/height() must follow size(), font() and the decorations.

Regression for Text#width() reporting the construction-time width after size() (and
font()/bold()/italic()/underline()/strikethrough()) changed the rendered text.
Run: python3 tests/text_size_test.py
"""

from pydraw import *

screen = Screen(600, 400)

message = Text(screen, ' What is ?:', 0, 0)
width_16, height_16 = message.width(), message.height()

message.size(200)
width_200, height_200 = message.width(), message.height()

x0, y0, x1, y1 = screen._canvas.bbox(message._ref)  # noqa - what tk actually drew
assert width_200 > width_16 * 5, f'width() still {width_200} after size(200), was {width_16}'
assert height_200 > height_16 * 5, f'height() still {height_200} after size(200), was {height_16}'
assert abs((x1 - x0) - width_200) <= 4, f'width() {width_200} disagrees with the canvas ({x1 - x0})'

message.size(16)
assert message.width() == width_16, 'width() did not return to the original after size(16)'

message.bold(True)
assert message.width() > width_16, 'width() did not grow for bold'
message.bold(False)

message.font('Courier')
assert message.width() != width_16, 'width() did not change for a new font'

print('text_size_test passed')
screen.update()
