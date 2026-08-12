# Render Abstraction Plan

## Adopted Decisions

- Normal user programs remain unchanged: they import pyDraw and call
  `Screen(...)` without selecting a backend.
- pyDraw lazily selects its built-in Tk runtime locally. The website installs
  an external browser runtime before executing the user's module.
- The open package owns platform-neutral state, render/event data, the runtime
  extension contract, the Tk backend, and backend conformance tests. It never
  imports the private browser package.
- Browser user code runs in a Python worker. DOM input reaches it through
  shared memory, and neutral render batches go to a separate renderer worker
  that owns a retained scene and the Canvas.
- `Screen.update()` remains synchronous and returns after the renderer
  acknowledges the frame. User tracebacks are captured independently of
  private runtime and renderer diagnostics.

## Goal

Make pyDraw independent of Turtle and Tk while preserving the current native
behavior. The open-source package will provide a platform-neutral core and a
built-in Tk backend. A separately distributed DOM renderer will be able to plug
into the same core for PyScript applications.

```text
User pyDraw application
           |
           v
Public pyDraw API
Objects, Screen, geometry, colors, collisions
           |
           v
Platform-neutral scene model
Render nodes in public screen coordinates
           |
           v
Backend contract
     /            \
    v              v
Built-in Tk      External DOM/Canvas
backend          backend
```

## 1. Lock Down Current Behavior

The temporary render compatibility suite records the behavior of the current
implementation before the rendering system changes. It covers:

- Exact visible coordinates
- Movement and rotation
- Shape, text, image, and Pen placement
- Styling and visibility
- Stacking order
- Mouse and keyboard coordinate translation
- `update()` and `loop()` behavior

This suite remains in place throughout the refactor and acts as the behavioral
baseline for the native backend.

## 1.5. Prove the Browser Path Is Viable

Before designing the production abstraction around assumptions, build a small
end-to-end PyScript vertical slice. It must prove the intended integration path,
not merely that PyScript can draw directly to a canvas.

The proof of concept should contain three deliberately separate pieces. These
can be small demo modules rather than production pyDraw source:

1. A small user Python application written against a pyDraw-shaped API.
2. A miniature platform-neutral core that accepts an explicitly supplied
   backend and models only the behavior needed by the demo.
3. A separate DOM renderer module that implements that hook and draws into an
   HTML Canvas element.

The initial spike usage resembled:

```python
from pydraw import Screen, Rectangle
from pydraw_dom import DOMBackend

screen = Screen(640, 480, backend=DOMBackend("#pydraw-canvas"))
box = Rectangle(screen, 20, 20, 100, 80)
```

This explicit `backend=` argument was only a convenient experimental seam. The
spike exists to discover what the production API must support, so it should not
make temporary architectural changes to the real library merely to support the
experiment. Reusing actual pyDraw source is optional if doing so becomes
simpler after inspecting its import boundaries.

The demo must verify all of the following:

- PyScript can load the user application, the miniature core, and the separately
  packaged renderer module.
- The demonstrated core-to-renderer path has no dependency on Tk or Turtle.
- The external module can be injected without pyDraw importing or knowing about
  that module.
- A pyDraw object becomes a visible Canvas drawing through that renderer.
- A later mutation of the object produces a visible redraw.
- At least one browser pointer or keyboard event travels back through the
  adapter and invokes a pyDraw callback with the correct coordinates.
- Rendering is scheduled without blocking the browser event loop.

The deliverable is a tiny reproducible browser demo plus notes recording any
PyScript, Pyodide, packaging, import, event-loop, or Canvas constraints found.
It is a go/no-go gate for the rest of the design: revise the proposed contracts
if the vertical slice shows that they do not fit the browser runtime.

### Spike Result

The vertical slice lives in the separate sibling repository
`pydraw-render-spike`. It successfully demonstrates:

- A user application importing a neutral pyDraw-shaped core and explicitly
  injecting a separately imported DOM backend
