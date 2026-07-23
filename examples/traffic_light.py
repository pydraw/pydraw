from pydraw import *


screen = Screen(400, 500, "Traffic Light")
screen.color(Color("lightblue"))

Rectangle(screen, 140, 60, 120, 320, Color("black"))
Text(screen, "Click to change the light", 110, 420, Color("black"))

lights = [
    Oval(screen, 165, 85, 70, 70, Color("gray")),
    Oval(screen, 165, 185, 70, 70, Color("gray")),
    Oval(screen, 165, 285, 70, 70, Color("gray")),
]

colors = [Color("red"), Color("yellow"), Color("green")]
current_light = 0


def update_lights():
    for light in lights:
        light.color(Color("gray"))

    lights[current_light].color(colors[current_light])


def mousedown(location, button):
    global current_light
    current_light = (current_light + 1) % 3
    update_lights()


update_lights()
screen.listen()
screen.loop()
