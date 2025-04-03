odoo.define('website_custom_chatbot.chatbot', function (require) {
    'use strict';

    const publicWidget = require('web.public.widget');
    const rpc = require('web.rpc');

    publicWidget.registry.Chatbot = publicWidget.Widget.extend({
        selector: '.s_chatbot',
        events: {
            'submit .chat-form': '_onSubmit',
            'click .option-button': '_onOptionClick',
        },

        start: function () {
            return this._super.apply(this, arguments).then(() => {
                return this._setupChatbot();
            });
        },

        _setupChatbot: function() {
            return this._loadDataset().then((dataset) => {
                this.dataset = dataset || [];
                if (this.dataset.length === 0) {
                    this._addBotMessage("Sorry, the chatbot dataset is unavailable at the moment.");
                    return;
                }
                this.mainTopics = [
                    "CraftSchoolship Overview",
                    "CraftEd ERP",
                    "CraftEd LMS",
                    "CraftEd Chat",
                    "CraftEd Meet",
                    "CraftEd AI",
                    "CraftEd Mobile",
                    "CraftEd Workspace",
                    "CraftEd Universe"
                ];
                this._showMainTopics();
            });
        },

        _loadDataset: function() {
            return rpc.query({
                route: '/website_custom_chatbot/load_dataset',
            }).catch(() => {
                console.error("Failed to load dataset.");
                return [];
            });
        },

        _showMainTopics: function() {
            const $chatWindow = this.$('.chat-window');
            $chatWindow.empty();
            
            const message = `
                <div class="message">
                    <div class="avatar bot-avatar">
                        <img src="/website_custom_chatbot/static/src/images/CraftChat_2-02.png"/>
                    </div>
                    <div class="message-content">
                        <p>Here are some topics you can ask about:</p>
                        <div class="options-container">
                            ${this.mainTopics.map(topic => `
                                <button class="option-button" data-topic="${topic}">${topic}</button>
                            `).join('')}
                        </div>
                    </div>
                </div>
            `;
            
            $chatWindow.append(message);
            this._scrollToBottom();
        },

        _onSubmit: function(ev) {
            ev.preventDefault();
            const $input = this.$('.chat-query');
            const query = $input.val().trim();
            
            if (!query) return;
            
            $input.val('');
            this._addUserMessage(query);
            
            if (query.toLowerCase() === "help" || query.toLowerCase() === "hi") {
                this._showMainTopics();
                return;
            }
            
            const bestMatch = this._findBestMatch(query);
            if (bestMatch) {
                this._addBotMessage(bestMatch.answer, bestMatch.topic);
            } else {
                this._addBotMessage("Sorry, I don't understand your question. Here are some topics you can ask about:", null, this.mainTopics);
            }
        },

        _onOptionClick: function(ev) {
            const topic = $(ev.currentTarget).data('topic');
            this._addUserMessage(topic);
            this._processTopicSelection(topic);
        },

        _addUserMessage: function(message) {
            const $chatWindow = this.$('.chat-window');
            const messageElement = `
                <div class="message user-message">
                    <div class="avatar user-avatar">
                        <img src="/website_custom_chatbot/static/src/images/user_msg.jpeg"/>
                    </div>
                    <div class="message-content user-message-content">
                        <p>${message}</p>
                    </div>
                </div>
            `;
            $chatWindow.append(messageElement);
            this._scrollToBottom();
        },

        _addBotMessage: function(message, topic = null, options = null) {
            const $chatWindow = this.$('.chat-window');
            
            let optionsHtml = '';
            if (options) {
                optionsHtml = `
                    <div class="options-container">
                        ${options.map(option => `
                            <button class="option-button" data-topic="${option}">${option}</button>
                        `).join('')}
                    </div>
                `;
            } else if (topic) {
                const relatedSubtopics = this._getRelatedSubtopics(topic);
                if (relatedSubtopics.length) {
                    optionsHtml = `
                        <p>Related topics:</p>
                        <div class="options-container">
                            ${relatedSubtopics.map(subtopic => `
                                <button class="option-button" data-topic="${subtopic}">${subtopic}</button>
                            `).join('')}
                        </div>
                    `;
                }
            }
            
            const messageElement = `
                <div class="message">
                    <div class="avatar bot-avatar">
                        <img src="/website_custom_chatbot/static/src/images/CraftChat_2-02.jpeg"/>
                    </div>
                    <div class="message-content">
                        <p>${message}</p>
                        ${optionsHtml}
                    </div>
                </div>
            `;
            
            $chatWindow.append(messageElement);
            this._scrollToBottom();
        },

        _processTopicSelection: function(topic) {
            const selectedTopic = this.dataset.find(item => 
                item.topic.toLowerCase() === topic.toLowerCase()
            );
            
            if (selectedTopic) {
                this._addBotMessage(selectedTopic.answer, selectedTopic.topic);
            } else {
                this._addBotMessage("Sorry, I couldn't find information about that topic.", null, [
                    "Back to Main Topics"
                ]);
            }
        },

        _getRelatedSubtopics: function(mainTopic) {
            const relatedTopics = this.dataset.filter(topic =>
                topic.topic.toLowerCase() !== mainTopic.toLowerCase() &&
                topic.topic.toLowerCase().includes(mainTopic.toLowerCase())
            );
            return [...new Set(relatedTopics.map(topic => topic.topic))];
        },

        _findBestMatch: function(query) {
            let bestMatch = null;
            let bestScore = 0;
            
            const queryWords = query.toLowerCase().split(/\s+/);
            
            this.dataset.forEach(topic => {
                topic.questions.forEach(question => {
                    const questionWords = question.toLowerCase().split(/\s+/);
                    const commonWords = queryWords.filter(word => 
                        questionWords.includes(word)
                    );
                    const score = commonWords.length / Math.max(
                        queryWords.length, 
                        questionWords.length
                    );
                    
                    if (score > bestScore) {
                        bestScore = score;
                        bestMatch = topic;
                    }
                });
            });
            
            return bestMatch;
        },

        _scrollToBottom: function() {
            const $chatWindow = this.$('.chat-window');
            $chatWindow.scrollTop($chatWindow[0].scrollHeight);
        },
    });
});