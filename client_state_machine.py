"""
Created on Sun Apr  5 00:00:32 2015

@author: zhengzhang
"""
from chat_utils import *
import json
import tetris as game
import pygame 
import threading

class ClientSM:
    def __init__(self, s):
        self.state = S_OFFLINE
        self.peer = ''
        self.me = ''
        self.out_msg = ''
        self.s = s
#===============================
        #GAME MOD
        self.game = None
#===============================

    def set_state(self, state):
        self.state = state

    def get_state(self):
        return self.state

    def set_myname(self, name):
        self.me = name

    def get_myname(self):
        return self.me

    def connect_to(self, peer):
        msg = json.dumps({"action":"connect", "target":peer})
        mysend(self.s, msg)
        response = json.loads(myrecv(self.s))
        if response["status"] == "success":
            self.peer = peer
            self.out_msg += 'You are connected with '+ self.peer + '\n'
            return (True)
        elif response["status"] == "busy":
            self.out_msg += 'User is busy. Please try again later\n'
        elif response["status"] == "self":
            self.out_msg += 'Cannot talk to yourself (sick)\n'
        else:
            self.out_msg += 'User is not online, try again later\n'
        return(False)

    def disconnect(self):
        msg = json.dumps({"action":"disconnect"})
        mysend(self.s, msg)
        self.out_msg += 'You are disconnected from ' + self.peer + '\n'
        self.peer = ''

#======================================================================
    #Game MOD
    def game_connect(self, peer):
        '''a function that is fundamentally similar to connect for chatting in groups (above function) but for a game'''
        msg = json.dumps({"action":"start_game", "target":peer}) # send the server the game request
        mysend(self.s, msg)
        response = json.loads(myrecv(self.s))
        #print(response['status'])
        if response["status"] == "success": #if the request was to a peer
            self.peer = peer
            self.out_msg += 'You are connected with '+ self.peer + '\n'
            return (True)
        elif response["status"] == "busy": #if peer was busy
            self.out_msg += 'User is busy. Please try again later\n'
        elif response["status"] == "self": #if the request was to self, then one can play alone
            self.state = S_GAME
            self.out_msg += 'You are playing in one player mode\n'
            return (True)
        elif response["status"] == "user_in_game":
            self.out_msg += 'User is currently in game, please wait\n'
        else:
            self.out_msg += 'User is not online, try again later\n'
        return(False)

    def game_driver_2player(self):
        self.game = game.Tetris(self.s,self.me,self.peer)           
        self.game.start_game()
        
    def game_driver_1player(self):
        self.game = game.Tetris(self.s,self.me,"") #when playing alone send an empty string as "peer"            
        self.game.start_game()

#======================================================================

    def proc(self, my_msg, peer_msg):
        self.out_msg = ''
#==============================================================================
# Once logged in, do a few things: get peer listing, connect, search
# And, of course, if you are so bored, just go
# This is event handling instate "S_LOGGEDIN"
#==============================================================================
        if self.state == S_LOGGEDIN:
            # todo: can't deal with multiple lines yet
            if len(my_msg) > 0:

                if my_msg == 'q':
                    self.out_msg += 'See you next time!\n'
                    self.state = S_OFFLINE

                elif my_msg == 'time':
                    mysend(self.s, json.dumps({"action":"time"}))
                    time_in = json.loads(myrecv(self.s))["results"]
                    self.out_msg += "Time is: " + time_in

                elif my_msg == 'who':
                    mysend(self.s, json.dumps({"action":"list"}))
                    logged_in = json.loads(myrecv(self.s))["results"]
                    self.out_msg += 'Here are all the users in the system:\n'
                    self.out_msg += logged_in

                elif my_msg[0] == 'c':
                    peer = my_msg[1:]
                    peer = peer.strip()
                    if self.connect_to(peer) == True:
                        self.state = S_CHATTING
                        self.out_msg += 'Connect to ' + peer + '. Chat away!\n\n'
                        self.out_msg += '-----------------------------------\n'
                    else:
                        self.out_msg += 'Connection unsuccessful\n'

                elif my_msg[0] == '?':
                    term = my_msg[1:].strip()
                    mysend(self.s, json.dumps({"action":"search", "target":term}))
                    search_rslt = json.loads(myrecv(self.s))["results"].strip()
                    if (len(search_rslt)) > 0:
                        self.out_msg += search_rslt + '\n\n'
                    else:
                        self.out_msg += '\'' + term + '\'' + ' not found\n\n'

                elif my_msg[0] == 'p' and my_msg[1:].isdigit():
                    poem_idx = my_msg[1:].strip()
                    mysend(self.s, json.dumps({"action":"poem", "target":poem_idx}))
                    poem = json.loads(myrecv(self.s))["results"]
                    # print(poem)
                    if (len(poem) > 0):
                        self.out_msg += poem + '\n\n'
                    else:
                        self.out_msg += 'Sonnet ' + poem_idx + ' not found\n\n'
