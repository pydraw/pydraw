"""
Tests the objects module of pydraw
"""

from pydraw import Object, Rectangle, Screen;

screen = Screen();


def test_object():
    obj = Object(screen, 350, 350);
    obj.moveto(360, 360);
    assert obj.x() == 360 and obj.y() == 360;

def test_rectangle():
    rect = Rectangle(screen, 250, 250, 50, 50);
    rect.moveto(230, 235);
    assert rect.x() == 230 and rect.y() == 235;
    assert rect.width() == 50 and rect.height() == 50;

