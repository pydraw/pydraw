# A Pythonic Representation of a Chess Board

from enum import Enum
from piece import PieceType, Piece, ChessColor


class Square(Enum):
    A8 = 0
    B8 = 1
    C8 = 2
    D8 = 3
    E8 = 4
    F8 = 5
    G8 = 6
    H8 = 7
    A7 = 8
    B7 = 9
    C7 = 10
    D7 = 11
    E7 = 12
    F7 = 13
    G7 = 14
    H7 = 15
    A6 = 16
    B6 = 17
    C6 = 18
    D6 = 19
    E6 = 20
    F6 = 21
    G6 = 22
    H6 = 23
    A5 = 24
    B5 = 25
    C5 = 26
    D5 = 27
    E5 = 28
    F5 = 29
    G5 = 30
    H5 = 31
    A4 = 32
    B4 = 33
    C4 = 34
    D4 = 35
    E4 = 36
    F4 = 37
    G4 = 38
    H4 = 39
    A3 = 40
    B3 = 41
    C3 = 42
    D3 = 43
    E3 = 44
    F3 = 45
    G3 = 46
    H3 = 47
    A2 = 48
    B2 = 49
    C2 = 50
    D2 = 51
    E2 = 52
    F2 = 53
    G2 = 54
    H2 = 55
    A1 = 56
    B1 = 57
    C1 = 58
    D1 = 59
    E1 = 60
    F1 = 61
    G1 = 62
    H1 = 63

    def is_black(self):
        dark = 0xAA55AA55AA55AA55
        return (dark >> self.value) & 1

    def is_white(self):
        return self.is_black()

    def color(self):
        return ChessColor.WHITE if self.is_white() else ChessColor.BLACK

    def __str__(self):
        return f'({self.name}: {self.color()})'


