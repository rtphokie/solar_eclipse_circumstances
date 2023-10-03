import logging
import unittest
from pprint import pprint

from circumstances import solar_eclipse_local
from metreport import report_20231013, report_20240408, report_20170821


class EclipseCircumstances(unittest.TestCase):
    # @unittest.skip('costly')

    def test_cache(self):
        uut = solar_eclipse_local('Raleigh',
                                  lat=35.7945,
                                  lon=-78.63760,
                                  logginglevel=logging.DEBUG)
        data, years_in_cache, years_not_in_cache = uut._get_cache_local(years=[2023])
        pprint(years_in_cache)
        pprint(years_not_in_cache)

    def test_constructory(self):
        uut = solar_eclipse_local('Albuquerque, NM',
                                  lat=35.0844,
                                  lon=-106.6504,
                                  logginglevel=logging.DEBUG)
        uut.get_year(years=[2023])
        data, years_in_cache, years_not_in_cache, filename_pickle = uut._get_cache_local(years=[2023])
        self.assertTrue(2023 in years_in_cache)

        uut.get_year(years=[1980, 2023])
        data, years_in_cache, years_not_in_cache, filename_pickle = uut._get_cache_local(years=[1980, 2023])
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
            uut = solar_eclipse_local(name, v['lat'], v['lon'], logginglevel=logging.INFO)
            inpath, nearpath, farpath, ofnotedata = uut.localize(years=[2023])
        pprint(ofnotedata)

    def test_report(self):
        driver=None
        s, driver = report_20231013(cityname='Albuquerque, NM', DMA='Albuquerque', lat=35.0844, lon=-106.6504, driver=driver)
        self.assertTrue('Maximum eclipse: 10:36:52 AM when the Sun will be 89.6% obscured by the Moon' in s)

        s,driver = report_20231013(cityname='Raleigh, NC', DMA='Raleigh-Fayetteville', lat=35.7945, lon=-78.63760, driver=driver)
        self.assertTrue('Between 1500 BC and 3000 AD, a total of 1599 solar eclipses have been visible from the Raleigh-'in s)

        # s,driver = report_20231013(cityname='Houston, TX', DMA='Houston', lat=29.7604, lon= -95.3698, driver=driver)
        # self.assertTrue('Between 1500 BC and 3000 AD, a total of 1599 solar eclipses have been visible from the Raleigh-'in s)

if __name__ == '__main__':
    unittest.main()
