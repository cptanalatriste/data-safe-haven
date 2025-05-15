"""Pulumi component for SRE Entra resources"""

from collections.abc import Mapping
from typing import ClassVar

import pulumi_azuread as entra
from pulumi import ComponentResource, Input, Output, ResourceOptions
from pulumi_azure_native import authorization, resources

from data_safe_haven.functions import replace_separators, seeded_uuid
from data_safe_haven.infrastructure.common import get_id_from_rg
from data_safe_haven.infrastructure.components import (
    EntraApplicationComponent,
    EntraDesktopApplicationProps,
    EntraWebApplicationProps,
)
from data_safe_haven.types import EntraApplicationId, EntraAppPermissionType


class SREEntraProps:
    """Properties for SREEntraComponent"""

    def __init__(
        self,
        group_names: Mapping[str, str],
        resource_group: Input[resources.ResourceGroup],
        sre_fqdn: Input[str],
        shm_name: Input[str],
        sre_name: Input[str],
        subscription_id: Input[str],
    ) -> None:
        self.group_names = group_names
        self.resource_group_id = Output.from_input(resource_group).apply(get_id_from_rg)
        self.shm_name = shm_name
        self.sre_fqdn = sre_fqdn
        self.sre_name = sre_name
        self.subscription_id = subscription_id


