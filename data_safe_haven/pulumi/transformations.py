"""Common transformations needed when manipulating Pulumi resources"""
# Third party imports
from pulumi_azure_native import network, resources

# Local imports
from data_safe_haven.exceptions import DataSafeHavenPulumiException


def get_id_from_rg(rg: resources.ResourceGroup) -> str:
    if id_ := rg.name:
        return str(id_)
    raise DataSafeHavenPulumiException(f"Resource group '{rg.name}'has no ID.")


def get_id_from_subnet(subnet: network.GetSubnetResult) -> str:
    if id_ := subnet.id:
        return str(id_)
    raise DataSafeHavenPulumiException(f"Subnet '{subnet.name}' has no ID.")


def get_name_from_subnet(subnet: network.GetSubnetResult) -> str:
    if name := subnet.name:
        return str(name)
    raise DataSafeHavenPulumiException(f"Subnet '{subnet.id}' has no name.")


def get_name_from_vnet(vnet: network.VirtualNetwork) -> str:
    if name := vnet.name:
        return str(name)
    raise DataSafeHavenPulumiException(f"Virtual network '{vnet.id}'has no name.")


def get_name_from_rg(rg: resources.ResourceGroup) -> str:
    if name := rg.name:
        return str(name)
    raise DataSafeHavenPulumiException(f"Resource group '{rg.id}'has no name.")
