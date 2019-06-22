from telegram import (KeyboardButton, ReplyKeyboardMarkup, ParseMode, ReplyKeyboardRemove, InlineKeyboardMarkup,
                      InlineKeyboardButton, InputMediaAnimation)
from constants import CATEGORIES, POST_CHANNEL_ID, ARTICLE_URL, POST_CHANNEL_LINK
import utils
from telegraph_handler import telegraph
from database import database
from telegram import ChatAction

CATEGORY, SUBCATEGORY, WHAT, UPDATE_TITLE, UPDATE_DESCRIPTION, UPDATE_LINK, KEYWORD, DEVICE, GIF = range(9)


def start(update, _):
    user_id = update.effective_user.id
    if database.is_user_position(user_id, "managing"):
        buttons = []
        for category in CATEGORIES:
            buttons.append(KeyboardButton(category))
        update.effective_message.reply_text("So you want to edit a subcategory? Well, lets start with the category.",
                                            reply_markup=ReplyKeyboardMarkup(utils.build_menu(buttons, 3)))
        return CATEGORY


def subcategory(update, context):
    category = update.message.text
    context.user_data["category"] = category
    titles = database.get_subcategories_title(category)
    buttons = []
    if titles:
        for title in titles:
            buttons.append(KeyboardButton(title))
        update.effective_message.reply_text("Great, now choose your subcategory",
                                            reply_markup=ReplyKeyboardMarkup(utils.build_menu(buttons, 3)))
        return SUBCATEGORY
    else:
        update.effective_message.reply_text("Sorry, you choose a category where there aren't any subcategories yet. "
                                            "Please select another one or hit /cancel")
        return CATEGORY


def what(update, context):
    title = update.message.text
    user_data = context.user_data
    user_data["title"] = title
    sub = database.get_subcategory(user_data["category"], title)
    user_data["sub_id"] = sub["_id"]
    buttons = [KeyboardButton("Title"), KeyboardButton("Description"), KeyboardButton("Help Link"),
               KeyboardButton("Keywords"), KeyboardButton("GIF")]
    if not sub['help_link']:
        sub['help_link'] = "None"
    # maybe we have to do more later if issues with the URL (id, anchor) appear
    body = f"What do you want to update?\n\nCurrent status:\n<i>Title</i>: {sub['title']}\n<i>Description</i>: " \
        f"{sub['description']}\n<i>Help Link</i>: {sub['help_link']}\n" \
        f"<i>Keywords</i>: {', '.join(sub['keywords'])}\n\n" \
        f"<a href=\"{ARTICLE_URL + '#' + title.replace(' ', '-')}\">Link to all the GIFs for this subcategory</a>"
    update.message.reply_html(body, reply_markup=ReplyKeyboardMarkup(utils.build_menu(buttons, 2),
                                                                     one_time_keyboard=True))
    return WHAT


# Title
def update_title(update, _):
    update.message.reply_text("Great. Tell me the new title please. And it still has to be unique,"
                              "no escape from that.", reply_markup=ReplyKeyboardRemove())
    return UPDATE_TITLE


def returned_title(update, context):
    title = update.message.text
    user_data = context.user_data
    if database.is_title_unique(user_data["category"], title):
        update.message.reply_text("This title is already used, please select another one or hit /cancel.")
        return UPDATE_TITLE
    else:
        to_edit = database.update_subcategory_title(user_data["category"], user_data["title"], title)
        telegraph.update_page()
        for message in to_edit:
            context.bot.send_chat_action(update.effective_chat.id, ChatAction.TYPING)
            caption = utils.create_caption(title, message["device"], message["help_link"])
            context.bot.edit_message_caption(POST_CHANNEL_ID, message["message_id"], caption=caption,
                                             parse_mode=ParseMode.HTML)
        update.message.reply_text("Updated Title!")
        database.insert_subcategory_worker(user_data["category"], title, update.effective_user.id)
        utils.log_action(context, update.effective_user.first_name, update.effective_user.id,
                         category=user_data["category"], subcategory_id=user_data["sub_id"],
                         titles={"old_title": user_data["title"], "new_title": title})
        # end conversation
        return -1


# Description
def update_description(update, _):
    update.message.reply_text("Great. Tell me the new description please :)", reply_markup=ReplyKeyboardRemove())
    return UPDATE_DESCRIPTION


