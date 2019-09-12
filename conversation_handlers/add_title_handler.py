from telegram import KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove
from constants import CATEGORIES
from database import database
import utils


GET_CATEGORY, GET_TITLE = range(2)


def start(update, _):
    user_id = update.effective_user.id
    if database.is_user_position(user_id, "managing"):
        pass
    else:
        return
    buttons = []
    for category in CATEGORIES:
        buttons.append(KeyboardButton(category))
    update.effective_message.reply_text("Oh hey. Choose a category :)",
                                        reply_markup=ReplyKeyboardMarkup(utils.build_menu(buttons, 3)))
    return GET_CATEGORY


def add_category(update, context):
    user_data = context.user_data
    category = update.effective_message.text
    user_data["category"] = category
    update.effective_message.reply_text("Wuhu. Now, send me the new title.", reply_markup=ReplyKeyboardRemove())
    return GET_TITLE


def add_title(update, context):
    category = context.user_data["category"]
    title = update.effective_message.text
    if database.is_title_not_unique(category, title):
        update.effective_message.reply_text("I'm sorry, but this title already exists. Send me another one or just "
                                            "/cancel.")
        return GET_TITLE
    else:
        database.add_title(category, title)
        update.effective_message.reply_text("Great, titles was added!")
        user_id = update.effective_user.id
        utils.log_action(context, update.effective_user.first_name, user_id, category=category, title=title)
        # end conversation
        return -1


def cancel(update, _):
    update.message.reply_text("Cancelled adding the title", reply_markup=ReplyKeyboardRemove())
    # end conversation
    return -1
