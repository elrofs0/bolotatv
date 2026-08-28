import asyncio
import aiohttp
import json
import re

# URL da lista focada em canais abertos e streams FAST estáveis do Brasil
M3U_URL = "https://github.io"

def mapear_categoria(grupo, nome):
    nome = nome.upper()
    grupo = grupo.upper() if grupo else ""
    if "NEWS" in grupo or "NOTI" in nome:
        return "NOTICIAS"
    elif "MOVIES" in grupo or "SERIES" in grupo or "FILME" in nome:
        return "FILMES"
    elif "DOCUMENTARIES" in grupo or "SPORTS" in grupo or "DOC" in nome or "ESPORTE" in nome:
        return "DOCUMENTARIOS"
    else:
        return "TV ABERTA"

async def processar_lista():
    print("[LOG] Iniciando varredura de canais estáveis...")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    async with aiohttp.ClientSession(headers=headers) as session:
        try:
            async with session.get(M3U_URL, timeout=20) as response:
                if response.status != 200: return
                conteudo = await response.text()
        except Exception:
            return

    linhas = conteudo.splitlines()
    canais_processados = []
    canal_atual = {}
    dentro_do_brasil = False

    group_title_regex = re.compile(r'group-title="([^"]+)"')

    for linha in linhas:
        if linha.startswith("#EXTINF"):
            grupo_match = group_title_regex.search(linha)
            grupo = grupo_match.group(1) if grupo_match else ""
            
            if grupo.strip().lower() == "brazil":
                dentro_do_brasil = True
                nome = linha.split(",")[-1].strip()
                
                # FILTRAGEM DE SEGURANÇA: Só aceita canais oficiais estáveis (Pluto, Samsung, Cultura, Record, etc.)
                # Evita servidores caseiros (.ts ou IPs numéricos que morrem em 24h)
                if any(x in nome.upper() for x in ["PLUTO", "SAMSUNG", "CULTURA", "RECORD", "SOUL", "SBT", "BAND"]):
                    canal_atual = {
                        "nome": nome,
                        "categoria": mapear_categoria(grupo, nome)
                    }
                else:
                    dentro_do_brasil = False
            else:
                dentro_do_brasil = False
                
        elif linha.startswith("http"):
            if dentro_do_brasil and canal_atual:
                url_limpa = linha.strip()
                # Só aceita links HTTPS padrão para não dar erro de segurança no navegador
                if url_limpa.startswith("https"):
                    canal_atual["url"] = url_limpa
                    canais_processados.append(canal_atual)
                canal_atual = {}
                dentro_do_brasil = False

    if len(canais_processados) == 0:
        return

    with open("canais.json", "w", encoding="utf-8") as f:
        json.dump(canais_processados, f, ensure_ascii=False, indent=2)
    print(f"[LOG] Sucesso! {len(canais_processados)} canais estáveis indexados.")

if __name__ == "__main__":
    asyncio.run(processar_lista())