#=========================================================================
                #GAME MOD
                elif my_msg[0] == 'g':
                    peer = my_msg[1:]
                    peer = peer.strip()
                    if self.game_connect(peer) == True: 
                        #True if its to a player that is also in state logged in or to self
                        self.state = S_GAME
                        if len(self.peer) >1:
                            self.out_msg += 'Connect to ' + peer + '. Are you ready!?\n'
                            self.out_msg += '-----------------------------------\n'
                        else: #if playing alone then just a line 
                            self.out_msg += '-----------------------------------\n'
                    else:
                        self.out_msg += 'Connection unsuccessful\n'

                elif my_msg[0] == 'r': # if user asks for the scores
                    mysend(self.s, json.dumps({"action":"rank"}))
                    ranking = json.loads(myrecv(self.s))["results"]
                    # print(poem)
                    if (len(ranking) > 0):
                        self.out_msg += ranking + '\n\n'
                    else:
                        self.out_msg += 'Ranking file not found\n\n'

#=========================================================================
                else:
                    self.out_msg += menu

            if len(peer_msg) > 0:
                peer_msg = json.loads(peer_msg)
                if peer_msg["action"] == "connect":
                    self.peer = peer_msg["from"]
                    self.out_msg += 'Request from ' + self.peer + '\n'
                    self.out_msg += 'You are connected with ' + self.peer
                    self.out_msg += '. Chat away!\n\n'
                    self.out_msg += '------------------------------------\n'
                    self.state = S_CHATTING
#====================================================================
                #GAME MOD
                # the peer response to start game: change the state to game
                elif peer_msg["action"] == "start_game":
                    peer = peer_msg["from"]
                    peer = peer.strip()

                    self.state = S_GAME
                    self.peer = peer

                    self.out_msg += 'Request from ' + self.peer + '\n'
                    self.out_msg += 'You are connected with ' + self.peer + '. Are you ready!?\n'
                    self.out_msg += '-----------------------------------\n'


#======================================================================
#==============================================================================
# Start chatting, 'bye' for quit
# This is event handling instate "S_CHATTING"
#==============================================================================
        elif self.state == S_CHATTING:
            if len(my_msg) > 0:     # my stuff going out
                mysend(self.s, json.dumps({"action":"exchange", "from":"[" + self.me + "]", "message":my_msg}))
                if my_msg == 'bye':
                    self.disconnect()
                    self.state = S_LOGGEDIN
                    self.peer = ''
            if len(peer_msg) > 0:    # peer's stuff, coming in
                peer_msg = json.loads(peer_msg)
                if peer_msg["action"] == "connect":
                    self.out_msg += "(" + peer_msg["from"] + " joined)\n"
                elif peer_msg["action"] == "disconnect":
                    self.state = S_LOGGEDIN
                else:
                    self.out_msg += peer_msg["from"] + peer_msg["message"]

            # Display the menu again
            if self.state == S_LOGGEDIN:
                self.out_msg += menu

#=====================================================
        elif self.state == S_GAME: # if the state is game
            #print("IT WORKS")
            self.state = S_LOGGEDIN #change state to return to main menu
            # changes state immediately to Loggedin to prevent bugs
            if len(self.peer) > 1: #if playing with a peer
                game_thread = threading.Thread(target=self.game_driver_2player())
                game_thread.daemon = True
                game_thread.start()
                game_thread.join()
            else: # if playing alone
                game_thread = threading.Thread(target=self.game_driver_1player())
                game_thread.daemon = True
                game_thread.start()
                game_thread.join()

            #print(game_thread.is_alive())

            # after the game we should get a message that says quit game       
            if self.state == S_LOGGEDIN:
                self.peer = ''
                self.out_msg += "Quit game" 
                self.out_msg += menu
                self.out_msg += "\n\nWelcome back " + self.me +"!"
                self.out_msg += "\nPlay again soon!" 
#=====================================================
                
#==============================================================================
# invalid state
#==============================================================================
        else:
            self.out_msg += 'How did you wind up here??\n'
            print_state(self.state)

        return self.out_msg