- Local package loading under PyScript without Tk or Turtle
- Immutable render data reaching an HTML Canvas
- A user mutation scheduled through `requestAnimationFrame`
- Exact Canvas-relative pointer coordinates traveling back into a Python user
  callback and producing a redraw

The project includes native core-contract tests, an automatic in-browser smoke
test, and a findings document. The external-backend direction is viable. The
event-loop follow-up also proves that the traditional tight `screen.update()`
pattern can remain responsive when user Python runs in a worker and `update()`
drains a main-thread event queue. A further optimized probe transferred the
Canvas into that worker and replaced synchronous event polling with a
shared-memory ring. Across three 1,000-event runs, median input latency was
0.015-0.025 ms and p95 was 0.035-0.045 ms, comparable to native Tk's 0.041 ms
median and 0.047 ms p95.

## 2. Define a Platform-Neutral Render Model

Objects must stop talking directly to a Tk canvas. Instead, they produce render
nodes using pyDraw's public top-left coordinate system.

Likely node types are:

- Polygon or path
- Ellipse
- Line or polyline
- Text
- Image

The first retained shape slice implements `PolygonNode` and `EllipseNode`.
Rectangle, RoundedRectangle, Triangle, Polygon, and CustomPolygon emit
polygons. RoundedRectangle generates actual rounded-corner vertices in core;
its radius is no longer implemented by abusing Tk border width. Oval emits an
ellipse with center, radii, and rotation as well as its current tessellated
points. The Tk backend uses those points because Tk Canvas cannot rotate native
ovals; a DOM backend may render the semantic ellipse directly. Calling
`Oval.wedges()` sets `render_as_polygon` on the node so every backend preserves
the explicitly requested polygonal rendering instead of silently ignoring it.
Core continues
to use the tessellated vertices for `contains()`, `overlaps()`, bounds, slices,
and custom wedge counts, so the native DOM path does not require separate
ellipse-specific geometry algorithms.

Text emits `TextNode` with a neutral font description, alignment, decorations,
rotation, and public-screen placement. Text measurement is a synchronous
backend service because core needs dimensions immediately for layout and
collision geometry. Tk implements it with Tk font metrics; a DOM backend can
use Canvas text metrics.

Image emits `ImageNode` containing its source, transform, tint, border,
resampling, flip, animation-frame, and visibility state. Core owns image
geometry but not decoding or platform image handles. Intrinsic-size and frame
count queries are synchronous backend services. Tk retains native
PNG/GIF/PPM images when no processing is needed and uses Pillow for transformed
bitmaps; a DOM backend can use browser decoding and native Canvas transforms.

Each node contains ordinary Python data only:

- A stable ID
- Screen-space geometry
- Fill and stroke
- Visibility
- Z-order
- Text and font or image information
- Any required transform

Tk objects, Canvas item IDs, Turtle coordinates, and browser objects must not
enter this model. Geometry and coordinate rules remain owned by pyDraw core; a
renderer must not reproduce the old centered-Turtle coordinate translation.

## 3. Introduce the Backend Contract

The per-screen backend should favor correctness and simplicity:

```python
class ScreenBackend(Protocol):
    def listen(self): ...
    def poll_events(self) -> tuple[InputEvent, ...]: ...
    def present(self, batch: RenderBatch): ...
    def run(self, step): ...
    def close(self): ...
```

A runtime creates the backend with a `ScreenConfig`, so mounting and initial
size configuration do not require a second public lifecycle API. `run(step)`
implements `Screen.loop()` by invoking the supplied core step until the screen
closes. Core retains render sources by stable ID and coalesces repeated
mutations. Each update contains only created, changed, removed, or reordered
nodes. Each backend may choose its own retained implementation strategy:

- Tk can retain Canvas items and diff frames by stable node ID.
- HTML Canvas can retain the neutral scene and redraw when a batch arrives.
- A test, SVG, or other future renderer can consume the same batches.

