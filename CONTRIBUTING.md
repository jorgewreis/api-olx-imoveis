# Como contribuir

Obrigado pelo interesse em melhorar o **OLX Imóveis Desktop**.

## Antes de começar

- Este projeto **não é oficial** da OLX. Não envie PRs que aumentem agressivamente o volume de requisições ao site ou contornem proteções.
- Respeite a [LGPD](https://www.gov.br/anpd/pt-br) e os [Termos de Uso da OLX](https://ajuda.olx.com.br/).
- Não inclua dados pessoais reais (telefones, nomes de anunciantes) em fixtures ou commits.

## Ambiente de desenvolvimento

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install -e ".[dev]"
$env:PYTHONPATH = "src"
pytest tests/ -v
```

## Padrão de Pull Request

1. Descreva o problema ou a melhoria na Issue (ou referencie uma existente).
2. Mantenha o escopo focado — uma correção ou feature por PR.
3. Adicione ou atualize testes em `tests/` quando alterar parsers ou `url_builder`.
4. Execute `pytest` localmente antes de abrir o PR.
5. Atualize o `README.md` se mudar comportamento visível ao usuário.

## Parsers e mudanças no site OLX

Se a OLX alterar o HTML/JSON:

1. Salve um trecho anonimizado em `tests/fixtures/` (sem dados pessoais).
2. Ajuste `src/olx_imoveis/parsers/`.
3. Documente em `docs/olx_reverse_engineering.md` se novos parâmetros de URL forem descobertos.

## Código de conduta

Seja respeitoso em Issues e revisões. Comportamento inadequado pode resultar em bloqueio do repositório.
