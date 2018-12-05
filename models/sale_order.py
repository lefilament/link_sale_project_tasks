# -*- coding: utf-8 -*-
# © 2017 Le Filament (<http://www.le-filament.com>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, models
from datetime import datetime
from dateutil.relativedelta import relativedelta


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.multi
    def saleorder_update_tasks(self):
        for order in self:
            stage_id_new = self.env['ir.values'].get_default(
                'sale.config.settings', 'project_task_type_id'
                )
            stage_new = self.env['project.task.type'].browse(stage_id_new)
            lf_tarif_jour = self.env['ir.values'].get_default(
                'project.config.settings', 'lf_tarif_jour'
                )
            lf_heures_jour = self.env['ir.values'].get_default(
                'project.config.settings', 'lf_heures_jour'
                )
            sale_project_id = order.project_project_id
            project_id = sale_project_id.id
            project_total_budget = 0
            for line in order.order_line:
                task_id_refer = self.env['project.task'].search(
                    [('sale_line_id', '=', line.id)]
                    )
                if task_id_refer:
                    if not line.product_id.project_id:
                        project_total_budget = (
                            project_total_budget
                            + line.price_subtotal
                            )
                        planned_hours = (
                            (line.price_subtotal / lf_tarif_jour)
                            * lf_heures_jour
                            )
                        task_id_refer.planned_hours = planned_hours
                    else:
                        if line.price_subtotal != task_id_refer.price_subtotal:
                            project = line.product_id.project_id
                            project_id_maint = project.id
                            project_update = self.env[
                                'project.project'
                                ].browse(project_id_maint)
                            project_update.lf_total_budget = (
                                (project_update.lf_total_budget
                                 - task_id_refer.price_subtotal
                                 )
                                + line.price_subtotal
                                )
                            planned_hours = (
                                (line.price_subtotal / lf_tarif_jour)
                                * lf_heures_jour
                                )
                            task_id_refer.planned_hours = planned_hours
                            task_id_refer.price_subtotal = line.price_subtotal
                else:
                    if line.product_id.track_service == 'project':
                        if line.product_id.project_id:
                            project = line.product_id.project_id
                            project_id = project.id
                            date_plan = datetime.strptime(
                                order.confirmation_date,
                                '%Y-%m-%d %H:%M:%S'
                                )
                            date_deadline = (
                                date_plan.date()
                                + relativedelta(
                                    years=int(line.product_uom_qty))).strftime(
                                        '%Y-%m-%d'
                                )
                            stage = line.product_id.project_task_type_id
                            if order.partner_id.is_company:
                                name_task = (
                                    order.partner_id.name + " - " + stage.name
                                    )
                            else:
                                name_task = (
                                     order.partner_id.parent_id.name
                                     + " - "
                                     + stage.name
                                     )
                        else:
                            stage = stage_new
                            project_id = sale_project_id.id
                            date_deadline = False
                            name_task = line.name.split('\n', 1)[0]
                        project_total_budget = (
                            project_total_budget + line.price_subtotal
                            )
                        planned_hours = (
                            (line.price_subtotal / lf_tarif_jour)
                            * lf_heures_jour
                            )
                        description_line = "<p>"
                        for line_name in line.name:
                            if line_name == '\n':
                                description_line = description_line + "</p><p>"
                            else:
                                description_line = description_line + line_name
                        self.env['project.task'].create({
                            'name': name_task,
                            'date_deadline': date_deadline,
                            'planned_hours': planned_hours,
                            'remaining_hours': planned_hours,
                            'partner_id': (
                                           order.partner_id.id
                                           or self.partner_dest_id.id
                                           ),
                            'user_id': self.env.uid,
                            # 'procurement_id': line.procurement_ids.id,
                            'description': description_line + '</p><br/>',
                            'project_id': project_id,
                            'company_id': order.company_id.id,
                            'stage_id': stage.id,
                            'sale_line_id': line.id
                            })
            project_date = self.env['project.project'].browse(project_id)
            project_date.lf_tarif_jour = lf_tarif_jour
            project_date.lf_total_budget = project_total_budget
            order.tasks_ids = self.env['project.task'].search([
                ('sale_line_id', 'in', order.order_line.ids)
                ])
            order.tasks_count = len(order.tasks_ids)
