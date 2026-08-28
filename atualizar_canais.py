"""
BOLOTA TV — Atualizador automático de canais
Fonte: iptv-org/iptv (streams/br.m3u), a maior lista pública e ativamente
mantida de canais IPTV do Brasil.

O que este script garante:
- Só entram canais HTTPS (canais http:// são bloqueados pelo navegador
  quando o site roda em https, como no GitHub Pages — "mixed content").
- Canais marcados [Geo-blocked] são descartados (não funcionam pra maioria).
- Sem duplicados: mantém apenas a primeira URL válida de cada canal.
- Categorização automática por palavras-chave no nome/tvg-id.
- Se a fonte falhar ou vier vazia, o canais.json atual NÃO é sobrescrito
  (evita zerar a lista do site por uma falha temporária de rede).
"""

import asyncio
import aiohttp
import json
import re
from collections import OrderedDict

M3U_URL = "https://raw.githubusercontent.com/iptv-org/iptv/master/streams/br.m3u"

CATEGORIAS = [
    ("NOTICIAS", ["NEWS", "NOTIC", "JORNAL", "CNN", "TIMES BRASIL", "BM&C", "J3NEWS"]),
    ("ESPORTES", ["SPORT", "ESPN", "SPORTV", "PREMIERE", "COMBATE", "N SPORTS", "CAZETV", "CAZE TV"]),
    ("FILMES", ["MOVIE", "FILME", "CINE", "TELECINE", "MEGAPIX", "TCM"]),
    ("SERIES", ["SERIES", "SÉRIE", "AXN", "SONY", "WARNER", "FX", "AMC", "TRUTV", "COMEDY CENTRAL"]),
    ("INFANTIL", ["KIDS", "GLOOB", "DISCOVERY KIDS", "NICK", "CARTOON", "DISNEY", "ZOOMOO", "DUMDUM", "BOX KIDS", "BABYFIRST", "RA TIM BUM"]),
    ("DOCUMENTARIOS", ["DISCOVERY", "HISTORY", "NATGEO", "NATIONAL GEO", "CURTA", "TRAVEL BOX", "TERRA VIVA", "AGRO", "FISH TV", "PETLOVERS", "BIS", "CANAL SAUDE", "CANAL SAÚDE"]),
    ("RELIGIAO", ["GOSPEL", "EVANGELIZAR", "CANCAO NOVA", "CANÇÃO NOVA", "NOVO TEMPO", "REDE VIDA", "BOAS NOVAS", "APARECIDA", "GIDEOES", "ADORAR"]),
    ("GOV_EDUCACAO", ["SENADO", "CAMARA", "CÂMARA", "JUSTICA", "JUSTIÇA", "TV ESCOLA", "TV CULTURA", "UFG", "UFOP", "CANAL GOV", "CANAL EDUCACAO", "CANAL EDUCAÇÃO", "CANAL LIBRAS"]),
]

# Linhas #EXTINF podem ter qualquer número de atributos tvg-* antes da vírgula + nome
EXTINF_RE = re.compile(r'#EXTINF:-?\d+(?P<attrs>(?:\s+[\w-]+="[^"]*")*)\s*,(?P<nome>.+)$')
TVGID_RE = re.compile(r'tvg-id="([^"]*)"')


def mapear_categoria(nome: str, tvg_id: str = "") -> str:
    alvo = f"{nome} {tvg_id}".upper()
    for categoria, chaves in CATEGORIAS:
        if any(chave in alvo for chave in chaves):
            return categoria
    return "TV ABERTA"


async def buscar_m3u() -> str:
    headers = {"User-Agent": "Mozilla/5.0 (compatible; BolotaTV/1.0)"}
    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.get(M3U_URL, timeout=aiohttp.ClientTimeout(total=30)) as resp:
            resp.raise_for_status()
            return await resp.text()


def processar(conteudo: str) -> list[dict]:
    linhas = [l.strip() for l in conteudo.splitlines() if l.strip()]
    canais: "OrderedDict[str, dict]" = OrderedDict()
    nome_atual = None
    tvgid_atual = ""

    for linha in linhas:
        if linha.startswith("#EXTINF"):
            m = EXTINF_RE.match(linha)
            if not m:
                nome_atual = None
                continue
            nome_atual = m.group("nome").strip()
            tvgid_m = TVGID_RE.search(m.group("attrs"))
            tvgid_atual = tvgid_m.group(1) if tvgid_m else ""
        elif linha.startswith("#"):
            # Ex: #EXTVLCOPT, #EXTGRP — ignora mas preserva o canal atual
            continue
        elif linha.startswith("http") and nome_atual:
            eh_geo_bloqueado = "GEO-BLOCKED" in nome_atual.upper()
            eh_https = linha.startswith("https")
            if eh_https and not eh_geo_bloqueado and nome_atual not in canais:
                canais[nome_atual] = {
                    "nome": nome_atual,
                    "categoria": mapear_categoria(nome_atual, tvgid_atual),
                    "url": linha,
                }
            nome_atual = None  # essa entrada já foi consumida

    return list(canais.values())


async def main():
    print("[LOG] Baixando lista atualizada de canais (iptv-org/br.m3u)...")
    try:
        conteudo = await buscar_m3u()
    except Exception as e:
        print(f"[ERRO] Falha ao baixar a lista: {e}. Mantendo canais.json atual.")
        return

    canais = processar(conteudo)

    if len(canais) < 50:
        # Fonte provavelmente veio corrompida/incompleta — não sobrescreve o site
        print(f"[ERRO] Só {len(canais)} canais processados (esperado bem mais). Abortando sem sobrescrever.")
        return

    canais.sort(key=lambda c: (c["categoria"], c["nome"]))

    with open("canais.json", "w", encoding="utf-8") as f:
        json.dump(canais, f, ensure_ascii=False, indent=2)

    print(f"[LOG] Sucesso: {len(canais)} canais únicos, HTTPS, sem geo-bloqueio, salvos em canais.json.")


if __name__ == "__main__":
    asyncio.run(main())
