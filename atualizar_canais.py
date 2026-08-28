import asyncio
import aiohttp
import json
import re

# URL da lista pública focada em canais do Brasil (IPTV-org)
M3U_URL = "https://github.io"

def mapear_categoria(grupo, nome):
    """Mapeia o grupo original do M3U para as categorias do seu HTML"""
    nome = nome.upper()
    grupo = grupo.upper() if grupo else ""
    
    if "NEWS" in grupo or "NOTI" in nome or "NOTÍCIAS" in nome:
        return "NOTICIAS"
    elif "MOVIES" in grupo or "SERIES" in grupo or "FILME" in nome or "SÉRIE" in nome:
        return "FILMES"
    elif "DOCUMENTARIES" in grupo or "SPORTS" in grupo or "DOC" in nome or "ESPORTE" in nome:
        return "DOCUMENTARIOS"
    else:
        return "TV ABERTA" # Padrão para canais gerais do Brasil

async def processar_lista():
    print("[LOG] Iniciando download da lista IPTV-org...")
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(M3U_URL, timeout=15) as response:
                if response.status != 200:
                    print(f"[ERRO] Falha ao baixar lista. Status: {response.status}")
                    return
                
                conteudo = await response.text()
        except Exception as e:
            print(f"[ERRO] Erro na requisição: {e}")
            return

    linhas = conteudo.splitlines()
    canais_processados = []
    canal_atual = {}

    print("[LOG] Fazendo o parsing das strings do M3U...")
    # Expressões regulares para capturar metadados do padrão M3U
    tvg_name_regex = re.compile(r'tvg-name="([^"]+)"')
    group_title_regex = re.compile(r'group-title="([^"]+)"')

    for linha in linhas:
        if linha.startswith("#EXTINF"):
            # Extrai o nome amigável do canal (texto após a última vírgula)
            nome = linha.split(",")[-1].strip() if "," in linha else "Canal Sem Nome"
            
            # Extrai o grupo/categoria original se existir
            grupo_match = group_title_regex.search(linha)
            grupo = grupo_match.group(1) if grupo_match else ""
            
            # Se não achar o nome no final, tenta pegar o tvg-name
            if not nome or nome == "Canal Sem Nome":
                name_match = tvg_name_regex.search(linha)
                nome = name_match.group(1) if name_match else "Canal Anonimo"

            canal_atual = {
                "nome": nome,
                "categoria": mapear_categoria(grupo, nome)
            }
        elif linha.startswith("http"):
            # Se a linha anterior configurou um canal, adiciona a URL correspondente
            if canal_atual:
                canal_atual["url"] = linha.strip()
                canais_processados.append(canal_atual)
                canal_atual = {}

    print(f"[LOG] Filtragem concluída. {len(canais_processados)} canais processados.")

    # Grava os dados estruturados diretamente no canais.json do seu repositório
    with open("canais.json", "w", encoding="utf-8") as f:
        json.dump(canais_processados, f, ensure_ascii=False, indent=2)
    
    print("[LOG] Arquivo canais.json atualizado com sucesso!")

if __name__ == "__main__":
    asyncio.run(processar_lista())
