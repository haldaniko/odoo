odoo.define('ai_contact_import.action', function (require) {
    'use strict';

    const AbstractAction = require('web.AbstractAction');
    const core = require('web.core');

    const QWeb = core.qweb;
    const _t = core._t;

    const AiContactImport = AbstractAction.extend({
        hasControlPanel: true,
        contentTemplate: 'ai_contact_import.Main',
        events: {
            'change .o_ai_contact_file': '_onFileChange',
            'click .o_ai_contact_analyze': '_onAnalyze',
            'click .o_ai_contact_start': '_onStart',
            'click .o_ai_contact_reset': '_onReset',
        },

        init() {
            this._super.apply(this, arguments);
            this.file = null;
            this.fileData = null;
            this.state = {
                status: 'idle',
                message: '',
                session: null,
            };
        },

        start() {
            return this._super.apply(this, arguments).then(() => {
                this._renderState();
            });
        },

        _onFileChange(ev) {
            this.file = ev.currentTarget.files[0] || null;
            this.fileData = null;
            this.state.message = this.file ? this.file.name : '';
            this.state.status = this.file ? 'ready' : 'idle';
            this._renderState();
        },

        async _onAnalyze() {
            if (!this.file) {
                this._setError(_t('Please choose a spreadsheet file first.'));
                return;
            }
            this.state.status = 'analyzing';
            this.state.message = _t('Reading the file and mapping columns with AI...');
            this._renderState();
            try {
                const fileData = await this._readFile(this.file);
                const result = await this._rpc({
                    model: 'ai.contact.import.session',
                    method: 'create_from_file',
                    args: [fileData, this.file.name, this.file.type],
                });
                this.state.status = 'mapped';
                this.state.session = result;
                this.state.message = _t('Columns are mapped. Review the summary and start import.');
                this._renderState();
            } catch (error) {
                this._setError(this._messageFromError(error));
            }
        },

        async _onStart() {
            if (!this.state.session || !this.state.session.id) {
                return;
            }
            this.state.status = 'importing';
            this.state.message = _t('Importing contacts...');
            this._renderState();
            try {
                while (!this.state.session.done) {
                    this.state.session = await this._rpc({
                        model: 'ai.contact.import.session',
                        method: 'process_next_batch',
                        args: [[this.state.session.id], 25],
                    });
                    this._renderState();
                    await new Promise((resolve) => setTimeout(resolve, 60));
                }
                this.state.status = 'done';
                this.state.message = _t('Import completed.');
                this._renderState();
            } catch (error) {
                this._setError(this._messageFromError(error));
            }
        },

        _onReset() {
            this.file = null;
            this.fileData = null;
            this.state = { status: 'idle', message: '', session: null };
            this.$('.o_ai_contact_file').val('');
            this._renderState();
        },

        _readFile(file) {
            return new Promise((resolve, reject) => {
                const reader = new FileReader();
                reader.onload = () => resolve(reader.result);
                reader.onerror = () => reject(reader.error);
                reader.readAsDataURL(file);
            });
        },

        _renderState() {
            const session = this.state.session || {};
            const total = session.total || 0;
            const processed = session.processed || 0;
            const percent = total ? Math.round((processed / total) * 100) : 0;
            this.$('.o_ai_contact_status').html(QWeb.render('ai_contact_import.Status', {
                state: this.state,
                session,
                percent,
            }));
            this.$('.o_ai_contact_analyze').prop('disabled', !this.file || this.state.status === 'analyzing' || this.state.status === 'importing');
            this.$('.o_ai_contact_start').prop('disabled', this.state.status !== 'mapped');
        },

        _setError(message) {
            this.state.status = 'error';
            this.state.message = message;
            this._renderState();
        },

        _messageFromError(error) {
            return (error && error.data && error.data.message) || (error && error.message) || _t('Unexpected import error.');
        },
    });

    core.action_registry.add('ai_contact_import', AiContactImport);

    return AiContactImport;
});
