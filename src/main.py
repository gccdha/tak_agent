from ast import Tuple
from enum import Enum
from os import WCOREDUMP
from pickle import EMPTY_TUPLE
import random
from typing import Any, Callable, override
# This project will have to be moved into a jupyter notebook .ipynb file...

def menu(params, message: str | None = None): # pyright: ignore[reportUnknownParameterType, reportMissingParameterType]
    keys = list(params.keys())    # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType, reportUnknownArgumentType]
    numkeys= len(keys)      # pyright: ignore[reportUnknownArgumentType]
    while True:
        if message is not None:
            print(message)
        else:
            print("Choose one of the following:")

        for i,p in enumerate(keys):  # pyright: ignore[reportUnknownVariableType, reportUnknownArgumentType]
            print(f"{i}) {p}")
        
        try:
            choice : int = int(input())
        except ValueError:
            print("ERROR: Please enter a number")
        else:
            if choice in range(0, numkeys):
                return params[keys[choice]]  # pyright: ignore[reportUnknownVariableType]
            else:
                print(f"ERROR: Please enter a number between 0 and {numkeys-1} (inclusive)")

def drop_menu() -> list[int]: # TODO: Make this way better, with its own ui and everything
    i = 0
    output: list[int] = []
    while True:
        print(f"Choose number of drops for tile {i} or -1 to end:")
        
        try:
            choice = int(input())
        except ValueError:
            print("ERROR: Please enter a number")
        else:
            match choice:
                case -1: return output
                case 0:
                    if i == 0: output.append(choice); i+=1
                    else: print("ERROR: Please enter a number greater than 0")
                case x if x < 0: print("ERROR: Please enter a non-negative number")
                case x: output.append(choice); i+=1

def generate_drops(board: "Board", square: tuple[int, int], dir : "Direction") -> list[list[drops]]:
    # get distance to wall in direction
    distance = 0
    current
    for i in range()
    # get if the wall is hard (capstone or edge of board) or soft (standing stone)


class Color(Enum):
    BLACK = 0
    WHITE = 1

class PieceType(Enum):
    FLATSTONE     = 0
    STANDINGSTONE = 1
    CAPSTONE      = 2

class Direction(Enum):
    UP    = 0
    RIGHT = 1
    DOWN  = 2
    LEFT  = 3

CAPSTONES = {3:0, 4:0, 5:1, 6:1, 7:2, 8:2}
NORMAL_STONES = {3:10, 4:15, 5:21, 6:30, 7:40, 8:50}
DEPTH = 3

B_ON_W = "\033[30;107m"
W_ON_B = "\033[97;40m"
RESET = "\033[0m"



class Piece:
    def __init__(self, color : Color, piece_type: PieceType):
        self.color: Color = color
        self.piece: PieceType = piece_type

    def get_string(self) -> str:
        piece_char = self.piece.name[0]

        match self.color:
            case Color.BLACK: colorcode = W_ON_B
            case Color.WHITE: colorcode = B_ON_W
        
        return colorcode + piece_char + RESET

class Move:
    def __init__(self, square:tuple[int,int], 
                 direction: Direction | None = None, 
                 count:int = 1, drops:list[int]|None = None, 
                 stone:PieceType = PieceType.FLATSTONE):
        self.square: tuple[int,int] = square # tuple of values (x, y),
        self.direction: Direction | None = direction
        self.count: int = count
        self.drops: list[int] = drops if drops is not None else [count]


