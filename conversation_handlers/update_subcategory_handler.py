from telegram import (KeyboardButton, ReplyKeyboardMarkup, ParseMode, ReplyKeyboardRemove, InlineKeyboardMarkup,
                      InlineKeyboardButton, InputMediaAnimation)
from constants import POST_CHANNEL_ID, ARTICLE_URL, POST_CHANNEL_LINK
import utils
from telegraph_handler import telegraph
from database import database
from telegram import ChatAction

CATEGORY, SUBCATEGORY, WHAT, UPDATE_TITLE, UPDATE_DESCRIPTION, UPDATE_LINK, KEYWORD, DEVICE, GIF = range(9)


def start(update, context):
    user_id = update.effective_user.id
    if database.is_user_position(user_id, "managing"):
        buttons = []
        for category in database.get_categories():
            buttons.append(KeyboardButton(category))
        update.effective_message.reply_text("So you want to edit a subcategory? Well, pick your poison.",
                                            reply_markup=ReplyKeyboardMarkup(utils.build_menu(buttons, 3)))
        context.user_data["category_list"] = []
        return CATEGORY


def subcategory(update, context):
    user_data = context.user_data
    category = update.effective_message.text
    user_data["category_list"].append(category)
    next_category = database.get_next_category(user_data["category_list"])
    if next_category:
        buttons = []
        for category in next_category:
            buttons.append(KeyboardButton(category))
        update.effective_message.reply_text("Alright. Select the next category pls",
                                            reply_markup=ReplyKeyboardMarkup(utils.build_menu(buttons, 3)))
    else:
        category_path = ".".join(user_data["category_list"])
        if database.is_gif_in_categories(category_path):
            sub = database.get_subcategory(category_path)
            user_data.update({"sub_id": sub["_id"], "category_path": category_path})
            buttons = [KeyboardButton("Description"), KeyboardButton("Help Link"),
                       KeyboardButton("Keywords"), KeyboardButton("GIF")]
            if not sub['help_link']:
                sub['help_link'] = "None"
            # maybe we have to do more later if issues with the URL (id, anchor) appear
            # title is an old term but usable here
            title = user_data["category_list"][-1]
            body = f"What do you want to update?\n\nCurrent status:\n<i>Title</i>: {title}\n" \
                   f"<i>Description</i>: {sub['description']}\n<i>Help Link</i>: {sub['help_link']}\n" \
                   f"<i>Keywords</i>: {', '.join(sub['keywords'])}\n\n" \
                   f"<a href=\"{ARTICLE_URL + '#' + title.replace(' ', '-')}\">Link to all the GIFs for this " \
                   f"subcategory</a>. In case you want to change the \"title\", change the categories."
            update.message.reply_html(body, reply_markup=ReplyKeyboardMarkup(utils.build_menu(buttons, 2),
                                                                             one_time_keyboard=True))
            del user_data["category_list"]
            return WHAT
        else:
            buttons = []
            for category in database.get_categories():
                buttons.append(KeyboardButton(category))
            message = "Sorry, there is no category created yet with that title. Either select another " \
                      "category or hit /cancel."
            update.effective_message.reply_text(message, reply_markup=ReplyKeyboardMarkup(utils.build_menu(buttons, 3)))
            user_data["category_list"] = []
    return CATEGORY


# Description
def update_description(update, _):
    update.message.reply_text("Great. Tell me the new description please :)", reply_markup=ReplyKeyboardRemove())
    return UPDATE_DESCRIPTION


def returned_description(update, context):
    description = update.message.text
    user_data = context.user_data
    old_description = database.update_subcategory_description(user_data["category_path"], description)
    update.message.reply_text("Updated Description!")
    database.insert_subcategory_worker(user_data["category_path"], update.effective_user.id)
    utils.log_action(context, update.effective_user.first_name, update.effective_user.id,
                     category_path=user_data["category_path"], subcategory_id=user_data["sub_id"],
                     description={"old_description": old_description, "new_description": description})
    # end conversation
    return -1


# Help Link
def update_link(update, _):
    update.message.reply_text("Great. Send me the new link. If you want to delete it, send /none.",
                              reply_markup=ReplyKeyboardRemove())
    return UPDATE_LINK


def returned_link(update, context):
    entity = update.message.entities[0]
    user_data = context.user_data
    if entity.type == "text_link":
        new_link = entity.url
    elif entity.type == "url":
        new_link = update.message.parse_entity(entity)
    else:
        update.message.reply_text("Hey man, your first markup must be a link, not bold formatting or other weird shit."
                                  " Try again or just press /none jesus christ.")
        return UPDATE_LINK
    if not new_link.startswith("http://"):
        if not new_link.startswith("https://"):
            new_link = "http://" + new_link
    returned = database.update_subcategory_link(user_data["category_path"], new_link)
    if returned["help_link"] != new_link:
        for message in returned["messages"]:
            context.bot.send_chat_action(update.effective_chat.id, ChatAction.TYPING)
            caption = utils.create_caption(user_data["title"], message["device"], new_link)
            context.bot.edit_message_caption(POST_CHANNEL_ID, message["message_id"], caption=caption,
                                             parse_mode=ParseMode.HTML, timeout=100)
    update.message.reply_text("Updated the help link!")
    database.insert_subcategory_worker(user_data["category_path"], update.effective_user.id)
    utils.log_action(context, update.effective_user.first_name, update.effective_user.id,
                     category_path=user_data["category_path"], subcategory_id=user_data["sub_id"],
                     links={"old_link": returned["help_link"], "new_link": new_link})
    # end conversation
    return -1


