import astropy.io.fits as pyfits
from numpy import *
from jplephem.spk import SPK
from tdb2tdt import tdb2tdt

# To run the code one needs to have access to one of the ephemeride files provided by jpl:
# https://ssd.jpl.nasa.gov/ftp/eph/planets/bsp/
# here I use the DE421 file

kernel = SPK.open('de421.bsp')

c = 299792.458 # km/s  (kilometers per second)

def barycor(date,ra,dec, orbit=False, return_correction=True, approx_einstein=10):
    """Apply barycentric correction to vector 
       date (in MJD) assuming coordinates ra,dec given in degrees
       optionally use orbit of a satellinte in heasarc format
       This includes geometric and shapiro corrections, but einstein
       correction is not implemented for now. Accurate to about 3e-4s.
       If return_correction=True (default), correction in seconds is returned.
       approx einstein is used to define number of points to calculate interpolated einstein correction (0 means do for each data point).
    see also https://asd.gsfc.nasa.gov/Craig.Markwardt/bary/ for detail and https://pages.physics.wisc.edu/~craigm/idl/ephem.html for the codebase
    which at least inspired the code below.
    v0.2: 21.03.2022 by V. Doroshenko
       """
    ra = radians(double(ra))
    dec = radians(double(dec))
    jd =  array(date,dtype=float64) + 2400000.5

    msol = 0.0002959122082855911
    
    # get positions and velocities of the sun, earth-moon barycenter and earth
    (x_sun,y_sun,z_sun),(vx_sun,vy_sun,vz_sun) = kernel[0,10].compute_and_differentiate(jd)
    (x_em,y_em,z_em),(vx_em,vy_em,vz_em) = kernel[0,3].compute_and_differentiate(jd)
    (x_e,y_e,z_e),(vx_e,vy_e,vz_e) = kernel[3,399].compute_and_differentiate(jd)
    
    
    x_earth = x_em + x_e
    y_earth = y_em + y_e
    z_earth = z_em + z_e
    
    vx_earth = (vx_em + vx_e)/86400 # velocities are always distance units per day as per jplephem documentation, so need to divide to get km/s
    vy_earth = (vy_em + vy_e)/86400
    vz_earth = (vz_em + vz_e)/86400
    

    if orbit:
        orbit = pyfits.open(orbit)
        mjdref = orbit[1].header['mjdreff']+orbit[1].header['mjdrefi']
        try:            
            minmet = (min(date)-1.-mjdref)*86400
            maxmet =(max(date)+1.-mjdref)*86400
        except:
            minmet = (date-1-mjdref)*86400
            maxmet = (date+1-mjdref)*86400
        try:
            t = orbit[1].data.field('time')
        except:
            t = orbit[1].data.field('sclk_utc')
        mi, ma = t.searchsorted([minmet,maxmet])
        t = t[mi:ma]/86400.+mjdref
        
        # interpolate orbit to observed time and convert to km and km/s
        try:            
            x_s = interp(date, t, orbit[1].data.field('x')[mi:ma]/1000.)
            y_s = interp(date, t, orbit[1].data.field('y')[mi:ma]/1000.)
            z_s = interp(date, t, orbit[1].data.field('z')[mi:ma]/1000.)
        
            vx_s = interp(date, t, orbit[1].data.field('vx')[mi:ma]/1000.)
            vy_s = interp(date, t, orbit[1].data.field('vy')[mi:ma]/1000.)
            vz_s = interp(date, t, orbit[1].data.field('vz')[mi:ma]/1000.)
        except:
            x_s = interp(date, t, orbit[1].data.field('pos_x')[mi:ma]/1000.)
            y_s = interp(date, t, orbit[1].data.field('pos_y')[mi:ma]/1000.)
            z_s = interp(date, t, orbit[1].data.field('pos_z')[mi:ma]/1000.)
        
            vx_s = interp(date, t, orbit[1].data.field('vel_x')[mi:ma]/1000.)
            vy_s = interp(date, t, orbit[1].data.field('vel_y')[mi:ma]/1000.)
            vz_s = interp(date, t, orbit[1].data.field('vel_z')[mi:ma]/1000.)
            
            
        
        x_obs, y_obs, z_obs = x_earth + x_s, y_earth + y_s, z_earth + z_s
        vx_obs, vy_obs, vz_obs = vx_earth + vx_s, vy_earth + vy_s, vz_earth + vz_s
        # orbital correction
        ocor = (vx_earth*x_s+vy_earth*y_s+vz_earth*z_s)/c**2
    else:
        x_obs, y_obs, z_obs = x_earth, y_earth , z_earth
        vx_obs, vy_obs, vz_obs = vx_earth , vy_earth , vz_earth
        ocor = 0.
        
    # #components of the object unit vector:
    x_obj = cos(dec)*cos(ra)
    y_obj = cos(dec)*sin(ra)
    z_obj = sin(dec)

    #geometric correction
    geo_corr = (x_obs*x_obj + y_obs*y_obj + z_obs*z_obj)/c

    #einstein correction
    if approx_einstein == 0:
        einstein_corr = tdb2tdt(jd)
    else:
        xx = linspace(jd.min(),jd.max(),approx_einstein)
        einstein_corr = tdb2tdt(xx)
        einstein_corr = interp(jd,xx,einstein_corr)
    #shapiro correction ("Shapiro") = - (2 G Msun/c^3) log(1 + cos th)
    sun_dist = sqrt((x_sun-x_obs)**2+(y_sun-y_obs)**2+(z_sun-z_obs)**2)
    costh = ((x_obs-x_sun)*x_obj+(y_obs-y_sun)*y_obj + (z_obs-z_sun)*z_obj)/sun_dist
    shapiro_corr = - 9.8509819e-06*log(1.+costh)
    corr = geo_corr + ocor + einstein_corr - shapiro_corr
    if return_correction:
        return corr
    else:
        return date + corr/86400.
