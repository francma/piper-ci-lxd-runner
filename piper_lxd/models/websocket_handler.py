from ws4py.client.threadedclient import WebSocketClient


class WebSocketHandler:

    def __init__(self, address, resource):
        self.web_socket = WebSocketClient(address)
        self.web_socket.resource = resource
        self.web_socket.connect()

    def send(self, data):
        self.web_socket.send(data)

    def close(self):
        self.web_socket.close()
