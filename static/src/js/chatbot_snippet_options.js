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

      
        changeBackgroundColor: function (previewMode, value, $opt) {
            this.$target.find('.chatbot-container').css('background-color', value || '');
        },

        changeTextColor: function (previewMode, value, $opt) {
            this.$target.find('.chat-window, .chat-header').css('color', value || '');
        },

     
        changeButtonColor: function (previewMode, value, $opt) {
            this.$target.find('.chatbot-toggle, .submit-btn').css('background-color', value || '');
        },
    });
});