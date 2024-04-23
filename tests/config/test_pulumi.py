from unittest.mock import patch

from pytest import fixture, raises

from data_safe_haven.config.pulumi import DSHPulumiConfig, DSHPulumiProject
from data_safe_haven.exceptions import (
    DataSafeHavenConfigError,
    DataSafeHavenParameterError,
)
from data_safe_haven.external import AzureApi
from data_safe_haven.functions import b64encode


@fixture
def stack_config():
    return """secretsprovider: azurekeyvault://example
encryptedkey: zjhejU2XsOKLo95w9CLD
config:
  azure-native:location: uksouth
"""


@fixture
def stack_config_encoded(stack_config):
    return b64encode(stack_config)


@fixture
def pulumi_project(stack_config_encoded):
    return DSHPulumiProject(stack_config=stack_config_encoded)


@fixture
def pulumi_project2():
    return DSHPulumiProject(
        stack_config=b64encode(
            """secretsprovider: azurekeyvault://example
encryptedkey: B5tHWpqERXgblwRZ7wgu
config:
  azure-native:location: uksouth
"""
        ),
    )


class TestDSHPulumiProject:
    def test_pulumi_project(self, pulumi_project):
        assert "encryptedkey: zjhejU2XsOKLo95w9CLD" in pulumi_project.stack_config

    def test_dump(self, pulumi_project, stack_config_encoded):
        d = pulumi_project.model_dump()
        assert d.get("stack_config") == stack_config_encoded

    def test_eq(self, pulumi_project):
        assert pulumi_project == pulumi_project.model_copy(deep=True)

    def test_not_eq(self, pulumi_project, pulumi_project2):
        assert pulumi_project != pulumi_project2


@fixture
def pulumi_config(pulumi_project, pulumi_project2):
    return DSHPulumiConfig(
        projects={"my_project": pulumi_project, "other_project": pulumi_project2}
    )


@fixture
def pulumi_config_yaml():
    return """projects:
  my_project:
    stack_config: c2VjcmV0c3Byb3ZpZGVyOiBhenVyZWtleXZhdWx0Oi8vZXhhbXBsZQplbmNyeXB0ZWRrZXk6IHpqaGVqVTJYc09LTG85NXc5Q0xECmNvbmZpZzoKICBhenVyZS1uYXRpdmU6bG9jYXRpb246IHVrc291dGgK
  other_project:
    stack_config: c2VjcmV0c3Byb3ZpZGVyOiBhenVyZWtleXZhdWx0Oi8vZXhhbXBsZQplbmNyeXB0ZWRrZXk6IEI1dEhXcHFFUlhnYmx3Ulo3d2d1CmNvbmZpZzoKICBhenVyZS1uYXRpdmU6bG9jYXRpb246IHVrc291dGgK
"""


class TestDSHPulumiConfig:
    def test_pulumi_config(self, pulumi_project):
        config = DSHPulumiConfig(projects={"my_project": pulumi_project})
        assert config.projects["my_project"] == pulumi_project

    def test_getitem(self, pulumi_config, pulumi_project, pulumi_project2):
        assert pulumi_config["my_project"] == pulumi_project
        assert pulumi_config["other_project"] == pulumi_project2

    def test_getitem_type_error(self, pulumi_config):
        with raises(TypeError, match="'key' must be a string."):
            pulumi_config[0]

    def test_getitem_index_error(self, pulumi_config):
        with raises(KeyError, match="No configuration for DSH Pulumi Project Ringo."):
            pulumi_config["Ringo"]

    def test_delitem(self, pulumi_config):
        assert len(pulumi_config.projects) == 2
        del pulumi_config["my_project"]
        assert len(pulumi_config.projects) == 1

    def test_delitem_value_error(self, pulumi_config):
        with raises(TypeError, match="'key' must be a string."):
            del pulumi_config[-1]

    def test_delitem_index_error(self, pulumi_config):
        with raises(KeyError, match="No configuration for DSH Pulumi Project Ringo."):
            del pulumi_config["Ringo"]

    def test_setitem(self, pulumi_config, pulumi_project):
        del pulumi_config["my_project"]
        assert len(pulumi_config.project_names) == 1
        assert "my_project" not in pulumi_config.project_names
        pulumi_config["my_project"] = pulumi_project
        assert len(pulumi_config.project_names) == 2
        assert "my_project" in pulumi_config.project_names

    def test_setitem_type_error(self, pulumi_config):
        with raises(TypeError, match="'key' must be a string."):
            pulumi_config[1] = 5

    def test_setitem_value_error(self, pulumi_config):
        with raises(ValueError, match="Stack other_project already exists."):
            pulumi_config["other_project"] = 5

    def test_project_names(self, pulumi_config):
        assert "my_project" in pulumi_config.project_names

    def test_to_yaml(self, pulumi_config):
        yaml = pulumi_config.to_yaml()
        assert isinstance(yaml, str)
        assert "projects:" in yaml
        assert "config: c2VjcmV0" in yaml

    def test_from_yaml(self, pulumi_config_yaml):
        DSHPulumiConfig.from_yaml(pulumi_config_yaml)

    def test_from_yaml_invalid_yaml(self):
        with raises(
            DataSafeHavenConfigError,
            match="Could not parse Pulumi configuration as YAML.",
        ):
            DSHPulumiConfig.from_yaml("a: [1,2")

    def test_from_yaml_not_dict(self):
        with raises(
            DataSafeHavenConfigError,
            match="Unable to parse Pulumi configuration as a dict.",
        ):
            DSHPulumiConfig.from_yaml("5")

    def test_from_yaml_validation_error(self):
        not_valid = "projects: -3"
        with raises(
            DataSafeHavenParameterError, match="Could not load Pulumi configuration."
        ):
            DSHPulumiConfig.from_yaml(not_valid)

    def test_upload(self, pulumi_config, context):
        with patch.object(AzureApi, "upload_blob", return_value=None) as mock_method:
            pulumi_config.upload(context)

        mock_method.assert_called_once_with(
            pulumi_config.to_yaml(),
            DSHPulumiConfig.filename,
            context.resource_group_name,
            context.storage_account_name,
            context.storage_container_name,
        )

    def test_from_remote(self, pulumi_config_yaml, context):
        with patch.object(
            AzureApi, "download_blob", return_value=pulumi_config_yaml
        ) as mock_method:
            pulumi_config = DSHPulumiConfig.from_remote(context)

        assert isinstance(pulumi_config, DSHPulumiConfig)
        assert pulumi_config["my_project"]
        assert len(pulumi_config.projects) == 2

        mock_method.assert_called_once_with(
            DSHPulumiConfig.filename,
            context.resource_group_name,
            context.storage_account_name,
            context.storage_container_name,
        )
