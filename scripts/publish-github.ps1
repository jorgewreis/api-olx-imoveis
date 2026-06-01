# Publica o repositorio api-olx-imoveis no GitHub (requer: gh auth login)
$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)

$env:Path = [System.Environment]::GetEnvironmentVariable("Path", "User") + ";" +
    [System.Environment]::GetEnvironmentVariable("Path", "Machine")

if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
    Write-Error "GitHub CLI (gh) nao encontrado. Instale: winget install GitHub.cli --scope user"
}

$null = gh auth status 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "Faca login no GitHub (abrira o navegador ou codigo em https://github.com/login/device):"
    gh auth login --hostname github.com --git-protocol https --web --skip-ssh-key
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Login no GitHub nao concluido. Execute: gh auth login"
    }
}

$user = gh api user -q .login
Write-Host "Usuario GitHub: $user"

$exists = gh repo view "$user/api-olx-imoveis" 2>$null
if ($LASTEXITCODE -eq 0) {
    Write-Host "Repositorio ja existe. Configurando remote e enviando..."
    git remote remove origin 2>$null
    git remote add origin "https://github.com/$user/api-olx-imoveis.git"
    git push -u origin main
} else {
    gh repo create api-olx-imoveis `
        --public `
        --source=. `
        --remote=origin `
        --description "Desktop app para busca de imoveis na OLX Brasil (nao oficial)" `
        --push
}

gh repo edit --description "Desktop app para busca de imoveis na OLX Brasil (nao oficial)" `
    --add-topic python --add-topic olx --add-topic imoveis --add-topic real-estate `
    --add-topic desktop-app --add-topic customtkinter --add-topic brazil --add-topic web-scraping

Write-Host ""
Write-Host "Repositorio publico: https://github.com/$user/api-olx-imoveis"
