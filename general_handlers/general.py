from objects.user import User
from database import database
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, MessageEntity
from telegram.error import BadRequest
from telegram.utils.helpers import mention_html
from constants import RECORDED_CHANNEL_ID, EDITED_CHANNEL_ID, ADMINS, BUMP_SECONDS
from job_handlers.bump_timer import bump_recorded, bump_edited
from utils import log_action


def new_person(update, context):
    new_users = update.message.new_chat_members
    for new_user in new_users:
        real_user = User(new_user.id, None)
        database.insert_user(real_user)
        log_action(context, new_user.first_name, new_user.id, new_person=True)
        text = f"Hello {mention_html(new_user.id, new_user.first_name)}!\n\nTo actually be a (productive) member of " \
               f"this group, you need to start me. Go ahead :)"
        button = [[InlineKeyboardButton("Start", url="https://telegram.me/gifsupportbot?start=lol")]]
        update.effective_message.reply_html(text, reply_markup=InlineKeyboardMarkup(button))


def new_person_manual(update, context):
    user_id = 0
    first_name = "Null"
    entities = update.message.parse_entities([MessageEntity.TEXT_MENTION, MessageEntity.HASHTAG])
    if update.message.reply_to_message:
        user_id = update.message.reply_to_message.from_user.id
        first_name = update.message.reply_to_message.from_user.first_name
    elif entities:
        for entity in entities:
            if entity["type"] == MessageEntity.HASHTAG:
                try:
                    user_id = int(entities[entity][3:])
                    first_name = "username"
                except ValueError:
                    update.message.reply_text("This is not even a valid user_id, jesus christ. Get yourself together")
                    break
            else:
                user_id = entity.user.id
                first_name = entity.user.first_name
    else:
        update.message.reply_text("Hey, include a proper mention there or reply to a message. Idiot")
        return
    real_user = User(user_id, None)
    database.insert_user(real_user)
    log_action(context, first_name, user_id, new_person=True)
    update.message.reply_text(f"User {first_name} added!")


def delete_person(update, context):
    user_id = 0
    first_name = "Null"
    entities = update.message.parse_entities([MessageEntity.TEXT_MENTION, MessageEntity.HASHTAG])
    if update.message.reply_to_message:
        user_id = update.message.reply_to_message.from_user.id
        first_name = update.message.reply_to_message.from_user.first_name
    if entities:
        for entity in entities:
            if entity["type"] == MessageEntity.HASHTAG:
                try:
                    user_id = int(entities[entity][3:])
                    first_name = "username"
                except ValueError:
                    update.message.reply_text("This is not even a valid user_id, jesus christ. Get yourself together")
                    break
            else:
                user_id = entity.user.id
                first_name = entity.user.first_name
    else:
        update.message.reply_text("Hey, include a proper mention there. Idiot")
        return
    removed = database.remove_user(user_id)
    if removed:
        log_action(context, first_name, user_id, removed_person=True)
        update.message.reply_text(f"User {first_name} removed!")
    else:
        update.message.reply_text(f"User {first_name} is not in the projects database!")


def cancel(update, context):
    user_id = update.effective_user.id
    user_data = context.user_data
    if not database.is_user_in_database(user_id):
        return
    # check if the user is currently in a editing callback
    editing = context.job_queue.get_jobs_by_name("edited" + str(user_id))
    # check if the user is currently in a managing callback
    managing = context.job_queue.get_jobs_by_name("managed" + str(user_id))
    if editing:
        for job in editing:
            job.schedule_removal()
        button = [[InlineKeyboardButton("I want to edit", f"https://telegram.me/gifsupportbot?start=edit_"
                                                          f"{user_data['gif_id']}_{user_data['message_id']}")]]
        try:
            context.bot.edit_message_caption(RECORDED_CHANNEL_ID, user_data["message_id"], caption="",
                                             reply_markup=InlineKeyboardMarkup(button))
        except BadRequest:
            pass
        if not context.job_queue.get_jobs_by_name(user_data["gif_id"]):
            context.job_queue.run_repeating(bump_recorded, BUMP_SECONDS, name=user_data["gif_id"],
                                            context=user_data["message_id"])
        update.message.reply_text("Cancelled!")
    elif managing:
        for job in editing:
            job.schedule_removal()
        button = [[InlineKeyboardButton("I want to manage", url=f"https://telegram.me/gifsupportbot?start=manage_"
                                                                f"{user_data['gif_id']}_{user_data['message_id']}")]]
        try:
            context.bot.edit_message_caption(EDITED_CHANNEL_ID, user_data["message_id"], caption="",
                                             reply_markup=InlineKeyboardMarkup(button))
        except BadRequest:
            pass
        if not context.job_queue.get_jobs_by_name(user_data["gif_id"]):
            context.job_queue.run_repeating(bump_edited, BUMP_SECONDS, name=user_data["gif_id"],
                                            context=user_data["message_id"])
        update.message.reply_text("Cancelled!")
    # if no jobs are found, this means that the user just used it without being in a conversationhandler. So we are
    # just going to give a generic help message back
    else:
        update.effective_message.reply_text("You aren't in a \"action\" with me, but the command works, so that "
                                            "is great?")


def helping(update, _):
    user_id = update.effective_user.id
    if not database.is_user_in_database(user_id):
        return
    text = "Hey. So you need help? Cool. A list of commands?\n\n/start - you can choose your jobs and devices\n/add - "\
           "as a <b>creator</b>, you can send your recorded GIFs there\n/manage - as a <b>manager</b>, you can manage "\
           "subcategories there\n/help - shows this help\n/cancel - Cancel your current action. Always!"
    if user_id in ADMINS:
        text += "\n\nOh hey, so you want super secret admin commands? Hmm. Okay.\n/add_person - add a person manually "\
                "in case they joined the group while the bot was down.\n/goaway - kick a person out of the project"
    update.message.reply_html(text)


def error(update, context):
    if update.effective_message:
        text = "Hey. So there happened an error while executing your command. I alerted @poolitzer already, " \
               "if you think you can help fixing this problem, just contact him. Otherwise, if he needs help, " \
               "he will contact you or so ;P\n\nPlease run /cancel once, you should most likely be able to use me " \
               "again. If not, well - not my problem ;P "
        update.effective_message.reply_text(text)
    payload = 'with the user ' + update.effective_user.first_name if update.effective_user \
        else 'within the channel ' + update.effective_chat.title
    text = f"Hey asshole, an error happened, fix it. Wanna know the error, asshole? Here: {context.error}. It " \
           f"happend {payload}. Yeah, good luck getting more info ;)"
    context.bot.send_message(208589966, text)
    raise
