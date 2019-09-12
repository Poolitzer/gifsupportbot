from telegram import (InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove, ParseMode, MessageEntity,
                      ChatAction)
from telegram.error import BadRequest
from telegram.utils.helpers import mention_html
from constants import EDITED_CHANNEL_ID, RECORDED_CHANNEL_ID, POST_CHANNEL_ID, BUMP_SECONDS, DELETEBUMPS, DELETEGIF
import utils
from job_handlers.bump_timer import bump_edited, bump_recorded
from database import database
from objects.subcategory import Subcategory
from telegraph_handler import telegraph

EDIT_FIX, NOTE_EDIT, NOTE_RECORD, NEW_DESCRIPTION, HELP_URL, KEYWORD = range(6)


# initial handler, not really in the conversation but who needs that anyway
def manage_what(update, context):
    data = context.args[0].split("_")
    user_id = update.effective_user.id
    if database.is_user_position(user_id, "managing"):
        pass
    else:
        return
    context.bot.send_chat_action(update.effective_chat.id, ChatAction.TYPING)
    gif_id = data[1]
    message_id = data[2]
    gif = database.get_gif(gif_id)
    context.user_data.update({"gif_id": gif_id, "message_id": message_id, "file_id": gif["edited_gif_id"],
                              "device": gif["device"], "category": gif["category"], "title": gif["title"],
                              "keywords": [], "help_link": "", "recorder": gif["recorded_gif_id"]})
    context.bot.edit_message_caption(EDITED_CHANNEL_ID, message_id,
                                     "Currently worked on by " + update.effective_user.first_name)
    buttons = [[InlineKeyboardButton("Yes", callback_data="is_edit_yes"),
                InlineKeyboardButton("No", callback_data="is_edit_no")]]
    caption = f"Is this GIF really good? Make sure it fits the category ({gif['category']}) and subcategory " \
              f"({gif['title']}), as well as the device ({gif['device']})"
    context.bot.send_document(user_id, gif["edited_gif_id"], caption=caption,
                              reply_markup=InlineKeyboardMarkup(buttons))
    payload = {"message_id": message_id, "gif_id": gif_id}
    name = "managed" + str(user_id)
    context.job_queue.run_once(two_hours_timer, 2 * 60 * 60, name=name, context=payload)
    for job in context.job_queue.get_jobs_by_name(gif_id):
        job.schedule_removal()


# real conversation starts here
# gif is good
def proceed(update, context):
    query = update.callback_query
    user_data = context.user_data
    if database.is_title_in_categories(user_data["category"], user_data["title"]):
        user_data["help_link"] = database.get_subcategory_help_link(user_data["category"], user_data["title"])
        user_id = update.effective_user.id
        add_gif_to_sub(context, user_id, update.effective_user.first_name)
        query.answer()
        update.effective_message.reply_text("Alright, thanks for confirming.")
        # end conversation
        return -1
    else:
        query.answer()
        update.effective_message.reply_text("LETS DO THIS. Send me a description of this subcategory")
        return NEW_DESCRIPTION


def new_description(update, context):
    description = update.message.text
    context.user_data["description"] = description
    update.message.reply_text("Nice, thanks. Now, please check if a FAQ pages exists somewhere and send me the link to "
                              "it. Otherwise, hit /skip.")
    return HELP_URL


def add_url(update, context):
    entities = update.message.parse_entities([MessageEntity.URL, MessageEntity.TEXT_LINK])
    user_data = context.user_data
    user_data["help_link"] = ""
    for entity in entities:
        if entity == MessageEntity.TEXT_LINK:
            user_data["help_link"] = entities[entity].url
        elif entities[entity].type == MessageEntity.URL:
            user_data["help_link"] = entities[entity]
        break
    if not user_data["help_link"]:
        update.message.reply_text("Hey man, your message markup must include a link. Try again or just press /skip "
                                  "jesus christ.")
        return HELP_URL
    if not user_data["help_link"].startswith("http"):
        user_data["help_link"] = "http://" + user_data["help_link"]
    update.message.reply_text("Nice. Now you need to send me keywords for this topic so people can find it when using "
                              "the inline function")
    return KEYWORD


def skip_url(update, _):
    update.message.reply_text("Nice. Now you need to send me keywords for this topic so people can find it when using "
                              "the inline function")
    return KEYWORD


