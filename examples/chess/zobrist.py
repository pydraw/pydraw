from board import Board, Square
from piece import ChessColor, Piece, PieceType
from move import Move, MoveGenerator
import random


#seed = 0x6E6F6168697362616461746368657373


class Zobrist:
    hashtable = [[]]

    def __init__(self):

        #random.seed(seed)

        self.hash = 0

        for square in range(64):
            for piece_type in PieceType:
                for color in ChessColor:

                    value = random.random()
                    self.hashtable[square][Piece(piece_type, color)] = value

    def hash(self, board: Board):
        for square in Square:
            for piece in board.squares.values():
                if not piece.none():
                    self.hash ^= self.hashtable[square][piece]

    def unhash(self, board: Board):
        pass
