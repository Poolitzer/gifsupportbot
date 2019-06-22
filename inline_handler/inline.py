import re
from constants import DEVICES, POST_CHANNEL_LINK
from database import database
from uuid import uuid4
from telegram import InlineQueryResultArticle, InputTextMessageContent, ParseMode


def inline(update, _):
    query = update.inline_query.query
    """ Removed cause no use currently, kept cause its cool and I maybe want to change this later
    # check if a category is given
    category = None
    for real_category in CATEGORIES:
        payload = re.findall(rf"{real_category}", query, re.IGNORECASE)
        if payload:
            category = real_category
            break
    """
    # check if a device is given
    device = None
    # user friendly devices
    devices = ["Android X", "android", "ios", "windows phone", "desktop", "macos", "web"]
    for real_device in devices:
        payload = re.findall(rf"{real_device.replace('_', ' ')}", query, re.IGNORECASE)
        if payload:
            # translate back to database friendly ones
            if real_device == "Android X":
                real_device = "android_x"
            elif real_device == "windows phone":
                real_device = "windows_phone"
            elif real_device == "desktop":
                real_device = "tdesktop"
            elif real_device == "macos":
                real_device = "macos_native"
            device = real_device
            query = query.replace(payload[0], '')
            break
    query = query.replace(' ', '')
    query = query.lower()
    words = query.split(' ')
    results = []
    # if device, we only get subs with those device, else we got everything and filter
    if device:
        subs = database.get_subcategories_device(device)
    else:
        subs = database.get_all_subcategories()
    for sub in subs:
        # test if title matches somehow
        if sub['title'].lower().startswith(query):
            # this shouldn't happen, but am I one for taking chances?
            content = content_creator(device, sub)
            for device in content:
                results.append(InlineQueryResultArticle(id=uuid4(), title=sub['title'],
                                                        input_message_content=content[device],
                                                        description=f"{sub['description']} - {device}"))
            if len(results) == 10:
                update.inline_query.answer(results)
                return
        # test if keyword matches somehow
        else:
            for word in words:
                done = False
                for keyword in sub["keywords"]:
                    if keyword.lower().startswith(word):
                        content = content_creator(device, sub)
                        for device in content:
                            results.append(InlineQueryResultArticle(id=uuid4(), title=sub['title'],
                                                                    input_message_content=content[device],
                                                                    description=f"{sub['description']} - {device}"))
                        if len(results) == 10:
                            update.inline_query.answer(results)
                            return
                        done = True
                        break
                if done:
                    break
    update.inline_query.answer(results, cache_time=0)


def content_creator(device, sub):
    content = {}
    if device:
        link = f"<a href=\"{POST_CHANNEL_LINK}/{sub['devices'][device]['message_id']}\">{sub['title']}</a>"
        content[device] = InputTextMessageContent(link, ParseMode.HTML)
    else:
        for device in DEVICES:
            if sub["devices"][device]["message_id"]:
                link = f"<a href=\"{POST_CHANNEL_LINK}/{sub['devices'][device]['message_id']}\">" \
                    f"{sub['title']}</a>"
                content[device] = InputTextMessageContent(link, ParseMode.HTML)
    return content
