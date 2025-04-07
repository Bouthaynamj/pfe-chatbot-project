# controllers/main.py
from odoo import http, _
import json
import os
import logging
from difflib import SequenceMatcher

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
                return []

            with open(dataset_path, 'r', encoding='utf-8') as file:
                dataset = json.load(file)

            return dataset
        except Exception as e:
            _logger.error(_("Error loading dataset: %s") % str(e))
            return []

    @http.route('/website_custom_chatbot/process_message', type='json', auth='public')
    def process_message(self, message, **kwargs):
        try:
            module_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            dataset_path = os.path.join(module_path, 'data', 'erp_dataset.json')
            
            if not os.path.exists(dataset_path):
                return {
                    'message': "Sorry, the chatbot dataset is unavailable at the moment.",
                    'options': None
                }

            with open(dataset_path, 'r', encoding='utf-8') as file:
                dataset = json.load(file)

            # Main topics for the help command
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
            if message.lower() in ['help', 'hi']:
                return {
                    'message': "Here are some topics you can ask about:",
                    'options': main_topics
                }

            # Find best match in the dataset
            best_match = None
            best_score = 0

            for topic in dataset:
                for question in topic['questions']:
                    score = self._similarity(message.lower(), question.lower())
                    if score > best_score:
                        best_score = score
                        best_match = topic

            # Threshold for considering it a match (adjust as needed)
            if best_match and best_score > 0.3:
                return {
                    'message': best_match['answer'],
                    'options': None
                }
            else:
                return {
                    'message': "Sorry, I don't understand your question. Here are some topics you can ask about:",
                    'options': main_topics
                }

        except Exception as e:
            _logger.error(_("Error processing message: %s") % str(e))
            return {
                'message': "Sorry, I encountered an error processing your request.",
                'options': None
            }

    def _similarity(self, a, b):
        return SequenceMatcher(None, a, b).ratio()