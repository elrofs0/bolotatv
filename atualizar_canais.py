import asyncio
import aiohttp
import json
import re

# Nova URL global estável do projeto IPTV-org (Agrupada por países)
M3U_URL = "https://iptv-org.github.io/iptv/index.country.m3u"

def mapear_categoria(grupo, nome):
    """Mapeia as tags originais do M3U para as categorias do seu HTML"""
    nome = nome.upper()
    grupo = grupo.upper() if grupo else ""
    
    if "NEWS" in grupo or "NOTI" in nome or "NOTÍCIAS" in nome:
        return "NOTICIAS"
    elif "MOVIES" in grupo or "SERIES" in grupo or "FILME" in nome or "SÉRIE" in nome:
        return "FILMES"
    elif "DOCUMENTARIES" in grupo or "SPORTS" in grupo or "DOC" in nome or "ESPORTE" in nome:
        return "DOCUMENTARIOS"
    else:
        return "TV ABERTA" # Padrão para canais gerais

async def processar_lista():
    print("[LOG] Iniciando download com cabeçalhos de navegador...")
    
    # Cabeçalho para simular um navegador real e evitar bloqueios (HTTP 403)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    async with aiohttp.ClientSession(headers=headers) as session:
        try:
            async with session.get(M3U_URL, timeout=20) as response:
                if response.status != 200:
                    print(f"[ERRO] Falha ao acessar. Status HTTP: {response.status}")
                    return
                conteudo = await response.text()
        except Exception as e:
            print(f"[ERRO] Falha na conexão de rede: {e}")
            return

    linhas = conteudo.splitlines()
    canais_processados = []
    canal_atual = {}
    dentro_do_brasil = False

    print("[LOG] Iniciando parsing e filtragem geo-localizada...")
    
    # Expressões regulares para varrer os metadados do M3U
    group_title_regex = re.compile(r'group-title="([^"]+)"')

    for linha in linhas:
        if linha.startswith("#EXTINF"):
            # O arquivo 'index.country.m3u' separa os países estritamente pelo group-title="Brazil"
            grupo_match = group_title_regex.search(linha)
            grupo = grupo_match.group(1) if grupo_match else ""
            
            if grupo.strip().lower() == "brazil":
                dentro_do_brasil = True
                nome = linha.split(",")[-1].strip() if "," in linha else "Canal Sem Nome"
                
                canal_atual = {
                    "nome": nome,
                    "categoria": mapear_categoria(grupo, nome)
                }
            else:
                dentro_do_brasil = False
                canal_atual = {}
                
        elif linha.startswith("http"):
            # Se a linha de mídia pertence a um canal do Brasil filtrado acima, armazena a URL
            if dentro_do_brasil and canal_atual:
                canal_atual["url"] = linha.strip()
                canais_processados.append(canal_atual)
                canal_atual = {}
                dentro_do_brasil = False

    print(f"[LOG] Filtragem concluída. {len(canais_processados)} canais brasileiros encontrados.")

    # Se falhar e retornar zero por segurança, mantém dados antigos para não quebrar a interface
    if len(canais_processados) == 0:
        print("[AVISO] Nenhum canal processado. Abortando escrita para não zerar o JSON.")
        return

    # Grava os dados estruturados no formato correto
    with open("canais.json", "w", encoding="utf-8") as f:
        json.dump(canais_processados, f, ensure_ascii=False, indent=2)
    
    print("[LOG] Sucesso! O arquivo canais.json foi atualizado.")

if __name__ == "__main__":
    asyncio.run(processar_lista())
