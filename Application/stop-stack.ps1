$stack = "dnsnotify"

Write-Host "Removing stack $stack ..."
docker stack rm $stack

Write-Host "Waiting for removal to finish ..."
Start-Sleep -Seconds 5
while (docker stack ls | Select-String -Pattern $stack) {
    Start-Sleep -Seconds 2
}

Write-Host "Stack removed."