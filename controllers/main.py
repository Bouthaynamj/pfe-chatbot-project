from odoo import http, _
import json
import os
import logging
from difflib import SequenceMatcher
from odoo.http import request

_logger = logging.getLogger(__name__)

class ChatbotController(http.Controller):
    
    @http.route('/website_custom_chatbot/load_dataset', type='json', auth='public')
    def load_dataset(self, **kwargs):
        try:
            # Update the path to point to the static folder
            module_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            dataset_path = os.path.join(module_path, 'static', 'src', 'data', 'erp_dataset.json')  # Updated path
            _logger.info(_("Loading dataset from: %s") % dataset_path)

            if not os.path.exists(dataset_path):
                _logger.error(_("Dataset file does not exist: %s") % dataset_path)
                return {"error": "Dataset file not found"}

            with open(dataset_path, 'r', encoding='utf-8') as file:
                dataset = json.load(file)

            if not isinstance(dataset, list):
                _logger.error(_("Invalid dataset format. Expected list, got %s") % type(dataset))
                return {"error": "Invalid dataset format"}

            return dataset
        except json.JSONDecodeError as e:
            _logger.error(_("Error decoding JSON dataset: %s") % str(e))
            return {"error": "Invalid JSON format"}
        except Exception as e:
            _logger.error(_("Error loading dataset: %s") % str(e))
            return {"error": str(e)}

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

        for topic in dataset:
            if not isinstance(topic, dict):
                continue
                
            if 'questions' in topic and 'answer' in topic:
                for question in topic['questions']:
                    try:
                        question_lower = question.lower()
                        score = self._similarity(user_message, question_lower)
                        
                        question_words = set(question_lower.split())
                        user_words_set = set(user_message.split())
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
                'message': "Here are some topics you can ask about:",
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

    @http.route('/website_custom_chatbot/process_message', type='json', auth='public')
    def process_message(self, message, session_id, **kwargs):
        try:
            _logger.info("Processing message: %s", message)
            _logger.info("Session ID: %s", session_id)

            # Validate user input
            if not message or not isinstance(message, str):
                return {
                    'message': "Please provide a valid message.",
                    'options': None
                }

            if not session_id or not isinstance(session_id, str):
                return {
                    'message': "Session error. Please refresh the page.",
                    'options': None
                }

            # Load dataset
            dataset = self.load_dataset()
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

            response = self._process_user_message(message, dataset)
            self._save_message_to_db(message, response['message'], session_id)
            return response

        except Exception as e:
            _logger.error("Error processing message: %s", str(e), exc_info=True)
            return {
                'message': "I encountered an error processing your request. Please try again.",
                'options': None
            }

    def _similarity(self, a, b):
        """Calculate similarity between two strings using SequenceMatcher."""
        try:
            return SequenceMatcher(None, a, b).ratio()
        except Exception as e:
            _logger.warning("Error in similarity calculation: %s", str(e))
            return 0

    def _save_message_to_db(self, user_message, bot_response, session_id):
        """Helper method to save messages to the database."""
        try:
            ChatbotMessage = request.env['chatbot.message'].sudo()
            ChatbotMessage.create({
                'request': user_message,
                'visitor_id': None,
                'user_id': request.env.user.id
                # response will be computed automatically
            })
        except Exception as e:
            _logger.error("Error saving message to DB: %s", str(e), exc_info=True)