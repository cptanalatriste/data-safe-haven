# echo "Logging into Azure ..."
# echo "Logging into Azure (without subscriptions)..."
echo "Just printing environment variables..."

echo "RESOURCE_GROUP=${RESOURCE_GROUP}"
echo "SERVICE_PRINCIPAL_APPID=${SERVICE_PRINCIPAL_APPID}"
echo "SERVICE_PRINCIPAL_PASSWORD=${SERVICE_PRINCIPAL_PASSWORD}"
echo "ENTRA_TENANT_ID=${ENTRA_TENANT_ID}"
echo "RECORD_NAME=${RECORD_NAME}"
echo "CONTAINER_GROUP_NAME=${CONTAINER_GROUP_NAME}"
echo "PRIVATE_ZONE_NAME=${PRIVATE_ZONE_NAME}"
echo "SUBSCRIPTION_ID=${SUBSCRIPTION_ID}"


az login --service-principal --username '****' --password '***' --tenant '****'
# az login --service-principal --username $SERVICE_PRINCIPAL_APPID --password $SERVICE_PRINCIPAL_PASSWORD --tenant $ENTRA_TENANT_ID
# az login --service-principal --username $SERVICE_PRINCIPAL_APPID --password $SERVICE_PRINCIPAL_PASSWORD --tenant $ENTRA_TENANT_ID --verbose --allow-no-subscriptions
# az login --identity

# TODO: Remove later!
echo "az login $?"

echo "Finding container group IP address..."
private_ip=$(az container show --name $CONTAINER_GROUP_NAME --resource-group $RESOURCE_GROUP --subscription $SUBSCRIPTION_ID --query 'ipAddress.ip' -o tsv) && echo $private_ip
echo "Deleting previous DNS record..."
az network private-dns record-set a delete --name $RECORD_NAME --zone-name $PRIVATE_ZONE_NAME --resource-group $RESOURCE_GROUP --subscription $SUBSCRIPTION_ID --yes
# TODO: Remove later!
echo "az network private-dns record-set a delete $?"

echo "Creating DNS record ..."
az network private-dns record-set a create --name $RECORD_NAME --zone-name $PRIVATE_ZONE_NAME --resource-group $RESOURCE_GROUP --subscription $SUBSCRIPTION_ID
# TODO: Remove later!
echo "az network private-dns record-set a create $?"

az network private-dns record-set a add-record --record-set-name $RECORD_NAME --zone-name $PRIVATE_ZONE_NAME --resource-group $RESOURCE_GROUP --subscription $SUBSCRIPTION_ID --ipv4-address $private_ip
# TODO: Remove later!
echo "az network private-dns record-set a add-record $?"
