from database import database
from telegram import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove
from objects.user import User
from constants import DEVICES, EDITED_CHANNEL_LINK, RECORDED_CHANNEL_LINK
from utils import build_menu, log_action
# states
POSITION, DEVICE = range(2)


def start(update, _):
    user_id = update.effective_user.id
    if database.is_user_in_database(user_id):
        button = [["Video recording"], ["Video editing"], ["Channel managing"], ["Video recording + editing"],
                  ["Video recording + Channel managing"], ["Video editing + Channel managing"], ["GIVE ME ALL OF IT!"]]
        update.message.reply_text("Hey. Great that you want to contribute to this project. Please choose what you want "
                                  "to do. If you want to restart, use /cancel",
                                  reply_markup=ReplyKeyboardMarkup(button, one_time_keyboard=True,
                                                                   resize_keyboard=True))
        return POSITION


def position(update, context):
    text = update.message.text
    user_id = update.effective_user.id
    user_data = context.user_data
    devices = True
    string_links = ""
    if text == "Video recording":
        positions = ["recording"]
    elif text == "Video editing":
        positions = ["editing"]
        string_links = RECORDED_CHANNEL_LINK
        devices = False
    elif text == "Channel managing":
        positions = ["managing"]
        string_links = EDITED_CHANNEL_LINK
        devices = False
    elif text == "Video recording + editing":
        positions = ["recording", "editing"]
        string_links = RECORDED_CHANNEL_LINK
    elif text == "Video recording + Channel managing":
        positions = ["managing", "recording"]
        string_links = EDITED_CHANNEL_LINK
    elif text == "Video editing + Channel managing":
        positions = ["managing", "editing"]
        string_links = EDITED_CHANNEL_LINK + "\n\n" + RECORDED_CHANNEL_LINK
        devices = False
    elif text == "GIVE ME ALL OF IT!":
        positions = ["managing", "editing", "recording"]
        string_links = EDITED_CHANNEL_LINK + "\n\n" + RECORDED_CHANNEL_LINK
    else:
        update.message.reply_text("Choose one of the buttons... Idiot....")
        return POSITION
    database.insert_user(User(user_id, positions))
    log_action(context, update.effective_user.first_name, user_id, new_position=positions)
    base_string = "Great. Please join these channels"
    if devices:
        user_data["devices"] = {}
        temp = []
        for cool_device in DEVICES.keys():
            temp.append(InlineKeyboardButton(cool_device, callback_data="user_devices" + cool_device))
        final_string = base_string + " and then tell me which devices you want to record for.\n\n" + string_links
        update.message.reply_text(final_string, reply_markup=ReplyKeyboardRemove())
        reply_markup = InlineKeyboardMarkup(build_menu(temp, 2))
        update.message.reply_text("Your first device please:", reply_markup=reply_markup, disable_web_page_preview=True)
        return DEVICE
    else:
        final_string = base_string + "\n\n" + string_links
        update.message.reply_text(final_string,
                                  reply_markup=ReplyKeyboardRemove())
        # end conversation
        return -1


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
        build_menu(temp, 2, footer_buttons=[InlineKeyboardButton("Finish!", callback_data="finish")]))
    query.edit_message_text(f"Want to add another one? Cool. Else, press the finish button."
                            f"\n\nDevices picked: {current_devices}",
                            reply_markup=reply_markup)
    return DEVICE


def finish(update, context):
    query = update.callback_query
    user_data = context.user_data
    user_id = update.effective_user.id
    database.insert_user_device(user_id, user_data["devices"])
    query.edit_message_text("Cool. Got your devices. Want to add a GIF right now? Send /add.")
    # end conversation
    return -1


def cancel(update, _):
    update.message.reply_text("Adding you to the project aborted. Run it again with /start",
                              reply_markup=ReplyKeyboardRemove())
    # end conversation
    return -1
