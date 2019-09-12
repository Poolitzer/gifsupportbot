from telegram import InlineKeyboardMarkup, InlineKeyboardButton, ParseMode, ChatAction
from telegram.error import BadRequest
from telegram.utils.helpers import mention_html
from constants import RECORDED_CHANNEL_ID, EDITED_CHANNEL_ID, BUMP_SECONDS, DELETEBUMPS, DELETEGIF
from job_handlers.bump_timer import bump_recorded, bump_edited
from utils import log_action
from database import database
STATUS, EDITED, NOTE = range(3)


# initial handler, not really in the conversation but who needs that anyway
def edit_what(update, context):
    data = context.args[0].split("_")
    user_id = update.effective_user.id
    if database.is_user_position(user_id, "editing"):
        pass
    else:
        return
    context.bot.send_chat_action(update.effective_chat.id, ChatAction.TYPING)
    gif_id = data[1]
    message_id = data[2]
    gif = database.get_gif(gif_id)
    context.user_data.update({"gif_id": gif_id, "message_id": message_id, "file_id": gif["recorded_gif_id"],
                              "device": gif["device"], "category": gif["category"], "title": gif["title"],
                              "recorder": gif["workers"]["recorder"]})
    context.bot.edit_message_caption(RECORDED_CHANNEL_ID, message_id,
                                     caption=f"Currently worked on by {update.effective_user.first_name}")
    edited_id = database.get_gif_edited_gif_id(gif_id)
    if edited_id:
        caption = "You got a GIF which was rejected by a manager. In order to make your work easier, " \
                  "you can use the edited GIF as well. Like, if you want. Pff."
        context.bot.send_document(user_id, edited_id, caption=caption)
    buttons = [[InlineKeyboardButton("Yes", callback_data="record_yes"),
                InlineKeyboardButton("No", callback_data="record_no")]]
    caption = "Is this GIF good?\n\nP.S.: If the initial GIF didn't follow the guidelines, it" \
              " may appear again in the recorded GIFs channel."
    context.bot.send_document(user_id, gif["recorded_gif_id"], caption=caption,
                              reply_markup=InlineKeyboardMarkup(buttons))
    payload = {"message_id": message_id, "gif_id": gif_id}
    name = "edited" + str(user_id)
    context.job_queue.run_once(two_hours_timer, 2 * 60 * 60, name=name, context=payload)
    for job in context.job_queue.get_jobs_by_name(gif_id):
        job.schedule_removal()


# real conversation starts here
# gif is good
def proceed(update, context):
    query = update.callback_query
    user_data = context.user_data
    text = "Have fun then. You have like what... 2 hours? Or so? Hurry up! And send me the edited recording as a GIF " \
           f"and not .mp4 or other formats or I will just ignore you.\nBtw, the used device is {user_data['device']}," \
           f" the category {user_data['category']} and the subcategory {user_data['title']}\n\nIf you don't want to " \
           f"edit and give the GIF back without the two hours wait time, send me /cancel."
    query.edit_message_caption(text)
    return EDITED


def add_edited(update, context):
    file_id = update.message.document.file_id
    user_id = update.effective_user.id
    gif_id = context.user_data["gif_id"]
    database.insert_edited_gif(gif_id, user_id, file_id)
    update.message.reply_text("Great, thank you. I notified the manager.\n\nP.S.: If the initial GIF didn't follow the "
                              "guidelines, it may appear again in the recorded GIFs channel")
    name = "edited" + str(user_id)
    for job in context.job_queue.get_jobs_by_name(name):
        job.schedule_removal()
    message = context.bot.send_document(EDITED_CHANNEL_ID, file_id)
    message_id = message.message_id
    button = [[InlineKeyboardButton("I want to manage!",
                                    url=f"https://telegram.me/gifsupportbot?start=manage_{gif_id}_{message_id}")]]
    context.bot.edit_message_reply_markup(EDITED_CHANNEL_ID, message_id, reply_markup=InlineKeyboardMarkup(button))
    context.job_queue.run_repeating(bump_edited, BUMP_SECONDS, name=gif_id, context=message_id)
    for message_id in database.get_gif_recorded_bumps(gif_id):
        try:
            context.bot.delete_message(RECORDED_CHANNEL_ID, message_id)
        except BadRequest:
            context.bot.send_message(RECORDED_CHANNEL_ID, DELETEBUMPS, reply_to_message_id=message_id)
            break
    context.bot.edit_message_caption(RECORDED_CHANNEL_ID, context.user_data["message_id"],
                                     caption="Done by " + update.effective_user.first_name)
    log_action(context, update.effective_user.first_name, user_id, edited_gif_id=gif_id, file_id=file_id)
    # end conversation
    return -1


