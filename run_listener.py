import time

from lib.listener import Listener


if __name__ == '__main__':
    serv = Listener()
    serv.start()
    time.sleep(10)
    serv.terminate()
