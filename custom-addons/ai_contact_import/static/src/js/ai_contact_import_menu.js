/** @odoo-module **/

import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

const { Component } = owl;
const favoriteMenuRegistry = registry.category("favoriteMenu");

export class AiContactImportMenu extends Component {
    setup() {
        this.action = useService("action");
    }

    importContacts() {
        this.action.doAction("ai_contact_import.action_ai_contact_import");
    }
}

AiContactImportMenu.template = "ai_contact_import.MenuItem";
AiContactImportMenu.components = { DropdownItem };

favoriteMenuRegistry.add("ai-contact-import-menu", {
    Component: AiContactImportMenu,
    groupNumber: 4,
    isDisplayed: ({ config }) =>
        config.actionType === "ir.actions.act_window" &&
        config.resModel === "res.partner" &&
        ["kanban", "list"].includes(config.viewType),
}, { sequence: 0 });

