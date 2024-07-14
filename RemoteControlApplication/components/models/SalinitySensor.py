from .Sensor import Sensor
from .config.DefaultParameters import DefaultParameters

class SalinitySensor(Sensor):
    _instance = None

    def __init__(self):
        super().__init__("salinity", DefaultParameters.intervals["salinity"]["min"], DefaultParameters.intervals["salinity"]["max"], DefaultParameters.intervals["salinity"]["delta"])

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

