from uuid import uuid4
from telegram import InlineQueryResultArticle, InputTextMessageContent, InlineKeyboardMarkup, ParseMode
from telegram.ext import CommandHandler, Updater, Filters, ConversationHandler, InlineQueryHandler, \
    CallbackQueryHandler, MessageHandler
from telegram.inline.inlinekeyboardbutton import InlineKeyboardButton
import json
import logging
import re

logging.basicConfig(filename="log.log", format='%(asctime)s - %(first_name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

database = json.load(open('./database.json'))
tokenbase = json.load(open('./tokens.json'))

ENTRY, CHANGEWHAT, UPDATE, CHANGE, TITEL, DESCRIPTION, KEYWORDS = range(7)


class Variables:
    variable = []
    add = []


Globalvariables = Variables()


def text_creator(index):
    text = "<a href=\"https://t.me/gifsupport/{}\">{}</a> :)".format(database["links"][index][2], database["links"][index][0])
    return InputTextMessageContent(text, ParseMode.HTML)


def start_admin(_, update):
    update.message.reply_text('Hi! Run /update to update an existing GIF, forward me one from the channel to add it and'
                              " don't forget that you can use /cancel almost every time.")


def start(_, update):
    update.message.reply_text("Go away.")


def new_member(_, update):
    for user in update.message.new_chat_members:
        if user["id"] == 730048833:
            update.message.reply_text("Hello group. I just wanted to mention that I wont moderate this group in any way"
                                      ", because honestly, why would you ever need that, argh, I should do something "
                                      "better with my time.")
        else:
            update.message.reply_text("Hello {}, nice to have you in this group. Ping Poolitzer if you have any "
                                      "questions regarding this bot, and otherwise, enjoy your stay.")
            tokenbase["ADMINS"].append(user["id"])
            with open('./tokens.json', 'w') as outfile:
                json.dump(tokenbase, outfile, indent=4, sort_keys=True)


def inlinequery(_, update):
    query = update.inline_query.query
    results = []
    amount = 0
    for index, words in enumerate(database["keywords"]):
        for word in words:
            payload = re.search(query, word)
            if payload:
                results.append(InlineQueryResultArticle(
                    id=uuid4(),
                    title=database["links"][index][0],
                    input_message_content=text_creator(index),
                    description=database["links"][index][1]
                ))
                amount += 1
                if amount == 5:
                    update.inline_query.answer(results)
                    break
                else:
                    break
            else:
                pass
    if amount <= 4:
        update.inline_query.answer(results)


def update_db(_, update):
    temp = []
    subtemp = []
    x = 0
    for index, names in enumerate(database["links"]):
        subtemp.append(
            InlineKeyboardButton(names[0], callback_data="update{}".format(str(len(str(index))) + str(index))))
        x += 1
        if x is 2:
            temp.append(subtemp)
            subtemp = []
            x = 0
        elif names is database["links"][-1] and x is 1:
            temp.append(subtemp)
    update.message.reply_text("Feel like updating a GIF entry? Pick one from the list. Use /cancel to cancel.",
                              reply_markup=InlineKeyboardMarkup(temp))
    return ENTRY


def entry(_, update):
    query = update.callback_query
    length = int(query.data[6])
    index = int(query.data[7:7 + length])
    buttons = [[InlineKeyboardButton("Titel", callback_data="entry{}".format(query.data[6:len(query.data)] + "0")),
                InlineKeyboardButton("Description", callback_data="entry{}".format(
                    query.data[6:len(query.data)] + "1"))],
               [InlineKeyboardButton("Post-ID", callback_data="entry{}".format(query.data[6:len(query.data)] + "2")),
                InlineKeyboardButton("keywords", callback_data="entry{}".format(query.data[6:len(query.data)] + "4"))],
               [InlineKeyboardButton("Delete it :0", callback_data="entry{}".format(
                   query.data[6:len(query.data)] + "5"))]]
    reply_markup = InlineKeyboardMarkup(buttons)
    query.edit_message_text("So, {} it is. What do you want to change?".format(database["links"][index][0]),
                            reply_markup=reply_markup)
    return CHANGEWHAT


def change(_, update):
    query = update.callback_query
    length = int(query.data[5])
    index = int(query.data[6:6 + length])
    todo = int(query.data[-1])
    if todo == 0:
        query.edit_message_text("Great. Please send me the new titel")
        Globalvariables.variable = [index, 0]
        return UPDATE
    elif todo == 1:
        query.edit_message_text("Great. Please send me the new description")
        Globalvariables.variable = [index, 1]
        return UPDATE
    elif todo == 2:
        query.edit_message_text("Great. Please send me the new post-id")
        Globalvariables.variable = [index, 2]
        return UPDATE
    elif todo == 4:

        temp = []
        subtemp = []
        x = 0
        for hupps, names in enumerate(database["keywords"][index]):
            subtemp.append(
                InlineKeyboardButton(names, callback_data="keyword{}".format(
                    query.data[5:len(query.data) - 1] + str(len(str(hupps))) + str(hupps))))
            x += 1
            if x is 2:
                temp.append(subtemp)
                subtemp = []
                x = 0
            elif names is database["keywords"][index][-1] and x is 1:
                temp.append(subtemp)
        temp.append([InlineKeyboardButton("Add a new one", callback_data="keyword{}new".format(
            query.data[5:len(query.data) - 1]))])
        query.edit_message_text("So, you want to change/delete a keyword or add a new one?",
                                reply_markup=InlineKeyboardMarkup(temp))
        return UPDATE
    else:
        buttons = [[InlineKeyboardButton("Delete", callback_data="delete{}yes".format(query.data[5:len(query.data)])),
                    InlineKeyboardButton("Cancel", callback_data="delete{}no".format(query.data[5:len(query.data)]))]]
        query.edit_message_text("Are you sure?", reply_markup=InlineKeyboardMarkup(buttons))
        return UPDATE


def change_keyword(_, update):
    query = update.callback_query
    length = int(query.data[7])
    index = int(query.data[8:8 + length])
    if query.data[-3:len(query.data)] == "new":
        query.edit_message_text("Great. Please send me the new keyword")
        Globalvariables.variable = [index, 4]
        return UPDATE
    else:
        buttons = [[InlineKeyboardButton("Update", callback_data="change{}yes".format(query.data[7:len(query.data)])),
                    InlineKeyboardButton("Delete", callback_data="change{}no".format(query.data[7:len(query.data)]))]]
        query.edit_message_text("Do you want to delete or update it?", reply_markup=InlineKeyboardMarkup(buttons))
        return CHANGE


def change_keyword_for_real(_, update):
    query = update.callback_query
    length = int(query.data[6])
    index = int(query.data[7:7 + length])
    length2 = int(query.data[7 + length])
    index2 = int(query.data[8 + length:8 + length + length2])
    todo = query.data[8 + length2 + length:len(query.data)]
    if todo == "yes":
        query.edit_message_text("Great. Please send me the new keyword")
        Globalvariables.variable = [index, 3, index2]
        return UPDATE
    else:
        query.edit_message_text("Deleted :(")
        del database["keywords"][index][index2]
        with open('./database.json', 'w') as outfile:
            json.dump(database, outfile, indent=4, sort_keys=True)
        return ConversationHandler.END


def delete_entry(_, update):
    query = update.callback_query
    length = int(query.data[6])
    index = int(query.data[7:7 + length])
    todo = str(query.data[-1:-2])
    if not todo == "no":
        query.edit_message_text("We let it stay :)")
    else:
        query.edit_message_text("Deleted :(")
        del database["links"][index]
        del database["keywords"][index]
        with open('./database.json', 'w') as outfile:
            json.dump(database, outfile, indent=4, sort_keys=True)
    return ConversationHandler.END


def pass_update(_, update):
    if Globalvariables.variable[1] == 0:
        update.message.reply_text("Changed title from {} to {}.".format(
            database["links"][Globalvariables.variable[0]][Globalvariables.variable[1]], update.message.text))
        database["links"][Globalvariables.variable[0]][Globalvariables.variable[1]] = update.message.text
        with open('./database.json', 'w') as outfile:
            json.dump(database, outfile, indent=4, sort_keys=True)
    elif Globalvariables.variable[1] == 1:
        update.message.reply_text("Changed description from {} to {}.".format(
            database["links"][Globalvariables.variable[0]][Globalvariables.variable[1]], update.message.text))
        database["links"][Globalvariables.variable[0]][Globalvariables.variable[1]] = update.message.text
        with open('./database.json', 'w') as outfile:
            json.dump(database, outfile, indent=4, sort_keys=True)
    elif Globalvariables.variable[1] == 2:
        update.message.reply_text("Changed id from {} to {}.".format(
            database["links"][Globalvariables.variable[0]][Globalvariables.variable[1]], update.message.text))
        database["links"][Globalvariables.variable[0]][Globalvariables.variable[1]] = update.message.text
        with open('./database.json', 'w') as outfile:
            json.dump(database, outfile, indent=4, sort_keys=True)
    elif Globalvariables.variable[1] == 3:
        update.message.reply_text("Changed keyword from {} to {}.".format(
            database["keywords"][Globalvariables.variable[0]][Globalvariables.variable[2]], update.message.text))
        database["keywords"][Globalvariables.variable[0]][Globalvariables.variable[2]] = update.message.text
        with open('./database.json', 'w') as outfile:
            json.dump(database, outfile, indent=4, sort_keys=True)
    elif Globalvariables.variable[1] == 4:
        update.message.reply_text("Added keyword {} to {}.".format(
            update.message.text, database["links"][Globalvariables.variable[0]][0]))
        database["keywords"][Globalvariables.variable[0]].append(update.message.text)
        with open('./database.json', 'w') as outfile:
            json.dump(database, outfile, indent=4, sort_keys=True)
    return ConversationHandler.END


def add_db(_, update):
    if update.message.forward_from_chat.id == -1001353729458:
        skip = False
        for post in database["links"]:
            if post[2] == update.message.forward_from_message_id:
                skip = True
                update.message.reply_text("Haha, funny. Please forward me a new post from the botsupport channel smh")
                return ConversationHandler.END
        if not skip:
            Globalvariables.add = [0, 0, update.message.forward_from_message_id]
            update.message.reply_text("Great, a new GIF. Please send its titel :) Use /cancel anytime to cancel.")
            return TITEL
    else:
        update.message.reply_text("Haha, funny. Please forward me an animation from the botsupport channel smh")
        return ConversationHandler.END


def add_titel(_, update):
    Globalvariables.add[0] = update.message.text
    update.message.reply_text("<b>{}</b> it is. Please send me a good description now"
                              .format(update.message.text), parse_mode=ParseMode.HTML)
    return DESCRIPTION


def add_description(_, update):
    Globalvariables.add[1] = update.message.text
    database["links"].append(Globalvariables.add)
    Globalvariables.add = []
    update.message.reply_text("The description is <b>{}</b>. Lets head over to keywords, send me one."
                              .format(update.message.text), parse_mode=ParseMode.HTML)
    return KEYWORDS


def add_keyword(_, update):
    messages = ["No one will see this. Sad story. Welp, there we go",
                "You added the keyword <b>{}</b>. If you want to add another one, send it. If you are finished, send "
                "/finish.", "Heyy. A second keyword. It's <b>{}</b>, right?",
                "A third? Well, thats cool. <b>{}</b> this time.", "A fourth? :OOO <b>{}</b>. Don't forget /finish...",
                "ANOTHER ONE? You are kidding me, right? It's <b>{}</b>, neat", "I really like <b>{}</b>.",
                "Don't push it too far though, not even with <b>{}</b>.", "Ok. Its enough. <b>{}</b>.",
                "Please. Stop. <b>{}</b>", "I'm really not creative anymore. <b>{}</b>"]
    Globalvariables.add.append(update.message.text)
    try:
        update.message.reply_text(messages[len(Globalvariables.add)].format(update.message.text),
                                  parse_mode=ParseMode.HTML)
    except IndexError:
        update.message.reply_text(messages[-1].format(update.message.text), parse_mode=ParseMode.HTML)
    return KEYWORDS


def finish(_, update):
    database["keywords"].append(Globalvariables.add)
    Globalvariables.add = []
    with open('./database.json', 'w') as outfile:
        json.dump(database, outfile, indent=4, sort_keys=True)
    update.message.reply_text("SUCCESS. Thanks for adding a post. Have a good one".format(update.message.text))
    return ConversationHandler.END


def cancel(_, update):
    update.message.reply_text('Mission ABORTED!')
    return ConversationHandler.END


def main():
    updater = Updater(token=tokenbase["BOTTOKEN"])
    dp = updater.dispatcher
    # TODO Filters.user(private["ADMINS"]) and remove the other hashtag
    dp.add_handler(CommandHandler("start", start_admin))
    # dp.add_handler(CommandHandler("start", start))
    conv_update_handler = ConversationHandler(
        # TODO Filters.user(private["ADMINS"])
        entry_points=[CommandHandler("update", update_db)],

        states={
            ENTRY: [CallbackQueryHandler(entry, pattern="update")],
            CHANGEWHAT: [CallbackQueryHandler(change, pattern="entry")],
            UPDATE: [MessageHandler(Filters.text, pass_update), CallbackQueryHandler(change_keyword, pattern="keyword"),
                     CallbackQueryHandler(delete_entry, pattern="delete")],
            CHANGE: [CallbackQueryHandler(change_keyword_for_real, pattern="change")]
        },

        fallbacks=[CommandHandler('cancel', cancel)],

    )
    dp.add_handler(conv_update_handler)
    conv_add_handler = ConversationHandler(
        # TODO Filters.user(private["ADMINS"]) &
        entry_points=[MessageHandler(Filters.forwarded & Filters.animation, add_db)],
        states={
            TITEL: [MessageHandler(Filters.text, add_titel)],
            DESCRIPTION: [MessageHandler(Filters.text, add_description)],
            KEYWORDS: [MessageHandler(Filters.text, add_keyword), CommandHandler('finish', finish)]
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )
    dp.add_handler(conv_add_handler)
    dp.add_handler(InlineQueryHandler(inlinequery))
    dp.add_handler(MessageHandler(Filters.status_update.new_chat_members, new_member))
    updater.start_polling()


if __name__ == '__main__':
    main()
