import logging
import os
import pprint

from loguru import logger
from telegram import Update
from telegram.ext import filters, MessageHandler, ApplicationBuilder, CommandHandler, ContextTypes
import yaml
try:
    from yaml import CLoader as Loader
except ImportError:
    from yaml import Loader


class InterceptHandler(logging.Handler):
    """Custom handler to redirect standard logging to Loguru."""
    def emit(self, record):
        # Get the corresponding Loguru level for the logging level
        level = logger.level(record.levelname).name if record.levelname in logger._core.levels else record.levelno
        # Use Loguru's logger to log the message
        logger.opt(depth=6, exception=record.exc_info).log(level, record.getMessage())


def redirect_standard_logging_to_loguru():
    """
    Configure the root logger to use Loguru
    Redirect python standard logging messages to loguru.
    """
    # Remove default handlers
    logging.root.handlers.clear()
    # Add custom handler
    logging.root.addHandler(InterceptHandler())
    # Set a default logging level (optional, Loguru handles its own filtering)
    logging.root.setLevel(logging.INFO)


class CustomHandler:

    def __init__(self, global_config):
        self.global_config = global_config

    async def on_photo_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        logger.info(f'update.effective_chat.id({update.effective_chat.id})')
        logger.info(pprint.pformat(update))
        logger.info(pprint.pformat(update.message.photo))
        biggest_photo = update.message.photo[-1]
        file_id = biggest_photo.file_id
        file_obj = await context.bot.get_file(file_id)
        file_content = await file_obj.download_as_bytearray()
        logger.info(pprint.pformat(file_id))
        logger.info(pprint.pformat(file_obj))

        if not file_obj.file_path or len(file_obj.file_path) <= 0:
            logger.error(f'A file path is not given with a file. File ID was ({file_id}).')
            return

        partial_output_file_path = self._get_last_part_of_url(file_obj.file_path)
        if not partial_output_file_path:
            logger.error(f'A file path is not valid. File ID was ({file_id}). File path was ({file_obj.file_path})')
            return

        base_dirpath = self._get_base_dirpath()
        full_output_file_path = f'{base_dirpath}{os.path.sep}{partial_output_file_path}'

        logger.info(f'Saving to ({full_output_file_path})...')
        try:
            fp = open(full_output_file_path, 'wb')
            fp.write(file_content)
            fp.close()
        except IOError as e:
            logger.error(f'An IO error has been occurred with filepath({full_output_file_path}).')
            logger.error(e)

        await update.message.reply_text("Image received.")

    def _get_base_dirpath(self):
        global_config = self.global_config
        the_first_dirpath = global_config['output_dirpath_list'][0]['path']
        return the_first_dirpath

    def _get_last_part_of_url(self, url) -> str:
        """
        Extracts the last part of a URL after splitting by '/'.
        @author: chatgpt-4

        :param url: The input URL as a string.
        :return: The last part of the URL.
        """
        if not url:
            return None

        # Split the URL by '/' and filter out empty parts
        parts = [part for part in url.split('/') if part]
        return parts[-1] if parts else None


def run_main_loop(global_config) -> None:
    bot_token = global_config['bot_token']
    application = ApplicationBuilder().token(bot_token).build()
    custom_handler = CustomHandler(global_config)
    photo_message_handler = MessageHandler(filters.PHOTO & (~filters.COMMAND), custom_handler.on_photo_message)
    application.add_handler(photo_message_handler)

    application.run_polling()


def read_global_config() -> dict:
    """Read a global configuration.
    """
    config_file_name = './main_config.yaml'
    try:
        f = open(config_file_name, 'r', encoding='utf-8')
        user_config = yaml.load(f.read(), Loader=Loader)
    except IOError:
        logger.error(f'Could not read file: {config_file_name}')
        return {}
    return user_config


def main() -> None:
    redirect_standard_logging_to_loguru()
    global_config = read_global_config()
    if len(global_config) <= 0:
        return
    run_main_loop(global_config)


if __name__ == "__main__":
    main()
