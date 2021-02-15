# TODO
- [x] Add .overlaps method to Renderables
        
        Make sure you keep in mind that rotations must be taken into account.
  
- [x] Contains must also work with rotations
- [x] Overload methods such as move, moveto, and contains to accept Locations, tuples, and plain x and y
- [x] Dependency injection of PIL, Image resizing, Rotation
- [x] Fix .move and .moveto to work with **kwargs
- [!] Fix .move and .moveto to work with **kwargs for Text (Non-Renderable)
- [x] Add Screen#grab(filename) to take screenshots
- [x] Add type-checks for all methods and constructors
- [x] Add .clone() and .transform() to Renderables (no CustomRenderables)
        
        Will clone shapes, .transform() can clone their transform (width, height, rotation).

- [x] Add more methods for CustomPolygons (.width(), .height(), .border(), etc.)
- [x] Fix `.vertices()` to respond with vertices clockwise from the top-left
- [x] Fix scrollbars on VNC.
- [x] Fix text to properly set height (IMPORTANT!)
- [x] `lookat()` method in Line
- [x] Argument limiting Color
- [x] Add error classes
- [x] Add Lines
- [x] Add Images
- [x] Polygons, regular and non  regular.