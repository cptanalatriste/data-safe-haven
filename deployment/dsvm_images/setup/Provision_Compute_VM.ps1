param(
    [Parameter(Mandatory = $true, HelpMessage = "Enter SHM ID (usually a string e.g enter 'testa' for Turing Development Safe Haven A)")]
    [string]$shmId,
    [Parameter(Mandatory = $false, HelpMessage = "Source image (one of 'Ubuntu1804' [default], 'Ubuntu1810', 'Ubuntu1904', 'Ubuntu1910'")]
    [ValidateSet("Ubuntu1804", "Ubuntu2004")]
    [string]$sourceImage = "Ubuntu2004",
    [Parameter(Mandatory = $false, HelpMessage = "VM size to use (e.g. 'Standard_E4_v3'. Using 'default' will use the value from the configuration file)")]
    [ValidateSet("default", "Standard_D4_v3", "Standard_E2_v3", "Standard_E4_v3", "Standard_E8_v3", "Standard_F4s_v2", "Standard_F8s_v2", "Standard_H8")]
    [string]$vmSize = "default"
)

Import-Module Az -ErrorAction Stop
Import-Module $PSScriptRoot/../../common/AzureStorage -Force -ErrorAction Stop
Import-Module $PSScriptRoot/../../common/Configuration -Force -ErrorAction Stop
Import-Module $PSScriptRoot/../../common/DataStructures -Force -ErrorAction Stop
Import-Module $PSScriptRoot/../../common/Deployments -Force -ErrorAction Stop
Import-Module $PSScriptRoot/../../common/Logging -Force -ErrorAction Stop
Import-Module $PSScriptRoot/../../common/Security -Force -ErrorAction Stop
Import-Module $PSScriptRoot/../../common/Templates -Force -ErrorAction Stop


# Get config and original context before changing subscription
# ------------------------------------------------------------
$config = Get-ShmConfig -shmId $shmId
$originalContext = Get-AzContext
$null = Set-AzContext -SubscriptionId $config.dsvmImage.subscription -ErrorAction Stop


# Select which VM size to use
# ---------------------------
if ($vmSize -eq "default") { $vmSize = $config.dsvmImage.build.vm.size }
# Standard_E2_v3  => 2 cores; 16GB RAM; £0.1163/hr; 2.3 GHz :: build 15h33m56s => £1.81
# Standard_F4s_v2 => 4 cores;  8GB RAM; £0.1506/hr; 3.7 GHz :: build 12h22m17s => £1.86
# Standard_D4_v3  => 4 cores; 16GB RAM; £0.1730/hr; 2.4 GHz :: build 16h41m13s => £2.88
# Standard_E4_v3  => 4 cores; 32GB RAM; £0.2326/hr; 2.3 GHz :: build 16h40m9s  => £3.88
# Standard_H8     => 8 cores; 56GB RAM; £0.4271/hr; 3.6 GHz :: build 12h56m6s  => £5.52
# Standard_E8_v3  => 8 cores; 64GB RAM; £0.4651/hr; 2.3 GHz :: build 17h8m17s  => £7.97


# Select which source URN to base the build on
# --------------------------------------------
if ($sourceImage -eq "Ubuntu1804") {
    $baseImageSku = "18.04-LTS"
    $shortVersion = "1804"
    Add-LogMessage -Level Warning "Note that '$sourceImage' is out-of-date. Please consider using a newer base Ubuntu version."
} elseif ($sourceImage -eq "Ubuntu2004") {
    $baseImageSku = "20.04-LTS"
    $shortVersion = "2004"
} else {
    Add-LogMessage -Level Fatal "Did not recognise source image '$sourceImage'!"
}
$buildVmName = "ComputeVM-Ubuntu${shortVersion}"
$cloudInitTemplate = Get-Content (Join-Path $PSScriptRoot ".." "cloud_init" "cloud-init-buildimage-ubuntu-${shortVersion}.yaml") -Raw


# Create resource groups if they do not exist
# -------------------------------------------
$null = Deploy-ResourceGroup -Name $config.dsvmImage.build.rg -Location $config.dsvmImage.location
$null = Deploy-ResourceGroup -Name $config.dsvmImage.bootdiagnostics.rg -Location $config.dsvmImage.location
$null = Deploy-ResourceGroup -Name $config.dsvmImage.network.rg -Location $config.dsvmImage.location
$null = Deploy-ResourceGroup -Name $config.dsvmImage.keyVault.rg -Location $config.dsvmImage.location


