from enum import Enum
import os
import random
from typing import override


#number of stones a player gets based on board size
CAPSTONES = {3:0, 4:0, 5:1, 6:1, 7:2, 8:2}
NORMAL_STONES = {3:10, 4:15, 5:21, 6:30, 7:40, 8:50}

#default depth for minimax
DEPTH = 3

#ANSI color escapes
B_ON_W = "\033[30;107m"
W_ON_B = "\033[97;40m"
RESET = "\033[0m"

#max width of board
TERM_WIDTH = 80


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


# General purpose menu that takes a dictionary as input, list the keys as options and returns the corresponding entry
# while checking for errors.
def menu(params, message: str | None = None):                                               # pyright: ignore[reportUnknownParameterType, reportMissingParameterType]
    keys = list(params.keys())                                                          # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType, reportUnknownArgumentType]
    numkeys= len(keys)                                                                        # pyright: ignore[reportUnknownArgumentType]
    while True:
        if message is not None:
            print(message)
        else:
            print("Choose one of the following:")

        for i,p in enumerate(keys):                                                                # pyright: ignore[reportUnknownVariableType, reportUnknownArgumentType]
            print(f"{i}) {p}")
        
        try:
            choice : int = int(input())
        except ValueError:
            print("ERROR: Please enter a number")
        else:
            if choice in range(0, numkeys):
                return params[keys[choice]]                                                        # pyright: ignore[reportUnknownVariableType]
            else:
                print(f"ERROR: Please enter a number between 0 and {numkeys-1} (inclusive)")

# Menu specifically for getting the sequence of drops. (WARN: doesn't check if the drops make sense!) 
def drop_menu() -> list[int]: # TODO: Make this way better, with its own ui and everything
    i = 1
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
                    print("ERROR: Please enter a number greater than 0")
                case x if x < 0: print("ERROR: Please enter a non-negative number")
                case _: output.append(choice); i+=1

# Generate a list of possible moves for a given stack in a given direction
def generate_drops(board: "Board", square: tuple[int, int], dir : "Direction", pickup : int) -> list[list[int]]:
    #get the stack to take from and if it has a capstone on top
    stack = board.get_stack(square)
    if stack is None:
        raise IndexError("square out of bounds")
    capstone = stack[-1].piece is PieceType.CAPSTONE

    # get distance to wall from square in direction dir
    wall, distance = board.distance_to_wall(square,dir)
    
    # is the wall hard (capstone or edge of board) or soft (standing stone)
    hard = wall is not PieceType.STANDINGSTONE

    output: list[list[int]] = []
    if distance == 0: #handle the case of a single capstone seperately
        if not hard and pickup == 1 and capstone:
            output.append([1])
    else:
        gdhelper(pickup,capstone, distance-1,  hard, output, []) 
    return output

# Recursively find all possible drops for a given pickup size, n
def gdhelper(n : int, capstone:bool, dist: int, hard:bool, output:list[list[int]], drops: list[int]):
    if n == 0: #if we run out of stones, add the path we used to get here
        output.append(drops)
        return
    elif dist == 0: #if we reach a wall drop all remaining stones (and deal with case where we can squash a standing stone)
        if not hard and capstone and n>1:
            output.append(drops+[n-1, 1])
        output.append(drops+[n])
        return

    # Recur for every possible amount of stones that could have been dropped
    for i in range(1,n+1):
        gdhelper(n-i, capstone, dist-1, hard, output, drops+[i])



class Piece:
    def __init__(self, color : Color, piece_type: PieceType):
        self.color: Color = color
        self.piece: PieceType = piece_type

    #return character with ANSI color applied
    def get_string(self) -> str:
        piece_char = self.piece.name[0]

        match self.color:
            case Color.BLACK: colorcode = W_ON_B
            case Color.WHITE: colorcode = B_ON_W
        
        return colorcode + piece_char + RESET


