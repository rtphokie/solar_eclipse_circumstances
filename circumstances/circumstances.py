import datetime
import logging
import pickle
from logging import Formatter
from logging.handlers import RotatingFileHandler
from zoneinfo import ZoneInfo

import dateutil.parser
import pandas as pd
import requests_cache
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait
from skyfield.api import load
from timezonefinder import TimezoneFinder

from utils import get_driver, directional_DMS_coordinates

ts = load.timescale()
tf = TimezoneFinder()  # reuse

# https://github.com/skyfielders/python-skyfield/issues/445
pd.set_option('display.max_columns', None)
pd.set_option('display.width', 1000)

MOON_RADIUS_KM = 1737.4
SUN_RADIUS_KM = 695700
months = ['', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']


# useful URLS
# Xavier Jubier's site
# url = f"http://movingfree.fr/php/xSE_5MCSE_Location_Search.php?FY=1000&TY=1299&ET=T&IS=0&Lat=35.77&Lng=78.63&ES=DateUp&Lang=en&Index=2&Last=7"
# url = f"http://xjubier.free.fr/php/xSE_EclipseInfos.php?Ec=1&Ecl[]=+10000407&Lang=en"

class solar_eclipse_local(object):

    def __init__(self, name, lat, lon, ele=None, timezone=None, places=2, driver=None,
                 logginglevel=logging.INFO):
        self.name = name
        self.lat = round(lat, places)
        self.lon = round(lon, places)
        self.ele = ele
        self.timezone = timezone
        self.key = None
        self.cachedir = './caches'
        self.session = requests_cache.CachedSession(f"{self.cachedir}/http.sqllite")
        self.logger = self._setup_logging('local', level=logginglevel)
        self.driver = driver

        if self.ele is None:
            self.ele = self._get_elevation(self.lat, self.lon)

        if self.timezone is None:
            self.timezone = tf.timezone_at(lng=lon, lat=lat)
            self.logger.debug(f"found {self.name} in the {self.timezone} timezone")

        self.key = f"{lat},{lon},{ele}"
        self.logger.info('-' * 20)
        self.logger.info(f"instantiated {self.name} ({self.lat},{self.lon}), ele {self.ele}m in {self.timezone}")

    def _get_elevation(self, lat, lon):
        url = f'https://api.opentopodata.org/v1/test-dataset?locations={lat},{lon}'
        r = self.session.get(url)
        data_elevation = r.json()
        try:
            elevation = round(data_elevation['results'][0]['elevation'])
            self.logger.debug(f"found elevation for {self.name} of {self.ele} meters, from cache {r.from_cache}")
        except Exception as e:
            elevation = 0
            self.logger.warning(f"failed to find elevation for {self.name}: {e}")
        try:
            if not r.from_cache:
                self.logger.warning(f"found elevation for {self.name} not from cache")
        except Exception:
            pass
        return elevation

    def _setup_logging(self, name,
                       level=logging.WARNING,
                       logformat="[%(asctime)s] %(levelname)s [%(name)s.%(funcName)s:%(lineno)d] %(message)s",
                       datefmt='%Y-%m-%dT%H:%M:%S', ):
        logger = logging.getLogger(name)
        logger.setLevel(level)
        formatter = Formatter(logformat, datefmt=datefmt)
        file_handler = RotatingFileHandler('./logs/local.log', maxBytes=1024, backupCount=5)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        logging.getLogger("requests_cache").setLevel(logging.WARNING)
        return logger

    def _get_cache_local(self, years=None):
        filename_pickle = f'caches/gsfc_local/{self.lat},{self.lon}.pickle'
        years_in_cache = []
        years_not_in_cache = []

        try:
            fp = open(filename_pickle, 'rb')
            data = pickle.load(fp)
            fp.close()
        except Exception as e:
            data = {}
            self.logger.warning(f"{e}")
        if self.key not in data:
            years_not_in_cache = years.copy()
        else:
            self.logger.debug(f"{len(data[self.key]['centuries_checked'])} centuries in cache")
            for year in years:
                century = int(year / 100)
                if century in data[self.key]['centuries_checked']:
                    years_in_cache.append(year)
                else:
                    years_not_in_cache.append(year)
        return data, years_in_cache, years_not_in_cache, filename_pickle

    def get_year(self, years):
        '''
        fetches eclipses visible for location defined in the object from the
        the NASA GSFC javascript eclipse site https://eclipse.gsfc.nasa.gov
        :param years: years to gather eclipses for (default, all years between 1500 BC and 3000 AD)
        :return: dictionary
        '''
        if years is None:
            years = list(range(-1401, 3000, 100))
        data, years_in_cache, years_not_in_cache, filename_pickle = self._get_cache_local(years=years)
        self.logger.debug(f"{years_in_cache} in cache for {self.name}")
        self.logger.debug(f"{years_not_in_cache} not in cache for {self.name}")

        if len(years_not_in_cache) > 0:
            self.logger.info(f"fetching {years_not_in_cache} for {self.name}")
            EW, NS, latd, latm, lats, lond, lonm, lons = directional_DMS_coordinates(self.lat, self.lon)
            url = 'https://eclipse.gsfc.nasa.gov/JSEX/JSEX-USA.html'
            if self.driver is None:
                self.driver = get_driver()
            if self.key not in data.keys():
                data[self.key] = {'city': self.name, 'lat': self.lat, 'lon': self.lon, 'ele': self.ele, 'eclipses': {},
                                  'by_year': {}, 'centuries_checked': []}

            enter_coordinates(self.driver, self.name, latd, latm, lats, NS, lond, lonm, lons, EW)
            for year in years_not_in_cache:
                button_no = int((year / 100) + 15)
                row = int(button_no / 5) + 2
                col = (button_no % 5) + 1
                self.logger.debug(f"fetching {year}, button ({row},{col}) for {self.name}")
                eclipses, by_year = click_century_buttons(self.driver, self.ele, row=row, column=col)
                data[self.key]['eclipses'].update(eclipses)
                data[self.key]['by_year'].update(by_year)
                data[self.key]['centuries_checked'].append(int(year / 100))

            fp = open(filename_pickle, 'wb')
            pickle.dump(data, fp)
            fp.close()

        return data[self.key]

    def localize(self, years=[2023, 2024]):
        # name, lat, lon, tz, ele=0, driver=None, usecache=True, row=None, column=None):
        targetdates = {'A': '+2023-10-14', 'T': '+2024-04-08', 'H': '+2023-10-01', 'P': '+2023-10-01'}
        superlatives = {'last_in_path': None, 'last_near_path': None,
                        'next_in_path': None, 'next_near_path': None}
        prevnextevents = {'A': superlatives.copy(), 'T': superlatives.copy(), 'H': superlatives.copy(),
                          'any': {'last': None, 'next': None}}
        farpath = {'A': {}, 'T': {}, 'P': {}, 'H': {}}
        inpath = {'A': {}, 'T': {}, 'P': {}, 'H': {}}
        nearpath = {'A': {}, 'T': {}, 'P': {}, 'H': {}}

        canon, otherdates = get_canon_Espenak()
        data = self.get_year(years)
        for eclipsename, localdata in data['eclipses'].items():
            # these iterate in order, negative years first

            if eclipsename in otherdates:
                canondata = canon[otherdates[eclipsename]]
            else:
                print(f"{eclipsename} not found in canon")
                raise
            baseeclipsetype = canondata['eclipse_type'][0]
            label = None
            for circ in ['c1', 'c2', 'mid', 'c3', 'c4']:
                # for circ in ['c1']:
                if localdata[circ] is None:
                    continue
                label = process_local_circ_times(circ, label, localdata, self.lon, self.timezone)
                localdata['label'] = label
            # eclipseid = label[0] + label[1:11].replace('-', '')
            localdata[
                'mapurl'] = f"http://xjubier.free.fr/en/site_pages/solar_eclipses/xSE_GoogleMap3.php?Ecl={canondata['id']}&Acc=2&Umb=1&Lmt=1&Mag=0&Lat={self.lat}&Lng={self.lon}&Zoom=7&LC=1"
            self.last_next_eclipses(baseeclipsetype, farpath, inpath, label, localdata, nearpath, prevnextevents,
                                    targetdates)
        return inpath, nearpath, farpath, prevnextevents

    def last_next_eclipses(self, baseeclipsetype, farpath, inpath, label, localdata, nearpath, prevnextevents,
                           targetdates):
        targetdate = f"{targetdates[baseeclipsetype]}T"  # pick eclipse of interest for comparing last and next, T24 is for sorting purposes
        if label[:14].replace('+', '~') < targetdate[:14].replace('+', '~') and not label.startswith(targetdate):
            prevnextevents['any']['last'] = localdata
        elif prevnextevents['any']['next'] is None and not label.startswith(targetdate):
            prevnextevents['any']['next'] = localdata
        if localdata['duration'] is not None:
            inpath[baseeclipsetype][label] = localdata
            if label[:14].replace('+', '~') < targetdate[:14].replace('+', '~') and not label.startswith(
                    targetdate):
                prevnextevents[baseeclipsetype]['last_in_path'] = localdata
            elif prevnextevents[baseeclipsetype]['next_in_path'] is None and not label.startswith(targetdate):
                prevnextevents[baseeclipsetype]['next_in_path'] = localdata
        elif (baseeclipsetype == 'T' and localdata['obs'] >= .9) or (baseeclipsetype in ['H','A'] and localdata['obs'] >= .8):
            # total eclipses above 90% obscuration or annular/hybrid above 80%
            nearpath[baseeclipsetype][label] = localdata
            if label[:14].replace('+', '~') < targetdate[:14].replace('+', '~') and not label.startswith(
                    targetdate):
                prevnextevents[baseeclipsetype]['last_near_path'] = localdata
            elif prevnextevents[baseeclipsetype]['next_near_path'] is None and not label.startswith(targetdate):
                prevnextevents[baseeclipsetype]['next_near_path'] = localdata
        else:
            farpath[baseeclipsetype][label] = localdata

    def fetch_google_circrequests(selfrequests, eclipse, height, latstr, lonstr):
        # doc http://xjubier.free.fr/en/site_pages/solar_eclipses/xSE_GoogleMap3_Help.html
        url = f'http://xjubier.free.fr/php/GE_xSrequestsE_LocalCircumstances.php?Eclipse={eclipse}&Details=1&Release=100&&HTTPCLIENT=7.3.6.9345,2.2,Google+Earth+Pro,en&BBOX={lonstr},{latstr},{height},0,0'
        print(url)
        raise
        headers = {
            'Accept': 'application/vnd.google-earth.kml+xml, application/vnd.google-earth.kmz, image/*, */*',
            'User-Agent': 'GoogleEarth/7.3.6.9345(Macintosh;Mac OS X (13.5.2);en;kml:2.2;client:Pro;type:default)',
            'Connection': 'Keep-Alive',
            'Accept-Encoding': 'gzip, deflate',
            'Accept-Language': 'en-US,*'
        }
        r = self.session.get(url, headers=headers)
        if not r.from_cache:
            print(r.from_cache, url)
        s = r.text
        if 'No such solar eclipse' in s:
            raise ValueError(f"No such eclipse on {eclipse}")
        return s


class solar_eclipse_canon(object):
    def __init__(self):
        pass


def click_century_buttons(driver, ele, row=None, column=None):
    if row is None:
        row_first = 2
        row_last = 10
        column_first = 1
        column_last = 5
    else:
        row_first = row
        row_last = row
        column_first = column
        column_last = column
    # click on each century button to perform javascript circumstance calculations
    results = {}
    by_year = {}
    for row in range(row_first, row_last + 1):
        for column in range(column_first, column_last + 1):
            enter_elevation(column, driver, ele, row)  # this also clears the previous table

            # wait for table to appear
            table = WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.ID, 'el_resultstable')))

            s = table.get_attribute('innerHTML')
            eclipse_data, year_data = process_gsfc_history_table(s)
            results.update(eclipse_data)
            by_year.update(year_data)
    return results, by_year


