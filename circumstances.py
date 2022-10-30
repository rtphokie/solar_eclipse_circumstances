import unittest
import datetime
from skyfield.api import Topos, Loader
import pandas as pd
import numpy as np
import math

pd.set_option('display.max_columns', None)
pd.set_option('display.width', 1000)

MOON_RADIUS_KM = 1737.4
SUN_RADIUS_KM = 695700


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
    '''
    calculate the apparant angular radius of the Sun and Moon, as well their ratio.
    :param df: dataframe containing moon_dist and sun_dist columns representing the distance in km
    '''
    for label in ['moon', 'sun']:
        if label == 'moon':
            equitorial_radius = MOON_RADIUS_KM
        elif label == 'sun':
            equitorial_radius = SUN_RADIUS_KM
        else:
            raise ValueError(f"unsupported body {label}")
        df[f'{label}_r'] = 180.0 / math.pi * np.arcsin(equitorial_radius / df[f'{label}_dist'])
    df['ratio'] = df.moon_r / df.sun_r


def alt_az_dist(df, body, label):
    '''
    altitude, azimuth and distance (in km) of the body calcualted across the passed dataframe

    :param df: df
    :param body: Skyfield body (sun or moon)
    :param label: body name, lowercase (sun or moon)
    :return:
    '''
    alt, az, distance = body.altaz()
    df[f'{label}_alt'] = alt.degrees
    df[f'{label}_az'] = alt.degrees
    df[f'{label}_dist'] = distance.km


def main(start, lat, lon, ele=100, end=None):
    load = Loader("/var/data")
    planets = load('de421.bsp')
    ts = load.timescale()

    if end is None:
        # 3 day span centered on midnight UTC on the day passed, in minute increments.
        time = ts.utc(start.year, start.month, start.day, 0, range(-2160, 2160))
    else:
        # span across the passed start and stop times with 2 additional minutes on each end
        timespan_sec = (end - start).seconds
        time = ts.utc(start.year, start.month, start.day, start.hour, start.minute,
                      range(start.second - 120, start.second + timespan_sec + 120))

    place = planets['earth'] + Topos(lat, lon, elevation_m=ele)

    moon = place.at(time).observe(planets['moon']).apparent()
    sun = place.at(time).observe(planets['sun']).apparent()

    df = pd.DataFrame(list(time.utc_datetime()), columns=['datetime'])
    df['separation'] = moon.separation_from(sun).degrees
    alt_az_dist(df, moon, 'moon')
    alt_az_dist(df, sun, 'sun')
    apparant_radius(df)
    df['eclipse_fraction'] = df.apply(lambda x: eclipse_fraction(x['separation'], x['sun_r'], x['moon_r']), axis=1)
    c1, c2, c3, c4, df_eclipsed, max_eclipse = contact_points(df)
    if end is None and c1 is not None:
        # refine at second resolution
        c1, c2, max_eclipse, c3, c4, df_eclipsed = main(c1.datetime, lat, lon, end=c4.datetime)

    return c1, c2, max_eclipse, c3, c4, df_eclipsed


def contact_points(df):
    '''
    calculate the 4 contact points plus maximum eclipse
    c1: beginning of partial eclipse
    c2: beginning of total eclipse
    maximum eclipse: center of discs of the Sun and Moon are at their closest
    c3: end of total eclipse
    c4: end of partial eclipse
    :param df: the dataframe containing timestamps separation and fraction of the Sun eclipsed by the Moon
    :return: rows for c1, c2, max_eclipse, c3, c4, and a dataframe sliced with just rows where the Sun is eclipsed.
    '''
    df_eclipsed = df[(df.eclipse_fraction > 0)]
    df_eclipsed_total = df[(df.eclipse_fraction >= 1)]
    c1, c2, max_eclipse, c3, c4 = None, None, None, None, None
    if len(df_eclipsed) > 0:
        c1 = df_eclipsed[df_eclipsed.datetime == df_eclipsed.datetime.min()].iloc[0]
        c4 = df_eclipsed[df_eclipsed.datetime == df_eclipsed.datetime.max()].iloc[0]
    if len(df_eclipsed_total) > 0:
        c2 = df_eclipsed_total[df_eclipsed_total.datetime == df_eclipsed_total.datetime.min()].iloc[0]
        c3 = df_eclipsed_total[df_eclipsed_total.datetime == df_eclipsed_total.datetime.max()].iloc[0]
        max_eclipse = df_eclipsed_total[df_eclipsed_total.separation == df_eclipsed_total.separation.min()]
        if len(max_eclipse) > 1:
            max_eclipse = max_eclipse[max_eclipse.ratio == max_eclipse.ratio.max()]
        max_eclipse = max_eclipse.iloc[0]
    return c1, c2, c3, c4, df_eclipsed, max_eclipse


