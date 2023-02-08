from board import Square, Board
from piece import ChessColor, Piece, PieceType
from enum import Enum


class MoveResult(Enum):
    NONE = 0
    CHECK = 1
    DOUBLE_CHECK = 2
    CHECKMATE = 3
    STALEMATE = 4


class MoveFlag(Enum):
    NONE = 0
    EN_PASSANT = 1
    CASTLING = 2
    PROMOTE_QUEEN = 3
    PROMOTE_KNIGHT = 4
    PROMOTE_ROOK = 5
    PROMOTE_BISHOP = 6
    PAWN_TWO_FORWARD = 7

    def promotion(self) -> bool:
        """
        Returns if the Flag is a promotion flag
        """

        return 3 <= self.value < 7

    def promotion_type(self) -> PieceType:
        if not self.promotion():
            return None

        return PieceType[self.name.replace('PROMOTE_', '')]


class Move:
    """
    A simple data structure representing a move
    """

    def __init__(self, from_square: Square, to_square: Square, flag: MoveFlag = MoveFlag.NONE):
        self.from_square = from_square
        self.to_square = to_square

        self.flag = flag

    def __str__(self):
        return f'{self.from_square} -> {self.to_square}'

    def __repr__(self):
        return self.__str__()

    def __eq__(self, other):
        return self.from_square.value == other.from_square.value and self.to_square.value == other.to_square.value

    def __hash__(self):
        return hash((self.from_square, self.to_square))