def enter_coordinates(driver, name, latd, latm, lats, NS, lond, lonm, lons, EW):
    # XPATH of each input field and the value to enter there
    eles = {'//*[@id="singlecolumn"]/form/div[2]/table[1]/tbody/tr[1]/td[2]/input': name,
            '//*[@id="singlecolumn"]/form/div[2]/table[1]/tbody/tr[2]/td[2]/input[1]': abs(latd),
            '//*[@id="singlecolumn"]/form/div[2]/table[1]/tbody/tr[2]/td[2]/input[2]': latm,
            '//*[@id="singlecolumn"]/form/div[2]/table[1]/tbody/tr[2]/td[2]/input[3]': round(lats),
            '//*[@id="singlecolumn"]/form/div[2]/table[1]/tbody/tr[2]/td[2]/select': NS,
            '//*[@id="singlecolumn"]/form/div[2]/table[1]/tbody/tr[3]/td[2]/input[1]': abs(lond),
            '//*[@id="singlecolumn"]/form/div[2]/table[1]/tbody/tr[3]/td[2]/input[2]': lonm,
            '//*[@id="singlecolumn"]/form/div[2]/table[1]/tbody/tr[3]/td[2]/input[3]': round(lons),
            '//*[@id="singlecolumn"]/form/div[2]/table[1]/tbody/tr[3]/td[2]/select': EW,
            '//*[@id="singlecolumn"]/form/div[2]/table[1]/tbody/tr[3]/td[2]/input[1]': abs(lond),
            }
    # enter coordinates
    for xpath, value in eles.items():
        elem = driver.find_element(By.XPATH, xpath)
        elem.click()
        if 'select' in xpath:
            select = Select(elem)
            el = select.select_by_visible_text(value)
        else:
            elem.clear()
            elem.send_keys(value)


