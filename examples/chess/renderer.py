from pydraw import *
from board import Board, Square, ChessColor
from piece import Piece, PieceType

from move import Move, MoveGenerator


# lightSquares:
#     normal: {r: 0.93333334, g: 0.84705883, b: 0.7529412, a: 1}
#     legal: {r: 0.8666667, g: 0.34901962, b: 0.34901962, a: 0}
#     selected: {r: 0.9245283, g: 0.7725114, b: 0.48406905, a: 0}
#     moveFromHighlight: {r: 0.8113208, g: 0.6759371, b: 0.41714135, a: 0}
#     moveToHighlight: {r: 0.8679245, g: 0.813849, b: 0.48718405, a: 0}
#   darkSquares:
#     normal: {r: 0.67058825, g: 0.47843137, b: 0.39607844, a: 1}
#     legal: {r: 0.77254903, g: 0.26666668, b: 0.30980393, a: 0}
#     selected: {r: 0.7830189, g: 0.6196811, b: 0.31394625, a: 0}
#     moveFromHighlight: {r: 0.7735849, g: 0.6194568, b: 0.36854753, a: 0}
#     moveToHighlight: {r: 0.7735849, g: 0.6780388, b: 0.37584552, a: 0}

WHITE_COLOR = Color(238, 216, 192)
BLACK_COLOR = Color(171, 123, 101)

WHITE_LEGAL_COLOR = Color(221, 89, 89)
BLACK_LEGAL_COLOR = Color(197, 68, 79)

WHITE_SELECTED_COLOR = Color(235, 196, 123)
BLACK_SELECTED_COLOR = Color(199, 158, 80)

WHITE_MOVE_FROM_COLOR = Color(206, 172, 106)
BLACK_MOVE_FROM_COLOR = Color(197, 157, 93)

WHITE_MOVE_TO_COLOR = Color(221, 207, 124)
BLACK_MOVE_TO_COLOR = Color(197, 172, 95)

COLORS = {ChessColor.WHITE: WHITE_COLOR, ChessColor.BLACK: BLACK_COLOR}
LEGAL_COLORS = {ChessColor.WHITE: WHITE_LEGAL_COLOR, ChessColor.BLACK: BLACK_LEGAL_COLOR}
SELECTED_COLORS = {ChessColor.WHITE: WHITE_SELECTED_COLOR, ChessColor.BLACK: BLACK_SELECTED_COLOR}
FROM_COLORS = {ChessColor.WHITE: WHITE_MOVE_FROM_COLOR, ChessColor.BLACK: BLACK_MOVE_FROM_COLOR}
TO_COLORS = {ChessColor.WHITE: WHITE_MOVE_TO_COLOR, ChessColor.BLACK: BLACK_MOVE_TO_COLOR}


class Renderer:
    def __init__(self, screen: Screen, x: float, y: float, size: float):
        self.screen = screen
        self.x = x
        self.y = y
        self.size = size

        self.squares = {}
        self.pieces = {}

        self.box_size = size / 8
        self.generator = MoveGenerator()

    def render_piece(self, piece: Piece, x: float, y: float):
        name = f'./textures/{str(piece.piece_type).lower()}_{str(piece.color).lower()}.png'
        image = Image(self.screen, name, x, y, self.box_size, self.box_size)
        return image

    def get_piece(self, location: Location) -> Renderable:
        """
        Get a piece sprite at a location
        :param location: A location to check
        :return:
        """

        for piece_sprite in self.pieces.values():
            if piece_sprite.contains(location):
                return piece_sprite

        return None

    def get_piece_by_square(self, square: Square) -> Renderable:
        """
        Gets the piece sprite on a square
        :param square: the Square to check
        :return: Renderable
        """

        square_box_center = self.squares.get(square).center()
        return self.get_piece(square_box_center)

    def get_square_sprite(self, location: Location) -> Renderable:
        for box in self.squares.values():
            if box.contains(location):
                return box

        return None

    def get_square(self, location: Location) -> Square:
        """
        Get a square sprite at a location
        :param location:
        :return:
        """

        for square in self.squares:
            if self.squares[square].contains(location):
                return square

        return None

    def reset_squares(self) -> None:
        for square in self.squares:
            self.squares[square].color(COLORS[square.color()])

    def render_moves(self, board: Board, square: Square) -> None:
        """
        Render the available move squares for a piece
        :param square: the Piece's Square to check (There can be multiple types of one piece)
        :return: None
        """

        moves = self.generator.generate_moves(board)
        squares = []
        for move in moves:
            if move.from_square == square:
                if self.generator.is_check_self(board, move):
                    continue

                squares.append(move.to_square)

        self.squares[square].color(FROM_COLORS[square.color()])
        for square in squares:
            box = self.squares[square]
            box.color(TO_COLORS[square.color()])

    def render_squares(self, board: Board) -> None:
        """
        Draws the squares on the board (only must be called once.
        :return: None
        """

        x = self.x
        y = self.y

        count = 0
        for square in board.squares:
            square_color = COLORS[square.color()]
            box = Rectangle(self.screen, x, y, self.box_size, self.box_size, square_color)
            self.squares[square] = box
            box.back()

            x += self.box_size
            count += 1
            if count % 8 == 0:
                y += self.box_size
                x = self.x

    def render_pieces(self, board: Board) -> None:
        x = self.x
        y = self.y

        temp_pieces = {}
        count = 0

        old_pieces = self.pieces

        for square in Square:
            piece = board.square(square)
            if piece.none():
                piece = self.get_piece_by_square(square)

                if piece is not None and piece in self.screen.objects():
                    # piece.remove()
                    pass

        for square in board.squares:
            piece = board.squares[square]

            if piece.piece_type is not PieceType.NONE:
                found_piece = None
                for cached_piece in self.pieces:
                    if cached_piece.piece_type == piece.piece_type and cached_piece.color == piece.color:
                        piece_sprite = self.pieces[cached_piece]
                        piece_sprite.moveto(x, y)
                        piece_sprite.front()

                        found_piece = cached_piece
                        temp_pieces[piece] = piece_sprite
                        break

                if found_piece is None:
                    new_piece = self.render_piece(piece, x, y)
                    temp_pieces[piece] = new_piece
                else:
                    self.pieces.pop(found_piece)

            x += self.box_size
            count += 1
            if count % 8 == 0:
                y += self.box_size
                x = self.x

        self.pieces = temp_pieces

        # Catch any weird issues where we do not remove when we should have (due to multithreading I believe)
        for piece in old_pieces.values():
            if piece not in self.squares.values() and piece not in self.pieces.values():
                piece.remove()

    def render(self, board: Board, draw_squares=False) -> None:
        """
        Renders a passed board onto the screen given the original size and position parameters
        :param board: the Board to render
        :return: None
        """

        if draw_squares:
            self.render_squares(board)

        x = self.x
        y = self.y

        # [piece.remove() for piece in self.pieces.values()]
        # self.pieces.clear()

        if not draw_squares:
            self.render_pieces(board)
            return

        count = 0
        for square in board.squares:
            piece = board.squares[square]
            if piece.piece_type is not PieceType.NONE:
                piece_sprite = self.render_piece(piece, x, y)
                piece_sprite.front()
                self.pieces[piece] = piece_sprite

            x += self.box_size
            count += 1
            if count % 8 == 0:
                y += self.box_size
                x = self.x
