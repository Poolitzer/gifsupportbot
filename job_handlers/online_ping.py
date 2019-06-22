from constants import PING_CHANNEL_ID


def ping(context):
    context.bot.send_message(PING_CHANNEL_ID, "..ping", disable_notification=True)
