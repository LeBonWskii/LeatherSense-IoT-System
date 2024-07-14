from .Sensor import Sensor
from .config.DefaultParameters import DefaultParameters

class TempSensor(Sensor):
    _instance = None
    
    def __init__(self):
        super().__init__("temperature", DefaultParameters.intervals["temperature"]["min"], DefaultParameters.intervals["temperature"]["max"], DefaultParameters.intervals["temperature"]["delta"])

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
