# Monitoring logs

Logs are collected for numerous parts of a Data Safe Haven.
Some of these logs are ingested into a central location, an Azure [Log Analytics Workspace](https://learn.microsoft.com/azure/azure-monitor/logs/log-analytics-workspace-overview), and others are stored separately.

## Log workspace

Each SRE has its own Log Analytics Workspace.
You can view the workspaces by going to the Azure portal and navigating to [Log Analytics Workspaces](https://portal.azure.com/#browse/Microsoft.OperationalInsights%2Fworkspaces).
Select which Log Analytics Workspace you want to view by clicking on the workspace named `shm-<YOUR_SHM_NAME>-sre-<YOUR_SRE_NAME>-log`.

The logs can be filtered using [Kusto Query Language (KQL)](https://learn.microsoft.com/en-us/azure/azure-monitor/logs/log-query-overview).

## Container logs

Some of the Data Safe Haven infrastructure is provisioned as containers.
These include,

- remote desktop portal
- package proxy
- Gitea and Hedgedoc

Logs from all containers are ingested into the [SRE's log analytics workspace](#log-workspace).
There are two logs

`ContainerEvents_CL`
: Event logs for the container instance resources such as starting, stopping, crashes and pulling images.

`ContainerInstanceLog_CL`
: Container process logs.
: This is where you can view the output of the containerised applications and will be useful for debugging problems.

## Workspace logs

Logs from all user workspaces are ingested into the [SRE's log analytics workspace](#log-workspace) using the [Azure Monitor Agent](https://learn.microsoft.com/en-us/azure/azure-monitor/agents/azure-monitor-agent-overview).

There are three logs

`Perf`
: Usage statistics for individual workspaces, such as percent memory used and percent disk space used.

`Syslog`
: Linux system logs for individual workspaces, useful for debugging problems related to system processes.

`Heartbeat`
: Verification that the Azure Monitor Agent is present on the workspaces and is able to connect to the [log analytics workspace](#log-workspace).
