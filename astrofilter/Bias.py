from os import path, listdir
import numpy as np
from astrofilter import Image

class Bias(Image.Image):
    def __init__(self, image, options={}):
        if isinstance(image, str):
            if path.isdir(image):
                _path = image
                files = listdir(_path)
                image = []
                for f in files:
                    if path.isfile(_path+f) and f.endswith('.fits'):
                        image.append(_path+f)
            elif path.isfile(image):
                super().__init__(image, options)
            else:
                raise Exception('that\'s not a file or directory.')

        if isinstance(image, list):
            for f in image[:5]:
                i = Image.Image(f, options)
                if not 'data' in locals():
                    data = [i.data]
                else:
                    data = np.append(data, [i.data], axis = 0)
                del i
            super().__init__(np.median(data, axis = 0), options)
            del data
