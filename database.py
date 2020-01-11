import logging
import re

from pymongo import MongoClient, UpdateOne, DeleteOne
from bson import ObjectId
import json

from betterdict.thesaurus import thes, Keypath


class Database:
    # users = for users, gifs = for created and edited gifs, posts = for posts
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.logger.debug("Database init")
        self.db = MongoClient()
        self.db = self.db["gifsupportbot"]
        self.categories = json.load(open("./categories.json"), object_hook=thes)

    def save_categories(self):
        with open("./categories.json", "w") as outfile:
            json.dump(self.categories, outfile, indent=4, sort_keys=True)

    def add_category(self, path):
        try:
            self.categories.set_path(path, None)
        except KeyError:
            return False
        self.save_categories()
        return True

    def rename_category(self, old_path, new_path):
        old = Keypath(old_path)
        new = Keypath(new_path)
        # genius work by dave, https://t.me/PythonThesaurus/125
        self.categories[new[:-1]][new[-1]] = self.categories[old[:-1]][old[-1]]
        del self.categories[old[:-1]][old[-1]]
        updated_categories = self.update_subcategory_path(old_path, new_path)
        self.save_categories()
        return updated_categories

    def delete_category(self, path):
        keypath = Keypath(path)
        try:
            # TODO get value from here
            self.categories[keypath[:-1]][keypath[-1]]
        except KeyError:
            return "error"
        del self.categories[keypath[:-1]][keypath[-1]]
        pass_on = self.delete_subcategory(path)
        # TODO
        """
        if value:
            pass_on.append(str(value))
        """
        self.save_categories()
        return pass_on

    def get_categories(self):
        return [i.replace("_", " ") for i in self.categories.keys()]

    def get_next_category(self, category_path):
        # thanks to https://stackoverflow.com/a/37704379 (ITS 10 AM OKAY. ME FEELING STUPID)
        path = [i.replace(" ", "_") for i in category_path]
        datadict = self.categories
        for k in path:
            datadict = datadict[k]
        if datadict:
            datadict = list(datadict.keys())
        if datadict:
            return [i.replace("_", " ") for i in datadict]
        else:
            return datadict

    def get_category(self, category_path):
        if category_path:
            try:
                return self.categories[category_path]
            except KeyError:
                return False
        else:
            return self.categories

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

    def get_gif(self, gif_id):
        gif_id = ObjectId(gif_id)
        return self.db.gifs.find_one({"_id": gif_id})

    def get_gif_edited_gif_id(self, gif_id):
        gif_id = ObjectId(gif_id)
        return self.db.gifs.find_one({"_id": gif_id})["edited_gif_id"]

    def get_gif_worker(self, gif_id, worker):
        gif_id = ObjectId(gif_id)
        return self.db.gifs.find_one({"_id": gif_id})["workers"][worker]

    def get_subcategorie_device(self, path, device):
        if self.db["categories"].find_one({"path": path, f"devices.{device}.file_id": {"$type": "string"}}):
            # subcategory already has a GIF for that device
            return False
        return True

    def is_gif_in_categories(self, category_path):
        if self.db["categories"].find_one({"category_path": category_path}):
            return True
        else:
            return False

    def insert_subcategory(self, subcategory):
        return str(self.db["categories"].insert_one(vars(subcategory)).inserted_id)

    def insert_device(self, category_path, device, file_id, message_id):
        self.db["categories"].update_one({"category_path": category_path},
                                         {"$set": {f"devices.{device}.file_id": file_id,
                                                   "devices.{device}.message_id": message_id}})

    def get_subcategory(self, category_path):
        return self.db["categories"].find_one({"category_path": category_path})

    def get_subcategory_keywords(self, category_path):
        return self.db["categories"].find_one({"category_path": category_path})["keywords"]

    def get_subcategory_devices(self, category_path):
        devices = self.db["categories"].find_one({"category_path": category_path})["devices"]
        temp = {}
        for device in devices:
            if devices[device]["message_id"]:
                temp[device] = devices[device]
        return temp

    def get_subcategory_help_link(self, category_path):
        return self.db["categories"].find_one({"category_path": category_path})["help_link"]

    def get_subcategories(self, category_path):
        category_path.replace(".", r"\.")
        return self.db["categories"].find({"category_path": {"$regex": rf'{category_path}'}})

    def insert_subcategory_worker(self, category_path, user_id):
        self.db["categories"].update_one({"category_path": category_path}, {"$push": {"workers": user_id}})

    def update_subcategory_path(self, old_category_path, new_category_path):
        old_category_path.replace(".", r"\.")
        temp = self.db["categories"].find({"category_path": {"$regex": rf'{old_category_path}'}})
        path_list = [i["category_path"] for i in temp]
        requests = []
        to_return = {"changed_categories": len(path_list), "post": []}
        for path in path_list:
            new_path = re.sub(rf'{old_category_path}\.', f'{new_category_path}', path)
            requests.append(UpdateOne(path, {"category_path": new_path}))
            old_last = path.split(".")[-1]
            new_last = new_path.split(".")[-1]
            # that means title changed, we have to edit the channel
            if old_last != new_last:
                # I am not trusting that temp and path_list have the same index
                wanted_category = self.db["categories"].find_one({"category_path": path})
                for device in wanted_category["devices"]:
                    # that means a channel post exists
                    if wanted_category["devices"][device]["message_id"]:
                        to_return["post"].append({"device": device, "help_link": wanted_category["help_link"],
                                                  "message_id": wanted_category["devices"][device]["message_id"]})
        if requests:
            self.db["categories"].bulk_write(requests)
        return to_return

    def delete_subcategory(self, category_path):
        category_path.replace(".", r"\.")
        temp = self.db["categories"].find({"category_path": {"$regex": rf'{category_path}'}})
        requests = []
        to_return = []
        for category in temp:
            requests.append(DeleteOne(category["category_path"]))
            for device in category["devices"]:
                # that means a channel post exists
                if category["devices"][device]["message_id"]:
                    to_return.append({"message_id": category["devices"][device]["message_id"],
                                      "gif_id": category["_id"]})
        if requests:
            self.db["category"].bulk_write(requests)
        return to_return

    def update_subcategory_description(self, category_path, description):
        temp = self.db["categories"].find_one({"category_path": category_path})
        self.db["categories"].update_one({"category_path": category_path}, {"$set": {"description": description}})
        return temp["description"]

    def update_subcategory_link(self, category_path, help_link):
        temp = self.db["categories"].find_one({"category_path": category_path})
        to_return = {"help_link": temp["help_link"], "messages": []}
        if help_link == "None":
            help_link = None
        self.db["categories"].update_one({"category_path": category_path}, {"$set": {"help_link": help_link}})
        for device in temp["devices"]:
            if temp["devices"][device]["message_id"]:
                to_return["messages"].append({"device": device, "message_id": temp["devices"][device]["message_id"]})
        return to_return

    def delete_subcategory_keyword(self, category_path, keyword):
        self.db["categories"].update_one({"category_path": category_path}, {"$pull": {"keywords": keyword}})

    def insert_subcategory_keyword(self, category_path, keyword):
        self.db["categories"].update_one({"category_path": category_path}, {"$addToSet": {"keywords": keyword}})

    def update_subcategory_gif(self, category_path, device, old_file_id, new_file_id):
        to_return = {"gif_id": "", "sub_id": "", "help_link": ""}
        gif_id = self.db.gifs.find_one({"edited_gif_id": old_file_id})['_id']
        to_return["gif_id"] = str(gif_id)
        self.db.gifs.update_one({"edited_gif_id": old_file_id}, {"$set": {"edited_gif_id": new_file_id}})
        sub = self.db["categories"].find_one({"category_path": category_path})
        to_return["sub_id"] = str(sub["_id"])
        to_return["help_link"] = sub["help_link"]
        self.db["categories"].update_one({"category_path": category_path},
                                         {"$set": {f"devices.{device}.file_id": new_file_id}})
        return to_return

    def get_subcategories_device(self, device):
        to_return = []
        for category in self.get_categories():
            subs = self.db[category].find({f"devices.{device}.file_id": {"$type": "string"}})
            for sub in subs:
                to_return.append(sub)
        return to_return

    def get_all_subcategories(self):
        to_return = []
        for category in self.get_categories():
            subs = self.db[category].find()
            for sub in subs:
                to_return.append(sub)
        return to_return


database = Database()
