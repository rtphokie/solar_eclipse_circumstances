import datetime
import unittest
from pprint import pprint
from zoneinfo import ZoneInfo

import dateutil.parser
import pandas as pd
from skyfield import api

from circumstances import gsfc_eclipse_history_for_coordinate, get_canon_GSFC, get_canon_Espenak, localize
from test_tools import get_jubier_circumstances, get_usno_circumstances

ts = api.load.timescale()
pd.set_option('display.max_rows', None)


class EclipseCircumstances(unittest.TestCase):
    # @unittest.skip('costly')

    def test_get_eclipse_history(self):

        locations = {'Raleigh, NC': {'lat': 35.7945, 'lon': -78.63760, 'ele': 100, 'tz': 'US/Eastern'},
                     'Charlotte, NC': {'lat': 35.2271, 'lon': -80.8431, 'ele': 230, 'tz': 'US/Eastern'},
                     'Albuquerque, NM': {'lat': 35.0844, 'lon': -106.6504, 'ele': 1950, 'tz': 'US/Mountain'},
                     }
        driver = None
        for name, v in locations.items():
            data, driver = gsfc_eclipse_history_for_coordinate(name, v['lat'], v['lon'], ele=v['ele'], driver=driver,
                                                               tz=v['tz'])
            for k, v in data['eclipses'].items():
                if '2023' in k:
                    print(k, name)
                    pprint(v['c1'])
                    pprint(v['c2'])

    def test_narative(self):
        canon, otherdates = get_canon_Espenak()

        locations = {
            'Raleigh, NC': {'lat': 35.7945, 'lon': -78.63760, 'ele': 100, 'tz': 'US/Eastern'},
            'Charlotte, NC': {'lat': 35.2271, 'lon': -80.8431, 'ele': 230, 'tz': 'US/Eastern'},
            'Houston, TX': {'lat': 29.7604, 'lon': -95.3698, 'ele': 15, 'tz': 'US/Central'},
            'Albuquerque, NM': {'lat': 35.0844, 'lon': -106.6504, 'ele': 1950, 'tz': 'US/Mountain'},
        }

        driver = None
        for name, v in locations.items():
            print(name, '-'*20)
            inpath, nearpath, farpath, driver = localize(name, v['lat'], v['lon'], v['tz'], ele=v['ele'],
                                                         driver=driver)

            print('A in path')
            for k in sorted(inpath['T'].keys()):
                v=inpath['T'][k]
                print(k, v['obs'], v['duration'], end=' ')
                print(f"{v['c1']['local_time']} - {v['c4']['local_time']}")
            print()
            print('A near path')
            for k in sorted(nearpath['T'].keys()):
                v=nearpath['T'][k]
                print(k, v['obs'], v['duration'], end=' ')
                print(f"{v['c1']['local_time']} - {v['c4']['local_time']}")
            print()

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
