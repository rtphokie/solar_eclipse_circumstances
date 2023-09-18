import datetime
import math
import unittest
from pprint import pprint

import pandas as pd
from numpy import arcsin
from skyfield.api import Topos, Loader

# https://github.com/skyfielders/python-skyfield/issues/445
pd.set_option('display.max_columns', None)
pd.set_option('display.width', 1000)
load = Loader("/var/data")
planets = load('de421.bsp')
ts = load.timescale()
MOON_RADIUS_KM = 1737.4
SUN_RADIUS_KM = 695700


# url = f"http://xjubier.free.fr/php/xSE_5MCSE_Location_Search.php?FY=1000&TY=1299&ET=T&IS=0&Lat=35.77&Lng=78.63&ES=DateUp&Lang=en&Index=2&Last=7"
# url = f"http://xjubier.free.fr/php/xSE_EclipseInfos.php?Ec=1&Ecl[]=+10000407&Lang=en"


def check_non_zero(x):
    return x > 0


def eclipse_fraction(s, body1, body2):
    '''
    calculates the percentage of the Sun's disk eclipse by the Moon, by calculating the size of the lune in squqre arc seconds
    created for solar eclipses but applicable to any two bodies
    see http://mathworld.wolfram.com/Lune.html
    :param s: separation in degrees
    :param body1: foreground body radius in degrees (Moon)
    :param body2: background body radius in degrees (Sub)
    :return:
    '''
    if s < (body1 + body2):
        a = (body2 + body1 + s) * (body1 + s - body2) * (s + body2 - body1) * (body2 + body1 - s)
        if a > 0:
            lunedelta = 0.25 * math.sqrt(a)
            lune_area = 2 * lunedelta + body2 * body2 * (
                math.acos(((body1 * body1) - (body2 * body2) - (s * s)) / (2 * body2 * s))) - body1 * body1 * (
                            math.acos(((body1 * body1) + (s * s) - (body2 * body2)) / (2 * body1 * s)))
            percent_eclipse = (1 - (lune_area / (math.pi * body2 * body2)))
        else:
            percent_eclipse = 100
    else:
        percent_eclipse = 0
    return percent_eclipse


def apparant_radius(df):
    for label in ['moon', 'sun']:
        if label == 'moon':
            equitorial_radius = MOON_RADIUS_KM
        elif label == 'sun':
            equitorial_radius = SUN_RADIUS_KM
        else:
            raise ValueError(f"unsupported body {label}")
        df[f'{label}_r'] = 180.0 / math.pi * arcsin(equitorial_radius / df[f'{label}_dist'])
    df['ratio'] = df.moon_r / df.sun_r


def alt_az_dist(df, body, label):
    alt, az, distance = body.altaz()
    df[f'{label}_alt'] = alt.degrees
    df[f'{label}_az'] = az.degrees
    df[f'{label}_dist'] = distance.km

def ase_circumstances(start, lat, lon, ele=100, end=None):
    return circumstances(start=start, lat=lat, lon=lon, ele=100, end=end, eclipsetype='annular')

def tse_circumstances(start, lat, lon, ele=100, end=None):
    return circumstances(start=start, lat=lat, lon=lon, ele=100, end=end, eclipsetype='total')

def circumstances(start, lat, lon, ele=100, end=None ,eclipsetype=None):
    if end is None:
        time = ts.utc(start.year, start.month, start.day, 0, range(-2160,
                                                                   2160))  # 3 day span centered on midnight UTC on the day passed, in minute increments.
    else:
        timespan_sec = (end - start).seconds
        time = ts.utc(start.year, start.month, start.day, start.hour, start.minute,
                      range(start.second - 120, start.second + timespan_sec + 120))
    time_first = time[0].utc_jpl()
    time_last = time[-1].utc_jpl()

    place = planets['earth'] + Topos(lat, lon, elevation_m=ele)

    moon = place.at(time).observe(planets['moon']).apparent()
    sun = place.at(time).observe(planets['sun']).apparent()

    df = pd.DataFrame(list(time.utc_datetime()), columns=['datetime'])
    df['separation'] = moon.separation_from(sun).degrees
    alt_az_dist(df, moon, 'moon')
    alt_az_dist(df, sun, 'sun')
    apparant_radius(df)
    df['eclipse_fraction'] = df.apply(lambda x: eclipse_fraction(x['separation'], x['sun_r'], x['moon_r']), axis=1)
    c1, c2, mid_eclipse,  c3, c4 = contact_points(df)
    if end is None and c1 is not None:
        c1, c2, mid_eclipse, c3, c4 = tse_circumstances(c1.datetime, lat, lon,
                                                                     end=c4.datetime)  # refine at higher resolution
    return  c1, c2, mid_eclipse,  c3, c4


