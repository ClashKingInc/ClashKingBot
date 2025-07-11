import subprocess
import time

import matplotlib.image as mpimg
import matplotlib.pyplot as plt
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer


def show_image(path):
    img = mpimg.imread(path)
    height, width = img.shape[:2]

    dpi = 100  # You can increase if you want a larger window
    figsize = (width / dpi, height / dpi)

    plt.clf()
    plt.close()
    plt.figure(figsize=figsize, dpi=dpi)

    fig = plt.gcf()
    fig.patch.set_alpha(0)
    plt.imshow(img)
    plt.axis('off')
    plt.subplots_adjust(left=0, right=1, top=1, bottom=0)
    plt.margins(0, 0)
    plt.gca().set_position([0, 0, 1, 1])
    plt.tight_layout(pad=0)
    plt.pause(0.001)


class ImageRegenerator(FileSystemEventHandler):
    def __init__(self):
        self.last = 0

    def on_modified(self, event):
        if event.src_path.endswith('canvas.py'):
            now = time.time()
            if now - self.last < 0.5:  # debounce
                return
            self.last = now
            print('Regenerating image...')
            subprocess.run(['python', 'canvas.py'])
            show_image('preview.png')


# Initial generation
subprocess.run(['python', 'canvas.py'])
plt.ion()
show_image('preview.png')

observer = Observer()
observer.schedule(ImageRegenerator(), path='.', recursive=False)
observer.start()

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    observer.stop()
observer.join()