Tk schedules the global core step from inside `mainloop()` on a 1 ms timer. It
does not present a frame before entering the loop or recursively poll Tk while
the loop is active. A continuously rescheduled idle callback is not used
because it can starve Tk input and timers. Scheduled callbacks can mutate
retained objects and the following step presents those mutations before the
next callback cycle.

`InputEvent` carries a kind plus an optional screen-space position, button, or
normalized key. Tk callbacks only enqueue these plain values. `Screen.update()`
drains them in order, invokes user handlers, and then presents the resulting
render batch. Tk never calls a Screen handler directly. Exceptions raised by a
handler leave `update()` and `loop()` with their original identity and traceback;
the Tk loop catches them only long enough to quit `mainloop()` and re-raise.

The native event benchmark delivered 300 generated pointer events through this
boundary at 0.114 ms median and 0.160 ms p95 with explicit `update()`, and
0.057 ms median and 0.083 ms p95 under `screen.loop()`.

The neutral interface must not imitate Tk operations such as
`create_polygon()`, `coords()`, or `itemconfigure()`. Idle updates do not walk
the scene, and multiple mutations to one object before `Screen.update()`
produce only its latest node.

## 4. Separate Rendering From Platform and Runtime Services

Rendering alone does not cover everything currently supplied through Turtle.
The per-screen backend must eventually cover:

- Window or Canvas lifecycle
- Additional host-specific input capabilities
- Frame scheduling and clocks
- Keyboard focus
- Image loading
- Dialogs
- Possibly screenshots

Screen background and title are explicit backend operations. Background is
required rendering state. Title is optional host behavior: Tk applies it to the
window, while a DOM backend may deliberately do nothing or map it to website UI.

Do not expose a hierarchy of renderer, host, scheduler, and platform objects at
the outset. The public extension boundary needs only two roles:

1. A process-wide `Runtime` creates a backend for each `Screen`.
2. A per-screen `ScreenBackend` exchanges plain input events and render frames
   with the platform.

The runtime is a factory rather than a shared backend instance so multiple
screens cannot accidentally share mutable window or event state. The core API
is intentionally small:

```python
class Runtime(Protocol):
    def create_screen(self, config: ScreenConfig) -> ScreenBackend: ...

def install_runtime(runtime: Runtime) -> None: ...
```

`ScreenBackend` initially needs only lifecycle, event polling, frame
presentation, and loop support. Render nodes, frames, and normalized input
events are immutable platform-neutral data. Rendering and host responsibilities
may remain separate inside a backend, especially in the private browser
implementation, without making that split part of the initial public contract.

The platform-service pass also moves drawable/window sizing, resize and
fullscreen requests, background images, dialogs, screenshots, and image-source
resolution behind `ScreenBackend`. A browser backend can therefore construct a
normal `Screen` without exposing Tk-style `root`, `canvas`, `screen`, or
`turtle` objects. Tk keeps those names only as temporary compatibility aliases
for legacy code that has not yet migrated. Image core treats `source` as an
opaque backend identifier, allowing a browser runtime to accept virtual-file,
URL, blob, or packaged-resource forms without weakening Tk's existing local
path validation.

Frame pacing remains in core for now. `Screen.sleep()` uses Python's monotonic
clock and sleep semantics; it should move behind the runtime only if Pyodide
worker testing demonstrates a behavioral or scheduling mismatch.

The default resolver lazily imports the built-in Tk runtime when the first
`Screen` is created. The browser bootstrap calls `install_runtime(...)` before
executing the user module. Runtime selection locks after the first screen so a
program cannot silently change platforms midway through execution. Importing
`pydraw` in Pyodide must not import Tk, and core must never auto-import or probe
for the external browser package.

Consequently, the same source file calls `Screen(...)` locally and on the
website without browser-specific imports, arguments, or edits. An internal
runtime override may be provided for tests, but explicit backend selection is
not part of the normal user model.

