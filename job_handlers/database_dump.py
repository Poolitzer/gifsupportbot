import subprocess
from constants import DATABASE_DUMP_CHANNEL_ID
import io
from datetime import datetime


def dump(context):
    run = subprocess.run(["mongodump", "-dgifsupportbot", "--gzip", "--archive"], capture_output=True)
    output = io.BytesIO(run.stdout)
    time = datetime.now().strftime("%d-%m-%Y")
    context.bot.send_document(DATABASE_DUMP_CHANNEL_ID, output, filename=f"{time}.archive.gz")
    context.bot.send_document(DATABASE_DUMP_CHANNEL_ID, open("./categories.json", "rb"))
