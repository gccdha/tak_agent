from copy import copy, deepcopy
from enum import Enum
import functools
from math import inf
from operator import itemgetter
from queue import PriorityQueue
import random
from typing import override
import cProfile
import pstats


#number of stones a player gets based on board size
CAPSTONES = {3:0, 4:0, 5:1, 6:1, 7:2, 8:2}
NORMAL_STONES = {3:10, 4:15, 5:21, 6:30, 7:40, 8:50}

#default depth for minimax
DEPTH = 3
MINIMAX_DECAY = 1
ALPHA_BETA = True

#ANSI color escapes
B_ON_W = "\033[30;107m"
W_ON_B = "\033[97;40m"
RESET = "\033[0m"

#max width of board (in characters)
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

DIRECTIONS = list(Direction)


# General purpose menu that takes a dictionary as input, list the keys as options and returns the corresponding entry
# while checking for invalid input.
def menu(params, message: str | None = None):                                               # pyright: ignore[reportUnknownParameterType, reportMissingParameterType]
    keys = list(params.keys())                                                          # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType, reportUnknownArgumentType]
    numkeys= len(keys)                                                                        # pyright: ignore[reportUnknownArgumentType]
    while True:
        if message is not None:
            print(message)
        else:
            print("Choose one of the following:")
        
        #print options
        for i,p in enumerate(keys):                                                                # pyright: ignore[reportUnknownVariableType, reportUnknownArgumentType]
            print(f"{i}) {p}")
        
        #get and validate input. repeat until input is valid
        try:
            choice : int = int(input())
        except ValueError:
            print("ERROR: Please enter a number")
        else:
            if choice in range(0, numkeys):
                return params[keys[choice]]                                                        # pyright: ignore[reportUnknownVariableType]
            else:
                print(f"ERROR: Please enter a number between 0 and {numkeys-1} (inclusive)")

# Menu specifically for getting the sequence of drops. (WARN: doesn't check if the drops make sense! 
# It is up to the user to ensure that the drops are possible for the piece they want to move)
def drop_menu() -> list[int]: #TODO Make this way better, with its own ui and validation
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
                case 0: print("ERROR: Please enter a number greater than 0")
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

    if distance == 0: #handle the case of a single capstone seperately
        if not hard and pickup == 1 and capstone:
            return [[1]] 
    else:
        return gd_cached(pickup,capstone, distance-1,  hard)
    return []

#We can cache the output of this since there are a limited number of possible drops
@functools.cache
def gd_cached(n:int, capstone:bool, dist:int,hard:bool):
    output: list[list[int]] = []
    gd_helper(n,capstone,dist,hard,output,[])
    return output

# Recursively find all possible drops for a given pickup size, n
def gd_helper(n : int, capstone:bool, dist: int, hard:bool, output:list[list[int]], drops: list[int]):
    if n == 0: #if we run out of stones, add the path we used to get here
        output.append(drops.copy())
        return
    elif dist == 0: #if we reach a wall drop all remaining stones (and deal with case where we can squash a standing stone)
        if not hard and capstone and n>1:
            output.append(drops+[n-1, 1])
        output.append(drops+[n])
        return

    #Recurse for every possible amount of stones that could have been dropped
    for i in range(1,n+1):
        drops.append(i)
        gd_helper(n-i, capstone, dist-1, hard, output, drops)
        _=drops.pop() # allows us to use append instead of concat which ends up with less copying



class Piece:
    __slots__ = ("color", "piece")

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
    __slots__ = ("square", "direction", "count", "drops", "stone", "flatten")
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
        self.flatten: bool = False

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
                #so it is unambiguous to just concat them all together
                drops = "".join(map(str, self.drops)) if self.drops is not None else ""

            #optional mark for flattening, but helps when trying to reverse moves and debug
            if self.flatten:
                flatten = "*"
            else:
                flatten =  ""

            return count + square + dir + drops + flatten


