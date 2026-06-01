# Engenharia reversa — busca pública OLX Imóveis

## API oficial (não usada para busca pública)

A [documentação de integração](https://developers.olx.com.br/anuncio/home.html) cobre publicação/gestão do inventário do anunciante (`autoupload`), não listagem do marketplace.

## Site público (`*.olx.com.br`)

### URL de listagem

Padrão base:

```
https://{uf}.olx.com.br/{regiao}/imoveis/{oferta}/{tipo}?{query}
```

| Segmento | Exemplos |
|----------|----------|
| `uf` | `sp`, `rj`, `mg` (subdomínio) |
| `regiao` | `estado-sp`, `sao-paulo-e-regiao`, `rio-de-janeiro-e-regiao` |
| `oferta` | `venda`, `aluguel` |
| `tipo` | `apartamentos`, `casas`, `terrenos`, `comercio-e-industria`, `temporada` |
| `bairro` (opcional) | segmento extra antes de `imoveis`, ex. `zona-sul` |

### Query params (filtros)

| Param | Significado |
|-------|-------------|
| `ps` | Preço mínimo (R$) |
| `pe` | Preço máximo (R$) |
| `se` | Quartos mínimo |
| `ss` | Quartos máximo |
| `bae` | Banheiros mínimo |
| `bas` | Banheiros máximo |
| `gsp` | Vagas de garagem mínimo |
| `q` | Termo de busca livre |
| `o` | Ordenação (`1` relevância, preço, data — varia por categoria) |

Referência comunitária: [olx-monitor](https://github.com/carmolim/olx-monitor).

### Paginação

- Parâmetro `page` na query string para páginas seguintes.
- Alternativa: link `rel=next` no HTML ou campo `nextPage` no JSON embutido.

### Extração de dados

O site é Next.js. O HTML contém:

```html
<script id="__NEXT_DATA__" type="application/json">...</script>
```

Caminhos JSON comuns na listagem (variam por deploy):

- `props.pageProps.ads`
- `props.pageProps.searchResults.ads`
- `props.pageProps.initialData.ads`

Campos típicos por anúncio na listagem:

- `listId`, `title`, `price`, `priceValue`
- `friendlyUrl` / `url`
- `location` → `municipality`, `neighbourhood`, `uf`
- `images[]` → `original`, `url`

### Página de detalhe

URL: `https://{uf}.olx.com.br/vi/{listId}.htm` ou URL amigável retornada na listagem.

Caminhos JSON comuns:

- `props.pageProps.ad`
- `props.pageProps.adDetail`

Campos úteis:

- `body` / `description` — descrição completa
- `parameters` / `properties` — quartos, área, condomínio
- `user` / `seller` — nome, `publicAccountId`, `isProfessional`
- `phone` / `phones` / `contact` — telefone quando exposto no payload

**Telefone:** nem sempre vem no `__NEXT_DATA__`; o app tenta extrair e oferece “Abrir na OLX” como fallback. Não persistir telefone além de 24h (LGPD).

### Política de acesso

- User-Agent: `OlxImoveisDesktop/1.0`
- Intervalo mínimo entre requisições: ~1s
- Cache local de listagens: 10 minutos
