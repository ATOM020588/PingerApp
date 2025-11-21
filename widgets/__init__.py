# widgets/__init__.py
from .switch_info_dialog import SwitchInfoDialog
from .plan_switch_info_dialog import PlanSwitchInfoDialog
from .add_planed_switch import AddPlanedSwitch
from .vlan_management import VlanManagementDialog
from .firmware_management import FirmwareManagementDialog
from .engineers_management import EngineersManagementDialog
from .operators_dialog import OperatorsDialog
from .models_management import ModelsManagementDialog
from .switch_edit_dialog import SwitchEditDialog


__all__ = [
    "VlanManagementDialog",
    "SwitchInfoDialog",
    "PlanSwitchInfoDialog",
    "AddPlanedSwitch",
    "FirmwareManagementDialog",
    "EngineersManagementDialog",
    "OperatorsDialog",
    "ModelsManagementDialog",
    "SwitchEditDialog"
]