def enter_elevation(column, driver, ele, row):
    xpath = '//*[@id="singlecolumn"]/form/div[2]/table[1]/tbody/tr[4]/td[2]/input'
    elem = driver.find_element(By.XPATH, xpath)
    elem.click()
    elem.clear()  # this helps ensure the table is cleared between button clicks, avoids DOM errors
    elem.send_keys(ele)
    xpath = f'//*[@id="singlecolumn"]/form/div[2]/table[2]/tbody/tr[{row}]/td[{column}]/input'
    button = driver.find_element(By.XPATH, xpath)
    button.click()


def get_canon_Espenak(year_start=-1499, year_end=3000, force=False):
    filename_pickle = 'caches/espenak_solar_eclipse_canon.pickle'
    try:
        fp = open(filename_pickle, 'rb')
        obj = pickle.load(fp)
        results = obj['results']
        otherdates = obj['otherdates']
        fp.close()
    except Exception as e:
        print(f'gsfc_eclipse_history cache read error | {e}')
        results = {}
        otherdates = {}
    if len(results) > 0 and not force:
        return results, otherdates

    s = requests_cache.CachedSession('caches/espenak_eclipse_cache.sqlite')
    for year0 in range(year_start, year_end, 100):
        r, url = get_canon_page(s, year0)
        soup = BeautifulSoup(r.text, 'html.parser')
        tables = soup.find_all('tbody')

        for table in tables:
            rows = table.find_all('tr')
            for row in rows:
                cells = row.find_all('td')
                if len(cells) < 15:
                    continue
                thisdict = parse_espenak_row(cells)
                atoms = thisdict['date_ut1'].split('-')
                year_utc = int(atoms[-3])
                month = months.index(atoms[-2])
                day = int(atoms[-1])
                if len(atoms) == 4:
                    year_utc *= -1
                    sign = '-'
                else:
                    sign = '+'

                thisdict['id'] = f"{sign}{abs(year_utc):04}{month:02}{day:02}"
                H, M, S = thisdict['ge_time_td'].split(':')
                td = ts.utc(year_utc, month, day, int(H), int(M), int(S))
                jpl = td.utc_jpl()
                tdp1 = formatdate(td + 1)
                tdm1 = formatdate(td - 1)
                otherdates[formatdate(td)] = thisdict['date_ut1']  # account for Delta T and GE that occurs across
                otherdates[tdm1] = thisdict['date_ut1']  # account for Delta T and GE that occurs across
                otherdates[tdp1] = thisdict['date_ut1']  # the international dateline
                thisdict['utc'] = td
                results[thisdict['date_ut1']] = thisdict
    fp = open(filename_pickle, 'wb')
    pickle.dump({'results': results, 'otherdates': otherdates}, fp)
    fp.close()
    return results, otherdates


