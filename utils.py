from constants import LOG_CHANNEL_ID, ARTICLE_URL
from telegram import ParseMode
from telegram.utils.helpers import mention_html


def build_menu(buttons, n_cols, header_buttons=None, footer_buttons=None):
    menu = [buttons[i:i + n_cols] for i in range(0, len(buttons), n_cols)]
    if header_buttons:
        menu.insert(0, header_buttons)
    if footer_buttons:
        menu.append(footer_buttons)
    return menu


def log_action(context, first_name, user_id, recorded_gif_id="", edited_gif_id="", file_id="", category="",
               subcategory_id="", created_sub=None, gif_to_sub=None, titles=None, description=None, links=None,
               deleted_keyword="", new_keyword="", edit_sub_gif=None, new_person=None, new_position=None,
               removed_person=None, title=""):
    body = f"{mention_html(int(user_id), first_name)} (#tq{user_id}) "
    if recorded_gif_id:
        body += f"<b>added a GIF.</b>\n\nId: #{recorded_gif_id}"
    elif edited_gif_id:
        body += f"<b>edited a GIF.</b>\n\nId: #{edited_gif_id}"
    elif created_sub:
        if not created_sub['help_link']:
            created_sub['help_link'] = "None"
        body += f"<b>created a subcategory.</b>\n\n<i>Category:</i> {category}\n<i>Title:</i> {created_sub['title']}\n"\
            f"<i>Description:</i> {created_sub['description']}\n<i>Help Link:</i> {created_sub['help_link']}\n" \
            f"<i>Keywords:</i> {', '.join(created_sub['keywords'])}\n\nSub Id: #{subcategory_id}"
    # this works because I dont pass it in the creation of a sub.
    elif gif_to_sub:
        body += f"<b>added a GIF to a subcategory.</b>\n\nGIF Id: #{gif_to_sub}"
    elif titles:
        body += f"<b>changed the title</b> from <i>{titles['old_title']}</i> to <i>{titles['new_title']}</i>."
    elif description:
        body += f"<b>changed the description</b> from <i>{description['old_description']}</i> to " \
            f"<i>{description['new_description']}</i>."
    elif links:
        if not links['old_link']:
            links['old_link'] = "None"
        if not links['new_link']:
            links['new_link'] = "None"
        body += f"<b>changed the Help Link</b> from <i>{links['old_link']}</i> to <i>{links['new_link']}</i>."
    elif deleted_keyword:
        body += f"<b>deleted the keyword</b> <i>{deleted_keyword}</i> from a sub."
    elif new_keyword:
        body += f"<b>added the keyword</b> <i>{new_keyword}</i> to a sub."
    elif edit_sub_gif:
        body += f"<b>changed the GIF of a sub.</b> Follow the GIF Id to see the old one directly:" \
                f"\n\nGIF Id: #{edit_sub_gif}"
    elif new_person:
        body += f"<b>has joined the team!</b>"
    elif new_position:
        body += f"<b>got himself the following position(s):</b> {', '.join(new_position)}"
    elif removed_person:
        body += f"<b>is removed from the project</b>"
    elif title:
        body += f"<b>added the title {title}.</b>"
    if not created_sub and category:
        body += f"\n\nCategory: <i>{category}</i>\nId: #{subcategory_id}"
    if file_id:
        context.bot.send_document(LOG_CHANNEL_ID, file_id, caption=body, disable_notification=True,
                                  parse_mode=ParseMode.HTML)
    else:
        context.bot.send_message(LOG_CHANNEL_ID, body, disable_notification=True, parse_mode=ParseMode.HTML)


def create_caption(title, device, help_link=""):
    # maybe we have to do more later if issues with the URL (id, anchor) appear
    url_anchor = "#" + title.replace(" ", "-")
    caption = f"{title}\n\n#{device} #gifsupport\n\n<a href=\"{ARTICLE_URL + url_anchor}\">More info</a>"
    if help_link:
        caption += f"    <a href=\"{help_link}\">More help</a>"
    return caption
