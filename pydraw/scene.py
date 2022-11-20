from pydraw import Screen, Location;


class Scene:
    """
    An abstraction of the Screen, designed to store the Screen in a certain state while retaining registered input
    handlers and the positions and attributes of objects registered to it.

    You can use Scenes to create multi-screen games or to manage different levels easily. It works exactly like a screen
    but will not render anything until it is "applied" to a Screen via `Screen.scene(some_scene)`
    """

    def __init__(self):
        self._screen = None;

    def screen(self):
        """
        Retrieve the screen that the scene is tied to
        :return: a Screen
        """
        return self._screen;

    def start(self) -> None:
        """
        Run as the initializer for the scene
        :return: None
        """

    def run(self) -> None:
        """
        Run the scene (the loop should go here)
        :return: None
        """

    def mousedown(self, location: Location, button: int) -> None:
        """
        Mouse event, called when a mouse button is pressed down.
        :param button: the button pressed (0-2)
        :param location: the location that was clicked
        :return: None
        """

    def mouseup(self, location: Location, button: int) -> None:
        """
        Mouse event, called when a mouse button is released.
        :param button: the button released (0-2)
        :param location: the location that was clicked
        :return: None
        """

    def mousedrag(self, location: Location, button: int) -> None:
        """
        Mouse event, called when the mouse moves after a mousedown event (without a mouseup event)
        :param button: the button being held (0-2)
        :param location: the Location the mouse has moved to
        :return: None
        """

    def mousemove(self, location: Location) -> None:
        """
        Mouse event called when the mouse moves over the Screen
        :param location: the Location the mouse moved to
        :return: None
        """

    def keydown(self, key: Screen.Key) -> None:
        """
        Key event called when a key is pressed
        :param key: the Key that was pressed
        :return: None
        """

    def keyup(self, key: Screen.Key) -> None:
        """
        Key event called when a key is released
        :param key: the Key that was released
        :return: None
        """

    def activate(self, screen: Screen) -> None:
        """
        Activates the Scene with a Screen (called internally)
        :param screen: the Screen to display the Scene on
        :return: None
        """

        self._screen = screen;
        self.start();
        self.run();
