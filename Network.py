import socket
import json
from Model import Constants


class Network():
    def __init__(self, ip, port, token, message_handler):
        self.receive_flag = True
        self.ip = ip
        self.port = port
        self.token = token
        self.message_handler = message_handler
        self.result = b''
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def connect(self):
        try:
            self.s.connect((self.ip, self.port))
            self.send({Constants.KEY_NAME: Constants.CONFIG_KEY_TOKEN, Constants.KEY_ARGS: [self.token]})
            init = self.receive()
            if init[Constants.KEY_NAME] == "wrong token":
                raise ConnectionRefusedError("wrong token")
            elif not init[Constants.KEY_NAME] == Constants.MESSAGE_TYPE_INIT:
                self.close()
                raise IOError("first message was not init")
        except Exception as e:
            print("error while connecting to server", e)
            return
        print("connected to server!")
        self.message_handler(init)
        self.start_receiving()

    def send(self, message):
        self.s.send(json.dumps(message).encode('UTF-8'))
        self.s.send(b'\x00')

    def receive(self):
        while self.receive_flag:
            self.result += self.s.recv(1024)
            if b'\x00' in self.result:
                ans = json.loads(self.result[:self.result.index(b'\x00')].decode('UTF-8'))
                self.result = self.result[self.result.index(b'\x00')+1:]
                return ans

    def start_receiving(self):
        import threading

        def run():
            while self.receive_flag:
                try:
                    self.message_handler(self.receive())
                except ConnectionError:
                    print("disconnected from server!")
                    self.close()
                    break

        tr = threading.Thread(target=run, daemon=False)
        tr.start()

    def terminate(self):
        self.receive_flag = False

    def close(self):
        self.terminate()
        self.s.close()