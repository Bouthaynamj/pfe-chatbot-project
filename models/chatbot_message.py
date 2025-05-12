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
            # Ensure the website visitor has a valid partner_id.
            if record.visitor_id:
                partner = record.visitor_id.partner_id
                if not partner or not partner.exists():
                    # Create a new Guest Partner record and update the visitor.
                    new_partner = self.env['res.partner'].create({'name': 'Guest Partner'})
                    record.visitor_id.write({'partner_id': new_partner.id})

            if not record.request:
                record.response = "Please provide a valid message."
                record.options = None
                continue

            dataset = record._load_dataset()
            if isinstance(dataset, dict) and dataset.get('error'):
                record.response = "I'm having trouble accessing my knowledge base. Please try again later."
                record.options = None
                continue

            response = record._process_user_message(record.request, dataset)
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
                'options': None
            }

        message_lower = message.lower().strip()

        if message_lower in ['help', 'hi', 'hello']:
            return {
                'message': "👋 Hello! I'm your CraftEd Assistant. I can help you with questions about our products and services. What would you like to know?",
                'options': None
            }

        # Check for question matches first
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

        # If no match found, show topics
        return {
            'message': "I'm not sure I understand. Here are some topics you can ask about:",
            'options': json.dumps(self._get_main_topics())
        }