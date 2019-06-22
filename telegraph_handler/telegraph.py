from tokens import telegraphtoken
import requests as r
from constants import ARTICLE_APPEND, ARTICLE_PREPEND
from telegraph_handler.utils import menu_generator, main_content_generator
from datetime import datetime
import json
import logging

logger = logging.getLogger(__name__)


def update_page():
    menu = menu_generator()
    main_content = main_content_generator()
    time = datetime.now().strftime("%d/%m/%y")
    ARTICLE_APPEND[2]["children"][0] = ARTICLE_APPEND[2]["children"][0].format(time)
    content = ARTICLE_PREPEND + menu + main_content + menu + ARTICLE_APPEND
    stuff = {"access_token": telegraphtoken, "title": "Test", "content": json.dumps(content)}
    request = r.post("https://api.telegra.ph/editPage/test-05-27-72", data=stuff)
    if request.status_code == 200:
        if request.json()["ok"]:
            pass
        else:
            logger.error(f"Telegraph returned a false error: {request.json()}")
    else:
        logger.error(f"Telegraph returned a non 200 code: {request.status_code} + {request.content}")
