import requests

from publisher import Publisher
from conf import conf


__touchetmanager_instance = None


def touchetmanager(*init_params):
    global __touchetmanager_instance
    if __touchetmanager_instance is None:
        __touchetmanager_instance = TouchetManager(*init_params)
    return __touchetmanager_instance


class TouchetManager(Publisher):
    def __init__(self):
        super().__init__()
        self.touchets = []

    # Call this to start an asynchonous process that will eventually instantiate the touchet
    def mktouchet(self, touchet_class):
        touchet_class.prepare(self)  # Let the touchet gather information and instantiate the touchet

    # Called by the touchet class once the touchet is ready
    def add_touchet(self, touchet):
        self.touchets.append(touchet)
        touchet.subscribe('*', self.propagate_touchet_event)

    def clear_touchets_with_shapes(self, shapes):
        todel = []
        for shape in shapes:
            for touchet in self.touchets:
                if shape in touchet.shapes:
                    todel.append(touchet)
        self.touchets = [t for t in self.touchets if t not in todel]

    def propagate_touchet_event(self, event, data):
        try:
            r = requests.get(conf()['event_sink_url'], params={'event': event, **data})
            r.raise_for_status()
        except requests.exceptions.RequestException as e:
            print("An error occured while attempting to connect to NodeRed:")
            print(e)

    def emit_global_event(self, event, data):
        self.propagate_touchet_event(event, {
            'touchet_type': "GLOBAL",
            **data
        })
