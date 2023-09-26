import re
from pprint import pprint

import dateutil.parser
import requests
import requests_cache
from bs4 import BeautifulSoup
from skyfield import api

ts = api.load.timescale()

months = ['', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
requests_cache.install_cache('caches/jubier_cache.sqlite')  # catch all cache for modules such as googlemaps

''' 
These tools get circumstances for a given eclipse from two highly respected sources, Javier Xubier personal website
and Fred Espenak's contributions to the NASA GSFC eclipse website, for comparison with our Skyfield based calculations
'''

def process(s):
    soup = BeautifulSoup(s, 'html.parser')

    tables = soup.find_all('tr')
    result = {}
    headers = ['date', 'eclipse type', 'c1_time', 'c1_sun_alt', 'c2_time', 'mid', 'mid_sun_alt', 'mid_sun_azi',
               'c3_time', 'c4_time', 'c4_sun_alt', 'mag', 'obs', 'duration']
    for row in soup.find_all('tr'):
        cells_data = row.find_all('td')
        data = []
        if len(cells_data) > 0:
            for cell in cells_data:
                data.append(cell.text)
            if not data[0].startswith('-'):
                data[0] = '+' + data[0]

            result[data[0]] = dict(map(lambda i, j: (i, j), headers, data))
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
            year = int(data[0][:5])
            monthstr = data[0][6:9]
            month = int(months.index(monthstr))
            day = int(data[0][11:13])

            ts.utc(2024, 4, 8)
            ts.utc(-2024, 4, 8)

            for attr in ['c1', 'c2', 'c3', 'c4']:
                timeattr = f"{attr}_time"
                if result[data[0]][timeattr] == '-':
                    result[data[0]][attr] = None
                else:
                    jk = result[data[0]][f"{attr}_time"]
                    print(jk)
                    if '(' in result[data[0]][f"{attr}_time"]:
                        HMstr, _ = result[data[0]][f"{attr}_time"].split('(')
                        H, M = HMstr.split(':')
                        S = 0
                    else:
                        H, M, S = result[data[0]][f"{attr}_time"].split(':')
                    dt = ts.utc(year, month, day, int(H), int(M), int(S))
                    result[data[0]][attr] = {'datatime': dt, 'ordinal': dt.toordinal()}
                    if f'{attr}_sun_alt' in result[data[0]]:
                        sun_alt = result[data[0]][f'{attr}_sun_alt']
                        sun_alt = sun_alt.replace('(r)', '').replace('(s)', '')
                        result[data[0]][attr]['sun_alt'] = float(sun_alt)
            jkl = data


def get_usno_circumstances(lat, lon, eclipse, alt=0, datestr=None):
    # https://aa.usno.navy.mil/data/SolarEclipses
    # https://aa.usno.navy.mil/calculated/eclipse/solar?eclipse=22023&lat=35.08&lon=-106.65&label=Albq&height=1490&submit=Get+Data
    url = f"https://aa.usno.navy.mil/calculated/eclipse/solar?eclipse={eclipse}&lat={lat}&lon={lon}&height={alt}&submit=Get+Data"
    r = requests.get(url)
    if not r.from_cache:
        print(r.from_cache, url)

    data = parse_usno(r.text, datestr)
    return data


def parse_usno(html, datestr):
    data = {}
    for c in ['c1', 'c2', 'c3', 'c4']:
        data[c] = {'datetime_utc': None, 'ordinal': None}
    soup = BeautifulSoup(html, 'html.parser')
    div = soup.find("div", {'class': "usa-layout-docs__main desktop:grid-col-12 usa-prose"})
    tables = div.find_all('table')
    rows = tables[1].find_all('tr')
    for row in rows[2:]:
        # Phenomenon	Day	Time (UT1)	Sun's Altitude (°)	Sun's Azimuth (°)	Position Angle (°)	Vertex Angle (°)
        cells = row.find_all('td')
        event = cells[0].text
        day = cells[1].text
        time = cells[2].text
        sunalt = cells[3].text
        sunaz = cells[4].text
        posang = cells[5].text
        vertang = cells[6].text
        eventdate = f"{datestr}T{time}Z"
        event_dt = dateutil.parser.isoparse(eventdate)
        if event == 'Eclipse Begins':
            c = 'c1'
        elif event == 'Annularity Begins' or event == 'Totality Begins':
            c = 'c2'
        elif event == 'Maximum Eclipse':
            c = 'mid'
        elif event == 'Annularity Ends' or event == 'Totality Ends':
            c = 'c3'
        elif event == 'Eclipse Ends':
            c = 'c4'
        else:
            raise ValueError(f"{event} event not handled")
        tt = ts.from_datetime(event_dt)
        data[c] = {'datetime_utc': event_dt, 'ordinal': tt.toordinal(),
                   'sun_alt': float(sunalt),
                   'sun_az': float(sunaz),
                   }
    rows = tables[2].find_all('tr')
    for row in rows:
        cells = row.find_all('td')
        data[cells[0].text] = cells[1].text
    return data


def get_jubier_circumstances(angle=0, eclipse="+20231014", height=0, latstr="", lonstr="", DEBUG=False):
    '''
    :param angle: viewing angle of the observer normally populated by Google Earth
    :param eclipse: UTC date of the eclipse to calculate for of the form [+-]YYYYMMDD
    :param height: observer height in meters
    :param latstr:
    :param lonstr:
    :param DEBUG:
    :return:
    '''

    if DEBUG:
        fp = open("caches/foo.xml")
        sa = fp.readlines()
        fp.close()
        s = ' '.join(sa)
    else:
        s = fetch_google_circ(eclipse, height, latstr, lonstr)
    fp = open('caches/foo.xml', 'w')
    fp.writelines(s)
    fp.close()
    if 'NO&nbsp;SOLAR&nbsp;ECLIPSE' in s:
        return None
    jkl = s.split('<![CDATA[')
    html, _ = jkl[2].split(' ]]')
    fp = open('caches/foo.html', 'w')
    fp.writelines(s)
    fp.close()
    soup = BeautifulSoup(html, 'html.parser')

    tables = soup.find_all('table')
    if len(tables) < 4:
        text_file = open("caches/googlecirc.html", "w")
        text_file.write(s)
        text_file.close()
        raise

    data = {}
    get_google_circ_parse_table_1(data, tables[1])
    get_google_circ_parse_table_2(data, tables[2])
    get_google_circ_parse_table_3(data, tables[3])
    return data


def get_google_circ_parse_table_3(iop, thistable):
    year = None
    rows = thistable.find_all('tr')
    for eventshort in ['c1', 'c2', 'c3', 'c4']:
        iop[eventshort] = {'utc_datetime': None, 'ordinal': None}
    for row in rows[1:]:
        cells = row.find_all('td')
        event = cells[0].text
        x = re.search("\((\w+)", event)
        if x:
            eventshort = x.group(1).lower()
        else:
            eventshort = event
        date = cells[1].text
        time = cells[2].text
        alt = cleanupvalues(cells[3].text)
        azi = cleanupvalues(cells[4].text)
        p = cleanupvalues(cells[5].text)
        v = cleanupvalues(cells[6].text)
        try:
            lc = cleanupvalues(cells[7].text)
        except:
            lc = None
        if lc is not None:
            lc = float(lc.strip('s'))
        if alt < 0:
            altstr = 'below horizon'
        elif alt < 10:
            altstr = 'below treeline'
        elif alt < 30:
            altstr = 'low'
        else:
            altstr = None
        # if year is None:
        #     pass
        #     eph = load_ephemeris(int(date[:4]))

        date_iso_str = f"{date.replace('/', '-')}T{time}Z"
        iop[eventshort] = {'date': date, 'time': time,
                           'utc_iso': date_iso_str,
                           'alt': alt, 'azi': azi,
                           'alt_str': altstr,
                           'cardinal': degrees_to_cardinal(azi),
                           'p': p, 'v': v, 'lc_sec': lc}
        # '2024-04-08T17:58:50.3Z'
        year = int(date[:4])
        month = int(date[5:7])
        day = int(date[8:10])
        hour = int(time[:2])
        minute = int(time[3:5])
        second = float(time[6:])
        iop[eventshort]['tt'] = ts.utc(year, month, day, hour, minute, second)
        iop[eventshort]['ordinal'] = iop[eventshort]['tt'].toordinal()


def degrees_to_cardinal(d):
    '''
    note: this is highly approximate...
    '''
    dirs_long = ["north", "north-northeast", "northeast", "east-northeast",
                 "east", "east-southeast", "southeast", "south-southeast",
                 "south", "south-southwest", "southwest", "west-southwest",
                 "west", "west-northwest", "northwest", "north-northwest"]
    dirs = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
            "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
    ix = int((d + 11.25) / 22.5)
    return dirs[ix % 16], dirs_long[ix % 16]


def get_google_circ_parse_table_2(iop, thistable):
    rows = thistable.find_all('tr')
    depthcell = rows[0].find_all('td')[0].contents
    if len(depthcell) == 5:
        iop['umberal depth'], _, iop['path width'], _, iop['obscuration'] = depthcell
    elif len(depthcell) == 3:
        iop['umberal depth'] = depthcell[0].replace(u'\xa0', u' ')
        iop['path width'] = None
        iop['obscuration'] = depthcell[2].replace(u'\xa0', u' ')
    elif len(depthcell) == 1:
        iop['umberal depth'] = None
        iop['path width'] = None
        iop['obscuration'] = depthcell[0].replace(u'\xa0', u' ')
    else:
        print('unexpected values in depthcell')
        pprint(depthcell)
        raise

    for attr in ['umberal depth', 'obscuration', 'path width']:
        focus = iop[attr]
        if iop[attr] is not None:
            iop[attr] = cleanupvalues(iop[attr])

    if iop['path width'] is not None:
        iop['path_width_km'] = float(iop['path width'].replace('km', ''))
        iop['path_width_mi'] = round(iop['path_width_km'] * 0.621371, 1)

    magnitudecell = rows[0].find_all('td')[4].contents
    if len(magnitudecell) == 5:
        iop['mag'], _, iop['moon/sun size ratio'], _, iop['umbral velocity'] = magnitudecell
    elif len(magnitudecell) == 3:
        iop['mag'], _, iop['moon/sun size ratio'] = magnitudecell
        iop['umbral velocity'] = None
    elif len(magnitudecell) == 1:
        iop['mag'] = None
        iop['moon/sun size ratio'] = None
        iop['umbral velocity'] = None
    else:
        print('unexpected values in magnitudecell')
        pprint(magnitudecell)
        raise

    for attr in ['mag', 'moon/sun size ratio', 'umbral velocity']:
        iop[attr] = cleanupvalues(iop[attr])
    if iop['umbral velocity'] is not None:
        iop['umberal_velocity_kps'] = float(iop['umbral velocity'].replace('km/s', ''))
        iop['umberal_velocity_mph'] = round(iop['umberal_velocity_kps'] * 2236.94, 1)
        iop['umberal_velocity_mach'] = round(iop['umberal_velocity_kps'] * 2.91545, 1)


def cleanupvalues(v):
    if v is None or len(v) == 0 or v == ' ':
        return None
    if '?' in v:
        return None
    newv = v.replace(u'\xa0', u' ')
    if ' : ' in newv:
        _, newv = newv.split(' : ')
    newv = newv.replace("°", '').replace("%", '')
    if 'km' not in v and ' (' not in v and not v.endswith('s'):
        newv = float(newv)
    return newv


def get_google_circ_parse_table_1(iop, thistable):
    rows = thistable.find_all('tr')
    iop['lat'] = cleanupvalues(rows[0].find_all('td')[2].text.replace(u'\xa0', u' ').replace('º', ''))
    iop['lon'] = cleanupvalues(rows[1].find_all('td')[2].text.replace(u'\xa0', u' ').replace('º', ''))

    iop['duration'] = None
    iop['duration_limb_corrected'] = None
    durationcell = rows[0].find_all('td')[4].contents
    if len(durationcell) == 3:
        iop['duration'] = cleanupvalues(durationcell[0])
        iop['duration_limb_corrected'] = cleanupvalues(durationcell[2])
    elif len(durationcell) < 3:
        iop['duration'] = str(durationcell[0])
    for durattr in ['duration', 'duration_limb_corrected']:
        if iop[durattr] is None:
            continue
        jinpath = re.search('(\d+)m([\d\.]+)s', iop[durattr])
        jpartial = re.search('([\w\s]+).*eclipse', str(iop[durattr]))
        if jinpath:
            iop[f'{durattr}_sec'] = float(jinpath.group(2).strip())
            iop[f'{durattr}_sec'] += float(jinpath.group(1).strip()) * 60
        if jpartial:
            iop['type_local'] = str(jpartial.group(1).strip())
    #


def fetch_google_circ(eclipse, height, latstr, lonstr):
    # doc http://xjubier.free.fr/en/site_pages/solar_eclipses/xSE_GoogleMap3_Help.html
    url = f'http://xjubier.free.fr/php/GE_xSE_LocalCircumstances.php?Eclipse={eclipse}&Details=1&Release=100&&HTTPCLIENT=7.3.6.9345,2.2,Google+Earth+Pro,en&BBOX={lonstr},{latstr},{height},0,0'
    headers = {
        'Accept': 'application/vnd.google-earth.kml+xml, application/vnd.google-earth.kmz, image/*, */*',
        'User-Agent': 'GoogleEarth/7.3.6.9345(Macintosh;Mac OS X (13.5.2);en;kml:2.2;client:Pro;type:default)',
        'Connection': 'Keep-Alive',
        'Accept-Encoding': 'gzip, deflate',
        'Accept-Language': 'en-US,*'
    }
    r = requests.get(url, headers=headers)
    if not r.from_cache:
        print(r.from_cache, url)
    s = r.text
    if 'No such solar eclipse' in s:
        raise ValueError(f"No such eclipse on {eclipse}")
    return s
