from publisher import Publisher


class Touchet(Publisher):
    def __init__(self, shapes):
        super().__init__()
        self.shapes = shapes

        # Auto-subscribe
        handlers = [func for func in dir(self) if callable(getattr(self, func)) and func.startswith('on_')]
        for shape in shapes:
            for func in handlers:
                shape.subscribe(func.replace('on_', '', 1), getattr(self, func))

    def emit_touchet_event(self, event, **args):
        self.publish(event, {
            'touchet_type': type(self).__name__.replace('Touchet', ''),
            'action': self.shapes[0].action_name,
            **args
        })