def formatdate(newtd):
    try:
        yesterday_year = int(newtd.utc_strftime('%Y'))
    except Exception as e:
        raise ValueError(f"unable to reformat passed date, expected skyfield time type, got {type(newtd)}")
    if yesterday_year < 0:
        yyneg = '-'
    else:
        yyneg = '+'
    yesterday_str = f"{yyneg}{abs(yesterday_year):04}{newtd.utc_strftime('-%b-%d')}"
    return yesterday_str


def get_canon_page(s, year0):
    neg_from = neg_to = ''
    if year0 < 0:
        neg_from = '-'
    if year0 + 99 < 0:
        neg_to = '-'
    url = f'https://eclipsewise.com/solar/SEcatalog/SE{neg_from}{abs(year0):04}-{neg_to}{abs(year0 + 99):04}.html'
    r = s.get(url)
    return r, url


def parse_espenak_row(cells):
    headers = ['date_ut1', 'ge_time_td', 'delta_t', 'delta_sigma_s', 'luna_no', 'saros_no', 'eclipse_type',
               'QLE', 'gamma', 'magnitude', 'ge_lat', 'ge_lon', 'sun_alt', 'path_width_km',
               'central_duration']
    thisdict = {}
    for header, cell in zip(headers, cells):
        value = cell.text.strip()
        if header in ['gamma', 'magnitude']:
            if len(value) > 0:
                thisdict[header] = float(value)
            else:
                thisdict[header] = None
        elif header in ['delta_t', 'delta_sigma_s', 'saros_no', 'sun_alt', 'luna_no', 'path_width_km']:
            try:
                if len(value) > 0 and value != '-':
                    thisdict[header] = int(value)
                else:
                    thisdict[header] = None
            except Exception as e:
                print('*', header, value)
                print(thisdict['date_ut1'])
                print(e)
                raise
        else:
            thisdict[header] = value
    return thisdict