class Game:
    def __init__(self, 
                    p1 : "Player | None" = None,
                    p2 : "Player | None" = None,
                    board_size : int | None = 5,
                    komi : float | None = 0,
                    p1_depth : int = DEPTH,
                    p2_depth : int = DEPTH) : 

        if board_size is None:
            board_size = menu(
                    { "3x3":3, "4x4":4, "5x5":5, "6x6":6, "7x7":7, "8x8":8},
                    "Please choose a board size:")
        
        capstones = CAPSTONES[board_size]
        normal_stones = NORMAL_STONES[board_size]

        if komi is None:
            komi = menu(
                    {"0":0, "0.5":0.5, "1":1, "1.5":1.5, "2":2, "2.5":2.5, "3":3},
                    "Please choose a komi (1st player handicap):")

        if p1 is None:
            p1= menu({
                "random" : RandomPlayer(), 
                "human": HumanPlayer(), 
                "minimax": MinimaxPlayer()},
                "Choose a strategy for player 1:")

        p1.__init__(Color.WHITE, normal_stones, capstones, -komi, p1_depth)

        if p2 is None:
            p2 = menu({
                "random" : RandomPlayer(), 
                "human": HumanPlayer(), 
                "minimax": MinimaxPlayer()},
                "Choose a strategy for player 2:")

        p2.__init__(Color.BLACK, normal_stones, capstones, komi, p2_depth)

        self.p1: Player = p1 # NOTE: May not need self.p1,p2 could just swap player and opponent and store the player number in the Player object for when needed
        self.p2: Player = p2
        self.board: Board = Board(board_size)
        self.current_player: Player = p1
        self.current_opponent: Player = p2
        self.turn_number : int = 0 
        self.moves : list[Move] = []



    def play(self):
        self.opener()
        while not self.is_over():
            self.turn()

    def opener(self):
        # get move from each player, (p1.get_move() etc.) but swap the Color. 
        # make it clear that it is the opener to any human player
        # self.turn_number
        pass #TODO:
    
    def turn(self):
        while True:
            move: Move = self.p1.get_move(self)
            if self.board.move(move):
                self.moves.append(move)
                break
        self.current_player, self.current_opponent = self.current_opponent, self.current_player
        if self.current_player == self.p1:
            self.turn_number += 1


    
    def is_over(self) -> bool: #TODO:
        # check if the game is over
        raise NotImplementedError







class Board:
    def __init__(self, size: int, board : list[list[list[Piece]]] | None = None):
        self.size: int = size
        if board is None:
            self.grid: list[list[list[Piece]]] = [[[] for _ in range(size)] for _ in range(size)]
        else:
            self.grid = board

    def move(self, move : Move) -> bool: #TODO:
        if not self.test_move(move):
            return False

        

        raise NotImplementedError
    
    def test_move(self, move:Move) -> bool: #TODO:
        # return true if a move can be made and false if it can't be
        raise NotImplementedError

    def open_spaces(self) -> int: #TODO:
        #return the number of spaces that don't have any piece on them 
        #(or maybe return true if there are any open and false otherwise?)
        raise NotImplementedError

    def is_road(self) -> bool: #TODO:
        # return true if there is a roard and false otherwise.
        #(use bfs from two sides to try to find the other side)
        #(there may be a way to do it incrementally, like store old bfs and use them instead
        #of recalculating every time but idk)
        raise NotImplementedError

    def display(self) -> None: #TODO: Add number and letters to board
        top = " ╭"+ "─┬"*(self.size-1) +"─╮"
        mid = " ├"+ "─┼"*(self.size-1) +"─┤"
        bot = " ╰"+ "─┴"*(self.size-1) +"─╯"

        print(top)
        for i,row in enumerate(self.grid):
            max_height = max(len(x) for x in row)
            row_str = ""
            if max_height == 0:
                row_str = " │"*(self.size+1)
            else:
                while max_height > 0:
                    line_str = " │"
                    for stack in row: 
                        if len(stack) >= max_height:
                            line_str += stack[max_height-1].get_string() + "│"
                        else:
                            line_str += " │"
                    max_height -= 1
                    row_str = row_str + line_str + "\n"
            if i != 0: print(mid)
            print(row_str[:-1])
        print(bot)


    def enumerate_moves(self, player : "Player") -> list[Move]:#TODO:
        #return a list of all valid moves for the player in current position
        #(passing the entire player object may be a bit overkill...)

        #one placement move for each open tile per type of tile player has >0 of left 

        #check notebook for movement check method

        raise NotImplementedError

    #TODO: doesn't need to be a method of board...
    def offset_tile(self, tile:tuple[int,int], dir: Direction,  times:int = 1) -> tuple[int,int]:
        match dir:
            case Direction.UP:    return (tile[0], tile[1]+times)
            case Direction.RIGHT: return (tile[0]+times, tile[1])
            case Direction.DOWN:  return (tile[0], tile[1]-times)
            case Direction.LEFT:  return (tile[0]-times, tile[1])

    def get_stack(self, tile : tuple[int, int], dir : Direction | None = None) -> list[Piece] | None:
        #NOTE: Tile tuple has ints in range [0,size-1] inclusive
        
        offset:Callable[[int, int],list[Piece]] = lambda x, y: self.grid[self.size - 1 - y - tile[1]][tile[0]+x]

        try:
            match dir:
                case None: return offset(0,0)
                case Direction.UP: return offset(0,1)
                case Direction.RIGHT: return offset(1,0)
                case Direction.DOWN: return offset(0,-1)
                case Direction.LEFT: return offset(-1,0)
        except IndexError:
            return None
    
    def distance_to_wall(self,tile:tuple[int,int], dir : Direction) -> tuple[PieceType | None, int]: #(type of wall (none for edge of board), distance)
        for i in range(0,self.size):
            stack = self.get_stack(self.offset_tile(tile, dir,i+1))
            if stack is None: return (None, i)
            match stack[-1].piece:
                case PieceType.FLATSTONE: pass
                case x: return (x, i) #TODO:check this
        return (None, 0)
        

