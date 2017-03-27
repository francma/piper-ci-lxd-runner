from ws4py.client import WebSocketBaseClient


class WebSocketHandler:

    class WebSocket(WebSocketBaseClient):
        def __init__(self, *args, **kwargs):
            super(WebSocketHandler.WebSocket, self).__init__(*args, **kwargs)

        def handshake_ok(self):
            pass

    def __init__(self, address, resource):
        self.web_socket = self.WebSocket(address)
        self.web_socket.resource = resource
        self.web_socket.connect()

    def on_message(self, data):
        self.web_socket.send(data)

    def close(self, message):
        self.web_socket.close(message)