from time import sleep

from telegram import Update
from telegram.ext import CommandHandler, CallbackContext

from bot import download_dict, dispatcher, download_dict_lock, DOWNLOAD_DIR
from bot.helper.ext_utils.bot_utils import get_download_by_gid, MirrorStatus
from bot.helper.ext_utils.fs_utils import clean_download
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.message_utils import sendMessage, delete_all_messages


def cancel_mirror(update: Update, context: CallbackContext):
    args = update.message.text.split(" ", maxsplit=1)
    mirror_message = None
    if len(args) > 1:
        gid = args[1]
        dl = get_download_by_gid(gid)
        if not dl:
            sendMessage(f"GID: <code>{gid}</code> not found.", context.bot, update)
            return
        with download_dict_lock:
            keys = list(download_dict.keys())
        mirror_message = dl.message
    elif update.message.reply_to_message:
        mirror_message = update.message.reply_to_message
        with download_dict_lock:
            keys = list(download_dict.keys())
            dl = download_dict[mirror_message.message_id]
    if len(args) == 1:
        if mirror_message is None or mirror_message.message_id not in keys:
            if BotCommands.MirrorCommand in mirror_message.text or \
                    BotCommands.TarMirrorCommand in mirror_message.text:
                msg = "Mirror already have been cancelled"
                sendMessage(msg, context.bot, update)
                return
            else:
                msg = "Please reply to the /mirror message which was used to start the download or /cancel gid to cancel it!"
                sendMessage(msg, context.bot, update)
                return
    if dl.status() == "Uploading":
        sendMessage("Upload in Progress, Don't Cancel it.", context.bot, update)
        return
    elif dl.status() == "Archiving":
        sendMessage("Archival in Progress, Don't Cancel it.", context.bot, update)
        return
    else:
        dl.download().cancel_download()
    sleep(1)  # Wait a Second For Aria2 To free Resources.
    clean_download(f'{DOWNLOAD_DIR}{mirror_message.message_id}/')


def cancel_all(update: Update, context: CallbackContext):
    with download_dict_lock:
        count = 0
        for dlDetails in list(download_dict.values()):
            if dlDetails.status() == MirrorStatus.STATUS_DOWNLOADING \
                    or dlDetails.status() == MirrorStatus.STATUS_WAITING \
                    or dlDetails.status().startswith(MirrorStatus.STATUS_RETRYING):
                dlDetails.download().cancel_download()
                count += 1
    delete_all_messages()
    sendMessage(f'Cancelled {count} downloads!', context.bot, update)


cancel_mirror_handler = CommandHandler(
    BotCommands.CancelMirror, cancel_mirror,
    (CustomFilters.authorized_chat | CustomFilters.authorized_user) & CustomFilters.mirror_owner_filter,
    run_async=True
)
cancel_all_handler = CommandHandler(
    BotCommands.CancelAllCommand, cancel_all,
    CustomFilters.owner_filter,
    run_async=True
)
dispatcher.add_handler(cancel_all_handler)
dispatcher.add_handler(cancel_mirror_handler)
