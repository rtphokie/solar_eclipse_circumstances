import logging
import unittest
from pprint import pprint

from circumstances import solar_eclipse_local


class EclipseCircumstances(unittest.TestCase):
    # @unittest.skip('costly')

    def test_cache(self):
        uut = solar_eclipse_local('Raleigh',
                                  lat=35.7945,
                                  lon=-78.63760,
                                  logginglevel=logging.DEBUG)
        data, years_in_cache, years_not_in_cache =  uut._get_cache_local(years=[2023])
        pprint(years_in_cache)
        pprint(years_not_in_cache)

    def test_constructory(self):
        uut = solar_eclipse_local('Raleigh',
                                  lat=35.7945,
                                  lon=-78.63760,
                                  logginglevel=logging.DEBUG)
        uut.get_year(years=[2023])
        data, years_in_cache, years_not_in_cache, filename_pickle = uut._get_cache_local(years=[2023])
        self.assertTrue(2023 in years_in_cache)

        uut.get_year(years=[1980,2023])
        data, years_in_cache, years_not_in_cache, filename_pickle = uut._get_cache_local(years=[1980,2023])
        self.assertTrue(1980 in years_in_cache)
        self.assertTrue(2023 in years_in_cache)
        #
        # uut.get_year(years=[0,-1310])
        uut.get_year()
        #
        data = uut.get_year(years=[2023])
        pprint(data['by'])


    def test_cities(self):
        locations = {
            'Raleigh, NC': {'lat': 35.7945, 'lon': -78.63760, 'ele': 100, 'tz': 'US/Eastern'},
        }

        driver = None
        for name, v in locations.items():
            inpath, nearpath, farpath, ofnotedata, driver = localize(name, v['lat'], v['lon'], v['tz'], ele=v['ele'],
                                                                     driver=driver, usecache=True)
        pprint(ofnotedata)


if __name__ == '__main__':
    unittest.main()