class MoveGenerator:
    offsets = [8, -8, -1, 1, 7, -7, 9, -9]
    all_knight_jumps = [15, 17, -17, -15, 10, -6, 6, -10]

    squares_to_edge = [[] * 8] * 64
    for file in range(8):
        for rank in range(8):
            north = 7 - rank
            south = rank
            west = file
            east = 7 - file

            square_index = (rank * 8 + file)
            squares_to_edge[square_index] = [
                # Orthogonals
                north,
                south,
                west,
                east,

                # Diagonals
                min(north, west),
                min(south, east),
                min(north, east),
                min(south, west)
            ]

    knight_moves = [[] * 8] * 64
    for square in range(64):
        # y = int(square / 8)
        # x = int(square - y * 8)

        rank = int(square / 8)
        file = int(square - rank * 8)

        legal_moves = [] * 8
        for i, jump in enumerate(all_knight_jumps):
            jump_square = square + jump
            if 0 <= jump_square < 64:
                jump_rank = int(jump_square / 8)
                jump_file = int(jump_square - jump_rank * 8)

                move_distance = max(abs(file - jump_file), abs(rank - jump_rank))
                if move_distance == 2:
                    legal_moves.append(jump_square)
        knight_moves[square] = legal_moves

    king_moves = [[] * 8] * 64
    for square in range(64):
        rank = int(square / 8)
        file = int(square - rank * 8)

        legal_king_moves = [] * 8
        for king_move in offsets:
            king_square = square + king_move
            if 0 <= king_square < 64:
                king_rank = int(king_square / 8)
                king_file = int(king_square - king_rank * 8)

                distance = max(abs(file - king_file), abs(rank - king_rank))
                if distance == 1:
                    legal_king_moves.append(king_square)
        king_moves[square] = legal_king_moves

    pawn_attack_directions = [[7, 5], [4, 6]]

    pawn_captures_white = [[] * 2] * 64
    pawn_captures_black = [[] * 2] * 64

    for square in range(64):
        rank = int(square / 8)
        file = int(square - rank * 8)

        white_captures = []
        black_captures = []
        if file > 0:
            if rank < 7:
                white_captures.append(square + 7)
            if rank > 0:
                black_captures.append(square - 9)

        if file < 7:
            if rank < 7:
                white_captures.append(square + 9)
            if rank > 0:
                black_captures.append(square - 7)
        pawn_captures_white[square] = white_captures
        pawn_captures_black[square] = black_captures

    # Bitboards (We are really just using 1 and 0 for if its attacked or not)
    bitboards = [[[0] * 64] * 6] * 2  # Default everything to 0, it will be changed to 1 if the square is under control

    white_attacks = 0x0
    black_attacks = 0x0

    # We will get undefended squares by ORing (white_attack | black_attack) will give us the undefended attacks

    def __init__(self):
        self.moves = []
        self.board = None

        self._incheck = False

    def incheck(self) -> ChessColor:
        return self._incheck

    def generate_moves(self, board: Board, for_checks=True):
        self.board = board
        self.moves = []

        for square in Square:
            piece = board.square(square)

            if piece.color != board.next:
                continue

            if piece.piece_type == PieceType.KING:
                self.generate_king_moves(square, piece)

            if piece.sliding():
                self.generate_sliding_moves(square, piece)
            elif piece.piece_type == PieceType.KNIGHT:
                self.generate_knight_moves(square, piece)
            elif piece.piece_type == PieceType.PAWN:
                self.generate_pawn_moves(square, piece)

            # To intensive
            # if for_checks:
            #     for i in range(len(self.moves) - 1, -1, -1):
            #         move: Move = self.moves[i]
            #         if self.is_check_self(board, move):
            #             self.moves.remove(move)

        return self.moves

    def generate_sliding_moves(self, start_square: Square, piece: Piece):
        start_direction_index = 4 if piece.piece_type == PieceType.BISHOP else 0
        end_direction_index = 4 if piece.piece_type == PieceType.ROOK else 8

        for direction in range(start_direction_index, end_direction_index):
            for n in range(self.squares_to_edge[start_square.value][direction]):
                target = start_square.value + self.offsets[direction] * (n + 1)
                target_square = Square(target)
                target_piece = self.board.square(target_square)

                # Friendly piece
                if not target_piece.none() and target_piece.color == self.board.next:
                    break

                self.moves.append(Move(start_square, target_square))

                # Enemy piece (only after capturing can we not move further)
                if not target_piece.none() and target_piece.color != self.board.next:
                    break

        return len(self.moves)

    def generate_knight_moves(self, start_square: Square, piece: Piece):
        # Add a check here for pins!

        for move in self.knight_moves[start_square.value]:
            target_square = Square(move)
            target_piece = self.board.square(target_square)

            # Skip if square is occupied by friendly piece
            if not target_piece.none() and target_piece.color == self.board.next:
                continue

            self.moves.append(Move(start_square, target_square))

    def generate_pawn_moves(self, start_square: Square, piece: Piece):
        pawn_offset = -8 if self.board.next == ChessColor.WHITE else 8
        start_rank = 6 if self.board.next == ChessColor.WHITE else 1
        before_promotion_rank = 1 if self.board.next == ChessColor.WHITE else 6

        # PROGRESSION MOVEMENT
        rank = int(start_square.value / 8)
        one_forward = Square(start_square.value + pawn_offset) if int(start_square.value / 8) > 0 else start_square

        if self.board.square(one_forward).none():
            if rank == before_promotion_rank:
                self.moves.append(Move(start_square, one_forward, flag=MoveFlag.PROMOTE_QUEEN))
            else:
                self.moves.append(Move(start_square, one_forward))

        if rank == start_rank:
            two_forward = Square(one_forward.value + pawn_offset)
            if self.board.square(two_forward).none() and self.board.square(one_forward).none():
                self.moves.append(Move(start_square, two_forward, flag=MoveFlag.PAWN_TWO_FORWARD))

        # CAPTURES MOVEMENT
        for i in range(2):
            if self.squares_to_edge[start_square.value][self.pawn_attack_directions[self.board.next.value][i]] > 0:
                pawn_capture_direction = self.offsets[self.pawn_attack_directions[self.board.next.value][i]]
                target_square = Square(start_square.value + pawn_capture_direction)
                target_piece = self.board.square(target_square)

                # Opponent Piece
                if not target_piece.none() and target_piece.color != self.board.next:
                    self.moves.append(Move(start_square, target_square))

                # Check En Passant
                elif self.board.en_passant is not None and target_square == self.board.en_passant:
                    if self.board.next == ChessColor.WHITE and int(target_square.value / 8) == 2:
                        self.moves.append(Move(start_square, target_square, MoveFlag.EN_PASSANT))
                    elif self.board.next == ChessColor.BLACK and int(target_square.value / 8) == 6:
                        self.moves.append(Move(start_square, target_square, MoveFlag.EN_PASSANT))

    def generate_king_moves(self, start_square: Square, piece: Piece):
        for move in self.king_moves[start_square.value]:
            target_square = Square(move)
            target_piece = self.board.square(target_square)

            # King cannot take his own pieces
            if not target_piece.none() and target_piece.color == self.board.next:
                continue

            capture = not target_piece.none() and target_piece.color != self.board.next
            if not capture:
                # King cannot move to squares that are under attack
                if self.square_is_check(target_square):
                    continue

            if not self.square_attacked(target_square):
                self.moves.append(Move(start_square, target_square))

                # Castling
                if not self.incheck() and not capture:
                    if (target_square == Square.F1 or target_square == Square.F8) and self.board.kingside_castle():
                        castle_square = Square(target_square.value + 1)
                        if self.board.square(castle_square).none():
                            if not self.square_attacked(castle_square):
                                self.moves.append(Move(start_square, castle_square, flag=MoveFlag.CASTLING))
                    elif (target_square == Square.D1 or target_square == Square.D8) and self.board.queenside_castle():
                        castle_square = Square(target_square.value - 1)
                        if self.board.square(castle_square).none() \
                                and self.board.square(Square(castle_square.value - 1)).none():
                            if not self.square_attacked(castle_square):
                                self.moves.append(Move(start_square, castle_square, flag=MoveFlag.CASTLING))

    def square_is_check(self, square: Square) -> bool:
        """
        Returns if the Square is in the Check ray (while the king is also in check)
        :param square:
        :return:
        """

        return False  # TODO

    def square_attacked(self, square: Square) -> bool:
        """
        Returns if the Square is being attacked by the opponent
        :param square: the Square to check
        :return: a bool
        """

        return False

        # self.populate_attacks()
        #
        # return (self.white_attacks | self.black_attacks
        #         if self.board.next == ChessColor.WHITE
        #         else self.black_attacks | self.white_attacks >> square.value) & 1

    def is_check(self, board_to_check: Board, move: Move, second=False):
        opponent_kingsquare = None
        check = MoveResult.NONE

        for square in board_to_check.squares:
            piece: Piece = board_to_check.square(square)
            if piece.piece_type == PieceType.KING and piece.color != board_to_check.next:
                opponent_kingsquare = square
                break

        fake_board: Board = board_to_check.clone()
        fake_generator: MoveGenerator = MoveGenerator()
        fake_board.make_move(move)
        fake_board.next = board_to_check.next  # We are checking if white has any checks so stay with white
        moves = fake_generator.generate_moves(fake_board, for_checks=False)
        for m in moves:
            m: Move = m
            if m.to_square == opponent_kingsquare:
                check = MoveResult.CHECK

                if second:
                    return check
                fake_board.next = ChessColor.BLACK if fake_board.next == ChessColor.WHITE else ChessColor.WHITE

                valid_response_moves = []
                for response_move in fake_generator.generate_moves(fake_board):
                    new_kingsquare = opponent_kingsquare
                    if response_move.from_square == opponent_kingsquare:
                        new_kingsquare = response_move.to_square

                    fake_board2 = fake_board.clone()
                    fake_board2.make_move(response_move)  # Will switch the color for us

                    escapes = True
                    for m3 in fake_generator.generate_moves(fake_board2):
                        if m3.to_square == new_kingsquare:
                            escapes = False
                            break

                    if escapes:
                        valid_response_moves.append(response_move)

                if len(valid_response_moves) == 0:
                    check = MoveResult.CHECKMATE
        return check

    def is_check_self(self, board_to_check: Board, move: Move):
        """
        Returns if theh current mover is still in check after the attempted move
        :param board_to_check:
        :param move:
        :return:
        """
        fake_board: Board = board_to_check.clone()
        fake_board.make_move(move)

        king_square = None
        for square in Square:
            piece = fake_board.square(square)
            if piece.piece_type == PieceType.KING and piece.color == board_to_check.next:
                king_square = square
                break

        moves = MoveGenerator().generate_moves(fake_board, for_checks=False)
        for m in moves:
            m: Move = m
            if m.to_square == king_square:
                return True

        return False
