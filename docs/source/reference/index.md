# Reference

## `dsh` command line interface

The `dsh` commands are the entrypoint to the Data Safe Haven command line interface.
All commands begin with `dsh`.

:::{typer} data_safe_haven.commands.cli:application
:prog: dsh
:width: 65
:::

## `config` commands

`config` commands are used to manage the configuration files that define SHMs and SREs.

:::{typer} data_safe_haven.commands.config:config_command_group
:width: 65
:prog: dsh config
:show-nested:
:make-sections:
:::

## `context` commands

`context` commands are used to manage the Data Safe Haven contexts, which are the grouping within which a single SHM and its associated SREs are organised.

:::{typer} data_safe_haven.commands.context:context_command_group
:width: 65
:prog: dsh context
:show-nested:
:make-sections:
:::

## `shm` commands

`shm` commands are used to deploy or teardown DSH Safe Haven Management infrastructure

:::{typer} data_safe_haven.commands.shm:shm_command_group
:width: 65
:prog: dsh shm
:show-nested:
:make-sections:
:::

## `sre` commands

`sre` commands are used to deploy or teardown the infrastructure for DSH Secure Research Environments

:::{typer} data_safe_haven.commands.sre:sre_command_group
:width: 65
:prog: dsh sre
:show-nested:
:make-sections:
:::

## `users` commands

`users` commands are used to manage users on the Entra ID associated with a DSH deployment.

:::{typer} data_safe_haven.commands.users:users_command_group
:width: 65
:prog: dsh users
:show-nested:
:make-sections:
:::

## `pulumi` commands

:::{typer} data_safe_haven.commands.pulumi:pulumi_command_group
:width: 65
:prog: dsh pulumi
:show-nested:
:make-sections:
:::
