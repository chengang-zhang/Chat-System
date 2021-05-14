"""
Created on Tue Jul 22 00:47:05 2014

@author: alina, zzhang
"""

import time
import socket
import select
import sys
import string
import indexer
import json
import pickle as pkl
from chat_utils import *
import chat_group as grp

class Server:
    def __init__(self):
        self.new_clients = [] #list of new sockets of which the user id is not known
        self.logged_name2sock = {} #dictionary mapping username to socket
        self.logged_sock2name = {} # dict mapping socket to user name
        self.all_sockets = []
        self.group = grp.Group()
        #start server
        self.server=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.bind(SERVER)
        self.server.listen(5)
        self.all_sockets.append(self.server)
        #initialize past chat indices
        self.indices={}
        # sonnet
        # self.sonnet_f = open('AllSonnets.txt.idx', 'rb')
        # self.sonnet = pkl.load(self.sonnet_f)
        # self.sonnet_f.close()
        self.sonnet = indexer.PIndex("AllSonnets.txt")
#=====================================================
        #GAME MOD
        self.gameGroup = grp.Group()
        self.gameScores = {}
        self.gameOver = False
        self.rankings = {}
        # server will update these scores as the game progresses
#=====================================================
        
    def new_client(self, sock):
        #add to all sockets and to new clients
        print('new client...')
        sock.setblocking(0)
        self.new_clients.append(sock)
        self.all_sockets.append(sock)

    def login(self, sock):
        #read the msg that should have login code plus username
        try:
            msg = json.loads(myrecv(sock))
            if len(msg) > 0:

                if msg["action"] == "login":
                    name = msg["name"]
                    if self.group.is_member(name) != True:
                        #move socket from new clients list to logged clients
                        self.new_clients.remove(sock)
                        #add into the name to sock mapping
                        self.logged_name2sock[name] = sock
                        self.logged_sock2name[sock] = name
                        #load chat history of that user
                        if name not in self.indices.keys():
                            try:
                                self.indices[name]=pkl.load(open(name+'.idx','rb'))
                            except IOError: #chat index does not exist, then create one
                                self.indices[name] = indexer.Index(name)
                        print(name + ' logged in')
                        self.group.join(name)
#==================================================================
                        self.gameGroup.join(name)
#==================================================================
                        mysend(sock, json.dumps({"action":"login", "status":"ok"}))
                    else: #a client under this name has already logged in
                        mysend(sock, json.dumps({"action":"login", "status":"duplicate"}))
                        print(name + ' duplicate login attempt')
                else:
                    print ('wrong code received')
            else: #client died unexpectedly
                self.logout(sock)
        except:
            self.all_sockets.remove(sock)

    def logout(self, sock):
        #remove sock from all lists
        name = self.logged_sock2name[sock]
        pkl.dump(self.indices[name], open(name + '.idx','wb'))
        del self.indices[name]
        del self.logged_name2sock[name]
        del self.logged_sock2name[sock]
        self.all_sockets.remove(sock)
        self.group.leave(name)
        sock.close()

#==============================================================================
# main command switchboard
#==============================================================================
    def handle_msg(self, from_sock):
        #read msg code
        msg = myrecv(from_sock)
        if len(msg) > 0:
#==============================================================================
# handle connect request
#==============================================================================
            msg = json.loads(msg)
            if msg["action"] == "connect":
                to_name = msg["target"]
                from_name = self.logged_sock2name[from_sock]
                if to_name == from_name:
                    msg = json.dumps({"action":"connect", "status":"self"})
                # connect to the peer
                elif self.group.is_member(to_name):
                    to_sock = self.logged_name2sock[to_name]
                    self.group.connect(from_name, to_name)
                    the_guys = self.group.list_me(from_name)
                    msg = json.dumps({"action":"connect", "status":"success"})
                    for g in the_guys[1:]:
                        to_sock = self.logged_name2sock[g]
                        mysend(to_sock, json.dumps({"action":"connect", "status":"request", "from":from_name}))
                else:
                    msg = json.dumps({"action":"connect", "status":"no-user"})
                mysend(from_sock, msg)
#==============================================================================
# handle messeage exchange: one peer for now. will need multicast later
#==============================================================================
            elif msg["action"] == "exchange":
                from_name = self.logged_sock2name[from_sock]
                the_guys = self.group.list_me(from_name)
                #said = msg["from"]+msg["message"]
                said2 = text_proc(msg["message"], from_name)
                self.indices[from_name].add_msg_and_index(said2)
                for g in the_guys[1:]:
                    to_sock = self.logged_name2sock[g]
                    self.indices[g].add_msg_and_index(said2)
                    mysend(to_sock, json.dumps({"action":"exchange", "from":msg["from"], "message":msg["message"]}))
#==============================================================================
#                 listing available peers
#==============================================================================
            elif msg["action"] == "list":
                from_name = self.logged_sock2name[from_sock]
                msg = self.group.list_all()
                mysend(from_sock, json.dumps({"action":"list", "results":msg}))
#==============================================================================
#             retrieve a sonnet
#==============================================================================
            elif msg["action"] == "poem":
                poem_indx = int(msg["target"])
                from_name = self.logged_sock2name[from_sock]
                print(from_name + ' asks for ', poem_indx)
                poem = self.sonnet.get_poem(poem_indx)
                poem = '\n'.join(poem).strip()
                print('here:\n', poem)
                mysend(from_sock, json.dumps({"action":"poem", "results":poem}))