def returned_link_none(update, context):
    user_data = context.user_data
    returned = database.update_subcategory_link(user_data["category_path"], "")
    if returned["help_link"] != "":
        for message in returned["messages"]:
            context.bot.send_chat_action(update.effective_chat.id, ChatAction.TYPING)
            caption = utils.create_caption(user_data["title"], message["device"])
            context.bot.edit_message_caption(POST_CHANNEL_ID, message["message_id"], caption=caption,
                                             parse_mode=ParseMode.HTML)
    update.message.reply_text("Updated the help link!")
    database.insert_subcategory_worker(user_data["category_path"], update.effective_user.id)
    utils.log_action(context, update.effective_user.first_name, update.effective_user.id,
                     category_path=user_data["category_path"], subcategory_id=user_data["sub_id"],
                     links={"old_link": returned["help_link"], "new_link": "None"})
    # end conversation
    return -1


# keywords
def update_keywords(update, context):
    user_data = context.user_data
    keywords = database.get_subcategory_keywords(user_data["category_path"])
    user_data["keywords"] = keywords
    buttons = []
    for index, keyword in enumerate(keywords):
        buttons.append(InlineKeyboardButton(keyword, callback_data="keyword" + str(index)))
    update.message.reply_text("Select a keyword you want to delete or send a new one.",
                              reply_markup=InlineKeyboardMarkup(
                                  utils.build_menu(buttons, 2)))
    return KEYWORD


def returned_keyword(update, context):
    user_data = context.user_data
    query = update.callback_query
    data = query.data[7:]
    keyword = user_data["keywords"][int(data)]
    query.answer()
    database.delete_subcategory_keyword(user_data["category_path"], keyword)
    update.effective_message.reply_text("Keyword successfully deleted!", reply_markup=ReplyKeyboardRemove())
    database.insert_subcategory_worker(user_data["category_path"], update.effective_user.id)
    utils.log_action(context, update.effective_user.first_name, update.effective_user.id,
                     category_path=user_data["category_path"], subcategory_id=user_data["sub_id"],
                     deleted_keyword=keyword)
    # end conversation
    return -1


def new_keyword(update, context):
    user_data = context.user_data
    keyword = update.message.text
    database.insert_subcategory_keyword(user_data["category_path"], keyword)
    update.message.reply_text("Keyword successfully added!", reply_markup=ReplyKeyboardRemove())
    database.insert_subcategory_worker(user_data["category_path"], update.effective_user.id)
    utils.log_action(context, update.effective_user.first_name, update.effective_user.id,
                     category_path=user_data["category_path"], subcategory_id=user_data["sub_id"], new_keyword=keyword)
    # end conversation
    return -1


# change gif
def update_gif(update, context):
    user_data = context.user_data
    devices = database.get_subcategory_devices(user_data["category_path"])
    user_data["devices"] = devices
    buttons = []
    links = ""
    for device in devices:
        buttons.append(InlineKeyboardButton(device, callback_data="device" + device))
        links += f"<a href=\"{POST_CHANNEL_LINK}/{devices[device]['message_id']}\">{device}</a>\n\n"
    update.message.reply_html("Select the device you want to update the GIF for. These are the channel links:\n\n"
                              + links, reply_markup=InlineKeyboardMarkup(utils.build_menu(buttons, 2)))
    return DEVICE


def returned_device(update, context):
    query = update.callback_query
    user_data = context.user_data
    device = query.data[6:]
    user_data["device"] = user_data["devices"][device]
    user_data["device"]["name"] = device
    query.edit_message_text("Great. Send me the new GIF now please.", reply_markup=ReplyKeyboardRemove())
    return GIF


def returned_gif(update, context):
    user_data = context.user_data
    new_file_id = update.message.document.file_id
    stuff = database.update_subcategory_gif(user_data["category_path"], user_data["device"]["name"],
                                            user_data["device"]["file_id"], new_file_id)
    title = user_data["category_path"].split(".")[-1]
    caption = utils.create_caption(title, user_data["device"]["name"], stuff["help_link"])
    context.bot.edit_message_media(chat_id=POST_CHANNEL_ID, message_id=user_data["device"]["message_id"],
                                   media=InputMediaAnimation(media=new_file_id, caption=caption))
    telegraph.update_page()
    update.message.reply_text("Edited GIF!", reply_markup=ReplyKeyboardRemove())
    database.insert_subcategory_worker(user_data["category_path"], update.effective_user.id)
    utils.log_action(context, update.effective_user.first_name, update.effective_user.id, file_id=new_file_id,
                     category_path=user_data["category_path"], subcategory_id=stuff["sub_id"],
                     edit_sub_gif=stuff["gif_id"])
    # end conversation
    return -1


def cancel(update, context):
    update.message.reply_text("Cancelled!", reply_markup=ReplyKeyboardRemove())
    user_data = context.user_data
    if "category_list" in user_data:
        del user_data["category_list"]
    # end conversation
    return -1