def add_keyword(update, context):
    user_data = context.user_data
    new_keyword = update.message.text
    messages = ["No one will see this. Sad story. Moving on",
                "You added the keyword <b>{}</b>. If you want to add another one, send it. If you are finished, send "
                "/finish.", "Heyy. A second keyword. It's <b>{}</b>, right?",
                "A third? Well, thats cool. <b>{}</b> this time.", "A fourth? :OOO <b>{}</b>. Don't forget /finish...",
                "ANOTHER ONE? You are kidding me, right? It's <b>{}</b>, neat", "I really like <b>{}</b>.",
                "Don't push it too far though, not even with <b>{}</b>.", "Ok. Its enough. <b>{}</b>.",
                "Please. Stop. <b>{}</b>", "I'm really not creative anymore. <b>{}</b>"]
    for keyword in user_data["keywords"]:
        if keyword == new_keyword:
            update.message.reply_text("Eyo mate. You already added this keyword. Send me a unique one or hit /finish.")
            return KEYWORD
    user_data["keywords"].append(new_keyword)
    try:
        update.message.reply_html(messages[len(user_data["keywords"])].format(new_keyword))
    except IndexError:
        update.message.reply_html(messages[-1].format(update.message.text))
    return KEYWORD


def finish_keywords(update, context):
    user_data = context.user_data
    user_id = update.effective_user.id
    sub = Subcategory(user_data["title"], user_data["description"], user_data["keywords"], user_id,
                      user_data["help_link"])
    sub_id = database.insert_subcategory(user_data["category"], sub)
    user_data["sub_id"] = sub_id
    utils.log_action(context, update.effective_user.first_name, user_id, category=user_data["category"],
                     subcategory_id=sub_id, created_sub=user_data)
    add_gif_to_sub(context, user_id, update.effective_user.first_name)
    update.message.reply_text("Done, thanks!")
    # end conversation
    return -1


def add_gif_to_sub(context, user_id, first_name):
    user_data = context.user_data
    gif_id = user_data["gif_id"]
    message_id = post_to_gif_channel(context.bot, user_data["title"], user_data["device"], user_data["help_link"],
                                     user_data["file_id"])
    database.insert_device(user_data["category"], user_data["title"], user_data["device"], user_data["file_id"],
                           message_id)
    telegraph.update_page()
    name = "managed" + str(user_id)
    for job in context.job_queue.get_jobs_by_name(name):
        job.schedule_removal()
    context.bot.edit_message_caption(EDITED_CHANNEL_ID, user_data["message_id"], caption="Done by " + first_name)
    for message_id in database.get_gif_recorded_bumps(gif_id):
        try:
            context.bot.delete_message(EDITED_CHANNEL_ID, message_id)
        except BadRequest:
            context.bot.send_message(EDITED_CHANNEL_ID, DELETEBUMPS, reply_to_message_id=message_id)
            break
    database.insert_gif_manager(gif_id, user_id)
    utils.log_action(context, first_name, user_id, category=user_data["category"], subcategory_id=user_data["sub_id"],
                     file_id=user_data["file_id"], gif_to_sub=gif_id)


def post_to_gif_channel(bot, title, device, help_link, file_id):
    caption = utils.create_caption(title, device, help_link)
    message = bot.send_animation(POST_CHANNEL_ID, file_id, caption=caption, parse_mode=ParseMode.HTML)
    return message.message_id


# gif is bad
def abort(update, _):
    query = update.callback_query
    buttons = [[InlineKeyboardButton("Yes", callback_data="ed_fix_yes"),
                InlineKeyboardButton("No", callback_data="ed_fix_no")]]
    query.edit_message_caption("Oh, ok. Can the mistake be fixed in the edit process?",
                               reply_markup=InlineKeyboardMarkup(buttons))
    return EDIT_FIX


# gif can be fixed from the editor
def edit_fix(update, _):
    query = update.callback_query
    query.edit_message_caption("Oh, ok. Please send me a note so I can message the editor.")
    return NOTE_EDIT


# gif must be rerecorded
def record_fix(update, context):
    query = update.callback_query
    gif_id = context.user_data["gif_id"]
    context.user_data["user_id"] = database.get_gif_worker(gif_id, "recorder")
    query.edit_message_caption("Yeah, lets just throw the GIF away. Send me a note now so I can message the recorder.")
    return NOTE_RECORD


