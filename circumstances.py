import datetime
import pickle
from pprint import pprint

import requests_cache
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait
from skyfield.api import load
from zoneinfo import ZoneInfo

import dateutil.parser
import pandas as pd

from utils import get_driver, directional_DMS_coordinates

ts = load.timescale()

# https://github.com/skyfielders/python-skyfield/issues/445
pd.set_option('display.max_columns', None)
pd.set_option('display.width', 1000)

MOON_RADIUS_KM = 1737.4
SUN_RADIUS_KM = 695700
months = ['', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']


# useful URLS
# Xavier Jubier's site
# url = f"http://xjubier.free.fr/php/xSE_5MCSE_Location_Search.php?FY=1000&TY=1299&ET=T&IS=0&Lat=35.77&Lng=78.63&ES=DateUp&Lang=en&Index=2&Last=7"
# url = f"http://xjubier.free.fr/php/xSE_EclipseInfos.php?Ec=1&Ecl[]=+10000407&Lang=en"


def gsfc_eclipse_history_for_coordinate(name, lat, lon, ele=0,  driver=None, usecache=True):
    filename_pickle = 'caches/gsfc_solar_eclipse_history_local.pickle'
    lat = round(lat, 2)
    lon = round(lon, 2)
    coords = f"{lat},{lon},{ele}"
    try:
        fp = open(filename_pickle, 'rb')
        data = pickle.load(fp)
        fp.close()
    except Exception as e:
        print('gsfc_eclipse_history cache read error')
        data = {}
        # raise
    if coords in data.keys() and usecache:
        return data[coords], driver

    EW, NS, latd, latm, lats, lond, lonm, lons = directional_DMS_coordinates(lat, lon)
    url = 'https://eclipse.gsfc.nasa.gov/JSEX/JSEX-USA.html'
    if driver is None:
        driver = get_driver()
    results = {'city': name, 'lat': lat, 'lon': lon, 'ele': ele, 'eclipses': {}}
    data[coords] = results

    driver.get(url)  # bring up the page
    enter_coordinates(driver, name , latd, latm, lats, NS, lond, lonm, lons, EW)
    data[coords]['eclipses'].update(click_century_buttons(driver, ele))

    fp = open(filename_pickle, 'wb')
    pickle.dump(data, fp)
    fp.close()

    return results, driver


def click_century_buttons(driver, ele):
    # click on each century button to perform javascript circumstance calculations
    results={}
    for row in range(2, 11):
        for column in range(1, 6):
            enter_elevation(column, driver, ele, row)  # this also clears the previous table

            # wait for table to appear
            table = WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.ID, 'el_resultstable')))

            s = table.get_attribute('innerHTML')
            eclipse_data = process_gsfc_history_table(s)
            results.update(eclipse_data)
    return results


