from telegram import (InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup,
                      ReplyKeyboardRemove)
from database import database
import utils
from objects.gif import Gif
from constants import RECORDED_CHANNEL_ID, DEVICES, CATEGORIES, BUMP_SECONDS
from job_handlers.bump_timer import bump_recorded
# states
GIF_DEVICE, GET_CATEGORY, GET_TITLE, NEW_GIF, DEVICE = range(5)


def add_command(update, _):
    user_id = update.effective_user.id
    if database.is_user_position(user_id, "recording"):
        temp = []
        for actual_device in database.get_user_devices(user_id):
            temp.append(InlineKeyboardButton(actual_device, callback_data="record_device" + actual_device))
        footer = [InlineKeyboardButton("Update Devices", callback_data="update_device")]
        update.message.reply_text("You want to add a new GIF? Great. Choose one of your devices you recorded for.\n\n"
                                  "Yours is not listed? Then hit the Update Devices button",
                                  reply_markup=InlineKeyboardMarkup(utils.build_menu(temp, 2, footer_buttons=footer)))
    return GIF_DEVICE


def add_device(update, context):
    query = update.callback_query
    user_data = context.user_data
    real_device = query.data[13:]
    user_data["device"] = real_device
    buttons = []
    for category in CATEGORIES:
        buttons.append(KeyboardButton(category))
    query.answer()
    update.effective_message.reply_text("Great. Now, choose a category :)",
                                        reply_markup=ReplyKeyboardMarkup(utils.build_menu(buttons, 3)))
    return GET_CATEGORY


def add_category(update, context):
    user_data = context.user_data
    category = update.effective_message.text
    user_data["category"] = category
    real_device = user_data["device"]
    titles = database.get_subcategories_device_category(category, real_device)
    if titles:
        buttons = []
        for title in titles:
            buttons.append(KeyboardButton(title))
        update.effective_message.reply_text("Okay. Select a fitting subcategory now please.",
                                            reply_markup=ReplyKeyboardMarkup(utils.build_menu(buttons, 3)))
        return GET_TITLE
    else:
        buttons = []
        for category in CATEGORIES:
            buttons.append(KeyboardButton(category))
        message = "Sorry, no free subcategory left in this category for your device. Please contact the manager of " \
                  "your choice in the GIF support group if you think that's a mistake, otherwise select another " \
                  "category or hit /cancel"
        update.effective_message.reply_text(message, reply_markup=ReplyKeyboardMarkup(utils.build_menu(buttons, 3)))
        return GET_CATEGORY


def add_title(update, context):
    user_data = context.user_data
    title = update.effective_message.text
    user_data["title"] = title
    update.effective_message.reply_text("Alright. Now, send me the GIF please. As a .mp4 file ;)",
                                        reply_markup=ReplyKeyboardRemove())
    return NEW_GIF


def add_user_device(update, context):
    query = update.callback_query
    user_data = context.user_data
    user_data["devices"] = {}
    temp = []
    for cool_device in DEVICES.keys():
        temp.append(InlineKeyboardButton(cool_device, callback_data="user_devices" + cool_device))
    reply_markup = InlineKeyboardMarkup(utils.build_menu(temp, 2))
    query.edit_message_text("Your first device please:", reply_markup=reply_markup)
    return DEVICE


def device(update, context):
    query = update.callback_query
    user_data = context.user_data
    real_device = query.data[12:]
    user_data["devices"][real_device] = True
    known = user_data["devices"]
    temp = []
    for the_device in DEVICES.keys():
        try:
            known[the_device]
        except KeyError:
            temp.append(InlineKeyboardButton(the_device, callback_data="user_devices" + the_device))
    current_devices = ", ".join(known)
    reply_markup = InlineKeyboardMarkup(
        utils.build_menu(temp, 2, footer_buttons=[InlineKeyboardButton("Finish!", callback_data="finish")]))
    query.edit_message_text(f"Want to add another one? Cool. Else, press the finish button."
                            f"\n\nDevices picked: {current_devices}",
                            reply_markup=reply_markup)
    return DEVICE


def finish(update, context):
    query = update.callback_query
    user_data = context.user_data
    user_id = update.effective_user.id
    database.insert_user_device(user_id, user_data["devices"])
    temp = []
    for real_device in database.get_user_devices(user_id):
        temp.append(InlineKeyboardButton(real_device, callback_data="record_device" + real_device))
    footer = [InlineKeyboardButton("Update Devices (really?)", callback_data="update_device")]
    query.edit_message_text("Cool. Got your devices. Now try again selecting the device you recorded for :)",
                            reply_markup=InlineKeyboardMarkup(utils.build_menu(temp, 2, footer_buttons=footer)))
    return GIF_DEVICE


def add_gif(update, context):
    user_data = context.user_data
    if update.message.document.mime_type != "video/mp4":
        update.message.reply_text("That's not a video. Please send a video as a file or send /cancel to abort.")
        return NEW_GIF
    update.message.reply_text("Nice, ty. Editors will be notified.")
    file_id = update.message.document.file_id
    gif_id = database.insert_gif(Gif(file_id, user_data["device"], update.effective_user.id, user_data["category"],
                                     user_data["title"]))
    message = context.bot.send_document(RECORDED_CHANNEL_ID, file_id)
    message_id = message.message_id
    button = [[InlineKeyboardButton("I want to edit",
                                    url=f"https://telegram.me/gifsupportbot?start=edit_{gif_id}_{message_id}")]]
    context.bot.edit_message_reply_markup(RECORDED_CHANNEL_ID, message_id, reply_markup=InlineKeyboardMarkup(button))
    context.job_queue.run_repeating(bump_recorded, BUMP_SECONDS, name=gif_id, context=message_id)
    utils.log_action(context, update.effective_user.first_name, update.effective_user.id, recorded_gif_id=gif_id,
                     file_id=file_id)
    # end conversation
    return -1


def cancel(update, _):
    update.message.reply_text("Cancelled the addition. Stupid human.")
    # end conversation
    return -1
