# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.

from odoo import models, fields, api, _
import random
import base64
import zipfile
import io
import tempfile
import shutil
import os
import uuid


class Directory(models.Model):
    _name = 'document.directory'
    _description = 'Document Directory'
    _rec_name = 'name'

    sequence = fields.Integer(string="Sequence")
    name = fields.Char(string='Name', required=True)
    image_medium = fields.Binary('Image')
    image_small = fields.Binary(
        "Small-sized image", attachment=True,
        help="Small-sized image of the product. It is automatically "
             "resized as a 64x64px image, with aspect ratio preserved. "
             "Use this field anywhere a small image is required.")
    file_count = fields.Integer(compute='_compute_file_counts')
    sub_directory_count = fields.Integer(
        compute='_compute_sub_directory_count')
    parent_id = fields.Many2one('document.directory', 'Parent Directory')
    visible_directory = fields.Boolean('Visible Directory')
    directory_tag_ids = fields.Many2many(
        'directory.tags', string='Diractory Tags')
    attachment_ids = fields.One2many(
        'ir.attachment', 'directory_id', string=" Files")
    directory_ids = fields.Many2many(
        'document.directory', compute='_compute_sub_directory_count')
    files = fields.Integer(string="Files", compute='_compute_file_counts_btn')
    sub_directories = fields.Integer(
        string="Sub Directories", compute='_compute_sub_directory_count_btn')
    color = fields.Integer(string='Color Index')
    company_id = fields.Many2one(
        'res.company', string='Company', default=lambda self: self.env.company)

    sh_user_ids = fields.Many2many(
        'res.users', relation='rel_directory_user', string='Users')

    sh_share_url = fields.Char(
        string="Link", compute='_compute_full_url')

    sh_access_token = fields.Char("Access Token")

    @api.model
    def default_get(self, fields):
        rec = super(Directory, self).default_get(fields)
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
                "parent_id": directory_id,
            })
        return rec


    def _get_token(self):
        """ Get the current record access token """
        if self.sh_access_token:
            return self.sh_access_token
        else:
            sh_access_token = str(uuid.uuid4())
            self.write({'sh_access_token': sh_access_token})
            return sh_access_token

    def _compute_full_url(self):
        base_url = self.env['ir.config_parameter'].sudo(
        ).get_param('web.base.url')
        self.sh_share_url = base_url + '/attachment/download_directiries' + \
            '?list_ids=%s&access_token=%s&name=%s' % (
                self.id, self._get_token(), 'directory')

    def action_share_directory(self):
        self._compute_full_url()

        template = self.env.ref(
            "sh_document_management.sh_document_management_share_directory_url_template")
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
    def _run_auto_delete_garbase_collection(self):
        attachment_ids = self.env['ir.attachment'].sudo().search(
            [('sh_document_as_zip', '=', True)])
        if attachment_ids:
            attachment_ids.sudo().unlink()

    def action_download_as_zip(self):
        if self.env.context.get('active_ids'):
            directory_ids = self.env['document.directory'].sudo().browse(
                self.env.context.get('active_ids'))
            if directory_ids:
                mem_zip = io.BytesIO()
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
                        'name': 'Documents.zip',
                        'sh_document_as_zip': True,
                        'type': 'binary',
                        'mimetype': 'application/zip',
                        'datas': content
                    })
                shutil.rmtree(tmp_dir)
                url = "/web/content/" + \
                    str(get_attachment.id) + "?download=true"
                return {
                    'type': 'ir.actions.act_url',
                    'url': url,
                    'target': 'current',
                }

    @api.model_create_multi
    def create(self, vals_list):
        for values in vals_list:
            sequence = self.env['ir.sequence'].next_by_code(
                'document.directory')
            number = random.randrange(1, 10)
            values['sequence'] = sequence
            values['color'] = number
        return super(Directory, self).create(vals_list)

    def _compute_file_counts(self):
        if self:
            for rec in self:
                ir_attachment_ids = self.env['ir.attachment'].sudo().search(
                    [('directory_id', '=', rec.id)])
                if ir_attachment_ids:
                    rec.file_count = len(ir_attachment_ids.ids)
                else:
                    rec.file_count = 0

    def _compute_sub_directory_count(self):
        if self:
            for rec in self:
                sub_directory_ids = self.env['document.directory'].sudo().search(
                    [('parent_id', '=', rec.id)])
                if sub_directory_ids:
                    rec.sub_directory_count = len(sub_directory_ids.ids)
                    rec.directory_ids = [(6, 0, sub_directory_ids.ids)]
                else:
                    rec.sub_directory_count = 0
                    rec.directory_ids = False

    def _compute_file_counts_btn(self):
        if self:
            for rec in self:
                ir_attachment_ids = self.env['ir.attachment'].sudo().search(
                    [('directory_id', '=', rec.id)])
                if ir_attachment_ids:
                    rec.files = len(ir_attachment_ids.ids)
                else:
                    rec.files = 0

    def _compute_sub_directory_count_btn(self):
        if self:
            for rec in self:
                sub_directory_ids = self.env['document.directory'].sudo().search(
                    [('parent_id', '=', rec.id)])
                if sub_directory_ids:
                    rec.sub_directories = len(sub_directory_ids.ids)
                else:
                    rec.sub_directories = 0

    def action_view_sub_directory(self):
        if self:
            for rec in self:
                return {
                    'name': _('Sub Directories'),
                    'type': 'ir.actions.act_window',
                    'res_model': 'document.directory',
                    'view_type': 'form',
                    'view_mode': 'kanban,tree,form',
                    'domain': [('parent_id', '=', rec.id)],
                    'target': 'current'
                }

    def action_view_files(self):
        if self:
            for rec in self:
                return {
                    'name': _('Files'),
                    'type': 'ir.actions.act_window',
                    'res_model': 'ir.attachment',
                    'view_type': 'form',
                    'view_mode': 'kanban,tree,form',
                    'domain': [('directory_id', '=', rec.id)],
                    'target': 'current'
                }

    def action_view(self):
        if self:
            return {
                'name': _('Files'),
                'type': 'ir.actions.act_window',
                        'res_model': 'ir.attachment',
                        'view_type': 'form',
                        'view_mode': 'kanban,tree,form',
                        'domain': [('directory_id', '=', self.id)],
                        'target': 'current'
            }
