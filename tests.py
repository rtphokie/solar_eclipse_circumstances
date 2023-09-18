import datetime
import unittest

import pandas as pd

from circumstances import tse_circumstances, ase_circumstances

pd.set_option('display.max_rows', None)


class EclipseCircumstances(unittest.TestCase):
    def compare_circumstance_calculations(self, results, max_delta_sec=4):
        deltas=[]
        for k, v in results.items():
            if v['us'] is None or v['jubier'] is None:
                self.assertIsNone(v['jubier'], f"expected Jubier's {k} to be None")
                self.assertIsNone(v['us'], f"expected our {k} to be None")
            else:
                if v['jubier'] > v['us']:
                    delta = (v['jubier'] - v['us']).seconds
                else:
                    delta = (v['us'] - v['jubier']).seconds
                deltas.append(delta)
                self.assertLessEqual(delta, max_delta_sec,
                                     f"our {k} calc ({v['us']}) differs from Jubier's ({v['jubier']}) by {delta} seconds")
        print(f"maximum delta: {max(deltas)}")

    def test_20240408_in_path_Ohio(self):
        # 40° 49' 02.57" N	  ↔  	40.81738°	    	3m56.0s (total eclipse)
        # 3m56.5s (lunar limb corrected)
        # 83° 30' 12.49" W	  ↔  	-83.50347°
        # Umbral depth : 99.98%
        # Path width : 181.7km
        # Obscuration : 100.00%
        # C3
        #  	Magnitude at maximum : 1.02660
        # Moon/Sun size ratio : 1.05322
        # Umbral velocity : 0.938km/s
        # Event (ΔT=69.2s)	Date	Time (UT)	Alt	Azi	P	V	LC
        # Start of partial eclipse (C1) : 	2024/04/08	17:55:53.0	+56.5°	189.1°	230°	04.5
        # Start of total eclipse (C2) : 	2024/04/08	19:10:42.0	+50.6°	219.0°	052°	11.2	-0.5s
        # Maximum eclipse (MAX) :        	2024/04/08	19:12:40.1	+50.4°	219.7°	142°	08.2
        # End of total eclipse (C3) :     	2024/04/08	19:14:38.0	+50.2°	220.4°	232°	05.3	+0.0s
        # End of partial eclipse (C4) : 	2024/04/08	20:26:46.5	+39.6°	240.9°	054°	11.6
        # Near Forest Ohio
        lat = '40.81738 N'
        lon = '83.50347 W'
        c1, c2, mid_eclipse, c3, c4 = tse_circumstances(datetime.datetime(2024, 4, 8), lat, lon, ele=276)

        results = {'c1': {'us': c1.datetime,
                          'jubier': datetime.datetime(2024, 4, 8, 17, 55, 53, 0, tzinfo=datetime.timezone.utc)},
                   'c2': {'us': c2.datetime,
                          'jubier': datetime.datetime(2024, 4, 8, 19, 10, 42, 0, tzinfo=datetime.timezone.utc)},
                   'mid': {'us': mid_eclipse.datetime,
                           'jubier': datetime.datetime(2024, 4, 8, 19, 12, 40, 100, tzinfo=datetime.timezone.utc)},
                   'c3': {'us': c3.datetime,
                          'jubier': datetime.datetime(2024, 4, 8, 19, 14, 38, 0, tzinfo=datetime.timezone.utc)},
                   'c4': {'us': c4.datetime,
                          'jubier': datetime.datetime(2024, 4, 8, 20, 26, 46, 500, tzinfo=datetime.timezone.utc)},
                   }

        self.compare_circumstance_calculations(results)

    def test_20240408_not_in_path_NC(self):
        # 35° 47' 40.34" N	  ↔  	35.79454°	    	(partial eclipse)
        # 78° 38' 15.36" W	  ↔  	-78.63760°
        # Obscuration : 78.40%
        # C4
        #  	Magnitude at maximum : 0.81990
        # Moon/Sun size ratio : 1.05328
        # Event (ΔT=69.2s)	Date	Time (UT)	Alt	Azi	P	V	LC
        # Start of partial eclipse (C1) : 	2024/04/08	17:58:50.4	+60.2°	201.6°	242°	04.5
        # Maximum eclipse (MAX) : 	2024/04/08	19:15:55.0	+50.7°	231.4°	322°	02.5
        # End of partial eclipse (C4) : 	2024/04/08	20:29:19.5	+37.8°	249.4°	042°	12.3
        # Raleigh NC
        lat = '35.7945 N'
        lon = '78.63760 W'
        c1, c2, mid_eclipse, c3, c4 = tse_circumstances(datetime.datetime(2024, 4, 8), lat, lon, ele=276)

        results = {'c1': {'us': c1.datetime,
                          'jubier': datetime.datetime(2024, 4, 8, 17, 58, 50, 400, tzinfo=datetime.timezone.utc)},
                   'c2': {'us': None, 'jubier': None},
                   'mid': {'us': mid_eclipse.datetime,
                           'jubier': datetime.datetime(2024, 4, 8, 19, 15, 55, 0, tzinfo=datetime.timezone.utc)},
                   'c3': {'us': None, 'jubier': None},
                   'c4': {'us': c4.datetime,
                          'jubier': datetime.datetime(2024, 4, 8, 20, 29, 19, 500, tzinfo=datetime.timezone.utc)},
                   }

        self.compare_circumstance_calculations(results)

    def test_20231014_in_path_NM(self):
        # 35° 05' 01.93" N	  ↔  	35.08387°	    	4m49.5s (annular eclipse)
        # 4m42.3s (lunar limb corrected)
        # 106° 38' 57.91" W	  ↔  	-106.64942°
        # Antumbral depth : 89.16%
        # Path width : 200.2km
        # Obscuration : 89.59%
        # C1
        #  	Magnitude at maximum : 0.97037
        # Moon/Sun size ratio : 0.94653
        # Antumbral velocity : 1.127km/s
        # Event (ΔT=69.2s)	Date	Time (UT)	Alt	Azi	P	V	LC
        # Start of partial eclipse (C1) : 	2023/10/14	15:13:16.7	+22.6°	118.8°	311°	12.1
        # Start of annular eclipse (C2) : 	2023/10/14	16:34:34.9	+35.8°	136.3°	319°	12.2	+1.7s
        # Maximum eclipse (MAX) :        	2023/10/14	16:36:59.7	+36.2°	136.9°	043°	09.4
        # End of annular eclipse (C3) : 	2023/10/14	16:39:24.4	+36.5°	137.5°	127°	06.7	-5.5s
        # End of partial eclipse (C4) : 	2023/10/14	18:09:29.1	+45.5°	164.7°	134°	07.1
        # Albequerque, NM
        lat = 35.08387
        lon = -106.64942
        c1, c2, mid_eclipse, c3, c4 = ase_circumstances(datetime.datetime(2023, 10, 14), lat, lon, ele=276)

        results = {'c1': {'us': c1.datetime, 'jubier': datetime.datetime(2023, 10, 14, 15, 13, 16, 700, tzinfo=datetime.timezone.utc)},
                   'c2': {'us': c2.datetime, 'jubier': datetime.datetime(2023, 10, 14, 16, 34, 34,900, tzinfo=datetime.timezone.utc)},
         'mid': {'us': mid_eclipse.datetime, 'jubier': datetime.datetime(2023, 10, 14, 16, 36, 59, 700, tzinfo=datetime.timezone.utc)},
                   'c3': {'us': c3.datetime, 'jubier': datetime.datetime(2023, 10, 14, 16, 39, 24, 400, tzinfo=datetime.timezone.utc)},
                   'c4': {'us': c4.datetime, 'jubier': datetime.datetime(2023, 10, 14, 18,  9, 29, 100, tzinfo=datetime.timezone.utc)},
                   }

        self.compare_circumstance_calculations(results)

    def test_20231014_not_in_path_NC(self):
        # 35° 47' 40.20" N	  ↔  	35.79450°	    	(partial eclipse)
        # 78° 38' 15.36" W	  ↔  	-78.63760°
        # Obscuration : 37.12%
        #  	Magnitude at maximum : 0.48747
        # Moon/Sun size ratio : 0.94863
        # Event (ΔT=69.2s)	Date	Time (UT)	Alt	Azi	P	V	LC
        # Start of partial eclipse (C1) : 	2023/10/14	15:56:03.4	+43.4°	157.7°	285°	01.9
        # Maximum eclipse (MAX) :        	2023/10/14	17:20:14.2	+45.7°	187.0°	224°	04.6
        # End of partial eclipse (C4) : 	2023/10/14	18:46:02.1	+39.4°	214.7°	162°	07.
        # Raleigh, NC
        lat = '35.7945 N'
        lon = '78.63760 W'
        c1, c2, mid_eclipse, c3, c4 = ase_circumstances(datetime.datetime(2023, 10, 14), lat, lon, ele=276)

        results = {'c1': {'us': c1.datetime, 'jubier': datetime.datetime(2023, 10, 14, 15, 56,  3, 400, tzinfo=datetime.timezone.utc)},
                   'c2': {'us': None, 'jubier': None},
         'mid': {'us': mid_eclipse.datetime, 'jubier': datetime.datetime(2023, 10, 14, 17, 20, 14, 200, tzinfo=datetime.timezone.utc)},
                   'c3': {'us': None, 'jubier': None},
                   'c4': {'us': c4.datetime, 'jubier': datetime.datetime(2023, 10, 14, 18, 46,  2, 100, tzinfo=datetime.timezone.utc)},
                   }

        self.compare_circumstance_calculations(results)
if __name__ == '__main__':
    unittest.main()