`Screen.update()` owns the cross-platform semantics: it polls normalized
events, dispatches callbacks, builds the current frame, and presents it
synchronously. It is the application loop boundary and is not reentrant. Event
callbacks mutate state and return; calling `update()` from inside a callback is
outside the supported execution model and may be rejected explicitly. The
browser backend implements synchronous presentation by waiting for its renderer
acknowledgement, while Tk implements the same contract locally.

## 5. Add an In-Memory Reference Backend

Create a `RecordingBackend` that reconstructs retained scene state from the
batches emitted by core.
Tests can then assert:

- Exact geometry
- Colors and styles
- Ordering
- Stable IDs
- Visibility behavior
- Absence of backend-specific values

This provides both a unit-test backend and a reference for the external DOM
renderer. The public repository should ideally expose a backend conformance test
kit that the separate renderer can run.

## 6. Migrate the Existing Implementation Incrementally

Move one complete vertical slice at a time:

1. Screen initialization and background
2. Lines and Pen
3. Rectangle, Triangle, Polygon, and CustomPolygon
4. Oval
5. Text
6. Images
7. Visibility and stacking
8. Mouse and keyboard events
9. Update, loop, dialogs, and lifecycle

For each slice, core produces neutral render state, the Tk renderer reproduces
the existing visible result, and the compatibility suite continues to pass.
Direct Canvas access disappears from that object type before proceeding to the
next slice.

During this migration the Tk renderer may temporarily sit on Turtle's Canvas.
Once core no longer depends on Turtle semantics, replace the remaining setup
with raw Tk.

## 7. Remove Turtle and Its Coordinate Translation

After the rendering and host boundaries are established:

- Replace `turtle.Screen()` with raw Tk setup.
- Remove centered Turtle Canvas coordinates.
- Use pyDraw's public top-left coordinates internally.
- Remove Turtle dependencies from color handling, exceptions, and helpers.
- Delete the vendored Turtle module if nothing public depends on it.
- Regenerate the compiled single-file distribution.

The compatibility suite must demonstrate that removing the hidden coordinate
translations did not change visible native behavior.

### Raw Tk cutover result

Completed on `render-abstract`:

- The native backend now creates a raw Tk root and Canvas without importing
  Turtle.
- Render nodes, Canvas items, and pointer events all use pyDraw's public
  top-left coordinate system directly.
- Core rendering and color handling contain no Tk or Turtle fallback paths.
- The transitional native `Screen` aliases and legacy coordinate conversion
  helpers were removed; Tk-specific tests reach the Tk backend explicitly.
- The unused vendored Turtle module was removed and the single-file compiler
  was updated to include the runtime, event, render, and Tk backend modules.

All 18 suites passed with 270 tests. The compatibility coverage includes 15
render/coordinate tests and 9 input/event-loop tests. The native event benchmark
remained effectively unchanged: 0.118 ms median and 0.176 ms p95 with explicit
`update()`, and 0.065 ms median and 0.096 ms p95 under `screen.loop()`.

## 8. Handle Browser Scheduling Deliberately

Native pyDraw can preserve the existing `update()` and `loop()` behavior. A
browser cannot safely run a blocking infinite Python loop on the DOM thread,
because doing so prevents painting and input dispatch. The spike measured this
directly: an event scheduled during a finite blocking loop was not dispatched
until the loop ended. Adding a cooperative async yield allowed the event to run
during the loop.

The host contract should represent the required semantic operations—processing
pending work, scheduling frames, and running until closed—without pretending
that every platform implements them with the same blocking mechanism.

The worker follow-up proves a compatibility strategy that does not require
traditional user applications to become async:

1. Run user Python in a PyScript worker.
2. Keep native DOM listeners and the browser host on the main thread.
3. Normalize and queue input events in that main-thread host.
4. Have browser `Screen.update()` drain the queue and invoke pyDraw callbacks
   before presenting the next frame.

In the probe, the DOM remained responsive, Python received the exact pointer
coordinates while a tight worker loop was still running, and the loop continued
after the callback. This makes worker-hosted execution plus explicit event
polling the current target architecture.

