from pulumi import ComponentResource, Input, ResourceOptions
from pulumi_azure_native import insights, storage

from data_safe_haven.infrastructure.components import (
    BlobContainerAcl,
    BlobContainerAclProps,
    WrappedLogAnalyticsWorkspace,
)


class NFSV3BlobContainerProps:
    def __init__(
        self,
        acl_user: Input[str],
        acl_group: Input[str],
        acl_other: Input[str],
        apply_default_permissions: Input[bool],
        container_name: Input[str],
        log_analytics_workspace: Input[WrappedLogAnalyticsWorkspace],
        resource_group_name: Input[str],
        storage_account: Input[storage.StorageAccount],
        subscription_name: Input[str],
    ):
        self.acl_user = acl_user
        self.acl_group = acl_group
        self.acl_other = acl_other
        self.apply_default_permissions = apply_default_permissions
        self.container_name = container_name
        self.log_analytics_workspace = log_analytics_workspace
        self.resource_group_name = resource_group_name
        self.storage_account = storage_account
        self.subscription_name = subscription_name


class NFSV3BlobContainerComponent(ComponentResource):
    def __init__(
        self,
        name: str,
        props: NFSV3BlobContainerProps,
        opts: ResourceOptions | None = None,
    ):
        super().__init__("dsh:common:NFSV3BlobContainerComponent", name, {}, opts)
        child_opts = ResourceOptions.merge(opts, ResourceOptions(parent=self))

        storage_container = storage.BlobContainer(
            f"{self._name}_blob_container_{props.container_name}",
            account_name=props.storage_account.name,
            container_name=props.container_name,
            default_encryption_scope="$account-encryption-key",
            deny_encryption_scope_override=False,
            public_access=storage.PublicAccess.NONE,
            resource_group_name=props.resource_group_name,
            opts=ResourceOptions.merge(
                child_opts,
                ResourceOptions(parent=props.storage_account),
            ),
        )

        BlobContainerAcl(
            f"{storage_container._name}_acl",
            BlobContainerAclProps(
                acl_user=props.acl_user,
                acl_group=props.acl_group,
                acl_other=props.acl_other,
                apply_default_permissions=props.apply_default_permissions,
                container_name=storage_container.name,
                resource_group_name=props.resource_group_name,
                storage_account_name=props.storage_account.name,
                subscription_name=props.subscription_name,
            ),
            opts=ResourceOptions.merge(
                child_opts,
                ResourceOptions(parent=props.storage_account),
            ),
        )

        insights.DiagnosticSetting(
            f"{storage_container._name}_diagnostic_settings",
            name="firewall_diagnostic_settings",
            log_analytics_destination_type="Dedicated",
            logs=[
                {
                    "category_group": "allLogs",
                    "enabled": True,
                    "retention_policy": {
                        "days": 0,
                        "enabled": False,
                    },
                },
                {
                    "category_group": "audit",
                    "enabled": True,
                    "retention_policy": {
                        "days": 0,
                        "enabled": False,
                    },
                },
            ],
            metrics=[
                {
                    "category": "Transaction",
                    "enabled": True,
                    "retention_policy": {
                        "days": 0,
                        "enabled": False,
                    },
                }
            ],
            resource_uri=storage_container.id,
            workspace_id=props.log_analytics_workspace.id,
        )

        self.name = storage_container.name

        self.register_outputs({})
