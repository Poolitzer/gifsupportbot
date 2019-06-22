class Gif(object):

    def __init__(self, original, device, recorder, edit=""):
        self.recorded_gif_id = original
        self.recorded_gif_bumps = []
        self.edited_gif_id = edit
        self.edited_gif_bumps = []
        self.device = device
        self.workers = {"recorder": recorder, "editor": 0, "manager": 0}