def get_canon_GSFC(year_start=-1499, year_end=3000):
    # https://eclipse.gsfc.nasa.gov/SEcat5/SEcatalog.html
    # https://eclipse.gsfc.nasa.gov/JSEX/JSEX-USA.html
    filename_pickle = 'caches/gsfc_eclipse_canon.pickle'
    try:
        fp = open(filename_pickle, 'rb')
        data = pickle.load(fp)
        fp.close()
    except Exception as e:
        s = requests_cache.CachedSession('caches/nasa_gsfc_eclipse_cache.sqlite')
        data = {}
        for year in range(year_start, year_end, 100):
            if year == -99:
                url = f'https://eclipse.gsfc.nasa.gov/SEcat5/SE{year:05}-{year + 99:04}.html'
            elif year < 0:
                url = f'https://eclipse.gsfc.nasa.gov/SEcat5/SE{year:05}-{year + 99:05}.html'
            else:
                url = f'https://eclipse.gsfc.nasa.gov/SEcat5/SE{year:04}-{year + 99:04}.html'
            r = s.get(url)
            soup = BeautifulSoup(r.text, 'html.parser')
            pres = soup.find_all('pre')
            for n in range(4, len(pres)):
                #                       TD of
                # Catalog  Calendar   Greatest          Luna Saros Ecl.               Ecl.            Sun Path  Central
                # Number     Date      Eclipse    ΔT     Num  Num  Type QLE  Gamma    Mag.   Lat Long Alt Width   Dur.
                #                                  s                                          °    °    °   km
                #           1          2          3          4          5          6          7          8          9
                # 0123456789*0123456789*0123456789*0123456789*0123456789*0123456789*0123456789*0123456789*0123456789*0
                # 00001 -1999 Jun 12  03:14:51  46438 -49456    5   T   -n  -0.2701  1.0733   6N  33W  74  247  06m37s
                lines = pres[n].text.split("\n")
                for line in lines[7:]:
                    if len(line) > 0:
                        catno = line[:5].strip()
                        year = line[5:11].strip()
                        monthstr = line[11:15].strip()
                        month = int(months.index(monthstr))
                        day = line[15:18].strip()
                        name = f"{int(year)}-{monthstr}-{day}"
                        if int(year) >= 0:
                            name = f"+{name}"
                        eclipse_type = line[50:53].strip()
                        lat = line[75:79].strip()
                        if 'N' in lat:
                            lat = int(lat[:-1])
                        elif 'S' in lat:
                            lat = int(lat[:-1]) * -1
                        else:
                            raise ValueError(f" latitude error with {lat}")
                        lon = line[80:85].strip()
                        if 'E' in lon:
                            lon = int(lon[:-1])
                        elif 'W' in lon:
                            lon = int(lon[:-1]) * -1
                        else:
                            raise ValueError(f" longitude error with {lon}")

                        data[name] = {'catno': catno, 'year': year, 'month': month, 'day': day,
                                      'eclipse_type': eclipse_type,
                                      'ge_lat': lat, 'ge_lon': lon}
            fp = open(filename_pickle, 'wb')
            pickle.dump(data, fp)
            fp.close()
    fp = open(filename_pickle, 'wb')
    pickle.dump(data, fp)
    fp.close()
    return data


