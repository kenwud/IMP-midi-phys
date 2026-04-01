class Event:
    pass

class CollisionEvent(Event):
    def __init__(self, shape_a, shape_b, velocity):
        self.shape_a = shape_a
        self.shape_b = shape_b
        self.velocity = velocity

class ProximityEvent(Event):
    def __init__(self, attractor, ball_body, ball_shape, distance):
        self.attractor = attractor
        self.ball_body = ball_body
        self.ball_shape = ball_shape
        self.distance = distance

class TransportEvent(Event):
    def __init__(self, playing):
        self.playing = playing

class EventBus:
    def __init__(self):
        self.listeners = []

    def subscribe(self, listener):
        self.listeners.append(listener)

    def post(self, event):
        for listener in self.listeners:
            listener(event)
