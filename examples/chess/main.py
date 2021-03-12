from pydraw import *
from board import Board, Evaluation
from renderer import Renderer
from move import Move, MoveGenerator
from ai import AIPlayer, EnginePlayer

screen = Screen(800, 600, "Chess")
# screen.fullscreen(True)
screen.color(Color('#303030'))

board = Board()
renderer = Renderer(screen, (screen.width() - min(screen.width(), screen.height())) / 2, 0, min(screen.width(), screen.height()))
renderer.render(board, draw_squares=True)

eval_text = Text(screen, 'Eval: 0', 10, 10, color=Color('white'))

generator = MoveGenerator()

screen.alert('Test\ntest\ntest')

ai = AIPlayer(screen)


def update_board():
    eval_text.text(f'Eval: {Evaluation(board).get() / 100}')

    renderer.render(board)
    renderer.reset_squares()
    screen.update()


dragging = False
dragged = None
dragged_square = None
dragged_piece = None


def mousedrag(button, location):
    global dragging
    global dragged
    global dragged_square
    global dragged_piece

    if button != 1:
        return

    if dragging and dragged is not None:
        dragged.moveto(location)
        dragged.move(-dragged.width() / 2, -dragged.height() / 2)

        # print(renderer.generator.generate_sliding_moves(dragged_square, dragged_piece))
        screen.update()
    elif not dragging:
        piece_sprite = renderer.get_piece(location)
        dragged_square = renderer.get_square(location)
        dragged_piece = board.square(dragged_square)

        if not dragged_piece.none() and dragged_piece.color != board.next:
            return

        if piece_sprite is not None:
            dragging = True
            dragged = piece_sprite
            dragged.front()  # Move to front to keep a clean visual
            renderer.render_moves(board, dragged_square)


def mouseup(button, location):
    from move import MoveResult

    global board
    global dragging
    global dragged

    if dragging and dragged is not None:
        dragging = False
        square = renderer.get_square(location)

        checkmate = False

        if square is not None:
            move = Move(dragged_square, square)
            moves = generator.generate_moves(board)

            if len(moves) == 0:
                screen.prompt('You have stalemated!', 'Draw')
                board = Board()
                update_board()
                return

            ai_result = False

            # We loop through so special moves such as castling will be flagged
            if square != dragged_square:
                if move in moves:
                    real_move = moves[moves.index(move)]

                    check = generator.is_check(board, real_move)
                    self_check = generator.is_check_self(board, real_move)
                    if not self_check:
                        if check != MoveResult.NONE:
                            if check == MoveResult.CHECKMATE:
                                board.make_move(real_move)
                                checkmate = True
                            else:
                                board.make_move(real_move)
                                update_board()
                                ai_result = ai.make_move(board)
                        else:
                            board.make_move(real_move)
                            update_board()
                            ai_result = ai.make_move(board)
                    else:
                        print('Self is in check, move rejected.')

        update_board()

        if ai_result != MoveResult.NONE:
            if ai_result == MoveResult.CHECK:
                pass
            elif ai_result == MoveResult.STALEMATE:
                screen.prompt('Stalemate.', 'Draw')
                board = Board()
                update_board()
            elif ai_result == MoveResult.CHECKMATE:
                screen.prompt('You have been checkmated', 'You Lose!')
                board = Board()
                update_board()

        if checkmate:
            screen.prompt('Checkmate Ocurred! You win!\nPlay Again?', 'Game Over')
            board = Board()
            renderer.render(board)

        dragged = None


def keydown(key):
    if key == 'p':
        print(board.pawn_attacks())


screen.listen()

fps = 60
running = True
while running:
    screen.update()