def process_gsfc_history_table(s):
    soup = BeautifulSoup(s, 'html.parser')

    tables = soup.find_all('tr')
    result = {}
    by_year = {}
    headers = ['date', 'eclipse type', 'c1_time', 'c1_sun_alt', 'c2_time', 'mid_time', 'mid_sun_alt', 'mid_sun_azi',
               'c3_time', 'c4_time', 'c4_sun_alt', 'mag', 'obs', 'duration']
    for row in soup.find_all('tr'):
        cells_data = row.find_all('td')
        result_row = {}
        if len(cells_data) > 0:
            result_row, year, month, day = gsfc_local_history_row(cells_data, headers, result_row)

            eclipse_at_sunriseset(result_row)

            for attr in ['c1', 'c2', 'mid', 'c3', 'c4']:
                gsfc_process_local_circ_fields(attr, day, month, result_row, year)
            result[result_row['date']] = result_row
            if year not in by_year:
                by_year[year] = {}
            by_year[year][result_row['date']] = result_row

    return result, by_year


def gsfc_process_local_circ_fields(attr, day, month, result_row, year):
    timeattr = f"{attr}_time"
    if result_row[timeattr] is None:
        result_row[attr] = None
    else:
        if '(' in result_row[f"{attr}_time"]:
            HMstr, _ = result_row[f"{attr}_time"].split('(')
            H, M = HMstr.split(':')
            S = 0
        else:
            H, M, S = result_row[f"{attr}_time"].split(':')
        tt = ts.utc(year, month, day, int(H), int(M), int(S))
        utciso = tt.utc_iso()
        atoms = utciso.split('-')
        newyear = int(atoms[-3])
        if utciso.startswith('-'):
            thesign = '-'
        else:
            thesign = '+'

        utciso = f"{thesign}{newyear:04}-{'-'.join(atoms[-2:])}"
        result_row[attr] = {'tt': tt, 'utc_iso': utciso}

        if f'{attr}_sun_azi' in result_row:
            sun_azi = result_row[f'{attr}_sun_alt'].replace('(r)', '').replace('(s)', '')
            result_row[f'{attr}_sun_azi'] = result_row[attr]['sun_azi'] = int(sun_azi)
        if f'{attr}_sun_alt' in result_row:
            sun_alt = result_row[f'{attr}_sun_alt']
            sun_alt = sun_alt.replace('(r)', '').replace('(s)', '')
            result_row[f'{attr}_sun_alt'] = result_row[attr]['sun_alt'] = int(sun_alt)


