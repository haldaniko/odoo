# -*- coding: utf-8 -*-
{
    'name': 'AI Contact Import',
    'version': '1.0',
    'category': 'Contacts',
    'summary': 'Import contacts from spreadsheets with AI column mapping',
    'depends': ['contacts', 'base_import'],
    'data': [
        'security/ir.model.access.csv',
        'views/ai_contact_import_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'ai_contact_import/static/src/js/ai_contact_import_action.js',
            'ai_contact_import/static/src/js/ai_contact_import_menu.js',
            'ai_contact_import/static/src/scss/ai_contact_import.scss',
            'ai_contact_import/static/src/xml/ai_contact_import.xml',
        ],
    },
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}

