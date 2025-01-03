import time
import json
from locust import task, HttpUser
from locust_plugins.users.socketio import SocketIOUser
import random

# class MySocketIOUser(SocketIOUser):
class QuickstartUser(HttpUser):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.hashe = str(random.getrandbits(1024))[0:10]
    
    @task(1)
    def join_queue(self):
        self.client.post(
            "/arene/gradio_api/queue/join",
            headers={
                'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:133.0) Gecko/20100101 Firefox/133.0',
                'Accept': '*/*',
                'Accept-Language': 'fr,fr-FR;q=0.8,en-US;q=0.5,en;q=0.3',
                'Accept-Encoding': 'gzip, deflate, br, zstd',
                'Referer': 'http://localhost:8001/arene/?cgu_acceptees',
                'content-type': 'application/json',
                'Origin': 'http://localhost:8001',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Sec-Fetch-Dest': 'empty',
                'Sec-Fetch-Mode': 'cors',
                'Sec-Fetch-Site': 'same-origin',
                'Sec-GPC': '1',
                'Priority': 'u=4'
            },
            json={
                "data": [
                    "<languia.block_arena.AppState object at 0x7fd7f74bb710>",
                    "<languia.block_arena.Conversation object at 0x7fd7f41e3150>",
                    "<languia.block_arena.Conversation object at 0x7fd7f41e2410>"
                ],
                "event_data": None,
                "fn_index": 0,
                "trigger_id": None,
                "session_hash": self.hashe
            }
        )
        
    # @task(2)
    # def get_data(self):
    #     self.client.get(f"/arene/gradio_api/queue/data?session_hash={self.hashe}",
    #         headers={
    #             'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:133.0) Gecko/20100101 Firefox/133.0',
    #             'Accept': 'text/event-stream',
    #             'Accept-Language': 'fr,fr-FR;q=0.8,en-US;q=0.5,en;q=0.3',
    #             'Accept-Encoding': 'gzip, deflate, br, zstd',
    #             'Referer': 'http://localhost:8001/arene/?cgu_acceptees',
    #             'Content-Type': 'application/json',
    #             'DNT': '1',
    #             'Connection': 'keep-alive',
    #             'Sec-Fetch-Dest': 'empty',
    #             'Sec-Fetch-Mode': 'cors',
    #             'Sec-Fetch-Site': 'same-origin',
    #             'Sec-GPC': '1',
    #             'Priority': 'u=4'
    #         }
    #     )       

    # @task(1)
    # def my_task(self):
    #     self.my_value = None

    #     self.connect("ws://127.0.0.1:8001/arene/gradio_api/queue/join")
    #     # example of subscribe
    #     import random

    #     hashe = random.getrandbits(1024)
    #     msg = '{"hash": "' + str(hashe) + '"}'
    #     json.loads(msg)
    #     self.ws.send(msg)
    #     # wait until I get a push message to on_message
    #     while True:
    #         while not self.my_value:
    #             time.sleep(0.1)
    #         msg = self.my_value["msg"]
    #         if msg == "send_data":
    #             self.ws.send('{"data": ["text2"], "fn": 0}')
    #         elif msg == "estimation":
    #             pass
    #         elif msg == "process_starts":
    #             pass
    #         elif msg == "process_completed":
    #             print(self.my_value, time.time())
    #             return True

    #         self.my_value = None

    #         # wait for additional pushes, while occasionally sending heartbeats, like a real client would
    #         self.sleep_with_heartbeat(10)

    # def on_message(self, message):
    #     self.my_value = json.loads(message)

    # if __name__ == "__main__":
    #     host = "ws://localhost:8001/queue/test"
