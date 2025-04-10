from odoo import models, fields, api

# Model Definition 
class ChatbotMessage(models.TransientModel):  
    _name = 'chatbot.message'
    _description = 'Chatbot Message'

    # Fields
    request = fields.Text(string='Request', required=True)  
    response = fields.Text(string='Response', required=True)  
    visitor_id = fields.Many2one('website.visitor', string='Visitor', readonly=True)  
    user_id = fields.Many2one(
        'res.users', 
        string='User', 
        readonly=True,
        default=lambda self: self.env.user.id
    )

    # Override create method to add custom logic if needed
    @api.model
    def create(self, vals):
        """Override create to handle additional logic if necessary."""
        # Add any custom logic here (e.g., validation, logging, etc.)
        return super(ChatbotMessage, self).create(vals)