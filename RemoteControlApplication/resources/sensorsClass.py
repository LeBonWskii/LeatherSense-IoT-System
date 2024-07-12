class Sensor:
    def __init__(self, sensor_type, min_value=None, max_value=None):
        self.sensor_type = sensor_type
        self.__min_value = min_value
        self.__max_value = max_value

    def set_parameters(self, min_value=None, max_value=None):
        if min_value is not None:
            self.__min_value = min_value
        if max_value is not None:
            self.__max_value = max_value

    def get_max_value(self):
        return self.__max_value
    
    def get_min_value(self):
        return self.__min_value
    
    def validate_value(self, min_value=None, max_value=None):
        if min_value is not None and min_value > self.__max_value: #user can't set min value greater than actual max value
            return False
        if max_value is not None and max_value < self.__min_value: #user can't set max value lower than actual min value
            return False
        return True


    
