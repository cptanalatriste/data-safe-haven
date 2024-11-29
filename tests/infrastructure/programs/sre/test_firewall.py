import pytest
from data_safe_haven.infrastructure.programs.sre.firewall import SREFirewallProps


@pytest.fixture
def firewall_props_internet_enabled(
    location,
    resource_group,
    subnet_apt_proxy_server,
    subnet_clamav_mirror,
    subnet_firewall,
    subnet_firewall_management,
    subnet_guacamole_containers,
    subnet_identity_containers,
    subnet_user_services_software_repositories,
    subnet_workspaces,
) -> SREFirewallProps:
    return SREFirewallProps(
        allow_workspace_internet=True,
        location=location,
        resource_group_name=resource_group.name,
        route_table_name="test-route-table",
        subnet_apt_proxy_server=subnet_apt_proxy_server,
        subnet_clamav_mirror=subnet_clamav_mirror,
        subnet_firewall=subnet_firewall,
        subnet_firewall_management=subnet_firewall_management,
        subnet_guacamole_containers=subnet_guacamole_containers,
        subnet_identity_containers=subnet_identity_containers,
        subnet_user_services_software_repositories=subnet_user_services_software_repositories,
        subnet_workspaces=subnet_workspaces,
    )
