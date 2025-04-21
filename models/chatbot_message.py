from odoo import models, fields, api

class ChatbotMessage(models.TransientModel):  
    _name = 'chatbot.message'
    _description = 'Chatbot Message'

    # Fields
    request = fields.Text(string='Request', required=True)  
    response = fields.Text(string='Response', compute='_compute_response', precompute=True, store=True)  
    visitor_id = fields.Many2one('website.visitor', string='Visitor', readonly=True)  
    user_id = fields.Many2one(
        'res.users', 
        string='User', 
        readonly=True,
        default=lambda self: self.env.user.id
    )

    @api.model
    def create(self, vals):
        """Override create to handle additional logic if necessary."""
        return super(ChatbotMessage, self).create(vals)

    @api.depends('request')
    def _compute_response(self):
        for record in self:
            if not record.request:
                record.response = "Please provide a valid message."
                continue

            # Get the dataset
            dataset = self._load_dataset()
            if isinstance(dataset, dict) and 'error' in dataset:
                record.response = "I'm having trouble accessing my knowledge base. Please try again later."
                continue

            if not dataset or not isinstance(dataset, list):
                record.response = "I'm currently unable to answer questions. Please try again later."
                continue

            # Process the message
            response = self._process_user_message(record.request, dataset)
            record.response = response.get('message', "I couldn't understand your question.")

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
            return {"error": str(e)}

    def _similarity(self, a, b):
        """Calculate similarity between two strings using SequenceMatcher."""
        try:
            return SequenceMatcher(None, a, b).ratio()
        except Exception:
            return 0

    def _process_user_message(self, message, dataset):
        """Process the user message and return the appropriate response"""
        # Handle help command
        if message.lower().strip() in ['help', 'hi', 'hello']:
            return {
                'message': "Here are some topics you can ask about:",
                'options': [
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
            }

        user_message = message.lower().strip()
        user_words = user_message.split()

        # Check for keyword matches
        keyword_map = {}
        matched_topics = []
        
        for topic in dataset:
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

        if matched_topics:
            return {'message': matched_topics[0]['answer']}

        # Enhanced similarity matching
        best_match = None
        best_score = 0.5
        best_question = ""

        for topic in dataset:
            if not isinstance(topic, dict):
                continue
                
            if 'questions' in topic and 'answer' in topic:
                for question in topic['questions']:
                    try:
                        question_lower = question.lower()
                        score = self._similarity(user_message, question_lower)
                        
                        question_words = set(question_lower.split())
                        user_words_set = set(user_words)
                        word_matches = question_words & user_words_set
                        if word_matches:
                            score += 0.1 * len(word_matches)  
                        
                        if score > best_score:
                            best_score = score
                            best_match = topic
                            best_question = question
                    except Exception:
                        continue

        if best_match and best_score > 0.5:
            return {'message': best_match['answer']}
        else:
            # Try to find a match based on topic names
            topic_match = None
            for topic in dataset:
                topic_name = topic.get('topic', '').lower()
                if any(word in topic_name for word in user_words):
                    topic_match = topic
                    break
            
            if topic_match:
                return {'message': topic_match['answer']}
            else:
                return {
                    'message': "I'm not sure I understand. Here are some topics you can ask about:",
                    'options': [
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
                }