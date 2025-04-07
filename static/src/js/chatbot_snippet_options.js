odoo.define('website_custom_chatbot.snippet_options', function (require) {
    'use strict';

    const options = require('web_editor.snippets.options');

    options.registry.ChatbotOptions = options.Class.extend({

        onFocus: function () {
            this.$target.addClass('active');
        },

        onBlur: function () {
            this.$target.removeClass('active');
        },

        _updateGlobalStyle: function (property, value) {
            let styleTag = document.getElementById('chatbot-global-style');
            if (!styleTag) {
                styleTag = document.createElement('style');
                styleTag.id = 'chatbot-global-style';
                document.head.appendChild(styleTag);
            }

            const cssRules = styleTag.sheet.cssRules || styleTag.sheet.rules;
            let ruleFound = false;

            
            for (let i = 0; i < cssRules.length; i++) {
                if (cssRules[i].selectorText === '.chatbot-container') {
                    cssRules[i].style[property] = value || '';
                    ruleFound = true;
                    break;
                }
            }

            
            if (!ruleFound) {
                styleTag.sheet.insertRule(`.chatbot-container { ${property}: ${value || ''}; }`, cssRules.length);
            }
        },

        changeBackgroundColor: function (previewMode, value, $opt) {
            this._updateGlobalStyle('background-color', value);
        },

        changeTextColor: function (previewMode, value, $opt) {
            this._updateGlobalStyle('color', value);
        },

        changeButtonColor: function (previewMode, value, $opt) {
            let styleTag = document.getElementById('chatbot-global-style');
            if (!styleTag) {
                styleTag = document.createElement('style');
                styleTag.id = 'chatbot-global-style';
                document.head.appendChild(styleTag);
            }

            const cssRules = styleTag.sheet.cssRules || styleTag.sheet.rules;
            let ruleFound = false;

            
            for (let i = 0; i < cssRules.length; i++) {
                if (cssRules[i].selectorText === '.chatbot-toggle, .submit-btn') {
                    cssRules[i].style['background-color'] = value || '';
                    ruleFound = true;
                    break;
                }
            }

            
            if (!ruleFound) {
                styleTag.sheet.insertRule(`.chatbot-toggle, .submit-btn { background-color: ${value || ''}; }`, cssRules.length);
            }
        },

        _updateChatbotIcon: function (iconUrl) {
            
            const chatbotIcon = document.querySelector('.chatbot-toggle img');
            if (chatbotIcon) {
                chatbotIcon.src = iconUrl;
            }

            
            localStorage.setItem('chatbotIcon', iconUrl);
        },

        changeChatbotIcon: function (previewMode, value, $opt) {
           
            this._updateChatbotIcon(value);
        },

        _loadChatbotIcon: function () {
          
            const savedIconUrl = localStorage.getItem('chatbotIcon');
            if (savedIconUrl) {
                const chatbotIcon = document.querySelector('.chatbot-toggle img');
                if (chatbotIcon) {
                    chatbotIcon.src = savedIconUrl;
                } else {
                   
                    setTimeout(() => this._loadChatbotIcon(), 100);
                }
            }
        },

        start: function () {
            this._super.apply(this, arguments);
            
            document.addEventListener('DOMContentLoaded', () => {
                this._loadChatbotIcon();
            });
        },
    });
});