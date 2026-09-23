"""PyAudio microphone and speaker. PyAudio is imported lazily so the
rest of the package (and its tests) work without it installed."""

from .pitch import SAMPLE_RATE, bytes_to_samples

CHUNK = 2048  # ~46 ms at 44.1 kHz, ~21 Hz frequency resolution


class Microphone:
    def __init__(self, sample_rate=SAMPLE_RATE, chunk=CHUNK):
        import pyaudio
        self.chunk = chunk
        self._pa = pyaudio.PyAudio()
        self.name = self._pa.get_default_input_device_info()["name"]
        self._stream = self._pa.open(format=pyaudio.paInt16, channels=1,
                                     rate=sample_rate, input=True,
                                     frames_per_buffer=chunk)

    def read(self):
        """Block for one chunk and return it as int16 samples."""
        data = self._stream.read(self.chunk, exception_on_overflow=False)
        return bytes_to_samples(data)

    def close(self):
        self._stream.stop_stream()
        self._stream.close()
        self._pa.terminate()


class Speaker:
    def __init__(self, sample_rate=SAMPLE_RATE):
        import pyaudio
        self._pa = pyaudio.PyAudio()
        self._stream = self._pa.open(format=pyaudio.paInt16, channels=1,
                                     rate=sample_rate, output=True)

    def play(self, pcm):
        """Play int16 PCM bytes; blocks until finished."""
        self._stream.write(pcm)

    def close(self):
        self._stream.stop_stream()
        self._stream.close()
        self._pa.terminate()
