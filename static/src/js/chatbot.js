odoo.define('website_custom_chatbot.chatbot', function (require) {
    'use strict';

    const publicWidget = require('web.public.widget');
    const rpc = require('web.rpc');

    publicWidget.registry.Chatbot = publicWidget.Widget.extend({
        selector: '.chatbot-wrapper',
        events: {
            'submit .chat-form': '_onSubmit',
            'click .option-button': '_onOptionClick',
            'click .chatbot-toggle': '_toggleChatbot',
            'click .close-chatbot': '_closeChatbot',
            'click .clear-chatbot': '_clearConversation',
        },

        start: function () {
            this._welcomeMessageShown = false;
            this._chatHistoryKey = 'craftschoolship_chat_history';

            return this._super.apply(this, arguments).then(() => {
                this.$('.hide-chatbot').on('click', this._hideChatbot.bind(this));

                // Restore the chatbot state on page load
                this._restoreChatbotState();

                return this._setupChatbot();
            });
        },

        _setupChatbot: function () {
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
                
                // Load conversation history from local storage
                this._loadConversation();
            });
        },

        _loadDataset: function () {
            return rpc.query({
                route: '/website_custom_chatbot/load_dataset',
            }).catch(() => {
                console.error("Failed to load dataset.");
                return [];
            });
        },

        _loadConversation: function () {
            const savedData = localStorage.getItem(this._chatHistoryKey);
            if (savedData) {
                const data = JSON.parse(savedData);
                
                // Clear if older than 24 hours
                const TWENTY_FOUR_HOURS = 24 * 60 * 60 * 1000;
                if (new Date().getTime() - data.timestamp > TWENTY_FOUR_HOURS) {
                    this._clearConversation();
                    return;
                }
                
                const $chatWindow = this.$('.chat-window');
                $chatWindow.html('');
                
                data.messages.forEach(msg => {
                    if (msg.type === 'user') {
                        this._addUserMessage(msg.content, true);
                    } else {
                        this._addBotMessage(msg.content, null, msg.options, true);
                    }
                });
                
                this._welcomeMessageShown = true;
                this._scrollToBottom();
            }
        },

        _saveConversation: function () {
            const messages = [];
            this.$('.chat-window .message').each((index, element) => {
                const $element = $(element);
                if ($element.hasClass('user-message')) {
                    messages.push({
                        type: 'user',
                        content: $element.find('.message-content p').text()
                    });
                } else {
                    const options = [];
                    $element.find('.option-button').each((i, btn) => {
                        options.push($(btn).data('topic'));
                    });
                    
                    messages.push({
                        type: 'bot',
                        content: $element.find('.message-content p').text(),
                        options: options.length > 0 ? options : null
                    });
                }
            });
            
            const conversationData = {
                messages: messages,
                timestamp: new Date().getTime()
            };
            
            localStorage.setItem(this._chatHistoryKey, JSON.stringify(conversationData));
        },

        _clearConversation: function () {
            localStorage.removeItem(this._chatHistoryKey);
            this.$('.chat-window').empty();
            this._welcomeMessageShown = false;
            this._addBotMessage("Hi, I can help with your ERP questions. How can I assist you today?");
        },

        _onSubmit: function (ev) {
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
                this._addBotMessage(bestMatch.answer);
            } else {
                this._addBotMessage("Sorry, I don't understand your question. Here are some topics you can ask about:", null, this.mainTopics);
            }
            
            this._saveConversation();
        },

        _onOptionClick: function (ev) {
            const topic = $(ev.currentTarget).data('topic');
            this._addUserMessage(topic);
            this._processTopicSelection(topic);
            this._saveConversation();
        },

        _addUserMessage: function (message, skipSave = false) {
            const $chatWindow = this.$('.chat-window');
            const messageElement = `
                <div class="message user-message">
                    <div class="avatar user-avatar">
                        <img src="/website_custom_chatbot/static/images/user_msg.png"/>
                    </div>
                    <div class="message-content user-message-content">
                        <p>${message}</p>
                    </div>
                </div>
            `;
            $chatWindow.append(messageElement);
            this._scrollToBottom();
            
            if (!skipSave) {
                this._saveConversation();
            }
        },

        _addBotMessage: function (message, topic = null, options = null, skipSave = false) {
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
            }

            const messageElement = `
                <div class="message">
                    <div class="avatar bot-avatar">
                        <img src="/website_custom_chatbot/static/images/chatbot_icon.png"/>
                    </div>
                    <div class="message-content">
                        <p>${message}</p>
                        ${optionsHtml}
                    </div>
                </div>
            `;

            $chatWindow.append(messageElement);
            this._scrollToBottom();
            
            if (!skipSave) {
                this._saveConversation();
            }
        },

        _processTopicSelection: function (topic) {
            const selectedTopic = this.dataset.find(item =>
                item.topic.toLowerCase() === topic.toLowerCase()
            );

            if (selectedTopic) {
                this._addBotMessage(selectedTopic.answer);
            } else {
                this._addBotMessage("Sorry, I couldn't find information about that topic.");
            }
        },

        _findBestMatch: function (query) {
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

        _showMainTopics: function () {
            this._addBotMessage("Here are some topics you can ask about:", null, this.mainTopics);
        },

        _scrollToBottom: function () {
            const $chatWindow = this.$('.chat-window');
            $chatWindow.scrollTop($chatWindow.prop('scrollHeight'));
        },

        _toggleChatbot: function () {
            const $chatbotContainer = this.$('.chatbot-container');
            const isVisible = $chatbotContainer.hasClass('visible');

            if (!isVisible && !this._welcomeMessageShown) {
                this._addBotMessage("Hi, I can help with your ERP questions. How can I assist you today?");
                this._welcomeMessageShown = true;
            }

            $chatbotContainer.toggleClass('hidden visible');

            // Save the chatbot state to localStorage
            localStorage.setItem('chatbot_state', isVisible ? 'closed' : 'open');
        },

        _hideChatbot: function () {
            const $chatbotContainer = this.$('.chatbot-container');
            $chatbotContainer.addClass('hidden').removeClass('visible');

            // Save the chatbot state to localStorage
            localStorage.setItem('chatbot_state', 'closed');
        },

        _closeChatbot: function () {
            // Clear the conversation
            localStorage.removeItem(this._chatHistoryKey);
            this.$('.chat-window').empty();
            this._welcomeMessageShown = false;

            // Hide the chatbot
            const $chatbotContainer = this.$('.chatbot-container');
            $chatbotContainer.addClass('hidden').removeClass('visible');

            // Save the chatbot state to localStorage
            localStorage.setItem('chatbot_state', 'closed');
        },

        _restoreChatbotState: function () {
            const state = localStorage.getItem('chatbot_state');
            const $chatbotContainer = this.$('.chatbot-container');

            if (state === 'open') {
                // Directly set the visibility without triggering animations
                $chatbotContainer.removeClass('hidden').addClass('visible').css('transition', 'none');
            } else {
                // Directly set the visibility without triggering animations
                $chatbotContainer.addClass('hidden').removeClass('visible').css('transition', 'none');
            }
        },
    });
});