# Ensure the Key Vault exists and set its access policies
# -------------------------------------------------------
$null = Deploy-KeyVault -Name $config.dsvmImage.keyVault.name -ResourceGroupName $config.dsvmImage.keyVault.rg -Location $config.dsvmImage.location
Set-KeyVaultPermissions -Name $config.dsvmImage.keyVault.name -GroupName $config.azureAdminGroupName


# Ensure that VNET and subnet exist
# ---------------------------------
$vnet = Deploy-VirtualNetwork -Name $config.dsvmImage.build.vnet.name -ResourceGroupName $config.dsvmImage.network.rg -AddressPrefix $config.dsvmImage.build.vnet.cidr -Location $config.dsvmImage.location
$subnet = Deploy-Subnet -Name $config.dsvmImage.build.subnet.name -VirtualNetwork $vnet -AddressPrefix $config.dsvmImage.build.subnet.cidr


# Set up the build NSG
# --------------------
Add-LogMessage -Level Info "Ensure that build NSG '$($config.dsvmImage.build.nsg.name)' exists..."
$buildNsg = Deploy-NetworkSecurityGroup -Name $config.dsvmImage.build.nsg.name -ResourceGroupName $config.dsvmImage.network.rg -Location $config.dsvmImage.location
# Get list of IP addresses which are allowed to connect to the VM candidates
$allowedIpAddresses = @($config.dsvmImage.build.nsg.allowedIpAddresses)
$existingRule = Get-AzNetworkSecurityRuleConfig -NetworkSecurityGroup $buildNsg | Where-Object { $_.Priority -eq 1000 }
if ($existingRule) {
    $allowedIpAddresses += @($existingRule.SourceAddressPrefix)
}
$allowedIpAddresses = $allowedIpAddresses | Where-Object { $_ } | Sort-Object | Get-Unique
# Add the necessary rules
Add-NetworkSecurityGroupRule -NetworkSecurityGroup $buildNsg `
                             -Access Allow `
                             -Name "AllowBuildAdminSSH" `
                             -Description "Allow port 22 for management over ssh" `
                             -DestinationAddressPrefix * `
                             -DestinationPortRange 22 `
                             -Direction Inbound `
                             -Priority 1000 `
                             -Protocol TCP `
                             -SourceAddressPrefix $allowedIpAddresses `
                             -SourcePortRange *
Add-NetworkSecurityGroupRule -NetworkSecurityGroup $buildNsg `
                             -Access Deny `
                             -Name "DenyAll" `
                             -Description "Inbound deny all" `
                             -DestinationAddressPrefix * `
                             -DestinationPortRange * `
                             -Direction Inbound `
                             -Priority 3000 `
                             -Protocol * `
                             -SourceAddressPrefix * `
                             -SourcePortRange *
$null = Set-SubnetNetworkSecurityGroup -VirtualNetwork $vnet -Subnet $subnet -NetworkSecurityGroup $buildNsg


