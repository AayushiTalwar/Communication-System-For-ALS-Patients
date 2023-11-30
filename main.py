from multiprocessing import Process, Pipe
import time

print("Here")

from string_builder import builder

print("Here 2")

from twitch_detect import ANN, detect

print("Here 3")

if __name__ == '__main__':
    parent_conn, child_conn = Pipe()
    
    print("Starting")

    p = Process(target=detect, args=(child_conn,))
    
    p.start()
    print("Camera On!!")

    builder(parent_conn)
    
    p.join()