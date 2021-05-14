#builtin
import requests
import json
from os import path
from time import sleep

#installed
import numpy as np
from astropy.io import fits
from skimage import img_as_ubyte, measure, exposure

#own
from astrofilter import Image, Bias, Dark, Flat

class Light(Image.Image):
    def __init__(self, image, options={}):
        super().__init__(image, options);

    def bias(self, image, options={}):
        bias = Bias.Bias(image, options)
        self.data-=bias.data
        if options.get('return', False):
            return bias
        del bias
        return self

    def dark(self, image, bias=None, options={}):
        dark = Dark.Dark(image, bias, options)
        self.data-=dark.data*self.exposure
        if options.get('return', False):
            return dark
        del dark
        return self

    def flat(self, image, bias=None, dark=None, options={}):
        flat = Flat.Flat(image, bias, dark, options)
        self.data/=flat.data
        if options.get('return', False):
            return flat
        del flat
        return self

    def binary(self):
        return self.binary or np.asarray(1 * (image > image.min()), dtype=bool)

    def filter(self):
        self.data = np.clip(self.data, np.mean(self.data)+2*np.std(self.data), None)
        binary = np.asarray(1 * (self.data > self.data.min()), dtype=bool)
        regions = measure.label(binary, connectivity=1)
        regions = measure.regionprops(regions, self.data)
        objects = np.asarray([])
        for region in regions:
            if region.area > 4:
                objects = np.append([region], objects)
            else:
                for pair in region.coords:
                    binary[pair[0],pair[1]] = 0
                    self.data[pair[0],pair[1]] = 0
        self.objects = objects
        self.binary = binary
        del binary
        del regions
        del objects
        return self

    def locate(self, key, callback=None):
        fits.PrimaryHDU(self.data).writeto(f'{path.dirname(path.abspath(__file__))}/tmp.fits', overwrite=True)
        r = requests.post('http://nova.astrometry.net/api/login', data={'request-json': json.dumps({"apikey": key})})
        session = json.loads(r.text)['session']
        url = 'http://nova.astrometry.net/api/upload'
        files = {'file': ('image.fits', open(f'{path.dirname(path.abspath(__file__))}/tmp.fits','rb'), 'application/octet-stream', {'Expires': '0'})}
        data = {"session": session}
        r = requests.post(url, files=files, data={'request-json': json.dumps(data)})
        submission = json.loads(r.text)["subid"]
        if callback is not None:
            callback({'submission': submission})
        @interval(10)
        def awaitJob():
            r = requests.post('http://nova.astrometry.net/api/submissions/'+str(submission))
            jobs = json.loads(r.text)["jobs"]
            return jobs[0] if len(jobs) > 0 else None
        job = awaitJob()
        if callback is not None:
            callback({'submission': submission, 'job': job})
        @interval(10)
        def awaitJobDone():
            r = requests.post('http://nova.astrometry.net/api/jobs/'+str(job))
            status = json.loads(r.text)["status"]
            return status if status != 'solving' else None
        status = awaitJobDone()
        if callback is not None:
            callback({'submission': submission, 'job': job, 'status': status})
        return self

    def histogramEqualize(self, kernel_size=16, clip_limit=0.05, bins=256):
        image = self.data
        image/= image.max()
        image = np.clip(image, 0, 1)
        return img_as_ubyte(exposure.equalize_adapthist(image, kernel_size, clip_limit, bins))

    def equalizeBins(self):
        sort = self.data.flatten().argsort()
        view = self.data.flatten()[sort]
        for i in range(256):
            view.put(range(round(view.size/256*i), round(view.size/256*(i+1))), i)
        view = view[sort.argsort()]
        del sort
        return view.reshape(self.data.shape)

    def compare(self, job):
        r = requests.post(f'http://nova.astrometry.net/api/jobs/{job}/annotations')
        annotations = json.loads(r.text)['annotations']
        nova = []
        new = []
        numbers = []
        for o in self.objects:
            isNew = True
            for a in annotations:
                if abs(a['pixelx'] - o.centroid[0]) <= 4 and abs(a['pixely'] - o.centroid[1]) <= 4:
                    isNew = False
            if isNew:
                new.append({"radius": o.equivalent_diameter/2, "pixelx": o.centroid[0], "pixely": o.centroid[1]})
        return {'nova': annotations, 'new': new}



def interval(time):
    def decorator(func):
        def wrapper(*args, **kwargs):
            value = None
            while value==None:
                value = func(*args, **kwargs)
                sleep(time)
            return value
        return wrapper
    return decorator
