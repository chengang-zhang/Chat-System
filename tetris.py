import pygame
import random
import json
from chat_utils import *
from threading import Thread
import pickle as pk

class Piece(object):  # class for a piece in tetris, makes coding easier
    def __init__(self, x, y, shape):
        self.x = x
        self.y = y
        self.shape = shape
        self.color = shape_colors[shapes.index(shape)]
        self.rotation = 0


class Tetris: #a class to run the whole game
    
    def __init__(self,my_socket, me, opp):
        pygame.font.init()
        self.s_width = 800
        self.s_height = 700
        self.play_width = 300
        self.play_height = 600
        self.block_size = 30

        self.my_socket = my_socket # the player's socket 
        self.me = me # player's name (used for displaying and keeping track of score)
        self.opp = opp # opp if there is any (also used for displaying and keeping track of score)
        if len(self.opp) > 1:
            self.multiplayer = True
        else:
            self.multiplayer = False
        self.score = 0 #data member score
        self.opp_score = 0 # data member opponent score
        self.old_scores = None # a dictionary to hold old scores (a function will be automatically called to update this data member when the game starts)

        self.top_left_x = (self.s_width - self.play_width) //2
        self.top_left_y = self.s_height - self.play_height

        self.my_old_record = 0
        self.record_score = 0
        self.RECORDRECORDSCORE = 0

        # SHAPES

        S = [['.....',
            '.....',
            '..00.',
            '.00..',
            '.....'],
            ['.....',
            '..0..',
            '..00.',
            '...0.',
            '.....']]

        Z = [['.....',
            '.....',
            '.00..',
            '..00.',
            '.....'],
            ['.....',
            '..0..',
            '.00..',
            '.0...',
            '.....']]

        I = [['..0..',
            '..0..',
            '..0..',
            '..0..',
            '.....'],
            ['.....',
            '0000.',
            '.....',
            '.....',
            '.....']]

        O = [['.....',
            '.....',
            '.00..',
            '.00..',
            '.....']]

        J = [['.....',
            '.0...',
            '.000.',
            '.....',
            '.....'],
            ['.....',
            '..00.',
            '..0..',
            '..0..',
            '.....'],
            ['.....',
            '.....',
            '.000.',
            '...0.',
            '.....'],
            ['.....',
            '..0..',
            '..0..',
            '.00..',
            '.....']]

        L = [['.....',
            '...0.',
            '.000.',
            '.....',
            '.....'],
            ['.....',
            '..0..',
            '..0..',
            '..00.',
            '.....'],
            ['.....',
            '.....',
            '.000.',
            '.0...',
            '.....'],
            ['.....',
            '.00..',
            '..0..',
            '..0..',
            '.....']]

        T = [['.....',
            '..0..',
            '.000.',
            '.....',
            '.....'],
            ['.....',
            '..0..',
            '..00.',
            '..0..',
            '.....'],
            ['.....',
            '.....',
            '.000.',
            '..0..',
            '.....'],
            ['.....',
            '..0..',
            '.00..',
            '..0..',
            '.....']]

        global shapes # make shapes a global varibale so the Piece class can access it
        shapes = [S, Z, I, O, J, L, T]
        global shape_colors # make shape_colors a global varibale so the Piece class can access it
        shape_colors = [(0, 255, 0), (255, 0, 0), (0, 255, 255), (255, 255, 0), (255, 165, 0), (0, 0, 255), (128, 0, 128)]
            
    def create_game_grid(self,locked_pos={}):
        grid = [[(0,0,0) for _ in range(10)] for _ in range(20)]

        for i in range(len(grid)):
            for j in range(len(grid[i])):
                if (j, i) in locked_pos:
                    c = locked_pos[(j,i)]
                    grid[i][j] = c
        return grid 

    def convert_shape(self,shape):
        positions = []
        format = shape.shape[shape.rotation % len(shape.shape)]

        for i, line in enumerate(format):
            row = list(line)
            for j, column in enumerate(row):
                if column == '0':
                    positions.append((shape.x + j, shape.y + i))

        for i, pos in enumerate(positions):
            positions[i] = (pos[0] - 2, pos[1] - 4)

        return positions

    def is_valid_space(self,shape, grid):
        '''checks if the space the player is trying to move a piece into is valid or not'''
        accepted_pos = [[(j, i) for j in range(10) if grid[i][j] == (0,0,0)] for i in range(20)]
        accepted_pos = [j for sub in accepted_pos for j in sub]

        formatted = self.convert_shape(shape)

        for pos in formatted:
            if pos not in accepted_pos:
                if pos[1] > -1:
                    return False
        return True

    def check_top(self,positions):
        '''checks if the user has reached the top of the playing board'''
        for pos in positions:
            x, y = pos
            if y < 1:
                return True
        return False

    def hold_shape(self):
        '''A function to allow player to hold a shape for feature use (hopefully implemented in the future)'''
        pass

    def get_shape(self):
        '''function to retrive a piece'''
        return Piece(5, 0, random.choice(shapes))

    def pop_up_text(self,board, text, size, color):
        '''displays text in the middle of the game screen'''
        font = pygame.font.SysFont("Apple SD Gothic Neo", size, bold=True)
        label = font.render(text, 1, color)

        board.blit(label, (self.top_left_x + self.play_width /2 - (label.get_width()/2), self.top_left_y + self.play_height/2 - label.get_height()/2))

    def draw_grid(self,board, grid):
        '''draws the grid on the board, allows user to see where the piece will drop if in it's current y position'''
        x_pos = self.top_left_x
        y_pos = self.top_left_y

        for i in range(len(grid)):
            pygame.draw.line(board, (128,128,128), (x_pos, y_pos + i*self.block_size), (x_pos+self.play_width, y_pos+ i*self.block_size))
            for j in range(len(grid[i])):
                pygame.draw.line(board, (128, 128, 128), (x_pos + j*self.block_size, y_pos),(x_pos + j*self.block_size, y_pos + self.play_height))

    def full_row_complete(self, grid, locked):
        '''when a user gets a full row, this function would be called to remove the whole row'''

        inc = 0
        for i in range(len(grid)-1, -1, -1):
            row = grid[i]
            if (0,0,0) not in row:
                inc += 1
                ind = i
                for j in range(len(row)):
                    try:
                        del locked[(j,i)]
                    except:
                        continue

        if inc > 0:
            for key in sorted(list(locked), key=lambda x: x[1])[::-1]:
                x, y = key
                if y < ind:
                    newKey = (x, y + inc)
                    locked[newKey] = locked.pop(key)

        return inc

    def draw_next_shape(self,shape, board):
        '''creates the next shape for the user to get'''
        font = pygame.font.SysFont("Apple SD Gothic Neo", 30)
        label = font.render("Next Shape:", 1, (255,255,255))

        x_pos = self.top_left_x + self.play_width + 50
        y_pos = self.top_left_y + self.play_height/2 - 100
        format = shape.shape[shape.rotation % len(shape.shape)]

        for i, line in enumerate(format):
            row = list(line)
            for j, column in enumerate(row):
                if column == '0':
                    pygame.draw.rect(board, shape.color, (x_pos + j*self.block_size, y_pos + i*self.block_size, self.block_size, self.block_size), 0)

        board.blit(label, (x_pos + 10, y_pos - 30))

    def dump_score(self,game_score):
        '''updates the player's high score, if the scored something higher than they previously did
        if this is the first time the player is playing, then their current score will be placed into the file'''
        #nscore is current score from game
        #score = self.highest_score() #old high score

        #try updating your score:
        try:
            if self.old_scores[self.me] < self.score:
                self.old_scores[self.me] = self.score
        except:
            self.old_scores[self.me] = self.score


        out_file = open("scores.txt", "wb")
        pk.dump(self.old_scores, out_file)
        out_file.close()


    def highest_score(self):
        '''finds the highest score that was ever scored and who scored it'''
        old = open("scores.txt","rb")
        self.old_scores = pk.load(old)
        old.close()
        #old_scores contains a dictionary of old scores with players names

        #find my score
        try:
            my_old = self.old_scores[self.me]
        except:
            my_old = 0

        self.my_old_record = my_old
        #find old maximum score:
        if len(self.old_scores) == 0:
            high_return = "0"
        else:
            holder_value = 0
            holder_name = None

            for k,v in self.old_scores.items():
                if v > holder_value:
                    holder_name = k
                    holder_value = v
            
            high_name = holder_name
            highest_score = str(holder_value)
            self.RECORDRECORDSCORE = holder_value

            high_return = high_name +" :"+ str(highest_score)
            self.record_score = high_return

        #return high_return, my_old

    def draw_opp_window(self,board_opp):
        '''future use when 2 players can see each others board'''
        pass

    def draw_window(self,board, grid):
        '''function to draw the window, showing the user the game board
        this function also handles showing the user various other things such as
        > the header
        > the current score
        > the opponents score (not functional)
        > the last score
        > the shape held (not implemented)
        > the top score and who scored it'''
        board.fill((0, 0, 0))
        pygame.font.init()

        #display the mode of the game ---------------------#
        font = pygame.font.SysFont("Apple SD Gothic Neo", 60)
        if self.multiplayer:
            label = font.render("2 Player Mode", 1, (255, 255, 255))
        else:
            label = font.render("1 Player Mode", 1, (255, 255, 255))

        board.blit(label, (self.top_left_x + self.play_width / 2 - (label.get_width() / 2), 30))
        #---------------------------------------------------#

        # current score ----------------------------------#
        font = pygame.font.SysFont("Apple SD Gothic Neo", 30)
        label = font.render("You"+': ' + str(self.score), 1, (255,255,255))
        x_pos = self.top_left_x + self.play_width + 50
        y_pos = self.top_left_y + self.play_height/2 - 100
        board.blit(label, (x_pos + 20, y_pos + 160))
        #---------------------------------------------------#

        #opponent score ----------------------------------#
        if self.multiplayer:
            font = pygame.font.SysFont("Apple SD Gothic Neo", 30)
            label = font.render(self.opp+': ' + str(self.opp_score), 1, (255,255,255))
            x_pos = self.top_left_x + self.play_width + 50
            y_pos = self.top_left_y + self.play_height/2 - 70
            board.blit(label, (x_pos + 20, y_pos + 160))
        #---------------------------------------------------#

        # your high score ----------------------------------#
        label = font.render('Your Personal', 1, (255,255,255))
        x_pos = self.top_left_x - 250
        y_pos = self.top_left_y -50
        board.blit(label, (x_pos + 20, y_pos + 160))

        label = font.render('High Score:', 1, (255,255,255))
        x_pos = self.top_left_x - 250
        y_pos = self.top_left_y -10
        board.blit(label, (x_pos + 20, y_pos + 160))

        if self.my_old_record > self.score: # if old record is higher
            label = font.render(str(self.my_old_record), 1, (255,255,255))
            x_pos = self.top_left_x - 250
            y_pos = self.top_left_y + 30
            board.blit(label, (x_pos + 20, y_pos + 160))
        else: # if current score is higher
            label = font.render(str(self.score), 1, (255,255,255))
            x_pos = self.top_left_x - 250
            y_pos = self.top_left_y + 30
            board.blit(label, (x_pos + 20, y_pos + 160))   
        #---------------------------------------------------#

        # overall high score -------------------------------#
        label = font.render('The Record', 1, (255,255,255))
        x_pos = self.top_left_x - 250
        y_pos = self.top_left_y + 150
        board.blit(label, (x_pos + 20, y_pos + 160))

        label = font.render('High Score:', 1, (255,255,255))
        x_pos = self.top_left_x - 250
        y_pos = self.top_left_y + 190
        board.blit(label, (x_pos + 20, y_pos + 160))
        if self.RECORDRECORDSCORE > self.score:
            label = font.render(str(self.record_score), 1, (255,255,255))
            x_pos = self.top_left_x - 250
            y_pos = self.top_left_y + 230
            board.blit(label, (x_pos + 20, y_pos + 160))
        else:
            label = font.render("You:"+str(self.score), 1, (255,255,255))
            x_pos = self.top_left_x - 250
            y_pos = self.top_left_y + 230
            board.blit(label, (x_pos + 20, y_pos + 160))                      
        #---------------------------------------------------#

        for i in range(len(grid)):
            for j in range(len(grid[i])):
                pygame.draw.rect(board, grid[i][j], (
                    self.top_left_x + j*self.block_size, 
                    self.top_left_y + i*self.block_size, 
                    self.block_size, self.block_size), 0)

        pygame.draw.rect(board, (128,128,128), (
            self.top_left_x, 
            self.top_left_y, 
            self.play_width, 
            self.play_height), 5)

        self.draw_grid(board, grid)

    def call_events(self,window,current_piece,grid):
        run = True
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                run = False
                return run
                #pygame.display.quit()

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_q:
                    self.pop_up_text(window, "GAVE UP!", 80, (255,255,255))
                    pygame.display.update()
                    pygame.time.delay(1500)
                    if self.multiplayer:
                        msg = json.dumps({"action":"quit","status":True})
                        mysend(self.my_socket, msg)
                        response = json.loads(myrecv(self.my_socket))
                    run = False
                    self.dump_score(self.score)
                    #pygame.display.quit()
                    #pygame.quit()
                    break
                if event.key == pygame.K_DOWN: #regular down
                    current_piece.y += 1
                    if not(self.is_valid_space(current_piece, grid)):
                        current_piece.y -= 1
                if event.key == pygame.K_UP: #rotate
                    current_piece.rotation += 1
                    if not(self.is_valid_space(current_piece, grid)):
                        current_piece.rotation -= 1
                if event.key == pygame.K_LEFT: #move left
                    current_piece.x -= 1
                    if not(self.is_valid_space(current_piece, grid)):
                        current_piece.x += 1
                if event.key == pygame.K_RIGHT: # move right
                    current_piece.x += 1
                    if not(self.is_valid_space(current_piece, grid)):
                        current_piece.x -= 1
                if event.key == pygame.K_SPACE: #speed down
                    bottom = False
                    while bottom != True:
                        current_piece.y += 1
                        if not(self.is_valid_space(current_piece, grid)):
                            current_piece.y -= 1
                            bottom = True

        return run,window,current_piece,grid

    def multiplayer_server_action_quit(self,window):
        '''function to communicate with server about status of other player'''
        run = True
        msg = json.dumps({"action":"quit","status":False})
        mysend(self.my_socket, msg)
        response = json.loads(myrecv(self.my_socket))
        opp_not_in_game = response["status"]
        if opp_not_in_game == True:
            #if opp_status is not in game
            #start shut down procedure
            #>display you won
            #>update score
            #>close game
            self.pop_up_text(window, "YOU WIN!", 80, (255,255,255))
            pygame.display.update()
            pygame.time.delay(1500)
            #---------------------------------------------------------------------------#
            # let the server know that you quit too so you can be removed from game group
            msg = json.dumps({"action":"quit","status":True})
            mysend(self.my_socket, msg)
            response = json.loads(myrecv(self.my_socket))
            #---------------------------------------------------------------------------#
            run = False
            self.dump_score(self.score)
        
        return run

    def multiplayer_server_action_exchange_points(self):
        '''function to communicate with server, sends score and recieves opponent scores'''
        msg = json.dumps({"action":"swap_points","points":self.score})
        mysend(self.my_socket, msg)
        response = json.loads(myrecv(self.my_socket))
        self.opp_score = response["points"]

    def run_game(self,window):
        '''the main function that runs the whole game in a while loop
        calls all the needed functions to allow the game to work
        aka the driver code'''
        self.highest_score() #updates the record high and personal high scores
        clock = pygame.time.Clock()
        fall_time = 0
        fall_speed = 0.27
        level_time = 0

        locked_positions = {}
        grid = self.create_game_grid(locked_positions)
        new_piece = False

        current_piece = self.get_shape()
        next_piece = self.get_shape()
        #score = self.score
        #opp_score = self.opp_score

        run = True
        while run:
            if self.multiplayer:
                run = self.multiplayer_server_action_quit(window)
                if run == False:
                    break
            #whether opponent still in game or not
            #-----------------------------------------------------------------#
                #if they are still in the game then we can update score
            if self.multiplayer:
                self.multiplayer_server_action_exchange_points()
            
            grid = self.create_game_grid(locked_positions)
            fall_time += clock.get_rawtime()
            level_time += clock.get_rawtime()
            clock.tick()

            if level_time/1000 > 5:
                level_time = 0
                if level_time > 0.12:
                    level_time -= 0.005

            if fall_time/1000 > fall_speed:
                fall_time = 0
                current_piece.y += 1
                if not(self.is_valid_space(current_piece, grid)) and current_piece.y > 0:
                    current_piece.y -= 1
                    new_piece = True

            run, window, current_piece, grid = self.call_events(window,current_piece,grid)

            shape_pos = self.convert_shape(current_piece)

            for i in range(len(shape_pos)):
                x, y = shape_pos[i]
                if y > -1:
                    grid[y][x] = current_piece.color

            if new_piece:
                for pos in shape_pos:
                    p = (pos[0], pos[1])
                    locked_positions[p] = current_piece.color
                current_piece = next_piece
                next_piece = self.get_shape()
                new_piece = False
                self.score += self.full_row_complete(grid, locked_positions) * 10

            self.draw_window(window, grid)
            self.draw_next_shape(next_piece, window)
            pygame.display.update()

            if self.check_top(locked_positions): #if at top then gave over
                self.pop_up_text(window, "GAME OVER!", 80, (255,255,255))
                pygame.display.update()
                pygame.time.delay(1500)
                self.dump_score(self.score)
                if self.multiplayer:
                    msg = json.dumps({"action":"quit","status":True})
                    mysend(self.my_socket, msg)
                    response = json.loads(myrecv(self.my_socket))
                run = False
                #self.dump_score(self.score)

        pygame.display.quit()
        pygame.quit()

    def main_menu(self, window):
        '''This function will display the first screen that the user will see,
        it displays press spacebar to play
        if the user presses the space bar then the main function above would get called,
        if the user exits the game then everything would shut down'''
        run = True
        while run:
            window.fill((0,0,0))
            self.pop_up_text(window, 'Press Spacebar To Play', 60, (255,255,255))
            pygame.display.update()
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    run = False
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_SPACE:
                        self.run_game(window)
                        run = False
        
        pygame.display.quit()

    def start_game(self):
        '''the function that the client_state_machine calls to start the game
        this function will call the main menu which then if the user chooses to play the game will call the main function'''
        window = pygame.display.set_mode((self.s_width, self.s_height))
        pygame.display.set_caption('Tetris')
        self.main_menu(window) 
        pygame.display.quit()
        pygame.quit()
        #return self.score    

''' Code to test the file (cannot use now since the game is integrated with the server)
def main():
    game = Tetris(None,"Player 1","Player 2")
    x = game.start_game()
    print(x)'''

