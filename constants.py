def set_resized_height(conf):
    global DEFAULT_RESIZED_HEIGHT
    # 360/width*height
    DEFAULT_RESIZED_HEIGHT = 360 / conf.resolution[0] * conf.resolution[1] 

DEFAULT_RESIZED_HEIGHT = 240
