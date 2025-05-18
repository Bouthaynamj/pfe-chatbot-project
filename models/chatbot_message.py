import requests
import json
import os
import logging
from odoo import models, fields, api

_logger = logging.getLogger(__name__)

class ChatbotMessage(models.TransientModel):
    _name = 'chatbot.message'
    _description = 'Chatbot Message'
    _order = 'id asc'

    request = fields.Text(string='Request')
    response = fields.Text(string='Response', compute='_compute_response', store=True)
    visitor_id = fields.Many2one('website.visitor', string='Visitor', readonly=True, index=True)
    options = fields.Text(string='Options', readonly=True)
    language = fields.Selection(
        [('en', 'English'), ('fr', 'French')],
        string='Language',
        default='en'
    )

    @api.model
    def create(self, vals):
        """Override create to ensure proper language handling"""
        # Store the original language for proper response handling
        language = vals.get('language', 'en')
        
        # Create the record
        record = super(ChatbotMessage, self).create(vals)
        
        # Force computation of response with the correct language
        record.with_context(force_language=language)._compute_response()
        
        return record

    @api.depends('request', 'language')
    def _compute_response(self):
        for record in self:
            lang = self.env.context.get('force_language') or record.language or 'en'
            _logger.debug("Processing request: %s in language: %s", record.request, lang)
            
            try:
                # Add explicit debug for translation process
                _logger.info("Loading dataset...")
                dataset = self._load_dataset()
                
                _logger.info("Processing message...")
                result = self._process_user_message(record.request, dataset, lang)
                
                record.response = result.get('message')
                record.options = result.get('options')
                
                _logger.info("Response generated: %s", record.response[:50])
            except Exception as e:
                _logger.error("Error generating response: %s", str(e), exc_info=True)
                record.response = "Sorry, I encountered an error processing your request."

    def _translate(self, text, target_lang='en'):
        """Translate text using MyMemory API"""
        if not text:
            return text
            
        # Handle dictionary format answers
        if isinstance(text, dict):
            if target_lang in text:
                return text[target_lang]
            elif 'en' in text:
                # If target language not available, fall back to English and translate
                text = text['en']
            else:
                # If neither available, use any available text
                text = next(iter(text.values()), "No translation available")
        
        # No need to translate if already in target language
        # Check if text is likely already in the target language (simplified check)
        if target_lang == 'en' and all(ord(c) < 128 for c in text):
            return text  # Likely English text
        elif target_lang == 'fr' and any(word in text.lower() for word in ['je', 'vous', 'avec', 'est']):
            return text  # Likely French text
            
        try:
            url = "https://api.mymemory.translated.net/get"
            params = {
                'q': text,
                'langpair': f'en|{target_lang}' if target_lang != 'en' else 'fr|en',
                'de': 'bouthayna.mejdi@horizon-tech.tn'  # Required for free API
            }
            
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            _logger.info("Translation API response status: %s", data.get('responseStatus'))
            
            if data.get('responseStatus') == 200 and data.get('responseData'):
                return data['responseData']['translatedText']
            else:
                _logger.warning("Translation failed: %s", data)
            return text
        except Exception as e:
            _logger.error("Translation error: %s", str(e), exc_info=True)  # Added exc_info for stack trace
            return text

    def _load_dataset(self):
        """Load the dataset from the JSON file"""
        try:
            module_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            dataset_path = os.path.join(module_path, 'static', 'src', 'data', 'erp_dataset.json')
            
            if not os.path.exists(dataset_path):
                _logger.error("Dataset file not found at: %s", dataset_path)
                return {"error": "Dataset file not found"}

            with open(dataset_path, 'r', encoding='utf-8') as file:
                dataset = json.load(file)
                if not dataset:
                    _logger.error("Empty dataset loaded")
                    return {"error": "Empty dataset"}
                return dataset
                
        except json.JSONDecodeError as e:
            _logger.error("JSON parsing error: %s", str(e))
            return {"error": "Invalid JSON format"}
        except Exception as e:
            _logger.error("Error loading dataset: %s", str(e))
            return {"error": str(e)}

    def _get_main_topics(self, lang='en'):
        """Returns the list of main topics for fallback"""
        topics = {
            'en': [
                "CraftEd ERP",
                "CraftEd LMS",
                "CraftEd Chat",
                "CraftEd Meet",
                "CraftEd AI",
                "CraftEd Mobile",
                "CraftEd Workspace",
                "CraftEd Universe"
            ],
            'fr': [
                "CraftEd ERP",
                "CraftEd LMS",
                "CraftEd Chat",
                "CraftEd Meet",
                "CraftEd IA",
                "CraftEd Mobile",
                "CraftEd Workspace",
                "CraftEd Univers"
            ]
        }
        return topics.get(lang, topics['en'])

    def _process_user_message(self, message, dataset, lang='en'):
        """Processes the user message and returns the appropriate response"""
        if not message:
            return {
                'message': self._translate("Please provide a valid message.", lang),
                'options': None
            }

        message_lower = message.lower().strip()
        
        # Special handling for common greetings
        if any(greeting in message_lower for greeting in ['help', 'hi', 'hello', 'bonjour', 'salut']):
            welcome_msg = {
                'en': "👋 Hello! I'm your CraftEd Assistant. I can help you with questions about our products and services. What would you like to know?",
                'fr': "👋 Bonjour ! Je suis votre assistant CraftEd. Je peux vous aider avec des questions sur nos produits et services. Que souhaitez-vous savoir ?"
            }
            return {
                'message': welcome_msg.get(lang, welcome_msg['en']),
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
                            # Extract answer in the correct language
                            if isinstance(topic['answer'], dict) and lang in topic['answer']:
                                answer = topic['answer'][lang]
                            elif isinstance(topic['answer'], dict) and 'en' in topic['answer']:
                                # Fallback to English and translate if needed
                                answer = self._translate(topic['answer']['en'], lang)
                            else:
                                # Fallback to whatever format is available
                                answer = self._translate(str(topic['answer']), lang)
                            return {
                                'message': answer,
                                'options': None
                            }
                    except Exception as e:
                        _logger.error("Error processing question: %s", str(e))
                        continue

        # If no match found, show topics
        topic_msg = {
            'en': "I'm not sure I understand. Here are some topics you can ask about:",
            'fr': "Je ne comprends pas bien. Voici des sujets sur lesquels vous pouvez poser des questions :"
        }
        
        return {
            'message': topic_msg.get(lang, topic_msg['en']),
            'options': json.dumps(self._get_main_topics(lang))
        }

    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        """Override to translate responses based on current language"""
        result = super(ChatbotMessage, self).search_read(domain=domain, fields=fields, offset=offset, limit=limit, order=order)
        
        # Get current language from context
        current_lang = self.env.context.get('current_lang', 'en')
        
        # Translate all messages to the requested language
        for record in result:
            # Translate user requests
            if 'request' in record:
                record['request'] = self._translate(record['request'], current_lang)
            
            # Translate bot responses
            if 'response' in record:
                # If it's a dictionary with language keys
                if isinstance(record['response'], dict):
                    if current_lang in record['response']:
                        record['response'] = record['response'][current_lang]
                    elif 'en' in record['response']:
                        record['response'] = self._translate(record['response']['en'], current_lang)
                # If it's a string
                else:
                    record['response'] = self._translate(record['response'], current_lang)
            
            # Translate options if available
            if 'options' in record and record['options']:
                try:
                    options = json.loads(record['options'])
                    translated_options = [self._translate(opt, current_lang) for opt in options]
                    record['options'] = json.dumps(translated_options)
                except (json.JSONDecodeError, TypeError):
                    pass
        
        return result

    @api.model
    def search_unlink(self, domain):
        """Search and unlink records matching the domain"""
        records = self.search(domain)
        count = len(records)
        records.unlink()
        return count