#for use with the hashing for the board. This gives a way to do moves that can be standardized under rotation
class MoveWrapper:
    __slots__ = ("move", "index", "direction")
    def __init__(self,
                 move: Move,
                 index: int,
                 direction: int|None
                 ):
        self.move: Move = move
        self.index:int  = index
        self.direction: int|None = direction


class Game:
    def __init__(self, 
                    p1 : "Player | None" = None,
                    p2 : "Player | None" = None,
                    board_size : int | None = 5,
                    komi : float | None = 0,
                    p1_depth : int = DEPTH,
                    p2_depth : int = DEPTH,
                    board : "Board| None" = None,
                    display_game : bool = False
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
        self.display_game: bool = display_game
        self.result_string: str = ""
        self.turn_number : int = 1
        self.moves : list[Move] = []


    # Main loop of the game
    def play(self):
        if self.display_game: self.display()
        # self.opener() #TODO: make minimax work with opener
        winner = self.winner()
        while winner is None:
            if self.display_game: 
                self.display()

            self.turn()
            winner = self.winner()

        if self.display_game:
            print("Game is over!")
            if not winner:
                print("Tie")
            else: print("Winner: Player ",winner)
            self.board.display()

    def display(self):
        #print the turn number, which player's turn it is and what the last move was
        print("="*TERM_WIDTH,"\nTurn ", self.turn_number, "  Current player:", self.current_player.id,"  Previous move: ", self.moves[-1].to_ptn() if self.moves else "n/a")
        #print the board
        self.board.display()
        #print each player, their pieces, their color, and their strategy
        self.current_player.display()
        self.current_opponent.display() 

    #Have each player play a stone as the other player (see self.turn())
    def opener(self):
        self.turn(True)
        if self.display_game: self.display()
        self.turn(True)

    
    #Get a turn from a player and swap players
    def turn(self, opener:bool = False):
        while True: # loop until a valid move is given
            player = self.current_player if not opener else self.current_opponent
            move: Move = self.current_player.get_move(self, opener)
            if self.board.move(move,player): 
                self.moves.append(move)
                break

        #swap players and increase turn num if both have gone
        self.current_player, self.current_opponent = self.current_opponent, self.current_player
        if self.current_player.id == 1:
            self.turn_number += 1


    #Check all win conditions. Return id of winner, 0 for tie, None for not over
    def winner(self) -> int | None: 
        roads = self.board.is_road()
        winner: int | None = None
        result = ""
        # if both players get a road in the same turn, the current_player (one who did it) should win
        if roads[self.current_player.piece_color]:
            if self.display_game: print("Road win!")
            winner = self.current_player.id
            result = "R"

        elif roads[self.current_opponent.piece_color]:
            if self.display_game: print("Road win!")
            winner = self.current_opponent.id
            result = "R"

        elif (self.board.open_spaces() == 0 #out of stones or full board
              or (self.current_player.capstones + self.current_player.normal_stones) == 0
              or (self.current_opponent.capstones + self.current_opponent.normal_stones) == 0):
            result = "F"
            if self.display_game: print("Flat win!")
            counts = self.board.flat_count()
            cur_score = counts[self.current_player.piece_color] + self.current_player.komi
            opp_score = counts[self.current_opponent.piece_color] + self.current_opponent.komi
            if cur_score == opp_score: # only way to tie
                self.result_string = "1/2-1/2"
                return 0
            if cur_score > opp_score:
                winner = self.current_player.id
            else:
                winner = self.current_opponent.id
        if winner == 1:
            self.result_string = result + "-0"
        elif winner == 2:
            self.result_string = "0-" + result
        return winner

    #output the ptn string for the game
    def move_string(self) -> str:
        output = ""
        for i,move in enumerate(self.moves):
            if i%2 == 0:
                output += str((i+2)//2) + ". " + move.to_ptn()
            else:
                output += " " + move.to_ptn() + "\n"

        return output + " " + self.result_string



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
            raise ValueError("None stack while getting stack for move")

        # for placements
        if move.direction is None:
            if move.stone == PieceType.CAPSTONE:
                player.capstones -= 1
            else:
                player.normal_stones -=1

            if move.stone is None:
                raise ValueError("Stone not specified for placement. Move must have either direction or stone.")

            stack.append(Piece(player.piece_color, move.stone))

        # for movements
        else:
            if move.drops is None:
                raise ValueError("Trying to move with None drops")
            pickup = stack[-move.count:]
            assert move.count <= len(stack)
            del stack[-move.count:] #TODO: make sure this does what you think it does

            offset = 1
            while len(pickup) != 0:
                # print("Offset: ", offset)
                # print("Drops: ", move.drops)
                # print("pickup: ", pickup)
                adj_stack = self.get_stack(self.offset_tile(move.square, move.direction, offset))
                if adj_stack is None:
                    raise ValueError("None stack during drops")

                if adj_stack and adj_stack[-1].piece == PieceType.STANDINGSTONE:
                    if pickup[0].piece != PieceType.CAPSTONE:
                        raise ValueError("Attempted to flatten standing stone with non-capstone")
                    adj_stack[-1].piece = PieceType.FLATSTONE
                    move.flatten = True

                # print("extending with: ",pickup[0:move.drops[offset-1]]) 
                adj_stack.extend(pickup[0:move.drops[offset-1]])

                if move.drops[offset-1] < len(pickup):
                    pickup = pickup[move.drops[offset-1]:]
                elif move.drops[offset-1] == len(pickup):
                    pickup = []

                offset += 1 

        return True


    def unmove(self, move : Move, player: "Player"):

        stack = self.get_stack(move.square)
        if stack is None:
            raise ValueError("None stack while geting stack for unmove")

        #For Placements
        if move.direction is None:
            if move.stone == PieceType.CAPSTONE:
                player.capstones += 1 
            else:
                player.normal_stones += 1
            
            if move.stone is None:
                raise ValueError("Stone not specified for un-placement. Move must have either direction or stone.")

            # make sure that the stone is the correct one
            assert stack.pop().piece == move.stone

        #For movements
        else:
            if move.drops is None:
                raise ValueError("Trying to unmove with None drops")
            
            pickup: list[Piece] = []

            
            offset = 1
            for drop in move.drops:
                adj_stack = self.get_stack(self.offset_tile(move.square, move.direction, offset))
                if adj_stack is None:
                    raise ValueError("None stack during undrops")

                dropped = adj_stack[-drop:]

                # dropped.reverse()

                pickup.extend(dropped)

                del adj_stack[-drop:]

                #WARN: this only works if the move has already been used, because that is when
                #move.flatten is set
                if move.flatten and len(dropped) == 1 and dropped[0].piece == PieceType.CAPSTONE:
                    adj_stack[-1].piece = PieceType.STANDINGSTONE
                    move.flatten = False #is this a good thing to do? idk

                offset += 1 

            if len(pickup) != move.count:
                raise ValueError("Number of unpickups based on drops is different from move.count")

            stack.extend(pickup)



            




    
    # return true if a move can be made and false if it can't be
    def test_move(self, move:Move, player: "Player") -> bool: #TODO: don't think this works 
        # (should replace this in the future with just not allowing bad input)
        
        moves = self.enumerate_moves(player)


        if move in moves:
            return True
        else:
            return False

    #return the number of spaces that don't have any piece on them 
    def open_spaces(self) -> int: 
        return sum(1 for x in self.grid for y in x if not y)

    #return a dict with the color of the player as key and the flat count as the value
    def flat_count(self):
        black = sum(1 for x in self.grid for y in x if y and y[-1].color == Color.BLACK and y[-1].piece == PieceType.FLATSTONE)
        white = sum(1 for x in self.grid for y in x if y and y[-1].color == Color.WHITE and y[-1].piece == PieceType.FLATSTONE)
        return {Color.BLACK:black, Color.WHITE:white}

    # return true if there is a roard and false otherwise.
    def is_road(self) :
        #(use dfs from two sides to try to find the other side)
        #(there may be a way to do it incrementally, like store old dfs and use them instead
        #of recalculating every time but idk)

        ub =  self.dfs(Direction.UP, Color.BLACK, (None, 0))
        uw =   self.dfs(Direction.UP, Color.WHITE, (None, 0))
        lb = self.dfs(Direction.LEFT, Color.BLACK, (self.size-1, None))
        lw =   self.dfs(Direction.LEFT, Color.WHITE, (self.size-1, None))

        return {Color.BLACK:ub or lb, Color.WHITE:uw or lw}

    #TODO: test this
    def dfs(self, node: Direction, col: Color, goal:tuple[int|None, int|None] = (None, None)) -> bool:

        stack: list[tuple[int, int]] = []
        visited : set[tuple[int,int]] = set()

        def valid_tile(a:int,b:int) -> bool:
            stk = self.get_stack((a,b))
            assert stk is not None

            return bool(stk) and stk[-1].piece != PieceType.STANDINGSTONE and stk[-1].color == col

        match node:
            case Direction.UP:    stack = [(x, self.size-1) for x in range(0,self.size) if valid_tile(x,self.size-1)] 
            case Direction.RIGHT: stack = [(self.size - 1, y) for y in range(0,self.size) if valid_tile(self.size -1, y)]
            case Direction.DOWN:  stack = [(x, 0) for x in range(0,self.size) if valid_tile(x,0)] 
            case Direction.LEFT:  stack = [(0,y) for y in range(0,self.size) if valid_tile(0,y)] 
        
        while stack:
            n = stack.pop()
            visited.add(n)

            # return true if the traversal reaches the goal row/column
            if n[1] == goal[1] or n[0] == goal[0]:
                return True

            # add neighbors to stack if they havn't been visited
            for i in range(4):
                neighbor = self.offset_tile(n, DIRECTIONS[i])
                if max(neighbor) >= self.size or min(neighbor) < 0: continue
                tile = self.get_stack(neighbor)
                if tile: 
                    p = tile[-1]
                    if p.color == col and p.piece != PieceType.STANDINGSTONE and neighbor not in visited:
                        stack.append(neighbor)

        # if the stack is empty after trying to add stuff to it, no path exists 
        return False

    #pretty print the board
    def display(self) -> None:
        global_max = max(max(len(z) for x in self.grid for z in x), 10)  #max height of any stack
        p = min(global_max,((TERM_WIDTH)-1)//self.size-1) # number of chars of padding on each side of stack characters
        top = " ╭"+ ("─"*(2*p+1)+"┬")*(self.size-1) +"─"*(2*p+1)+"╮"
        mid = " ├"+ ("─"*(2*p+1)+"┼")*(self.size-1) +"─"*(2*p+1)+"┤"
        bot = " ╰"+ ("─"*(2*p+1)+"┴")*(self.size-1) +"─"*(2*p+1)+"╯"
        letters = " "
        for i in range(self.size):
            letters = letters + " "*(p+1)+chr(97+i)+" "*(p) #letter label for bottom


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


    #return a list of all valid moves for the player in current position
    def enumerate_moves(self, player : "Player", opener:bool = False) -> list[Move]:
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
                            dir = DIRECTIONS[i]
                            possible_drops = generate_drops(self, square, dir, pickup)
                            for drops in possible_drops:
                                moves.append(Move(square,dir,pickup, drops)) 
        return moves

    # gives the tile "times" number of tiles in "dir" direction
    #TODO: doesn't need to be a method of board..
    #PERF: one of the most called functions
    def offset_tile(self, tile:tuple[int,int], dir: Direction,  times:int = 1) -> tuple[int,int]:
        match dir:
            case Direction.UP:    return (tile[0], tile[1]+times)
            case Direction.RIGHT: return (tile[0]+times, tile[1])
            case Direction.DOWN:  return (tile[0], tile[1]-times)
            case Direction.LEFT:  return (tile[0]-times, tile[1])

    # Returns the stack on the given tile. Returns None if the tile is outside the board area.
    #PERF: this is the most called function in the program...
    def get_stack(self, tile : tuple[int, int]) -> list[Piece] | None:
        #NOTE: Tile tuple has ints in range [0,size-1] inclusive
        if max(tile) >= self.size or min(tile) < 0: return None
        else: return self.grid[self.size - 1 - tile[1]][tile[0]]
    
    #returns a tuple in the form (type of wall (None for edge of board),  distance to wall)
    def distance_to_wall(self,tile:tuple[int,int], dir : Direction) -> tuple[PieceType | None, int]:
        for i in range(0,self.size):
            stack = self.get_stack(self.offset_tile(tile, dir,i+1))
            if stack is None: return (None, i) # wall
            if stack:
                match stack[-1].piece:
                    case PieceType.FLATSTONE: pass
                    case x: return (x, i)
        return (None, 0)


    # return the location of the starting corner for the hash
    def starting_corner(self) -> tuple[int, int]:
        s = self.size-1
        corners = [(0,0), (0,s), (s,0), (s,s)]

        max = -inf
        max_corner = (0,0)

        for corner in corners:
            stack = self.get_stack(corner)
            assert stack is not None

            if not stack:
                continue
            
            id:int = 0

            #every index in the stack gets a unique power of 2
            for i,piece in enumerate(stack):
                c = piece.color
                if c == Color.WHITE:
                    id += 2**i

            # a 1 is added to prevent things with leading zeroes, and a 2 bit code 
            # representing the top piece type is added
            id = (id+2**len(stack))*4+stack[-1].piece.value
            
            # find the corner with the highest number (this is an arbitrary metric but uniqeuly
            # relates to each possible stack which is all that matters for selecting the same corner)
            if id > max:
                max_corner = corner

        return max_corner


    # return a hash of the board object that is invariant under rotation
    # output tuple of form (hash for board, (move's square's index in spiral, Direction((move direction-direction clockwise from corner)%4)))
    def zhash(self, move : Move|None) -> tuple[str,MoveWrapper|None]:

        #get the enum number for the direction that is clockwise from this corner 
        start_dir = 0
        s = self.size-1
        corner = self.starting_corner()
        if   corner == (0,0): start_dir = 0 
        elif corner == (0,s): start_dir = 1 
        elif corner == (s,s): start_dir = 2 
        elif corner == (s,0): start_dir = 3
        else: raise Exception("invalid corner for hash")

        #offset the corner one space off the board away from the clockwise direction
        tile = self.offset_tile(corner, Direction((start_dir+2)%4))
        output:str = ""
        dir = start_dir
        index = 0
        move_index = -1
        # go all the way across the board spiraling clockwise until center
        for i in range(self.size*2, 1, -1):
            for _ in range(0,i//2):
                tile = self.offset_tile(tile, Direction(dir))
                if move is not None and move.square == tile:
                    move_index = index
                # print(tile)
                stack = self.get_stack(tile)
                assert stack is not None

                index+=1
                if not stack: 
                    output+="0"

                    continue
                for piece in stack:
                    output+=piece.color.name[0]
                output+=stack[-1].piece.name[0]

            dir = (dir+1)%4
                 
        if move is None:
            return (output, None)

        assert move_index >= 0
        out_move = copy(move)
        if move.direction is not None:
            relative_direction = (move.direction.value - start_dir)%4
        else:
            relative_direction = None

        return (output, MoveWrapper(out_move, move_index, relative_direction))

    def decode_move(self, move: MoveWrapper) -> Move:
        #get the enum number for the direction that is clockwise from this corner 
        start_dir = 0
        s = self.size-1
        corner = self.starting_corner()
        if   corner == (0,0): start_dir = 0 
        elif corner == (0,s): start_dir = 1 
        elif corner == (s,s): start_dir = 2 
        elif corner == (s,0): start_dir = 3
        else: raise Exception("invalid corner for decoding move")

        #offset the corner one space off the board away from the clockwise direction
        tile = self.offset_tile(corner, Direction((start_dir+2)%4))
        dir = start_dir
        index = 0

        # go all the way across the board spiraling clockwise until we find the tile
        for i in range(self.size*2, 1, -1):
            for _ in range(0,i//2):
                tile = self.offset_tile(tile, Direction(dir))
                # print(move.index," ", index)
                if move.index == index:
                    out_move = copy(move.move)
                    out_move.square = tile
                    out_move.direction = Direction((start_dir + move.direction)%4) if move.direction is not None else None 
                    return out_move
                index+=1
            dir = (dir+1)%4

        raise Exception("made it to the end of decode function without finding the tile")
                 
#base player class
class Player:
    def __init__(self,
                 piece_color : Color = Color.BLACK,
                 normal_stones : int = 0,
                 capstones : int = 0, komi : float = 0,
                 depth: int = DEPTH,
                 id : int = 0,
                 ab : bool = ALPHA_BETA
                 ):
        self.piece_color: Color = piece_color
        self.komi: float = komi
        self.normal_stones: int = normal_stones
        self.capstones: int = capstones
        self.depth: int = depth
        self.id: int = id
        self.ab: bool = ab
        self.evaluationdict: dict[str,float] = {}

    def get_move(self, game : Game, opener:bool = False) -> "Move":   # pyright: ignore[reportUnusedParameter]
        raise NotImplementedError

    def display(self) -> None:
        if self.piece_color == Color.BLACK:
            color = W_ON_B
        else:
            color = B_ON_W
        strat = self.player_type()
        print(f"{color}Player:{self.id}  Strategy:{strat}, Normal Stones: {self.normal_stones}  Capstones: {self.capstones}{RESET}")

    def player_type(self) ->str:
        raise NotImplementedError



class HumanPlayer(Player):
    @override
    #get move from player by asking for each part
    def get_move(self, game: Game, opener:bool = False) -> Move:
        #TODO:: add checking for each part. Add option during start of game to use PTN

        if opener: print("OPENER: choose a square to place one of your opponent's flatstones on!")

        #Get square
        rows = {chr(ord('A')+x):x for x in range(0,game.board.size)}
        cols = {str(x):x for x in range(0,game.board.size)}
        square: tuple[int, int] = ( 
            menu(rows, "Choose a column:"),
            menu( cols, "Choose a row:")
        )

        if opener: return Move(square, stone = PieceType.FLATSTONE)

        stack = game.board.get_stack(square)
        if not stack:  #choose piece for placement
            piece = menu({"flatstone":PieceType.FLATSTONE, 
                          "standing stone":PieceType.STANDINGSTONE,
                          "capstone stone":PieceType.CAPSTONE}, "What kind of piece would you like to place?:")
            return Move(square,stone = piece)

        else: #movement

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
    #select random move from list of all possible moves
    def get_move(self, game: Game, opener:bool = False) -> Move:
        moves = game.board.enumerate_moves(self, opener)
        return random.choice(moves)

    @override
    def player_type(self) -> str:
        return "Random"



class MinimaxPlayer(Player):    

    @override
    def get_move(self, game : Game, opener:bool = False) -> Move:#TODO:
        assert self.depth is not None
        self.nodes: list[float]  = [0.0 for _ in range(0,self.depth+1)]
        self.boarddict: dict[str,list[MoveWrapper]] = dict()
        v, move = self.minimax(game.board,self.depth,game.current_opponent, True)
        # v,move = self.iterative_deepening(game.board, game.current_opponent)
        # print("move: ", move.to_ptn(), " value: ", v)
        # print("Nodes: ", self.nodes)
        # prop = []
        # for i in range(1, len(self.nodes)):
            # prop.append(self.nodes[i] / self.nodes[i-1])
        # print("Proportions: ",  prop)
        return move

    #TODO:  There are still some bugs (3 look ahead looses to 2 lookahead on a 3x3 board?)
    # also would be a good idea to introduce some randomness if there are multiple equally good moves
    # also should probably disincentivise making super tall stacks but idk...
    # absolutely need to optimize much better (and do alpha-beta...)
    # find a way to make the agent not give up (currently the slight penalty for longer games means that 
    # if all paths would lead to the opponent winning based on the agent's play, it will end the game asap,
    # but it should instead try to prolong the game to see if the the opponent makes a mistake)
    def minimax(self, board:Board, max_depth:int, op:Player, own_turn:bool, alpha: float|None = None, beta: float|None = None) -> tuple[float, Move]: #TODO: There is so much wrong with this but it works...
        # This is just raw minimax, we can add a different agent for alpha-beta if there is time
        # for move in board.enumerate_moves(self): min/max of minimax(depth-1, board.copy.move(move))

        # self.nodes[self.depth - max_depth] += 1

        #check if game is over. if so, return evaluation of current board
        roads = board.is_road()
        if (roads[self.piece_color] 
            or roads[op.piece_color]
            or self.capstones + self.normal_stones == 0 
            or op.capstones + op.normal_stones == 0
            or board.open_spaces() == 0
            or max_depth == 0):
            return (self.evaluate_board(board, 0, own_turn), Move((-1,-1))) #TODO: Komi
 
        player = self if own_turn else op
        possible_moves = self.get_possible_moves(board, player)

        best_value = float('-inf') if own_turn else float('inf')
        best_move: tuple[float,Move] = (best_value,possible_moves[0])

        for move in possible_moves: 
            # we move, recurse and unmove. This is much faster than copying each time
            _=board.move(move, player)
            v,_ = self.minimax(board, max_depth-1, op, not own_turn, alpha, beta)
            board.unmove(move, player)

            if self.depth == max_depth:
                print(move.to_ptn(), ":", v)
                b,m = board.zhash(move)
                print("hash: ", b, "\n Move: ", m.move.to_ptn(), " index: ", m.index, " dir: ", m.direction)

            v*=MINIMAX_DECAY

            min_max = max if own_turn else min
            if v == best_value:
                b,p = board.zhash(move)
                assert p is not None
                self.boarddict[b].append(p)

            elif min_max(v,  best_value) == v:
                b,p = board.zhash(move)
                assert p is not None
                self.boarddict[b] = [p]
                best_move =(v,move)
                best_value = v



            if alpha is not None and beta is not None:
                if own_turn:
                    if best_value >= beta:
                        # print("Pruning")
                        break
                    alpha = max(alpha, best_value)
                else:
                    if best_value <= alpha:
                        # print("Pruning")
                        break
                    beta = min(beta, best_value)
            
        # can also return random choice from best_moves later, but determinism is good for testing
        assert best_move[0] == best_value
        return best_move 


            
    def get_possible_moves(self, board:Board, player:Player) -> list[Move]:
        #TODO: should probably use priority queue or something (?)
        random = board.enumerate_moves(player)
        b,_=board.zhash(None) 
        best_moves = self.boarddict.get(b, [])
        best_moves = [board.decode_move(x) for x in best_moves]
        best_moves.extend(random)

        return list(dict.fromkeys(best_moves))
        
    #evaluate the board based on what I think is important
    def evaluate_board(self, board:Board, komi:float, own_turn:bool, ) -> float:
        b,_ = board.zhash(None)
        score = self.evaluationdict.get(b)
        if score is not None:
            return score

        op_color = Color((self.piece_color.value + 1)%2)
        flat_count = board.flat_count() #dict color  -> int
        flat_score = flat_count[self.piece_color]-flat_count[op_color]
        
        #TODO: test different values for roads (maybe make based on board size?)
        road = board.is_road()
        road_score = 0
        if road[self.piece_color]:
            road_score += 100
        if road[op_color]:
            road_score -= 100
            if road_score == 0: # if we make the move we win otherwise we lose
                road_score += -100 if not own_turn else 100 

        # Ideas: Hard caps, discourage stacks above carry limit, add small bonus for walls
        # add small punishment every turn to force offensive play, add bonus for the number of 
        # posible moves (and punish giving op more move options)
         
        score =  flat_score if road_score == 0 else road_score
        self.evaluationdict[b] = score
        return score

    #TODO: iterative deepening

    def iterative_deepening(self, board:Board, op:Player) -> tuple[float, Move]:
        output = self.minimax(game.board, 1, op, True)
        max_level = 1

        print(f"tring range from 2 to {self.depth+1}")
        for i in range(2,self.depth+1):
            output = self.minimax(game.board, i, op, True, -inf if self.ab else None, inf if self.ab else None)
            max_level = i
            print("level: ", max_level)
        return output

        
        # try:
        #     print(f"tring range from 2 to {self.depth+1}")
        #     for i in range(2,self.depth+1):
        #         print("i")
        #         output = self.minimax(game.board, i, op, True)
        #         max_level = i
        #         print("level: ", max_level)
        # except KeyboardInterrupt:
        #     print(f"Interupted minimax! Max level: {max_level}")
        # except:
        #     print("OTHER ERROR")
        # finally:
        #     return output

            
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
"""
def run():
    for size in range (3,4):
        for k in range(0,1):
            komi = k/2
            wins1 = 0
            wins2 = 0
            ties = 0
            games = 10000
            for _ in range(games):
                game = Game(RandomPlayer(), RandomPlayer(), display_game=False, board_size=size, komi=komi)
                # print("Normal stones: ", game.current_player.normal_stones, " Capstones: ", game.current_player.capstones)
                game.play()
                #print(game.result_string)
                match game.winner():
                    case 1: wins1+=1 
                    case 2: wins2+=1
                    case 0: ties+=1
                    case _: print("GAME ENDED WITH NONE")

            print(f"{games} games, {size}x{size} board, {komi} komi:\nP1: {wins1}, P2: {wins2}, Ties: {ties}")
"""




"""
if __name__ == "__main__":
    profiler = cProfile.Profile()
    profiler.enable()

    run()

    profiler.disable()
    stats = pstats.Stats(profiler)
    stats.sort_stats("ncalls").print_stats()
"""

for i in range(10, 0):
    print(i)


game = Game(MinimaxPlayer(), MinimaxPlayer(), 3, 0, DEPTH, DEPTH, None, True)
try:
    profiler = cProfile.Profile()
    profiler.enable()
    game.play()
    profiler.disable()
    stats = pstats.Stats(profiler)
    stats.sort_stats("cumtime").print_stats()

finally:
    print(game.move_string())    

"""
TODO:
1. Last move is not counted or printed when using move_string()
2. 

AFTER TURNED IN:
- make a function that calls an llm api to get a move and see how it does
"""




"""
    STATS:
    27 min 1 sec for a 38 ply game of 2 minimax agents at depth 5 on 3x3
    3  min 4 sec for a 34 ply game of 2 minimax agents at depth 4 on 3x3   -> (improved dfs gives 2:45)
    91 min +     for a 31 ply game of 2 depth 4 agents on 4x4 (not complete)
"""


"""
    Idea: make a hash that scores each corner. It then starts hashing from that corner and goes in a 
spiral arround the board. This ensures that if two boards are the same rotationally, they will
be hashed the same way. To represent the square of the move, just use an index into the spiral.
To represent the direction of a move, we can just say which axis is should be moved in and if it 
should be moved towards or away from the starting tile of the spiral

first: implemet hashing algorithm
second: imlement move "hashing"
third: implement retrieving move from move "hash"



def board.largest_corner() -> (int, int) => returns index of largest scored corner of any board 
def board.zhash(move: Move) -> (str, str) => returns rotationally invariant hash of board AND move 
def board.decode_move(move: str) -> Move => returns real move from "hashed" move based on board


uses: we can put scores for each board hash in a dict to cache the evaluation function
we can also hash board positions with their list of best moves for minimax iterative deepening

To hash stacks of pieces, we start with a leading 1 to mark the beginnig, then 0 for black and 1 for white, end with 00 if flatstone, 01 if standing and 10 if cap

"""
