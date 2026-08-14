"""Built-in Tk backend."""

from pydraw.runtime import BackendTerminated, Runtime, ScreenBackend
from pydraw.events import InputEvent
from pydraw.render import EllipseNode, ImageNode, PolygonNode, PolylineNode, TextNode


class TkBackend(ScreenBackend):

    def __init__(self, config):
        import tkinter as tk

        self.tk = tk
        self.root = tk.Tk()
        self.canvas = tk.Canvas(
            self.root,
            width=config.width,
            height=config.height,
            borderwidth=0,
            highlightthickness=0,
        )
        self.canvas.pack(fill='both', expand=True)
        self.width = config.width
        self.height = config.height
        self.items = {}
        self.fonts = {}
        self.image_refs = {}
        self.image_keys = {}
        self.source_images = {}
        self.events = []
        self.running = False
        self.closed = False
        self._canvas_size = (config.width, config.height)
        self.background_ref = None
        self.background_item = None

        self.root.resizable(False, False)
        self.root.title(config.title)
        self.root.update_idletasks()
        self.root.protocol('WM_DELETE_WINDOW', self._window_closed)
        self.canvas.bind('<Configure>', self._configure, add='+')

    def _window_closed(self):
        self.closed = True
        self.root.destroy()

    def _configure(self, event):
        self._canvas_size = None
        self.canvas_size()

    def poll_events(self):
        if self.closed:
            raise BackendTerminated()
        try:
            if not self.running:
                self.canvas.update()
        except self.tk.TclError as error:
            raise BackendTerminated() from error
        events = tuple(self.events)
        self.events.clear()
        return events

    def listen(self):
        self.events.clear()
        self.canvas.focus_force()
        self.canvas.bind('<Key>', self._queue_keydown)
        self.canvas.bind('<KeyRelease>', self._queue_keyup)
        self.canvas.bind('<Motion>', self._queue_mousemove)
        for button in (1, 2, 3):
            self.canvas.bind(
                '<Button-{}>'.format(button),
                lambda event, button=button: self._queue_pointer(
                    'mousedown', event, button
                ),
            )
            self.canvas.bind(
                '<Button{}-ButtonRelease>'.format(button),
                lambda event, button=button: self._queue_pointer(
                    'mouseup', event, button
                ),
            )
            self.canvas.bind(
                '<B{}-Motion>'.format(button),
                lambda event, button=button: self._queue_pointer(
                    'mousedrag', event, button
                ),
            )

    def _position(self, event):
        return (
            self.canvas.canvasx(event.x),
            self.canvas.canvasy(event.y),
        )

    def _queue_pointer(self, kind, event, button=None):
        self.events.append(InputEvent(kind, self._position(event), button, None))

    def _queue_mousemove(self, event):
        self._queue_pointer('mousemove', event)

    def _key(self, event):
        key = str(event.char)
        if not key or key.strip() == '' or not key.isprintable():
            key = event.keysym
        return key.lower()

    def _queue_keydown(self, event):
        self.events.append(InputEvent('keydown', None, None, self._key(event)))

    def _queue_keyup(self, event):
        self.events.append(InputEvent('keyup', None, None, self._key(event)))

    def present(self, frame):
        if self.closed:
            raise BackendTerminated()
        try:
            return self._present(frame)
        except self.tk.TclError as error:
            raise BackendTerminated() from error

    def _present(self, frame):
        if frame is None:
            return None

        for render_id in frame.removals:
            item = self.items.pop(render_id, None)
            if item is not None:
                self.canvas.delete(item)
            self.image_refs.pop(render_id, None)
            self.image_keys.pop(render_id, None)

        for node in frame.upserts:
            if isinstance(node, PolylineNode):
                self._present_polyline(node)
            elif isinstance(node, (PolygonNode, EllipseNode)):
                self._present_polygon(node)
            elif isinstance(node, TextNode):
                self._present_text(node)
            elif isinstance(node, ImageNode):
                self._present_image(node)
            else:
                raise TypeError('TkBackend received an unsupported render node')

        for render_id in frame.backs:
            item = self.items.get(render_id)
            if item is not None:
                self.canvas.tag_lower(item)
        for render_id in frame.fronts:
            item = self.items.get(render_id)
            if item is not None:
                self.canvas.tag_raise(item)

        if not frame.empty():
            self.canvas.update_idletasks()
        return None

    def _present_polyline(self, node):
        coordinates = []
        points = node.points
        if len(points) == 1:
            points = points + points
        for x, y in points:
            coordinates.extend((x, y))

        options = {
            'fill': self._color(node.color),
            'width': node.width,
            'dash': node.dash,
            'state': 'normal' if node.visible else 'hidden',
            'capstyle': node.cap,
        }
        item = self.items.get(node.id)
        if item is None:
            item = self.canvas.create_line(*coordinates, **options)
            self.items[node.id] = item
        else:
            self.canvas.coords(item, *coordinates)
            self.canvas.itemconfigure(item, **options)

        if node.top:
            self.canvas.tag_raise(item)

    def _present_polygon(self, node):
        coordinates = []
        for x, y in node.points:
            coordinates.extend((x, y))

        options = {
            'fill': '' if node.fill is None else self._color(node.fill),
            'outline': '' if node.outline is None else self._color(node.outline),
            'width': node.width,
            'state': 'normal' if node.visible else 'hidden',
            'joinstyle': self.tk.MITER,
        }
        item = self.items.get(node.id)
        if item is None:
            item = self.canvas.create_polygon(*coordinates, **options)
            self.items[node.id] = item
        else:
            self.canvas.coords(item, *coordinates)
            self.canvas.itemconfigure(item, **options)

    def _present_text(self, node):
        x, y = node.position
        decorations = []
        if node.bold:
            decorations.append('bold')
        if node.italic:
            decorations.append('italic')
        if node.underline:
            decorations.append('underline')
        if node.strikethrough:
            decorations.append('overstrike')

        options = {
            'text': node.text,
            'anchor': 'nw',
            'justify': node.align,
            'fill': self._color(node.color),
            'font': (node.font, -node.size, ' '.join(decorations)),
            'state': 'normal' if node.visible else 'hidden',
            'angle': -node.rotation,
        }
        coordinates = (x, y)
        item = self.items.get(node.id)
        if item is None:
            item = self.canvas.create_text(*coordinates, **options)
            self.items[node.id] = item
        else:
            self.canvas.coords(item, *coordinates)
            self.canvas.itemconfigure(item, **options)

    def _present_image(self, node):
        key = (
            node.source,
            node.width,
            node.height,
            node.rotation,
            node.tint,
            node.tint_alpha,
            node.border,
            node.smooth,
            node.flip_x,
            node.flip_y,
            node.frame,
        )
        if self.image_keys.get(node.id) != key:
            self.image_refs[node.id] = self._build_image(node)
            self.image_keys[node.id] = key

        x, y = node.position
        coordinates = (
            x + node.width / 2,
            y + node.height / 2,
        )
        options = {
            'image': self.image_refs[node.id],
            'state': 'normal' if node.visible else 'hidden',
        }
        item = self.items.get(node.id)
        if item is None:
            item = self.canvas.create_image(*coordinates, **options)
            self.items[node.id] = item
        else:
            self.canvas.coords(item, *coordinates)
            self.canvas.itemconfigure(item, **options)

    def _build_image(self, node):
        import os

        extension = os.path.splitext(node.source)[1].lower()
        intrinsic = self.measure_image(node.source)
        native = extension in ('.png', '.gif', '.ppm')
        transformed = (
            (int(node.width), int(node.height)) != intrinsic
            or node.rotation % 360 != 0
            or node.tint is not None
            or node.border is not None
            or node.flip_x
            or node.flip_y
            or node.frame >= 0
        )
        if native and not transformed:
            return self.source_images[node.source]

        try:
            from PIL import Image as PILImage, ImageOps, ImageTk
        except ImportError:
            from pydraw.errors import UnsupportedError

            raise UnsupportedError(
                'Image rendering modifications require Pillow on the Tk backend.'
            )

        with PILImage.open(node.source) as original:
            if node.frame >= 0:
                try:
                    original.seek(node.frame)
                except EOFError:
                    from pydraw.errors import PydrawError

                    raise PydrawError(
                        "Image: no frame {} exists for '{}'".format(
                            node.frame, node.source,
                        )
                    )
            image = original.convert('RGBA')

        if node.flip_x:
            image = ImageOps.flip(image)
        if node.flip_y:
            image = ImageOps.mirror(image)
        if node.tint is not None:
            alpha = image.getchannel('A')
            gray = ImageOps.grayscale(image)
            image = ImageOps.colorize(
                gray,
                (0, 0, 0, 0),
                node.tint + (node.tint_alpha,),
            )
            image.putalpha(alpha)
        if node.border is not None:
            image = ImageOps.expand(image, border=10, fill=node.border)

        target_size = (int(node.width), int(node.height))
        if image.size != target_size:
            image = image.resize(
                target_size,
                PILImage.LANCZOS if node.smooth else PILImage.NEAREST,
            )
        if node.rotation % 360 != 0:
            image = image.rotate(
                -node.rotation,
                resample=PILImage.BILINEAR if node.smooth else PILImage.NEAREST,
                expand=1,
                fillcolor=None,
            )
        return ImageTk.PhotoImage(image=image, master=self.root)

    def set_title(self, title):
        self.root.title(title)

    def set_background(self, color):
        self.canvas.configure(background=self._color(color))

    def set_background_image(self, source):
        self.background_ref = self.tk.PhotoImage(master=self.root, file=source)
        width, height = self.canvas_size()
        if self.background_item is None:
            self.background_item = self.canvas.create_image(
                width / 2,
                height / 2,
                image=self.background_ref,
            )
        else:
            self.canvas.coords(self.background_item, width / 2, height / 2)
            self.canvas.itemconfigure(
                self.background_item,
                image=self.background_ref,
            )
        self.canvas.tag_lower(self.background_item)

    @staticmethod
    def _color(color):
        if isinstance(color, tuple):
            return '#{:02x}{:02x}{:02x}'.format(*color)
        return color

    def canvas_size(self):
        if self._canvas_size is not None:
            return self._canvas_size
        try:
            width = self.canvas.winfo_width()
            height = self.canvas.winfo_height()
        except self.tk.TclError:
            return -1, -1
        if width > 1 and height > 1:
            self._canvas_size = (width, height)
            self.width = width
            self.height = height
        return width, height

    def window_size(self):
        try:
            return self.root.winfo_width(), self.root.winfo_height()
        except self.tk.TclError:
            return -1, -1

    def resize(self, width, height):
        self.canvas.configure(width=width, height=height)
        self.root.geometry('{}x{}'.format(width, height))
        self._canvas_size = None
        self.root.update_idletasks()

    def set_fullscreen(self, fullscreen):
        self.root.attributes('-fullscreen', fullscreen)
        return bool(self.root.tk.getboolean(
            self.root.attributes('-fullscreen')
        ))

    def alert(self, text, title, accept_text, cancel_text):
        from tkinter.simpledialog import SimpleDialog

        dialog = SimpleDialog(
            self.root,
            text=text,
            buttons=[accept_text, cancel_text],
            default=0,
            cancel=1,
            title=title,
        )
        return dialog.go()

    def prompt(self, text, title):
        from tkinter.simpledialog import askstring

        return askstring(title, text, parent=self.root)

    def grab(self, filename):
        try:
            from PIL import ImageGrab

            width, height = self.canvas_size()
            x1 = self.canvas.winfo_rootx()
            y1 = self.canvas.winfo_rooty()
            x2 = x1 + width
            y2 = y1 + height
            ImageGrab.grab().crop((x1, y1, x2, y2)).save(filename)
            return filename
        except Exception as error:
            from pydraw.errors import UnsupportedError

            raise UnsupportedError(
                "Screen#grab(): Pillow is required. Install it with 'pip install pillow'."
            ) from error

    def measure_text(self, text, font, size, bold, italic):
        import tkinter.font as tkfont

        decorations = []
        if bold:
            decorations.append('bold')
        if italic:
            decorations.append('italic')
        font_data = (font, -size, ' '.join(decorations))
        measured_font = self.fonts.get(font_data)
        if measured_font is None:
            measured_font = tkfont.Font(root=self.root, font=font_data)
            self.fonts[font_data] = measured_font

        width = max((measured_font.measure(line) for line in text.split('\n')),
                    default=0)
        return width, measured_font.metrics('linespace')

    def measure_image(self, source):
        import os

        extension = os.path.splitext(source)[1].lower()
        if not extension:
            from pydraw.errors import PydrawError

            raise PydrawError('Image(): path must include a file extension.')
        if not os.path.isfile(source):
            from pydraw.errors import InvalidArgumentError

            raise InvalidArgumentError(
                "Image(): path does not reference an existing file: '{}'.".format(
                    source
                )
            )
        if extension in ('.png', '.gif', '.ppm'):
            image = self.source_images.get(source)
            if image is None:
                image = self.tk.PhotoImage(master=self.root, file=source)
                self.source_images[source] = image
            return image.width(), image.height()

        try:
            from PIL import Image as PILImage
        except ImportError:
            from pydraw.errors import UnsupportedError

            raise UnsupportedError(
                'Pillow is required for formats other than PNG, GIF, and PPM.'
            )
        with PILImage.open(source) as image:
            return image.size

    def image_frames(self, source):
        try:
            from PIL import Image as PILImage
        except ImportError:
            from pydraw.errors import UnsupportedError

            raise UnsupportedError('Animated image control requires Pillow.')

        with PILImage.open(source) as image:
            frames = getattr(image, 'n_frames', 1)
        if frames <= 1:
            from pydraw.errors import PydrawError

            raise PydrawError('Image#load(): image is not animated.')
        return frames

    def item_for(self, render_id):
        return self.items.get(render_id)

    def run(self, step):
        if self.closed:
            raise BackendTerminated()
        active = [True]
        scheduled = [None]
        failure = [None]

        def tick():
            if not active[0]:
                return
            try:
                step()
            except BaseException as error:
                active[0] = False
                failure[0] = (error, error.__traceback__)
                self.root.quit()
                return
            if active[0]:
                scheduled[0] = self.root.after(1, tick)

        scheduled[0] = self.root.after(1, tick)
        self.running = True
        try:
            self.root.mainloop()
        except self.tk.TclError as error:
            raise BackendTerminated() from error
        finally:
            self.running = False
            active[0] = False
            if scheduled[0] is not None:
                try:
                    self.root.after_cancel(scheduled[0])
                except self.tk.TclError:
                    pass
        if failure[0] is not None:
            error, traceback = failure[0]
            raise error.with_traceback(traceback)

    def close(self):
        self.closed = True
        self.canvas.delete('all')
        self.root.destroy()


class TkRuntime(Runtime):

    def create_screen(self, config):
        return TkBackend(config)
