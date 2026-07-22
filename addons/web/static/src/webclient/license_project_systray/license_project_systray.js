/** @odoo-module **/

import { Dialog } from "@web/core/dialog/dialog";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

import { Component } from "@odoo/owl";

const LICENSE_TITLE = "Лиценз CRM Base 02.011\n02-011-0127";
const PROJECT_TITLE = "Проект BG16RFPR001-1.012-0189-C01";
const PROJECT_IMAGE = "/web/static/src/webclient/license_project_systray/project-plameli.jpg";
const LICENSE_ROWS = [
    ["РАЗРАБОТЧИК", "Ай-Ти Степ ООД"],
    ["CRM система", "CRM Base 02.11"],
    ["ЛИЦЕНЗ", "02-011-0127"],
    ["ЛИЦЕНЗОПОЛУЧАТЕЛ", "Пламели финанс ЕООД"],
    ["Финансирано на проект", "BG16RFPR001-1.012-0189-C01"],
];

export class LicenseDetailsDialog extends Component {}
LicenseDetailsDialog.template = "web.LicenseDetailsDialog";
LicenseDetailsDialog.components = { Dialog };
LicenseDetailsDialog.props = {
    close: Function,
    rows: Array,
    title: String,
};

export class ProjectImageDialog extends Component {}
ProjectImageDialog.template = "web.ProjectImageDialog";
ProjectImageDialog.components = { Dialog };
ProjectImageDialog.props = {
    close: Function,
    imageSrc: String,
    title: String,
};

export class LicenseProjectSystray extends Component {
    setup() {
        this.dialog = useService("dialog");
    }

    get licenseButtonLabel() {
        return LICENSE_TITLE;
    }

    get projectButtonLabel() {
        return PROJECT_TITLE;
    }

    openLicenseDialog() {
        this.dialog.add(LicenseDetailsDialog, {
            rows: LICENSE_ROWS,
            title: LICENSE_TITLE,
        });
    }

    openProjectDialog() {
        this.dialog.add(ProjectImageDialog, {
            imageSrc: PROJECT_IMAGE,
            title: PROJECT_TITLE,
        });
    }
}

LicenseProjectSystray.template = "web.LicenseProjectSystray";

export const systrayItem = {
    Component: LicenseProjectSystray,
};

registry.category("systray").add("web.license_project_systray", systrayItem, { sequence: 24 });