def notify_editor(update, context):
    note = update.message.text
    user_id = update.effective_user.id
    user_name = update.effective_user.first_name
    gif_id = context.user_data["gif_id"]
    message_id = context.user_data["message_id"]
    file_id = context.user_data["file_id"]
    update.message.reply_text("Thank you, I notified the editors")
    name = "managed" + str(user_id)
    for job in context.job_queue.get_jobs_by_name(name):
        job.schedule_removal()
    try:
        context.bot.delete_message(EDITED_CHANNEL_ID, message_id)
    except BadRequest:
        context.bot.send_message(EDITED_CHANNEL_ID, DELETEGIF, reply_to_message_id=message_id)
    for message_id in database.get_gif_edited_bumps(gif_id):
        try:
            context.bot.delete_message(EDITED_CHANNEL_ID, message_id)
        except BadRequest:
            context.bot.send_message(EDITED_CHANNEL_ID, DELETEBUMPS, reply_to_message_id=message_id)
            break
    ps = "\n\nP.S: Discuss this issue with " + mention_html(user_id, user_name) + " if needed. Either in the " \
                                                                                  "group or private."
    note += ps
    if len(note) > 1024:
        message = context.bot.send_document(chat_id=RECORDED_CHANNEL_ID, document=file_id)
        bump = context.bot.send_message(chat_id=RECORDED_CHANNEL_ID, text=note, reply_to_message_id=message.message_id,
                                        parse_mode=ParseMode.HTML)
        message_id = bump.message_id
        button = [[InlineKeyboardButton("I want to edit!", url=f"https://telegram.me/gifsupportbot?start=edit_"
                                                               f"{gif_id}_{message_id}")]]
        context.bot.edit_message_reply_markup(RECORDED_CHANNEL_ID, message_id, reply_markup=button)
        database.insert_gif_recorded_bump(gif_id, message_id)
    else:
        message = context.bot.send_document(chat_id=RECORDED_CHANNEL_ID, document=file_id, caption=note,
                                            parse_mode=ParseMode.HTML)
        message_id = message.message_id
        button = [[InlineKeyboardButton("I want to edit!", url=f"https://telegram.me/gifsupportbot?start=edit_"
                                                               f"{gif_id}_{message_id}")]]
        context.bot.edit_message_reply_markup(RECORDED_CHANNEL_ID, message_id, reply_markup=button)
    context.job_queue.run_repeating(bump_recorded, BUMP_SECONDS, name=gif_id, context=message.message_id)
    # end conversation
    return -1


def notify_recorder(update, context):
    note = update.message.text
    user_id = update.effective_user.id
    user_name = update.effective_user.first_name
    gif_id = context.user_data["gif_id"]
    message_id = context.user_data["message_id"]
    file_id = context.user_data["file_id"]
    recorder = context.user_data["recorder"]
    update.message.reply_text("Thank you, I notified the recorder")
    name = "managed" + str(user_id)
    for job in context.job_queue.get_jobs_by_name(name):
        job.schedule_removal()
    try:
        context.bot.delete_message(EDITED_CHANNEL_ID, message_id)
    except BadRequest:
        context.bot.send_message(EDITED_CHANNEL_ID, DELETEGIF, reply_to_message_id=message_id)
    for message_id in database.get_gif_edited_bumps(gif_id):
        try:
            context.bot.delete_message(EDITED_CHANNEL_ID, message_id)
        except BadRequest:
            context.bot.send_message(EDITED_CHANNEL_ID, DELETEBUMPS, reply_to_message_id=message_id)
            break
    ps = "\n\nP.S: Discuss this issue with " + mention_html(user_id, user_name) + " if needed. Either in the " \
                                                                                  "group or private."
    note += ps
    if len(note) > 1024:
        context.bot.send_document(chat_id=int(recorder), document=file_id)
        context.bot.send_message(chat_id=int(recorder), text=note, parse_mode=ParseMode.HTML)
    else:
        context.bot.send_document(chat_id=int(recorder), document=file_id, caption=note, parse_mode=ParseMode.HTML)
    database.delete_gif(gif_id)
    # end conversation
    return -1


# timer runs out
def two_hours_timer(context):
    context.bot.send_message(int(context.job.name[7:]), "Sorry, you took too long :(",
                             reply_markup=ReplyKeyboardRemove())
    data = context.job.context
    button = [[InlineKeyboardButton("I want to manage!", url=f"https://telegram.me/gifsupportbot?start=manage_"
                                    f"{data['gif_id']}_{data['message_id']}")]]
    context.bot.edit_message_caption(EDITED_CHANNEL_ID, data["message_id"], caption="",
                                     reply_markup=InlineKeyboardMarkup(button))
    context.job_queue.run_repeating(bump_edited, BUMP_SECONDS, name=data["gif_id"], context=data["message_id"])


def cancel(update, context):
    data = context.user_data
    user_id = update.effective_user.id
    button = [[InlineKeyboardButton("I want to manage!", url=f"https://telegram.me/gifsupportbot?start=manage_"
                                    f"{data['gif_id']}_{data['message_id']}")]]
    context.bot.edit_message_caption(EDITED_CHANNEL_ID, data["message_id"], caption="",
                                     reply_markup=InlineKeyboardMarkup(button))
    context.job_queue.run_repeating(bump_edited, BUMP_SECONDS, name=data["gif_id"], context=data["message_id"])
    name = "managed" + str(user_id)
    for job in context.job_queue.get_jobs_by_name(name):
        job.schedule_removal()
    update.message.reply_text("Cancelled!", reply_markup=ReplyKeyboardRemove())
    # end conversation
    return -1
