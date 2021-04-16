from pydraw import Scene, Rectangle, Color

scene: Scene = Scene(800, 600)

# Okay now we place objects in the scene?

# Another issue is input. We are presumably going
# import this scene and then set the screen to it,
# so we will need some input. Perhaps the default
# listener registration actually will work, because
# the entire file gets run when you import it.

box = Rectangle(scene, 10, 10, 50, 50, Color('red'))


def mousedown(button, location):
    box.center(location)


scene.listen()


# Okay so turns out the above code will work. We can
# register events just fine for the scene. But what about
# some sort of loop?

# If we add a while loop here it will not work because
# it will block the main thread. We need to "store" a
# loop rather than create one.

def run():
    # Put loop code here
    running = True
    fps = 30
    while running:
        scene.update()
        scene.sleep(1 / fps)


# ^ The scene functions as a screen object but will
# not actually render anything.

# It's worth noting that you can also register individual
# event methods rather than using the automatic feature:
def some_keydown_method(key):
    print(key)


scene.register('keydown', some_keydown_method)

# The idea behind the feature above would be to allow for
# the creation of a scene and registration of input
# methods within a file that is already registering input
# to a screen or another scene.
