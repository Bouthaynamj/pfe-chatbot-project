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
            this._sessionId = this._generateSessionId();
            this._welcomeMessageShown = false;
            this._chatHistoryKey = 'craftschoolship_chat_history';

            return this._super.apply(this, arguments).then(() => {
                this.$('.hide-chatbot').on('click', this._hideChatbot.bind(this));
                this._restoreChatbotState();
                this._setupChatbot();
            });
        },

        _generateSessionId: function () {
            return 'session_' + Math.random().toString(36).substr(2, 9);
        },

        _setupChatbot: function () {
            this._loadConversation();
            
            if (!this._welcomeMessageShown) {
                this._addBotMessage("Hi, I can help with your ERP questions. How can I assist you today?");
                this._welcomeMessageShown = true;
            }
        },

        _loadConversation: function () {
            const savedData = localStorage.getItem(this._chatHistoryKey);
            if (savedData) {
                const data = JSON.parse(savedData);
                
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

        _onSubmit: function (ev) {
            ev.preventDefault();
            const $input = this.$('.chat-query');
            const query = $input.val().trim();

            if (!query) return;

            $input.val('');
            this._addUserMessage(query);

            rpc.query({
                route: '/website_custom_chatbot/process_message',
                params: { 
                    message: query,
                    session_id: this._sessionId
                },
            }).then(response => {
                this._addBotMessage(response.message, null, response.options);
                this._saveConversation();
            }).catch(error => {
                console.error("Error processing message:", error);
                this._addBotMessage("Sorry, I encountered an error processing your request.");
                this._saveConversation();
            });
        },

        _onOptionClick: function (ev) {
            const topic = $(ev.currentTarget).data('topic');
            this._addUserMessage(topic);
            
            rpc.query({
                route: '/website_custom_chatbot/process_message',
                params: { 
                    message: topic,
                    session_id: this._sessionId
                },
            }).then(response => {
                this._addBotMessage(response.message, null, response.options);
                this._saveConversation();
            }).catch(error => {
                console.error("Error processing topic:", error);
                this._addBotMessage("Sorry, I encountered an error processing your request.");
                this._saveConversation();
            });
        },

        _addUserMessage: function (message, skipSave = false) {
            const $chatWindow = this.$('.chat-window');
            const messageElement = `
                <div class="message user-message d-flex align-items-start justify-content-end mb-3">
                    <div class="message-content py-3 px-4 rounded shadow-sm text-white" 
                         style="max-width: 75%; background-color: #4F46E5; border-radius: 14px; font-size: 15px; line-height: 1.6; margin-right: 10px;">
                        <p class="m-0">${message}</p>
                    </div>
                    <div class="avatar user-avatar rounded-circle d-flex justify-content-center align-items-center bg-light text-secondary" 
                         style="width: 42px; height: 42px; flex-shrink: 0; overflow: hidden;">
                        <img src="/website_custom_chatbot/static/images/user_msg.png" class="img-fluid"/>
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
                    <div class="options-container d-flex flex-column py-2" style="gap: 10px;">
                        ${options.map(option => `
                            <button class="option-button btn text-center rounded border" 
                                    style="background-color: #f0f4ff; border-color: #8e8ff3; color: #6667ab; font-size: 14px; font-weight: 500;" 
                                    data-topic="${option}">${option}</button>
                        `).join('')}
                    </div>
                `;
            }

            const messageElement = `
                <div class="message d-flex align-items-start mb-3">
                    <div class="avatar bot-avatar bg-primary rounded-circle d-flex justify-content-center align-items-center text-white" 
                         style="width: 42px; height: 42px; flex-shrink: 0; overflow: hidden; margin-right: 10px;">
                        <img src="/website_custom_chatbot/static/images/chatbot_icon.png" class="img-fluid"/>
                    </div>
                    <div class="message-content bg-white rounded shadow-sm py-3 px-4" 
                         style="max-width: 75%; border-radius: 14px; font-size: 15px; line-height: 1.6;">
                        <p class="m-0">${message}</p>
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
            localStorage.setItem('chatbot_state', isVisible ? 'closed' : 'open');
        },

        _hideChatbot: function () {
            const $chatbotContainer = this.$('.chatbot-container');
            $chatbotContainer.addClass('hidden').removeClass('visible');
            localStorage.setItem('chatbot_state', 'closed');
        },

        _closeChatbot: function () {
            localStorage.removeItem(this._chatHistoryKey);
            this.$('.chat-window').empty();
            this._welcomeMessageShown = false;

            const $chatbotContainer = this.$('.chatbot-container');
            $chatbotContainer.addClass('hidden').removeClass('visible');
            localStorage.setItem('chatbot_state', 'closed');
        },

        _clearConversation: function () {
            localStorage.removeItem(this._chatHistoryKey);
            this.$('.chat-window').empty();
            this._welcomeMessageShown = false;
            this._addBotMessage("Hi, I can help with your ERP questions. How can I assist you today?");
        },

        _restoreChatbotState: function () {
            const state = localStorage.getItem('chatbot_state');
            const $chatbotContainer = this.$('.chatbot-container');

            if (state === 'open') {
                $chatbotContainer.removeClass('hidden').addClass('visible').css('transition', 'none');
            } else {
                $chatbotContainer.addClass('hidden').removeClass('visible').css('transition', 'none');
            }
        },
    });
});