#==============================================================================
#                 time
#==============================================================================
            elif msg["action"] == "time":
                ctime = time.strftime('%d.%m.%y,%H:%M', time.localtime())
                mysend(from_sock, json.dumps({"action":"time", "results":ctime}))
#==============================================================================
#                 search
#==============================================================================
            elif msg["action"] == "search":
                term = msg["target"]
                from_name = self.logged_sock2name[from_sock]
                print('search for ' + from_name + ' for ' + term)
                # search_rslt = (self.indices[from_name].search(term))
                search_rslt = '\n'.join([x[-1] for x in self.indices[from_name].search(term)])
                print('server side search: ' + search_rslt)
                mysend(from_sock, json.dumps({"action":"search", "results":search_rslt}))
#==============================================================================
# the "from" guy has had enough (talking to "to")!
#==============================================================================
            elif msg["action"] == "disconnect":
                from_name = self.logged_sock2name[from_sock]
                the_guys = self.group.list_me(from_name)
                self.group.disconnect(from_name)
                the_guys.remove(from_name)
                if len(the_guys) == 1:  # only one left
                    g = the_guys.pop()
                    to_sock = self.logged_name2sock[g]
                    mysend(to_sock, json.dumps({"action":"disconnect"}))
#==============================================================================
#                 the "from" guy really, really has had enough
#==============================================================================

#==============================================================================
            #GAME MOD
            #server handling for starting a game
            elif msg["action"] == "start_game":
                to_name = msg["target"]
                from_name = self.logged_sock2name[from_sock]
                if to_name == from_name: #if self
                    msg = json.dumps({"action": "start_game", "status": "self"})
                # if connecting to a peer
                elif self.gameGroup.is_member(to_name):
                    to_sock = self.logged_name2sock[to_name]
                    self.gameOver = False # make sure that gameOver is False from the start
                    # detect whether in game
                    # print(self.gameGroup)
                    if len(self.gameGroup.list_me(to_name)) == 1:
                        self.gameGroup.connect(from_name, to_name)
                        #the_guys = self.gameGroup.list_me(from_name)
                        msg = json.dumps(
                            {"action": "start_game", "status": "success"})
                        #tell the peer that they have been called to a game
                        mysend(to_sock, json.dumps(
                            {"action": "start_game", "status": "request", "from": from_name}))

                        # update the dictionary with scores:
                        self.gameScores = {from_name:0,to_name:0}
                    else: #user is in a game with some other person, or by themselves
                        msg = json.dumps({"action": "start_game", "status": "user_in_game"})
                else: 
                    msg = json.dumps(
                        {"action": "start_game", "status": "no-user"})
                mysend(from_sock, msg)

            elif msg["action"] == "swap_points":
                # server updates the players scores
                #self.gameScores = {}
                from_name = self.logged_sock2name[from_sock]
                self.gameScores[from_name] = msg["points"] 
                #updates my score in the dictionary

                the_guys = self.gameGroup.list_me(from_name)
                to_name = the_guys[1]
                #to_name is the name of opponent
                try:
                    opp_score = self.gameScores[to_name]
                except:
                    opp_score = 0
                #the score gets sent to the other user
                mysend(from_sock, json.dumps({"action":"swap_points","points":opp_score}))  
            
            elif msg["action"] == "quit": #if the user quits/loses the game
                from_name = self.logged_sock2name[from_sock]
                the_guys = self.gameGroup.list_me(from_name)
                if msg["status"] == True: #if one player quits then the other would know (False until True)
                    self.gameOver = True
                    self.gameGroup.disconnect(from_name)
                    the_guys.remove(from_name)
                #will always send False until True:
                mysend(from_sock, json.dumps({"action":"quit","status":self.gameOver}))
#==============================================================================
            elif msg["action"] == "rank": #allows user to get the ranking
                # currently doesn't work properly
                from_name = self.logged_sock2name[from_sock]
                #print(from_name + ' asks for ranking')
                rankings = open("scores.txt","rb")
                self.rankings = pkl.load(rankings)
                rankings.close()
                result = "Name: # of points\n"
                #holder = "Name: # of points"
                for k,v in self.rankings.items():
                    holder = str(k) + ": " + str(v) +" points\n"
                    result = result + holder
                mysend(from_sock, json.dumps({"action":"rank", "results":str(result)}))

            elif msg["action"] == "my_score":
                from_name = self.logged_sock2name[from_sock]
                rankings = open("scores.txt","rb")
                self.rankings = pkl.load(rankings)
                rankings.close()
                result = None
                #holder = "Name: # of points"
                for k,v in self.rankings.items():
                    if k == from_name:
                        result = v
                mysend(from_sock, json.dumps({"action":"rank", "my_score":v}))
                
        else:
            #client died unexpectedly
            self.logout(from_sock)

#==============================================================================
# main loop, loops *forever*
#==============================================================================
    def run(self):
        print ('starting server...')
        while(1):
           read,write,error=select.select(self.all_sockets,[],[])
           print('checking logged clients..')
           for logc in list(self.logged_name2sock.values()):
               if logc in read:
                   self.handle_msg(logc)
           print('checking new clients..')
           for newc in self.new_clients[:]:
               if newc in read:
                   self.login(newc)
           print('checking for new connections..')
           if self.server in read :
               #new client request
               sock, address=self.server.accept()
               self.new_client(sock)

def main():
    server=Server()
    server.run()

main()