The first optimized follow-up experimented with putting rendering in the user
Python worker and removes synchronous worker/main-thread operations from the
hot path:

- Transfer the visible HTML Canvas into the Python worker as an
  `OffscreenCanvas`.
- Give the main-thread host and worker a `SharedArrayBuffer` event ring.
- Have native DOM listeners normalize input and write directly into that ring.
- Have `Screen.update()` drain the ring from worker-local memory before drawing
  to the worker-owned Canvas.
- Treat `Screen.update()` as a non-reentrant application-loop operation. Event
  callbacks mutate state and return to the outer update rather than invoking it
  recursively.

Three independent runs delivered 1,000 events in roughly 32 ms each while also
rendering over 1,100 Canvas frames. Median and p95 latency matched or beat the
native characterization benchmark. Browser p99 was 0.145-0.165 ms and the worst
observed event was 2.325 ms, still well under a frame.

The production implementation requires cross-origin isolation headers or
PyScript's service-worker fallback for shared memory. The worker-transfer
bootstrap currently uses PyScript's exposed XWorker and must be encapsulated and
version-pinned until a documented high-level transferable-object API exists.
Cooperative async execution can remain an additional browser API, but it is not
required to preserve the classic `while ...: screen.update()` pattern. The
separate renderer-worker topology below supersedes same-worker Canvas ownership
as the production target because it better isolates the private renderer.

### Private Renderer Isolation

Transferring the Canvas into the user Python worker provides the lowest
possible latency but makes private runtime objects more accessible to arbitrary
user Python. The isolation follow-up therefore moves Canvas ownership into a
distinct private renderer worker:

1. Main-thread DOM listeners write normalized input into a shared ring.
2. The user Python worker drains input and publishes neutral frames into
   double-buffered shared memory.
3. The private renderer worker owns the Canvas and consumes those frames.
4. `Screen.update()` waits for an atomic renderer acknowledgement before
   returning, preserving synchronous native semantics.

The unchanged user fixture selected no backend, imported no browser module, and
successfully delivered 100 events and 103 acknowledged frames. The renderer
verified the exact expected output pixel. Publish-to-draw-to-acknowledgement
latency measured 0.455 ms median, 0.610 ms p95, 0.850 ms p99, and 2.145 ms
maximum. This separate renderer worker is the preferred production topology:
the small performance cost buys isolation of proprietary renderer execution
from introspectable user Python.

### User Debug Information

The website bootstrap, not the renderer, owns user-module execution. It runs the
uploaded file inside the user Python worker and reports structured exceptions
to the page. Prototype tests preserved exact user filenames, line numbers,
function names, source lines, exception types, messages, and formatted
tracebacks for both a nested runtime `ValueError` and a compile-time
`SyntaxError` with its caret offset.

Production diagnostics must maintain separate channels:

- User-code failures receive rich Python information suitable for editor links.
- Public core failures retain actionable library frames where appropriate.
- Private host and renderer failures return stable platform error codes without
  exposing private stacks.

The runner should also capture `stdout`/`stderr`, uncaught callback and asyncio
task exceptions, exception chains and groups, and source-version identifiers.

## 9. Keep the Browser Implementation Separate

The open pyDraw package contains:

- Core scene and geometry code
- Backend protocols
- The built-in Tk backend
- The recording backend
- Backend conformance tests

The separate browser package contains:

- PyScript and Pyodide host integration
- DOM/Canvas rendering
- Browser event translation
- Browser scheduling
- Browser asset loading

Core never imports the browser package. The website bootstrap installs its
runtime as the process default before executing the unchanged user module.

## First Production Step

After the browser viability spike passes, add the pure runtime registry,
`ScreenConfig`, the minimal `Runtime` and `ScreenBackend` protocols, normalized
input-event data, and a recording backend without first changing current Tk
rendering. Then migrate one rendering vertical slice at a time and add render
node types only as each slice requires them. This avoids designing a large
backend API in advance of its actual consumers.