class Player:
    def __init__(self, piece_color : Color = Color.BLACK, normal_stones : int = 0, capstones : int = 0, komi : float = 0, depth: int = DEPTH):
        self.piece_color: Color = piece_color
        self.komi: float = komi
        self.normal_stones: int = normal_stones
        self.capstones: int = capstones
        self.depth: int = depth

    def get_move(self, game : Game) -> "Move":   # pyright: ignore[reportUnusedParameter]
        raise NotImplementedError

class HumanPlayer(Player):
    @override
    def get_move(self, game: Game) -> Move: #TODO:: add checking for each part. Add option durring start of game to use PTN
        # get a move from the player in PTN or just ask for each part

        rows = {chr(ord('A')+x):x for x in range(0,game.board.size)}
        cols = {str(x):x for x in range(0,game.board.size)}
        square: tuple[int, int] = ( 
            menu(rows, "Choose a column:"),
            menu( cols, "Choose a row:")
        )
        stack = game.board.get_stack(square)
        if not stack:
            #place 
            piece = menu({"flatstone":PieceType.FLATSTONE, 
                          "standing stone":PieceType.STANDINGSTONE,
                          "capstone stone":PieceType.CAPSTONE}, "What kind of piece would you like to place?:")
            return Move(square,stone = piece)
        else:
            #move
            direction = menu({"up":Direction.UP, "right":Direction.RIGHT,
                              "down":Direction.DOWN, "left":Direction.LEFT},
                             "Chose a direction to move:")
            count = 1
            if len(stack) > 1:
                count = menu({str(x):x for x in range(1,min(game.board.size+1, len(stack)))}, 
                             "How many pieces do you want to grab from this stack?")
            drops = drop_menu()

            return Move(square, direction, count, drops)



class RandomPlayer(Player):
    @override
    def get_move(self, game: Game) -> Move:
        moves = game.board.enumerate_moves(self)
        return random.choice(moves)

class MinimaxPlayer(Player):
    def evaluate(self, board: Board) -> int: #TODO:
        #evaluate a position. could try wall = 1, flat = 2, cap = 3 or just raw controlled area
        raise NotImplementedError
    
    #TODO: optional: make a function that calls the chatgpt api to get a move

    @override
    def get_move(self, game : Game) -> Move:#TODO:
        assert self.depth is not None
        return self.minimax(0, self.depth, game.board )[1]


    def minimax(self, depth:int, max_depth:int, board:Board) -> tuple[int, Move]: #TODO: (this is the recursive one)
        # if depth%2 == 0: max; else: min (or something like that) 
        # This is just raw minimax, we can add a different agent for alpha-beta if there is time
        # for move in board.enumerate_moves(self): min/max of minimax(depth-1, board.copy.move(move))
        raise NotImplementedError




wc = Piece(Color.WHITE, PieceType.CAPSTONE)
wf = Piece(Color.WHITE, PieceType.FLATSTONE)
ws = Piece(Color.WHITE, PieceType.STANDINGSTONE)
bc = Piece(Color.BLACK, PieceType.CAPSTONE)
bf = Piece(Color.BLACK, PieceType.FLATSTONE)
bs = Piece(Color.BLACK, PieceType.STANDINGSTONE)



grid =  [[[wc],[],[ bf, wc]],
                                [[ws, bs],[wf, wf, wf, wf, bf],[]],
                                [[],[bc],[wc,wf,ws,bc,bf,bs]]]

board = Board(3, grid)
print(board.grid)
board.display()
