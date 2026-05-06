/** @odoo-module **/
/**
 * smart_contacts/static/src/js/role_toggle.js
 *
 * Patches the BooleanToggle widget inside the form view so that toggling a
 * role flag triggers an immediate save (autosave) — this makes the
 * customer_rank / supplier_rank sync feel instant to the user.
 *
 * Also adds a visual "pulse" animation to the chip when roles change.
 */

import { patch } from "@web/core/utils/patch";
import { BooleanToggleField } from "@web/views/fields/boolean_toggle/boolean_toggle_field";

const ROLE_FIELDS = new Set([
    "is_customer",
    "is_vendor",
    "is_employee_contact",
    "is_partner_contact",
]);

patch(BooleanToggleField.prototype, {
    /**
     * After the standard toggle, if this is one of our role fields,
     * highlight the role chip so the user has clear visual feedback.
     */
    async onChange(newValue) {
        await super.onChange(newValue);

        if (!ROLE_FIELDS.has(this.props.name)) {
            return;
        }

        // Pulse the role chip
        const bar = this.el?.closest(".sc-role-bar");
        if (!bar) return;

        const chip = bar.querySelector(".sc-role-chip");
        if (!chip) return;

        chip.classList.remove("sc-chip-pulse");
        // Force reflow so the animation restarts
        void chip.offsetWidth;
        chip.classList.add("sc-chip-pulse");
    },
});
