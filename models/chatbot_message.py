from odoo import models, fields, api
import json
import os
import logging

_logger = logging.getLogger(__name__)

class ChatbotMessage(models.TransientModel):
    _name = 'chatbot.message'
    _description = 'Chatbot Message'
    _order = 'id asc'

    request = fields.Text(string='Request')
    response = fields.Text(string='Response', compute='_compute_response', store=True)
    visitor_id = fields.Many2one('website.visitor', string='Visitor', readonly=True, index=True)
    options = fields.Text(string='Options', readonly=True)

    @api.depends('request')
    def _compute_response(self):
        for record in self:
            if not record.request:
                record.response = "Please provide a valid message."
                continue

            dataset = self._load_dataset()
            if isinstance(dataset, dict) and 'error' in dataset:
                record.response = "I'm having trouble accessing my knowledge base. Please try again later."
                continue

            response = self._process_user_message(record.request, dataset)
            record.response = response.get('message', "I couldn't understand your question.")
            record.options = response.get('options')

    def _load_dataset(self):
        """Load the dataset from the JSON file"""
        try:
            module_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            dataset_path = os.path.join(module_path, 'static', 'src', 'data', 'erp_dataset.json')
            
            if not os.path.exists(dataset_path):
                return {"error": "Dataset file not found"}

            with open(dataset_path, 'r', encoding='utf-8') as file:
                return json.load(file)
                
        except Exception as e:
            _logger.error("Error loading dataset: %s", str(e))
            return {"error": str(e)}

    def _get_main_topics(self):
        """Returns the list of main topics for fallback"""
        return [
            "CraftEd ERP",
            "CraftEd LMS",
            "CraftEd Chat",
            "CraftEd Meet",
            "CraftEd AI",
            "CraftEd Mobile",
            "CraftEd Workspace",
            "CraftEd Universe"
        ]

    def _process_user_message(self, message, dataset):
        """Processes the user message and returns the appropriate response"""
        if not message:
            return {
                'message': "Please provide a valid message.",
                'options': json.dumps(self._get_main_topics())  
            }

        message_lower = message.lower().strip()
        
        
        if message_lower in ['help', 'hi', 'hello']:
            return {
                'message': "Hello, here are some topics you can ask about:",
                'options': json.dumps(self._get_main_topics())  
            }

        # Check for exact topic matches
        main_topics = [topic.lower() for topic in self._get_main_topics()]
        if message_lower in main_topics:
            for entry in dataset:
                if 'answer' in entry and message_lower in entry['answer'].lower():
                    return {
                        'message': entry['answer'],
                        'options': None  
                    }
            return {
                'message': f"Sorry, I couldn't find any information on {message}.",
                'options': json.dumps(self._get_main_topics())  
            }

        # Check for question matches
        for topic in dataset:
            if not isinstance(topic, dict):
                continue

            if 'questions' in topic and 'answer' in topic:
                for question in topic['questions']:
                    try:
                        if message_lower in question.lower():
                            return {
                                'message': topic['answer'],
                                'options': None  
                            }
                    except Exception:
                        continue

        return {
            'message': "I'm not sure I understand. Here are some topics you can ask about:",
            'options': json.dumps(self._get_main_topics())  
        }