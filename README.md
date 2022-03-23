# Python implementation of barycentric correction

Mostly indended for correction of satellite data (shall work with most orbit files), i.e. does not include some fancy stuff common for high-precision pulsar timing.
The code is inspired by this [write-up](https://asd.gsfc.nasa.gov/Craig.Markwardt/bary/) by Craig Markward and has been tested agains HEASARC barycor task to $\sim1e-7$\,s.
By default de421 ephemerides by JPL are used, but those are not included in the repo and need to be downloaded from [JPL](https://ssd.jpl.nasa.gov/ftp/eph/planets/bsp/).
Other ephemerides (like de200 used by barycorr by default) can also be used. 

