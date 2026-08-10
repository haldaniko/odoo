# -*- coding: utf-8 -*-

import base64
import html
import json
import logging
import os
import re

import requests

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools.mimetypes import guess_mimetype

_logger = logging.getLogger(__name__)

OPENROUTER_URL = 'https://openrouter.ai/api/v1/chat/completions'
DEFAULT_MODEL = 'google/gemini-2.5-flash-lite'

SUPPORTED_FIELDS = {
    'name': 'Full contact or company name',
    'email': 'Email address',
    'phone': 'Phone number',
    'mobile': 'Mobile phone number',
    'website': 'Website URL',
    'function': 'Job position',
    'company_name': 'Company name as plain text',
    'street': 'Street address',
    'street2': 'Street address line 2',
    'city': 'City',
    'zip': 'ZIP or postal code',
    'country_id': 'Country name or country code',
    'state_id': 'State, province, or region',
    'vat': 'Tax ID or VAT number',
    'title': 'Contact title, for example Mr. or Ms.',
    'category_id': 'Contact tags or categories',
    'lang': 'Language code or language name',
    'comment': 'Internal notes',
    'is_company': 'Whether the row is a company',
}


def _json_loads(value, fallback):
    try:
        return json.loads(value or '')
    except Exception:
        return fallback


