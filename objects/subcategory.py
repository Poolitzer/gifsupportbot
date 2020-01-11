from constants import DEVICES


class Subcategory(object):

    def __init__(self, description, keywords, path, worker, help_link=""):
        self.description = description
        self.devices = self.create_device_list()
        self.help_link = help_link
        self.keywords = keywords
        self.category_path = path
        self.workers = [worker]

    @staticmethod
    def create_device_list():
        temp = {}
        for device in DEVICES:
            temp[device] = {"file_id": None, "message_id": None}
        return temp