def returned_description(update, context):
    description = update.message.text
    user_data = context.user_data
    old_description = database.update_subcategory_description(user_data["category"], user_data["title"], description)
    update.message.reply_text("Updated Description!")
    database.insert_subcategory_worker(user_data["category"], user_data["title"], update.effective_user.id)
    utils.log_action(context, update.effective_user.first_name, update.effective_user.id,
                     category=user_data["category"], subcategory_id=user_data["sub_id"],
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
    returned = database.update_subcategory_link(user_data["category"], user_data["title"], new_link)
    if returned["help_link"] != new_link:
        for message in returned["messages"]:
            context.bot.send_chat_action(update.effective_chat.id, ChatAction.TYPING)
            caption = utils.create_caption(user_data["title"], message["device"], new_link)
            context.bot.edit_message_caption(POST_CHANNEL_ID, message["message_id"], caption=caption,
                                             parse_mode=ParseMode.HTML, timeout=100)
    update.message.reply_text("Updated the help link!")
    database.insert_subcategory_worker(user_data["category"], user_data["title"], update.effective_user.id)
    utils.log_action(context, update.effective_user.first_name, update.effective_user.id,
                     category=user_data["category"], subcategory_id=user_data["sub_id"],
                     links={"old_link": returned["help_link"], "new_link": new_link})
    # end conversation
    return -1


def returned_link_none(update, context):
    user_data = context.user_data
    returned = database.update_subcategory_link(user_data["category"], user_data["title"], "")
    if returned["help_link"] != "":
        for message in returned["messages"]:
            context.bot.send_chat_action(update.effective_chat.id, ChatAction.TYPING)
            caption = utils.create_caption(user_data["title"], message["device"])
            context.bot.edit_message_caption(POST_CHANNEL_ID, message["message_id"], caption=caption,
                                             parse_mode=ParseMode.HTML)
    update.message.reply_text("Updated the help link!")
    database.insert_subcategory_worker(user_data["category"], user_data["title"], update.effective_user.id)
    utils.log_action(context, update.effective_user.first_name, update.effective_user.id,
                     category=user_data["category"], subcategory_id=user_data["sub_id"],
                     links={"old_link": returned["help_link"], "new_link": "None"})
    # end conversation
    return -1


# keywords
def update_keywords(update, context):
    user_data = context.user_data
    keywords = database.get_subcategory_keywords(user_data["category"], user_data["title"])
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
    database.delete_subcategory_keyword(user_data["category"], user_data["title"], keyword)
    update.effective_message.reply_text("Keyword successfully deleted!", reply_markup=ReplyKeyboardRemove())
    database.insert_subcategory_worker(user_data["category"], user_data["title"], update.effective_user.id)
    utils.log_action(context, update.effective_user.first_name, update.effective_user.id,
                     category=user_data["category"], subcategory_id=user_data["sub_id"], deleted_keyword=keyword)
    # end conversation
    return -1


def new_keyword(update, context):
    user_data = context.user_data
    keyword = update.message.text
    database.insert_subcategory_keyword(user_data["category"], user_data["title"], keyword)
    update.message.reply_text("Keyword successfully added!", reply_markup=ReplyKeyboardRemove())
    database.insert_subcategory_worker(user_data["category"], user_data["title"], update.effective_user.id)
    utils.log_action(context, update.effective_user.first_name, update.effective_user.id,
                     category=user_data["category"], subcategory_id=user_data["sub_id"], new_keyword=keyword)
    # end conversation
    return -1


# change gif
def update_gif(update, context):
    user_data = context.user_data
    devices = database.get_subcategory_devices(user_data["category"], user_data["title"])
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
    stuff = database.update_subcategory_gif(user_data["category"], user_data["title"], user_data["device"]["name"],
                                            user_data["device"]["file_id"], new_file_id)
    caption = utils.create_caption(user_data["title"], user_data["device"]["name"], stuff["help_link"])
    context.bot.edit_message_media(chat_id=POST_CHANNEL_ID, message_id=user_data["device"]["message_id"],
                                   media=InputMediaAnimation(media=new_file_id, caption=caption))
    telegraph.update_page()
    update.message.reply_text("Edited GIF!", reply_markup=ReplyKeyboardRemove())
    database.insert_subcategory_worker(user_data["category"], user_data["title"], update.effective_user.id)
    utils.log_action(context, update.effective_user.first_name, update.effective_user.id, file_id=new_file_id,
                     category=user_data["category"], subcategory_id=stuff["sub_id"], edit_sub_gif=stuff["gif_id"])
    # end conversation
    return -1


def cancel(update, _):
    update.message.reply_text("Cancelled!", reply_markup=ReplyKeyboardRemove())
    # end conversation
    return -1
