from odoo import models


class PurchaseRequisitionReport(models.AbstractModel):
    _name = 'report.pr_flow_mgmt.report_purchase_requisition_document'
    _description = 'Purchase Requisition Report'

    def _get_report_values(self, docids, data=None):
        docs = self.env['pr.flow.requisition'].browse(docids)
        return {
            'doc_ids': docids,
            'doc_model': 'pr.flow.requisition',
            'docs': docs,
            'data': data,
        }

