from odoo import models, fields, api
import json
import os
import logging
import uuid
import time
from difflib import SequenceMatcher

_logger = logging.getLogger(__name__)

class ChatbotMessage(models.TransientModel):  
    _name = 'chatbot.message'
    _description = 'Chatbot Message'
    _order = 'create_date asc'  

    # Fields
    request = fields.Text(string='Request') 
    response = fields.Text(string='Response', compute='_compute_response', precompute=True, store=True)
    session_id = fields.Char(string='Session ID', readonly=True, index=True)
    visitor_id = fields.Many2one('website.visitor', string='Visitor', readonly=True, index=True)
    options = fields.Text(string='Options', readonly=True)
    message_timestamp = fields.Float(string='Message Timestamp', readonly=True, default=lambda self: time.time())
    message_hash = fields.Char(string='Message Hash', readonly=True)  
    user_id = fields.Many2one(
        'res.users', 
        string='User', 
        readonly=True,
        default=lambda self: self.env.user.id
    )

    @api.model
    def get_visitor_from_request(self):
        """Get or create a visitor ID for the chatbot session"""
        try:
            # Try to get visitor from website module
            visitor = self.env['website.visitor'].sudo()._get_visitor_from_request()
            if visitor:
                _logger.info("Found website visitor: %s", visitor.id)
                return {'visitor_id': str(visitor.id)}
            
            # If no visitor found, create a session-based ID
            request = self.env['ir.http'].get_request()
            if request and hasattr(request, 'session') and request.session:
                if hasattr(request.session, 'sid'):
                    session_id = request.session.sid
                else:
                    session_id = request.session.session_id if hasattr(request.session, 'session_id') else str(uuid.uuid4())
                
                _logger.info("Using session ID: %s", session_id)
                return {'visitor_id': f"session_{session_id}"}
                
            # Final fallback
            random_id = str(uuid.uuid4())
            _logger.info("Creating random visitor ID: %s", random_id)
            return {'visitor_id': f"uuid_{random_id}"}
        except Exception as e:
            _logger.error("Error getting visitor: %s", str(e))
            return {'visitor_id': f"error_{str(uuid.uuid4())}"}

    @api.model
    def create(self, vals):
        """Override create to handle additional logic if necessary."""
        content = vals.get('request') or vals.get('response') or ''
        vals['message_hash'] = f"{content[:100]}_{time.time()}"
        return super(ChatbotMessage, self).create(vals)

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

            if not dataset or not isinstance(dataset, list):
                record.response = "I'm currently unable to answer questions. Please try again later."
                continue

            response = self._process_user_message(record.request, dataset)
            record.response = response.get('message', "I couldn't understand your question.")

    @api.model
    def _load_dataset(self):
        """Load the dataset from the JSON file"""
        try:
            module_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            dataset_path = os.path.join(module_path, 'static', 'src', 'data', 'erp_dataset.json')
            _logger.info("Loading dataset from: %s", dataset_path)
            
            if not os.path.exists(dataset_path):
                _logger.error("Dataset file does not exist: %s", dataset_path)
                return {"error": "Dataset file not found"}

            with open(dataset_path, 'r', encoding='utf-8') as file:
                dataset = json.load(file)

            if not isinstance(dataset, list):
                _logger.error("Invalid dataset format. Expected list, got %s", type(dataset))
                return {"error": "Invalid dataset format"}
                
            return dataset
        except json.JSONDecodeError as e:
            _logger.error("Error decoding JSON dataset: %s", str(e))
            return {"error": "Invalid JSON format"}
        except Exception as e:
            _logger.error("Error loading dataset: %s", str(e))
            return {"error": str(e)}

    def _similarity(self, a, b):
        """Calculate similarity between two strings using SequenceMatcher."""
        try:
            return SequenceMatcher(None, a.lower(), b.lower()).ratio()
        except Exception as e:
            _logger.warning("Error in similarity calculation: %s", str(e))
            return 0

    def _get_main_topics(self):
        """Returns the list of main topics for fallback"""
        return [
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

    def _find_best_match(self, user_message, dataset):
        """Finds the best matching answer for the user message"""
        best_match = None
        best_score = 0.5
        best_question = ""
        
        user_words = user_message.split()
        user_words_set = set(word.lower() for word in user_words)
        
        for topic in dataset:
            if not isinstance(topic, dict):
                continue
                
            if 'questions' in topic and 'answer' in topic:
                for question in topic['questions']:
                    try:
                        question_lower = question.lower()
                        score = self._similarity(user_message, question_lower)
                        
                        question_words = set(question_lower.split())
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
        
        return best_match, best_score

    def _find_topic_match(self, user_message, dataset):
        """Finds a match based on topic names"""
        user_message_lower = user_message.lower()
        user_words = user_message_lower.split()
        
        for topic in dataset:
            if not isinstance(topic, dict) or 'topic' not in topic:
                continue
                
            topic_name = topic['topic'].lower()
            
            if any(word in topic_name for word in user_words):
                return topic
                
            if self._similarity(user_message_lower, topic_name) > 0.7:
                return topic
                
        return None

    def _get_keyword_matches(self, user_message, dataset):
        """Finds matches based on keywords"""
        user_message = user_message.lower()
        user_words = user_message.split()
        keyword_map = {}
        matched_topics = []
        
        for topic in dataset:
            if not isinstance(topic, dict):
                continue
                
            if 'keywords' in topic and isinstance(topic['keywords'], list):
                for keyword in topic['keywords']:
                    keyword_lower = keyword.lower()
                    if keyword_lower not in keyword_map:
                        keyword_map[keyword_lower] = topic

        for word in user_words:
            if word in keyword_map:
                matched_topics.append(keyword_map[word])
            else:
                for keyword in keyword_map:
                    if word in keyword or keyword in word:
                        matched_topics.append(keyword_map[keyword])

        return matched_topics

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
                'message': "Hello, here are some topics you can ask about:",
                'options': self._get_main_topics()
            }

        user_message = message_lower
        
        keyword_matches = self._get_keyword_matches(user_message, dataset)
        if keyword_matches:
            return {
                'message': keyword_matches[0]['answer'],
                'options': None
            }

        best_match, best_score = self._find_best_match(user_message, dataset)
        
        if best_match and best_score > 0.5:
            return {
                'message': best_match['answer'],
                'options': None
            }
        else:
            topic_match = self._find_topic_match(user_message, dataset)
            
            if topic_match:
                return {
                    'message': topic_match['answer'],
                    'options': None
                }
            else:
                # Always include options in fallback messages
                return {
                    'message': "I'm not sure I understand. Here are some topics you can ask about:",
                    'options': self._get_main_topics()
                }

    @api.model
    def process_message(self, message, visitor_id):
        """Process chatbot message and return response"""
        try:
            if not message or not message.strip():
                return {
                    'message': "Please provide a valid message.",
                    'options': None
                }
            
            _logger.info("Processing message: %s", message)
            _logger.info("Visitor ID: %s", visitor_id)

            if not message or not isinstance(message, str):
                return {
                    'message': "Please provide a valid message.",
                    'options': None
                }

            if not visitor_id or not isinstance(visitor_id, str):
                return {
                    'message': "Visitor error. Please refresh the page.",
                    'options': None
                }

            recent_time = time.time() - 5.0
            domain = []
            if visitor_id.isdigit():
                domain = ['|', 
                        ('visitor_id', '=', int(visitor_id)),
                        ('session_id', '=', visitor_id)]
            else:
                domain = [('session_id', '=', visitor_id)]
                
            domain.append(('request', '=', message))
            domain.append(('message_timestamp', '>', recent_time))
            
            recent_messages = self.search_count(domain)
            if recent_messages > 0:
                _logger.info("Duplicate message detected, skipping: %s", message)
                return {
                    'message': "I'm processing your previous request. Please wait a moment.",
                    'options': None
                }
            
            numeric_visitor_id = None
            if visitor_id.isdigit():
                numeric_visitor_id = int(visitor_id)
            
            dataset = self._load_dataset()
            if isinstance(dataset, dict) and 'error' in dataset:
                return {
                    'message': "I'm having trouble accessing my knowledge base. Please try again later.",
                    'options': None
                }

            if not dataset or not isinstance(dataset, list):
                return {
                    'message': "I'm currently unable to answer questions. Please try again later.",
                    'options': None
                }

            response_data = self._process_user_message(message, dataset)
            
            user_msg_vals = {
                'request': message,
                'message_timestamp': time.time(),
            }
            
            # Ensure options are properly serialized before saving
            options_json = None
            if response_data.get('options'):
                try:
                    options_json = json.dumps(response_data.get('options'))
                    _logger.info("Serialized options for response: %s", options_json)
                except (TypeError, ValueError) as e:
                    _logger.error("Error serializing options: %s", str(e))
            
            bot_msg_vals = {
                'response': response_data.get('message'),
                'options': options_json,
                'message_timestamp': time.time() + 0.1,
            }
            
            if numeric_visitor_id:
                user_msg_vals['visitor_id'] = numeric_visitor_id
                bot_msg_vals['visitor_id'] = numeric_visitor_id
            else:
                user_msg_vals['session_id'] = visitor_id
                bot_msg_vals['session_id'] = visitor_id
            
            # Create user message
            self.create(user_msg_vals)
            # Create bot message with options
            self.create(bot_msg_vals)
            
            return response_data

        except Exception as e:
            _logger.error("Error processing message: %s", str(e), exc_info=True)
            return {
                'message': "I encountered an error processing your request. Please try again.",
                'options': None
            }
            
    @api.model
    def save_message(self, message_type, content, visitor_id, options=None):
        """Save a message to the chat history"""
        _logger.info("Saving %s message for visitor %s: %s", message_type, visitor_id, content[:30] if content else "")
        _logger.info("With options: %s", options)
        
        if not content:
            return False
            
        # Always ensure options is properly serialized as a JSON string
        options_json = None
        if options:
            try:
                # If options is already a string, make sure it's valid JSON
                if isinstance(options, str):
                    # Validate by parsing and re-stringifying
                    parsed = json.loads(options)
                    options_json = json.dumps(parsed)
                else:
                    options_json = json.dumps(options)
                _logger.info("Serialized options: %s", options_json)
            except (TypeError, ValueError, json.JSONDecodeError) as e:
                _logger.error("Error serializing options: %s", str(e))
        
        message_vals = {
            'message_timestamp': time.time(),
            'session_id': visitor_id,
            'options': options_json
        }
        
        if message_type == 'user':
            message_vals['request'] = content
        else:
            message_vals['response'] = content
        
        if visitor_id and visitor_id.isdigit():
            message_vals['visitor_id'] = int(visitor_id)
        
        try:
            new_id = self.create(message_vals).id
            _logger.info("Message saved with ID: %s", new_id)
            return new_id
        except Exception as e:
            _logger.error("Error saving message: %s", str(e))
            return False

    @api.model
    def get_conversation(self, visitor_id):
        """Get conversation history for a visitor"""
        _logger.info("Getting conversation for visitor: %s", visitor_id)
        domain = []
        
        if visitor_id.isdigit():
            domain = ['|', 
                    ('visitor_id', '=', int(visitor_id)),
                    ('session_id', '=', visitor_id)]
        else:
            domain = [('session_id', '=', visitor_id)]
        
        messages = self.search(domain, order='create_date asc, id asc')
        _logger.info("Found %s messages", len(messages))
        
        result = {
            'messages': []
        }
        
        # First, gather all user messages and bot messages
        user_messages = []
        bot_messages = []
        
        for msg in messages:
            try:
                if msg.request:
                    user_messages.append({
                        'type': 'user',
                        'content': msg.request,
                        'date': msg.create_date,
                        'options': None
                    })
                
                if msg.response and msg.response != "Please provide a valid message.":
                    # Parse options from JSON for consistent format
                    options = None
                    if msg.options:
                        try:
                            if isinstance(msg.options, str):
                                options = json.loads(msg.options)
                                _logger.info("Parsed options from string: %s", options)
                            else:
                                options = msg.options
                                _logger.info("Using options directly: %s", options)
                        except json.JSONDecodeError as e:
                            _logger.warning("Could not parse options JSON: %s - %s", msg.options, str(e))
                    
                    bot_messages.append({
                        'type': 'bot',
                        'content': msg.response,
                        'date': msg.create_date,
                        'options': options
                    })
            except Exception as e:
                _logger.error("Error processing message %s: %s", msg.id, str(e))
        
        # Add all messages to the result in proper order
        all_messages = []
        for i in range(max(len(user_messages), len(bot_messages))):
            if i < len(user_messages):
                all_messages.append(user_messages[i])
            if i < len(bot_messages):
                all_messages.append(bot_messages[i])
        
        # Ensure the most recent fallback message with options is preserved
        fallback_msg_with_options = None
        for msg in reversed(all_messages):
            if (msg['type'] == 'bot' and 
                "Here are some topics you can ask about:" in msg.get('content', '') and 
                msg.get('options')):
                fallback_msg_with_options = msg
                break
        
        result['messages'] = all_messages
        result['fallback_options'] = fallback_msg_with_options['options'] if fallback_msg_with_options else None
        
        return result

    @api.model
    def clear_conversation(self, visitor_id):
        """Clear conversation history for a visitor"""
        _logger.info("Clearing conversation for visitor: %s", visitor_id)
        domain = []
        
        if visitor_id.isdigit():
            domain = ['|', 
                    ('visitor_id', '=', int(visitor_id)),
                    ('session_id', '=', visitor_id)]
        else:
            domain = [('session_id', '=', visitor_id)]
        
        messages = self.search(domain)
        _logger.info("Deleting %s messages", len(messages))
        messages.unlink()
        return {'success': True}