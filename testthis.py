import unittest
from pprint import pprint
#import requests, requests_cache  # https://requests-cache.readthedocs.io/en/latest/
#from bs4 import BeautifulSoup
#from mpl_toolkits.basemap import Basemap
#import matplotlib.pyplot as plt
# import shapefile
# import simple_cache
#import csv
#import matplotlib.colors as mcol

import numpy as np
#import matplotlib as mpl
#import matplotlib.pyplot as plt
#from mpl_toolkits.basemap import Basemap as Basemap
#from matplotlib.colors import rgb2hex
#from matplotlib.patches import Polygon
#from matplotlib.collections import PatchCollection

# https://www.weather.gov/gis/CWAmetadata

#requests_cache.install_cache('test_cache', backend='sqlite', expire_after=3600)


def latimes():
    url = 'https://datadesk-prod-origin.californiatimes.com/projects/elections-data/2020-11-03/president.json'
    r = requests.get(url)
    data = r.json()
    return (data)


def draw_us_map():
    # Set the lower left and upper right limits of the bounding box:
    lllon = -119
    urlon = -64
    lllat = 22.0
    urlat = 50.5
    # and calculate a centerpoint, needed for the projection:
    centerlon = float(lllon + urlon) / 2.0
    centerlat = float(lllat + urlat) / 2.0

    m = Basemap(resolution='h',  # crude, low, intermediate, high, full
                llcrnrlon=lllon, urcrnrlon=urlon,
                lon_0=centerlon,
                llcrnrlat=lllat, urcrnrlat=urlat,
                lat_0=centerlat,
                projection='tmerc')

    # # Read state boundaries.
    # shp_info = m.readshapefile('st99_d00', 'states',
    #                            drawbounds=True, color='lightgrey')

    # Read CWA
    shp_info = m.readshapefile('w_10nv20/w_10nv20', 'counties', drawbounds=True)
    # Read DMAs
    # shp_info = m.readshapefile('dma_2008/DMAs', 'cwas', drawbounds=True)


def plotito():
    draw_us_map()
    plt.title('US Counties')
    # # Get rid of some of the extraneous whitespace matplotlib loves to use.
    plt.tight_layout(pad=0, w_pad=0, h_pad=0)
    plt.show()


def usa_state_colormap(shapefile='dma_2008/DMAs', segmentname='CWA', title='', colorbar_title=''):
    """
    Code adapted from:
    https://stackoverflow.com/questions/39742305/how-to-use-basemap-python-to-plot-us-with-50-states
    State shape files (st9_d00, etc.) avail in basemap examples
    https://github.com/matplotlib/basemap/tree/master/examples
    """

    # Lambert Conformal map of lower 48 states.
    plt.figure(figsize=(10, 8))
    m = Basemap(llcrnrlon=-119, llcrnrlat=22, urcrnrlon=-64, urcrnrlat=49,
                projection='lcc', lat_1=33, lat_2=45, lon_0=-95, resolution='c', )
    ax = plt.gca()  # get current axes instance
    m.drawmapboundary(fill_color='white')
    dmas = m.readshapefile(shapefile, 'dmas', drawbounds=True, color='lightblue')
    # cwas = m.readshapefile('c_10nv20/c_10nv20', 'cwas', drawbounds=True, color='lightgreen')
    m.readshapefile('cb_2018_us_state_5m/cb_2018_us_state_5m', 'states', drawbounds=True, color='grey')

    paths = []
    eclipselist=["ASE_1908_06_28", "ASE_1940_04_07", "ASE_1984_05_30", "ASE_2023_10_14", "ASE_2084_07_03", "ASE_2093_07_23", "TSE_1900_05_28", "TSE_1918_06_08", "TSE_1959_10_02", "TSE_2017_08_21", "TSE_2024_04_08", "TSE_2045_08_12", "TSE_2078_05_11", "TSE_2079_05_01", ]
    for eclipse in eclipselist:
        if '202' not in eclipse:
            continue
        m.readshapefile(f'mygeodata/{eclipse}-line', f'{eclipse}-polygon', drawbounds=True, color='red')
        m.readshapefile(f'mygeodata/{eclipse}-polygon', f'{eclipse}-polygon', drawbounds=True, color='blue')
        for info, shape in zip(m.__dict__[f'{eclipse}-polygon'], m.__dict__[f'{eclipse}-polygon']):
            print(info)
            paths.append(Polygon(np.array(shape), True))
        ax.add_collection(PatchCollection(paths, facecolor='grey', edgecolor='k', linewidths=1., zorder=1, alpha=0.2))

    CWG_Markets = ['SEATTLE-TACOMA', 'BOSTON', 'JACKSONVILLE, BRUNSWICK', 'DAYTON', 'ORLANDO-DAYTONA BCH-MELBRN',
                   'CHARLOTTE', 'PITTSBURGH', 'ATLANTA', 'BIRMINGHAM', 'MACON', 'EUGENE']
    markets = set()

    patches = []
    for info, shape in zip(m.dmas_info, m.dmas):
        # print(info)
        markets.add(info['NAME'])
        if 'EUGENE' in info['NAME']:
            print (info['NAME'])
        if info['NAME'] in CWG_Markets:
            patches.append(Polygon(np.array(shape), True))
    ax.add_collection(PatchCollection(patches, facecolor='m', edgecolor='k', linewidths=1., zorder=2, alpha=0.2))
    pprint(markets)

    # print(shp_dma)
    # for info, lightning in zip(m.shp_dma, m.dmas):
    #     print(info)

    return ax


def alaska_transform(xy):
    """Transform Alaska's geographical placement so fits on US map"""
    x, y = xy
    return (0.3 * x + 1000000, 0.3 * y - 1100000)


def hawaii_transform(xy):
    """Transform Hawaii's geographical placement so fits on US map"""
    x, y = xy
    return (x + 5250000, y - 1400000)


class MyTestCase(unittest.TestCase):

    def test_plot(self):
        usa_state_colormap(shapefile='dma_2008/DMAs', segmentname='NAME',
                           title='by DMA')
        plt.tight_layout()
        plt.show()


# san bernadino, CA is split up among 3 CWAs


if __name__ == '__main__':
    unittest.main()
