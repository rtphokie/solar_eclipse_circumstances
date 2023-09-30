import datetime
import unittest
from pprint import pprint
from zoneinfo import ZoneInfo

import dateutil.parser
import pandas as pd
from skyfield import api

from circumstances import solar_eclipse_local
from test_tools import get_jubier_circumstances, get_usno_circumstances

ts = api.load.timescale()
pd.set_option('display.max_rows', None)


class EclipseCircumstances(unittest.TestCase):
    # @unittest.skip('costly')

    def test_cities(self):
        locations = {
        'Raleigh, NC': {'lat': 35.7945, 'lon': -78.63760, 'ele': 100, 'tz': 'US/Eastern'},
        }


        driver=None
        for name, v in locations.items():
            inpath, nearpath, farpath, ofnotedata, driver = localize(name, v['lat'], v['lon'], v['tz'], ele=v['ele'],
                                                                 driver=driver, usecache=True)

        pprint(ofnotedata)

    def test_narative(self):
        canon, otherdates = get_canon_Espenak()

        locations = {
            # 'Raleigh, NC': {'lat': 35.7945, 'lon': -78.63760, 'ele': 100, 'tz': 'US/Eastern'},
            # 'Charlotte, NC': {'lat': 35.2271, 'lon': -80.8431, 'ele': 230, 'tz': 'US/Eastern'},
            # 'Houston, TX': {'lat': 29.7604, 'lon': -95.3698, 'ele': 15, 'tz': 'US/Central'},
            'Albuquerque, NM': {'lat': 35.0844, 'lon': -106.6504, 'ele': 1950, 'tz': 'US/Mountain'},
        }

        driver = None
        for name, v in locations.items():
            print()
            print(name, v['lat'], v['lon'], '-'*20)
            inpath, nearpath, farpath, ofnotedata, driver = localize(name, v['lat'], v['lon'], v['tz'], ele=v['ele'],
                                                         driver=driver, usecache=True)

            print('in   path', len(inpath['A']))
            print('near path', len(nearpath['A']))
            total=0
            for k, v in farpath.items():
                total+=len(v)
            for k, v in nearpath.items():
                total+=len(v)
            for k, v in inpath.items():
                total+=len(v)
            print('total', total)

            for path in ['in_path', 'near_path']:
                print()
                print(f"Looking at eclipses passing {path} {name},")
                for eclipsetype, data in ofnotedata.items():
                    if data[f'last_{path}'] is None:
                        print(f" looking back to 1500 BC, a {eclipsetype} has not passed {path} ")
                    else:
                        print(f"the last {eclipsetype} was {data[f'last_{path}']['c1']['local_iso']}, ")
                    if data[f'next_{path}'] is None:
                        print(f" a {eclipsetype} wont pass again {path} through 3000 AD. ")
                    else:
                        print(f"The next will be {data[f'next_{path}']['c1']['local_iso']}. ")

            # pprint (ofnotedata)

    def testlkjasdf(self):
        now =  '~2023-09-27'
        then = '-1293-07-05'
        jkl=[now, then]

        print(then < now)
        pprint(jkl)
        jkl =  sorted(jkl)
        pprint(jkl)

    @unittest.skip('needs update')
    def test_get_gsfc_canon(self):
        data = get_canon_GSFC()
        print(len(data))
        self.assertEqual(11898, len(data))
        pprint(data)

    def test_canon(self):
        data = get_canon_Espenak(year_start=-1499, year_end=3000)
        self.assertEqual(len(data), 10644)


