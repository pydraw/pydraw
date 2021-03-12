from pydraw import Screen
from board import Square, ChessColor, Board, Evaluation
from piece import Piece, PieceType
from move import Move, MoveGenerator, MoveResult, MoveFlag

from engine import Engine

import random
import sys

sys.setrecursionlimit(150000)

positive_infinity = 9999999
negative_infinity = -positive_infinity


class AIPlayer:

    depth = 1

    def __init__(self, screen: Screen):
        self.difficulty = 0
        self.screen = screen

        self.best_move = None
        self.best_eval = 0

        self.best_eval_iter = self.best_eval = 0
        self.best_move_iter = self.best_move

    def make_move(self, board):
        import time

        start_time = time.time()
        move: Move = self.calculate_best_move_ab(3, board, board.next)[1]

        check = MoveGenerator().is_check(board, move)
        board.make_move(move)

        finish_time = time.time()
        print('Calculation finished;',
              'Start Time:', start_time,
              'Finish Time:', finish_time,
              'Took:', finish_time - start_time)

        return check

    def make_move2(self, board):
        self.difficulty += 0
        generator = MoveGenerator()
        moves = generator.generate_moves(board)

        if len(moves) == 0:
            return 'stalemate'

        moves = self.order_moves(board, moves)

        best_evaluation = Evaluation(board).get()  # We want this to be as low as possible
        move = random.choice(moves)

        while generator.is_check_self(board, move):
            moves.remove(move)
            try:
                move = random.choice(moves)
            except IndexError:
                return 'stalemate'

        for m in moves:
            if generator.is_check_self(board, m):
                # print('Move results in check, so omitted', m)
                continue

            check = generator.is_check(board, m)
            if check:
                if check == MoveResult.CHECKMATE:
                    board.make_move(m)
                    print('Checkmated move:', m)
                    # self.screen.prompt('You have been checkmated', 'You Lost!')
                    return True
            fake_board: Board = board.clone()
            fake_board.make_move(m)
            evaluation = Evaluation(fake_board)
            if evaluation.get() < best_evaluation:
                best_evaluation = evaluation.material
                move = m

            if m.flag == MoveFlag.CASTLING:
                move = m
                break

        if len(moves) == 0:
            self.screen.prompt('You have stalemated!', 'Draw')
            print('Stalemate!')
            return
        board.make_move(move)

    def calculate_best_move(self, depth: int, board: Board, color: ChessColor, maximize=True):
        if depth == 0:
            value = Evaluation(board).get(color)
            return value, None

        best_move = None
        possible_moves = MoveGenerator().generate_moves(board)
        possible_moves.sort(key=lambda x: 0.5 - random.random())
        best_move_value = negative_infinity if maximize else positive_infinity

        node_board: Board = board.clone()

        for move in possible_moves:
            test_board: Board = node_board.clone()
            test_board.make_move(move)

            value = self.calculate_best_move(depth - 1, test_board, color, not maximize)[0]
            print(('Max:' if maximize else 'Min:'), depth, move, value, best_move, best_move_value)

            if maximize:
                if value > best_move_value:
                    best_move_value = value
                    best_move = move

            else:
                if value < best_move_value:
                    best_move_value = value
                    best_move = move

        print('Depth:', depth, '| Best Move:', best_move, '|', best_move_value)
        return best_move_value, best_move

    def calculate_best_move_ab(self, depth: int, board: Board, color: ChessColor,
                               alpha=negative_infinity, beta=positive_infinity, maximize=True):
        if depth == 0:
            value = Evaluation(board).get(color)
            return value, None

        best_move: Move = None
        possible_moves = MoveGenerator().generate_moves(board)
        possible_moves.sort(key=lambda x: 0.5 - random.random())
        # possible_moves = self.order_moves(board, color, possible_moves)

        # If we're maximizing we will want to start as low as possible, and vice versa
        best_move_value = negative_infinity if maximize else positive_infinity

        node_board: Board = board.clone()

        for move in possible_moves:
            test_board: Board = node_board.clone()
            if MoveGenerator().is_check_self(test_board, move):
                continue

            test_board.make_move(move)

            value = self.calculate_best_move_ab(depth - 1, test_board, color, alpha, beta, not maximize)[0]
            print(('Max:' if maximize else 'Min:'), depth, move, value, best_move, best_move_value)

            if maximize:
                if value > best_move_value:
                    best_move_value = value
                    best_move = move

                alpha = max(alpha, value)
            else:
                if value < best_move_value:
                    best_move_value = value
                    best_move = move

                beta = min(beta, value)

            # Check for a prunable branch!
            if beta <= alpha:
                print('Prune:', alpha, beta)
                break

        print('Depth:', depth, '| Best Move:', best_move, '|', best_move_value)
        best_move = possible_moves[0] if best_move is None else best_move
        return best_move_value, best_move

    @staticmethod
    def order_moves(board: Board, color: ChessColor, moves: list) -> list:
        move_scores = {}

        for i in range(len(moves)):
            move: Move = moves[i]
            score = 0

            piece = board.square(move.from_square)
            piece_type = piece.piece_type
            capture_type = board.square(move.to_square).piece_type

            if capture_type != PieceType.NONE:
                score = Evaluation.values[capture_type] - Evaluation.values[piece_type]

            if move.flag.promotion():
                score += Evaluation.values[move.flag.promotion_type()]

            if move.to_square in board.pawn_attacks():
                score -= Evaluation.values[piece_type] * 1.5

            move_scores[move] = score

        sorted_moves = sorted(moves, key=lambda m: move_scores[m], reverse=True)
        return sorted_moves


class EnginePlayer:
    """
    An AIPlayer that uses a real chess engine to create a more challenging opponent
    """

    def __init__(self, depth: int = 12, difficulty: int = 10):
        self.depth = depth
        self.engine = Engine('engine/engine.exe', depth=self.depth)
        self.engine.setoption('Skill Level', difficulty)

    def make_move(self, board: Board):
        """
        Make a move
        """

        moves = []
        for move in board.moves:
            moves.append(self.uci(move))
            print(move)
        self.engine.setposition(moves)

        print(moves)
        best_uci = self.engine.bestmove()['bestmove']
        print('Best Move:', best_uci)
        best_move = Move(Square[best_uci[:2].upper()], Square[best_uci[2:].upper()])

        generator = MoveGenerator()
        generated_moves = generator.generate_moves(board)
        if best_move in generated_moves:
            best_move = generated_moves[generated_moves.index(best_move)]

        mate_check = generator.is_check(board, best_move)
        board.make_move(best_move)

        return mate_check

    @staticmethod
    def uci(move: Move) -> str:
        return f'{move.from_square.name.lower()}{move.to_square.name.lower()}'