def enter_coordinates(driver, name , latd, latm, lats, NS, lond, lonm, lons, EW):
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
        results=obj['results']
        otherdates=obj['otherdates']
        fp.close()
    except Exception as e:
        print(f'gsfc_eclipse_history cache read error | {e}')
        results = {}
        otherdates={}
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
                H, M, S = thisdict['ge_time_td'].split(':')
                td = ts.utc(year_utc, month, day,int(H), int(M), int(S))
                jpl=td.utc_jpl()
                tdp1=formatdate(td+1)
                tdm1=formatdate(td-1)
                otherdates[formatdate(td)]=thisdict['date_ut1']  # account for Delta T and GE that occurs across
                otherdates[tdm1]=thisdict['date_ut1']  # account for Delta T and GE that occurs across
                otherdates[tdp1]=thisdict['date_ut1']  # the international dateline
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
    headers = ['date', 'eclipse type', 'c1_time', 'c1_sun_alt', 'c2_time', 'mid_time', 'mid_sun_alt', 'mid_sun_azi',
               'c3_time', 'c4_time', 'c4_sun_alt', 'mag', 'obs', 'duration']
    for row in soup.find_all('tr'):
        cells_data = row.find_all('td')
        data = []
        if len(cells_data) > 0:
            for cell in cells_data:
                if cell.text == '-':
                    data.append(None)
                else:
                    data.append(cell.text)
            if not data[0].startswith('-'):
                data[0] = '+' + data[0]
            data[0]=data[0].replace('2500-Feb-29', '2500-Feb-28') # correct for error in GSFC leap year calculations

            atoms=data[0][1:].split('-')
            data[0]=f"{data[0][0]}{int(atoms[0]):04}-{atoms[1]}-{atoms[2]}"

            result[data[0]] = dict(map(lambda i, j: (i, j), headers, data))
            for attr in ['obs']:
                result[data[0]][attr] = float(result[data[0]][attr].replace('(r)', '').replace('(s)', ''))
            result[data[0]]['notes'] = []
            for attr in ['c1', 'mid', 'c4']:
                if 'r' in result[data[0]][f'{attr}_sun_alt']:
                    if 'c' in attr:
                        result[data[0]]['notes'].append(f'partial eclipse in progress at sunrise')
                    else:
                        result[data[0]]['notes'].append(f'partial eclipse in progress at sunrise')
                if 's' in result[data[0]][f'{attr}_sun_alt']:
                    if 'c' in attr:
                        result[data[0]]['notes'].append(f'maximum eclipse in progress at sunset')
                    else:
                        result[data[0]]['notes'].append(f'maximum eclipse in progress at sunset')
            if data[0].startswith('-'):
                _, year, monthstr, day = data[0].split('-')
                year = f"-{year}"  # put neg sign back
            else:
                year, monthstr, day = data[0].split('-')
            year = int(year)
            month = int(months.index(monthstr))
            day = int(day)
            for attr in ['c1', 'c2', 'mid', 'c3', 'c4']:
                timeattr = f"{attr}_time"
                if result[data[0]][timeattr] is None:
                    result[data[0]][attr] = None
                else:
                    if '(' in result[data[0]][f"{attr}_time"]:
                        HMstr, _ = result[data[0]][f"{attr}_time"].split('(')
                        H, M = HMstr.split(':')
                        S = 0
                    else:
                        H, M, S = result[data[0]][f"{attr}_time"].split(':')
                    tt = ts.utc(year, month, day, int(H), int(M), int(S))
                    lkjasdf=tt.utc_jpl()
                    utciso=tt.utc_iso()
                    atoms=utciso.split('-')
                    newyear=int(atoms[-3])
                    if utciso.startswith('-'):
                        thesign='-'
                    else:
                        thesign='+'


                    try:
                        utciso=f"{thesign}{newyear:04}-{'-'.join(atoms[-2:])}"
                    except Exception as e:
                        pass
                    result[data[0]][attr] = {'tt': tt, 'utc_iso': utciso}

                    if f'{attr}_sun_azi' in result[data[0]]:
                        sun_azi = result[data[0]][f'{attr}_sun_alt'].replace('(r)', '').replace('(s)', '')
                        result[data[0]][f'{attr}_sun_azi'] = result[data[0]][attr]['sun_azi'] = int(sun_azi)
                    if f'{attr}_sun_alt' in result[data[0]]:
                        sun_alt = result[data[0]][f'{attr}_sun_alt']
                        sun_alt = sun_alt.replace('(r)', '').replace('(s)', '')
                        result[data[0]][f'{attr}_sun_alt'] = result[data[0]][attr]['sun_alt'] = int(sun_alt)
    return result


def localize(name, lat, lon, tz, ele=0, driver=None, usecache=True, ):
    farpath = {'A': {}, 'T': {}, 'P': {}, 'H': {}}
    inpath = {'A': {}, 'T': {}, 'P': {}, 'H': {}}
    nearpath = {'A': {}, 'T': {}, 'P': {}, 'H': {}}
    canon, otherdates = get_canon_Espenak()
    data, driver = gsfc_eclipse_history_for_coordinate(name, lat, lon, ele=ele, driver=driver, usecache=usecache)
    for eclipsename, localdata in data['eclipses'].items():
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
            year = int(localdata[circ]['utc_iso'][:5])
            datepart = localdata[circ]['utc_iso'][5:]
            if int(year) >= 1883:
                utc = dateutil.parser.isoparse(f"{year}{datepart}")
                local = utc.astimezone(ZoneInfo(tz))
                localdata[circ]['local_time'] = local.strftime('%-I:%M:%S %p %Z')
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
        if localdata['duration'] is not None:
            inpath[baseeclipsetype][label] = localdata
        elif localdata['obs'] > .9:
            nearpath[baseeclipsetype][label] = localdata
        else:
            farpath[baseeclipsetype][label] = localdata

    return inpath, nearpath, farpath, driver
