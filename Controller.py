from Network import Network
from Model import Model, Constants
from AI import AI
import json
from threading import Thread
from queue import Queue


class Controller():
    def __init__(self, settings_file):
        self.settings_file = settings_file
        self.sending_flag = True
        self.conf = {}
        self.network = None
        self.queue = Queue()
        self.model = Model(self.queue)
        self.client = AI()

    def start(self):
        self.read_settings()
        self.network = Network(ip=self.conf[Constants.CONFIG_KEY_IP],
                               port=self.conf[Constants.CONFIG_KEY_PORT],
                               token=self.conf[Constants.CONFIG_KEY_TOKEN],
                               message_handler=self.handle_message)
        self.network.connect()

        def run():
            while self.sending_flag:
                event = self.queue.get()
                self.queue.task_done()
                message = {
                    Constants.KEY_NAME: Constants.MESSAGE_TYPE_EVENT,
                    Constants.KEY_ARGS: [event]
                }
                self.network.send(message)
        Thread(target=run, daemon=True).start()

    def terminate(self):
        print("finished!")
        self.network.close()
        self.sending_flag = False

    def read_settings(self):
        with open(self.settings_file) as file:
            self.conf = json.loads(file.read())

    def handle_message(self, message):
        if message[Constants.KEY_NAME] == Constants.MESSAGE_TYPE_INIT:
            self.model.handle_init_message(message)
        elif message[Constants.KEY_NAME] == Constants.MESSAGE_TYPE_TURN:
            self.model.handle_turn_message(message)
            self.do_turn()
        elif message[Constants.KEY_NAME] == Constants.MESSAGE_TYPE_SHUTDOWN:
            self.terminate()

    def do_turn(self):

        def run():
            self.client.do_turn(self.model.world)

        Thread(target=run, daemon=True).start()

c = Controller("connection.conf")
c.start()