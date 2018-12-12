from uuid import uuid4
from github import Github
from telegram import InlineQueryResultArticle, InputTextMessageContent, InlineKeyboardMarkup, ParseMode, MessageEntity
from telegram.ext import CommandHandler, Updater, Filters, ConversationHandler, InlineQueryHandler, \
    CallbackQueryHandler, MessageHandler
from telegram.inline.inlinekeyboardbutton import InlineKeyboardButton
from telegram.utils.helpers import mention_html
import json
import logging
import re
from pymongo import MongoClient

logging.basicConfig(filename="log.log", format='%(asctime)s - %(first_name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

database = json.load(open('./database.json'))
tokenbase = json.load(open('./tokens.json'))

ENTRY, CHANGEWHAT, UPDATE, CHANGE, TITEL, DESCRIPTION, KEYWORDS, QUESTION, DEVICE, LINK, CALLBACK, GIF = range(12)

g = Github(tokenbase["GITHUBTOKEN"])


class Variables:
    variable = []
    add = []


Globalvariables = Variables()


class Database:

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.logger.debug("Database init")
        self.db = MongoClient()
        self.db = self.db["gifsupportbot"]

    def insert_posts(self, posts):
        self.db.posts.insert_one(posts)

    def insert_demo_posts(self, posts):
        self.db.demo_posts.insert_one(posts)

    def insert_voter(self, post_id, voter):
        temp = self.db.posts.find_one({"post_id": post_id})['voters']
        temp.append(voter)
        self.db.posts.update_one({"post_id": post_id}, {"$set": {'voters': temp}})

    def insert_demo_voter(self, post_id, voter):
        temp = self.db.demo_posts.find_one({"post_id": post_id})['voters']
        temp.append(voter)
        self.db.demo_posts.update_one({"post_id": post_id}, {"$set": {'voters': temp}})

    def update_vote(self, post_id, voter_id, votes):
        temp = self.db.posts.find_one({"post_id": post_id})['voters']
        for voter in temp:
            if voter["id"] == voter_id:
                voter["voted"] = votes
        self.db.posts.update_one({"post_id": post_id}, {"$set": {'voters': temp}})

    def update_demo_vote(self, post_id, voter_id, votes):
        temp = self.db.demo_posts.find_one({"post_id": post_id})['voters']
        for voter in temp:
            if voter["id"] == voter_id:
                voter["voted"] = votes
        self.db.demo_posts.update_one({"post_id": post_id}, {"$set": {'voters': temp}})


Database = Database()


class Post:

    def __init__(self, post_id):
        self.post_id = post_id
        self.voters = []


class Voter:

    def __init__(self, user_id, mention, lang_code, voted):
        self.id = user_id
        self.mention = mention
        self.lang_code = lang_code
        self.voted = voted


def text_creator(index):
    text = "<a href=\"https://t.me/gifsupport/{}\">{}</a> :)" \
        .format(database["links"][index][2], database["links"][index][0])
    return InputTextMessageContent(text, ParseMode.HTML)


def text_creator_demo(index):
    text = "<a href=\"https://t.me/gifsupport/{}\">{}</a> :)" \
        .format(database["links_demo"][index][2], database["links_demo"][index][0])
    return InputTextMessageContent(text, ParseMode.HTML)


def markup_creator(post_id):
    pro = 0
    con = 0
    for voter in Database.db.posts.find_one({"post_id": post_id})["voters"]:
        if voter["voted"] == 1:
            pro += 1
        if voter["voted"] == -1:
            con += 1
    return InlineKeyboardMarkup([[InlineKeyboardButton("👍{}".format(pro), callback_data="vote_yes"),
                                  InlineKeyboardButton("👎{}".format(con), callback_data="vote_no")]])


def markup_demo_creator(post_id):
    pro = 0
    con = 0
    for voter in Database.db.demo_posts.find_one({"post_id": post_id})["voters"]:
        if voter["voted"] == 1:
            pro += 1
        if voter["voted"] == -1:
            con += 1
    return InlineKeyboardMarkup([[InlineKeyboardButton("👍{}".format(pro), callback_data="demo_vote_yes"),
                                  InlineKeyboardButton("👎{}".format(con), callback_data="demo_vote_no")]])


def start_admin(_, update, args):
    if args:
        args[0].split('_')
        if args[1]:
            Globalvariables.add = [0, 0, int(args[0]), "DEMO"]
        else:
            Globalvariables.add = [0, 0, int(args[0])]
        update.message.reply_text("Great. lets do it then. Send me a fitting title please")
        return TITEL
    else:
        update.message.reply_text('Hi! Run /update to update an existing GIF, forward me one from the channel to add it'
                                  " and don't forget that you can use /cancel almost every time.")
        return ConversationHandler.END


def new_member(_, update):
    if update.effective_chat.id == -1001374913393:
        for user in update.message.new_chat_members:
            if user["id"] == 730048833:
                update.message.reply_text("Hello group. I just wanted to mention that I wont moderate this group in any"
                                          " way, because honestly, why would you ever need that, argh, I should do "
                                          "something better with my time. Pool, you idiot, the ID is {}"
                                          .format(update.effective_chat.id))
            else:
                update.message.reply_text("Hello {}, nice to have you in this group. Ping Poolitzer if you have any "
                                          "questions regarding this bot, and otherwise, enjoy your stay."
                                          .format(mention_html(user["id"], user["first_name"])),
                                          parsemode=ParseMode.HTML)
                tokenbase["ADMINS"].append(user["id"])
                with open('./tokens.json', 'w') as outfile:
                    json.dump(tokenbase, outfile, indent=4, sort_keys=True)


def inlinequery(_, update):
    query = update.inline_query.query
    results = []
    amount = 0
    for index, words in enumerate(database["keywords"]):
        for word in words:
            payload = re.search(query, word, re.IGNORECASE)
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


def demoinlinequery(_, update):
    query = update.inline_query.query
    results = []
    amount = 0
    query = query[4:len(query)]
    for index, words in enumerate(database["keywords_demo"]):
        for word in words:
            payload = re.search(query, word, re.IGNORECASE)
            if payload:
                results.append(InlineQueryResultArticle(
                    id=uuid4(),
                    title=database["links_demo"][index][0],
                    input_message_content=text_creator_demo(index),
                    description=database["links_demo"][index][1]
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


def vote(_, update):
    query = update.callback_query
    todo = query.data[-2:len(query.data)]
    user = query.from_user
    post = Database.db.posts.find_one({"post_id": query.message.message_id})
    update_vote = Database.update_vote
    insert_vote = Database.insert_voter
    markup = markup_creator
    return real_vote(query, todo, user, post, update_vote, insert_vote, markup)


def demovote(_, update):
    query = update.callback_query
    todo = query.data[-2:len(query.data)]
    user = query.from_user
    post = Database.db.demo_posts.find_one({"post_id": query.message.message_id})
    update_vote = Database.update_demo_vote
    insert_vote = Database.insert_demo_voter
    markup = markup_demo_creator
    return real_vote(query, todo, user, post, update_vote, insert_vote, markup)


def real_vote(query, todo, user, post, update_vote, insert_voter, markup):
    for voter in post["voters"]:
        if voter["id"] == user.id:
            if todo == "no":
                if voter["voted"] == -1:
                    update_vote(query.message.message_id, user.id, 0)
                    query.answer("You took your vote back")
                    query.message.edit_reply_markup(reply_markup=markup(query.message.message_id))
                    return
                else:
                    update_vote(query.message.message_id, user.id, -1)
                    query.answer("You voted against it")
                    query.message.edit_reply_markup(reply_markup=markup(query.message.message_id))
                    return
            else:
                if voter["voted"] == 1:
                    update_vote(query.message.message_id, user.id, 0)
                    query.answer("You took your vote back")
                    query.message.edit_reply_markup(reply_markup=markup(query.message.message_id))
                    return
                else:
                    update_vote(query.message.message_id, user.id, 1)
                    query.answer("You voted in favour of it")
                    query.message.edit_reply_markup(reply_markup=markup(query.message.message_id))
                    return
    if todo == "no":
        insert_voter(query.message.message_id, vars(Voter(user.id, user.mention_html(), user.language_code, -1)))
        query.answer("You voted against it")
        query.message.edit_reply_markup(reply_markup=markup(query.message.message_id))
    else:
        insert_voter(query.message.message_id, vars(Voter(user.id, user.mention_html(), user.language_code, 1)))
        query.answer("You voted in favour of it")
        query.message.edit_reply_markup(reply_markup=markup(query.message.message_id))


def linus_is_stupid(_, update):
    if update.message.reply_to_message:
        update.message.reply_to_message.reply_text("EXACTLY! Thank you. Finally someone says it.")
    else:
        update.message.reply_text("EXACTLY! Thank you. Finally someone says it.")


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


def change_keyword_for_real(bot, update):
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
        bot.send_message(-1001214567646, "{} deleted the keyword {} from the entry {}. Not so much chaos, panic, "
                                         "disorder 'n stuff I assume? "
                         .format(mention_html(update.effective_user.id, update.effective_user.first_name),
                                 database["keywords"][index][index2], database["links"][index][0]),
                         parse_mode=ParseMode.HTML)
        del database["keywords"][index][index2]
        with open('./database.json', 'w') as outfile:
            json.dump(database, outfile, indent=4, sort_keys=True)
        return ConversationHandler.END


def delete_entry(bot, update):
    query = update.callback_query
    length = int(query.data[6])
    index = int(query.data[7:7 + length])
    todo = str(query.data[-2:11])
    if todo == "no":
        query.edit_message_text("We let it stay :)")
    else:
        query.edit_message_text("Deleted :(")
        bot.send_message(-1001214567646, "{} deleted {}. Chaos, panic, disorder 'n stuff."
                         .format(mention_html(update.effective_user.id, update.effective_user.first_name),
                                 database["links"][index][0]),
                         parse_mode=ParseMode.HTML)
        del database["links"][index]
        del database["keywords"][index]
        with open('./database.json', 'w') as outfile:
            json.dump(database, outfile, indent=4, sort_keys=True)
    return ConversationHandler.END


def pass_update(bot, update):
    if Globalvariables.variable[1] == 0:
        update.message.reply_text("Changed title from {} to {}.".format(
            database["links"][Globalvariables.variable[0]][Globalvariables.variable[1]], update.message.text))
        bot.send_message(-1001214567646, "{} changed title from {} to {}."
                         .format(mention_html(update.effective_user.id, update.effective_user.first_name),
                                 database["links"][Globalvariables.variable[0]][0], update.message.text),
                         parse_mode=ParseMode.HTML)
        database["links"][Globalvariables.variable[0]][Globalvariables.variable[1]] = update.message.text
    elif Globalvariables.variable[1] == 1:
        update.message.reply_text("Changed description from {} to {}.".format(
            database["links"][Globalvariables.variable[0]][Globalvariables.variable[1]], update.message.text))
        bot.send_message(-1001214567646, "{} changed description from {} to {}."
                         .format(mention_html(update.effective_user.id, update.effective_user.first_name),
                                 database["links"][Globalvariables.variable[0]][0], update.message.text),
                         parse_mode=ParseMode.HTML)
        database["links"][Globalvariables.variable[0]][Globalvariables.variable[1]] = update.message.text
    elif Globalvariables.variable[1] == 2:
        update.message.reply_text("Changed id from {} to {}.".format(
            database["links"][Globalvariables.variable[0]][Globalvariables.variable[1]], update.message.text))
        bot.send_message(-1001214567646, "{} changed id from {} to {}."
                         .format(mention_html(update.effective_user.id, update.effective_user.first_name),
                                 database["links"][Globalvariables.variable[0]][0], update.message.text),
                         parse_mode=ParseMode.HTML)
        database["links"][Globalvariables.variable[0]][Globalvariables.variable[1]] = update.message.text
    elif Globalvariables.variable[1] == 3:
        update.message.reply_text("Changed keyword from {} to {}.".format(
            database["keywords"][Globalvariables.variable[0]][Globalvariables.variable[2]], update.message.text))
        bot.send_message(-1001214567646, "{} changed keyword {} from {} to {}."
                         .format(mention_html(update.effective_user.id, update.effective_user.first_name),
                                 database["links"][Globalvariables.variable[0]][0],
                                 database["links"][Globalvariables.variable[0]][0], update.message.text),
                         parse_mode=ParseMode.HTML)
        database["keywords"][Globalvariables.variable[0]][Globalvariables.variable[2]] = update.message.text
    elif Globalvariables.variable[1] == 4:
        update.message.reply_text("Added keyword {} to {}.".format(
            update.message.text, database["links"][Globalvariables.variable[0]][0]))
        bot.send_message(-1001214567646, "{} added keyword {} to {}."
                         .format(mention_html(update.effective_user.id, update.effective_user.first_name),
                                 update.message.text, database["links"][Globalvariables.variable[0]][0]),
                         parse_mode=ParseMode.HTML)
        database["keywords"][Globalvariables.variable[0]].append(update.message.text)
    with open('./database.json', 'w') as outfile:
        json.dump(database, outfile, indent=4, sort_keys=True)
    return ConversationHandler.END


def add_db_demo(_, update):
    Globalvariables.add = [0, "Title", "Device", "link", "DEMO"]
    update.message.reply_text("Ah DEMO GIF? Cool. Send the gif now. Use /cancel anytime to cancel.")
    return GIF


def add_gif_demo(_, update):
    Globalvariables.add[0] = update.message.animation.file_id
    update.message.reply_text("Alright. Please send its question :) Use /cancel anytime to cancel.")
    return QUESTION


def add_db(_, update):
    Globalvariables.add = [update.message.animation.file_id, "Title", "Device", "link"]
    update.message.reply_text("Great, a new GIF. Please send its question :) Use /cancel anytime to cancel.")
    return QUESTION


def add_question(_, update):
    Globalvariables.add[1] = update.message.text
    update.message.reply_text("Got the Question. Now the device please :) Use /cancel anytime to cancel.")
    return DEVICE


def add_device(_, update):
    for device in database["devices"]:
        if update.message.text.lower() == device:
            Globalvariables.add[2] = update.message.text.lower()
            if device == "android":
                update.message.reply_text("My favourite device tbh. Now the link, we are done then :) "
                                          "Use /cancel anytime to cancel.")
            elif device == "ios":
                update.message.reply_text("Ihhh, an apple device. Now the link, we are done then :) "
                                          "Use /cancel anytime to cancel.")
            return LINK
    update.message.reply_text("Sorry, you device isn't in my database. If its just a typo, send it again. If you "
                              "believe that this is an error, ping @Poolitzer :)")
    return DEVICE


def add_link(bot, update):
    posting_id = -1001353729458
    Globalvariables.add[3] = update.message.text
    caption = "{}\n\n#{} #gifsupport\n\n<a href=\"{}\">More help</a>".format(
        Globalvariables.add[1], Globalvariables.add[2], Globalvariables.add[3])
    votebuttons = InlineKeyboardMarkup([[InlineKeyboardButton("👍", callback_data="vote_yes"),
                                         InlineKeyboardButton("👎", callback_data="vote_no")]])
    try:
        if Globalvariables.add[4]:
            del Globalvariables.add[4]
            posting_id = -1001353632441
            Globalvariables.add.append("DEMO")
            votebuttons = InlineKeyboardMarkup([[InlineKeyboardButton("👍", callback_data="demo_vote_yes"),
                                                 InlineKeyboardButton("👎", callback_data="demo_vote_no")]])
    except IndexError:
        pass
    message = bot.send_animation(posting_id, Globalvariables.add[0], caption=caption, parse_mode=ParseMode.HTML,
                                 reply_markup=votebuttons)
    buttons = InlineKeyboardMarkup([[InlineKeyboardButton("Yes", callback_data="yes"),
                                     InlineKeyboardButton("No", callback_data="no")]])
    update.message.reply_text("Thank you so much so far. Do you have the spare time to add this GIF to the database "
                              "of this bot? Should take about 1 minute.", reply_markup=buttons)
    Globalvariables.add[2] = message.message_id
    try:
        if Globalvariables.add[3]:
            Globalvariables.add = [0, 0, 0, "DEMO"]
            Database.insert_demo_posts(vars(Post(message.message_id)))
    except IndexError:
        Globalvariables.add = [0, 0, 0]
        Database.insert_posts(vars(Post(message.message_id)))
    return CALLBACK


def queryhandler(bot, update):
    query = update.callback_query
    if query.data == "yes":
        query.edit_message_text("Great. lets do it then. Send me a fitting title please")
        return TITEL
    else:
        query.edit_message_text("Awww :(")
        try:
            if Globalvariables.add[3]:
                button = InlineKeyboardMarkup([[InlineKeyboardButton("Start", url="https://t.me/GIFSupportbot/?start={}"
                                                                     .format(str(Globalvariables.add[2]) + "_DEMO"))]])
                bot.send_message(-1001374913393,
                                 "Anyone feels like adding the newest DEMO GIF? I mean. It would be nice...",
                                 reply_markup=button, parse_mode=ParseMode.HTML)
        except IndexError:
            button = InlineKeyboardMarkup([[InlineKeyboardButton("Start", url="https://t.me/GIFSupportbot/?start={}"
                                                                 .format(Globalvariables.add[2]))]])
            bot.send_message(-1001374913393, "Does someone have enough time to add "
                                             "<a href=\"https://t.me/gifsupport/{}\"> this post</a> to my database?".
                             format(Globalvariables.add[2]), reply_markup=button, parse_mode=ParseMode.HTML)
        return ConversationHandler.END


def add_title(_, update):
    Globalvariables.add[0] = update.message.text
    update.message.reply_text("<b>{}</b> it is. Please send me a good description now"
                              .format(update.message.text), parse_mode=ParseMode.HTML)
    return DESCRIPTION


def add_description(_, update):
    Globalvariables.add[1] = update.message.text
    try:
        if Globalvariables.add[3]:
            del Globalvariables.add[3]
            database["links_demo"].append(Globalvariables.add)
            Globalvariables.add = ["DEMO"]
    except IndexError:
        database["links"].append(Globalvariables.add)
        Globalvariables.add = []
    update.message.reply_text("The description is <b>{}</b>. Lets head over to keywords, send me one."
                              .format(update.message.text), parse_mode=ParseMode.HTML)
    return KEYWORDS


def add_keyword(_, update):
    messages = ["No one will see this. Sad story. Moving on",
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


def finish(bot, update):
    try:
        if Globalvariables.add[0] == "DEMO":
            del Globalvariables.add[0]
            database["keywords_demo"].append(Globalvariables.add)
    except IndexError:
        database["keywords"].append(Globalvariables.add)
        bot.send_message(-1001374913393,
                         "Added {} to the database from {}, updated GitHub, pardon me for breathing which "
                         "I never do anyway, oh god this is so depressing"
                         .format(database["links"][-1][0],
                                 mention_html(update.effective_user.id, update.effective_user.first_name)),
                         parse_mode=ParseMode.HTML)
        repo = g.get_repo('Poolitzer/gifsupportbot')
        contents = repo.get_contents("database.json", ref="master")
        repo.update_file(contents.path, "Automatically update database", json.dumps(database, indent=4, sort_keys=True),
                         contents.sha)
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
    conv_update_handler = ConversationHandler(
        entry_points=[CommandHandler("update", update_db, Filters.user(tokenbase["ADMINS"]))],

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
        entry_points=[MessageHandler(Filters.user(tokenbase["ADMINS"]) & Filters.animation,
                                     add_db),
                      CommandHandler("start", start_admin, filters=Filters.user(tokenbase["ADMINS"]), pass_args=True),
                      CommandHandler("demo", add_db_demo, filters=Filters.user(tokenbase["ADMINS"]))],
        states={
            GIF: [MessageHandler(Filters.animation, add_gif_demo)],
            QUESTION: [MessageHandler(Filters.text, add_question)],
            DEVICE: [MessageHandler(Filters.text, add_device)],
            LINK: [MessageHandler(Filters.text & Filters.entity(MessageEntity.TEXT_LINK), add_link)],
            CALLBACK: [CallbackQueryHandler(queryhandler)],
            TITEL: [MessageHandler(Filters.text, add_title)],
            DESCRIPTION: [MessageHandler(Filters.text, add_description)],
            KEYWORDS: [MessageHandler(Filters.text, add_keyword), CommandHandler('finish', finish)]
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )
    dp.add_handler(conv_add_handler)
    dp.add_handler(CallbackQueryHandler(vote, pattern="vote"))
    dp.add_handler(CallbackQueryHandler(demovote, pattern="demo"))
    dp.add_handler(InlineQueryHandler(demoinlinequery, pattern="demo"))
    dp.add_handler(InlineQueryHandler(inlinequery))
    dp.add_handler(MessageHandler(Filters.status_update.new_chat_members, new_member))
    dp.add_handler(CommandHandler('LinusIsStupid', linus_is_stupid))
    updater.bot.send_message(-1001214567646, "Not Linus bot online")
    updater.start_polling()


if __name__ == '__main__':
    main()
