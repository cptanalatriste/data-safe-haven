# Managing SREs

## List available SRE configurations and deployment status

- Run the following if you want to check what SRE configurations are available in the current context, and whether those SREs are deployed

```{code} shell
$ dsh config available
```

which will give output like the following

```{code} shell
Available SRE configurations for context 'green':
┏━━━━━━━━━━━━━━┳━━━━━━━━━━┓
┃ SRE Name     ┃ Deployed ┃
┡━━━━━━━━━━━━━━╇━━━━━━━━━━┩
│ emerald      │ x        │
│ jade         │          │
│ olive        │          │
└──────────────┴──────────┘
```

## Remove a deployed Data Safe Haven

- Run the following if you want to teardown a deployed SRE:

```{code} shell
$ dsh sre teardown YOUR_SRE_NAME
```

::::{admonition} Tearing down an SRE is destructive and irreversible
:class: danger
Running `dsh sre teardown` will destroy **all** resources deployed within the SRE.
Ensure that any desired outputs have been extracted before deleting the SRE.
**All** data remaining on the SRE will be deleted.
The user groups for the SRE on Microsoft Entra ID will also be deleted.
::::

- Run the following if you want to teardown the deployed SHM:

```{code} shell
$ dsh shm teardown
```

::::{admonition} Tearing down an SHM
:class: warning
Tearing down the SHM permanently deletes **all** remotely stored configuration and state data.
Tearing down the SHM also renders the SREs inaccessible to users and prevents them from being fully managed using the CLI.
All SREs associated with the SHM should be torn down before the SHM is torn down.
::::
