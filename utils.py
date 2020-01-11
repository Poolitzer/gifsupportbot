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


def log_action(context, first_name, user_id, recorded_gif_id="", edited_gif_id="", file_id="", category_path="",
               subcategory_id="", created_sub=None, gif_to_sub=None, description=None, links=None,
               deleted_keyword="", new_keyword="", edit_sub_gif=None, new_person=None, new_position=None,
               removed_person=None, returned_to_recorder=None, returned_to_editor=None, new_category=None,
               rename_category=None, delete_category=None):
    body = f"{mention_html(int(user_id), first_name)} (#tq{user_id}) "
    if recorded_gif_id:
        body += f"<b>added a GIF.</b>\n\nId: #{recorded_gif_id}"
    elif edited_gif_id:
        body += f"<b>edited a GIF.</b>\n\nId: #{edited_gif_id}"
    elif created_sub:
        if not created_sub['help_link']:
            created_sub['help_link'] = "None"
        body += f"<b>created a subcategory.</b>\n\n<i>Category:</i> {category_path}\n<i>Title:</i> " \
                f"{category_path.split('.')[-1]}\n<i>Description:</i> {created_sub['description']}\n<" \
                f"i>Help Link:</i> {created_sub['help_link']}\n<i>Keywords:</i> {', '.join(created_sub['keywords'])}" \
                f"\n\nSub Id: #{subcategory_id}"
    # this works because I dont pass it in the creation of a sub.
    elif gif_to_sub:
        body += f"<b>added a GIF to a subcategory.</b>\n\nGIF Id: #{gif_to_sub}"
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
    elif returned_to_recorder:
        body += f"<b>returned a GIF to the recorders (last time you see this ID).</b>" \
                f"\n\nGIF Id: #{returned_to_recorder}."
    elif returned_to_editor:
        body += f"<b>returned a GIF to the editors.</b>\n\nGIF Id: #{returned_to_editor}."
    elif new_category:
        body += f"<b>created a category.</b> Category path: <i>{new_category}</i>"
    elif rename_category:
        body += f"<b>renamed a category.</b> Category path: <i>{rename_category[0]}</i> > <i>{rename_category[1]}</i>" \
                f". {rename_category[2]} categories have been changed"
    elif delete_category:
        body += f"<b>deleted a category.</b> Category path: <i>{delete_category['path']}</i>. This means these GIFs " \
                f"are now gone: {', '.join(delete_category['categories'])}"
    if not created_sub and category_path:
        body += f"\n\nCategory path: <i>{category_path}</i>\nId: #{subcategory_id}"
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
