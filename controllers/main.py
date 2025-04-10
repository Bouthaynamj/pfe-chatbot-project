
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
            module_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            dataset_path = os.path.join(module_path, 'data', 'erp_dataset.json')
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

    @http.route('/website_custom_chatbot/process_message', type='json', auth='public')
    def process_message(self, message, session_id, **kwargs):
        try:
            _logger.info("Processing message: %s", message)
            _logger.info("Session ID: %s", session_id)

            # Validate user input
            if not message or not isinstance(message, str):
                _logger.error("Invalid input: message is missing or not a string")
                return {
                    'message': "Please provide a valid message.",
                    'options': None
                }

            if not session_id or not isinstance(session_id, str):
                _logger.error("Invalid input: session_id is missing or not a string")
                return {
                    'message': "Session error. Please refresh the page.",
                    'options': None
                }

            # Load dataset
            dataset = self.load_dataset()
            if isinstance(dataset, dict) and 'error' in dataset:
                _logger.error("Failed to load dataset: %s", dataset['error'])
                return {
                    'message': "I'm having trouble accessing my knowledge base. Please try again later.",
                    'options': None
                }

            if not dataset or not isinstance(dataset, list):
                _logger.error("Empty or invalid dataset")
                return {
                    'message': "I'm currently unable to answer questions. Please try again later.",
                    'options': None
                }

            # Main topics for fallback
            main_topics = [
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

            # Handle help command
            if message.lower().strip() in ['help', 'hi', 'hello']:
                response = {
                    'message': "Here are some topics you can ask about:",
                    'options': main_topics
                }
                _logger.info("Help command detected. Responding with main topics.")
                self._save_message_to_db(message, response['message'], session_id)
                return response

            # Preprocess user message
            user_message = message.lower().strip()
            user_words = user_message.split()

            # Create a keyword map for faster lookup
            keyword_map = {}
            for topic in dataset:
                if not isinstance(topic, dict):
                    continue
                if 'keywords' in topic and isinstance(topic['keywords'], list):
                    for keyword in topic['keywords']:
                        keyword_lower = keyword.lower()
                        if keyword_lower not in keyword_map:
                            keyword_map[keyword_lower] = topic

            # Check for direct keyword matches 
            matched_topics = []
            for word in user_words:
                if word in keyword_map:
                    matched_topics.append(keyword_map[word])
                else:
                    # Check for partial matches in keywords
                    for keyword in keyword_map:
                        if word in keyword or keyword in word:
                            matched_topics.append(keyword_map[keyword])

            # If we found keyword matches, return the best one
            if matched_topics:
                # Get the most relevant match 
                best_match = matched_topics[0]
                response = {
                    'message': best_match['answer'],
                    'options': None
                }
                _logger.info("Keyword match found for message: %s", message)
                self._save_message_to_db(message, response['message'], session_id)
                return response

            # If no keyword matches, check for similar questions
            best_match = None
            best_score = 0.5  
            best_question = ""

            for topic in dataset:
                if not isinstance(topic, dict):
                    _logger.warning("Invalid topic format: %s", topic)
                    continue
                    
                if 'questions' in topic and 'answer' in topic:
                    for question in topic['questions']:
                        try:
                            question_lower = question.lower()
                            # Calculate similarity between user message and question
                            score = self._similarity(user_message, question_lower)
                            
                          
                            question_words = set(question_lower.split())
                            user_words_set = set(user_words)
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

           
            if best_match and best_score > 0.5:
                response = {
                    'message': best_match['answer'],
                    'options': None
                }
                _logger.info("Best match found with score %s for question: %s", best_score, best_question)
            else:
                # Try to find a match based on topic names
                topic_match = None
                for topic in dataset:
                    topic_name = topic.get('topic', '').lower()
                    if any(word in topic_name for word in user_words):
                        topic_match = topic
                        break
                
                if topic_match:
                    response = {
                        'message': topic_match['answer'],
                        'options': None
                    }
                else:
                    response = {
                        'message': "I'm not sure I understand. Here are some topics you can ask about:",
                        'options': main_topics
                    }
                    _logger.info("No suitable match found (best score was %s). Using fallback.", best_score)

            # Save the conversation in the database
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
        """Helper method to save messages to database."""
        try:
            if not hasattr(request, 'env'):
                _logger.warning("No request.env available, skipping DB save")
                return
                
            ChatbotMessage = request.env['chatbot.message'].sudo()
            if not ChatbotMessage:
                _logger.warning("ChatbotMessage model not found, skipping DB save")
                return
                
            ChatbotMessage.create_message(
                user_message=user_message,
                bot_response=bot_response,
                session_id=session_id,
                ip_address=request.httprequest.remote_addr
            )
        except Exception as e:
            _logger.error("Error saving message to DB: %s", str(e), exc_info=True)