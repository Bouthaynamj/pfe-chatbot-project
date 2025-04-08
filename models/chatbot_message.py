from odoo import models, fields, api

class ChatbotMessage(models.TransientModel):  # Changed to TransientModel
    _name = 'chatbot.message'
    _description = 'Chatbot Message'
    _order = 'create_date desc'

    name = fields.Char(string='ID', required=True, copy=False, readonly=True, 
                      default=lambda self: self.env['ir.sequence'].next_by_code('chatbot.message'))
    request = fields.Text(string='Request', required=True)  # Renamed from user_message to request
    response = fields.Text(string='Response', required=True)  # Renamed from bot_response to response
    create_date = fields.Datetime(string='Created on', readonly=True)
    ip_address = fields.Char(string='IP Address')
    user_id = fields.Many2one('res.users', string='User', readonly=True,
                             default=lambda self: self.env.user.id)

    @api.model
    def create_message(self, request, response, ip_address=False):  # Updated parameter names
        return self.create({
            'request': request,  # Updated field name
            'response': response,  # Updated field name
            'ip_address': ip_address,
        })