class SREEntraComponent(ComponentResource):
    """Deploy SRE Entra resources with Pulumi"""

    azure_role_ids: ClassVar[dict[str, str]] = {
        "DNS Zone Contributor": "befefa01-2a29-4197-83a8-272ff33ce314",
        "Azure Container Instances Contributor Role": "5d977122-f97e-4b4d-a52f-6b43003ddb4d",
        "Contributor": "b24988ac-6180-42a0-ab88-20f7382dd24c",
    }

    def __init__(
        self,
        name: str,
        stack_name: str,
        props: SREEntraProps,
        opts: ResourceOptions | None = None,
    ) -> None:
        super().__init__("dsh:sre:EntraComponent", name, {}, opts)
        child_opts = ResourceOptions.merge(opts, ResourceOptions(parent=self))

        # Create Entra groups
        for group_name, group_description in props.group_names.items():
            entra.Group(
                replace_separators(f"{self._name}_group_{group_name}", "_"),
                description=group_description,
                display_name=group_description,
                mail_enabled=False,
                prevent_duplicate_names=True,
                security_enabled=True,
            )

        # Get the Microsoft Graph service principal
        msgraph_service_principal = entra.ServicePrincipal(
            f"{self._name}_microsoft_graph_service_principal",
            client_id=EntraApplicationId.MICROSOFT_GRAPH.value,
            use_existing=True,
        )

        # Identity application
        # - needs read-only permissions for users/groups
        # - needs delegated permission to read users (for validating log-in attempts)
        # - needs an application secret for authentication
        self.identity_application = EntraApplicationComponent(
            f"{self._name}_identity",
            EntraDesktopApplicationProps(
                application_name=Output.concat(
                    "Data Safe Haven (",
                    props.shm_name,
                    " - ",
                    props.sre_name,
                    ") Identity Service Principal",
                ),
                application_permissions=[
                    (EntraAppPermissionType.APPLICATION, "User.Read.All"),
                    (EntraAppPermissionType.APPLICATION, "GroupMember.Read.All"),
                    (EntraAppPermissionType.DELEGATED, "User.Read.All"),
                ],
                msgraph_service_principal=msgraph_service_principal,
            ),
            opts=child_opts,
        )

        # Add an application password
        self.identity_application_secret = entra.ApplicationPassword(
            f"{self._name}_identity_application_secret",
            application_id=self.identity_application.application.id,
            display_name="Apricot Authentication Secret",
        )

        # Remote desktop application
        # - only used as part of the OAuth 2.0 authorization flow
        # - does not need any application permissions
        # - does not need an application secret
        self.remote_desktop_url = Output.from_input(props.sre_fqdn).apply(
            lambda fqdn: f"https://{str(fqdn).strip('/')}/"
        )
        self.remote_desktop_application = EntraApplicationComponent(
            f"{self._name}_remote_desktop",
            EntraWebApplicationProps(
                application_name=Output.concat(
                    "Data Safe Haven (",
                    props.shm_name,
                    " - ",
                    props.sre_name,
                    ") Remote Desktop Service Principal",
                ),
                application_permissions=[],
                msgraph_service_principal=msgraph_service_principal,
                redirect_url=self.remote_desktop_url,
            ),
            opts=child_opts,
        )

        # DNS monitor application
        self.dns_monitor_application = EntraApplicationComponent(
            f"{self._name}_dns_monitor",
            EntraDesktopApplicationProps(
                application_name=Output.concat(
                    "Data Safe Haven (",
                    props.shm_name,
                    " - ",
                    props.sre_name,
                    ") DNS Monitor Service Principal",
                ),
                application_permissions=[],
                msgraph_service_principal=msgraph_service_principal,
            ),
        )

        # Add an application password to the DNS monitor.
        self.dns_monitor_application_secret = entra.ApplicationPassword(
            f"{self._name}_dns_monitor_application_secret",
            application_id=self.dns_monitor_application.application.id,
            display_name="DNS Monitor Authentication Secret",
        )

        # # Grant "DNS Zone Contributor" permissions to the Service Principal.
        # authorization.RoleAssignment(
        #     f"{self._name}_dns_zone_contributor_role_assignment",
        #     principal_id=self.dns_monitor_application.application_service_principal.object_id,
        #     principal_type=authorization.PrincipalType.SERVICE_PRINCIPAL,
        #     role_assignment_name=str(seeded_uuid(f"{stack_name} DNS Zone Contributor")),
        #     role_definition_id=Output.concat(
        #         "/subscriptions/",
        #         props.subscription_id,
        #         "/providers/Microsoft.Authorization/roleDefinitions/",
        #         self.azure_role_ids["DNS Zone Contributor"],
        #     ),
        #     scope=props.resource_group_id,
        #     opts=child_opts,
        # )

        # # Grant "Azure Container Instances Contributor Role" permissions to the Service Principal.
        # authorization.RoleAssignment(
        #     f"{self._name}_container_instances_contributor_role_assignment",
        #     principal_id=self.dns_monitor_application.application_service_principal.object_id,
        #     principal_type=authorization.PrincipalType.SERVICE_PRINCIPAL,
        #     role_assignment_name=str(
        #         seeded_uuid(f"{stack_name} Container Instances Contributor")
        #     ),
        #     role_definition_id=Output.concat(
        #         "/subscriptions/",
        #         props.subscription_id,
        #         "/providers/Microsoft.Authorization/roleDefinitions/",
        #         self.azure_role_ids["Azure Container Instances Contributor Role"],
        #     ),
        #     scope=props.resource_group_id,
        #     opts=child_opts,
        # )

        # Grant "Contributor" permissions to the Service Principal.
        authorization.RoleAssignment(
            f"{self._name}_contributor_role_assignment",
            principal_id=self.dns_monitor_application.application_service_principal.object_id,
            principal_type=authorization.PrincipalType.SERVICE_PRINCIPAL,
            role_assignment_name=str(seeded_uuid(f"{stack_name} Contributor")),
            role_definition_id=Output.concat(
                "/subscriptions/",
                props.subscription_id,
                "/providers/Microsoft.Authorization/roleDefinitions/",
                self.azure_role_ids["Contributor"],
            ),
            scope=f"subscriptions/{props.subscription_id}",  # TODO(cgavidia): Only for testing!
            opts=child_opts,
        )

        # Register outputs
        self.identity_application_id = self.identity_application.application.client_id
        self.identity_application_secret = self.identity_application_secret.value
        self.remote_desktop_application_id = (
            self.remote_desktop_application.application.client_id
        )

        self.dns_monitor_application_id = (
            self.dns_monitor_application.application.client_id
        )
        self.dns_monitor_application_secret = self.dns_monitor_application_secret.value
