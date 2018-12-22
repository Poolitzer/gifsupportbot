from uuid import uuid4
from github import Github
from telegram import (InlineQueryResultArticle, InputTextMessageContent, InlineKeyboardMarkup, MessageEntity, ParseMode,
                      ReplyKeyboardMarkup, ReplyKeyboardRemove)
from telegram.ext import (CommandHandler, Updater, Filters, ConversationHandler, InlineQueryHandler,
                          CallbackQueryHandler, MessageHandler)
from telegram.inline.inlinekeyboardbutton import InlineKeyboardButton
from telegram.error import BadRequest
from telegram.utils.helpers import mention_html
import json
import logging
import re
from pymongo import MongoClient
from bson import ObjectId

logging.basicConfig(filename="log.log", format='%(asctime)s - %(first_name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

database = json.load(open('./database.json'))
tokenbase = json.load(open('./tokens.json'))

(TITLE, DESCRIPTION, KEYWORDS, DEVICE, NEW_GIF, POSITION, DEVICES, WHAT, WHAT_DEVICE, EXISTING_GIF, NEW_EXISTING_GIF,
 EDITED, ANOTHER_EXISTING_GIF, POST_TITEL, POST_DESCRIPTION, POST_LINK, DEVICES_ADD, EDIT_TITLE, EDIT_DESCRIPTION,
 EDIT_NEW_DEVICE, EDIT_DEVICE, EDITED_NEW) = range(22)


class Database:
    # users = for users, gifs = for created and edited gifs, posts = for posts and voting
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.logger.debug("Database init")
        self.db = MongoClient()
        self.db = self.db["gifsupportbot"]

    def insert_user(self, user):
        temp = self.db.users.find_one({"id": user["id"]})
        if temp:
            self.db.users.update_one({"id": user["id"]}, {"$set": {'positions': user["positions"]}})
        else:
            self.db.users.insert_one(user)

    def insert_user_device(self, user_id, device):
        self.db.users.update_one({"id": user_id}, {"$set": {'devices': device}})

    def insert_gif(self, gif):
        return self.db.gifs.insert_one(gif).inserted_id

    def add_gif_device(self, gif_id, device, file_id, user_id):
        gif_id = ObjectId(gif_id)
        self.db.gifs.update_one({"_id": gif_id}, {"$set": {'added.' + device: file_id,
                                                           'added.' + device + "_edited": False}},
                                {"$unset": {"devices." + device: ""}},
                                {"$addToSet": {"people": user_id}})

    def start_edit(self, gif_id, device):
        self.db.gifs.update_one({"_id": ObjectId(gif_id)}, {"$set": {'added.' + device + "_edited": True}})

    def add_gif_edited(self, gif_id, device, file_id, user_id):
        gif_id = ObjectId(gif_id)
        self.db.gifs.update_one({"_id": gif_id}, {"$set": {'added.' + device: file_id,
                                                           'added.' + device + "_managed": False}},
                                {"$addToSet": {"people": user_id}})

    def abort_edit(self, gif_id, device):
        self.db.gifs.update_one({"_id": ObjectId(gif_id)}, {"$set": {"added." + device + "_edited": False}})

    def start_manage(self, gif_id, device):
        self.db.gifs.update_one({"_id": ObjectId(gif_id)}, {"$set": {'added.' + device + "_managed": True}})

    def add_gif_managed(self, gif_id, device, user_id):
        gif_id = ObjectId(gif_id)
        self.db.gifs.update_one({"_id": gif_id}, {"$set": {'added.' + device + "_done": True}},
                                {"$addToSet": {"people": user_id}})

    def abort_manage(self, gif_id, device):
        self.db.gifs.update_one({"_id": ObjectId(gif_id)}, {"$set": {'added' + device + "_managed": False}})

    def insert_voter(self, post_id, voter):
        self.db.posts.update_one({"post_id": post_id}, {"$addToSet": {'voters': voter}})

    def insert_demo_voter(self, post_id, voter):
        self.db.demo_posts.update_one({"post_id": post_id}, {"$addToSet": {'voters': voter}})

    def update_vote(self, post_id, voter_id, votes):
        temp = self.db.posts.find_one({"post_id": post_id})['voters']
        for voter in temp:
            if voter["id"] == voter_id:
                voter["voted"] = votes
        self.db.posts.update_one({"post_id": post_id}, {"$set": {'voters': temp}})

    def update_demo_vote(self, post_id, voter_id, votes):
        temp = self.db.demo_posts.find_one({"post_id": post_id})['voters']
        for voter in temp:
            if voter["id"] == voter_id:
                voter["voted"] = votes
        self.db.demo_posts.update_one({"post_id": post_id}, {"$set": {'voters': temp}})


Database = Database()


class User:

    def __init__(self, user_id, mention, positions):
        self.id = user_id
        self.mention = mention
        self.positions = positions
        self.devices = []


class Gif:

    def __init__(self, title, description, added, devices, people):
        self.title = title
        self.description = description
        self.added = added
        self.devices = devices
        self.people = people


class Voter:

    def __init__(self, user_id, mention, lang_code, voted):
        self.id = user_id
        self.mention = mention
        self.lang_code = lang_code
        self.voted = voted


class Helpers:

    @staticmethod
    def text_creator(index):
        text = "<a href=\"https://t.me/gifsupport/{}\">{}</a> :)" \
            .format(database["links"][index][2], database["links"][index][0])
        return InputTextMessageContent(text, ParseMode.HTML)

    @staticmethod
    def text_creator_demo(index):
        text = "<a href=\"https://t.me/gifsupport/{}\">{}</a> :)" \
            .format(database["links_demo"][index][2], database["links_demo"][index][0])
        return InputTextMessageContent(text, ParseMode.HTML)

    @staticmethod
    def device_buttons(callback_data):
        temp = []
        subtemp = []
        x = 0
        for device in database["devices"]:
            subtemp.append(InlineKeyboardButton(device, callback_data=callback_data + device))
            x += 1
            if x is 2:
                temp.append(subtemp)
                subtemp = []
                x = 0
        if subtemp:
            temp.append(subtemp)
        return temp

    @staticmethod
    def device_buttons_remove(remove):
        temp = []
        subtemp = []
        x = 0
        for device in database["devices"]:
            not_skip = False
            for get_deleted in remove:
                if device == get_deleted:
                    not_skip = True
                    break
            if not_skip:
                pass
            else:
                subtemp.append(InlineKeyboardButton(device, callback_data="user_devices" + device))
                x += 1
                if x is 2:
                    temp.append(subtemp)
                    subtemp = []
                    x = 0
        if subtemp:
            temp.append(subtemp)
        return temp

    @staticmethod
    def user_device(user_id, callback_data):
        temp = []
        subtemp = []
        x = 0
        user_devices = Database.db.users.find_one({"id": user_id})["devices"]
        if not user_devices:
            return None
        for device in user_devices:
            subtemp.append(InlineKeyboardButton(device, callback_data=callback_data + device))
            x += 1
            if x is 2:
                temp.append(subtemp)
                subtemp = []
                x = 0
        if subtemp:
            temp.append(subtemp)
        return InlineKeyboardMarkup(temp)

    @staticmethod
    def notification(bot, position, device, insert_id):
        text = ""
        button = [[InlineKeyboardButton("Yes, I have time", callback_data=position + str(insert_id) + device)]]
        if position == "editing":
            text = "Hello there. A new GIF wants to be edited. Can you? :)"
        elif position == "managing":
            text = "Hello there. A new GIF wants to be added to the channel. Can you? :)"
        for user in Database.db.users.find():
            try:
                if user["positions"][position]:
                    bot.send_message(user["id"], text, reply_markup=InlineKeyboardMarkup(button))
            except KeyError:
                pass

    @staticmethod
    def markup_creator(post_id):
        pro = 0
        con = 0
        for voter in Database.db.posts.find_one({"post_id": post_id})["voters"]:
            if voter["voted"] == 1:
                pro += 1
            if voter["voted"] == -1:
                con += 1
        return InlineKeyboardMarkup([[InlineKeyboardButton("👍{}".format(pro), callback_data="vote_yes"),
                                      InlineKeyboardButton("👎{}".format(con), callback_data="vote_no")]])

    @staticmethod
    def markup_demo_creator(post_id):
        pro = 0
        con = 0
        for voter in Database.db.demo_posts.find_one({"post_id": post_id})["voters"]:
            if voter["voted"] == 1:
                pro += 1
            if voter["voted"] == -1:
                con += 1
        return InlineKeyboardMarkup([[InlineKeyboardButton("👍{}".format(pro), callback_data="demo_vote_yes"),
                                      InlineKeyboardButton("👎{}".format(con), callback_data="demo_vote_no")]])

    @staticmethod
    def query_answer_creator(post_id):
        pro = 0
        con = 0
        for voter in Database.db.posts.find_one({"post_id": post_id})["voters"]:
            if voter["voted"] == 1:
                pro += 1
            if voter["voted"] == -1:
                con += 1
        return "👍 - {}\n👎 - {} \n\n Counters in the post will be updated soon".format(pro, con)

    @staticmethod
    def query_answer_demo_creator(post_id):
        pro = 0
        con = 0
        for voter in Database.db.demo_posts.find_one({"post_id": post_id})["voters"]:
            if voter["voted"] == 1:
                pro += 1
            if voter["voted"] == -1:
                con += 1
        return "👍 - {}\n👎 - {} \n\n Counters in the post will be updated soon".format(pro, con)


Helpers = Helpers()


def start_admin(_, update):
    button = [["Video recording"], ["Video editing"], ["Channel managing"], ["Video recording + editing"],
              ["Video recording + Channel managing"], ["Video editing + Channel managing"], ["GIVE ME ALL OF IT!"]]
    update.message.reply_text("Hey. Great that you want to contribute to this project. "
                              "Please choose what you want to do.",
                              reply_markup=ReplyKeyboardMarkup(button, one_time_keyboard=True, resize_keyboard=True))
    return POSITION


def add_position(_, update, user_data):
    text = update.message.text
    user_id = update.effective_user.id
    mention = update.effective_user.mention_html()
    devices = True
    if text == "Video recording":
        Database.insert_user(vars(User(user_id, mention, {"recording": True})))
    elif text == "Video editing":
        Database.insert_user(vars(User(user_id, mention, {"editing": True})))
        devices = False
    elif text == "Channel managing":
        Database.insert_user(vars(User(user_id, mention, {"managing": True})))
        devices = False
    elif text == "Video recording + editing":
        Database.insert_user(vars(User(user_id, mention, {"recording": True, "editing": True})))
    elif text == "Video recording + Channel managing":
        Database.insert_user(vars(User(user_id, mention, {"recording": True, "managing": True})))
    elif text == "Video editing + Channel managing":
        Database.insert_user(vars(User(user_id, mention, {"editing": True, "managing": True})))
        devices = False
    else:
        Database.insert_user(vars(User(user_id, mention, {"recording": True, "editing": True, "managing": True})))
    if devices:
        user_data["devices"] = {}
        update.message.reply_text("Great. Please tell me which devices you want to record for.",
                                  reply_markup=InlineKeyboardMarkup(Helpers.device_buttons("user_devices")))
        return DEVICES
    else:
        update.message.reply_text("Great. I will notify you if there is a job to do",
                                  reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END


def user_device(_, update, user_data):
    query = update.callback_query
    device = query.data[12:len(query.data)]
    user_data["devices"][device] = True
    known = user_data["devices"]
    query.edit_message_text("Want to add another one? Cool. Else, send /finish.",
                            reply_markup=InlineKeyboardMarkup(Helpers.device_buttons_remove(known)))
    return DEVICES


def finish_devices(_, update, user_data):
    Database.insert_user_device(update.effective_user.id, user_data["devices"])
    update.message.reply_text("Cool. Got your devices. Want to add a GIF right now? Send /add.",
                              reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END


def add_db(_, update):
    buttons = [[InlineKeyboardButton("New", callback_data="what_new"),
                InlineKeyboardButton("Existing", callback_data="what_existing")]]
    update.message.reply_text("A new GIF? Nice. Do you want to make a new one or add a specific device to an existing "
                              "GIF?", reply_markup=InlineKeyboardMarkup(buttons))
    return WHAT


def add_what(_, update, user_data):
    query = update.callback_query
    todo = query.data[5:len(query.data)]
    user_data["GIF"] = {}
    if todo == "new":
        query.edit_message_text("Great. Send me a title then")
        return TITLE
    else:
        buttons = Helpers.user_device(update.effective_user.id, "what_device")
        if not buttons:
            user_data["devices"] = {}
            query.edit_message_text("Lets start with adding your devices. Which do you have?",
                                    reply_markup=Helpers.device_buttons("user_devices"))
            return DEVICES_ADD
        query.edit_message_text("An existing it shall be. For what of your devices?", reply_markup=buttons)
        return WHAT_DEVICE


def add_user_device(_, update, user_data):
    query = update.callback_query
    device = query.data[12:len(query.data)]
    user_data["devices"][device] = True
    known = user_data["devices"]
    query.edit_message_text("Want to add another one? Cool. Else, send /finish.",
                            reply_markup=InlineKeyboardMarkup(Helpers.device_buttons_remove(known)))
    return DEVICES_ADD


def add_finish_devices(_, update, user_data):
    query = update.callback_query
    Database.insert_user_device(update.effective_user.id, user_data["devices"])
    try:
        if user_data["GIF"]["title"]:
            buttons = Helpers.user_device(update.effective_user.id, "what_device")
            query.edit_message_text("Cool. Now tell me for which of yours you would like to record",
                                    reply_markup=buttons)
            return DEVICE
    except KeyError:
        buttons = Helpers.user_device(update.effective_user.id, "device")
        query.edit_message_text("An existing it shall be. For what of your devices?", reply_markup=buttons)
        return WHAT_DEVICE


def add_title(_, update, user_data):
    user_data["GIF"]["title"] = update.message.text
    update.message.reply_html("<b>{}</b> it is. Please send me a good description now"
                              .format(update.message.text))
    return DESCRIPTION


def add_description(_, update, user_data):
    text = update.message.text
    user_data["GIF"]["description"] = text
    buttons = Helpers.user_device(update.effective_user.id, "device")
    if not buttons:
        user_data["devices"] = {}
        update.message.reply_text("<b>{}</b>, nice. I need to know your devices now. Which do you have?".format(text),
                                  reply_markup=Helpers.device_buttons("user_devices"))
        return DEVICES_ADD
    update.message.reply_html("<b>{}</b>, nice. Please tell me which devices you want to record for.".format(text),
                              reply_markup=buttons)
    return DEVICE


def add_device(_, update, user_data):
    query = update.callback_query
    device = query.data[6:len(query.data)]
    user_data["GIF"]["device"] = device
    query.edit_message_text("<b>{}</b> it is. Send your recorded GIF in the highest quality, as a file please :)"
                            .format(device), parse_mode=ParseMode.HTML)
    return NEW_GIF


def add_raw_gif(bot, update, user_data):
    if update.message.document.mime_type != "video/mp4":
        update.message.reply_text("Thats not a video. Please send a video as a file or /cancel to abort.")
        return NEW_GIF
    user_data["GIF"]["file_id"] = update.message.document.file_id
    temp_devices = database["devices"].copy()
    del temp_devices[user_data["GIF"]["device"]]
    gif = Gif(user_data["GIF"]["title"], user_data["GIF"]["description"],
              {user_data["GIF"]["device"]: user_data["GIF"]["file_id"], user_data["GIF"]["device"] + "_edited": False},
              temp_devices, [update.effective_user.id])
    insert_id = Database.insert_gif(vars(gif))
    buttons = Helpers.user_device(update.effective_user.id, "device")
    update.message.reply_text("Thanks for your submission. The editors have been informed :) Do you want to record for "
                              "another device? Else, send /finish", reply_markup=buttons)
    Helpers.notification(bot, "editing", user_data["GIF"]["device"], insert_id)
    return DEVICE


def finish_adding(_, update):
    update.message.reply_text("Cool. Have a nice day.")
    return ConversationHandler.END


def what_device(_, update, user_data):
    query = update.callback_query
    device = query.data[11:len(query.data)]
    user_data["GIF"]["device"] = device
    temp = []
    subtemp = []
    x = 0
    amount = 0
    for gif in Database.db.gifs.find({"devices." + device: True}):
        subtemp.append(InlineKeyboardButton(gif["title"], callback_data="gif" + str(gif["_id"])))
        x += 1
        amount += 1
        if x is 2:
            temp.append(subtemp)
            subtemp = []
            x = 0
        if amount == 8:
            break
    if amount == 0:
        query.edit_message_text("No existing GIFs for your device :(")
        return ConversationHandler.END
    if subtemp:
        temp.append(subtemp)
    query.edit_message_text("Pick one please", reply_markup=InlineKeyboardMarkup(temp))
    return EXISTING_GIF


def what_gif(_, update, user_data):
    query = update.callback_query
    gif_id = query.data[3:len(query.data)]
    user_data["GIF"]["id"] = gif_id
    query.edit_message_text("Cool. Send your recorded GIF in the highest quality, as a file please :)")
    return NEW_EXISTING_GIF


def new_existing_gif(bot, update, user_data):
    if update.message.document.mime_type != "video/mp4":
        update.message.reply_text("Thats not a video. Please send a video as a file or /cancel to abort.")
        return NEW_GIF
    user_data["GIF"]["file_id"] = update.message.document.file_id
    source = user_data["GIF"]
    Database.add_gif_device(source["id"], source["device"], source["file_id"], update.effective_user.id)
    buttons = Helpers.user_device(update.effective_user.id, "another")
    update.message.reply_text("Thanks for your submission. The editors have been informed :) Do you want to record for "
                              "another device? Else, send /finish", reply_markup=buttons)
    Helpers.notification(bot, "editing", source["device"], source["id"])
    return ConversationHandler.END


def another_gif(_, update, user_data):
    query = update.callback_query
    device = query.data[7:len(query.data)]
    user_data["GIF"]["device"] = device
    query.edit_message_text("Cool. Send your recorded GIF in the highest quality, as a file please :)")
    return NEW_EXISTING_GIF


def cancel(_, update):
    update.message.reply_text('Mission ABORTED!')
    return ConversationHandler.END


def edit_what(bot, update, user_data):
    query = update.callback_query
    gif_id = query.data[7:31]
    device = query.data[31:len(query.data)]
    gif = Database.db.gifs.find_one({"_id": ObjectId(gif_id)})
    if gif["added"][device + "_edited"]:
        try:
            if gif["added"][device + "_managed"]:
                query.message.reply_text("Sorry, someone finished editing :(")
        except KeyError:
            button = [[InlineKeyboardButton("check again", callback_data=query.data)]]
            query.message.reply_text("Someone was faster then you and is editing the file right now.",
                                     reply_markup=InlineKeyboardMarkup(button))
        return ConversationHandler.END
    else:
        user_data["GIF_edit"] = {}
        user_data["GIF_edit"]["id"] = gif_id
        user_data["GIF_edit"]["device"] = device
        Database.start_edit(gif_id, device)
        query.message.reply_text("Have fun. You can see the file below. Don't forget the startscreen.")
        bot.send_document(update.effective_chat.id, gif["added"][device])
        return EDITED


def add_edited(bot, update, user_data):
    user_data["GIF_edit"]["file_id"] = update.message.document.file_id
    source = user_data["GIF_edit"]
    Database.add_gif_edited(source["id"], source["device"], source["file_id"], update.effective_user.id)
    update.message.reply_text("Thanks for editing. The channel manager have been informed :)")
    Helpers.notification(bot, "managing", source["device"], source["id"])
    return ConversationHandler.END


def edit_instantly(_, update, user_data):
    user_data["GIF_edit_instant"] = {}
    update.message.reply_text("Well, thats cool. Lets start with the title. Send me one please")
    return EDIT_TITLE


def edit_add_title(_, update, user_data):
    user_data["GIF_edit_instant"]["title"] = update.message.text
    update.message.reply_html("<b>{}</b> it is. Please send me a good description now"
                              .format(update.message.text))
    return EDIT_DESCRIPTION


def edit_add_description(_, update, user_data):
    text = update.message.text
    user_data["GIF_edit_instant"]["description"] = text
    buttons = Helpers.user_device(update.effective_user.id, "edit_device")
    if not buttons:
        user_data["devices"] = {}
        update.message.reply_text("<b>{}</b>, nice. I need to know your devices now. Which do you have?".format(text),
                                  reply_markup=Helpers.device_buttons("user_devices"))
        return EDIT_NEW_DEVICE
    update.message.reply_html("<b>{}</b>, nice. Please tell me which devices you want to record for.".format(text),
                              reply_markup=buttons)
    return EDIT_DEVICE


def edit_user_device(_, update, user_data):
    query = update.callback_query
    device = query.data[12:len(query.data)]
    user_data["devices"][device] = True
    known = user_data["devices"]
    query.edit_message_text("Want to add another one? Cool. Else, send /finish.",
                            reply_markup=InlineKeyboardMarkup(Helpers.device_buttons_remove(known)))
    return EDIT_NEW_DEVICE


def edit_finish_devices(_, update, user_data):
    query = update.callback_query
    Database.insert_user_device(update.effective_user.id, user_data["devices"])
    buttons = Helpers.user_device(update.effective_user.id, "edit_device")
    query.edit_message_text("For what of your devices you'd like to send me the GIF?", reply_markup=buttons)
    return EDIT_DEVICE


def edit_add_device(_, update, user_data):
    query = update.callback_query
    device = query.data[11:len(query.data)]
    user_data["GIF_edit_instant"]["device"] = device
    query.edit_message_text("<b>{}</b> it is. Send the finished GIF now please :)"
                            .format(device), parse_mode=ParseMode.HTML)
    return EDITED_NEW


def add_edited_directly(bot, update, user_data):
    user_data["GIF_edit_instant"]["file_id"] = update.message.document.file_id
    source = user_data["GIF_edit_instant"]
    temp_devices = database["devices"].copy()
    del temp_devices[source["device"]]
    gif = Gif(source["title"], source["description"],
              {source["device"]: source["file_id"], source["device"] + "_edited": True,
               source["device"] + "_managed": False}, temp_devices, [update.effective_user.id])
    insert_id = Database.insert_gif(vars(gif))
    update.message.reply_text("Thanks for editing. The channel manager have been informed :)")
    Helpers.notification(bot, "managing", source["device"], insert_id)
    return ConversationHandler.END


def cancel_editing(_, update, user_data):
    update.message.reply_text('editing ABORTED!')
    gif_id = user_data["GIF_edit"]["gif_id"]
    Database.abort_edit(gif_id, user_data["GIF_edit"]["device"])
    return ConversationHandler.END


def manage_what(bot, update, user_data):
    query = update.callback_query
    gif_id = query.data[8:32]
    device = query.data[32:len(query.data)]
    gif = Database.db.gifs.find_one({"_id": ObjectId(gif_id)})
    if gif["added"][device + "_managed"]:
        try:
            if gif["added"][device + "_done"]:
                query.edit_message_text("Sorry, someone finished managing :(")
        except KeyError:
            button = [[InlineKeyboardButton("check again", callback_data=query.data)]]
            query.edit_message_text("Someone was faster then you and is managing the GIF right now.",
                                    reply_markup=InlineKeyboardMarkup(button))
        return ConversationHandler.END
    else:
        user_data["POST"] = {}
        user_data["POST"]["post"] = []
        user_data["POST"]["id"] = gif_id
        user_data["POST"]["device"] = device
        Database.start_manage(gif_id, device)
        button = InlineKeyboardMarkup([[InlineKeyboardButton("Yes", callback_data="yes_title")]])
        query.edit_message_text("Let's get this started. The internal title is <b>{}</b>, should this be the "
                                "title/question of the post as well? Press yes to apply it, or send me a more fitting "
                                "one.".format(gif["title"]), reply_markup=button, parse_mode=ParseMode.HTML)
        update.effective_message.reply_animation(gif["added"][device])
        return POST_TITEL


def new_title(_, update, user_data):
    text = update.message.text
    user_data["POST"]["post"].append(text)
    gif = Database.db.gifs.find_one({"_id": ObjectId(user_data["POST"]["id"])})
    button = InlineKeyboardMarkup([[InlineKeyboardButton("Yes", callback_data="yes_description")]])
    update.message.reply_html("<b>{}</b> it is. Same story with the description: Currently it is <b>{}</b>, do you want"
                              " to keep that? Send a better one else :)"
                              .format(text, gif["description"]), reply_markup=button)
    return POST_DESCRIPTION


def skip_title(_, update, user_data):
    query = update.callback_query
    gif = Database.db.gifs.find_one({"_id": ObjectId(user_data["POST"]["id"])})
    user_data["POST"]["post"].append(gif["title"])
    button = InlineKeyboardMarkup([[InlineKeyboardButton("Yes", callback_data="yes_description")]])
    query.edit_message_text("<b>{}</b> it is. Same story with the description: Currently it is <b>{}</b>, do you want "
                            "to keep that? Send a better one else :)"
                            .format(gif["title"], gif["description"]), reply_markup=button, parse_mode=ParseMode.HTML)
    return POST_DESCRIPTION


def new_description(_, update, user_data):
    text = update.message.text
    user_data["POST"]["post"].append(text)
    update.message.reply_html("<b>{}</b> it is. Please send me the link to the fitting telegraph section now ;)"
                              .format(text))
    return POST_LINK


def skip_description(_, update, user_data):
    query = update.callback_query
    gif = Database.db.gifs.find_one({"_id": ObjectId(user_data["POST"]["id"])})
    user_data["POST"]["post"].append(gif["title"])
    query.edit_message_text("<b>{}</b> it is. Please send me the link to the fitting telegraph section now ;)"
                            .format(gif["description"]))
    return POST_LINK


def add_link(bot, update, user_data):
    entities = update.message.entities
    if entities:
        if entities[0].type == MessageEntity.URL:
            pass
        else:
            update.message.reply_text("Please send me an URL, thanks :)")
            return POST_LINK
    else:
        update.message.reply_text("Please send me an URL, thanks :)")
        return POST_LINK
    user_data["POST"]["link"] = update.message.text
    user_data["keywords"] = []
    update.message.reply_text("Great URL. I like it. Please send me a keyword now.")
    return KEYWORDS


def add_keyword(_, update, user_data):
    messages = ["No one will see this. Sad story. Moving on",
                "You added the keyword <b>{}</b>. If you want to add another one, send it. If you are finished, send "
                "/finish.", "Heyy. A second keyword. It's <b>{}</b>, right?",
                "A third? Well, thats cool. <b>{}</b> this time.", "A fourth? :OOO <b>{}</b>. Don't forget /finish...",
                "ANOTHER ONE? You are kidding me, right? It's <b>{}</b>, neat", "I really like <b>{}</b>.",
                "Don't push it too far though, not even with <b>{}</b>.", "Ok. Its enough. <b>{}</b>.",
                "Please. Stop. <b>{}</b>", "I'm really not creative anymore. <b>{}</b>"]
    user_data["keywords"].append(update.message.text)
    try:
        update.message.reply_html(messages[len(user_data["keywords"])].format(update.message.text))
    except IndexError:
        update.message.reply_html(messages[-1].format(update.message.text))
    return KEYWORDS


def finish_keywords(bot, update, user_data):
    g = Github(tokenbase["GITHUBTOKEN"])
    posting_id = -1001353729458
    source = user_data["POST"]
    device = source["device"]
    post = source["post"]
    gif = Database.db.gifs.find_one({"_id": ObjectId(user_data["POST"]["id"])})
    caption = "{}\n\n#{} #gifsupport\n\n<a href=\"{}\">More help</a>".format(post[0], device, source["link"])
    vote_buttons = InlineKeyboardMarkup([[InlineKeyboardButton("👍", callback_data="vote_yes"),
                                         InlineKeyboardButton("👎", callback_data="vote_no")]])
    message = bot.send_animation(posting_id, gif["added"][device], caption=caption, parse_mode=ParseMode.HTML,
                                 reply_markup=vote_buttons)
    post.append(message.message_id)
    database["links"].append(post)
    database["keywords"].append(user_data["keywords"])
    bot.send_message(-1001374913393,
                     "Added {} to the database from {}, updated GitHub, pardon me for breathing which "
                     "I never do anyway, oh god this is so depressing"
                     .format(database["links"][-1][0],
                             mention_html(update.effective_user.id, update.effective_user.first_name)),
                     parse_mode=ParseMode.HTML)
    repo = g.get_repo('Poolitzer/gifsupportbot')
    contents = repo.get_contents("database.json", ref="master")
    repo.update_file(contents.path, "Automatically update database", json.dumps(database, indent=4, sort_keys=True),
                     contents.sha)
    with open('./database.json', 'w') as outfile:
        json.dump(database, outfile, indent=4, sort_keys=True)
    Database.add_gif_managed(source["id"], source["device"], update.effective_user.id)
    update.message.reply_text("SUCCESS. Thanks for adding a post. Have a good one".format(update.message.text))
    return ConversationHandler.END


def cancel_managing(_, update, user_data):
    update.message.reply_text('editing ABORTED!')
    gif_id = user_data["POST"]["gif_id"]
    Database.abort_manage(gif_id, user_data["POST"]["device"])
    return ConversationHandler.END


def vote(_, update, job_queue):
    query = update.callback_query
    todo = query.data[-2:len(query.data)]
    user = query.from_user
    post = Database.db.posts.find_one({"post_id": query.message.message_id})
    update_vote = Database.update_vote
    insert_vote = Database.insert_voter
    markup = Helpers.markup_creator
    return real_vote(query, todo, user, post, update_vote, insert_vote, markup, job_queue)


def demovote(_, update, job_queue):
    query = update.callback_query
    todo = query.data[-2:len(query.data)]
    user = query.from_user
    post = Database.db.demo_posts.find_one({"post_id": query.message.message_id})
    update_vote = Database.update_demo_vote
    insert_vote = Database.insert_demo_voter
    markup = Helpers.markup_demo_creator
    return real_vote(query, todo, user, post, update_vote, insert_vote, markup, job_queue)


def real_vote(query, todo, user, post, update_vote, insert_voter, markup, job):
    for voter in post["voters"]:
        if voter["id"] == user.id:
            if todo == "no":
                if voter["voted"] == -1:
                    update_vote(query.message.message_id, user.id, 0)
                    if job.jobs():
                        query.answer("You took your vote back.\n" +
                                     Helpers.query_answer_demo_creator(query.message.message_id), show_alert=True)
                    else:
                        query.answer("You took your vote back. Posts will be updated soon")
                        job.run_once(update_reply_markup, 5, context=[query.message, markup])
                    return
                else:
                    update_vote(query.message.message_id, user.id, -1)
                    if job.jobs():
                        query.answer("You voted against it.\n" +
                                     Helpers.query_answer_demo_creator(query.message.message_id), show_alert=True)
                    else:
                        query.answer("You voted against it. Posts will be updated soon")
                        job.run_once(update_reply_markup, 5, context=[query.message, markup])
                    return
            else:
                if voter["voted"] == 1:
                    update_vote(query.message.message_id, user.id, 0)
                    if job.jobs():
                        query.answer("You took your vote back.\n" +
                                     Helpers.query_answer_demo_creator(query.message.message_id), show_alert=True)
                    else:
                        query.answer("You took your vote back. Posts will be updated soon")
                        job.run_once(update_reply_markup, 5, context=[query.message, markup])
                    return
                else:
                    update_vote(query.message.message_id, user.id, 1)
                    if job.jobs():
                        query.answer("You voted in favour of it.\n" +
                                     Helpers.query_answer_demo_creator(query.message.message_id), show_alert=True)
                    else:
                        query.answer("You voted in favour of it. Posts will be updated soon")
                        job.run_once(update_reply_markup, 5, context=[query.message, markup])
                    return
    if todo == "no":
        insert_voter(query.message.message_id, vars(Voter(user.id, user.mention_html(), user.language_code, -1)))
        if job.jobs():
            pass
        else:
            job.run_once(update_reply_markup, 5, context=[query.message, markup])
        query.answer("You voted against it. Posts will be updated soon")
        query.message.edit_reply_markup(reply_markup=markup(query.message.message_id))
    else:
        insert_voter(query.message.message_id, vars(Voter(user.id, user.mention_html(), user.language_code, 1)))
        if job.jobs():
            pass
        else:
            job.run_once(update_reply_markup, 5, context=[query.message, markup])
        query.answer("You voted in favour of it. Posts will be updated soon")
        query.message.edit_reply_markup(reply_markup=markup(query.message.message_id))


def update_reply_markup(bot, job):
    try:
        job.context[0].edit_reply_markup(reply_markup=job.context[1](job.context[0].message_id))
    except BadRequest:
        pass


def inlinequery(_, update):
    query = update.inline_query.query
    results = []
    amount = 0
    for index, words in enumerate(database["keywords"]):
        for word in words:
            payload = re.search(query, word, re.IGNORECASE)
            if payload:
                results.append(InlineQueryResultArticle(
                    id=uuid4(),
                    title=database["links"][index][0],
                    input_message_content=Helpers.text_creator(index),
                    description=database["links"][index][1]
                ))
                amount += 1
                if amount == 5:
                    update.inline_query.answer(results)
                    break
                else:
                    pass
            else:
                pass
    if amount <= 4:
        update.inline_query.answer(results)


def demoinlinequery(_, update):
    query = update.inline_query.query
    results = []
    amount = 0
    query = query[4:len(query)]
    for index, words in enumerate(database["keywords_demo"]):
        for word in words:
            payload = re.search(query, word, re.IGNORECASE)
            if payload:
                results.append(InlineQueryResultArticle(
                    id=uuid4(),
                    title=database["links_demo"][index][0],
                    input_message_content=Helpers.text_creator_demo(index),
                    description=database["links_demo"][index][1]
                ))
                amount += 1
                if amount == 5:
                    update.inline_query.answer(results)
                    break
                else:
                    break
            else:
                pass
    if amount <= 4:
        update.inline_query.answer(results)


def main():
    updater = Updater(token=tokenbase["BOTTOKEN"])
    dp = updater.dispatcher
    dp.add_handler(CallbackQueryHandler(vote, pattern="vote", pass_job_queue=True))
    dp.add_handler(CallbackQueryHandler(demovote, pattern="demo", pass_job_queue=True))
    dp.add_handler(InlineQueryHandler(demoinlinequery, pattern="demo"))
    dp.add_handler(InlineQueryHandler(inlinequery))
    conv_add_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start_admin,
                                     filters=Filters.user(tokenbase["ADMINS"]) & Filters.private)],
        states={
            POSITION: [MessageHandler(Filters.text, add_position, pass_user_data=True)],
            DEVICES: [CallbackQueryHandler(user_device, pattern="user_devices", pass_user_data=True),
                      CommandHandler('finish', finish_devices, pass_user_data=True)]
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )
    dp.add_handler(conv_add_handler)
    conv_add_handler = ConversationHandler(
        entry_points=[CommandHandler("add", add_db, filters=Filters.user(tokenbase["ADMINS"]))],
        states={
            WHAT: [CallbackQueryHandler(add_what, pattern="what", pass_user_data=True)],
            TITLE: [MessageHandler(Filters.text, add_title, pass_user_data=True)],
            DESCRIPTION: [MessageHandler(Filters.text, add_description, pass_user_data=True)],
            DEVICE: [CallbackQueryHandler(add_device, pattern="device", pass_user_data=True)],
            NEW_GIF: [MessageHandler(Filters.document, add_raw_gif, pass_user_data=True)],
            WHAT_DEVICE: [CallbackQueryHandler(what_device, pattern="what_device", pass_user_data=True)],
            EXISTING_GIF: [CallbackQueryHandler(what_gif, pattern="gif", pass_user_data=True)],
            NEW_EXISTING_GIF: [MessageHandler(Filters.document, new_existing_gif, pass_user_data=True)],
            ANOTHER_EXISTING_GIF: [CallbackQueryHandler(another_gif, pattern="another", pass_user_data=True),
                                   CommandHandler("finish", finish_adding)],
            DEVICES_ADD: [CallbackQueryHandler(add_user_device, pattern="user_devices", pass_user_data=True),
                          CommandHandler('finish', add_finish_devices, pass_user_data=True)]
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )
    dp.add_handler(conv_add_handler)
    conv_add_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(edit_what, pattern="editing", pass_user_data=True),
                      CommandHandler("edited", edit_instantly, filters=Filters.user(tokenbase["ADMINS"]),
                                     pass_user_data=True)
                      ],
        states={
            EDITED: [MessageHandler(Filters.animation, add_edited, pass_user_data=True)],
            EDIT_TITLE: [MessageHandler(Filters.text, edit_add_title, pass_user_data=True)],
            EDIT_DESCRIPTION: [MessageHandler(Filters.text, edit_add_description, pass_user_data=True)],
            EDIT_NEW_DEVICE: [CallbackQueryHandler(edit_user_device, pattern="user_devices", pass_user_data=True),
                              CommandHandler('finish', edit_finish_devices, pass_user_data=True)],
            EDIT_DEVICE: [CallbackQueryHandler(edit_add_device, pattern="edit_device", pass_user_data=True)],
            EDITED_NEW: [MessageHandler(Filters.animation, add_edited_directly, pass_user_data=True)]
        },
        fallbacks=[CommandHandler('cancel', cancel_editing, pass_user_data=True)],
    )
    dp.add_handler(conv_add_handler)
    conv_add_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(manage_what, pattern="managing", pass_user_data=True)],
        states={
            POST_TITEL: [MessageHandler(Filters.text, new_title, pass_user_data=True),
                         CallbackQueryHandler(skip_title, pattern="yes_title", pass_user_data=True)],
            POST_DESCRIPTION: [MessageHandler(Filters.text, new_description, pass_user_data=True),
                               CallbackQueryHandler(skip_description, pattern="yes_description", pass_user_data=True)],
            POST_LINK: [MessageHandler(Filters.text, add_link, pass_user_data=True)],
            KEYWORDS: [MessageHandler(Filters.text, add_keyword, pass_user_data=True),
                       CommandHandler('finish', finish_keywords, pass_user_data=True)]
        },
        fallbacks=[CommandHandler('cancel', cancel_managing, pass_user_data=True)],
    )
    dp.add_handler(conv_add_handler)
    updater.bot.send_message(-1001214567646, "Not Linus bot online", disable_notification=True)
    updater.start_polling()


if __name__ == '__main__':
    main()
