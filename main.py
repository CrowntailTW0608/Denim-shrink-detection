import os.path
import tkinter as tk
from tkinter import filedialog
from tkinter import messagebox
from tkinter import ttk
import cv2
import time
from PIL import Image, ImageTk
import numpy as np
import datetime
import configparser
from PIL import Image

import matplotlib
matplotlib.use("TkAgg")
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg#, NavigationToolbar2TkAgg
from matplotlib.figure import Figure

import matplotlib.pyplot as plt

config = configparser.ConfigParser()
config.read('config.ini')


# some config
width, height = 800, 600
# width, height = 1600, 1200

imageflip_lr = False
dict_mode_tkinter_color = {'STANDARD': 'green', 'DETECTION': 'blue'}
dict_mode_opencv_color = {'STANDARD': (0, 255, 120), 'DETECTION': (0, 0, 255)}
FPS = 15

from myUtils import myRet, MyVideoCapture, find_boxes

class Application:

    def __init__(self, root, cap):
        '''
        :param root:
        :param cap:
        '''
        self.root = root
        self.cap = cap
        self.paused = False

        tabControl = ttk.Notebook(root, style='lefttab.TNotebook')  # Create Tab Control

        tabfram_mainstream = ttk.Frame(tabControl)
        tabControl.add(tabfram_mainstream, text='Main')

        tabControl.pack(expand=1, fill="both")

        standard_ret = myRet(**config['STANDARD'])
        detection_ret = myRet(**config['DETECTION'])

        self.dict_area_ret = {'STANDARD': standard_ret, 'DETECTION': detection_ret}
        self.dict_area_panel_ret = {'STANDARD': None, 'DETECTION': None}

        self.guiMainStream(tabfram_mainstream)
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        self.tic = time.time()

    def guiMainStream(self, root):

        self.cnt_hist_refresh_s = 0
        # 創建StringVar，用於保存筆刷顏色
        self.color = tk.StringVar(value='GREEN')
        self.area_mode = tk.StringVar(value='STANDARD')  # STANDARD #DETECTION

        framMainStream = ttk.Frame(root)
        framMainStream.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=5, pady=5)

        framMainStreamLeft = ttk.Frame(framMainStream)
        framMainStreamLeft.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=1, pady=2)
        framMainStreamRight = ttk.LabelFrame(framMainStream, text='-')
        framMainStreamRight.pack(side=tk.RIGHT, fill=tk.BOTH, expand=False, padx=1, ipadx=3, pady=24)

        # Main cavans
        framMainStreamLeftTop = ttk.Frame(framMainStreamLeft)
        framMainStreamLeftTop.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=1, pady=2)

        # color historgram
        framMainStreamLeftBottom = ttk.Frame(framMainStreamLeft)
        framMainStreamLeftBottom.pack(side=tk.BOTTOM, fill=tk.BOTH, expand=True, padx=1, pady=2)

        # self.panel = tk.Label(framMainStreamLeftTop)
        self.main_cavas = tk.Canvas(framMainStreamLeftTop, width=width - 1, height=height - 1, bg='black')
        self.main_cavas.pack(side=tk.TOP, padx=5, pady=10)

        image = np.zeros((height, width, 3)).astype(np.uint8)
        image = Image.fromarray(image)
        image = ImageTk.PhotoImage(image)

        # self.panel.configure(image=image)
        self.main_cavas.create_image(0, 0, image=image, anchor=tk.NW)
        # self.panel.image = image

        mydpi = 60
        self.fig_hist, self.axesHist = plt.subplots(1, 2, figsize=((width - 5)/mydpi, (height //2)//mydpi ),dpi=mydpi )
        self.axesHist[0].plot([0], [0])
        # self.axesHist[0].set_xlabel('Frequency(Hz)')
        # self.axesHist[0].set_ylabel('Amplitude')
        self.axesHist[0].set_title('STANDARD')

        self.axesHist[1].plot([0], [0])
        # self.axesHist[1].set_xlabel('Frequency(Hz)')
        # self.axesHist[1].set_ylabel('Amplitude')
        self.axesHist[1].set_title('DETECTION')

        self.fig_hist.suptitle('Histogram update every 5s ')
        self.fig_hist.tight_layout()

        self.tkplotHist = FigureCanvasTkAgg(self.fig_hist, framMainStreamLeftBottom)
        self.tkplotHist._tkcanvas.pack(side=tk.TOP,  fill=tk.BOTH, expand=True)

        self.dict_mode_axes = dict_mode_tkinter_color = {'STANDARD': self.axesHist[0], 'DETECTION': self.axesHist[1]}


        self.gui_image_btn_start = ttk.Button(framMainStreamRight, text="開始", width=10,
                                              command=lambda: self.btn_function_main_stream("START"))
        self.gui_image_btn_start.pack(side=tk.TOP, pady=3, ipady=12)

        self.gui_image_btn_pause = ttk.Button(framMainStreamRight, text="暫停", width=10,
                                              command=lambda: self.btn_function_main_stream("PAUSE"))
        self.gui_image_btn_pause.pack(side=tk.TOP, pady=3, ipady=12)

        self.gui_image_btn_save = ttk.Button(framMainStreamRight, text="儲存", width=10,
                                             command=lambda: self.btn_function_main_stream("SAVE"))
        self.gui_image_btn_save.pack(side=tk.TOP, pady=3, ipady=12)

        self.gui_image_btn_save = ttk.Button(framMainStreamRight, text="設定標準框", width=10,
                                             command=lambda: self.btn_function_main_stream("SET_STANDARD"))
        self.gui_image_btn_save.pack(side=tk.TOP, pady=3, ipady=12)
        self.gui_image_btn_save = ttk.Button(framMainStreamRight, text="設定檢測框", width=10,
                                             command=lambda: self.btn_function_main_stream("SET_DETECTION"))
        self.gui_image_btn_save.pack(side=tk.TOP, pady=3, ipady=12)

        tk.Radiobutton(framMainStreamRight, text="標準區域", variable=self.area_mode, value='STANDARD',
                       command=self.set_ret_color).pack(side=tk.TOP, pady=3, ipady=12)
        tk.Radiobutton(framMainStreamRight, text="檢測區域", variable=self.area_mode, value='DETECTION',
                       command=self.set_ret_color).pack(side=tk.TOP, pady=3, ipady=12)

        self.save = False
        self.paused = True
        self.brush_size = tk.Scale(framMainStreamRight, from_=1, to=50, orient='horizontal')
        self.brush_size.set(10)
        self.brush_size.pack(side=tk.TOP, pady=3, ipady=12)

        self.setup()

    def setup(self):

        self.main_cavas.bind('<B1-Motion>', self.paint_ret)
        self.main_cavas.bind('<ButtonRelease-1>', self.reset)

    def set_ret_color(self):
        self.color.set(dict_mode_opencv_color[self.area_mode.get()])

    def save_image(self)->bool:
        path = r'./images/saved/image_{}.png'.format(datetime.datetime.now().strftime("%Y%m%d%H%M%S"))
        if not os.path.isdir(os.path.dirname(path)): os.makedirs(os.path.dirname(path))
        cv2.imwrite(path, cv2.cvtColor(self.img, cv2.COLOR_RGB2BGR))

    def update_stream(self):
        if not self.paused:
            ret, frame = self.cap.read()
            if ret:
                self.toc = time.time()
                fps = 1/(self.toc-self.tic)

                self.frame = frame
                img = frame

                # img, box = find_boxes(img)

                self.img = img


                self.show_fps(img, fps)
                self.tic = time.time()


            self.delay = int(1000 / FPS)
            self.root.after(self.delay, self.update_stream)

        if self.frame is not None:
            img = self.show_ret_info()
            self.img = img
            tk_img = ImageTk.PhotoImage(image=Image.fromarray(self.img))
            self.tk_img = tk_img   #to prevent the image be recycled by system
            self.main_cavas.create_image(1, 1, image=tk_img, anchor=tk.NW)



    def show_fps(self,img,fps):
        cv2.putText(img, 'FPS : {:.1f}'.format(fps), (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1, cv2.LINE_AA)

    def btn_function_main_stream(self, select):
        '''
        :param select: button
        :return: None
        '''
        if select == 'START':
            self.paused = False
            self.update_stream()
        elif select == 'PAUSE':
            self.paused = True
        elif select == 'SAVE':
            self.save_image()

    def show_ret_info(self):
        '''
        update the rectangle on panel
        :globol vars : panel,
        :return: None
        '''
        img = self.frame.copy()
        for am, r in self.dict_area_ret.items():
            if r.saved:
                x1, y1, x2, y2 = r.pts()
                cv2.rectangle(img, (x1, y1), (x2, y2), color=dict_mode_opencv_color[am], thickness=1, lineType=cv2.LINE_AA)

                s = self.cal_satraturation(self.frame[y1:y2, x1:x2, :])
                s = 'sat_{:.3f}_{:.3f}'.format(s[0], s[1])
                cv2.putText(img, s, (x1,y1-10), cv2.FONT_HERSHEY_SIMPLEX,0.3, (0, 0, 0), 1, cv2.LINE_AA)

                s = self.cal_light(self.frame[y1:y2, x1:x2, :])
                s = 'light_{:.3f}_{:.3f}'.format(s[0], s[1])
                cv2.putText(img, s, (x1,y1-10-10), cv2.FONT_HERSHEY_SIMPLEX,0.3, (0, 0, 0), 1, cv2.LINE_AA)

                s = self.cal_HLS(self.frame[y1:y2, x1:x2, :])
                s = 'hls{:.3f}_{:.3f}_{:.3f}'.format(s[0], s[1], s[2])
                cv2.putText(img, s, (x1,y1-10-10-10), cv2.FONT_HERSHEY_SIMPLEX,0.3, (0, 0, 0), 1, cv2.LINE_AA)

                if self.cnt_hist_refresh_s >= 5*FPS:
                    # draw color hist
                    ax = self.dict_mode_axes[am]
                    dict_hist = self.cal_hist(self.frame[y1:y2, x1:x2, :])
                    self.draw_hist(ax,dict_hist)

        if self.cnt_hist_refresh_s >= 5*FPS:
            self.tkplotHist.draw()
            self.cnt_hist_refresh_s = 0


        if all([r.saved for _, r in self.dict_area_ret.items()]):

            x1, y1, x2, y2 = self.dict_area_ret['STANDARD'].pts()
            self.cal_satraturation(self.frame[y1:y2, x1:x2, :])
            h_s, l_s, s_s = self.cal_HLS(self.frame[y1:y2, x1:x2, :])

            x1, y1, x2, y2 = self.dict_area_ret['DETECTION'].pts()
            self.cal_satraturation(self.frame[y1:y2, x1:x2, :])
            h_d, l_d, s_d = self.cal_HLS(self.frame[y1:y2, x1:x2, :])

            error = np.sqrt((h_d - h_s) ** 2 + (l_s - l_d) ** 2)

            self.show_level(img, error)

        self.cnt_hist_refresh_s += 1

        return img

    def show_level(self,img,error_scroe:float)->None:
        '''
        show level result on image
        :param error_scroe:
        :return:
        '''
        x = width-80
        y = 50
        font_size = 40
        font_color = 'Green'

        level = self.get_level(error_scroe)
        color = (0, 255, 100) if float(level) >= 4 else (255, 150, 20)

        cv2.putText(img, '{:.3f}'.format(error_scroe), (x, y+20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1, cv2.LINE_AA)
        cv2.putText(img, level, (x, y), cv2.FONT_HERSHEY_SIMPLEX, 1.6, color, 2, cv2.LINE_AA)

    def paint_ret(self, event):

        self.paused = True
        am = self.area_mode.get()
        ret = self.dict_area_ret[am]
        img = self.frame

        if ret.saved: ret.clear()

        if ret.has_start_pts():
            self.main_cavas.create_image(1, 1, image=self.tk_img, anchor=tk.NW)

            self.show_ret_info()

            ret.set_end_pt(event.x, event.y)
            x1, y1, x2, y2 = ret.pts()
            self.main_cavas.create_rectangle(x1, y1, x2, y2, fill=None, outline=dict_mode_tkinter_color[am])
            # cv2.rectangle(img, (x1, y1), (x2, y2), color=dict_mode_color[am], thickness=1, lineType=cv2.LINE_AA)

        if not ret.has_start_pts():
            ret.set_start_pt(event.x, event.y)

        # self.update_stream()


    def reset(self, event):
        am = self.area_mode.get()
        ret = self.dict_area_ret[am]

        msg_box = tk.messagebox.askquestion('設定框', '確認儲存框框?', icon='warning')
        if msg_box == 'yes':
            ret.save_pts()
            self.show_ret_info()
        else:
            ret.clear()
            self.update_stream()

    def cal_satraturation(self, img):

        fImg = img.astype(np.float32)
        hlsCopy = cv2.cvtColor(fImg, cv2.COLOR_BGR2HLS)

        return np.mean(hlsCopy[:, :, 2]),np.std(hlsCopy[:, :, 2])

    def cal_light(self, img):

        fImg = img.astype(np.float32)
        hlsCopy = cv2.cvtColor(fImg, cv2.COLOR_BGR2HLS)

        return np.mean(hlsCopy[:, :, 1]),np.std(hlsCopy[:, :, 1])

    def cal_HLS(self, img):

        # 圖像歸一化，且轉換為浮點型
        fImg = img.astype(np.float32)
        # fImg = fImg / 255.0

        # 顏色空間轉換 BGR -> HLS
        hlsCopy = cv2.cvtColor(fImg, cv2.COLOR_BGR2HLS)
        return np.mean(hlsCopy[:, :, 0]),np.mean(hlsCopy[:, :, 1]),np.mean(hlsCopy[:, :, 2])

    def cal_hist(self,img):
        color = ('r','b', 'g' )
        dict_hist = {}
        for channel, col in enumerate(color):
            histr = cv2.calcHist([img], [channel], None, [256], [0, 256])/len(img.flatten())
            dict_hist[col] = histr
        return dict_hist

    def draw_hist(self, ax, dict_hist):
        ax.clear()
        for color,hist in dict_hist.items():
            ax.plot(hist, color=color)
        return ax


    def get_level(self,val:float)->float:
        '''

        :param val:
        :return:
        '''
        assert isinstance(val,float) or isinstance(val,int)
        if val >= 50:
            val = '1'
        elif val >= 36:
            val = '1.5'
        elif val >= 27:
            val = '2'
        elif val >= 19:
            val = '2.5'
        elif val >= 15:
            val = '3'
        elif val >= 11:
            val = '3.5'
        elif val >= 7:
            val = '4'
        elif val > 3:
            val = '4.5'
        else:
            val = '5'
        return val

    def on_closing(self):
        if messagebox.askokcancel("Quit", "Do you want to quit?"):
            del self.cap
            for ret_name,ret_pts in self.dict_area_ret.items():
                for pt_namem,pt_val in ret_pts.get_saved_pts().items():
                    config.set(ret_name,pt_namem,str(pt_val))

            with open(r'config.ini', 'w') as configfile:
                config.write(configfile)

            self.root.destroy()




def main():

    # initail capture
    cap = MyVideoCapture(0 + cv2.CAP_DSHOW,width, height)

    root = tk.Tk()
    root.title("Denim shrink detection")
    root.bind('<Escape>', lambda e: root.quit())
    app = Application(root, cap)
    root.mainloop()


if __name__ == '__main__':
    main()
