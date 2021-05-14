'''THIS FILE WAS MADE SO THAT I COULD DUMP A DICTIONARY INTO THE SCORES.TXT FILE'''

import pickle as pk

x = {"elmo":30}

pk.dump(x, open("scores.txt", "wb"))