# gif is bad
def abort(update, _):
    query = update.callback_query
    query.edit_message_caption("Oh, ok. Please send me a note so I can message the recorder.")
    return NOTE


def notify_recorder(update, context):
    note = update.message.text
    user_id = update.effective_user.id
    user_name = update.effective_user.first_name
    gif_id = context.user_data["gif_id"]
    message_id = context.user_data["message_id"]
    file_id = context.user_data["file_id"]
    recoder = context.user_data["recorder"]
    update.message.reply_text("Thank you, I notified the recorder")
    name = "edited" + str(user_id)
    for job in context.job_queue.get_jobs_by_name(name):
        job.schedule_removal()
    try:
        context.bot.delete_message(RECORDED_CHANNEL_ID, message_id)
    except BadRequest:
        context.bot.send_message(RECORDED_CHANNEL_ID, DELETEGIF, reply_to_message_id=message_id)
    for message_id in database.get_gif_recorded_bumps(gif_id):
        try:
            context.bot.delete_message(RECORDED_CHANNEL_ID, message_id)
        except BadRequest:
            context.bot.send_message(RECORDED_CHANNEL_ID, DELETEBUMPS, reply_to_message_id=message_id)
    ps = "\n\nP.S: Discuss this issue with " + mention_html(user_id, user_name) + " if needed. Either in the " \
                                                                                  "group or private."
    note += ps
    if len(note) > 1024:
        context.bot.send_document(chat_id=int(recoder), document=file_id)
        context.bot.send_message(chat_id=int(recoder), text=note, parse_mode=ParseMode.HTML)
    else:
        context.bot.send_document(chat_id=int(recoder), document=file_id, caption=note, parse_mode=ParseMode.HTML)
    database.delete_gif(gif_id)
    # end conversation
    return -1


# timer runs out
def two_hours_timer(context):
    context.bot.send_message(int(context.job.name[6:]), "Sorry, you took too long :(")
    data = context.job.context
    button = [[InlineKeyboardButton("I want to edit", url=f"https://telegram.me/gifsupportbot?start=edit_"
                                                          f"{data['gif_id']}_{data['message_id']}")]]
    context.bot.edit_message_caption(RECORDED_CHANNEL_ID, data["message_id"], caption="",
                                     reply_markup=InlineKeyboardMarkup(button))
    context.job_queue.run_repeating(bump_recorded, BUMP_SECONDS, name=data["gif_id"], context=data["message_id"])


def cancel(update, context):
    data = context.user_data
    user_id = update.effective_user.id
    button = [[InlineKeyboardButton("I want to edit", url=f"https://telegram.me/gifsupportbot?start=edit_"
                                                          f"{data['gif_id']}_{data['message_id']}")]]
    context.bot.edit_message_caption(RECORDED_CHANNEL_ID, data["message_id"], caption="",
                                     reply_markup=InlineKeyboardMarkup(button))
    context.job_queue.run_repeating(bump_recorded, BUMP_SECONDS, name=data["gif_id"], context=data["message_id"])
    name = "edited" + str(user_id)
    for job in context.job_queue.get_jobs_by_name(name):
        job.schedule_removal()
    update.message.reply_text("Cancelled!")
    # end conversation
    return -1