# Convert PyPI package lists into requirements files
# --------------------------------------------------
$temporaryDir = New-Item -ItemType Directory -Path (Join-Path ([System.IO.Path]::GetTempPath()) ([Guid]::NewGuid().ToString()))
$packageVersions = Get-Content (Join-Path $PSScriptRoot ".." "packages" "python-requirements.json") | ConvertFrom-Json -AsHashtable
foreach ($packageList in Get-ChildItem (Join-Path $PSScriptRoot ".." "packages" "packages-python-pypi-*.list")) {
    $pythonVersion = ($packageList.BaseName -split "-")[-1]
    Get-Content $packageList | `
        ForEach-Object {
            if ($packageVersions["py${pythonVersion}"].Contains($_)) { "$_$($packageVersions["py${pythonVersion}"][$_])" } else { "$_" }
        } | Out-File (Join-Path $temporaryDir "python-requirements-py${pythonVersion}.txt")
}


# Load the cloud-init template then add resources and expand mustache placeholders
# --------------------------------------------------------------------------------
$config["dbeaver"] = @{
    drivers = $(Get-Content -Raw -Path "../packages/dbeaver-driver-versions.json" | ConvertFrom-Json -AsHashtable)
}
$cloudInitTemplate = Expand-CloudInitResources -Template $cloudInitTemplate -ResourcePath (Join-Path $PSScriptRoot ".." "cloud_init" "scripts")
$cloudInitTemplate = Expand-CloudInitResources -Template $cloudInitTemplate -ResourcePath (Join-Path $PSScriptRoot ".." "packages")
$cloudInitTemplate = Expand-CloudInitResources -Template $cloudInitTemplate -ResourcePath $temporaryDir.FullName
$cloudInitTemplate = Expand-MustacheTemplate -Template $cloudInitTemplate -Parameters $config
$null = Remove-Item -Path $temporaryDir -Recurse -Force -ErrorAction SilentlyContinue


# Construct build VM parameters
# -----------------------------
$buildVmAdminUsername = Resolve-KeyVaultSecret -VaultName $config.dsvmImage.keyVault.name -SecretName $config.keyVault.secretNames.buildImageAdminUsername -DefaultValue "dsvmbuildadmin" -AsPlaintext
$buildVmBootDiagnosticsAccount = Deploy-StorageAccount -Name $config.dsvmImage.bootdiagnostics.accountName -ResourceGroupName $config.dsvmImage.bootdiagnostics.rg -Location $config.dsvmImage.location
$buildVmName = "Candidate${buildVmName}-$(Get-Date -Format "yyyyMMddHHmm")"
$buildVmNic = Deploy-VirtualMachineNIC -Name "$buildVmName-NIC" -ResourceGroupName $config.dsvmImage.build.rg -Subnet $subnet -PublicIpAddressAllocation "Static" -Location $config.dsvmImage.location
$adminPasswordName = "$($config.keyVault.secretNames.buildImageAdminPassword)-${buildVmName}"


# Check cloud-init size
# ---------------------
$CloudInitEncodedLength = ($cloudInitTemplate | ConvertTo-Base64).Length
if ($CloudInitEncodedLength / 87380 -gt 0.9) {
    Add-LogMessage -Level Warning "The current cloud-init size ($CloudInitEncodedLength Base64 characters) is more than 90% of the limit of 87380 characters!"
}


# Deploy the VM
# -------------
Add-LogMessage -Level Info "Provisioning a new VM image in $($config.dsvmImage.build.rg) '$($config.dsvmImage.subscription)'..."
Add-LogMessage -Level Info "  VM name: $buildVmName"
Add-LogMessage -Level Info "  VM size: $vmSize"
Add-LogMessage -Level Info "  Base image: Ubuntu $baseImageSku"
$params = @{
    Name                   = $buildVmName
    Size                   = $vmSize
    AdminPassword          = (Resolve-KeyVaultSecret -VaultName $config.dsvmImage.keyVault.name -SecretName $adminPasswordName -DefaultLength 20)
    AdminUsername          = $buildVmAdminUsername
    BootDiagnosticsAccount = $buildVmBootDiagnosticsAccount
    CloudInitYaml          = $cloudInitTemplate
    Location               = $config.dsvmImage.location
    NicId                  = $buildVmNic.Id
    OsDiskSizeGb           = $config.dsvmImage.build.vm.diskSizeGb
    OsDiskType             = "Standard_LRS"
    ResourceGroupName      = $config.dsvmImage.build.rg
    ImageSku               = $baseImageSku
}
$vm = Deploy-UbuntuVirtualMachine @params -NoWait


# Tag the VM with the git commit hash
# -----------------------------------
$null = New-AzTag -ResourceId $vm.Id -Tag @{"Build commit hash" = $(git rev-parse --verify HEAD) }


# Log connection details for monitoring this build
# ------------------------------------------------
$publicIp = (Get-AzPublicIpAddress -ResourceGroupName $config.dsvmImage.build.rg | Where-Object { $_.Id -Like "*${buildVmName}-NIC-PIP" }).IpAddress
Add-LogMessage -Level Info "This process will take several hours to complete."
Add-LogMessage -Level Info "  You can monitor installation progress using: ssh $buildVmAdminUsername@$publicIp"
Add-LogMessage -Level Info "  The password for this account can be found in the '${adminPasswordName}' secret in the Azure Key Vault at:"
Add-LogMessage -Level Info "  $($config.dsvmImage.subscription) > $($config.dsvmImage.keyVault.rg) > $($config.dsvmImage.keyVault.name)"
Add-LogMessage -Level Info "  Once logged in, check the installation progress with: /opt/verification/analyse_build.py"
Add-LogMessage -Level Info "  The full log file can be viewed with: tail -f -n+1 /var/log/cloud-init-output.log"


# Switch back to original subscription
# ------------------------------------
$null = Set-AzContext -Context $originalContext -ErrorAction Stop
