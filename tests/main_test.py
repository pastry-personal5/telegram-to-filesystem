import unittest
from unittest.mock import AsyncMock, MagicMock, patch
import logging
from loguru import logger
import os

from main import CustomHandler
import main


class TestCustomHandler(unittest.TestCase):

    def setUp(self):
        """Set up mock configuration and initialize CustomHandler."""
        self.mock_global_config = {
            'output_dirpath_list': [{'path': '/mock/output'}],
            'bot_token': 'fake_bot_token'
        }
        self.handler = CustomHandler(self.mock_global_config)

    def test_get_base_dirpath(self):
        """Test the _get_base_dirpath method."""
        base_dirpath = self.handler._get_base_dirpath()
        self.assertEqual(base_dirpath, '/mock/output')

    def test_get_last_part_of_url_valid(self):
        """Test _get_last_part_of_url with a valid URL."""
        url = "http://example.com/path/to/resource.jpg"
        result = self.handler._get_last_part_of_url(url)
        self.assertEqual(result, "resource.jpg")

    def test_get_last_part_of_url_invalid(self):
        """Test _get_last_part_of_url with an invalid URL."""
        url = ""
        result = self.handler._get_last_part_of_url(url)
        self.assertIsNone(result)

    @patch('os.path.sep', '/')
    @patch('builtins.open', new_callable=MagicMock)
    async def test_on_photo_message_success(self, mock_open):
        """Test on_photo_message with valid input."""
        # Mock Telegram update and context
        mock_update = AsyncMock()
        mock_update.effective_chat.id = 12345
        mock_update.message.photo = [
            MagicMock(file_id="file1"),
            MagicMock(file_id="file2"),
            MagicMock(file_id="file3")  # Mock the largest photo
        ]
        mock_context = AsyncMock()
        mock_context.bot.get_file.return_value = AsyncMock(
            file_path="http://example.com/path/to/file.jpg",
            download_as_bytearray=AsyncMock(return_value=b"fake_image_content")
        )

        # Call on_photo_message
        await self.handler.on_photo_message(mock_update, mock_context)

        # Assertions
        mock_context.bot.get_file.assert_called_once_with("file3")
        mock_context.bot.get_file.return_value.download_as_bytearray.assert_called_once()
        mock_open.assert_called_once_with('/mock/output/file.jpg', 'wb')
        mock_open().write.assert_called_once_with(b"fake_image_content")
        mock_update.message.reply_text.assert_called_once_with("Image received.")

    @patch('builtins.open', side_effect=IOError("File write error"))
    async def test_on_photo_message_ioerror(self, mock_open):
        """Test on_photo_message handling an IOError."""
        # Mock Telegram update and context
        mock_update = AsyncMock()
        mock_update.effective_chat.id = 12345
        mock_update.message.photo = [MagicMock(file_id="file1")]
        mock_context = AsyncMock()
        mock_context.bot.get_file.return_value = AsyncMock(
            file_path="http://example.com/path/to/file.jpg",
            download_as_bytearray=AsyncMock(return_value=b"fake_image_content")
        )

        # Call on_photo_message
        with self.assertLogs('loguru.logger', level='ERROR') as cm:
            await self.handler.on_photo_message(mock_update, mock_context)

        # Assertions
        self.assertIn("An IO error has been occurred", cm.output[-1])
        mock_open.assert_called_once()

    @patch('loguru.logger.error')
    async def test_on_photo_message_no_file_path(self, mock_error):
        """Test on_photo_message when file_path is missing."""
        # Mock Telegram update and context
        mock_update = AsyncMock()
        mock_update.effective_chat.id = 12345
        mock_update.message.photo = [MagicMock(file_id="file1")]
        mock_context = AsyncMock()
        mock_context.bot.get_file.return_value = AsyncMock(
            file_path=None,
            download_as_bytearray=AsyncMock(return_value=b"fake_image_content")
        )

        # Call on_photo_message
        await self.handler.on_photo_message(mock_update, mock_context)

        # Assertions
        mock_error.assert_called_with('A file path is not given with a file. File ID was (file1).')
        mock_update.message.reply_text.assert_not_called()


if __name__ == '__main__':
    unittest.main()
