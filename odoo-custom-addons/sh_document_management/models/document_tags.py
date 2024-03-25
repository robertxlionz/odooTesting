# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.

from odoo import models, fields, api
import random


class DocumentTags(models.Model):
    _name = 'document.tags'
    _description = 'Document Tags'
    _rec_name = 'name'

    name = fields.Char('Name', required=True)
    color = fields.Integer(string='Color Index')

    @api.model_create_multi
    def create(self, vals_list):
        res_ids = super(DocumentTags, self).create(vals_list)
        for res in res_ids:
            number = random.randrange(1, 10)
            res.color = number
        return res_ids
