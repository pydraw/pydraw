![pyDraw](https://pydraw.graphics/logo.png)

![version](https://img.shields.io/pypi/v/pydraw)

pyDraw is a graphics library built to keep drawing and input simple and synchronized.

It started as a replacement for turtle in computer science classrooms. It has grown quite
a bit since then, but the goal is still the same: make graphics easy to learn, easy to
teach, and useful beyond the first lesson.

## Features

- Simple, one-line shape construction
- Consistent object management and manipulation
- Straightforward mouse and keyboard input
- A top-left anchored coordinate system
- Regular shapes and custom polygons
- Precise `.overlaps()` and `.contains()` methods for Renderables
- Dedicated `Location` (Vector2D) and `Color` classes
- Support for tuples and Locations throughout the API, including constructors
- Designed to be learned, taught, and extended

## Getting Started

### Recommended

The easiest way to install pyDraw is from [PyPI](https://pypi.org/project/pydraw/):

```shell
python -m pip install pydraw
```

### Other Options

You can also download the single-file `pydraw.py` from the
[releases page](https://github.com/pydraw/pydraw/releases) and place it in your project's
directory.

After installation, you can import the library with:

```python
from pydraw import *
```

The wildcard import contains pyDraw's supported drawing API. Explicit imports work too,
of course, if that better suits your project.

## Basic Setup

After importing pydraw, you can write a basic skeleton program like so:

```python
from pydraw import *

screen = Screen(800, 600, 'My First Project!')  # Create a screen to draw on.

screen.loop()  # Keep the program open and update the screen each frame.
```

We can create our first object with just one new line:
```python
from pydraw import *

screen = Screen(800, 600, 'My First Project!')

# This creates a rectangle at x=50, y=50 that is 50 pixels wide and 50 pixels tall.
# Shapes are top-left anchored, so this position is the rectangle's top-left corner.
# The canvas origin is also at the top left: positive x goes right and positive y goes down.
box = Rectangle(screen, 50, 50, 50, 50)

screen.loop()
```


And getting straight to the point, one of pyDraw's primary features is easy user input:
```python
from pydraw import *

screen = Screen(800, 600, 'My First Project!')

box = Rectangle(screen, 50, 50, 50, 50)

def mousedown(location, button):
    print(f'Wow, mouse button {button}!')

def mouseup(location, button):
    print('How un-impressive...')

def keydown(key):
    print(f'You pressed {key}. Keyboard input!')

def keyup(key):
    print('For when you really just gotta stop moving, keyup is here to save you.')

# All of the above methods must be defined above this statement (because Python):
screen.listen()


# As you can see, input is just a matter of defining functions and telling pyDraw to listen.
screen.loop()
```

Most objects use the same getter/setter style, so once you know one shape, the others feel
familiar:
```python
# ... code above

box = Rectangle(screen, 50, 50, 50, 50)  # Remember this is (x, y, width, height)!
box.x(box.y())  # Set the box's x coordinate to its y coordinate.
                # Calling box.x() without a value returns the current coordinate.

box.location()  # We can get its Location like this!

box.move(-5, 100)  # Move by -5 on the x-axis and 100 on the y-axis.
box.moveto(screen.width() / 2, screen.height() / 2)  # Move near the screen's center.

box.width(box.height())  # Set the box's width to its height.

box.color(Color('red'))  # Let's change the color to red.
screen.color(Color('lightblue'))  # The screen background can change too.

box.border(Color('black'), fill=False)  # Add a black border without filling the shape.

box.rotate(14)  # Rotate our box by 14 degrees clockwise.
box.rotation(box.rotation() + 14)  # The rotation method can get and set the angle too.

box.visible(False)  # Hide our box. Calling box.visible() returns its current state.

box.remove()  # Just get rid of that old box. We can make a better one soon :)

# code below ...
```

Lastly we can create some other objects and interact with them:

All the Renderables below support the common methods above, including `overlaps()` and
`contains()`. `CustomPolygon` and `Image` have specialized constructors and a few extra
operations, but they still share the same geometry and collision API.
```python
# ... code above

not_a_box = Oval(screen, 400, 50, 100, 100, Color('magenta'))  # now we have a beautiful oval
almost_a_box = Triangle(screen, 200, 450, 100, 50, Color('yellow'), rotation=30)  # uno dos tres
# ^ Also note that we are setting the color, and also setting the rotation of the triangle,
# but the other parameters are still in the usual format: (x, y, width, height).
# IMPORTANT: Triangle's base is on the left, with the triangle's location as its top corner.

# We can create a regular polygon by specifying a number of sides before the location.
# The constructor is (screen, num_sides, x, y, width, height)!
schrodingers_box = Polygon(screen, 5, 250, 150, 50, 50, border=Color('red'))

# We can create an evil polygon like this (we can pass in a list of locations or tuples):
weird_evil_box = CustomPolygon(screen, [(500, 50), (550, 50), (550, 100), (500, 50)])
# ^ The real term for these is "irregular polygons." But irregular is hard to type,
#   so here we are.


# We can interact with these objects with these methods:
not_a_box.overlaps(almost_a_box)  # Do these objects overlap?
weird_evil_box.contains(Location(525, 75))  # Is this point inside the shape?

schrodingers_box.distance(not_a_box)  # Gets the precise distance between the centers

# code below ...
```

### Text, Images, and Lines

Text, Image, and Line follow the same general rules as other objects, with a few operations
of their own.

#### Text
```python
# ... code above

text = Text(screen, 'Some Cool Text!', 0, 0, Color('purple'))
text.center(screen.width() / 2, screen.height() / 2)  # Centering text is easy!
text.font('Calibri')
text.rotate(45)  # You can still rotate text if you want :)

text.bold(True)
text.underline(True)
text.strikethrough(False)

# code below ...
```

#### Images
```python
# ... code above

image = Image(screen, 'image.png', screen.width() / 3, screen.height() / 3)
# ^ We can load an image like this, and it will display on the screen.
# PNG, GIF, and PPM images can be displayed directly. Resizing, tinting, rotating,
# flipping, and other bitmap operations use Pillow. It is installed with the package;
# single-file users can install it with: python -m pip install pillow

# Now that we have Pillow installed, we can have some fun.
image.width(150)
image.height(150)

image.rotate(5)

image.color(Color('red'), alpha=123)
# ^ This will tint the image with a red color, at an alpha level of 123 (default).
# If you increase the alpha, the image will become less visible and the tint-color more so,
# and vice versa.

# code below ...
```

#### Lines
```python
# ... code above

# Let's create a nice line that goes across the screen with a beautiful blue color.
line = Line(screen, 150, 150, screen.width() - 50, screen.height() - 50,
            color=Color('blue'))

# We can modify the line's thickness:
line.thickness(5)

# We can even rotate the line!
line.rotate(35, point=1)  # Note that here we are specifying which point to rotate AROUND!

# We can use a special feature of lines to make them point at stuff!
line.lookat(another_location)  # SUPER NIFTY!

# code below ...
```

---

## Documentation
The documentation is available at [pydraw.graphics](https://pydraw.graphics). Documentation
is also shipped with the package, so supporting IDEs can show completion and method details.

---

## Extending pyDraw

The normal drawing API lives at the package root. If you are building a new platform backend,
the lower-level contracts are kept in `pydraw.runtime`, `pydraw.render`, and `pydraw.events`.
This keeps the beginner-facing API small without closing off the internals meant for extension.

Custom drawing objects can build on `Object`, `Renderable`, `CustomRenderable`, or
`CustomPolygon`, depending on how much of pyDraw's geometry behavior they need.

---

## DIY

If you want to build your own version of pyDraw, fork this repository and make it yours.
Running `python tools/compile.py` from the repository root creates the single-file build at
`compiled/pydraw.py`, where it will be held dearly.

---

## License

pyDraw is available under the [MIT License](LICENSE.md).

Third-party components and examples that carry their own license notices remain
subject to those notices.

---

## A Big Thanks To

- Barry Lindler (An incredible person and a good friend)
  - Follow this man on Twitter: [@barrylindler](https://twitter.com/barrylindler)
- Whatever geniuses came up with the crossing number algorithm, and the line-segment orientation algorithm
- Schrödinger for his cat obsession
- The nerd who decided to create ANOTHER language and actually did a good job: Guido van Rossum
  - (He kinda created Python) (Sometimes you can still find him on StackOverflow too...)
- My Dad. For all sorts of reasons. ¯\_(ツ)_/¯
