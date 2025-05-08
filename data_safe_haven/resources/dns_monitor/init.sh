echo "Logging into Azure ..."
az login --service-principal --username $SERVICE_PRINCIPAL_APPID --password $SERVICE_PRINCIPAL_PASSWORD --tenant $ENTRA_TENANT_ID
echo "Finding container group IP address..."
private_ip=$(az container show --name $CONTAINER_GROUP_NAME --resource-group $RESOURCE_GROUP --subscription $SUBSCRIPTION_ID --query 'ipAddress.ip' -o tsv) && echo $private_ip
echo "Deleting previous DNS record..."
az network private-dns record-set a delete --name $RECORD_NAME --zone-name $PRIVATE_ZONE_NAME --resource-group $RESOURCE_GROUP --subscription $SUBSCRIPTION_ID --yes
echo "Creating DNS record ..."
az network private-dns record-set a create --name $RECORD_NAME --zone-name $PRIVATE_ZONE_NAME --resource-group $RESOURCE_GROUP --subscription $SUBSCRIPTION_ID
az network private-dns record-set a add-record --record-set-name $RECORD_NAME --zone-name $PRIVATE_ZONE_NAME --resource-group $RESOURCE_GROUP --subscription $SUBSCRIPTION_ID --ipv4-address $private_ip