class AiContactImportSession(models.TransientModel):
    _name = 'ai.contact.import.session'
    _description = 'AI Contact Import Session'
    _transient_max_hours = 12.0

    file_name = fields.Char()
    total_rows = fields.Integer(default=0)
    processed_rows = fields.Integer(default=0)
    created_count = fields.Integer(default=0)
    skipped_count = fields.Integer(default=0)
    error_count = fields.Integer(default=0)
    headers_json = fields.Text(default='[]')
    rows_json = fields.Text(default='[]')
    mapping_json = fields.Text(default='{}')
    errors_json = fields.Text(default='[]')

    @api.model
    def create_from_file(self, file_base64, file_name, file_type=False):
        if not file_base64:
            raise UserError(_('Please choose a file to import.'))

        raw_file = base64.b64decode(file_base64.split(',')[-1])
        guessed_type = file_type or guess_mimetype(raw_file)
        import_wizard = self.env['base_import.import'].create({
            'res_model': 'res.partner',
            'file': raw_file,
            'file_name': file_name,
            'file_type': guessed_type,
        })
        read_options = {
            'encoding': '',
            'separator': '',
            'quoting': '"',
        }
        _file_length, rows = import_wizard._read_file(read_options)
        if not rows or len(rows) < 2:
            raise UserError(_('The file must contain a header row and at least one contact row.'))

        headers = [self._clean_cell(header) or _('Column %s') % (idx + 1) for idx, header in enumerate(rows[0])]
        data_rows = [self._row_to_dict(headers, row) for row in rows[1:] if any(self._clean_cell(value) for value in row)]
        if not data_rows:
            raise UserError(_('No contact rows were found after the header row.'))

        mapping = self._map_headers_with_ai(headers, data_rows[:5])
        session = self.create({
            'file_name': file_name,
            'total_rows': len(data_rows),
            'headers_json': json.dumps(headers),
            'rows_json': json.dumps(data_rows),
            'mapping_json': json.dumps(mapping),
        })
        return session._status()

    def process_next_batch(self, batch_size=25):
        self.ensure_one()
        rows = _json_loads(self.rows_json, [])
        mapping = _json_loads(self.mapping_json, {})
        errors = _json_loads(self.errors_json, [])
        batch_size = max(1, min(int(batch_size or 25), 100))
        start = self.processed_rows
        end = min(start + batch_size, len(rows))

        for index, row in enumerate(rows[start:end], start=start + 1):
            try:
                vals = self._prepare_partner_values(row, mapping)
                if not vals.get('name'):
                    vals['name'] = vals.get('email') or vals.get('phone') or _('Imported Contact')
                self.env['res.partner'].with_context(import_file=True).create(vals)
                self.created_count += 1
            except Exception as exc:
                self.error_count += 1
                errors.append({'row': index, 'error': str(exc)})
                _logger.exception('Failed to import contact row %s', index)

        self.processed_rows = end
        self.errors_json = json.dumps(errors[-50:])
        return self._status()

    def _status(self):
        self.ensure_one()
        mapping = _json_loads(self.mapping_json, {})
        headers = _json_loads(self.headers_json, [])
        errors = _json_loads(self.errors_json, [])
        mapped = [{'column': column, 'field': field} for column, field in mapping.items() if field]
        extra = [column for column in headers if not mapping.get(column)]
        return {
            'id': self.id,
            'file_name': self.file_name,
            'total': self.total_rows,
            'processed': self.processed_rows,
            'remaining': max(self.total_rows - self.processed_rows, 0),
            'created': self.created_count,
            'errors': self.error_count,
            'done': self.processed_rows >= self.total_rows,
            'mapped': mapped,
            'extra': extra,
            'errorDetails': errors[-10:],
        }

    def _map_headers_with_ai(self, headers, sample_rows):
        api_key, model = self._openrouter_settings()
        if not api_key:
            raise UserError(_('OPENROUTER_API_KEY is missing. Add it to the .env file and restart Odoo.'))

        available_fields = self._available_fields()
        prompt = {
            'task': 'Map spreadsheet contact columns to Odoo res.partner fields.',
            'rules': [
                'Return only JSON: {"mapping": {"Original Column": "field_name_or_null"}}.',
                'Use only the available field names.',
                'Use null when a column does not clearly match any available field.',
                'Do not invent custom fields.',
            ],
            'available_fields': available_fields,
            'columns': headers,
            'sample_rows': sample_rows,
        }
        try:
            response = requests.post(
                OPENROUTER_URL,
                headers={
                    'Authorization': 'Bearer %s' % api_key,
                    'Content-Type': 'application/json',
                    'HTTP-Referer': 'http://localhost',
                    'X-Title': 'Odoo AI Contact Import',
                },
                json={
                    'model': model or DEFAULT_MODEL,
                    'messages': [
                        {'role': 'system', 'content': 'You map CRM import columns. Output strict JSON only.'},
                        {'role': 'user', 'content': json.dumps(prompt, ensure_ascii=False)},
                    ],
                    'temperature': 0,
                    'response_format': {'type': 'json_object'},
                },
                timeout=45,
            )
            response.raise_for_status()
            content = response.json()['choices'][0]['message']['content']
            ai_mapping = self._extract_mapping(content)
        except Exception as exc:
            raise UserError(_('OpenRouter column mapping failed: %s') % exc)

        allowed = set(available_fields)
        return {
            column: ai_mapping.get(column) if ai_mapping.get(column) in allowed else None
            for column in headers
        }

    def _available_fields(self):
        fields_info = self.env['res.partner'].fields_get(list(SUPPORTED_FIELDS))
        return {
            name: {
                'label': fields_info.get(name, {}).get('string', name),
                'type': fields_info.get(name, {}).get('type', 'char'),
                'description': description,
            }
            for name, description in SUPPORTED_FIELDS.items()
            if name in fields_info
        }

    def _prepare_partner_values(self, row, mapping):
        vals = {}
        extra_values = {}
        for column, value in row.items():
            value = self._clean_cell(value)
            if not value:
                continue
            field_name = mapping.get(column)
            if field_name:
                if not self._put_field_value(vals, field_name, value):
                    extra_values[column] = value
            else:
                extra_values[column] = value

        extra_note = self._extra_note(extra_values)
        if extra_note:
            vals['comment'] = (vals.get('comment') or '') + extra_note
        return vals

    def _put_field_value(self, vals, field_name, value):
        if field_name == 'country_id':
            record = self._find_country(value)
            if record:
                vals[field_name] = record.id
                return True
            return False
        elif field_name == 'state_id':
            record = self._find_by_name('res.country.state', value)
            if record:
                vals[field_name] = record.id
                return True
            return False
        elif field_name == 'title':
            record = self._find_or_create_by_name('res.partner.title', value)
            vals[field_name] = record.id
            return True
        elif field_name == 'category_id':
            tags = [self._find_or_create_by_name('res.partner.category', item).id for item in self._split_multi(value)]
            if tags:
                vals[field_name] = [(6, 0, tags)]
                return True
            return False
        elif field_name == 'lang':
            lang = self._find_language(value)
            if lang:
                vals[field_name] = lang.code
                return True
            return False
        elif field_name == 'is_company':
            vals[field_name] = value.strip().lower() in ('1', 'true', 'yes', 'y', 'company')
            return True
        else:
            vals[field_name] = value
            return True

    def _extra_note(self, extra_values):
        if not extra_values:
            return ''
        items = ''.join(
            '<li><b>%s:</b> %s</li>' % (html.escape(str(key)), html.escape(str(value)))
            for key, value in extra_values.items()
        )
        return '<div><p><b>AI import extra fields</b></p><ul>%s</ul></div>' % items

    def _find_country(self, value):
        country = self.env['res.country'].search([('code', '=ilike', value.strip())], limit=1)
        return country or self._find_by_name('res.country', value)

    def _find_language(self, value):
        Lang = self.env['res.lang']
        return Lang.search(['|', ('code', '=ilike', value.strip()), ('name', '=ilike', value.strip())], limit=1)

    def _find_by_name(self, model, value):
        result = self.env[model].name_search(value, operator='ilike', limit=1)
        return self.env[model].browse(result[0][0]) if result else self.env[model]

    def _find_or_create_by_name(self, model, value):
        record = self._find_by_name(model, value)
        return record or self.env[model].create({'name': value})

    def _split_multi(self, value):
        return [item.strip() for item in re.split(r'[,;|]', value or '') if item.strip()]

    def _row_to_dict(self, headers, row):
        normalized = list(row) + [''] * max(len(headers) - len(row), 0)
        return {header: self._clean_cell(normalized[index]) for index, header in enumerate(headers)}

    def _clean_cell(self, value):
        return str(value or '').strip()

    def _extract_mapping(self, content):
        try:
            payload = json.loads(content)
        except json.JSONDecodeError:
            match = re.search(r'\{.*\}', content or '', re.S)
            payload = json.loads(match.group(0)) if match else {}
        return payload.get('mapping', payload) if isinstance(payload, dict) else {}

    def _openrouter_settings(self):
        env_values = self._read_dotenv()
        api_key = os.environ.get('OPENROUTER_API_KEY') or env_values.get('OPENROUTER_API_KEY')
        model = os.environ.get('OPENROUTER_MODEL') or env_values.get('OPENROUTER_MODEL') or DEFAULT_MODEL
        return api_key, model

    def _read_dotenv(self):
        values = {}
        for path in self._candidate_env_paths():
            if not os.path.exists(path):
                continue
            with open(path, encoding='utf-8') as env_file:
                for line in env_file:
                    line = line.strip()
                    if not line or line.startswith('#') or '=' not in line:
                        continue
                    key, value = line.split('=', 1)
                    values[key.strip()] = value.strip().strip('"').strip("'")
            break
        return values

    def _candidate_env_paths(self):
        module_path = os.path.abspath(os.path.dirname(__file__))
        return [
            os.path.join(os.getcwd(), '.env'),
            os.path.abspath(os.path.join(module_path, '..', '..', '..', '.env')),
        ]
