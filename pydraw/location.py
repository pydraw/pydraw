class Location:
    def __init__(self, x: float, y: float):
        self._x = x;
        self._y = y;

    def move(self, dx: float, dy: float):
        self._x += dx;
        self._y += dy;

    def moveto(self, x: float, y: float):
        self._x = x;
        self._y = y;

    def x(self, new_x: float = None) -> float:
        if new_x is not None:
            self._x = new_x;

        return self._x;

    def y(self, new_y: float = None) -> float:
        if new_y is not None:
            self._y = new_y;

        return self._y;

    def __str__(self):
        return f'(X: {self._x}, Y: {self._y})';

    def __repr__(self):
        return self.__str__();

    def __iter__(self):
        """
        Allows the location to be accessed as a tuple
        """
        yield self._x;
        yield self._y;

    def __getitem__(self, item):
        """
        Allows the location to be accessed as a tuple
        """

        if item == 0:
            return self._x;
        elif item == 1:
            return self._y;
        else:
            raise IndexError(f'Accessed index beyond x and y, index: {item}.');
