from odoo import http
import json
import os
import logging

_logger = logging.getLogger(__name__)

class ChatbotController(http.Controller):
    
    @http.route('/website_custom_chatbot/load_dataset', type='json', auth='public')
    def load_dataset(self, **kwargs):
        try:
            module_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            dataset_path = os.path.join(module_path, 'data', 'erp_dataset.json')
            
            _logger.info(f"Loading dataset from: {dataset_path}")
            
            if not os.path.exists(dataset_path):
                _logger.error(f"Dataset file does not exist: {dataset_path}")
                return []
                
            with open(dataset_path, 'r', encoding='utf-8') as file:
                dataset = json.load(file)
                
            return dataset
        except Exception as e:
            _logger.error(f"Error loading dataset: {str(e)}")
            return []