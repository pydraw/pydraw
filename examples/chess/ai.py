from board import Board, Evaluation
from move import MoveGenerator, Move, MoveFlag
import random


class AIPlayer:
    def __init__(self):
        self.difficulty = 0

    def make_move(self, board):
        self.difficulty += 0
        generator = MoveGenerator()
        moves = generator.generate_moves(board)

        best_evaluation = 0  # We want this to be as low as possible
        move = random.choice(moves)
        for m in moves:
            fake_board: Board = board.clone()
            fake_board.make_move(m)
            evaluation = Evaluation(fake_board)
            if evaluation.material < best_evaluation:
                best_evaluation = evaluation.material
                move = m

            if m.flag == MoveFlag.CASTLING:
                move = m
                break

        if len(moves) == 0:
            print('Stalemate!')
            return
        board.make_move(move)
