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

            # Create a valid partner to satisfy the FK constraint,
            # then assign its ID to the website visitor.
            partner = self.env['res.partner'].sudo().create({
                'name': 'Test Partner',
            })

            # Create test visitor with proper fields using a numeric access_token
            token = str(int.from_bytes(os.urandom(4), 'big') % 2147483647)
            self.visitor = self.env['website.visitor'].sudo().with_context(tracking_disable=True).create({
                'access_token': token,
                'lang_id': self.env.ref('base.lang_en').id,
                'website_id': website.id,
                'partner_id': partner.id,
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
                # Force re-computation while still in the patch context.
                message._compute_response()
                self.env.invalidate_all()
                return message
        except Exception as e:
            _logger.error("Message creation failed: %s", str(e))
            raise

    @patch('odoo.addons.website_custom_chatbot.models.chatbot_message.os.path.exists')
    @patch('builtins.open', new_callable=mock_open)
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

    def test_exact_topic_match_without_answer(self):
        """Test exact topic match when no dataset entry contains the topic in its answer"""
        # Patch _load_dataset to return a dataset without matching answer in any entry
        dataset = [{
            "topic": "CraftEd ERP",
            "questions": ["What is CraftEd ERP?", "Tell me about ERP"],
            "answer": "Information not available."
        }]
        with patch('odoo.addons.website_custom_chatbot.models.chatbot_message.ChatbotMessage._load_dataset', return_value=dataset):
            message = self.ChatbotMessage.with_context(tracking_disable=True).create({
                'request': "CraftEd ERP",
                'visitor_id': self.visitor.id
            })
            message._compute_response()
            self.assertIn("Sorry, I couldn't find any information on", message.response)
            options = message.options
            self.assertIsNotNone(options)
            self.assertIsInstance(json.loads(options), list)

    def test_question_exception_handling(self):
        """Test that an exception in the question matching branch is handled gracefully"""
        # Create dataset with a non-string question to force exception when calling lower()
        dataset = [{
            "topic": "CraftEd ERP",
            "questions": [None, "Tell me about ERP"],
            "answer": "CraftEd ERP answer."
        }]
        with patch('odoo.addons.website_custom_chatbot.models.chatbot_message.ChatbotMessage._load_dataset', return_value=dataset):
            message = self.ChatbotMessage.with_context(tracking_disable=True).create({
                'request': "tell me about erp",
                'visitor_id': self.visitor.id
            })
            message._compute_response()
            # Should return the valid answer from question matching despite exception in the first question
            self.assertEqual(message.response, "CraftEd ERP answer.")
            # As the field might be stored as a falsy value, use assertFalse instead of assertIsNone.
            self.assertFalse(message.options)

    def test_invalid_partner_creates_guest_partner(self):
        """Test that an invalid partner_id (non-existent record) gets replaced by a Guest Partner"""
        # 1. Create a real partner and assign it to the visitor
        test_partner = self.env['res.partner'].sudo().create({'name': 'Test Partner'})
        self.visitor.write({'partner_id': test_partner.id})
        # 2. Delete the partner to simulate non-existence
        test_partner.unlink()
        # 3. Verify that the visitor's partner does not exist
        self.assertFalse(self.visitor.partner_id.exists())
        # 4. Create a message to trigger _compute_response which should create a new Guest Partner
        message = self._create_test_message("What is CraftEd ERP?")
        self.assertNotEqual(message.visitor_id.partner_id.name, "Test Partner")
        self.assertEqual(message.visitor_id.partner_id.name, "Guest Partner")