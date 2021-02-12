![pyDraw Logo](etc/pydraw.png)

This is a simple graphics library designed to make graphics
and input simple and synchronized.

It was originally designed to replace turtle as the goto graphics library for teaching
computer science. It has grown into a larger project, with loftier goals of creating an 
easy-to-use library that will be easy to learn, teach, and use in almost any circumstance.

Indicators: (⭐ = Important, 🚀 = Awesome/Fun Feature, 😻 = Cat)

### Features
- Simple, One-Line Shape Construction
- Consistent Object Management and Manipulation
- Simplified and Globalized Input System 🚀
- Multi-Screen support, Top-Left Anchored Coordinate System
- Special Shapes, Irregular Polygons
- Precise `.overlaps()` and `.contains()` methods for all Renderables!
  - Highly Optimized Algorithms for __0.01 * 10<sup>-16</sup>s__ runtime (avg).
- Separated Location (Vector2D) and Color classes!
- Support for Tuples/Locations in most cases (no constructors!)
- Designed for LEARNING! 🚀😻

## Getting Started

### Recommended
In order to install pydraw, you can use Python's default dependency repository, 
[pypi](https://pypi.org) by running the command `pip install pydraw` in the terminal.

### Other Options

You can also install pydraw by downloading a release file, `pydraw.py` from the 
[releases](https://github.com/pydraw/pydraw), and placing the file in your project's
directory.


#### After installation, you can import the library with: `from pydraw import *`.

## Basic Setup

---
After importing pydraw, you can write a basic skeleton program like so:

```python
from pydraw import *

screen = Screen(800, 600, 'My First Project!')  # creates a screen to draw on

running = True
while running:
    screen.update()  # We want to update the screen if we make any changes!
    screen.sleep(30 / 1000)  # Limit our updates by a certain time delay, in this case 30fps

screen.exit()  # Must be called at the end of a pydraw program
```

We can create our first object like so:
```python
from pydraw import *

screen = Screen(800, 600, 'My First Project!')

# Here we create a rectangle at x=50, y=50 that is 50 pixels wide and 50 pixels tall.
# It is top-left anchored. This means that the position is the location of the top left corner.
# It's important to know that pydraw's canvas has the origin in the top left, with
# positive-y at the bottom of the screen, and positive-x to the right of the screen.
box = Rectangle(screen, 50, 50, 50, 50) 

running = True
while running:
    screen.update()
    screen.sleep(30 / 1000)

screen.exit()
```


⭐ And getting straight to the point, one of pydraw's primary features is incredibly easy user-input detection.
```python
from pydraw import *

screen = Screen(800, 600, 'My First Project!')

box = Rectangle(screen, 50, 50, 50, 50) 

def mousedown(button, location):
  print('Wow, you pressed the mouse!')

def mouseup(button, location):
  print('How un-impressive...')

def keydown(key):
  print('Keyboard input is key to creating interactive programs!')

def keyup(key):
  print('For when you really just gotta stop moving, keyup is here to save you.')

# All of the above methods must be defined above this statement (because Python):
screen.listen()


# -- As you can see, user input is as simple as defining methods and telling pydraw to listen!
#    This feature has been long overdue for teachers who want to teach Python to their students
#    by making really cool stuff but can't escape how ridiculously input has been handled in the past.
#    Now defining user input is easy to understand and use.


running = True
while running:
    screen.update()
    screen.sleep(30 / 1000)

screen.exit()
```

This library supports many modifiers and methods for almost all objects:
```python
# ... code above

box = Rectangle(screen, 50, 50, 50, 50)
box.x(box.y())  # set the box's x coordinate to its y coordinate
                # notice how you can access the coordinates or change them with methods.

box.location()  # We can get the location like this!

box.move(-5, 100)  # move the box by -5 on the x-axis, 100 on the y.
box.moveto(screen.width() / 2, screen.height() / 2)  # move to near the center of the screen
                                                     # THEORY!: What do we need to do to p

box.width(box.height())  # set the box's width to its height
                         # again, it's important to notice the methods are dual-purpose

box.color(Color('red'))  # let's change the color to red
                         # it's helpful to know that the screen's color is white by default
                         # but, it can be changed with: "screen.color()"

box.border(Color('black'), fill=False)  # now we give the box a black border.
                                        # And we can make it a framed rectangle by setting fill=False

box.rotate(14)  # rotate our box by 14 degrees, clockwise
box.rotation(box.rotation() + 14)  # this is the same as the above line with the rotation method

box.visible(False)  # Hide our box. It is not visible
                    # We can also get the visibility-state by not passing anything

box.remove()  # Just get rid of that old box. We can make a better one soon :)

# code below ...
```

Lastly we can create some other objects and interact with them:
```python
# ... code above

not_a_box = Oval(screen, 400, 50, 100, 100, Color('magenta'))  # now we have a beautiful oval
almost_a_box = Triangle(screen, 200, 450, 100, 50, Color('yellow'), rotation=30) # three sides?
# ^ Also note that we are setting the color, and also setting the rotation of the triangle

# We can create a regular polygon by specifying a number of sides before the location.
schrodingers_box = Polygon(screen, 5, 250, 150, 50, 50, border=Color('red'))

# We can create an evil polygon like this (we can pass in a list of locations or tuples):
weird_evil_box = CustomPolygon(screen, [(500, 50), (550, 50), (550, 100), (500, 50)])
# ^ The real term for these is "Irregular Polygons". But irregular is hard to type so here we are.


# We can interact with these objects with these methods:
not_a_box.overlaps(almost_a_box)  # Do these objects overlap?
weird_evil_box.contains(Location(525, 75))  # Is this point inside the shape?

schrodingers_box.distance(not_a_box)  # Gets the precise distance between the centers

# code below ...
```

---

## API/Docs
The documentation for [pydraw](https://pypi.org/project/pydraw) is available at the main website: https://pydraw.graphics
The documentation is shipped with the package so code completion and method descriptors are
available.

---

## DIY
If you want to build your own version of pydraw, just fork this repository and run 
`python -m build` in the terminal. You should get a release/ directory with a pydraw.py held
dearly within it.

---

### A Big Thanks To:
- Barry Lindler (An incredible person with a brain that can bench 345lbs and a heart of gold)
  - Follow this man on Twitter: [@barrylindler](https://twitter.com/barrylindler)
- Whatever geniuses came up with the crossing number algorithm, and the line-segment orientation algorithm
- Schrödinger for his cat obsession
- The nerd who decided to create ANOTHER language and actually did a good job: Guido van Rossum
  - (He kinda created Python) (Sometimes you can still find him on StackOverflow too...)
- My Dad. For all sorts of reasons. ¯\_(ツ)_/¯

