import numpy as np
from astropy.io import fits

class Image:
    def __init__(self, image, options={}):
        exposure = options.get('exposure', None)

        if isinstance(image, Image):
            self.data = image.image
            self.exposure = image.exposure or exposure
        elif isinstance(image, str):
            hdulist = fits.open(image)
            hdu = hdulist[0]
            self.data = np.asarray(hdu.data, dtype=np.float32)
            self.exposure = hdu.header[exposure] if isinstance(exposure, str) else exposure
            del hdu
            hdulist.close()
        elif isinstance(image, fits.HDUList):
            hdu = image[0]
            self.data = np.asarray(hdu.data, dtype=np.float32)
            self.exposure = hdu.header[exposure] if isinstance(exposure, str) else exposure
            del hdu
        elif isinstance(image, fits.PrimaryHDU):
            self.data = np.asarray(image.data, dtype=np.float32)
            self.exposure = hdu.header[exposure] if isinstance(exposure, str) else exposure
        elif isinstance(image, np.ndarray):
            self.data = image
            self.exposure = exposure
        else:
            raise TypeError('only Image, str, fits HDUList, fits PrimaryHDU, and numpy ndarray are allowed.');
