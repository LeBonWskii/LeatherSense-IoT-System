from abc import ABC, abstractmethod
import sys
sys.path.append("../..")
from database.models.database import Database

class Sensor(ABC):
    def __init__(self, type, min_value=None, max_value=None, delta=None, value=None):
        self._type = type
        self._min = min_value
        self._max = max_value
        self._delta = delta
        self._value = value
        if self._type is None:
            ret
        try:
            connection = Database().connect()
            cursor = connection.cursor()
            query = '''
                REPLACE INTO parameter (type, min, max, delta)
                VALUES (%s, %s, %s, %s);
            '''
            cursor.execute(query, (self._type, self._min, self._max, self._delta))
            connection.commit()
            cursor.close()
        except Exception as e:
            print(f"[Sensor] Error: {e}")
    
    @property
    def type(self):
        return self._type
    
    @property
    def min(self):
        return self._min

    @min.setter
    def min(self, min_value):
        try:
            database = Database()
            connection = database.connect()
            cursor = connection.cursor()
            query = '''
                UPDATE parameter
                SET min = %s
                WHERE type = %s;
            '''
            cursor.execute(query, (min_value, self._type))
            connection.commit()
            cursor.close()
            self._min = min_value
        except Exception as e:
            print(f"[Sensor] Error: {e}")

    @property
    def max(self):
        return self._max

    @max.setter
    def max(self, max_value):
        try:
            database = Database()
            connection = database.connect()
            cursor = connection.cursor()
            query = '''
                UPDATE parameter
                SET max = %s
                WHERE type = %s;
            '''
            cursor.execute(query, (max_value, self._type))
            connection.commit()
            cursor.close()
            self._max = max_value
        except Exception as e:
            print(f"[Sensor] Error: {e}")
        self._max = max_value
    
    @property
    def delta(self):
        return self._delta
    
    @delta.setter
    def delta(self, delta):
        try:
            database = Database()
            connection = database.connect()
            cursor = connection.cursor()
            query = '''
                UPDATE parameter
                SET delta = %s
                WHERE type = %s;
            '''
            cursor.execute(query, (delta, self._type))
            connection.commit()
            cursor.close()
            self._delta = delta
        except Exception as e:
            print(f"[Sensor] Error: {e}")
        self._delta = delta

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, value):
        self._value = value
