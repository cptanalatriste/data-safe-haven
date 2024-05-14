from collections.abc import MutableMapping

from pulumi.automation import (
    ConfigValue,
    LocalWorkspace,
    ProjectSettings,
    Stack,
    StackSettings,
)
from pytest import fixture, raises

from data_safe_haven.config import DSHPulumiProject
from data_safe_haven.exceptions import (
    DataSafeHavenConfigError,
    DataSafeHavenPulumiError,
)
from data_safe_haven.infrastructure import SHMProjectManager
from data_safe_haven.infrastructure.project_manager import (
    AzureCliSingleton,
    ProjectManager,
    PulumiAccount,
)


@fixture
def mock_azure_cli_confirm(monkeypatch):
    """Always pass AzureCliSingleton.confirm without attempting login"""
    monkeypatch.setattr(AzureCliSingleton, "confirm", lambda self: None)  # noqa: ARG005


@fixture
def mock_install_plugins(monkeypatch):
    """Skip installing Pulumi plugins"""
    monkeypatch.setattr(
        ProjectManager, "install_plugins", lambda self: None  # noqa: ARG005
    )


@fixture
def offline_pulumi_account(monkeypatch, mock_azure_cli_confirm):  # noqa: ARG001
    """Overwrite PulumiAccount so that it runs locally"""
    monkeypatch.setattr(
        PulumiAccount, "env", {"PULUMI_CONFIG_PASSPHRASE": "passphrase"}
    )


@fixture
def local_project_settings(context_no_secrets, mocker):  # noqa: ARG001
    """Overwrite adjust project settings to work locally, no secrets"""
    mocker.patch.object(
        ProjectManager,
        "project_settings",
        ProjectSettings(
            name="data-safe-haven",
            runtime="python",
        ),
    )


@fixture
def shm_stack_manager(
    context_no_secrets,
    config_sres,
    pulumi_config_no_key,
    mock_azure_cli_confirm,  # noqa: ARG001
    mock_install_plugins,  # noqa: ARG001
    mock_key_vault_key,  # noqa: ARG001
    offline_pulumi_account,  # noqa: ARG001
    local_project_settings,  # noqa: ARG001
):
    return SHMProjectManager(
        context=context_no_secrets,
        config=config_sres,
        pulumi_config=pulumi_config_no_key,
    )


class TestSHMProjectManager:
    def test_constructor(
        self,
        context_no_secrets,
        config_sres,
        pulumi_config_no_key,
        pulumi_project,
        mock_azure_cli_confirm,  # noqa: ARG002
        mock_install_plugins,  # noqa: ARG002
    ):
        shm = SHMProjectManager(context_no_secrets, config_sres, pulumi_config_no_key)
        assert isinstance(shm, SHMProjectManager)
        assert isinstance(shm, ProjectManager)
        assert shm.context == context_no_secrets
        assert shm.cfg == config_sres
        assert shm.pulumi_project == pulumi_project

    def test_new_project(
        self,
        context_no_secrets,
        config_sres,
        pulumi_config_empty,
        mock_azure_cli_confirm,  # noqa: ARG002
        mock_install_plugins,  # noqa: ARG002
    ):
        shm = SHMProjectManager(
            context_no_secrets, config_sres, pulumi_config_empty, create_project=True
        )
        assert isinstance(shm, SHMProjectManager)
        assert isinstance(shm, ProjectManager)
        assert shm.context == context_no_secrets
        assert shm.cfg == config_sres
        # Ensure a project was created
        assert isinstance(shm.pulumi_project, DSHPulumiProject)
        assert "acmedeployment" in pulumi_config_empty.project_names
        assert pulumi_config_empty["acmedeployment"].stack_config == {}
        assert pulumi_config_empty.encrypted_key is None

    def test_new_project_fail(
        self,
        context_no_secrets,
        config_sres,
        pulumi_config_empty,
        mock_azure_cli_confirm,  # noqa: ARG002
        mock_install_plugins,  # noqa: ARG002
    ):
        shm = SHMProjectManager(
            context_no_secrets, config_sres, pulumi_config_empty, create_project=False
        )
        with raises(
            DataSafeHavenConfigError,
            match="No SHM/SRE named acmedeployment is defined.",
        ):
            _ = shm.pulumi_project

    def test_project_settings(self, shm_stack_manager):
        project_settings = shm_stack_manager.project_settings
        assert isinstance(project_settings, ProjectSettings)
        assert project_settings.name == "data-safe-haven"
        assert project_settings.runtime == "python"
        assert project_settings.backend is None

    def test_stack_settings(self, shm_stack_manager):
        stack_settings = shm_stack_manager.stack_settings
        assert isinstance(stack_settings, StackSettings)
        assert stack_settings.config == shm_stack_manager.pulumi_project.stack_config
        assert (
            stack_settings.encrypted_key
            == shm_stack_manager.pulumi_config.encrypted_key
        )
        assert (
            stack_settings.secrets_provider
            == shm_stack_manager.context.pulumi_secrets_provider_url
        )

    def test_pulumi_project(self, shm_stack_manager, pulumi_project):
        assert shm_stack_manager.pulumi_project == pulumi_project

    def test_run_pulumi_command(self, shm_stack_manager):
        stdout = shm_stack_manager.run_pulumi_command("stack ls")
        assert "shm-acmedeployment*" in stdout

    def test_run_pulumi_command_command_error(self, shm_stack_manager):
        with raises(
            DataSafeHavenPulumiError,
            match="Failed to run command.",
        ):
            shm_stack_manager.run_pulumi_command("notapulumicommand")

    def test_stack(self, shm_stack_manager):
        stack = shm_stack_manager.stack
        assert isinstance(stack, Stack)

    def test_stack_config(self, shm_stack_manager):
        stack = shm_stack_manager.stack
        assert stack.name == "shm-acmedeployment"
        assert isinstance(stack.workspace, LocalWorkspace)
        workspace = stack.workspace
        assert (
            workspace.secrets_provider
            == shm_stack_manager.context.pulumi_secrets_provider_url
        )
        config = stack.get_all_config()
        assert config["azure-native:location"].value == "uksouth"
        assert config["data-safe-haven:variable"].value == "5"

    def test_stack_all_config(self, shm_stack_manager):
        config = shm_stack_manager.stack_all_config
        assert isinstance(config, MutableMapping)
        assert isinstance(config["azure-native:location"], ConfigValue)
        assert config["azure-native:location"].value == "uksouth"
        assert config["data-safe-haven:variable"].value == "5"

    def test_update_dsh_pulumi_project(self, shm_stack_manager):
        shm_stack_manager.set_config("new-key", "hello", secret=False)
        config = shm_stack_manager.stack_all_config
        assert "data-safe-haven:new-key" in config
        assert config.get("data-safe-haven:new-key").value == "hello"
        shm_stack_manager.update_dsh_pulumi_project()
        stack_config = shm_stack_manager.pulumi_project.stack_config
        assert "data-safe-haven:new-key" in stack_config
        assert stack_config.get("data-safe-haven:new-key") == "hello"
