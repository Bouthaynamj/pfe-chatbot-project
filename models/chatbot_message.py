from odoo import models, fields, api

#Model Definition 
class ChatbotMessage(models.TransientModel):  
    _name = 'chatbot.message'
    _description = 'Chatbot Message'
    _order = 'create_date desc'
#fields
    name = fields.Char(string='ID', required=True, copy=False, readonly=True, 
                      default=lambda self: self.env['ir.sequence'].next_by_code('chatbot.message'))
    
    request = fields.Text(string='Request', required=True)  
    response = fields.Text(string='Response', required=True)  
    create_date = fields.Datetime(string='Created on', readonly=True)
    ip_address = fields.Char(string='IP Address')
    visitor_id = fields.Many2one('website.visitor', string='Visitor', readonly=True)  
    user_id = fields.Many2one('res.users', string='User', readonly=True,
                             default=lambda self: self.env.user.id)
#methods
    @api.model
    def create_message(self, request, response, visitor_id=None, ip_address=None):
        """Create a chatbot message and associate it with a visitor."""
        return self.create({
            'request': request,
            'response': response,
            'visitor_id': visitor_id,
            'ip_address': ip_address,
        })