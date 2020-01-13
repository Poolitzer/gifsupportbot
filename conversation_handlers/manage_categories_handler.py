from telegram import ChatAction

import utils
from constants import POST_CHANNEL_ID
from database import database
from utils import log_action
from telegraph_handler.telegraph import update_page


def manage(update, _):
    user_id = update.effective_user.id
    if not database.is_user_position(user_id, "managing"):
        return
    message = "Hello there fellow manager. This command is basically a help message for the actual commands you want " \
              "to run.\n\n" \
              "• <b>New Categories</b>\n<i>Note: If a non-existent categories is submitted, they will be " \
              "automatically created. Also note that underlines are not supported, they will be turned to spaces</i>" \
              "\n\n<b>Syntax:</b>\n/mc [category path]\n<b>Example:</b>\n<code>/mc settings.chat settings.themese" \
              "</code>\n\n" \
              "• <b>Move/Rename category</b>\n<i>Note: You can not create multiple new categories using this " \
              "command. You must use /mc first if the path you are trying to move the gifs to does not exist.</i>" \
              "\n\n<b>Syntax:</b>\n/rc [old path]>[new path]\n<b>Example:</b>\n<code>/rc settings.chat " \
              "settings.themese>settings.chat settings.themes</code>\n\n" \
              "• <b>Delete category</b>\n<i>Note: When you use this command, this means every gif within the " \
              "selected category gets deleted. When you provide a parent category, it and every sub category gets " \
              "deleted, potentially a lot of GIFs. Be very very careful about what you are doing here, otherwise " \
              "people will get angry.</i>\n\n<b>Syntax:</b>\n/dc [category path]\n<b>Example:</b>\n<code>/dc " \
              "settings.chat settings.themes</code>\n\n" \
              "• <b>Show categories</b>\n\n<b>Syntax:</b>\n/tree [optional path]\n<b>Example:</b>\n<code>/tree " \
              "settings</code>"
    update.effective_message.reply_text(message, parse_mode="HTML")


def new_category(update, context):
    user_id = update.effective_user.id
    if not database.is_user_position(user_id, "managing"):
        return
    path = update.effective_message.text[4:]
    path = path.replace(" ", "_")
    success = database.add_category(path)
    if not success:
        update.effective_message.reply_text("That category already exists or would override an existing one. "
                                            "Try again")
        return
    update.effective_message.reply_text("Thanks, new category saved; recorders can create GIFs for it now.")
    log_action(context, update.effective_user.first_name, user_id, new_category=path)


def rename_category(update, context):
    user_id = update.effective_user.id
    if not database.is_user_position(user_id, "managing"):
        return
    context.bot.send_chat_action(update.effective_chat.id, ChatAction.TYPING)
    text = update.effective_message.text.replace(" ", "_")
    text = text[4:].split(">")
    try:
        categories = database.rename_category(text[0], text[1])
    except IndexError:
        update.effective_message.reply_text("You screwed the > part up, try again")
        return
    except KeyError:
        update.effective_message.reply_text("You screwed the path for the old part up, try again")
        return
    except FileNotFoundError:
        update.effective_message.reply_text("The new path already exists, you can't do it like that")
        return
    except FileExistsError:
        update.effective_message.reply_text("The new path does not exist until the latest category, which it has to.")
        return
    text.append(categories['changed_categories'])
    update_page()
    if categories["post"]:
        for post in categories["post"]:
            context.bot.send_chat_action(update.effective_chat.id, ChatAction.TYPING)
            caption = utils.create_caption(text[1].split(".")[-1], post["device"], post["help_link"])
            context.bot.edit_message_caption(POST_CHANNEL_ID, post["message_id"], caption=caption,
                                             parse_mode="HTML")
    update.effective_message.reply_text(f"Category renamed, {categories['changed_categories']} changed")
    log_action(context, update.effective_user.first_name, user_id, rename_category=text)


def delete_category_question(update, context):
    user_id = update.effective_user.id
    if not database.is_user_position(user_id, "managing"):
        return
    path = update.effective_message.text[4:]
    path = path.replace(" ", "_")
    categories = database.get_subcategories(path)
    how_many = {"categories": 0, "GIFs": 0}
    for category in categories:
        how_many["categories"] += 1
        for device in category["devices"]:
            if category["devices"][device]["message_id"]:
                how_many["GIFs"] += 1
    update.effective_message.reply_text(f"Are you 100% sure you want to do this? This means I would delete "
                                        f"{how_many['GIFs']} GIFs from {how_many['categories']} categories. If yes, "
                                        f"send me /yes. If you screw this up, a lot of people are going to be "
                                        f"seriously angry at you.")
    context.user_data["path"] = path


def delete_category(update, context):
    user_id = update.effective_user.id
    if not database.is_user_position(user_id, "managing"):
        return
    if "path" in context.user_data:
        path = context.user_data["path"]
        del context.user_data["path"]
    else:
        return
    context.bot.send_chat_action(update.effective_chat.id, ChatAction.TYPING)
    categories = database.delete_category(path)
    if "error" == categories:
        update.effective_message.reply_text("You screwed up, that path doesn't exist; try again or so.")
        return
    """
    value = categories[-1]
    del categories[-1]
    """
    for category in categories:
        context.bot.delete_message(POST_CHANNEL_ID, category["message_id"])
    update.effective_message.reply_text("THEY ARE GONE.")
    category_ids = [f"#{i['gif_id']}" for i in categories]
    # TODO +value here
    to_return = {"path": path, "categories": category_ids}
    update_page()
    log_action(context, update.effective_user.first_name, user_id, delete_category=to_return)


def tree(update, _):
    user_id = update.effective_user.id
    if not database.is_user_position(user_id, "managing"):
        return
    message = update.effective_message.text
    dictionary = database.get_category(message[6:])
    if not dictionary:
        update.effective_message.reply_text("You made a typo there, this category path does not exists")
        return
    generator = to_tree(dictionary)
    update.effective_message.reply_text('\n'.join(generator), parse_mode="HTML")


def to_tree(d, c=0):
    for a, b in d.items():
        yield '   '.join('|' for _ in range(c + 1)) + f'---<code>{a.replace("_", " ")}</code>'
        yield from [] if b is None else to_tree(b, c + 1)
