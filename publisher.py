import time


class Publisher():
    def __init__(self):
        self.triggers = {'*': []}

    def subscribe(self, event, callback):
        if event in self.triggers:
            self.triggers[event].append(callback)
        else:
            self.triggers[event] = [callback]

    def publish(self, event, data):
        if data is None:
            data = {}
        data['timestamp'] = time.time()
        # print(self.__class__, event, data)
        for c in self.triggers['*']:
            c(event, data)
        if event in self.triggers:
            callbacks = self.triggers[event]
            for c in callbacks:
                c(event, data)
