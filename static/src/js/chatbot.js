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
            'click .close-chatbot': '_onCloseChatbot',
            'click .minimize-chatbot': '_onMinimizeChatbot',
            'change .language-selector': '_onLanguageChange',
            'click .lang-option': '_onLangOptionClick',
            'click .settings-btn': '_onSettingsClick'
        },

        start: function () {
            this.language = 'en'; // Default language
            this.isLanguageDropdownOpen = false;
            
            // Close language dropdown when clicking outside
            $(document).on('click', this._onDocumentClick.bind(this));
            
            return this._super.apply(this, arguments).then(() => {
                // Set initial language from selector
                this.language = this.$('.language-selector').val();
                // Update language dropdown UI
                this._updateLanguageDropdownUI();
                return this._loadExistingConversation();
            });
        },
        
        _onDocumentClick: function(ev) {
            // Close dropdown when clicking outside
            if (this.isLanguageDropdownOpen && 
                !$(ev.target).closest('.language-settings-wrapper').length) {
                this._closeLanguageDropdown();
            }
        },

        _onSettingsClick: function(ev) {
            ev.preventDefault();
            ev.stopPropagation();
            
            if (this.isLanguageDropdownOpen) {
                this._closeLanguageDropdown();
            } else {
                this._openLanguageDropdown();
            }
        },
        
        _openLanguageDropdown: function() {
            this.$('.language-dropdown').removeClass('d-none');
            this.isLanguageDropdownOpen = true;
        },
        
        _closeLanguageDropdown: function() {
            this.$('.language-dropdown').addClass('d-none');
            this.isLanguageDropdownOpen = false;
        },

        _onLangOptionClick: function(ev) {
            const $target = $(ev.currentTarget);
            const newLang = $target.data('lang');
            
            if (newLang) {
                this.$('.language-selector').val(newLang).trigger('change');
                this._closeLanguageDropdown();
            }
        },

        _updateLanguageDropdownUI: function() {
            // Update active state in dropdown
            this.$('.lang-option').removeClass('active');
            this.$('.lang-option[data-lang="' + this.language + '"]').addClass('active');
        },

        _onLanguageChange: function(ev) {
            const oldLanguage = this.language;
            this.language = $(ev.currentTarget).val();
            
            // Update the language dropdown UI
            this._updateLanguageDropdownUI();
            
            // Clear chat window
            this._clearChatWindow();
            
            // Reload conversation in new language
            return this._loadExistingConversation();
            
            // Update lang attribute for accessibility
            this.$('.chat-window').attr('lang', this.language);
        },

        _showWelcomeMessage: function() {
            const welcomeMessage = this.language === 'en' ? 
                "👋 Hello! I'm your CraftEd Assistant. I can help you with questions about our products and services. What would you like to know?" :
                "👋 Bonjour ! Je suis votre assistant CraftEd. Je peux vous aider avec des questions sur nos produits et services. Que souhaitez-vous savoir ?";
            
            this._addBotMessage(welcomeMessage, null);
        },

        _loadExistingConversation: function() {
            const self = this;
            
            // Always show welcome message first, regardless of existing messages
            self._showWelcomeMessage();
            
            return this._rpc({
                model: 'chatbot.message',
                method: 'search_read',
                args: [[['visitor_id', '=', this.getSession().visitor_id]]],
                kwargs: {
                    fields: ['request', 'response', 'options', 'language'],
                    context: {'current_lang': this.language} // Pass current language preference
                }
            }).then(messages => {
                // Process existing messages if any
                if (messages && messages.length > 0) {
                    messages.forEach(msg => {
                        if (msg.request) {
                            self._addUserMessage(msg.request);
                        }
                        if (msg.response) {
                            let options = msg.options ? JSON.parse(msg.options) : null;
                            self._addBotMessage(msg.response, options);
                        }
                    });
                }
            }).catch(error => {
                console.error("Error loading conversation:", error);
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
                    'language': this.language // Send current language with request
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

        _addUserMessage: function (message) {
            if (!message) return;
            
            const $chatWindow = this.$('.chat-window');
            $chatWindow.append(`
                <div class="message user-message d-flex align-items-start justify-content-end mb-4">
                    <div class="message-content py-3 px-4 rounded shadow-sm text-white" 
                         style="max-width: 80%; background: linear-gradient(135deg, #4F46E5, #7e7df7); border-radius: 18px; font-size: 15px; line-height: 1.6; margin-right: 10px;">
                        <p class="m-0">${message}</p>
                    </div>
                    <div class="avatar user-avatar rounded-circle d-flex justify-content-center align-items-center bg-white" 
                         style="width: 42px; height: 42px; flex-shrink: 0; overflow: hidden; box-shadow: 0 3px 8px rgba(0,0,0,0.05);">
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
                    <div class="options-container d-flex flex-column py-3" style="gap: 8px;">
                        ${options.map(option => `
                            <button class="option-button btn text-center rounded py-2 px-3 w-100" 
                                    style="background-color: rgba(79, 70, 229, 0.05); border: 1px solid rgba(79, 70, 229, 0.2); 
                                          color: #4F46E5; border-radius: 12px; font-size: 14px; font-weight: 500; 
                                          transition: all 0.2s ease;" 
                                    data-topic="${option}">${option}</button>
                        `).join('')}
                    </div>
                `;
            }

            $chatWindow.append(`
                <div class="message d-flex align-items-start mb-4">
                    <div class="avatar bot-avatar rounded-circle d-flex justify-content-center align-items-center" 
                         style="width: 42px; height: 42px; flex-shrink: 0; overflow: hidden; margin-right: 10px; 
                                background: linear-gradient(135deg, #4F46E5, #7e7df7); box-shadow: 0 3px 8px rgba(79, 70, 229, 0.2);">
                        <img src="/website_custom_chatbot/static/images/chatbot_icon.png" class="img-fluid p-1"/>
                    </div>
                    <div class="message-content bg-white rounded shadow-sm py-3 px-4" 
                         style="max-width: 85%; border-radius: 18px; font-size: 15px; line-height: 1.6; position: relative;">
                        <p class="m-0">${message}</p>
                        ${optionsHtml}
                    </div>
                </div>
            `);
            this._scrollToBottom();
        },

        _clearChatWindow: function() {
            this.$('.chat-window').empty();
        },

        _scrollToBottom: function () {
            const $chatWindow = this.$('.chat-window');
            $chatWindow.scrollTop($chatWindow[0].scrollHeight);
        },

        _toggleChatbot: function () {
            this.$('.chatbot-container').toggleClass('hidden visible');
        },

        _onCloseChatbot: function () {
            const self = this;
            // Clear the chat window
            this._clearChatWindow();

            // Delete all messages for this visitor from the database
            this._rpc({
                model: 'chatbot.message',
                method: 'search_unlink',
                args: [[['visitor_id', '=', this.getSession().visitor_id]]],
            }).then(() => {
                // Show welcome message again
                self._showWelcomeMessage();
                // Hide the chatbot
                self.$('.chatbot-container').addClass('hidden').removeClass('visible');
            });
        },

        _onMinimizeChatbot: function () {
            this.$('.chatbot-container').addClass('hidden').removeClass('visible');
        }
    });

    return publicWidget.registry.Chatbot;
});