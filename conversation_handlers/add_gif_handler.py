from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from database import database
import utils
from objects.gif import Gif
from constants import RECORDED_CHANNEL_ID, DEVICES
from job_handlers.bump_timer import bump_recorded
# states
GIF_DEVICE, NEW_GIF, DEVICE = range(3)


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
    query.edit_message_text("Great. Send your recorded GIF in the highest quality now, as a file please :)")
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
    update.message.reply_text("Nice, ty. Editors have been notified.")
    file_id = update.message.document.file_id
    gif_id = database.insert_gif(Gif(file_id, user_data["device"], update.effective_user.id))
    message = context.bot.send_document(RECORDED_CHANNEL_ID, file_id)
    message_id = message.message_id
    button = [[InlineKeyboardButton("I want to edit",
                                    url=f"https://telegram.me/gifsupportbot?start=edit_{gif_id}_{message_id}")]]
    context.bot.edit_message_reply_markup(RECORDED_CHANNEL_ID, message_id, reply_markup=InlineKeyboardMarkup(button))
    context.job_queue.run_repeating(bump_recorded, 2 * 60 * 60, name=gif_id, context=message_id)
    utils.log_action(context, update.effective_user.first_name, update.effective_user.id, recorded_gif_id=gif_id,
                     file_id=file_id)
    # end conversation
    return -1


def cancel(update, _):
    update.message.reply_text("Cancelled the addition. Stupid human.")
    # end conversation
    return -1
