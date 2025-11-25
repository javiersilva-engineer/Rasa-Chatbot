Get-Content .env | ForEach-Object {
    if ($_ -match '^([^=]+)=(.*)$') {
        $name = $matches[1]
        $value = $matches[2]
        [Environment]::SetEnvironmentVariable($name, $value, "Process")
        Write-Host "Variable cargada: $name"
    }
}

#PARA EJECUTAR .env EN POWERSHELL: .\load_env.ps1