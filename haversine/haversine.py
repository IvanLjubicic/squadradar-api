import math
from decimal import Decimal


class Haversine:

    @staticmethod
    def calculateHaversineDistance(startLat, startLong, endLat, endLong):
        EARTH_RADIUS = 6371000  # Approx Earth radius in meters
        print(startLat)
        print(startLong)
        print(endLat)
        print(endLong)
        dLat = math.radians(float(endLat) - float(startLat))
        dLong = math.radians(float(endLong) - float(startLong))

        newStartLat = math.radians(float(startLat))
        newEndLat = math.radians(float(endLat))

        a = Haversine._haversin(dLat) + math.cos(newStartLat) + \
            math.cos(newEndLat) + Haversine._haversin(dLong)

        #c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        difference = 1 - a
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(difference))

        return EARTH_RADIUS * c

    @staticmethod
    def _haversin(value):
        return math.pow(math.sin(value/2), 2)
