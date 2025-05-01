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
            'click .clear-chatbot': '_clearConversation',
        },

        start: function () {
            this._visitorId = localStorage.getItem('chatbot_visitor_id');
            this._isLoadingConversation = false;
            this._hasInitialized = false;
            this._lastLoadTime = 0;
            
            console.log("[Chatbot] Initial visitor ID from localStorage:", this._visitorId);
            
            return this._super.apply(this, arguments).then(() => {
                this.$('.hide-chatbot').on('click', this._hideChatbot.bind(this));
                
                // Initialize with debounce to prevent multiple initializations
                return this._debouncedInitialize().then(() => {
                    // Add a slight delay to ensure the conversation is loaded before checking options
                    setTimeout(() => {
                        this._ensureFallbackOptions();
                    }, 500);
                });
            });
        },

        _debouncedInitialize: function() {
            if (this._initializePromise) {
                return this._initializePromise;
            }
            
            this._initializePromise = new Promise(resolve => {
                setTimeout(() => {
                    this._initializeChatbot().then(() => {
                        this._initializePromise = null;
                        resolve();
                    });
                }, 100);
            });
            
            return this._initializePromise;
        },

        _initializeChatbot: function() {
            if (this._hasInitialized) {
                return Promise.resolve();
            }

            const now = Date.now();
            if (now - this._lastLoadTime < 500) {
                return Promise.resolve();
            }
            this._lastLoadTime = now;

            return new Promise(resolve => {
                if (this._visitorId) {
                    console.log("[Chatbot] Using existing visitor ID:", this._visitorId);
                    this._setupChatbot()
                        .then(() => this._restoreChatbotState())
                        .then(() => {
                            this._hasInitialized = true;
                            resolve();
                        });
                } else {
                    console.log("[Chatbot] No visitor ID found, getting one...");
                    this._getVisitorId()
                        .then(() => this._setupChatbot())
                        .then(() => this._restoreChatbotState())
                        .then(() => {
                            this._hasInitialized = true;
                            resolve();
                        });
                }
            });
        },

        _getVisitorId: function() {
            console.log("[Chatbot] Requesting visitor ID from server");
            return this._rpc({
                model: 'chatbot.message',
                method: 'get_visitor_from_request',
                args: [],
            }).then(result => {
                if (result && result.visitor_id) {
                    this._visitorId = result.visitor_id;
                    console.log("[Chatbot] Received visitor ID:", this._visitorId);
                    localStorage.setItem('chatbot_visitor_id', this._visitorId);
                    return this._visitorId;
                } else {
                    console.error("[Chatbot] Invalid visitor ID response", result);
                    this._visitorId = localStorage.getItem('chatbot_visitor_id') || 
                                     ('local_' + Math.random().toString(36).substring(2, 9));
                    localStorage.setItem('chatbot_visitor_id', this._visitorId);
                    return this._visitorId;
                }
            }).catch(error => {
                console.error("[Chatbot] Error getting visitor ID:", error);
                this._visitorId = localStorage.getItem('chatbot_visitor_id') || 
                                 ('local_' + Math.random().toString(36).substring(2, 9));
                localStorage.setItem('chatbot_visitor_id', this._visitorId);
                return this._visitorId;
            });
        },

        _setupChatbot: function () {
            console.log("[Chatbot] Setting up chatbot with visitor ID:", this._visitorId);
            return this._loadConversation();
        },

        _loadConversation: function () {
            if (this._isLoadingConversation) {
                console.log("[Chatbot] Already loading conversation, skipping");
                return Promise.resolve();
            }
            
            this._isLoadingConversation = true;
            console.log("[Chatbot] Loading conversation for visitor:", this._visitorId);
            
            return this._rpc({
                model: 'chatbot.message',
                method: 'get_conversation',
                args: [this._visitorId],
            }).then(result => {
                const $chatWindow = this.$('.chat-window');
                $chatWindow.empty();
                
                if (result && result.messages && result.messages.length > 0) {
                    console.log("[Chatbot] Found messages:", result.messages.length);
                    
                    const seenMessages = new Set();
                    let showWelcomeMessage = true;
                    let hasOptionsDisplayed = false; 
                    
                    // First pass - add all messages from history
                    result.messages.forEach(msg => {
                        if (!msg.content || seenMessages.has(msg.content + msg.date)) {
                            return;
                        }
                        
                        // Skip welcome message if found in history
                        if (msg.type === 'bot' && 
                            msg.content.includes("Hi, I can help with your ERP questions")) {
                            showWelcomeMessage = false;
                        }
                        
                        seenMessages.add(msg.content + msg.date);
                        
                        if (msg.type === 'user') {
                            this._addUserMessage(msg.content, true);
                        } else {
                            // Ensure options are parsed properly
                            let options = msg.options;
                            if (typeof options === 'string' && options) {
                                try {
                                    options = JSON.parse(options);
                                } catch (e) {
                                    console.error("[Chatbot] Error parsing options string:", e);
                                    options = null;
                                }
                            }
                            
                            // Check if this message has options
                            if (options && Array.isArray(options) && options.length > 0) {
                                hasOptionsDisplayed = true;
                            }
                            
                            this._addBotMessage(msg.content, null, options, true);
                        }
                    });
                    
                    // Only add welcome message if not found in history
                    if (showWelcomeMessage) {
                        // Add welcome message at the beginning
                        $chatWindow.prepend(this._createWelcomeMessage());
                    }
                    
                    // Check for fallback options
                    if (!hasOptionsDisplayed) {
                        const lastBotMsg = result.messages.reverse().find(msg => msg.type === 'bot');
                        if (lastBotMsg && lastBotMsg.content.includes("I'm not sure I understand")) {
                            // If the last bot message indicates it didn't understand, add main topics
                            this._addBotMessage("I'm not sure I understand. Here are some topics you can ask about:", 
                                null, this._getMainTopics(), true);
                            hasOptionsDisplayed = true;
                        }
                    }
                } else {
                    
                    this._addBotMessage("Hi, I can help with your ERP questions. How can I assist you today?", null, null, true);
                }
                
                this._scrollToBottom();
                this._isLoadingConversation = false;
                return Promise.resolve();
            }).catch(error => {
                console.error("[Chatbot] Error loading conversation:", error);
                const $chatWindow = this.$('.chat-window');
                $chatWindow.empty();
                this._addBotMessage("Hi, I can help with your ERP questions. How can I assist you today?", null, null, true);
                this._isLoadingConversation = false;
                return Promise.resolve();
            });
        },

        _createWelcomeMessage: function() {
            // Helper to create welcome message element
            const messageElement = `
                <div class="message d-flex align-items-start mb-3">
                    <div class="avatar bot-avatar bg-primary rounded-circle d-flex justify-content-center align-items-center text-white" 
                         style="width: 42px; height: 42px; flex-shrink: 0; overflow: hidden; margin-right: 10px;">
                        <img src="/website_custom_chatbot/static/images/chatbot_icon.png" class="img-fluid"/>
                    </div>
                    <div class="message-content bg-white rounded shadow-sm py-3 px-4" 
                         style="max-width: 75%; border-radius: 14px; font-size: 15px; line-height: 1.6;">
                        <p class="m-0">Hi, I can help with your ERP questions. How can I assist you today?</p>
                    </div>
                </div>
            `;
            return messageElement;
        },

        _onSubmit: function (ev) {
            ev.preventDefault();
            const $input = this.$('.chat-query');
            const query = $input.val().trim();

            if (!query) {
                console.log("[Chatbot] Empty query, not sending");
                return;
            }

            $input.val('');
            
            if (!this._visitorId) {
                this._visitorId = localStorage.getItem('chatbot_visitor_id');
                if (!this._visitorId) {
                    return this._getVisitorId().then(() => {
                        this._addUserMessage(query);
                        return this._processUserMessage(query);
                    });
                }
            }
            
            const lastMessage = sessionStorage.getItem('last_message');
            const timestamp = Date.now();
            sessionStorage.setItem('last_message', query + '_' + timestamp);
            
            if (lastMessage === query + '_' + timestamp) {
                console.log("[Chatbot] Duplicate message detected, ignoring");
                return;
            }
            
            this._addUserMessage(query);
            return this._processUserMessage(query);
        },

        _processUserMessage: function(query) {
            console.log("[Chatbot] Processing user message:", query);
            return this._rpc({
                model: 'chatbot.message',
                method: 'process_message',
                args: [query, this._visitorId],
            }).then(response => {
                if (response && response.message) {
                    // Log the response to help debug options
                    console.log("[Chatbot] Received response:", response);
                    
                    // Handle options
                    let options = response.options;
                    if (typeof options === 'string' && options) {
                        try {
                            options = JSON.parse(options);
                        } catch (e) {
                            console.error("[Chatbot] Error parsing options string:", e);
                            options = null;
                        }
                    }
                    
                    this._addBotMessage(response.message, null, options);
                } else {
                    this._addBotMessage("I'm sorry, I couldn't process your request.");
                }
            }).catch(error => {
                console.error("[Chatbot] Error processing user message:", error);
                this._addBotMessage("Sorry, I encountered an error processing your request.");
            });
        },

        _onOptionClick: function (ev) {
            const topic = $(ev.currentTarget).data('topic');
            if (!topic) {
                console.error("[Chatbot] No topic found in option click");
                return;
            }
            
            this._addUserMessage(topic);
            
            return this._rpc({
                model: 'chatbot.message',
                method: 'process_message',
                args: [topic, this._visitorId],
            }).then(response => {
                if (response && response.message) {
                    // Handle options
                    let options = response.options;
                    if (typeof options === 'string' && options) {
                        try {
                            options = JSON.parse(options);
                        } catch (e) {
                            console.error("[Chatbot] Error parsing options from option click:", e);
                            options = null;
                        }
                    }
                    
                    this._addBotMessage(response.message, null, options);
                } else {
                    this._addBotMessage("I'm sorry, I couldn't process your request.");
                }
            }).catch(error => {
                console.error("[Chatbot] Error processing topic:", error);
                this._addBotMessage("Sorry, I encountered an error processing your request.");
            });
        },

        _addUserMessage: function (message, skipSave = false) {
            if (!message) return;
            
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
            if (!message) return;
            
            const $chatWindow = this.$('.chat-window');
            
            // Ensure options are properly parsed
            let parsedOptions = options;
            console.log("[Chatbot] Adding bot message with options:", options);
            
            if (typeof parsedOptions === 'string' && parsedOptions) {
                try {
                    parsedOptions = JSON.parse(parsedOptions);
                    console.log("[Chatbot] Parsed options from string:", parsedOptions);
                } catch (e) {
                    console.error("[Chatbot] Error parsing options string:", e);
                    parsedOptions = null;
                }
            }
            
            // If message indicates topics but no options provided, use main topics
            if (!parsedOptions && message.includes("topics you can ask about")) {
                parsedOptions = this._getMainTopics();
                console.log("[Chatbot] Using main topics as options:", parsedOptions);
            }
            
            let optionsHtml = '';
            if (parsedOptions && Array.isArray(parsedOptions) && parsedOptions.length > 0) {
                optionsHtml = `
                    <div class="options-container d-flex flex-wrap justify-content-center py-3" style="gap: 10px;">
                        ${parsedOptions.map(option => `
                            <button class="option-button btn text-center rounded py-2 px-3 m-1" 
                                    style="background-color: #f0f4ff; border: 1px solid #8e8ff3; color: #6667ab; 
                                          font-size: 14px; font-weight: 500; min-width: 160px; flex: 0 0 auto;
                                          transition: all 0.2s ease; box-shadow: 0 1px 2px rgba(0,0,0,0.05);" 
                                    data-topic="${option}"
                                    onmouseover="this.style.backgroundColor='#e4e9ff'; this.style.boxShadow='0 2px 4px rgba(0,0,0,0.1)';"
                                    onmouseout="this.style.backgroundColor='#f0f4ff'; this.style.boxShadow='0 1px 2px rgba(0,0,0,0.05)';">${option}</button>
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
                         style="max-width: 85%; border-radius: 14px; font-size: 15px; line-height: 1.6;">
                        <p class="m-0">${message}</p>
                        ${optionsHtml}
                    </div>
                </div>
            `;

            $chatWindow.append(messageElement);
            this._scrollToBottom();
            
            if (!skipSave) {
                this._saveMessage('bot', message, parsedOptions);
            }
        },

        _saveMessage: function (messageType, content, options = null) {
            console.log("[Chatbot] Saving message:", messageType, content);
            
            if (!this._visitorId) {
                console.error("[Chatbot] Cannot save message - no visitor ID");
                return Promise.resolve();
            }
            
            return this._rpc({
                model: 'chatbot.message',
                method: 'save_message',
                args: [messageType, content, this._visitorId, options],
            }).catch(error => {
                console.error("[Chatbot] Error saving message:", error);
            });
        },

        _scrollToBottom: function () {
            const $chatWindow = this.$('.chat-window');
            $chatWindow.scrollTop($chatWindow[0].scrollHeight);
        },

        _toggleChatbot: function () {
            const $chatbotContainer = this.$('.chatbot-container');
            const isVisible = $chatbotContainer.hasClass('visible');

            $chatbotContainer.toggleClass('hidden visible');
            localStorage.setItem('chatbot_state', isVisible ? 'closed' : 'open');
        },

        _hideChatbot: function () {
            const $chatbotContainer = this.$('.chatbot-container');
            $chatbotContainer.addClass('hidden').removeClass('visible');
            localStorage.setItem('chatbot_state', 'closed');
        },

        _closeChatbot: function () {
            this._rpc({
                model: 'chatbot.message',
                method: 'clear_conversation',
                args: [this._visitorId],
            }).then(() => {
                this.$('.chat-window').empty();
                this._addBotMessage("Hi, I can help with your ERP questions. How can I assist you today?", null, null, true);
                this._hideChatbot();
            }).catch(error => {
                console.error("[Chatbot] Error closing chatbot:", error);
                this.$('.chat-window').empty();
                this._addBotMessage("Hi, I can help with your ERP questions. How can I assist you today?", null, null, true);
                this._hideChatbot();
            });
        },

        _clearConversation: function () {
            this._rpc({
                model: 'chatbot.message',
                method: 'clear_conversation',
                args: [this._visitorId],
            }).then(() => {
                this.$('.chat-window').empty();
                this._addBotMessage("Hi, I can help with your ERP questions. How can I assist you today?", null, null, true);
            }).catch(error => {
                console.error("[Chatbot] Error clearing conversation:", error);
                this.$('.chat-window').empty();
                this._addBotMessage("Hi, I can help with your ERP questions. How can I assist you today?", null, null, true);
            });
        },

        _restoreChatbotState: function () {
            const state = localStorage.getItem('chatbot_state');
            const $chatbotContainer = this.$('.chatbot-container');

            $chatbotContainer.css('transition', 'none');

            if (state === 'open') {
                $chatbotContainer.removeClass('hidden').addClass('visible');
            } else {
                $chatbotContainer.addClass('hidden').removeClass('visible');
            }

            setTimeout(() => {
                $chatbotContainer.css('transition', '');
            }, 50);
        },

        _getMainTopics: function() {
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
            ];
        },

        _ensureFallbackOptions: function() {
            // Check if there are any option buttons in the chat window
            const hasOptions = this.$('.chat-window .option-button').length > 0;
            
            if (!hasOptions) {
                // If no options are displayed, add a fallback message with options
                const lastBotMsg = this.$('.chat-window .message:not(.user-message)').last();
                
                if (lastBotMsg.length > 0 && 
                    !lastBotMsg.find('.options-container').length && 
                    !lastBotMsg.find('.message-content').text().includes("Hi, I can help with your ERP questions")) {
                    
                    // Add a new bot message with the main topics
                    this._addBotMessage(
                        "I'm not sure I understand. Here are some topics you can ask about:", 
                        null, 
                        this._getMainTopics(), 
                        true
                    );
                }
            }
        },
    });

    return publicWidget.registry.Chatbot;
});