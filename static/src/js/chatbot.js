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
            this._visitorId = null;
            
            // Set initial state to closed
            localStorage.setItem('chatbot_state', 'closed');
            
            return this._super.apply(this, arguments).then(() => {
                this.$('.hide-chatbot').on('click', this._hideChatbot.bind(this));
                return this._getVisitorId().then(() => {
                    this._setupChatbot();
                    return this._restoreChatbotState();
                });
            });
        },

        _getVisitorId: function() {
            return rpc.query({
                route: '/website_custom_chatbot/get_visitor_id',
            }).then(result => {
                this._visitorId = result.visitor_id;
                return this._visitorId;
            }).catch(error => {
                console.error("Error getting visitor ID:", error);
                // Fallback to random ID if RPC fails
                this._visitorId = 'local_' + Math.random().toString(36).substr(2, 9);
                return this._visitorId;
            });
        },

        _setupChatbot: function () {
            this._loadConversation();
        },

        _loadConversation: function () {
            return rpc.query({
                route: '/website_custom_chatbot/get_conversation',
                params: { visitor_id: this._visitorId },
            }).then(result => {
                const $chatWindow = this.$('.chat-window');
                $chatWindow.empty();
                
                if (result.messages && result.messages.length > 0) {
                    result.messages.forEach(msg => {
                        if (msg.type === 'user') {
                            this._addUserMessage(msg.content, true);
                        } else {
                            this._addBotMessage(msg.content, null, msg.options, true);
                        }
                    });
                } else {
                    // Show welcome message if no conversation exists
                    this._addBotMessage("Hi, I can help with your ERP questions. How can I assist you today?", null, null, true);
                }
                this._scrollToBottom();
            }).catch(error => {
                console.error("Error loading conversation:", error);
                this._addBotMessage("Hi, I can help with your ERP questions. How can I assist you today?", null, null, true);
            });
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
                    visitor_id: this._visitorId
                },
            }).then(response => {
                this._addBotMessage(response.message, null, response.options);
            }).catch(error => {
                console.error("Error processing message:", error);
                this._addBotMessage("Sorry, I encountered an error processing your request.");
            });
        },

        _onOptionClick: function (ev) {
            const topic = $(ev.currentTarget).data('topic');
            this._addUserMessage(topic);
            
            rpc.query({
                route: '/website_custom_chatbot/process_message',
                params: { 
                    message: topic,
                    visitor_id: this._visitorId
                },
            }).then(response => {
                this._addBotMessage(response.message, null, response.options);
            }).catch(error => {
                console.error("Error processing topic:", error);
                this._addBotMessage("Sorry, I encountered an error processing your request.");
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
                this._saveMessage('user', message);
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
                this._saveMessage('bot', message, options);
            }
        },

        _saveMessage: function (messageType, content, options = null) {
            return rpc.query({
                route: '/website_custom_chatbot/save_message',
                params: { 
                    message_type: messageType,
                    content: content,
                    options: options,
                    visitor_id: this._visitorId
                },
            }).catch(error => {
                console.error("Error saving message:", error);
            });
        },

        _scrollToBottom: function () {
            const $chatWindow = this.$('.chat-window');
            $chatWindow.scrollTop($chatWindow.prop('scrollHeight'));
        },

        _toggleChatbot: function () {
            const $chatbotContainer = this.$('.chatbot-container');
            const isVisible = $chatbotContainer.hasClass('visible');

            if (isVisible) {
         
                $chatbotContainer.toggleClass('hidden visible');
                localStorage.setItem('chatbot_state', 'closed');
            } else {
       
                $chatbotContainer.toggleClass('hidden visible');
                localStorage.setItem('chatbot_state', 'open');
                
            
            }
        },

        _hideChatbot: function () {
            // Just hide the chatbot without clearing the conversation
            const $chatbotContainer = this.$('.chatbot-container');
            $chatbotContainer.addClass('hidden').removeClass('visible');
            localStorage.setItem('chatbot_state', 'closed');
            
            // Don't clear the chat window or call the clear_conversation endpoint
        },

        _closeChatbot: function () {
            rpc.query({
                route: '/website_custom_chatbot/clear_conversation',
                params: { visitor_id: this._visitorId },
            }).then(() => {
                this.$('.chat-window').empty();
                // Add welcome message before hiding
                this._addBotMessage("Hi, I can help with your ERP questions. How can I assist you today?", null, null, true);
                
                const $chatbotContainer = this.$('.chatbot-container');
                $chatbotContainer.addClass('hidden').removeClass('visible');
                localStorage.setItem('chatbot_state', 'closed');
            }).catch(error => {
                console.error("Error clearing conversation:", error);
                // Still add the welcome message even if clearing fails
                this.$('.chat-window').empty();
                this._addBotMessage("Hi, I can help with your ERP questions. How can I assist you today?", null, null, true);
            });
        },

        _clearConversation: function () {
            rpc.query({
                route: '/website_custom_chatbot/clear_conversation',
                params: { visitor_id: this._visitorId },
            }).then(() => {
                this.$('.chat-window').empty();
                this._addBotMessage("Hi, I can help with your ERP questions. How can I assist you today?", null, null, true);
            }).catch(error => {
                console.error("Error clearing conversation:", error);
                this.$('.chat-window').empty();
                this._addBotMessage("Hi, I can help with your ERP questions. How can I assist you today?", null, null, true);
            });
        },

        _restoreChatbotState: function () {
            // Get saved state, default to 'closed' if not set
            const state = localStorage.getItem('chatbot_state') || 'closed';
            const $chatbotContainer = this.$('.chatbot-container');

            if (state === 'open') {
                $chatbotContainer.removeClass('hidden').addClass('visible').css('transition', 'none');
                // Load conversation if there is one, otherwise show welcome message
                this._loadConversation();
            } else {
                // Default state - chatbot is hidden
                $chatbotContainer.addClass('hidden').removeClass('visible').css('transition', 'none');
                
                // Make sure the state is saved as closed
                localStorage.setItem('chatbot_state', 'closed');
            }
        },
    });
});