def contact_points(df):
    '''
    calculate the 4 contact points plus maximum eclipse
    c1: beginning of partial eclipse
    c2: beginning of total eclipse
    mid eclipse: mid point between c2 and c3, generally the best point to view the corona.
    c3: end of total eclipse
    c4: end of partial eclipse
    :param df: the dataframe containing timestamps separation and fraction of the Sun eclipsed by the Moon
    :return: rows for c1, c2, max_eclipse, c3, c4, and a dataframe sliced with just rows where the Sun is eclipsed.
    '''
    df_eclipsed = df[(df.eclipse_fraction > 0)]
    max_eclipse_fraction = df.eclipse_fraction.max()
    df_eclipsed_max = df[(df.eclipse_fraction == max_eclipse_fraction)]
    c1, c2, max_eclipse, c3, c4 = None, None, None, None, None
    if len(df_eclipsed) > 0:
        c1 = df_eclipsed[df_eclipsed.datetime == df_eclipsed.datetime.min()].iloc[0]
        c4 = df_eclipsed[df_eclipsed.datetime == df_eclipsed.datetime.max()].iloc[0]
        if max_eclipse_fraction > 1:
            c2 = df_eclipsed_max[df_eclipsed_max.datetime == df_eclipsed_max.datetime.min()].iloc[0]
            c3 = df_eclipsed_max[df_eclipsed_max.datetime == df_eclipsed_max.datetime.max()].iloc[0]
        midpoint = round(len(df_eclipsed_max)/2)
        mid_eclipse = df_eclipsed_max.iloc[midpoint]

    return c1, c2, mid_eclipse, c3, c4


class MyTestCase(unittest.TestCase):

    def test_20240408_seattle(self):
        c1, c2, max_eclipse, c3, c4, df = tse_circumstances(datetime.datetime(2024, 4, 8), 47.55414, -122.28822)
        pprint(max_eclipse)
        print(df.eclipse_fraction.max())

    def test_20240408_in_path(self):
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
        # Maximum eclipse (MAX) : 	2024/04/08	19:12:40.1	+50.4°	219.7°	142°	08.2
        # End of total eclipse (C3) : 	2024/04/08	19:14:38.0	+50.2°	220.4°	232°	05.3	+0.0s
        # End of partial eclipse (C4) : 	2024/04/08	20:26:46.5	+39.6°	240.9°	054°	11.6
        lat = '40.81738 N'
        lon = '83.50347 W'
        c1, c2, max_eclipse, c3, c4, df = tse_circumstances(datetime.datetime(2024, 4, 8), lat, lon, ele=276)
        pd.set_option('display.max_rows', None)
        c1_jubier = datetime.datetime(2024, 4, 8, 17, 55, 53, 0, tzinfo=datetime.timezone.utc)
        c1_delta = (c1.datetime - c1_jubier).seconds
        print('c1', c1_delta, c1.datetime, c1_jubier)

        c2_jubier = datetime.datetime(2024, 4, 8, 19, 10, 42, 0, tzinfo=datetime.timezone.utc)
        if c2.datetime > c2_jubier:
            c2_delta = (c2.datetime - c2_jubier).seconds
        else:
            c2_delta = (c2_jubier - c2.datetime).seconds
        print('c2', c2_delta, c2.datetime, c2_jubier)
        self.assertLessEqual(c2_delta, 10)

        max_jubier = datetime.datetime(2024, 4, 8, 19, 12, 40, 200000, tzinfo=datetime.timezone.utc)
        if max_eclipse.datetime > max_jubier:
            max_delta = (max_eclipse.datetime - max_jubier).seconds
        else:
            max_delta = (max_jubier - max_eclipse.datetime).seconds
        print('max', max_delta, max_eclipse.datetime, max_jubier)
        self.assertLessEqual(max_delta, 10)

        c3_jubier = datetime.datetime(2024, 4, 8, 19, 14, 38, 0, tzinfo=datetime.timezone.utc)
        if c3.datetime > c3_jubier:
            c3_delta = (c3.datetime - c3_jubier).seconds
        else:
            c3_delta = (c3_jubier - c3.datetime).seconds
        print('c3', c3_delta, c3.datetime, c3_jubier)
        self.assertLessEqual(c3_delta, 10)

        c4_jubier = datetime.datetime(2024, 4, 8, 20, 26, 46, 600000, tzinfo=datetime.timezone.utc)
        if c4.datetime > c4_jubier:
            c4_delta = (c4.datetime - c4_jubier).seconds
        else:
            c4_delta = (c4_jubier - c4.datetime).seconds
        print('c4', c4_delta, c4.datetime, c4_jubier)
        self.assertLessEqual(c4_delta, 10)

    def test_20240408_out_of_path(self):
        c1, c2, max_eclipse, c3, c4, df = tse_circumstances(datetime.datetime(2024, 4, 8), '35.86146 N', '78.71175 W',
                                                            ele=101)

        pd.set_option('display.max_rows', None)
        # 17:58:45.6
        c1_jubier = datetime.datetime(2024, 4, 8, 17, 58, 45, 600000, tzinfo=datetime.timezone.utc)
        c1_delta = (c1.datetime - c1_jubier).seconds
        print('c1', c1_delta, c1.datetime, c1_jubier)
        print()
        print('c2', c2)
        print('c2', max_eclipse)
        self.assertLessEqual(c1_delta, 10)
        self.assertEqual(c2, None)
        self.assertEqual(max_eclipse, None)
        self.assertEqual(c3, None)

        c4_jubier = datetime.datetime(2024, 4, 8, 20, 29, 18, 900000, tzinfo=datetime.timezone.utc)
        if c4.datetime > c4_jubier:
            c4_delta = (c4.datetime - c4_jubier).seconds
        else:
            c4_delta = (c4_jubier - c4.datetime).seconds
        self.assertLessEqual(c4_delta, 10)

    def test_20240408_no_eclipse(self):
        c1, c2, max_eclipse, c3, c4, df = tse_circumstances(datetime.datetime(2024, 4, 8), '60.75046 N', '-142.47609 W',
                                                            ele=101)

        self.assertEqual(c1, None)
        self.assertEqual(c2, None)
        self.assertEqual(max_eclipse, None)
        self.assertEqual(c3, None)
        self.assertEqual(c4, None)


if __name__ == '__main__':
    unittest.main()
