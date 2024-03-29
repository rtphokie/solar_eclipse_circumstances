import logging
import logging
import unittest
from pprint import pprint

from circumstances import solar_eclipse_local, get_eclipse_path, distance_to_path, get_canon_Espenak
from metreport import report_20231013, main


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

    def test_distance(self):
        results = get_eclipse_path(name='+2023-10-14', eclipsetype='A')
        self.assertEqual(107, len(results))

        th_data, mindist, bearing, bearing_dir = distance_to_path(name='+2023-10-14', eclipsetype='A', lat=35.7945,
                                                                  lon=-78.63760)
        print(mindist, bearing, bearing_dir)

    def test_report(self):
        # lat = 36.96
        # market = Bowling Green
        # city = Bowling Green, KY
        # state = KY
        # tz = US/Central
        # lon = -86.49
        # ele = 159
        s, driver = report_20231013(cityname='Bowling Green, KY', DMA='Bowling Green', lat=36.96, lon=-86.49, generate_csv=True)
        driver = None
        return
        s, driver = report_20231013(cityname='Albuquerque, NM', DMA='Albuquerque-Santa Fe', lat=35.0844, lon=-106.6504,
                                    driver=driver, generate_csv=True)
        self.assertTrue('Maximum eclipse: 10:36:52 AM when the Sun will be 89.6% obscured by the Moon' in s)

        s, driver = report_20231013(cityname='Raleigh, NC', DMA='Raleigh-Durham (Fayetteville)', lat=35.7945,
                                    lon=-78.63760,
                                    driver=driver, generate_csv=True)
        self.assertTrue(
            'Between 1500 BC and 3000 AD, a total of 1599 solar eclipses have been visible from' in s)
    #
    #     s, driver = report_20231013(cityname='Houston, TX', DMA='Houston', lat=29.7604, lon=-95.3698, driver=driver)
    #     self.assertTrue('The ~110 mile wide path of annularity is 182 miles to the southwest')
    #
    #     s, driver = report_20231013(cityname='Portland, OR', DMA='Portland', lat=45.5152, lon=-122.6784, driver=driver)
    #
    def test_generate_reports(self):
        main()

    def test_canon_Espenak(self):
        canon, otherdates = get_canon_Espenak()
        for k, v in canon.items():
            if k.startswith('-'):
                continue
            if 'E' in v['ge_lon']:
                continue
            lon=int(v['ge_lon'].replace('W', ''))*-1
            if lon > -180 and v['eclipse_type'] == 'A':
                print (k, v['eclipse_type'], v['ge_lat'], v['ge_lon'])
                print(f"https://eclipsewise.com/solar/SEping/2001-2100/SE2012-05-20A.gif")

if __name__ == '__main__':
    unittest.main()
