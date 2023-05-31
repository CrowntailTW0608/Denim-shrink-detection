

import sys
import numpy as np
from PIL import Image, ImageOps, ImageDraw
from scipy.ndimage import morphology, label
import cv2


def find_boxes(orig):
    # img = ImageOps.grayscale(orig)
    img = cv2.cvtColor(orig, cv2.COLOR_BGR2GRAY)
    im = np.array(img)

    # Inner morphological gradient.
    im = morphology.grey_dilation(im, (3, 3)) - im

    # Binarize.
    mean, std = im.mean(), im.std()
    t = mean + std
    im[im < t] = 0
    im[im >= t] = 1

    # Connected components.
    lbl, numcc = label(im)
    # Size threshold.
    min_size = 200 # pixels
    box = []
    for i in range(1, numcc + 1):
        py, px = np.nonzero(lbl == i)
        if len(py) < min_size:
            im[lbl == i] = 0
            continue

        xmin, xmax, ymin, ymax = px.min(), px.max(), py.min(), py.max()
        # Four corners and centroid.
        box.append([
            [(xmin, ymin), (xmax, ymin), (xmax, ymax), (xmin, ymax)],
            (np.mean(px), np.mean(py))])

    return im.astype(np.uint8) * 255, box


class myRet():
    def __init__(self,
                 x1_saved:str=None,y1_saved:str=None,
                 x2_saved:str=None,y2_saved:str=None):

        def chk_num(v:str):
            if not v :
                return None
            elif not v.isnumeric():
                return None
            elif v.isnumeric():
                return int(v)
            else:
                raise type(v)

        self.x1_saved = chk_num(x1_saved)
        self.y1_saved = chk_num(y1_saved)
        self.x2_saved = chk_num(x2_saved)
        self.y2_saved = chk_num(y2_saved)

        self.saved = all( [self.x1_saved,self.y1_saved,self.x2_saved,self.y2_saved] )

        if self.saved:
            self.x1, self.y1, self.x2, self.y2 = self.x1_saved,self.y1_saved,self.x2_saved,self.y2_saved
        else:
            self.x1, self.y1, self.x2, self.y2 = None, None, None, None

    def set_start_pt(self, x, y):
        self.x1, self.y1 = x, y

    def set_end_pt(self, x, y):
        self.x2, self.y2 = x, y

    def has_start_pts(self):
        return True if self.x1 and self.y1 else False

    def pts(self):
        return self.x1, self.y1, self.x2, self.y2

    def get_saved_pts(self):
        return {'x1_saved': self.x1_saved, 'y1_saved': self.y1_saved,
                'x2_saved': self.x2_saved, 'y2_saved': self.y2_saved}

    def save_pts(self):
        self.saved = True
        self.x1_saved, self.y1_saved, self.x2_saved, self.y2_saved = self.x1, self.y1, self.x2, self.y2

    def clear(self):
        self.set_start_pt(None, None)
        self.set_end_pt(None, None)
        self.clear_save()

    def clear_save(self):
        self.x1_saved, self.y1_saved, self.x2_saved, self.y2_saved = None, None, None, None
        self.saved = False


class MyVideoCapture:
    def __init__(self, video_source=0,width=800, height=600):
        self.vid = cv2.VideoCapture(video_source)
        if not self.vid.isOpened():
            raise ValueError("Unable to open this camera \n select another video source", video_source)

        # self.width = self.vid.get(cv2.CAP_PROP_FRAME_WIDTH)
        # self.height = self.vid.get(cv2.CAP_PROP_FRAME_HEIGHT)

        self.width,self.height = width, height

        self.flipped = True
        self.flipped = False

    def read(self):
        if self.vid.isOpened():
            isTrue, frame = self.vid.read()
            if isTrue:
                if self.flipped:
                    frame = cv2.flip(frame, 1)
                frame = cv2.resize(frame, (self.width,self.height), interpolation=cv2.INTER_AREA)
                return (isTrue, cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))

            else:
                return (isTrue, None)
        else:
            return (False, None)

    def __del__(self):
        if self.vid.isOpened():
            self.vid.release()