class Board:
    class FenParser:
        def __init__(self, fen_str):
            self.fen_str = fen_str

            self.to_move = ChessColor.WHITE
            self.white_castle_rights = ''
            self.black_castle_rights = ''

            self.enpassant = None

        def parse(self) -> list:
            data = self.fen_str.split(" ")

            self.to_move = ChessColor.BLACK if data[1] != 'w' else ChessColor.WHITE

            # Castling
            for character in data[2]:
                character = str(character)
                if not character.isalpha():
                    break

                if character.isupper():
                    self.white_castle_rights += character
                elif character.islower():
                    self.black_castle_rights += character

            # En Passant
            if str(data[3]) != '-':
                self.enpassant = Square(str(data[3]).upper())

            ranks = data[0].split("/")
            pieces_on_all_ranks = [self.parse_rank(rank) for rank in ranks]
            return self.convert(pieces_on_all_ranks)

        def convert(self, all_pieces):
            all_pieces = [piece for rank in all_pieces for piece in rank]
            pieces = []
            for piece in all_pieces:
                piece_type = PieceType.NONE
                if piece.lower() == 'k':
                    piece_type = PieceType.KING
                elif piece.lower() == 'q':
                    piece_type = PieceType.QUEEN
                elif piece.lower() == 'r':
                    piece_type = PieceType.ROOK
                elif piece.lower() == 'b':
                    piece_type = PieceType.BISHOP
                elif piece.lower() == 'n':
                    piece_type = PieceType.KNIGHT
                elif piece.lower() == 'p':
                    piece_type = PieceType.PAWN

                piece_color = ChessColor.WHITE if piece.isupper() else ChessColor.BLACK
                pieces.append(Piece(piece_type, piece_color))

            return pieces

        def parse_rank(self, rank):
            import re
            rank_re = re.compile("(\d|[kqbnrpKQBNRP])")
            piece_tokens = rank_re.findall(rank)
            pieces = self.flatten(map(self.expand_or_noop, piece_tokens))
            return pieces

        def flatten(self, lst):
            from itertools import chain
            return list(chain(*lst))

        def expand_or_noop(self, piece_str):
            import re
            piece_re = re.compile("([kqbnrpKQBNRP])")
            retval = ""
            if piece_re.match(piece_str):
                retval = piece_str
            else:
                retval = self.expand(piece_str)
            return retval

        def expand(self, num_str):
            return int(num_str) * " "

    def __init__(self, fen='rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1'):
        squarelist = [square for square in Square]
        if fen is not None:
            parser = self.FenParser(fen)
            piecelist = parser.parse()

            self.white_castle_rights = parser.white_castle_rights
            self.black_castle_rights = parser.black_castle_rights

            self.en_passant = parser.enpassant
            self.next = parser.to_move
        else:
            piecelist = [Piece.NONE] * 64
            self.white_castle_rights = 'KQ'
            self.black_castle_rights = 'kq'
            self.en_passant = None
            self.next = ChessColor.WHITE

        self.squares = {}
        for i in range(len(squarelist)):
            self.squares[squarelist[i]] = piecelist[i]

        self.moves = []

    def make_move(self, move):
        from move import Move, MoveFlag  # Inject import so we can use from this base file

        move_from = move.from_square
        move_to = move.to_square

        # move_piece = self.square(move_from)

        piece = self.square(move_from)

        # Handles captures
        captures = None
        if not self.square(move.to_square).none():
            # print('capture')
            captures = self.square(move.to_square)

        # Handle Promotions
        if move.flag.promotion():
            promote_type = PieceType.NONE
            if move.flag == MoveFlag.PROMOTE_QUEEN:
                promote_type = PieceType.QUEEN
            elif move.flag == MoveFlag.PROMOTE_ROOK:
                promote_type = PieceType.ROOK
            elif move.flag == MoveFlag.PROMOTE_BISHOP:
                promote_type = PieceType.BISHOP
            elif move.flag == MoveFlag.PROMOTE_KNIGHT:
                promote_type = PieceType.KNIGHT

            piece_color = piece.color
            piece = Piece(promote_type, piece_color)

        castled = False
        # print('Piece:', piece.piece_type.name, move.flag)
        # Handle other MoveFlags
        if move.flag == MoveFlag.EN_PASSANT:
            pawn_captured_square = Square(move_to.value + (8 if self.next == ChessColor.WHITE else -8))
            self.squares[pawn_captured_square] = Piece.NONE
        elif move.flag == MoveFlag.CASTLING:
            # print('Castling Flag detected!')
            kingside = move_to == Square.G1 or move_to == Square.G8
            castle_rook_current = Square(move_to.value + (1 if kingside else -2))
            castle_rook_new = Square(move_to.value + (-1 if kingside else 1))

            rook = self.square(castle_rook_current)

            if kingside:
                if self.next == ChessColor.WHITE:
                    self.white_castle_rights.replace('K', '')
                else:
                    self.black_castle_rights.replace('k', '')
            else:
                if self.next == ChessColor.WHITE:
                    self.white_castle_rights.replace('Q', '')
                else:
                    self.black_castle_rights.replace('q', '')

            castled = True
            # print('Castled:', castled)
            self.squares[castle_rook_current] = Piece.NONE
            self.squares[castle_rook_new] = rook

        self.squares[move.from_square] = Piece.NONE
        self.squares[move.to_square] = piece

        if move.flag == MoveFlag.PAWN_TWO_FORWARD:
            self.en_passant = Square(move.from_square.value + (-8 if self.next == ChessColor.WHITE else +8))

        # Handle castling rights
        if move.flag != MoveFlag.CASTLING:
            if move_to == Square.H1 or move_from == Square.H1:
                self.white_castle_rights.replace('K', '')
            elif move_to == Square.A1 or move_from == Square.A1:
                self.white_castle_rights.replace('Q', '')

            if move_to == Square.H8 or move_from == Square.H8:
                self.black_castle_rights.replace('k', '')
            elif move_to == Square.A8 or move_from == Square.A8:
                self.black_castle_rights.replace('q', '')

        self.moves.append(move)
        self.next = ChessColor.BLACK if self.next == ChessColor.WHITE else ChessColor.WHITE

    def unmake_move(self, move, captures=None):
        piece = self.square(move.to_square)
        if captures is not None:
            self.squares.update(move.to_square, captures)

        self.squares.update(move.from_square, piece)

    def kingside_castle(self):
        return 'K' in self.white_castle_rights if self.next == ChessColor.WHITE else 'k' in self.black_castle_rights

    def queenside_castle(self):
        return 'Q' in self.white_castle_rights if self.next == ChessColor.WHITE else 'q' in self.black_castle_rights

    def last(self) -> ChessColor:
        return ChessColor.WHITE if self.next == ChessColor.BLACK else ChessColor.BLACK

    def pawn_attacks(self, color: ChessColor = None):
        from move import MoveGenerator
        if color is None:
            color = ChessColor.WHITE if self.next == ChessColor.BLACK else ChessColor.BLACK

        pawn_captures = MoveGenerator.pawn_captures_white \
            if color == ChessColor.BLACK \
            else MoveGenerator.pawn_captures_black

        pawn_attacks = []
        for square in self.squares:
            piece = self.square(square)
            if not piece.none() and piece.piece_type == PieceType.PAWN and piece.color == color:
                for attack_square in pawn_captures[square.value]:
                    pawn_attacks.append(Square(attack_square))

        return pawn_attacks

    def square(self, square: Square) -> Piece:
        """
        Get the piece on a square
        :param square: the Square to check
        :return: the Piece on a Square, PieceType will be None if the piece does not exist
        """

        return self.squares[square]

    def clone(self):
        board = Board(fen=None)
        board.squares = self.squares.copy()

        board.white_castle_rights = self.white_castle_rights
        board.black_castle_rights = self.black_castle_rights

        board.en_passant = self.en_passant
        board.next = ChessColor(self.next.value)

        return board


