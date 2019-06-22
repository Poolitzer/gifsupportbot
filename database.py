import logging
from constants import CATEGORIES
from pymongo import MongoClient
from bson import ObjectId


class Database:
    # users = for users, gifs = for created and edited gifs, posts = for posts
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.logger.debug("Database init")
        self.db = MongoClient()
        self.db = self.db["gifsupportbot"]

    def insert_user(self, user):
        temp = self.db.users.find_one({"id": user.id})
        if temp:
            self.db.users.update_one({"id": user.id}, {"$set": {'positions': user.positions}})
        else:
            self.db.users.insert_one(vars(user))

    def remove_user(self, user_id):
        count = self.db["users"].delete_one({"id": user_id}).deleted_count
        if count == 0:
            return False
        else:
            return True

    def is_user_in_database(self, user_id):
        temp = self.db.users.find_one({"id": user_id})
        if temp:
            return True
        else:
            return False

    def is_user_position(self, user_id, position):
        temp = self.db.users.find_one({"id": user_id, f'positions.{position}': {"$exists": True}})
        if temp:
            return True
        else:
            return False

    def get_user_devices(self, user_id):
        temp = self.db.users.find_one({"id": user_id})
        to_return = []
        for device in temp["devices"].keys():
            to_return.append(device)
        return to_return

    def insert_user_device(self, user_id, device):
        self.db.users.update_one({"id": user_id}, {"$set": {'devices': device}})

    def insert_gif(self, gif):
        return str(self.db.gifs.insert_one(vars(gif)).inserted_id)

    def delete_gif(self, gif_id):
        gif_id = ObjectId(gif_id)
        self.db.gifs.delete_one({"_id": gif_id})

    def insert_edited_gif(self, gif_id, user_id, edited_gif_id):
        gif_id = ObjectId(gif_id)
        self.db.gifs.update_one({"_id": gif_id}, {"$set": {"edited_gif_id": edited_gif_id,
                                                           "workers.editor": user_id}})

    def insert_gif_recorded_bump(self, gif_id, message_id):
        gif_id = ObjectId(gif_id)
        self.db.gifs.update_one({"_id": gif_id}, {"$addToSet": {"recorded_gif_bumps": message_id}})

    def insert_gif_edited_bump(self, gif_id, message_id):
        gif_id = ObjectId(gif_id)
        self.db.gifs.update_one({"_id": gif_id}, {"$addToSet": {"edited_gif_bumps": message_id}})

    def insert_gif_manager(self, gif_id, user_id):
        gif_id = ObjectId(gif_id)
        self.db.gifs.update_one({"_id": gif_id}, {"$set": {"workers.manager": user_id}})

    def get_gif_recorded_bumps(self, gif_id):
        gif_id = ObjectId(gif_id)
        return self.db.gifs.find_one({"_id": gif_id})["recorded_gif_bumps"]

    def get_gif_edited_bumps(self, gif_id):
        gif_id = ObjectId(gif_id)
        return self.db.gifs.find_one({"_id": gif_id})["edited_gif_bumps"]

    def get_gif_device(self, gif_id):
        gif_id = ObjectId(gif_id)
        return self.db.gifs.find_one({"_id": gif_id})["device"]

    def get_gif_recorded_id(self, gif_id):
        gif_id = ObjectId(gif_id)
        return self.db.gifs.find_one({"_id": gif_id})["recorded_gif_id"]

    def get_gif_edited_gif_id(self, gif_id):
        gif_id = ObjectId(gif_id)
        return self.db.gifs.find_one({"_id": gif_id})["edited_gif_id"]

    def get_gif_worker(self, gif_id, worker):
        gif_id = ObjectId(gif_id)
        return self.db.gifs.find_one({"_id": gif_id})["workers"][worker]

    def get_subcategories_device_category(self, category, device):
        to_return = []
        for post in self.db[category].find({f"devices.{device}.file_id": {"$not": {"$type": "string"}}}):
            to_return.append(post["title"])
        return to_return

    def get_subcategories_title(self, category):
        to_return = []
        for post in self.db[category].find():
            to_return.append(post["title"])
        return to_return

    def is_title_unique(self, category, title):
        temp = self.db[category].find_one({"title": title})
        if temp:
            return True
        else:
            return False

    def insert_subcategory(self, category, subcategory):
        return str(self.db[category].insert_one(vars(subcategory)).inserted_id)

    def insert_device(self, category, title, device, file_id, message_id):
        self.db[category].update_one({"title": title}, {"$set": {f"devices.{device}.file_id": file_id,
                                                                 f"devices.{device}.message_id": message_id}})

    def get_subcategory(self, category, title):
        return self.db[category].find_one({"title": title})

    def get_subcategory_keywords(self, category, title):
        return self.db[category].find_one({"title": title})["keywords"]

    def get_subcategory_devices(self, category, title):
        devices = self.db[category].find_one({"title": title})["devices"]
        temp = {}
        for device in devices:
            if devices[device]["message_id"]:
                temp[device] = devices[device]
        return temp

    def get_subcategory_help_link(self, category, title):
        return self.db[category].find_one({"title": title})["help_link"]

    def get_subcategories(self, category):
        return self.db[category].find()

    def insert_subcategory_worker(self, category, title, user_id):
        self.db[category].update_one({"title": title}, {"$push": {"workers": user_id}})

    def update_subcategory_title(self, category, old_title, new_title):
        temp = self.db[category].find_one({"title": old_title})
        self.db[category].update_one({"title": old_title}, {"$set": {"title": new_title}})
        to_return = []
        for device in temp["devices"]:
            if temp["devices"][device]["message_id"]:
                to_return.append({"device": device, "message_id": temp["devices"][device]["message_id"],
                                  "help_link": temp["help_link"]})
        return to_return

    def update_subcategory_description(self, category, title, description):
        temp = self.db[category].find_one({"title": title})
        self.db[category].update_one({"title": title}, {"$set": {"description": description}})
        return temp["description"]

    def update_subcategory_link(self, category, title, help_link):
        temp = self.db[category].find_one({"title": title})
        to_return = {"help_link": temp["help_link"], "messages": []}
        self.db[category].update_one({"title": title}, {"$set": {"help_link": help_link}})
        for device in temp["devices"]:
            if temp["devices"][device]["message_id"]:
                to_return["messages"].append({"device": device, "message_id": temp["devices"][device]["message_id"]})
        return to_return

    def delete_subcategory_keyword(self, category, title, keyword):
        self.db[category].update_one({"title": title}, {"$pull": {"keywords": keyword}})

    def insert_subcategory_keyword(self, category, title, keyword):
        self.db[category].update_one({"title": title}, {"$addToSet": {"keywords": keyword}})

    def update_subcategory_gif(self, category, title, device, old_file_id, new_file_id):
        to_return = {"gif_id": "", "sub_id": "", "help_link": ""}
        gif_id = self.db.gifs.find_one({"edited_gif_id": old_file_id})['_id']
        to_return["gif_id"] = str(gif_id)
        self.db.gifs.update_one({"edited_gif_id": old_file_id}, {"$set": {"edited_gif_id": new_file_id}})
        sub = self.db[category].find_one({"title": title})
        to_return["sub_id"] = str(sub["_id"])
        to_return["help_link"] = sub["help_link"]
        self.db[category].update_one({"title": title}, {"$set": {f"devices.{device}.file_id": new_file_id}})
        return to_return

    def get_subcategories_device(self, device):
        to_return = []
        for category in CATEGORIES:
            subs = self.db[category].find({f"devices.{device}.file_id": {"$type": "string"}})
            for sub in subs:
                to_return.append(sub)
        return to_return

    def get_all_subcategories(self):
        to_return = []
        for category in CATEGORIES:
            subs = self.db[category].find()
            for sub in subs:
                to_return.append(sub)
        return to_return


database = Database()
