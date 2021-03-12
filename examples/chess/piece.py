import enum


class ChessColor(enum.Enum):
    WHITE = 0
    BLACK = 1

    def __str__(self):
        return self.name


class PieceType(enum.Enum):
    NONE = 0
    PAWN = 1
    KNIGHT = 2
    BISHOP = 3
    ROOK = 4
    QUEEN = 5
    KING = 6

    def __str__(self):
        return self.name


class Piece:
    NONE = None

    def __init__(self, piece_type: PieceType, color: ChessColor):
        self.piece_type = piece_type
        self.color = color

    def sliding(self) -> bool:
        return self.piece_type == PieceType.QUEEN or self.piece_type == PieceType.ROOK\
               or self.piece_type == PieceType.BISHOP

    def none(self) -> bool:
        return self.piece_type == PieceType.NONE

    def __str__(self):
        return f'{self.color} {self.piece_type}'

    # def __eq__(self, other):
    #     return self.piece_type == other.piece_type and self.color == other.color


Piece.NONE = Piece(PieceType.NONE, None)
