# Examples

These examples are here to show you how to maximize pyDraw's potential in certain areas such as:
- Screen manipulation (width and height)
- Shape creation
- User input
- CustomPolygons
- Text creation
- And more...

The examples are listed in order of complexity and categorized by subject.

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

A multiplayer game: you own your ship and write it directly, so it never lags, while
everyone else's ships replicate in. Health belongs to the server, which also decides
who your shots actually hit -- because a player cannot be trusted to report their own
health. Shows all three of pydraw's networking ideas in one file.

```
python3 net_ships.py            # host and play
python3 net_ships.py <address>  # join someone else
```

Run the first line twice on one machine for two players: whoever starts first hosts.
To run a server with no window at all, on a machine that everyone can reach:

```
python3 -m pydraw.network net_ships:Arena
```
