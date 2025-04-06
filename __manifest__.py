{
    'name': 'Website Custom Chatbot',
    'version': '1.0',
    'category': 'Website',
    'summary': 'Adds a custom chatbot snippet to the website builder',
    'description': """
        This module adds a customizable chatbot widget that can be dragged and dropped
        onto any Odoo website page.
    """,
    'author': 'Bouthayna',
    'website': 'https://yourwebsite.com',
    'depends': ['website'],
    'data': [
        'views/chatbot_template.xml',  # Keep only this file
    ],
    'assets': {
        'web.assets_frontend': [
            'website_custom_chatbot/static/src/js/chatbot.js',
            'website_custom_chatbot/static/src/js/chatbot_snippet_options.js',
            'website_custom_chatbot/static/src/scss/chatbot.scss',
        ],
    },
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
    'auto_install': False,
}