from constants import RECORDED_CHANNEL_ID, EDITED_CHANNEL_ID
from database import database


def bump_recorded(context):
    message = context.bot.send_message(RECORDED_CHANNEL_ID, "#bump", reply_to_message_id=context.job.context)
    database.insert_gif_recorded_bump(context.job.name, message.message_id)


def bump_edited(context):
    message = context.bot.send_message(EDITED_CHANNEL_ID, "#bump", reply_to_message_id=context.job.context)
    database.insert_gif_edited_bump(context.job.name, message.message_id)
