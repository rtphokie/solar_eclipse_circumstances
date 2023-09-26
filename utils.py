import os

import pandas as pd
from selenium import webdriver
from skyfield.api import Loader, load

ts = load.timescale()

# https://github.com/skyfielders/python-skyfield/issues/445
pd.set_option('display.max_columns', None)
pd.set_option('display.width', 1000)

MOON_RADIUS_KM = 1737.4
SUN_RADIUS_KM = 695700
months = ['', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']


def load_ephemeris(year=2023):
    load = Loader("/var/data")  # centralize local caching of ephemeris files
    if 1899 < year < 2053:
        de = 'de421.bsp'
    elif 1549 < year < 2650:
        # supplants DE430
        # documentation: https://doi.org/10.3847/1538-3881/abd414
        de = 'de440.bsp'
    elif -3000 < year < 3000:
        de = 'de406.bsp'
    elif -13200 < year < 17191:
        # supplants DE431
        # documentation: https://doi.org/10.3847/1538-3881/abd414
        de = 'de406.bsp'
    else:
        raise ValueError(f"unable to find a JPL Lunar Ephemeride for the year {year}")
        # de='de422.bsp'
    eph = load(de)
    m = eph['moon']
    jkl = str(eph).split("\n")
    print(year, de, jkl[1])

    return eph


def decdeg2dms(dd):
    mult = -1 if dd < 0 else 1
    mnt, sec = divmod(abs(dd) * 3600, 60)
    deg, mnt = divmod(mnt, 60)
    return int(mult * deg), int(mult * mnt), mult * sec


def directional_DMS_coordinates(lat, lon):
    latd, latm, lats = decdeg2dms(lat)
    lond, lonm, lons = decdeg2dms(abs(lon))
    if lat < 0:
        NS = 'S'
    else:
        NS = 'N'
    if lon < 0:
        EW = 'W'
    else:
        EW = 'E'
    return EW, NS, latd, latm, lats, lond, lonm, lons


def check_non_zero(x):
    return x > 0


def get_driver():
    driver = None
    os.system("ps -ef | grep -i Chrome | awk '{ print $2 }' | xargs kill")

    options = webdriver.ChromeOptions()
    # options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument(r"--user-data-dir=/Users/trice/Library/Application Support/Google/Chrome")
    options.add_argument(r'--profile-directory=Profile 10')
    driver = webdriver.Chrome(options=options)
    return driver

def localmeantime(utc, longitude):
    """
    :param utc: string Ex. '2008-12-2'
    :param longitude: longitude
    :return: Local Mean Time Timestamp
    """
    lmt = utc + datetime.timedelta(seconds=round(4*60*longitude))
    lmt = lmt.replace(tzinfo=None)
    return lmt

