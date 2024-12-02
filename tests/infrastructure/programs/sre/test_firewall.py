from functools import partial
from typing import Callable

import pulumi
import pulumi.runtime
import pytest
from pulumi_azure_native import network

from data_safe_haven.infrastructure.programs.sre.firewall import (
    SREFirewallComponent,
    SREFirewallProps,
)

from ..resource_assertions import assert_equal, assert_equal_json


@pytest.fixture
def allow_internet_props_setter(
    location: str,
    resource_group_name: str,
    subnet_apt_proxy_server: network.GetSubnetResult,
    subnet_clamav_mirror: network.GetSubnetResult,
    subnet_firewall: network.GetSubnetResult,
    subnet_firewall_management: network.GetSubnetResult,
    subnet_guacamole_containers: network.GetSubnetResult,
    subnet_identity_containers: network.GetSubnetResult,
    subnet_user_services_software_repositories: network.GetSubnetResult,
    subnet_workspaces: network.GetSubnetResult,
) -> Callable[[bool], SREFirewallProps]:

    def set_allow_workspace_internet(
        allow_workspace_internet: bool,  # noqa: FBT001
    ) -> SREFirewallProps:
        return SREFirewallProps(
            allow_workspace_internet=allow_workspace_internet,
            location=location,
            resource_group_name=resource_group_name,
            route_table_name="test-route-table",  # TODO: Move to fixture if works.
            subnet_apt_proxy_server=subnet_apt_proxy_server,
            subnet_clamav_mirror=subnet_clamav_mirror,
            subnet_firewall=subnet_firewall,
            subnet_firewall_management=subnet_firewall_management,
            subnet_guacamole_containers=subnet_guacamole_containers,
            subnet_identity_containers=subnet_identity_containers,
            subnet_user_services_software_repositories=subnet_user_services_software_repositories,
            subnet_workspaces=subnet_workspaces,
        )

    return set_allow_workspace_internet


@pytest.fixture
def allow_internet_component_setter(
    stack_name: str,
    allow_internet_props_setter: Callable[[bool], SREFirewallProps],
    tags: dict[str, str],
) -> Callable[[bool], SREFirewallComponent]:

    def set_allow_workspace_internet(allow_workspace_internet) -> SREFirewallComponent:
        firewall_props: SREFirewallProps = allow_internet_props_setter(
            allow_workspace_internet
        )

        return SREFirewallComponent(
            name="firewall-name",
            stack_name=stack_name,
            props=firewall_props,
            tags=tags,
        )

    return set_allow_workspace_internet


class TestSREFirewallProps:

    @pulumi.runtime.test
    def test_props_allow_workspace_internet_enabled(
        self, allow_internet_props_setter: Callable[[bool], SREFirewallProps]
    ):
        firewall_props: SREFirewallProps = allow_internet_props_setter(
            allow_workspace_internet=True
        )
        pulumi.Output.from_input(firewall_props.allow_workspace_internet).apply(
            partial(assert_equal, True), run_with_unknowns=True  # noqa: FBT003
        )

    @pulumi.runtime.test
    def test_props_allow_workspace_internet_disabled(
        self, allow_internet_props_setter: Callable[[bool], SREFirewallProps]
    ):
        firewall_props: SREFirewallProps = allow_internet_props_setter(
            allow_workspace_internet=False
        )
        pulumi.Output.from_input(firewall_props.allow_workspace_internet).apply(
            partial(assert_equal, False), run_with_unknowns=True  # noqa: FBT003
        )


class TestSREFirewallComponent:

    @pulumi.runtime.test
    def test_component_allow_workspace_internet_enabled(
        self,
        allow_internet_component_setter: Callable[[bool], SREFirewallComponent],
    ):
        firewall_component: SREFirewallComponent = allow_internet_component_setter(
            allow_workspace_internet=True
        )

        firewall_component.firewall.application_rule_collections.apply(
            partial(assert_equal_json, []),
            run_with_unknowns=True,
        )
