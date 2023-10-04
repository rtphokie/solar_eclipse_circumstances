
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


def apparent_radius(df):
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


def circumstances(start, lat, lon, ele=100, end=None, tzstring=None, eph=None):
    '''
    Calculates local circumstances of an eclipse returning datetimes (UTC) for partial
    eclipse contact points (c1 and c4), the moment of maxium eclipse, along with contact
    points for total or annular eclipse as appropraite.

    :param start: the date and time to start searching for an eclipse (datetime, required)
                  when end is None, this is treated as a mid point of a search beginning 00:00 UTC
                  the previous day, ending 00:00 UTC the following day
    :param lat: latitude in degrees (float, positive north, negative south)
    :param lon: longitude in degrees (float, positive east, negative west)
    :param ele: elevation in meters (int)
    :param end: date and time to end search (datetime, default None)
    :param tzstring: converts UTC to local for all datetimes (optional, example 'US/Eastern')
    :return: for each of the 5 circumstances, a pandas series is returned:
        a da

        c1:  beginning of partial eclipse
        c2:  beginning of total or annular eclipse (or None outside of path of totality/annularity)
        mid: moment of maximum eclipse
        c3:  end of total or annular eclipse (or None outside of path of totality/annularity)
        c4:  end of partial eclipse

    '''

    year = int(start.utc_strftime('%Y'))
    month = int(start.utc_strftime('%-m'))
    day = int(start.utc_strftime('%-d'))
    hour = int(start.utc_strftime('%-H'))
    minute = int(start.utc_strftime('%-M'))
    second = int(start.utc_strftime('%-S'))
    if eph is None:
        eph = load_ephemeris(year)
    if end is None:
        # all we have is a day, so let look across all minutes across a
        # 2 day span centered on noon UTC on the day passed
        time = ts.utc(year, month, day, 12, range(-1440, 1440))
    else:
        # second level resolution across entire eclipse
        timespan_sec = (end - start) * 86400
        startsec = int(second) - 60  # 1 minutes before C1
        endsec = int(second + 60 + timespan_sec)  # 1 minute after C4
        time = ts.utc(year, month, day, hour, minute, range(startsec, endsec))

    # build data frame from those times
    df = pd.DataFrame({
        'ordinal': time.toordinal(),  # needed really only for testing against other calculations
        'utc_iso': time.utc_iso(),
        'tt': list(time),
        'jd': list(time.tt),
    })

    place = eph['earth'] + Topos(lat, lon, elevation_m=ele)

    # get position of Moon and Sun at each time
    moon = place.at(time).observe(eph['moon']).apparent()
    sun = place.at(time).observe(eph['sun']).apparent()

    # add a column for angular separation of the Moon and Sun
    df['separation'] = moon.separation_from(sun).degrees

    # lets get the lunar and solar distance... that might be useful
    alt_az_dist(df, moon, 'moon')
    alt_az_dist(df, sun, 'sun')

    # and the apparant radius, which provides the ratio, we'll need that
    apparent_radius(df)

    # calculate how much of the Sun's disk is eclipsed by the Moon
    df['eclipse_fraction'] = df.apply(lambda x: eclipse_fraction(x['separation'], x['sun_r'], x['moon_r']), axis=1)

    # now we can find when the partial (and if applicable total or annular) eclipses begin and end as well as the midpoint
    c1, c2, mid_eclipse, c3, c4 = contact_points(df)

    if end is None and c1 is not None:
        # repeat at second resolution from C1 to C4
        c1, c2, mid_eclipse, c3, c4 = circumstances(c1.tt, lat, lon, end=c4.tt, eph=eph)  # refine at higher resolution
    return c1, c2, mid_eclipse, c3, c4


def contact_points(df):
    '''
    calculate the 4 contact points plus maximum eclipse, uses ordinal dates to simplify support for negative years
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
    c1, c2, mid_eclipse, c3, c4 = None, None, None, None, None
    if len(df_eclipsed) > 0:
        c1 = df_eclipsed.loc[df_eclipsed.ordinal.idxmin()]  # earliest time Sun is obscured
        c4 = df_eclipsed.loc[df_eclipsed.ordinal.idxmax()]  # latest time
        if max_eclipse_fraction > 1:
            c2 = df_eclipsed_max.loc[df_eclipsed_max.ordinal.idxmin()]  # earliest time when Sun is 100% obscured
            c3 = df_eclipsed_max.loc[df_eclipsed_max.ordinal.idxmax()]  # latest  time
        midpoint = round(len(df_eclipsed_max) / 2)
        mid_eclipse = df_eclipsed_max.iloc[midpoint]

    return c1, c2, mid_eclipse, c3, c4

