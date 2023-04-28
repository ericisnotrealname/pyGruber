# encoding:utf-8
import socket
import _thread
import psutil
import multiprocessing
from lib import log
 
class Header:
    """
    Used to read and parse header information
    """
 
    def __init__(self, conn):
        self._method = None
        header = b''
        try:
            while 1:
                data = conn.recv(4096)
                header = b"%s%s" % (header, data)
                if header.endswith(b'\r\n\r\n') or (not data):
                    break
        except:
            pass
        self._header = header
        self.header_list = header.split(b'\r\n')
        self._host = None
        self._port = None
 
    def get_method(self):
        """
        get request method
        :return:
        """
        if self._method is None:
            self._method = self._header[:self._header.index(b' ')]
        return self._method
 
    def get_host_info(self):
        """
        获取目标主机的ip和端口
        :return:
        """
        if self._host is None:
            method = self.get_method()
            line = self.header_list[0].decode('utf8')
            if method == b"CONNECT":
                host = line.split(' ')[1]
                if ':' in host:
                    host, port = host.split(':')
                else:
                    port = 443
            else:
                for i in self.header_list:
                    if i.startswith(b"Host:"):
                        host = i.split(b" ")
                        if len(host) < 2:
                            continue
                        host = host[1].decode('utf8')
                        break
                else:
                    host = line.split('/')[2]
                if ':' in host:
                    host, port = host.split(':')
                else:
                    port = 80
            self._host = host
            self._port = int(port)
        return self._host, self._port
 
    @property
    def data(self):
        """
        返回头部数据
        :return:
        """
        return self._header
 
    def is_ssl(self):
        """
        判断是否为 https协议
        :return:
        """
        if self.get_method() == b'CONNECT':
            return True
        return False
 
    def __repr__(self):
        return str(self._header.decode("utf8"))


class Listener:
    def __init__(self, ip="127.0.0.1", port=8080):
        """
        代理服务
        :param ip:
        :param port:
        """
        self.ip = ip
        self.port = port
        self.log = log.logger
        self.serve = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.serve.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.serve.bind((self.ip, self.port))
        self.serve.listen(10)
        self.__listener_serve__ = None

    def communicate(self, sock1, sock2):
        """
        socket之间的数据交换
        :param sock1:
        :param sock2:
        :return:
        """
        try:
            while True:
                data = sock1.recv(1024)
                if not data:
                    return
                sock2.sendall(data)
        except:
            pass

    def handle(self, client):
        """
        处理连接进来的客户端
        :param client:
        :return:
        """
        timeout = 60
        client.settimeout(timeout)
        header = Header(client)
        if not header.data:
            client.close()
            return
        self.log.info(*header.get_host_info(), header.get_method())
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            server.connect(header.get_host_info())
            server.settimeout(timeout)
            if header.is_ssl():
                data = b"HTTP/1.0 200 Connection Established\r\n\r\n"
                client.sendall(data)
                _thread.start_new_thread(self.communicate, (client, server))
            else:
                server.sendall(header.data)
            self.communicate(server, client)
        except:
            server.close()
            client.close()

    def __start__(self):
        self.log.info(f"proxy listening on {self.ip}:{self.port}...")
        while True:
            conn, addr = self.serve.accept()
            self.log.info(f"from: {addr}")
            _thread.start_new_thread(self.handle, (conn,))
    
    def start(self):
        self.__listener_serve__ = multiprocessing.Process(target=self.__start__)
        self.__listener_serve__.start()

    def is_alive(self):
        if self.__listener_serve__ == None:
            return False
        return self.__listener_serve__.is_alive()

    def terminate(self):
        if self.is_alive():
            parent = psutil.Process(self.__listener_serve__.pid)
            for proc in parent.children(recursive=True) + [parent]:
                proc.terminate()
        else:
            raise "listener is not running"