class MyTestCase(unittest.TestCase):

    def test_20240408_in_path(self):
        c1, c2, max_eclipse, c3, c4, df = main(datetime.datetime(2024, 4, 8), '40.81629 N', '83.50467 W', ele=276)
        pd.set_option('display.max_rows', None)
        c1_jubier = datetime.datetime(2024, 4, 8, 17, 55, 53, 0, tzinfo=datetime.timezone.utc)
        c1_delta = (c1.datetime - c1_jubier).seconds
        self.assertLessEqual(c1_delta, 10)

        c2_jubier = datetime.datetime(2024, 4, 8, 19, 10, 42, 0, tzinfo=datetime.timezone.utc)
        if c2.datetime > c2_jubier:
            c2_delta = (c2.datetime - c2_jubier).seconds
        else:
            c2_delta = (c2_jubier - c2.datetime).seconds
        self.assertLessEqual(c2_delta, 10)

        max_jubier = datetime.datetime(2024, 4, 8, 19, 12, 40, 200000, tzinfo=datetime.timezone.utc)
        if max_eclipse.datetime > max_jubier:
            max_delta = (max_eclipse.datetime - max_jubier).seconds
        else:
            max_delta = (max_jubier - max_eclipse.datetime).seconds
        self.assertLessEqual(max_delta, 10)

        c3_jubier = datetime.datetime(2024, 4, 8, 19, 14, 38, 0, tzinfo=datetime.timezone.utc)
        if c3.datetime > c3_jubier:
            c3_delta = (c3.datetime - c3_jubier).seconds
        else:
            c3_delta = (c3_jubier - c3.datetime).seconds
        self.assertLessEqual(c3_delta, 10)

        c4_jubier = datetime.datetime(2024, 4, 8, 20, 26, 46, 600000, tzinfo=datetime.timezone.utc)
        if c4.datetime > c4_jubier:
            c4_delta = (c4.datetime - c4_jubier).seconds
        else:
            c4_delta = (c4_jubier - c4.datetime).seconds
        self.assertLessEqual(c4_delta, 10)

    def test_20240408_out_of_path(self):
        c1, c2, max_eclipse, c3, c4, df = main(datetime.datetime(2024, 4, 8), '35.7796 N', '78.6382 W', ele=101)

        pd.set_option('display.max_rows', None)
        c1_jubier = datetime.datetime(2024, 4, 8, 17, 58, 49, 700000, tzinfo=datetime.timezone.utc)
        c1_delta = (c1.datetime - c1_jubier).seconds
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
        c1, c2, max_eclipse, c3, c4, df = main(datetime.datetime(2024, 4, 8), '60.75046 N', '-142.47609 W', ele=101)

        self.assertEqual(c1, None)
        self.assertEqual(c2, None)
        self.assertEqual(max_eclipse, None)
        self.assertEqual(c3, None)
        self.assertEqual(c4, None)

    def test_20170821_in_path(self):
        # Santee, SC
        c1, c2, max_eclipse, c3, c4, df = main(datetime.datetime(2017, 8, 21), '33.54925 N', '80.50248W', ele=276)
        pd.set_option('display.max_rows', None)
        c1_jubier = datetime.datetime(2017, 8, 21, 17, 14, 48, 400000, tzinfo=datetime.timezone.utc)
        c1_delta = (c1.datetime - c1_jubier).seconds
        self.assertLessEqual(c1_delta, 10)

        c2_jubier = datetime.datetime(2017, 8, 21, 18, 43, 32, 700000, tzinfo=datetime.timezone.utc)
        if c2.datetime > c2_jubier:
            c2_delta = (c2.datetime - c2_jubier).seconds
        else:
            c2_delta = (c2_jubier - c2.datetime).seconds
        self.assertLessEqual(c2_delta, 10)

        max_jubier = datetime.datetime(2017, 8, 21, 18, 44, 50, 400000, tzinfo=datetime.timezone.utc)
        if max_eclipse.datetime > max_jubier:
            max_delta = (max_eclipse.datetime - max_jubier).seconds
        else:
            max_delta = (max_jubier - max_eclipse.datetime).seconds
        self.assertLessEqual(max_delta, 10)

        c3_jubier = datetime.datetime(2017, 8, 21, 18, 46, 7, 900000, tzinfo=datetime.timezone.utc)
        if c3.datetime > c3_jubier:
            c3_delta = (c3.datetime - c3_jubier).seconds
        else:
            c3_delta = (c3_jubier - c3.datetime).seconds
        self.assertLessEqual(c3_delta, 10)

        c4_jubier = datetime.datetime(2017, 8, 21, 20, 7, 51, 800000, tzinfo=datetime.timezone.utc)
        if c4.datetime > c4_jubier:
            c4_delta = (c4.datetime - c4_jubier).seconds
        else:
            c4_delta = (c4_jubier - c4.datetime).seconds
        self.assertLessEqual(c4_delta, 10)


if __name__ == '__main__':
    unittest.main()
