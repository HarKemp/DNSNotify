Get-Content .env | ForEach-Object {
    if ($_ -match '^\s*#' -or $_.Trim() -eq '') { return }   # skip comments
    $parts = $_ -split '=', 2
    [System.Environment]::SetEnvironmentVariable($parts[0], $parts[1])
}

docker compose -f prod.yml build `
    ml-model `
    mattermost `
    notification-service `
    test-client

docker stack deploy -c prod.yml dnsnotify