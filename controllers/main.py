from odoo import http, _
from odoo.http import request

class ChatbotController(http.Controller):
    @http.route('/website_custom_chatbot/process_message', type='json', auth='public')
    def process_message(self, message, visitor_id, **kwargs):
        """Route that forwards the request to the model for processing"""
        ChatbotMessage = request.env['chatbot.message'].sudo()
        return ChatbotMessage.process_message(message, visitor_id)
        
    @http.route('/website_custom_chatbot/get_visitor_id', type='json', auth='public')
    def get_visitor_id(self, **kwargs):
        """Get or create a visitor ID for the chatbot session"""
        visitor = request.env['website.visitor'].sudo()._get_visitor_from_request()
        if not visitor:
            # Create a random ID if no visitor record exists
            import uuid
            return {'visitor_id': str(uuid.uuid4())}
        return {'visitor_id': str(visitor.id)}
        
    @http.route('/website_custom_chatbot/save_message', type='json', auth='public')
    def save_message(self, message_type, content, visitor_id, options=None, **kwargs):
        """Save a message to the chat history"""
        ChatbotMessage = request.env['chatbot.message'].sudo()
        return ChatbotMessage.create({
            'request': content if message_type == 'user' else '',
            'response': content if message_type == 'bot' else '',
            'visitor_id': visitor_id,
        })
        
    @http.route('/website_custom_chatbot/get_conversation', type='json', auth='public')
    def get_conversation(self, visitor_id, **kwargs):
        """Get conversation history for a visitor"""
        messages = request.env['chatbot.message'].sudo().search([
            ('visitor_id', '=', visitor_id)
        ], order='create_date asc')
        
        return {
            'messages': [{
                'type': 'user' if msg.request else 'bot',
                'content': msg.request or msg.response,
                'date': msg.create_date
            } for msg in messages]
        }
        
    @http.route('/website_custom_chatbot/clear_conversation', type='json', auth='public')
    def clear_conversation(self, visitor_id, **kwargs):
        """Clear conversation history for a visitor"""
        messages = request.env['chatbot.message'].sudo().search([
            ('visitor_id', '=', visitor_id)
        ])
        messages.unlink()
        return {'success': True}