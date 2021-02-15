from pydraw import *

# not overlapping
points1 = [(37.5, -37.5), (37.5, 37.5), (-37.5, 37.5), (-37.5, -37.5)]
points2 = [(30.0, -10.0975), (0.0, 20.2125), (-30, -10.0975)]

screen = Screen(800, 600);
[print(vertex) for vertex in Oval._generate_vertices(10, 9)]
