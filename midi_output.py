import rtmidi
import mido
from logger import get_logger

log = get_logger("MidiOutput")

class MidiOutput:
    def __init__(self):
        self.midi_out = rtmidi.MidiOut()
        self.current_port_name = None

    def get_ports(self):
        return self.midi_out.get_ports()

    def open_port(self, port_index):
        if self.midi_out.is_port_open():
            self.midi_out.close_port()
        ports = self.get_ports()
        if port_index < len(ports):
            self.midi_out.open_port(port_index)
            self.current_port_name = ports[port_index]
            log.info(f"Opened MIDI Port: {self.current_port_name}")

    def send_note_on(self, note, velocity=100, channel=0):
        if self.midi_out.is_port_open():
            msg = mido.Message('note_on', note=note, velocity=velocity, channel=channel)
            self.midi_out.send_message(list(msg.bytes()))
            
    def send_note_off(self, note, channel=0):
        if self.midi_out.is_port_open():
            msg = mido.Message('note_off', note=note, channel=channel)
            self.midi_out.send_message(list(msg.bytes()))

    def send_cc(self, control, value, channel=0):
        if self.midi_out.is_port_open():
            # control: 0-127, value: 0-127
            msg = mido.Message('control_change', control=control, value=value, channel=channel)
            self.midi_out.send_message(list(msg.bytes()))

    def panic(self):
        if self.midi_out.is_port_open():
            for channel in range(16):
                # CC 123 is "All Notes Off"
                msg = mido.Message('control_change', control=123, value=0, channel=channel)
                self.midi_out.send_message(list(msg.bytes()))
                # Also CC 120 "All Sound Off" for good measure
                msg = mido.Message('control_change', control=120, value=0, channel=channel)
                self.midi_out.send_message(list(msg.bytes()))

    def close(self):
        if self.midi_out.is_port_open():
            self.midi_out.close_port()