#Class that represents a move (placement or real move)
#It may be wise to create subclasses for placement and movement
class Move:
    def __init__(self,
                 square:tuple[int,int], 
                 direction: Direction | None = None, 
                 count:int = 1, #number of tiles to pick up to move
                 drops:list[int]|None = None, 
                 stone:PieceType = PieceType.FLATSTONE
                 ):
        self.square: tuple[int,int] = square # tuple of values (x, y),
        self.direction: Direction | None = direction
        self.count: int = count
        self.drops: list[int] | None = drops
        self.stone: PieceType | None= stone if direction is None else None

    #return a string that is this move in PTN (Portable Tak Notation)
    def to_ptn(self) -> str:
        square =  chr(97+self.square[0])+str(self.square[1]+1) # Get square rank and column

        # Placement
        if self.direction is None:
            if self.stone is None: raise ValueError("Error while converting piece to PTN: Move cannot have no stone and no direction")
            stone = "" if self.stone is PieceType.FLATSTONE else self.stone.name[0]  
            return stone+square

        # Movement
        else:
            match self.direction:
                case Direction.UP: dir = "+"
                case Direction.RIGHT: dir = ">"
                case Direction.DOWN: dir = "-"
                case Direction.LEFT: dir = "<"

            #count can be excluded if it is 1
            count = "" if self.count == 1 else str(self.count)

            #drops can be excluded if they are the same as count
            if self.drops is not None and self.drops[0] == self.count: 
                drops = ""
            else:
                #drops are always 1 digit numbers because the max board size is 8
                #so we just concat them all together
                drops = "".join(map(str, self.drops)) if self.drops is not None else ""

            return count + square + dir + drops


#
class Game:
    def __init__(self, 
                    p1 : "Player | None" = None,
                    p2 : "Player | None" = None,
                    board_size : int | None = 5,
                    komi : float | None = 0,
                    p1_depth : int = DEPTH,
                    p2_depth : int = DEPTH,
                    board : "Board| None" = None
                 ) : 
        # Get board size if not specified (defaults to 5)
        if board_size is None:
            board_size = menu(
                    { "3x3":3, "4x4":4, "5x5":5, "6x6":6, "7x7":7, "8x8":8},
                    "Please choose a board size:")
        
        # Get komi if not specified (defaults to 0)
        if komi is None:
            komi = menu(
                    {"0":0, "0.5":0.5, "1":1, "1.5":1.5, "2":2, "2.5":2.5, "3":3},
                    "Please choose a komi (1st player handicap):")

        # Get the correct number of stones for the board size
        capstones = CAPSTONES[board_size]
        normal_stones = NORMAL_STONES[board_size]

        # Get P1 and P2 methods (defaults to asking)
        if p1 is None:
            p1= menu({
                "random" : RandomPlayer(), 
                "human": HumanPlayer(), 
                     "minimax": MinimaxPlayer()},
                "Choose a strategy for player 1:")

        p1.__init__(Color.WHITE, normal_stones, capstones, 0, p1_depth, 1)

        if p2 is None:
            p2 = menu({
                "random" : RandomPlayer(), 
                "human": HumanPlayer(), 
                "minimax": MinimaxPlayer()},
                "Choose a strategy for player 2:")

        p2.__init__(Color.BLACK, normal_stones, capstones, komi, p2_depth, 2)

        # Use provided board if it is the correct size, otherwise use empty board.
        self.board: Board = Board(board_size) if board is None or board.size != board_size else board

        self.current_player: Player = p1
        self.current_opponent: Player = p2
        self.turn_number : int = 0 
        self.moves : list[Move] = []


    # Main loop of the game
    def play(self, display:bool = False):
        self.opener(display)
        while not self.is_over():
            if display: 
                self.display()
            self.turn()
        print("Game is over!")
        self.board.display()

    def display(self):
        #print the turn number, which player's turn it is and what the last move was
        print("Turn ", self.turn_number, "  Current player:", self.current_player.id,"  Previous move: ", self.moves[-1].to_ptn() if self.moves else "n/a")
        #print the board
        self.board.display()
        #print each player, their pieces, their color, and their strategy
        self.current_player.display()
        self.current_opponent.display() 

    def opener(self, display:bool):
        if display: self.display()
        move1= self.current_player.get_move(self, opener = True)
        _=self.board.move(move1, self.current_opponent)
        if display: self.display() 
        move2 = self.current_opponent.get_move(self, opener = True)
        _=self.board.move(move2,self.current_player)
        if display: self.display()
        # get move from each player, (p1.get_move() etc.) but swap the Color. 
        # make it clear that it is the opener to any human player
        # self.turn_number

        pass #TODO:
    
    def turn(self):
        while True:
            move: Move = self.current_player.get_move(self)
            if self.board.move(move,self.current_player):
                self.moves.append(move)
                break
        self.current_player, self.current_opponent = self.current_opponent, self.current_player
        if self.current_player.id == 1:
            self.turn_number += 1


    
    def is_over(self) -> bool: 
        x = self.board.is_road()
        if self.board.is_road() != (False, False):
            print(f"Road win!{x}")
            return True
        if self.board.open_spaces() == 0:
            print("Flat win!")
            return True
        if (self.current_player.capstones + self.current_player.normal_stones) == 0:
            print("current player out of stones!")
            return True
        if (self.current_opponent.capstones + self.current_opponent.normal_stones) == 0:
            print("current opponent out of stones!")
            return True
        return False







