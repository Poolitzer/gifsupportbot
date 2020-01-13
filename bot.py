import logging
from telegram.ext import (Updater, CallbackQueryHandler, ConversationHandler, CommandHandler,
                          MessageHandler, InlineQueryHandler, Filters, PicklePersistence)
from tokens import bottoken
from general_handlers import general
from conversation_handlers import (start_handler, add_gif_handler, edit_gif_handler, manage_gif_handler,
                                   manage_categories_handler, update_subcategory_handler)
from inline_handler.inline import inline
from job_handlers import database_dump, online_ping, job_persistent
from constants import ADMINS

import datetime

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO, filename="log.log")


def main():
    my_persistence = PicklePersistence(filename='pickle_file')
    # since we are facing timeout error, I will keep increasing those until they are done
    updater = Updater(token=bottoken, persistence=my_persistence, use_context=True,
                      request_kwargs={'read_timeout': 10, 'connect_timeout': 10})
    dp = updater.dispatcher
    new_person_handler = MessageHandler(Filters.status_update.new_chat_members, general.new_person)
    dp.add_handler(new_person_handler)
    # conversation to add GIFs from an recorder
    conversation_handler = ConversationHandler(
        entry_points=[CommandHandler("add", add_gif_handler.add_command, filters=Filters.private)],
        states={
            add_gif_handler.GIF_DEVICE: [CallbackQueryHandler(add_gif_handler.add_device, pattern="record_device"),
                                         CallbackQueryHandler(add_gif_handler.add_user_device,
                                                              pattern="update_device")],
            add_gif_handler.DEVICE: [CallbackQueryHandler(add_gif_handler.device, pattern="user_devices"),
                                     CallbackQueryHandler(add_gif_handler.finish, pattern="finish")],
            add_gif_handler.GET_CATEGORY: [MessageHandler(Filters.text, add_gif_handler.add_category)],
            add_gif_handler.NEW_GIF: [MessageHandler(Filters.document, add_gif_handler.add_gif)]
        },
        fallbacks=[CommandHandler('cancel', add_gif_handler.cancel)], persistent=True, name="add_gif_handler")
    dp.add_handler(conversation_handler)
    # conversation to edit GIFs
    # not in conversation cause chat restriction
    initial_add_handler = CommandHandler("start", edit_gif_handler.edit_what, Filters.regex("edit"))
    dp.add_handler(initial_add_handler)
    conversation_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(edit_gif_handler.proceed, pattern="record_yes"),
                      CallbackQueryHandler(edit_gif_handler.abort, pattern="record_no")],
        states={
            edit_gif_handler.EDITED: [MessageHandler(Filters.animation, edit_gif_handler.add_edited)],
            edit_gif_handler.NOTE: [MessageHandler(Filters.text, edit_gif_handler.notify_recorder)],
            ConversationHandler.TIMEOUT: [MessageHandler(Filters.all, edit_gif_handler.two_hours_timer)]
        },
        fallbacks=[CommandHandler('cancel', edit_gif_handler.cancel)], conversation_timeout=2 * 60 * 60,
        persistent=True, name="edit_gif_handler"
        )
    dp.add_handler(conversation_handler)
    # conversation to manage edited GIFs
    # not in conversation cause chat restriction
    initial_add_handler = CommandHandler("start", manage_gif_handler.manage_what, Filters.regex("manage"))
    dp.add_handler(initial_add_handler)
    conversation_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(manage_gif_handler.proceed, pattern="is_edit_yes"),
                      CallbackQueryHandler(manage_gif_handler.abort, pattern="is_edit_no")],
        states={
            manage_gif_handler.NEW_DESCRIPTION: [MessageHandler(Filters.text, manage_gif_handler.new_description)],
            manage_gif_handler.HELP_URL: [MessageHandler((Filters.text & (Filters.entity("url") |
                                                         Filters.entity("text_link"))),  manage_gif_handler.add_url),
                                          CommandHandler("skip", manage_gif_handler.skip_url)],
            manage_gif_handler.KEYWORD: [MessageHandler(Filters.text, manage_gif_handler.add_keyword),
                                         CommandHandler("finish", manage_gif_handler.finish_keywords)],
            manage_gif_handler.EDIT_FIX: [CallbackQueryHandler(manage_gif_handler.edit_fix, pattern="ed_fix_yes"),
                                          CallbackQueryHandler(manage_gif_handler.record_fix, pattern="ed_fix_no")],
            manage_gif_handler.NOTE_RECORD: [MessageHandler(Filters.text, manage_gif_handler.notify_recorder)],
            manage_gif_handler.NOTE_EDIT: [MessageHandler(Filters.text, manage_gif_handler.notify_editor)],
            ConversationHandler.TIMEOUT: [MessageHandler(Filters.all, manage_gif_handler.two_hours_timer),
                                          CallbackQueryHandler(manage_gif_handler.two_hours_timer)]
        },
        fallbacks=[CommandHandler('cancel', manage_gif_handler.cancel)], conversation_timeout=2 * 60 * 60,
        persistent=True, name="manage_gif_handler"
    )
    dp.add_handler(conversation_handler)
    # conversation to update added GIFs/subcategories
    conv_add_handler = ConversationHandler(
        entry_points=[CommandHandler("manage", update_subcategory_handler.start)],
        states={
            update_subcategory_handler.CATEGORY: [MessageHandler(Filters.text, update_subcategory_handler.subcategory)],
            update_subcategory_handler.WHAT: [MessageHandler(Filters.regex("Description"),
                                                             update_subcategory_handler.update_description),
                                              MessageHandler(Filters.regex("Help Link"),
                                                             update_subcategory_handler.update_link),
                                              MessageHandler(Filters.regex("Keywords"),
                                                             update_subcategory_handler.update_keywords),
                                              MessageHandler(Filters.regex("GIF"),
                                                             update_subcategory_handler.update_gif)
                                              ],
            # description
            update_subcategory_handler.UPDATE_DESCRIPTION: [
                MessageHandler(Filters.text, update_subcategory_handler.returned_description)],
            # help_link
            update_subcategory_handler.UPDATE_LINK: [MessageHandler((Filters.text & (Filters.entity("url") |
                                                                                     Filters.entity("text_link"))),
                                                                    update_subcategory_handler.returned_link),
                                                     CommandHandler("none",
                                                                    update_subcategory_handler.returned_link_none)],
            # keyword
            update_subcategory_handler.KEYWORD: [CallbackQueryHandler(update_subcategory_handler.returned_keyword,
                                                                      pattern="keyword"),
                                                 MessageHandler(Filters.text, update_subcategory_handler.new_keyword)],
            # gif
            update_subcategory_handler.DEVICE: [CallbackQueryHandler(update_subcategory_handler.returned_device,
                                                                     pattern="device")],
            update_subcategory_handler.GIF: [MessageHandler(Filters.animation, update_subcategory_handler.returned_gif)]
        },
        fallbacks=[CommandHandler('cancel', update_subcategory_handler.cancel)],
        persistent=True, name="update_sub_handler"
    )
    dp.add_handler(conv_add_handler)
    # general start handler
    conversation_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start_handler.start, filters=Filters.private)],
        states={
            start_handler.POSITION: [MessageHandler(Filters.text, start_handler.position)],
            start_handler.DEVICE: [CallbackQueryHandler(start_handler.device, pattern="user_devices"),
                                   CallbackQueryHandler(start_handler.finish, pattern="finish")]
        },
        fallbacks=[CommandHandler('cancel', start_handler.cancel)], persistent=True, name="start_handler",
        allow_reentry=True)
    dp.add_handler(conversation_handler)
    # manage categories
    dp.add_handler(CommandHandler("help_manage", manage_categories_handler.manage))
    dp.add_handler(CommandHandler("mc", manage_categories_handler.new_category, filters=Filters.private))
    dp.add_handler(CommandHandler("rc", manage_categories_handler.rename_category, filters=Filters.private))
    dp.add_handler(CommandHandler("dc", manage_categories_handler.delete_category_question, filters=Filters.private))
    dp.add_handler(CommandHandler("yes", manage_categories_handler.delete_category, filters=Filters.private))
    dp.add_handler(CommandHandler("tree", manage_categories_handler.tree, filters=Filters.private))
    # relatively smart general cancel handler
    dp.add_handler(CommandHandler("cancel", general.cancel))
    # help handler, displays a help message
    dp.add_handler(CommandHandler("help", general.helping))
    # manual add users to the database handler stuff
    dp.add_handler(CommandHandler("add_person", general.new_person_manual,
                                  Filters.user(user_id=ADMINS)))
    # remove users from the database
    dp.add_handler(CommandHandler("goaway", general.delete_person,
                                  Filters.user(user_id=ADMINS)))
    dp.add_handler(InlineQueryHandler(inline))
    dp.add_error_handler(general.error)
    job_queue = updater.job_queue
    job_queue.run_daily(database_dump.dump, datetime.time(0, 0, 0))
    job_queue.run_repeating(online_ping.ping, 10*60, first=0, name="ping")
    job_queue.run_repeating(job_persistent.save_jobs_job, datetime.timedelta(minutes=1))

    try:
        job_persistent.load_jobs(job_queue)

    except FileNotFoundError:
        # First run
        pass
    updater.start_polling()
    updater.idle()
    job_persistent.save_jobs(job_queue)


if __name__ == '__main__':
    main()