class Evaluation:

    # Piece Values
    # In centipawns:
    values = {
        PieceType.PAWN: 100,
        PieceType.KNIGHT: 320,  # We want to avoid exchanging 3 pawns for 1 piece
        PieceType.BISHOP: 330,  # We want to avoid exchanging 3 pawns for 1 piece or a knight for a bishop
        PieceType.ROOK: 500,  # We also want to avoid exchanging 2 pieces for a rook + a pawn, so rook stays at 500
        PieceType.QUEEN: 900,
        PieceType.KING: 20000
    }

    # | Piece Square Tables | - We use these to determine positional evaluation (where the pieces ARE)

    # [Pawn] - We encourage pawns towards the center and pawns on A-C & F-H to shelter the castled King
    # Note that we will reverse this table for each side. (This is blacks table by default, since A8 = index 0)
    pawn_squares = [0,  0,  0,  0,  0,  0,  0,  0,
                    50, 50, 50, 50, 50, 50, 50, 50,
                    10, 10, 20, 30, 30, 20, 10, 10,
                     5,  5, 10, 25, 25, 10,  5,  5,
                     0,  0,  0, 20, 20,  0,  0,  0,
                     5, -5, -10,  0,  0, -10, -5,  5,
                     5, 10, 10, -20, -20, 10, 10,  5,
                     0,  0,  0,  0,  0,  0,  0,  0]

    # [Knight] - Encourage the Knight to go to the center and stay away from edges and corners
    knight_squares = [-50, -40, -30, -30, -30, -30, -40, -50,
                        -40, -20,  0,  0,  0,  0, -20, -40,
                        -30,  0, 10, 15, 15, 10,  0, -30,
                        -30,  5, 15, 20, 20, 15,  5, -30,
                        -30,  0, 15, 20, 20, 15,  0, -30,
                        -30,  5, 10, 15, 15, 10,  5, -30,
                        -40, -20,  0,  5,  5,  0, -20, -40,
                        -50, -40, -30, -30, -30, -30, -40, -50]

    # [Bishop] - Encourage Bishops to stay away from the edges and hold the center while staying closeby
    bishop_squares = [-20, -10, -10, -10, -10, -10, -10, -20,
                        -10,  0,  0,  0,  0,  0,  0, -10,
                        -10,  0,  5, 10, 10,  5,  0, -10,
                        -10,  5,  5, 10, 10,  5,  5, -10,
                        -10,  0, 10, 10, 10, 10,  0, -10,
                        -10, 10, 10, 10, 10, 10, 10, -10,
                        -10,  5,  0,  0,  0,  0,  5, -10,
                        -20, -10, -10, -10, -10, -10, -10, -20]

    # [Rook] - Encourage rooks to go to the 7th rank, but to stay away from the edges where it is less useful,
    # (also prefers castling)
    rook_squares = [0,  0,  0,  0,  0,  0,  0,  0,
                      5, 10, 10, 10, 10, 10, 10,  5,
                     -5,  0,  0,  0,  0,  0,  0, -5,
                     -5,  0,  0,  0,  0,  0,  0, -5,
                     -5,  0,  0,  0,  0,  0,  0, -5,
                     -5,  0,  0,  0,  0,  0,  0, -5,
                     -5,  0,  0,  0,  0,  0,  0, -5,
                      0,  0,  0,  5,  5,  0,  0,  0]

    # [Queen] - Designed to keep the Queen away from edges and encourage her to protect the center
    queen_squares = [-20, -10, -10, -5, -5, -10, -10, -20,
                        -10,  0,  0,  0,  0,  0,  0, -10,
                        -10,  0,  5,  5,  5,  5,  0, -10,
                         -5,  0,  5,  5,  5,  5,  0, -5,
                          0,  0,  5,  5,  5,  5,  0, -5,
                        -10,  5,  5,  5,  5,  5,  0, -10,
                        -10,  0,  5,  0,  0,  0,  0, -10,
                        -20, -10, -10, -5, -5, -10, -10, -20]

    # [King] - We have two different maps for the King, one for midgame and one for endgame
    #   [Midgame] - We will encourage castling and staying safe on the Back Rank with pawn protection
    #   [Endgame] - Encourage centering the King around any existing pieces
    king_squares_midgame = [-30, -40, -40, -50, -50, -40, -40, -30,
                            -30, -40, -40, -50, -50, -40, -40, -30,
                            -30, -40, -40, -50, -50, -40, -40, -30,
                            -30, -40, -40, -50, -50, -40, -40, -30,
                            -20, -30, -30, -40, -40, -30, -30, -20,
                            -10, -20, -20, -20, -20, -20, -20, -10,
                             20, 20,  0,  0,  0,  0, 20, 20,
                             20, 30, 10,  0,  0, 10, 30, 20]

    king_squares_endgame = [-50, -40, -30, -20, -20, -30, -40, -50,
                            -30, -20, -10,  0,  0, -10, -20, -30,
                            -30, -10, 20, 30, 30, 20, -10, -30,
                            -30, -10, 30, 40, 40, 30, -10, -30,
                            -30, -10, 30, 40, 40, 30, -10, -30,
                            -30, -10, 20, 30, 30, 20, -10, -30,
                            -30, -30,  0,  0,  0,  0, -30, -30,
                            -50, -30, -30, -30, -30, -30, -30, -50]

    piece_squares = {
        PieceType.PAWN: pawn_squares,
        PieceType.KNIGHT: knight_squares,
        PieceType.BISHOP: bishop_squares,
        PieceType.ROOK: rook_squares,
        PieceType.QUEEN: queen_squares,
        PieceType.KING: [
            king_squares_midgame,
            king_squares_endgame
        ]
    }

    def __init__(self, board: Board):
        material = 0  # Negative if in black's favor, positive if in white's favor
        position = 0  # Same as above ^

        endgame = False
        queens = 0
        for square in board.squares:
            piece = board.square(square)
            if piece.piece_type == PieceType.QUEEN:
                queens += 1

        endgame = queens == 0

        # First we will check material
        for square in board.squares:
            piece = board.square(square)
            if not piece.none():
                sign = +1 if piece.color == ChessColor.WHITE else -1
                material += (sign * self.values[piece.piece_type])

                square_value = self.piece_squares[piece.piece_type]
                if piece.piece_type == PieceType.KING:
                    square_value = square_value[0] if not endgame else square_value[1]

                position += (sign * self.read(square_value, square, piece.color))

        self.position = position
        self.material = material

    def get(self, color=ChessColor.WHITE) -> float:
        if color == ChessColor.WHITE:
            return self.material + self.position
        else:
            return -self.material - self.position

    @staticmethod
    def read(table: list, square: Square, color: ChessColor = ChessColor.WHITE):
        if color == ChessColor.WHITE:
            rank = int(square.value / 8)
            file = int(square.value - rank * 8)

            rank = 7 - rank  # Reverse the rank
            square = Square(rank * 8 + file)

        return table[square.value]
