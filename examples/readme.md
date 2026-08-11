# Examples

These examples are here to show you how to maximize pyDraw's potential in certain areas such as:
- Screen manipulation (width and height)
- Shape creation
- User input
- CustomPolygons
- Text creation
- And more...

The examples are listed in order of complexity and categorized by subject.

See the [networking guide](../network.md) for a complete multiplayer
walkthrough and API overview.

### Bouncy Window

Just a basic window with two boxes that bounce around, and when they overlap they change color!
![screenshot](https://i.ibb.co/tH8xHD7/bouncy-window.png)

### Clock

Using the vertices of our shape we can orbit around with lines!
![screenshot](https://i.ibb.co/Yhr8LCX/clock.png)

### Painter

Creating CustomPolygons, Text, and Lines all in one! This example also displays collection
of keyboard and mouse input in a fairly complex and functional fashion.

![screenshot](https://i.ibb.co/mq1k9V9/painter.png)

### Net Paint

A shared canvas: everyone draws, and everyone sees it. The simplest kind of
multiplayer -- send what you drew, listen for what everyone else drew.

### Net Pong

The server owns the ball, the score and the paddles. Clients only ask to move; the
server decides whether to believe them, which is why nobody can fake the score.

### Net Ships

A simple multiplayer game with no custom Room. Each player owns their position,
health, and score. Players use `net.send()` for `fire` and `score` events.

```
python3 net_ships.py            # host and play
python3 net_ships.py <address>  # join someone else
```

### Net Ships v2

The same game with server-owned health, scoring, hit detection, and spawns. It
shows `Room`, `@action`, `player.state`, `player.seed()`, and `player.reset()`.

```
python3 net_ships_v2.py
python3 net_ships_v2.py <address>
```

To run v2 as a server with no window:

```
python3 -m pydraw.network net_ships_v2:Arena
```
