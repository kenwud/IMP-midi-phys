from event_bus import TransportEvent

class Transport:
    def __init__(self, bus, bpm=120):
        self.bus = bus
        self.playing = False
        self.bpm = bpm
        
    def play(self):
        self.playing = True
        self.bus.post(TransportEvent(True))
        
    def stop(self):
        self.playing = False
        self.bus.post(TransportEvent(False))
        
    def toggle(self):
        self.playing = not self.playing
        self.bus.post(TransportEvent(self.playing))

    def reset(self):
        self.playing = False
        self.bus.post(TransportEvent(False))