class EclipseCircumstancesJubier(unittest.TestCase):

    def compare_circumstance_calculations(self, results, max_delta_sec=10):
        delta_jubier = []
        for k, v in results.items():
            if v['us'] is None or v['jubier'] is None:
                self.assertIsNone(v['jubier'], f"expected Jubier's {k} to be None")
                self.assertIsNone(v['us'], f"expected our {k} to be None")
            else:
                delta_seconds = abs(v['us'] - v['jubier']) * 86400  # convert ordinal day to seconds
                delta_jubier.append(delta_seconds)
                # self.assertLessEqual(delta_seconds, max_delta_sec, f"our {k} calc ({v['us']}) differs from Jubier's ({v['jubier']}) by {delta_seconds} seconds")
        print(f"maximum delta from jubier calculations: {max(delta_jubier):.1f} seconds")
        # if 'usno' in v:
        #     delta_usno = []
        #     for k, v in results.items():
        #         if v['us'] is None or v['usno'] is None:
        #             self.assertIsNone(v['usno'], f"expected USNO's {k} to be None")
        #             self.assertIsNone(v['us'], f"expected our {k} to be None")
        #         else:
        #             if v['usno'] > v['us']:
        #                 delta = (v['usno'] - v['us']) * 86400
        #             else:
        #                 delta = (v['us'] - v['usno']) * 86400
        #             delta_usno.append(delta)
        #             self.assertLessEqual(delta, max_delta_sec,
        #                                  f"our {k} calc ({v['us']}) differs from the USNO's ({v['usno']}) by {delta:.1f} seconds")
        #     print(f"maximum delta from USNO calculations: {max(delta_usno):.1f} seconds")

    # @unittest.skip('not yet updated')
    def test_20240408_in_path(self):
        # Near Forest Ohio
        lat = 40.81738
        lon = -83.50347
        ele = 284
        c1, c2, mid, c3, c4 = circumstances(ts.utc(2024, 4, 8), lat, lon, ele=ele)
        jubier = get_jubier_circumstances(latstr=lat, lonstr=lon, height=ele, eclipse='+20240408')
        usno = get_usno_circumstances(lat=lat, lon=lon, alt=ele, eclipse='12024', datestr='2024-04-08')
        results = {
            'c1': {'us': c1.ordinal, 'jubier': jubier['c1']['ordinal'], 'usno': usno['c1']['ordinal']},
            'c2': {'us': c2.ordinal, 'jubier': jubier['c2']['ordinal'], 'usno': usno['c2']['ordinal']},
            'mid': {'us': mid.ordinal, 'jubier': jubier['max']['ordinal'], 'usno': usno['mid']['ordinal']},
            'c3': {'us': c3.ordinal, 'jubier': jubier['c3']['ordinal'], 'usno': usno['c3']['ordinal']},
            'c4': {'us': c4.ordinal, 'jubier': jubier['c4']['ordinal'], 'usno': usno['c4']['ordinal']},
        }
        self.compare_circumstance_calculations(results)

    def test_20240408_not_in_path(self):
        # Raleigh NC
        lat = 35.7945
        lon = -78.63760
        ele = 96
        c1, c2, mid, c3, c4 = circumstances(ts.utc(2024, 4, 8), lat, lon, ele=ele)
        jubier = get_jubier_circumstances(latstr=lat, lonstr=lon, height=ele, eclipse='+20240408')
        usno = get_usno_circumstances(lat=lat, lon=lon, alt=ele, eclipse='12024', datestr='2024-04-08')
        results = {
            'c1': {'us': c1.ordinal, 'jubier': jubier['c1']['ordinal'], 'usno': usno['c1']['ordinal']},
            'c2': {'us': None, 'jubier': jubier['c2']['ordinal'], 'usno': usno['c2']['ordinal']},
            'mid': {'us': mid.ordinal, 'jubier': jubier['max']['ordinal'], 'usno': usno['mid']['ordinal']},
            'c3': {'us': None, 'jubier': jubier['c3']['ordinal'], 'usno': usno['c3']['ordinal']},
            'c4': {'us': c4.ordinal, 'jubier': jubier['c4']['ordinal'], 'usno': usno['c4']['ordinal']},
        }
        self.compare_circumstance_calculations(results)

    def test_20170821_not_in_path(self):
        # Raleigh NC
        lat = 35.7945
        lon = -78.63760
        ele = 111
        c1, c2, mid, c3, c4 = circumstances(ts.utc(2017, 8, 21), lat, lon, ele=ele)
        print(c1)
        print(c1.tt.utc_jpl())
        jubier = get_jubier_circumstances(latstr=lat, lonstr=lon, height=ele, eclipse='+20170821')
        usno = get_usno_circumstances(lat=lat, lon=lon, alt=ele, eclipse='22017', datestr='2017-08-21')
        results = {
            'c1': {'us': c1.ordinal, 'jubier': jubier['c1']['ordinal'], 'usno': usno['c1']['ordinal']},
            'c2': {'us': None, 'jubier': jubier['c2']['ordinal'], 'usno': usno['c2']['ordinal']},
            'mid': {'us': mid.ordinal, 'jubier': jubier['max']['ordinal'], 'usno': usno['mid']['ordinal']},
            'c3': {'us': None, 'jubier': jubier['c3']['ordinal'], 'usno': usno['c3']['ordinal']},
            'c4': {'us': c4.ordinal, 'jubier': jubier['c4']['ordinal'], 'usno': usno['c4']['ordinal']},
        }
        self.compare_circumstance_calculations(results)

    # @unittest.skip('not yet updated')
    def test_20231014_in_path(self):
        # Albequerque, NM
        lat = 35.08387
        lon = -106.64942
        ele = 1490
        c1, c2, mid, c3, c4 = circumstances(ts.utc(2023, 10, 14), lat, lon, ele=ele)

        jubier = get_jubier_circumstances(latstr=lat, lonstr=lon, height=ele, eclipse='+20231014')
        usno = get_usno_circumstances(lat=lat, lon=lon, alt=ele, eclipse='22023', datestr='2023-10-14')

        results = {
            'c1': {'us': c1.ordinal, 'jubier': jubier['c1']['ordinal'], 'usno': usno['c1']['ordinal']},
            'c2': {'us': c2.ordinal, 'jubier': jubier['c2']['ordinal'], 'usno': usno['c2']['ordinal']},
            'mid': {'us': mid.ordinal, 'jubier': jubier['max']['ordinal'], 'usno': usno['mid']['ordinal']},
            'c3': {'us': c3.ordinal, 'jubier': jubier['c3']['ordinal'], 'usno': usno['c3']['ordinal']},
            'c4': {'us': c4.ordinal, 'jubier': jubier['c4']['ordinal'], 'usno': usno['c4']['ordinal']},
        }
        self.compare_circumstance_calculations(results)

    # @unittest.skip('not yet updated')
    def test_20231014_not_in_path(self):
        # Raleigh, NC
        lat = 35.7945
        lon = -78.6376
        ele = 96
        c1, c2, mid, c3, c4 = circumstances(ts.utc(2023, 10, 14), lat, lon, ele=ele)

        jubier = get_jubier_circumstances(latstr=lat, lonstr=lon, height=ele, eclipse='+20231014')
        usno = get_usno_circumstances(lat=lat, lon=lon, alt=ele, eclipse='22023', datestr='2023-10-14')

        results = {
            'c1': {'us': c1.ordinal, 'jubier': jubier['c1']['ordinal'], 'usno': usno['c1']['ordinal']},
            'c2': {'us': None, 'jubier': jubier['c2']['utc_datetime'], 'usno': usno['c2']['datetime_utc']},
            'mid': {'us': mid.ordinal, 'jubier': jubier['max']['ordinal'], 'usno': usno['mid']['ordinal']},
            'c3': {'us': None, 'jubier': jubier['c3']['utc_datetime'], 'usno': usno['c3']['datetime_utc']},
            'c4': {'us': c4.ordinal, 'jubier': jubier['c4']['ordinal'], 'usno': usno['c4']['ordinal']},
        }
        self.compare_circumstance_calculations(results)

    # @unittest.skip('not yet updated')
    def test_20231014_way_not_in_path(self):
        # Bangor Maine
        lat = 44.8016
        lon = -68.7712
        ele = 36
        c1, c2, mid, c3, c4 = circumstances(ts.utc(2023, 10, 14), lat, lon, ele=ele)

        jubier = get_jubier_circumstances(latstr=lat, lonstr=lon, height=ele, eclipse='+20231014')
        usno = get_usno_circumstances(lat=lat, lon=lon, alt=ele, eclipse='22023', datestr='2023-10-14')

        results = {
            'c1': {'us': c1.ordinal, 'jubier': jubier['c1']['ordinal'], 'usno': usno['c1']['ordinal']},
            'c2': {'us': None, 'jubier': jubier['c2']['utc_datetime'], 'usno': usno['c2']['datetime_utc']},
            'mid': {'us': mid.ordinal, 'jubier': jubier['max']['ordinal'], 'usno': usno['mid']['ordinal']},
            'c3': {'us': None, 'jubier': jubier['c3']['utc_datetime'], 'usno': usno['c3']['datetime_utc']},
            'c4': {'us': c4.ordinal, 'jubier': jubier['c4']['ordinal'], 'usno': usno['c4']['ordinal']},
        }
        self.compare_circumstance_calculations(results)


if __name__ == '__main__':
    unittest.main()