class Board:
    def __init__(self, size: int, board : list[list[list[Piece]]] | None = None):
        self.size: int = size
        if board is None:
            self.grid: list[list[list[Piece]]] = [[[] for _ in range(size)] for _ in range(size)]
        else:
            self.grid = board

    def move(self, move : Move, player: "Player", test : bool = False) -> bool: #TODO: test this function more thuroughly
        if test and not self.test_move(move, player):
            return False



        stack= self.get_stack(move.square)
        if stack is None:
            raise ValueError("None stack while getting stack for move");

        # for placements
        if move.direction is None:
            if move.stone == PieceType.CAPSTONE:
                player.capstones -= 1
            else:
                player.normal_stones -=1

            if move.stone is None:
                raise ValueError("Stone not specified for placement")

            stack.append(Piece(player.piece_color, move.stone))

        # for movements
        else:
            if move.drops is None:
                raise ValueError("Trying to move with None drops")
            pickup = stack[-move.count:]
            del stack[-move.count:] #TODO: make sure this does what you think it does

            offset = 1
            while len(pickup) != 0:
                # print("Offset: ", offset)
                # print("Drops: ", move.drops)
                # print("pickup: ", pickup)
                adj_stack = self.get_stack(self.offset_tile(move.square, move.direction, offset))
                if adj_stack is None:
                    raise ValueError("None stack durring drops")

                if adj_stack and adj_stack[-1].piece == PieceType.STANDINGSTONE:
                    if pickup[0].piece != PieceType.CAPSTONE:
                        raise ValueError("Attempted to flatten standing stone with non-capstone")
                    adj_stack[-1].piece = PieceType.FLATSTONE

                # print("extending with: ",pickup[0:move.drops[offset-1]]) 
                adj_stack.extend(pickup[0:move.drops[offset-1]])

                if move.drops[offset-1] < len(pickup):
                    pickup = pickup[move.drops[offset-1]:]
                elif move.drops[offset-1] == len(pickup):
                    pickup = []

                offset += 1 

        return True


    
    def test_move(self, move:Move, player: "Player") -> bool: 
        # return true if a move can be made and false if it can't be
        # (should replace this in the future with just not allowing bad input)

        if move in self.enumerate_moves(player):
            return True
        else:
            return False

    def open_spaces(self) -> int: 
        #return the number of spaces that don't have any piece on them 
        #(or maybe return true if there are any open and false otherwise?)
        return sum(1 for x in self.grid for y in x if not y)

    def is_road(self) -> tuple[bool,bool]: # output is (black?, white?)
        # return true if there is a roard and false otherwise.
        #(use bfs from two sides to try to find the other side)
        #(there may be a way to do it incrementally, like store old bfs and use them instead
        #of recalculating every time but idk)

        ub =  self.dfs(Direction.UP, Color.BLACK, [], [], (None, 0))
        uw =   self.dfs(Direction.UP, Color.WHITE, [], [], (None, 0))
        lb = self.dfs(Direction.LEFT, Color.BLACK, [], [], (self.size-1, None))
        lw =   self.dfs(Direction.LEFT, Color.WHITE, [], [], (self.size-1, None))

        return (ub or lb, uw or lw)







    def dfs(self, node: Direction | tuple[int, int], col: Color, stack:list[tuple[int,int]], visited : list[tuple[int,int]], goal:tuple[int|None, int|None] = (None, None)) -> bool:
        match node:
            case Direction.UP:    stack = [(x, self.size-1) for x in range(0,self.size-1)] 
            case Direction.RIGHT: stack = [(self.size - 1, y) for y in range(0,self.size-1)]
            case Direction.DOWN:  stack = [(x, 0) for x in range(0,self.size-1)] 
            case Direction.LEFT:  stack = [(0,y) for y in range(0,self.size-1)] 
            case n:
                visited.append(n)
                # return true if the traversal reaches the goal row/column
                if n[1] == goal[1] or n[0] == goal[0]:
                    # print(f"n[1] == goal[1] or n[0] == goal[0]. n:{n},  goal:{goal}")
                    return True
                # add neighbors to stack
                for i in range(4):
                    neighbor = self.offset_tile(n, Direction(i))
                    tile = self.get_stack(neighbor)
                    if tile is not None and tile and tile[-1].color == col and tile[-1].piece != PieceType.STANDINGSTONE and neighbor not in visited:
                        stack.append(neighbor)

        # if the stack is empty after trying to add stuff to it, no path exists 
        if not stack:
            return False

        # print(stack)

        # Search the next subtree
        return self.dfs(stack.pop(), col, stack, visited, goal)






    def display(self) -> None:
        global_max = max(max(len(z) for x in self.grid for z in x), 10) 
        p = min(global_max,((TERM_WIDTH)-1)//self.size-1)
        top = " ╭"+ ("─"*(2*p+1)+"┬")*(self.size-1) +"─"*(2*p+1)+"╮"
        mid = " ├"+ ("─"*(2*p+1)+"┼")*(self.size-1) +"─"*(2*p+1)+"┤"
        bot = " ╰"+ ("─"*(2*p+1)+"┴")*(self.size-1) +"─"*(2*p+1)+"╯"
        letters = " "
        for i in range(self.size):
            letters = letters + " "*(p+1)+chr(97+i)+" "*(p)


        print(top)
        for i,row in enumerate(self.grid):
            max_height = global_max
            row_str = ""
            if max_height == 0: # handle all cels empty case
                row_str = (" "*(2*p+1)+"")*(self.size+1)
            else:
                while max_height > 0:
                    if max_height == global_max//2:
                        line_str = str(self.size - i)+"│" # draw index numbers
                    else:
                        line_str = " │"

                    for stack in row: 
                        if len(stack) >= max_height: # print things with tiles at this height
                            line_str += " "*p+ stack[max_height-1].get_string() + " "*p+"│"
                        else: # print spaces for things not at this height
                            line_str += " "*(2*p+1)+"│"
                    max_height -= 1
                    row_str = row_str + line_str + "\n"
            if i != 0: print(mid)
            print(row_str[:-1])
        print(bot)
        print(letters)


    def enumerate_moves(self, player : "Player", opener:bool = False) -> list[Move]:
        #return a list of all valid moves for the player in current position

        moves: list[Move] = []
        # for every square...
        for row in range(self.size):
            for col in range(self.size):
                square = (col,row)
                stack = self.get_stack(square)
                if not stack: # ... if its empty, the player can place any stone they have on it ...
                    if player.normal_stones > 0:
                        moves.append(Move(square)) #(only flatstone placement allowed in the opener)
                        if not opener: moves.append(Move(square,stone=PieceType.STANDINGSTONE))
                    if player.capstones > 0 and not opener:
                        moves.append(Move(square, stone=PieceType.CAPSTONE))
                elif stack[-1].color == player.piece_color and not opener: # ... and if it is their color they can move it.
                    for pickup in range(1,min(self.size, len(stack))+1):
                        for i in range(4):
                            dir = Direction(i)
                            possible_drops = generate_drops(self, square, dir, pickup)
                            for drops in possible_drops:
                                moves.append(Move(square,dir,pickup, drops)) 
        return moves
        


    #TODO: doesn't need to be a method of board...
    def offset_tile(self, tile:tuple[int,int], dir: Direction,  times:int = 1) -> tuple[int,int]:
        match dir:
            case Direction.UP:    return (tile[0], tile[1]+times)
            case Direction.RIGHT: return (tile[0]+times, tile[1])
            case Direction.DOWN:  return (tile[0], tile[1]-times)
            case Direction.LEFT:  return (tile[0]-times, tile[1])

    # Returns the stack on the given tile. Returns None if the tile is outside
    # the board area.
    def get_stack(self, tile : tuple[int, int]) -> list[Piece] | None:
        #NOTE: Tile tuple has ints in range [0,size-1] inclusive
        if max(tile) >= self.size or min(tile) < 0: return None
        else: return self.grid[self.size - 1 - tile[1]][tile[0]]
    
    def distance_to_wall(self,tile:tuple[int,int], dir : Direction) -> tuple[PieceType | None, int]: #(type of wall (none for edge of board), distance)
        for i in range(0,self.size):
            stack = self.get_stack(self.offset_tile(tile, dir,i+1))
            if stack is None: return (None, i)
            if stack:
                match stack[-1].piece:
                    case PieceType.FLATSTONE: pass
                    case x: return (x, i)
        return (None, 0)
        

class Player:
    def __init__(self, piece_color : Color = Color.BLACK, normal_stones : int = 0, capstones : int = 0, komi : float = 0, depth: int = DEPTH, id : int = 0):
        self.piece_color: Color = piece_color
        self.komi: float = komi
        self.normal_stones: int = normal_stones
        self.capstones: int = capstones
        self.depth: int = depth
        self.id: int = id

    def get_move(self, game : Game, opener:bool = False) -> "Move":   # pyright: ignore[reportUnusedParameter]
        raise NotImplementedError

    def display(self) -> None:
        if self.piece_color == Color.BLACK:
            color = B_ON_W
        else:
            color = W_ON_B
        strat = self.player_type()
        print(f"{color}Player:{self.id}  Strategy:{strat}, Normal Stones: {self.normal_stones}  Capstones: {self.capstones}{RESET}")

    def player_type(self) ->str:
        raise NotImplementedError



class HumanPlayer(Player):
    @override
    def get_move(self, game: Game, opener:bool = False) -> Move: #TODO:: add checking for each part. Add option durring start of game to use PTN
        # get a move from the player in PTN or just ask for each part

        if opener: print("OPENER: choose a square to place one of your opponent's flatstones on!")
        rows = {chr(ord('A')+x):x for x in range(0,game.board.size)}
        cols = {str(x):x for x in range(0,game.board.size)}
        square: tuple[int, int] = ( 
            menu(rows, "Choose a column:"),
            menu( cols, "Choose a row:")
        )

        if opener: return Move(square, stone = PieceType.FLATSTONE)

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

    @override
    def player_type(self) -> str:
        return "Human"



class RandomPlayer(Player):
    @override
    def get_move(self, game: Game, opener:bool = False) -> Move:
        moves = game.board.enumerate_moves(self, opener)
        return random.choice(moves)
    @override
    def player_type(self) -> str:
        return "Random"

class MinimaxPlayer(Player):
    def evaluate(self, board: Board) -> int: #TODO:
        #evaluate a position. could try wall = 1, flat = 2, cap = 3 or just raw controlled area
        raise NotImplementedError
    
    #TODO: optional: make a function that calls an llm api to get a move and see how it does

    @override
    def get_move(self, game : Game, opener:bool = False) -> Move:#TODO:
        assert self.depth is not None
        return self.minimax(0, self.depth, game.board )[1]


    def minimax(self, depth:int, max_depth:int, board:Board) -> tuple[int, Move]: #TODO: (this is the recursive one)
        # if depth%2 == 0: max; else: min (or something like that) 
        # This is just raw minimax, we can add a different agent for alpha-beta if there is time
        # for move in board.enumerate_moves(self): min/max of minimax(depth-1, board.copy.move(move))
        raise NotImplementedError

    @override
    def player_type(self) -> str:
        return "Minimax (Depth:" + str(self.depth) + ")"




"""
wc = Piece(Color.WHITE, PieceType.CAPSTONE)
wf = Piece(Color.WHITE, PieceType.FLATSTONE)
ws = Piece(Color.WHITE, PieceType.STANDINGSTONE)
bc = Piece(Color.BLACK, PieceType.CAPSTONE)
bf = Piece(Color.BLACK, PieceType.FLATSTONE)
bs = Piece(Color.BLACK, PieceType.STANDINGSTONE)



grid =  [[[wf],[],[ bf, wc]],
         [[wf, bs],[wf, wf, wf, wf, bf],[]],
         [[],[bc],[wf,wf,wf,bf,bf,bc]]]

board = Board(3,grid)
player = RandomPlayer(Color.WHITE, 3, 1)

game = Game(board = board)

game.board.display()
move = Move((2,2),Direction.LEFT, 1, [1])
_=game.board.move(move,player)
print(move.to_ptn())
game.board.display()
for _ in range(10):
    move = player.get_move(game)
    _=game.board.move(move,player)
    print(move.to_ptn())
    game.board.display()
"""

for i in range(100):
    game = Game(RandomPlayer(), RandomPlayer())
    print("Normal stones: ", game.current_player.normal_stones, " Capstones: ", game.current_player.capstones)
    game.play(True)

