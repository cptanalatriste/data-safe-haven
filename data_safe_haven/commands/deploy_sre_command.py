"""Command-line application for deploying a Secure Research Environment from project files"""
# Standard library imports
from typing import Any, Dict, List, Optional

# Third party imports
import typer
from typing_extensions import Annotated

# Local imports
from data_safe_haven.config import Config, DotFileSettings
from data_safe_haven.exceptions import (
    DataSafeHavenConfigException,
    DataSafeHavenException,
    DataSafeHavenInputException,
)
from data_safe_haven.external import AzureApi, GraphApi
from data_safe_haven.functions import (
    alphanumeric,
    password,
    validate_azure_vm_sku,
    validate_ip_address,
)
from data_safe_haven.provisioning import SREProvisioningManager
from data_safe_haven.pulumi import PulumiStack
from data_safe_haven.utility import SoftwarePackageCategory
from .base_command import BaseCommand


class DeploySRECommand(BaseCommand):
    """Deploy a Secure Research Environment component"""

    def __init__(self):
        """Constructor"""
        super().__init__()
        self._available_vm_skus: Dict[str, Dict[str, Any]] = {}

    def entrypoint(
        self,
        name: Annotated[str, typer.Argument(help="Name of SRE to deploy")],
        allow_copy: Annotated[
            Optional[bool],
            typer.Option(
                "--allow-copy",
                "-c",
                help="Whether to allow text to be copied out of the SRE.",
            ),
        ] = None,
        allow_paste: Annotated[
            Optional[bool],
            typer.Option(
                "--allow-paste",
                "-p",
                help="Whether to allow text to be pasted into the SRE.",
            ),
        ] = None,
        data_provider_ip_addresses: Annotated[
            Optional[List[str]],
            typer.Option(
                "--data-provider-ip-address",
                "-d",
                help="An IP address or range used by your data providers. [*may be specified several times*]",
                callback=lambda vms: [validate_ip_address(vm) for vm in vms],
            ),
        ] = None,
        research_desktops: Annotated[
            Optional[List[str]],
            typer.Option(
                "--research-desktop",
                "-r",
                help="A virtual machine SKU to make available to your users as a research desktop. [*may be specified several times*]",
                callback=lambda ips: [validate_azure_vm_sku(ip) for ip in ips],
            ),
        ] = None,
        software_packages: Annotated[
            Optional[SoftwarePackageCategory],
            typer.Option(
                "--software-packages",
                "-s",
                help="The category of package to allow users to install from enabled software repositories.",
            ),
        ] = None,
        user_ip_addresses: Annotated[
            Optional[List[str]],
            typer.Option(
                "--user-ip-address",
                "-u",
                help="An IP address or range used by your users. [*may be specified several times*]",
                callback=lambda ips: [validate_ip_address(ip) for ip in ips],
            ),
        ] = None,
    ) -> None:
        """Typer command line entrypoint"""
        sre_name = "UNKNOWN"
        try:
            # Use a JSON-safe SRE name
            sre_name = alphanumeric(name)

            # Use dotfile settings to load the job configuration
            try:
                settings = DotFileSettings()
            except DataSafeHavenException as exc:
                raise DataSafeHavenInputException(
                    f"Unable to load project settings. Please run this command from inside the project directory.\n{str(exc)}"
                ) from exc
            config = Config(settings.name, settings.subscription_name)
            self.update_config(
                sre_name,
                config,
                allow_copy=allow_copy,
                allow_paste=allow_paste,
                data_provider_ip_addresses=data_provider_ip_addresses,
                research_desktops=research_desktops,
                software_packages=software_packages,
                user_ip_addresses=user_ip_addresses,
            )

            # Load GraphAPI as this may require user-interaction that is not possible as part of a Pulumi declarative command
            graph_api = GraphApi(
                tenant_id=config.shm.aad_tenant_id,
                default_scopes=["Application.ReadWrite.All", "Group.ReadWrite.All"],
            )

            # Initialise Pulumi stack
            shm_stack = PulumiStack(config, "SHM")
            stack = PulumiStack(config, "SRE", sre_name=sre_name)
            # Set Azure options
            stack.add_option("azure-native:location", config.azure.location)
            stack.add_option(
                "azure-native:subscriptionId", config.azure.subscription_id
            )
            stack.add_option("azure-native:tenantId", config.azure.tenant_id)
            # Load SHM stack outputs
            stack.add_option(
                "shm-domain_controllers-domain_sid",
                shm_stack.output("domain_controllers")["domain_sid"],
                True,
            )
            stack.add_option(
                "shm-domain_controllers-ldap_root_dn",
                shm_stack.output("domain_controllers")["ldap_root_dn"],
                True,
            )
            stack.add_option(
                "shm-domain_controllers-ldap_server_ip",
                shm_stack.output("domain_controllers")["ldap_server_ip"],
                True,
            )
            stack.add_option(
                "shm-domain_controllers-netbios_name",
                shm_stack.output("domain_controllers")["netbios_name"],
                True,
            )
            stack.add_option(
                "shm-monitoring-automation_account_name",
                shm_stack.output("monitoring")["automation_account_name"],
                True,
            )
            stack.add_option(
                "shm-monitoring-log_analytics_workspace_id",
                shm_stack.output("monitoring")["log_analytics_workspace_id"],
                True,
            )
            stack.add_secret(
                "shm-monitoring-log_analytics_workspace_key",
                shm_stack.output("monitoring")["log_analytics_workspace_key"],
                True,
            )
            stack.add_option(
                "shm-monitoring-resource_group_name",
                shm_stack.output("monitoring")["resource_group_name"],
                True,
            )
            stack.add_option(
                "shm-networking-private_dns_zone_base_id",
                shm_stack.output("networking")["private_dns_zone_base_id"],
                True,
            )
            stack.add_option(
                "shm-networking-resource_group_name",
                shm_stack.output("networking")["resource_group_name"],
                True,
            )
            stack.add_option(
                "shm-networking-subnet_identity_servers_prefix",
                shm_stack.output("networking")["subnet_identity_servers_prefix"],
                True,
            )
            stack.add_option(
                "shm-networking-subnet_subnet_monitoring_prefix",
                shm_stack.output("networking")["subnet_monitoring_prefix"],
                True,
            )
            stack.add_option(
                "shm-networking-subnet_update_servers_prefix",
                shm_stack.output("networking")["subnet_update_servers_prefix"],
                True,
            )
            stack.add_option(
                "shm-networking-virtual_network_name",
                shm_stack.output("networking")["virtual_network_name"],
                True,
            )
            stack.add_option(
                "shm-update_servers-ip_address_linux",
                shm_stack.output("update_servers")["ip_address_linux"],
                True,
            )
            # Add necessary secrets
            stack.copy_secret("password-domain-ldap-searcher", shm_stack)
            stack.add_secret("password-gitea-database-admin", password(20))
            stack.add_secret("password-hedgedoc-database-admin", password(20))
            stack.add_secret("password-nexus-admin", password(20))
            stack.add_secret("password-user-database-admin", password(20))
            stack.add_secret("password-secure-research-desktop-admin", password(20))
            stack.add_secret("token-azuread-graphapi", graph_api.token, replace=True)

            # Deploy Azure infrastructure with Pulumi
            stack.deploy()

            # Add Pulumi infrastructure information to the config file
            config.read_stack(stack.stack_name, stack.local_stack_path)

            # Upload config to blob storage
            config.upload()

            # Provision SRE with anything that could not be done in Pulumi
            manager = SREProvisioningManager(
                available_vm_skus=self.available_vm_skus(config),
                shm_stack=shm_stack,
                sre_name=sre_name,
                sre_stack=stack,
                subscription_name=config.subscription_name,
                timezone=config.shm.timezone,
            )
            manager.run()

        except DataSafeHavenException as exc:
            raise DataSafeHavenException(
                f"Could not deploy Secure Research Environment {sre_name}.\n{str(exc)}"
            ) from exc

    def update_config(
        self,
        sre_name,
        config: Config,
        allow_copy: Optional[bool] = None,
        allow_paste: Optional[bool] = None,
        data_provider_ip_addresses: Optional[List[str]] = None,
        research_desktops: Optional[List[str]] = None,
        software_packages: Optional[SoftwarePackageCategory] = None,
        user_ip_addresses: Optional[List[str]] = None,
    ) -> None:
        # Create a config entry for this SRE if it does not exist
        if sre_name not in config.sres.keys():
            highest_index = max([0] + [sre.index for sre in config.sres.values()])
            config.sres[sre_name].index = highest_index + 1

        # Set whether copying text out of the SRE is allowed
        if allow_copy is not None:
            if config.sres[sre_name].remote_desktop.allow_copy and (
                config.sres[sre_name].remote_desktop.allow_copy != allow_copy
            ):
                self.logger.debug(
                    f"Overwriting existing text copying rule {config.sres[sre_name].remote_desktop.allow_copy}"
                )
            self.logger.info(
                f"Setting [bold]text copying out of SRE {sre_name}[/] to [green]{'allowed' if allow_copy else 'forbidden'}[/]."
            )
            config.sres[sre_name].remote_desktop.allow_copy = allow_copy
        if config.sres[sre_name].remote_desktop.allow_copy is None:
            raise DataSafeHavenConfigException(
                "No text copying rule was found. Use [bright_cyan]'--allow-copy / -c'[/] to set one."
            )

        # Set whether pasting text into the SRE is allowed
        if allow_paste is not None:
            if config.sres[sre_name].remote_desktop.allow_paste and (
                config.sres[sre_name].remote_desktop.allow_paste != allow_paste
            ):
                self.logger.debug(
                    f"Overwriting existing text pasting rule {config.sres[sre_name].remote_desktop.allow_paste}"
                )
            self.logger.info(
                f"Setting [bold]text pasting into SRE {sre_name}[/] to [green]{'allowed' if allow_paste else 'forbidden'}[/]."
            )
            config.sres[sre_name].remote_desktop.allow_paste = allow_paste
        if config.sres[sre_name].remote_desktop.allow_paste is None:
            raise DataSafeHavenConfigException(
                "No text pasting rule was found. Use [bright_cyan]'--allow-paste / -p'[/] to set one."
            )

        # Set data provider IP addresses
        if data_provider_ip_addresses:
            if config.sres[sre_name].data_provider_ip_addresses and (
                config.sres[sre_name].data_provider_ip_addresses
                != data_provider_ip_addresses
            ):
                self.logger.debug(
                    f"Overwriting existing data provider IP addresses {config.sres[sre_name].data_provider_ip_addresses}"
                )
            self.logger.info(
                f"Setting [bold]data provider IP addresses[/] to [green]{data_provider_ip_addresses}[/]."
            )
            config.sres[
                sre_name
            ].data_provider_ip_addresses = data_provider_ip_addresses
        if len(config.sres[sre_name].data_provider_ip_addresses) == 0:
            raise DataSafeHavenConfigException(
                "No data provider IP addresses were found. Use [bright_cyan]'--data-provider-ip-address / -d'[/] to set one."
            )

        # Set research desktops
        if research_desktops:
            if config.sres[sre_name].research_desktops and (
                config.sres[sre_name].research_desktops != research_desktops
            ):
                self.logger.debug(
                    f"Overwriting existing research desktops {config.sres[sre_name].research_desktops}"
                )
            self.logger.info(
                f"Setting [bold]research desktops[/] to [green]{research_desktops}[/]."
            )
            # Construct VM details
            idx_cpu, idx_gpu = 0, 0
            available_vm_skus = self.available_vm_skus(config)
            for vm_sku in research_desktops:
                if int(available_vm_skus[vm_sku]["GPUs"]) > 0:
                    vm_name = f"srd-gpu-{idx_gpu:02d}"
                    idx_gpu += 1
                else:
                    vm_name = f"srd-cpu-{idx_cpu:02d}"
                    idx_cpu += 1
                config.sres[sre_name].add_research_desktop(vm_name)
                config.sres[sre_name].research_desktops[vm_name].sku = vm_sku
        if len(config.sres[sre_name].research_desktops) == 0:
            raise DataSafeHavenConfigException(
                "No research desktops were found. Use [bright_cyan]'--research-desktop / -r'[/] to add one."
            )

        # Select which software packages can be installed by users
        if software_packages is not None:
            if config.sres[sre_name].software_packages and (
                config.sres[sre_name].software_packages != software_packages
            ):
                self.logger.debug(
                    f"Overwriting existing software package rule {config.sres[sre_name].software_packages}"
                )
            self.logger.info(
                f"Setting [bold]allowed software packages in SRE {sre_name}[/] to [green]{'allowed' if software_packages else 'forbidden'}[/]."
            )
            config.sres[sre_name].software_packages = software_packages
        if not config.sres[sre_name].software_packages:
            raise DataSafeHavenConfigException(
                "No software package rule was found. Use [bright_cyan]'--software-packages / -s'[/] to set one."
            )

        # Set user IP addresses
        if user_ip_addresses:
            if config.sres[sre_name].research_user_ip_addresses and (
                config.sres[sre_name].research_user_ip_addresses != user_ip_addresses
            ):
                self.logger.debug(
                    f"Overwriting existing user IP addresses {config.sres[sre_name].research_user_ip_addresses}"
                )
            self.logger.info(
                f"Setting [bold]user IP addresses[/] to [green]{user_ip_addresses}[/]."
            )
            config.sres[sre_name].research_user_ip_addresses = user_ip_addresses
        if len(config.sres[sre_name].research_user_ip_addresses) == 0:
            raise DataSafeHavenConfigException(
                "No user IP addresses were found. Use [bright_cyan]'--user-ip-address / -u'[/] to set one."
            )

    def available_vm_skus(self, config: Config) -> Dict[str, Dict[str, Any]]:
        """Load available VM SKUs for this region"""
        if not self._available_vm_skus:
            azure_api = AzureApi(config.subscription_name)
            self._available_vm_skus = azure_api.list_available_vm_skus(
                config.azure.location
            )
        return self._available_vm_skus
