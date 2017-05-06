#! /usr/bin/python2.7

############################################## standard libs
import sys
from copy import deepcopy
from math import degrees, radians, floor, ceil
##############################################  numpy
import numpy
##############################################  pystrain
from pystrain.strain import *
from pystrain.geodesy.utm import *
from pystrain.iotools.iparser import *
############################################## ploting
from mpl_toolkits.basemap import Basemap
import matplotlib.pyplot as plt

def plot_map(sta_list, stensor_list):
    lat0    = degrees(sum([ x.lat for x in sta_list ])/len(sta_list))
    lon0    = degrees(sum([ x.lon for x in sta_list ])/len(sta_list))
    lons    = [ degrees(x.lon) for x in sta_list ]
    lats    = [ degrees(x.lat) for x in sta_list ]
    lon_off = (max(lons)-min(lons))/10
    lat_off = (max(lats)-min(lats))/10
    my_map = Basemap(projection='merc', lat_0 = lat0, lon_0 = lon0, resolution = 'c', llcrnrlon=min(lons)-lon_off, llcrnrlat=min(lats)-lat_off, urcrnrlon=max(lons)+lon_off, urcrnrlat=max(lats)+lat_off)
    my_map.drawcoastlines()
    my_map.drawcountries()
    my_map.fillcontinents(color = 'coral')
    my_map.drawmapboundary()
    my_map.drawmeridians(numpy.arange(floor(min(lons)), ceil(max(lons)), 2), labels=[True,False,False,True])
    my_map.drawparallels(numpy.arange(floor(min(lats)), ceil(max(lats)), 2), labels=[False,True,True,False], fontsize=10)

    for sta in sta_list:
        x, y = my_map(degrees(sta.lon), degrees(sta.lat))
        my_map.plot(x, y, 'bo', markersize=10)
        plt.text(x, y, sta.name)
        print 'Point at {}, {}'.format(degrees(sta.lon), degrees(sta.lat))

    for tnr in stensor_list:
        x, y = my_map(degrees(tnr.lon), degrees(tnr.lat))
        my_map.plot(x, y, 'r+', markersize=8)
        print 'Tensor at {}, {}'.format(degrees(tnr.lon), degrees(tnr.lat))

    print '[DEBUG] Area is {}/{}/{}/{}'.format(min(lons), max(lons), min(lats), max(lats))
    plt.show()
    return

X_GRID_STEP = 40000
Y_GRID_STEP = 40000
print '[DEBUG] x and y step sizes are {} and {} meters on UTM'.format(X_GRID_STEP, Y_GRID_STEP)

##  Parse stations from input file
sta_list_ell = parse_ascii_input( sys.argv[1] )
print '[DEBUG] Number of stations parsed: {}'.format(len(sta_list_ell))

##  Make a new station list (copy of the original one), where all coordinates
##+ are in UTM. All points should belong to the same ZONE.
mean_lon = degrees(sum([ x.lon for x in sta_list_ell ])/len(sta_list_ell))
utm_zone = floor(mean_lon/6)+31
utm_zone = utm_zone + int(utm_zone<=0)*60 - int(utm_zone>60)*60
print '[DEBUG] Mean longtitude is {} deg.; using Zone = {} for UTM'.format(mean_lon, utm_zone)
sta_list_utm = deepcopy(sta_list_ell)
for idx, sta in enumerate(sta_list_utm):
    N, E, Zone, lcm = ell2utm(sta.lat, sta.lon, Ellipsoid("wgs84"), utm_zone)
    sta_list_utm[idx].lon = E
    sta_list_utm[idx].lat = N
    assert Zone == utm_zone, "[ERROR] Invalid UTM Zone."
print '[DEBUG] Station list transformed to UTM.'

##  Construct the grid, based on station coordinates (Ref. UTM)
grd = make_grid(sta_list_utm, X_GRID_STEP, Y_GRID_STEP)
print '[DEBUG] Constructed the grid. Limits are:'
print '\tEasting : from {} to {} with step {}'.format(grd.x_min, grd.x_max, grd.x_step)
print '\tNorthing: from {} to {} with step {}'.format(grd.y_min, grd.y_max, grd.y_step)

print '[DEBUG] Estimating strain tensor for each cell center'
##  Iterate through the grid (on each cell center)
strain_list = []
prev_x = 0
prev_y = 0
for x, y in grd:
    clat, clon = utm2ell(x, y, utm_zone)
    print '\t[DEBUG] Strain at E={}, N={} (lat={}, lon={})'.format(x, y, degrees(clat), degrees(clon))
    print '\t[DEBUG] x_step={}, y_step={}'.format(x-prev_x, y-prev_y)
    ##  Construct the LS matrices, A and b
    A, b = ls_matrices(sta_list_utm, x, y)
    ##  Solve LS
    estim, res, rank, sing_vals = numpy.linalg.lstsq(A, b)
    ## print result
    # print '\tUx={}\n\tUy={}\n\tomega={}\n\tTx={}\n\tTxy={}\n\tTy={}'.format(x[0], x[1], x[2], x[3], x[4], x[5])
    strain_list.append(Station(lat=clat, lon=clon))
    prev_x = x
    prev_y = y

plot_map(sta_list_ell, strain_list)