def eclipse_at_sunriseset(result_row):
    ''' moves the (r) and (s) which indicate the event is happening at sunrise or sunset, to notes'''
    if '(r)' in result_row['obs']:
        result_row['notes'].append('underway at sunrise')
    if '(s)' in result_row['obs']:
        result_row['notes'].append('underway at sunset')
    result_row['obs'] = float(result_row['obs'].replace('(r)', '').replace('(s)', ''))


def gsfc_local_history_row(cells_data, headers, result_row):
    data = []
    for cell in cells_data:
        if cell.text == '-':
            data.append(None)
        else:
            data.append(cell.text)
    if not data[0].startswith('-'):
        data[0] = '+' + data[0]
    data[0] = data[0].replace('2500-Feb-29', '2500-Feb-28')  # correct for error in GSFC leap year calculations
    # clean up YYYYMMMDD column
    atoms = data[0][1:].split('-')
    data[0] = f"{data[0][0]}{int(atoms[0]):04}-{atoms[1]}-{atoms[2]}"
    result_row = dict(map(lambda i, j: (i, j), headers, data))
    result_row['notes'] = []

    if result_row['date'].startswith('-'):
        _, year, monthstr, day = result_row['date'].split('-')
        year = f"-{year}"  # put neg sign back
    else:
        year, monthstr, day = result_row['date'].split('-')
    year = int(year)
    month = int(months.index(monthstr))
    day = int(day)

    return result_row, year, month, day


def process_local_circ_times(circ, label, localdata, lon, tz):
    year = int(localdata[circ]['utc_iso'][:5])
    datepart = localdata[circ]['utc_iso'][5:]
    if int(year) >= 1883:
        utc = dateutil.parser.isoparse(f"{year}{datepart}")
        local = utc.astimezone(ZoneInfo(tz))
        localdata[circ]['local_tz'] = local.strftime('%Z')[0] + local.strftime('%Z')[-1]
        localdata[circ]['local_time'] = local.strftime('%-I:%M:%S %p')
        localdata[circ]['local_date'] = local.strftime('%a %b %-d, %Y')
    else:
        utc = dateutil.parser.isoparse(f"1886{datepart}")
        local = utc + datetime.timedelta(seconds=round(4 * 60 * lon))
        localdata[circ]['local_time'] = local.strftime('%-I:%M:%S %p LMT')
    if year < 0:
        sign = '-'
    else:
        sign = '+'
    localdata[circ]['local_iso'] = f"{sign}{abs(year):04}" + local.strftime('-%m-%dT%H:%M:%S')
    if circ == 'c1':
        label = localdata[circ]['local_iso']
    return label
