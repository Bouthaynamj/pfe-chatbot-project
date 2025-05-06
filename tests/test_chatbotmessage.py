from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError
import json
import os
import logging
from unittest.mock import patch, mock_open

_logger = logging.getLogger(__name__)

class TestChatbotMessage(TransactionCase):
    
    def setUp(self):
        super(TestChatbotMessage, self).setUp()
        try:
            # Initialize test environment with proper mocking
            self.ChatbotMessage = self.env['chatbot.message'].sudo()
            
            # Create test website if not exists
            website = self.env['website'].sudo().with_context(tracking_disable=True).create({
                'name': 'Test Website'
            })
            
            # Create test visitor with proper fields
            self.visitor = self.env['website.visitor'].sudo().with_context(tracking_disable=True).create({
                'access_token': 'test_token_' + os.urandom(8).hex(),
                'lang_id': self.env.ref('base.lang_en').id,
                'website_id': website.id,
                'access_token': 'test_' + os.urandom(8).hex()  # Ensure unique token
            })
            
            # Define test dataset that matches your JSON structure
            self.test_dataset = [{
                "topic": "CraftEd ERP",
                "questions": ["What is CraftEd ERP?", "Tell me about ERP"],
                "answer": "CraftEd ERP is an enterprise resource planning system designed for educational institutions."
            }]
        except Exception as e:
            _logger.error("Setup failed: %s", str(e))
            raise

    def tearDown(self):
        """Clean up after each test"""
        try:
            # Clean up test records
            self.ChatbotMessage.search([]).unlink()
            super(TestChatbotMessage, self).tearDown()
        except Exception as e:
            _logger.error("Teardown failed: %s", str(e))
            raise

    def _create_test_message(self, request_text='', with_dataset=True):
        """Helper method to create test messages"""
        try:
            with patch('odoo.addons.website_custom_chatbot.models.chatbot_message.ChatbotMessage._load_dataset') as mock_load:
                mock_load.return_value = self.test_dataset if with_dataset else {"error": "Test error"}
                
                message = self.ChatbotMessage.with_context(tracking_disable=True).create({
                    'request': request_text,
                    'visitor_id': self.visitor.id
                })
                return message
        except Exception as e:
            _logger.error("Message creation failed: %s", str(e))
            raise

    @patch('odoo.addons.website_custom_chatbot.models.chatbot_message.os.path.exists')
    @patch('builtins.open', new_callable=mock_open)  # Changed to patch builtins.open directly
    def test_load_dataset_success(self, mock_file, mock_exists):
        """Test successful dataset loading"""
        try:
            mock_exists.return_value = True
            mock_file.return_value.read.return_value = json.dumps(self.test_dataset)
            
            result = self.ChatbotMessage._load_dataset()
            self.assertEqual(result, self.test_dataset)
        except Exception as e:
            _logger.error("Dataset loading test failed: %s", str(e))
            self.fail(f"Dataset loading test failed: {str(e)}")

    def test_create_message_with_request(self):
        """Test creating a message with a request"""
        message = self._create_test_message('What is CraftEd ERP?')
        self.assertEqual(message.request, 'What is CraftEd ERP?')
        self.assertEqual(message.visitor_id.id, self.visitor.id)

    def test_process_user_message_empty(self):
        """Test processing empty message"""
        try:
            result = self.ChatbotMessage._process_user_message("", self.test_dataset)
            self.assertEqual(result.get('message'), "Please provide a valid message.")
            self.assertIsNone(result.get('options'))
        except Exception as e:
            _logger.error("Empty message test failed: %s", str(e))
            raise

    def test_process_user_message_greeting(self):
        """Test processing greeting message"""
        try:
            result = self.ChatbotMessage._process_user_message("hi", self.test_dataset)
            self.assertEqual(result.get('message'), "Hello, here are some topics you can ask about:")
            options = result.get('options')
            self.assertIsNotNone(options)
            self.assertIsInstance(json.loads(options), list)
        except Exception as e:
            _logger.error("Greeting test failed: %s", str(e))
            raise

    def test_compute_response_with_request(self):
        """Test compute_response with valid request"""
        message = self._create_test_message('crafted erp')
        self.assertTrue("enterprise resource planning" in message.response.lower())

    def test_compute_response_dataset_error(self):
        """Test compute_response when dataset loading fails"""
        message = self._create_test_message('test', with_dataset=False)
        self.assertEqual(
            message.response,
            "I'm having trouble accessing my knowledge base. Please try again later."
        )

    def test_compute_response_no_request(self):
        """Test compute_response with no request"""
        message = self._create_test_message('')
        self.assertEqual(message.response, "Please provide a valid message.")