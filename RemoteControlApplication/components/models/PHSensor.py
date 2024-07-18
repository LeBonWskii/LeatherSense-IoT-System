from .Sensor import Sensor
from .config.DefaultParameters import DefaultParameters

class PHSensor(Sensor):
    _instance = None

    def __init__(self):
        super().__init__("ph", DefaultParameters.intervals["ph"]["min"], DefaultParameters.intervals["ph"]["max"], DefaultParameters.intervals["ph"]["delta"])
    
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

