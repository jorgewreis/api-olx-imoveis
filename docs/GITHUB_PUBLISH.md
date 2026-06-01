# Publicar no GitHub

O repositório local já está inicializado com commit em `main`. Para criar o remoto público e enviar o código:

## 1. Autenticar no GitHub CLI

```powershell
gh auth login --hostname github.com --git-protocol https --web --skip-ssh-key
```

Siga o código exibido em https://github.com/login/device se o navegador não abrir automaticamente.

Verifique:

```powershell
gh auth status
```

## 2. Publicar (automático)

```powershell
cd api-olx-imoveis
.\scripts\publish-github.ps1
```

O script cria `https://github.com/<seu-usuario>/api-olx-imoveis`, define topics e faz `git push`.

## 3. Release opcional (.exe)

Com Python 3.10+ instalado:

```powershell
.\build_exe.bat
gh release create v1.0.0 dist/OlxImoveis.exe --title "v1.0.0" --notes "Primeira versao desktop para Windows."
```

## Atualizar README com seu usuário

Após o push, confira se os links em `README.md` apontam para o seu usuário GitHub (substitua `jwmenezes` se necessário).
