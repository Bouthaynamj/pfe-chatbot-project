from odoo import models, fields, api
import json
import os
import logging
import uuid
from difflib import SequenceMatcher

_logger = logging.getLogger(__name__)

class ChatbotMessage(models.TransientModel):  
    _name = 'chatbot.message'
    _description = 'Chatbot Message'

    # Fields
    request = fields.Text(string='Request', required=True)  
    response = fields.Text(string='Response', compute='_compute_response', precompute=True, store=True)
    session_id = fields.Char(string='Session ID', readonly=True)
    visitor_id = fields.Many2one('website.visitor', string='Visitor', readonly=True)  
    user_id = fields.Many2one(
        'res.users', 
        string='User', 
        readonly=True,
        default=lambda self: self.env.user.id
    )

    @api.model
    def get_visitor_from_request(self):
        """Get or create a visitor ID for the chatbot session"""
        try:
            visitor = self.env['website.visitor'].sudo()._get_visitor_from_request()
            if visitor:
                return {'visitor_id': str(visitor.id)}
            else:
                # Create a random ID if no visitor record exists
                return {'visitor_id': str(uuid.uuid4())}
        except Exception as e:
            _logger.error("Error getting visitor: %s", str(e))
            return {'visitor_id': 'local_' + str(uuid.uuid4())}

    @api.model
    def create(self, vals):
        """Override create to handle additional logic if necessary."""
        return super(ChatbotMessage, self).create(vals)

    @api.depends('request')
    def _compute_response(self):
        for record in self:
            if not record.request:
                record.response = "Please provide a valid message."
                continue

            # Get the dataset
            dataset = self._load_dataset()
            if isinstance(dataset, dict) and 'error' in dataset:
                record.response = "I'm having trouble accessing my knowledge base. Please try again later."
                continue

            if not dataset or not isinstance(dataset, list):
                record.response = "I'm currently unable to answer questions. Please try again later."
                continue

            # Process the message
            response = self._process_user_message(record.request, dataset)
            record.response = response.get('message', "I couldn't understand your question.")

    @api.model
    def _load_dataset(self):
        """Load the dataset from the JSON file"""
        try:
            module_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            dataset_path = os.path.join(module_path, 'static', 'src', 'data', 'erp_dataset.json')
            _logger.info("Loading dataset from: %s", dataset_path)
            
            if not os.path.exists(dataset_path):
                _logger.error("Dataset file does not exist: %s", dataset_path)
                return {"error": "Dataset file not found"}

            with open(dataset_path, 'r', encoding='utf-8') as file:
                dataset = json.load(file)

            if not isinstance(dataset, list):
                _logger.error("Invalid dataset format. Expected list, got %s", type(dataset))
                return {"error": "Invalid dataset format"}
                
            return dataset
        except json.JSONDecodeError as e:
            _logger.error("Error decoding JSON dataset: %s", str(e))
            return {"error": "Invalid JSON format"}
        except Exception as e:
            _logger.error("Error loading dataset: %s", str(e))
            return {"error": str(e)}

    def _similarity(self, a, b):
        """Calculate similarity between two strings using SequenceMatcher."""
        try:
            return SequenceMatcher(None, a, b).ratio()
        except Exception as e:
            _logger.warning("Error in similarity calculation: %s", str(e))
            return 0

    def _get_main_topics(self):
        """Returns the list of main topics for fallback"""
        return [
            "CraftSchoolship Overview",
            "CraftEd ERP",
            "CraftEd LMS",
            "CraftEd Chat",
            "CraftEd Meet",
            "CraftEd AI",
            "CraftEd Mobile",
            "CraftEd Workspace",
            "CraftEd Universe"
        ]

    def _find_best_match(self, user_message, dataset):
        """Finds the best matching answer for the user message"""
        best_match = None
        best_score = 0.5
        best_question = ""

        user_words = user_message.split()
        user_words_set = set(user_words)

        for topic in dataset:
            if not isinstance(topic, dict):
                continue
                
            if 'questions' in topic and 'answer' in topic:
                for question in topic['questions']:
                    try:
                        question_lower = question.lower()
                        score = self._similarity(user_message, question_lower)
                        
                        question_words = set(question_lower.split())
                        word_matches = question_words & user_words_set
                        if word_matches:
                            score += 0.1 * len(word_matches)  
                        
                        if score > best_score:
                            best_score = score
                            best_match = topic
                            best_question = question
                    except Exception as e:
                        _logger.warning("Error calculating similarity: %s", str(e))
                        continue

        return best_match, best_score

    def _find_topic_match(self, user_message, dataset):
        """Finds a match based on topic names"""
        user_words = user_message.split()
        for topic in dataset:
            topic_name = topic.get('topic', '').lower()
            if any(word in topic_name for word in user_words):
                return topic
        return None

    def _get_keyword_matches(self, user_message, dataset):
        """Finds matches based on keywords"""
        user_words = user_message.split()
        keyword_map = {}
        matched_topics = []
        
        for topic in dataset:
            if 'keywords' in topic and isinstance(topic['keywords'], list):
                for keyword in topic['keywords']:
                    keyword_lower = keyword.lower()
                    if keyword_lower not in keyword_map:
                        keyword_map[keyword_lower] = topic

        for word in user_words:
            if word in keyword_map:
                matched_topics.append(keyword_map[word])
            else:
                for keyword in keyword_map:
                    if word in keyword or keyword in word:
                        matched_topics.append(keyword_map[keyword])

        return matched_topics

    def _process_user_message(self, message, dataset):
        """Processes the user message and returns the appropriate response"""
        # Handle help command
        if message.lower().strip() in ['help', 'hi', 'hello']:
            return {
                'message': "Hello, here are some topics you can ask about:",
                'options': self._get_main_topics()
            }

        user_message = message.lower().strip()
        
        # Check for keyword matches
        keyword_matches = self._get_keyword_matches(user_message, dataset)
        if keyword_matches:
            return {
                'message': keyword_matches[0]['answer'],
                'options': None
            }

        # Enhanced similarity matching
        best_match, best_score = self._find_best_match(user_message, dataset)
        
        if best_match and best_score > 0.5:
            return {
                'message': best_match['answer'],
                'options': None
            }
        else:
            # Try to find a match based on topic names
            topic_match = self._find_topic_match(user_message, dataset)
            
            if topic_match:
                return {
                    'message': topic_match['answer'],
                    'options': None
                }
            else:
                return {
                    'message': "I'm not sure I understand. Here are some topics you can ask about:",
                    'options': self._get_main_topics()
                }
    
    @api.model
    def process_message(self, message, visitor_id):
        """Process chatbot message and return response"""
        try:
            _logger.info("Processing message: %s", message)
            _logger.info("Visitor ID: %s", visitor_id)

            # Validate user input
            if not message or not isinstance(message, str):
                return {
                    'message': "Please provide a valid message.",
                    'options': None
                }

            if not visitor_id or not isinstance(visitor_id, str):
                return {
                    'message': "Visitor error. Please refresh the page.",
                    'options': None
                }

            # Load dataset
            dataset = self._load_dataset()
            if isinstance(dataset, dict) and 'error' in dataset:
                return {
                    'message': "I'm having trouble accessing my knowledge base. Please try again later.",
                    'options': None
                }

            if not dataset or not isinstance(dataset, list):
                return {
                    'message': "I'm currently unable to answer questions. Please try again later.",
                    'options': None
                }

            # Process the message and get response
            response_data = self._process_user_message(message, dataset)
            
            # Create message record
            self.create({
                'request': message,
                'visitor_id': visitor_id,
            })
            
            return response_data

        except Exception as e:
            _logger.error("Error processing message: %s", str(e), exc_info=True)
            return {
                'message': "I encountered an error processing your request. Please try again.",
                'options': None
            }
            
    @api.model
    def save_message(self, message_type, content, visitor_id, options=None):
        """Save a message to the chat history"""
        return self.create({
            'request': content if message_type == 'user' else '',
            'response': content if message_type == 'bot' else '',
            'visitor_id': visitor_id,
        }).id
        
    @api.model
    def get_conversation(self, visitor_id):
        """Get conversation history for a visitor"""
        messages = self.search([
            ('visitor_id', '=', visitor_id)
        ], order='create_date asc')
        
        return {
            'messages': [{
                'type': 'user' if msg.request else 'bot',
                'content': msg.request or msg.response,
                'date': msg.create_date
            } for msg in messages]
        }
        
    @api.model
    def clear_conversation(self, visitor_id):
        """Clear conversation history for a visitor"""
        messages = self.search([
            ('visitor_id', '=', visitor_id)
        ])
        messages.unlink()
        return {'success': True}