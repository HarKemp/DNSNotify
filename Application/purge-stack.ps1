$stack = "dnsnotify"
$prefix = "dnsnotify_"
$extra  = @("grafana-data", "clickhouse-data", "nats-data" "mattermost-data" "mattermost-config-exchange" "postgres-data")   # add any other exact names

Write-Host "Removing stack $stack ..."
docker stack rm $stack
Start-Sleep -Seconds 5

$vols = docker volume ls --format "{{.Name}}" | Where-Object {
    $_ -like "$prefix*" -or $extra -contains $_
}

if ($vols) {
    Write-Host "Deleting volumes:`n$($vols -join "`n")"
    $vols | ForEach-Object { docker volume rm $_ }
} else {
    Write-Host "No matching volumes to delete."
}

Write-Host "Purge complete."