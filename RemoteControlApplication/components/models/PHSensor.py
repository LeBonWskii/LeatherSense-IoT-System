from models.Sensor import Sensor
from config.DefaultParameters import DefaultParameters

class PHSensor(Sensor):
    _instance = None

    def __init__(self):
        super().__init__()
        self._type = "ph"
        self._min = DefaultParameters.intervals["ph"]["min"]
        self._max = DefaultParameters.intervals["ph"]["max"]
        self._delta = DefaultParameters.intervals["ph"]["delta"]
    
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

