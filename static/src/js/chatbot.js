odoo.define('website_custom_chatbot.chatbot', function (require) {
    'use strict';

    const publicWidget = require('web.public.widget');
    const core = require('web.core');
    const _t = core._t;

    publicWidget.registry.Chatbot = publicWidget.Widget.extend({
        selector: '.chatbot-wrapper',
        events: {
            'submit .chat-form': '_onSubmit',
            'click .option-button': '_onOptionClick',
            'click .chatbot-toggle': '_toggleChatbot',
            'click .close-chatbot': '_closeChatbot',
        },

        start: function () {
            return this._super.apply(this, arguments).then(() => {
                // Show welcome message without options
                this._addBotMessage(
                    "👋 Hello! I'm your CraftEd Assistant. I can help you with questions about our products and services. What would you like to know?",
                    null,
                    true
                );
                return this._loadExistingConversation();
            });
        },

        _loadExistingConversation: function() {
            return this._rpc({
                model: 'chatbot.message',
                method: 'search_read',
                args: [[['visitor_id', '=', this.getSession().visitor_id]]],
                kwargs: {
                    fields: ['request', 'response', 'options']
                }
            }).then(messages => {
                const $chatWindow = this.$('.chat-window');
                $chatWindow.empty();

                // Always show welcome message first
                this._addBotMessage(
                    "👋 Hello! I'm your CraftEd Assistant. I can help you with questions about our products and services. What would you like to know?",
                    null,
                    true
                );

                // Then append existing conversation if any
                if (messages && messages.length > 0) {
                    messages.forEach(msg => {
                        if (msg.request) {
                            this._addUserMessage(msg.request, true);
                        }
                        if (msg.response) {
                            let options = msg.options ? JSON.parse(msg.options) : null;
                            this._addBotMessage(msg.response, options, true);
                        }
                    });
                }
            });
        },

        _onSubmit: function (ev) {
            ev.preventDefault();
            const $input = this.$('.chat-query');
            const query = $input.val().trim();

            if (!query) return;

            $input.val('');
            this._sendMessage(query);
        },

        _onOptionClick: function (ev) {
            const topic = $(ev.currentTarget).data('topic');
            if (!topic) return;
            
            this._sendMessage(topic);
        },

        _sendMessage: function(message) {
            if (!message) return;
            
            this._addUserMessage(message);
            
            return this._rpc({
                model: 'chatbot.message',
                method: 'create',
                args: [{
                    'request': message,
                    'visitor_id': this.getSession().visitor_id,
                }],
            }).then(messageId => {
                return this._rpc({
                    model: 'chatbot.message',
                    method: 'read',
                    args: [messageId, ['response', 'options']]
                });
            }).then(result => {
                if (result && result.length > 0) {
                    const botMessage = result[0];
                    const options = botMessage.options ? JSON.parse(botMessage.options) : null;
                    this._addBotMessage(botMessage.response, options);
                }
            });
        },

        _getDefaultOptions: function() {
            return [
                "CraftEd ERP",
                "CraftEd LMS",
                "CraftEd Chat",
                "CraftEd Meet",
                "CraftEd AI",
                "CraftEd Mobile",
                "CraftEd Workspace",
                "CraftEd Universe"
            ];
        },

        _addUserMessage: function (message) {
            if (!message) return;
            
            const $chatWindow = this.$('.chat-window');
            $chatWindow.append(`
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
            `);
            this._scrollToBottom();
        },

        _addBotMessage: function (message, options) {
            if (!message) return;
            
            const $chatWindow = this.$('.chat-window');
            let optionsHtml = '';
            
            if (options && options.length > 0) {
                optionsHtml = `
                    <div class="options-container d-flex flex-wrap justify-content-center py-3" style="gap: 10px;">
                        ${options.map(option => `
                            <button class="option-button btn text-center rounded py-2 px-3 m-1" 
                                    style="background-color: #f0f4ff; border: 1px solid #8e8ff3; color: #6667ab; 
                                          font-size: 14px; font-weight: 500; min-width: 160px; flex: 0 0 auto;
                                          transition: all 0.2s ease; box-shadow: 0 1px 2px rgba(0,0,0,0.05);" 
                                    data-topic="${option}">${option}</button>
                        `).join('')}
                    </div>
                `;
            }

            $chatWindow.append(`
                <div class="message d-flex align-items-start mb-3">
                    <div class="avatar bot-avatar bg-primary rounded-circle d-flex justify-content-center align-items-center text-white" 
                         style="width: 42px; height: 42px; flex-shrink: 0; overflow: hidden; margin-right: 10px;">
                        <img src="/website_custom_chatbot/static/images/chatbot_icon.png" class="img-fluid"/>
                    </div>
                    <div class="message-content bg-white rounded shadow-sm py-3 px-4" 
                         style="max-width: 85%; border-radius: 14px; font-size: 15px; line-height: 1.6;">
                        <p class="m-0">${message}</p>
                        ${optionsHtml}
                    </div>
                </div>
            `);
            this._scrollToBottom();
        },

        _scrollToBottom: function () {
            const $chatWindow = this.$('.chat-window');
            $chatWindow.scrollTop($chatWindow[0].scrollHeight);
        },

        _toggleChatbot: function () {
            this.$('.chatbot-container').toggleClass('hidden visible');
        },

        _closeChatbot: function () {
            this.$('.chatbot-container').addClass('hidden').removeClass('visible');
        }
    });

    return publicWidget.registry.Chatbot;
});