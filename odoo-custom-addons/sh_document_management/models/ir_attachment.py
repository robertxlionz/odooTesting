# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.

from odoo import models, fields, api
import random
import base64
import zipfile
from io import BytesIO
import tempfile
import shutil
import os


class Attachment(models.Model):
    _inherit = 'ir.attachment'

    directory_id = fields.Many2one('document.directory', string='Directory')
    document_tags = fields.Many2many('document.tags', string='Document Tags')
    color = fields.Integer(string='Color Index')
    sh_document_as_zip = fields.Boolean('Document as zip')
    sh_user_ids = fields.Many2many(
        'res.users', relation='rel_attachment_user', string='Users')

    sh_share_url = fields.Char(
        string="Link", compute='_compute_full_url')

    def _compute_full_url(self):
        base_url = self.env['ir.config_parameter'].sudo(
        ).get_param('web.base.url')
        self.sh_share_url = base_url + '/attachment/download_directiries' + \
            '?list_ids=%s&access_token=%s&name=%s' % (
                self.id, self.access_token, 'document')

    def action_share_directory(self):
        self._compute_full_url()

        template = self.env.ref(
            "sh_document_management.sh_document_management_share_document_url_template")
        partner_to = ''
        total_receipients = len(self.sh_user_ids)
        count = 1
        if self.sh_user_ids:
            for resp in self.sh_user_ids:
                partner_to += str(resp.partner_id.id)
                if count < total_receipients:
                    partner_to += ','
                count += 1

        template.partner_to = partner_to
        template.sudo().send_mail(self.id, force_send=True, email_values={
            'email_from': self.env.user.email}, email_layout_xmlid='mail.mail_notification_light')

    @api.model
    def default_get(self, fields):
        rec = super(Attachment, self).default_get(fields)
        active_id = self._context.get("active_id")
        active_model = self._context.get("active_model")
        directory_id = None
        if active_id and active_model == 'document.directory':
            directory_id = active_id
        params = self._context.get("params")
        if not active_model and params and params.get("model") == 'document.directory':
            directory_id = params.get("id")
        if directory_id:
            rec.update({
                "directory_id": directory_id,
            })
        return rec

    @api.model_create_multi
    def create(self, vals_list):
        for values in vals_list:
            number = random.randrange(1, 10)
            values['color'] = number
        return super(Attachment, self).create(vals_list)

    def action_download_as_zip_attachment(self):
        if self.env.context.get('active_ids'):
            attachment_ids = self.env['ir.attachment'].sudo().browse(
                self.env.context.get('active_ids'))
            directories = []
            if attachment_ids:
                for attachment in attachment_ids:
                    if attachment.directory_id and attachment.directory_id.id not in directories:
                        directories.append(attachment.directory_id.id)
            directory_ids = self.env['document.directory'].sudo().browse(
                directories)
            if directory_ids:
                mem_zip = BytesIO()
                tmp_dir = tempfile.mkdtemp(suffix=None, prefix=None, dir=None)
                path = tmp_dir
                path_main = os.path.join('/tmp')
                is_exist = os.path.exists(path_main)
                if not is_exist:
                    os.mkdir(path_main)
                path_ED = path_main
                # path_ID = tmp_dir
                with zipfile.ZipFile(mem_zip,
                                     mode="w",
                                     compression=zipfile.ZIP_DEFLATED) as zf:
                    for directory in directory_ids:
                        path = os.path.join(path_ED, directory.name)
                        is_exist = os.path.exists(path)
                        if not is_exist:
                            os.mkdir(path)
                        documents = self.env['ir.attachment'].sudo().search(
                            [('directory_id', '=', directory.id)])
                        if documents:
                            for attachment in documents:
                                # if bill then only export attachment.
                                attachment_name = attachment.name.replace(
                                    '/', '_') if attachment.name else 'attachment'
                                f = open(path + "/" + attachment_name,
                                         "wb")  # create
                                content_base64 = base64.b64decode(
                                    attachment.datas)
                                f.write(content_base64)
                                f.close()
                                zf.write(path + "/" + attachment_name)

                content = base64.encodebytes(mem_zip.getvalue())
                if content:
                    get_attachment = self.env['ir.attachment'].sudo().create({
                        'name':'Documents.zip',
                        'sh_document_as_zip':True,
                        'type':'binary',
                        'mimetype':'application/zip',
                        'datas':content
                    })
                shutil.rmtree(tmp_dir)
                url = "/web/content/" + str(get_attachment.id) + "?download=true"
                return {
                    'type': 'ir.actions.act_url',
                    'url': url,
                    'target': 'current',
                }
