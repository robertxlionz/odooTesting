# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.

from odoo import fields, models
import uuid


class ShShareDirectories(models.TransientModel):
    _name = "sh.share.directories"
    _description = "Share Directories"

    sh_name = fields.Char(string='Name')
    access_token = fields.Char(required=True, default=lambda x: str(
        uuid.uuid4()))
    sh_share_url = fields.Char(string="Link", compute='_compute_full_url')
