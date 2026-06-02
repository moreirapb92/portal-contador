# -*- coding: utf-8 -*-

import json
import sys
import time
from datetime import datetime
from pathlib import Path

import requests


def esta_em_exe():
    return getattr(sys, "frozen", False)


def pasta_base():
    """
    Desenvolvimento:
      C:/Users/NONATO/Documents/portalcontador/agente_local

    EXE painel:
      dist/AgenteXMLPortalContador

    EXE runner:
      dist/AgenteXMLPortalContador/AgenteXMLRunner
      então volta uma pasta.
    """
    if esta_em_exe():
        pasta = Path(sys.executable).resolve().parent

        if pasta.name.lower() == "agentexmlrunner":
            return pasta.parent

        return pasta

    return Path(__file__).resolve().parent


BASE_DIR = pasta_base()
ARQUIVO_CONFIG = BASE_DIR / "config_agente.json"
ARQUIVO_HISTORICO = BASE_DIR / "historico_envio.json"
PASTA_LOGS = BASE_DIR / "logs"


def carregar_config():
    if not ARQUIVO_CONFIG.exists():
        raise FileNotFoundError(f"Arquivo config_agente.json não encontrado em: {ARQUIVO_CONFIG}")

    with open(ARQUIVO_CONFIG, "r", encoding="utf-8-sig") as arquivo:
        return json.load(arquivo)


def carregar_historico():
    if not ARQUIVO_HISTORICO.exists():
        return {}

    with open(ARQUIVO_HISTORICO, "r", encoding="utf-8-sig") as arquivo:
        return json.load(arquivo)


def salvar_historico(historico):
    with open(ARQUIVO_HISTORICO, "w", encoding="utf-8") as arquivo:
        json.dump(historico, arquivo, indent=4, ensure_ascii=False)


def log(mensagem):
    PASTA_LOGS.mkdir(exist_ok=True)

    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    linha = f"[{agora}] {mensagem}"

    print(linha)

    arquivo_log = PASTA_LOGS / f"envio_{datetime.now().strftime('%Y-%m-%d')}.log"

    with open(arquivo_log, "a", encoding="utf-8") as arquivo:
        arquivo.write(linha + "\n")


def deve_ignorar_arquivo(config, arquivo):
    nome = arquivo.name.lower()
    padroes = config.get("ignorar_arquivos_com", [])

    for padrao in padroes:
        if str(padrao).lower() in nome:
            return True

    return False


def listar_xmls(config):
    arquivos = []
    ignorados_tipo = 0

    extensoes = [e.lower() for e in config.get("extensoes", [".xml"])]
    enviar_subpastas = bool(config.get("enviar_subpastas", True))

    for pasta in config.get("pastas_xml", []):
        pasta_path = Path(pasta)

        if not pasta_path.exists():
            log(f"AVISO: pasta não encontrada: {pasta}")
            continue

        if enviar_subpastas:
            encontrados = pasta_path.rglob("*")
        else:
            encontrados = pasta_path.glob("*")

        for arquivo in encontrados:
            if not arquivo.is_file():
                continue

            if arquivo.suffix.lower() not in extensoes:
                continue

            if deve_ignorar_arquivo(config, arquivo):
                ignorados_tipo += 1
                continue

            arquivos.append(arquivo)

    arquivos = sorted(arquivos, key=lambda x: x.stat().st_mtime)

    return arquivos, ignorados_tipo


def chave_historico(arquivo):
    stat = arquivo.stat()
    return f"{arquivo.resolve()}|{stat.st_size}|{int(stat.st_mtime)}"


def enviar_arquivo(config, arquivo):
    api_url = config["api_url"]
    cnpj = config["cnpj"]
    token = config["token"]
    timeout = int(config.get("timeout", 60))

    with open(arquivo, "rb") as f:
        files = {
            "arquivo": (arquivo.name, f, "text/xml")
        }

        data = {
            "cnpj": cnpj,
            "token": token
        }

        resposta = requests.post(
            api_url,
            data=data,
            files=files,
            timeout=timeout
        )

    try:
        retorno = resposta.json()
    except Exception:
        retorno = {
            "sucesso": False,
            "erro": resposta.text
        }

    if resposta.status_code >= 400:
        erro = retorno.get("erro", resposta.text)
        raise Exception(f"HTTP {resposta.status_code}: {erro}")

    if not retorno.get("sucesso"):
        raise Exception(retorno.get("erro", "Erro desconhecido."))

    return retorno


def executar_envio():
    config = carregar_config()
    historico = carregar_historico()

    todos_arquivos, ignorados_por_tipo = listar_xmls(config)

    limite = int(config.get("limite_por_execucao", 0))

    arquivos_pendentes = []

    for arquivo in todos_arquivos:
        chave_local = chave_historico(arquivo)

        if chave_local not in historico:
            arquivos_pendentes.append(arquivo)

    if limite > 0:
        arquivos_para_enviar = arquivos_pendentes[:limite]
    else:
        arquivos_para_enviar = arquivos_pendentes

    total_encontrados_validos = len(todos_arquivos)
    total_pendentes = len(arquivos_pendentes)
    total_execucao = len(arquivos_para_enviar)

    enviados = 0
    ignorados_ja_enviados = total_encontrados_validos - total_pendentes
    erros = 0

    log("=" * 60)
    log("Iniciando envio de XMLs")
    log(f"BASE_DIR: {BASE_DIR}")
    log(f"Config usado: {ARQUIVO_CONFIG}")
    log(f"XMLs válidos encontrados: {total_encontrados_validos}")
    log(f"Ignorados por tipo de arquivo: {ignorados_por_tipo}")
    log(f"Já enviados anteriormente: {ignorados_ja_enviados}")
    log(f"Pendentes para envio: {total_pendentes}")

    if limite > 0:
        log(f"Limite por execução: {limite}")

    log(f"Serão enviados agora: {total_execucao}")

    if total_execucao == 0:
        log("Nenhum XML novo para enviar.")
        log("=" * 60)

        return {
            "total": total_encontrados_validos,
            "pendentes": total_pendentes,
            "enviados": enviados,
            "ignorados": ignorados_ja_enviados,
            "ignorados_tipo": ignorados_por_tipo,
            "erros": erros
        }

    for arquivo in arquivos_para_enviar:
        chave_local = chave_historico(arquivo)

        try:
            log(f"Enviando: {arquivo}")

            retorno = enviar_arquivo(config, arquivo)

            historico[chave_local] = {
                "arquivo": str(arquivo),
                "enviado_em": datetime.now().isoformat(),
                "chave_acesso": retorno.get("chave_acesso", ""),
                "numero": retorno.get("numero", ""),
                "serie": retorno.get("serie", ""),
                "tipo_documento": retorno.get("tipo_documento", ""),
                "criado": retorno.get("criado", False),
                "mensagem": retorno.get("mensagem", "")
            }

            salvar_historico(historico)

            enviados += 1

            log(
                f"OK: {retorno.get('tipo_documento')} "
                f"Nº {retorno.get('numero')} "
                f"Chave {retorno.get('chave_acesso')}"
            )

            time.sleep(0.1)

        except KeyboardInterrupt:
            log("Envio cancelado pelo usuário.")
            break

        except Exception as erro:
            erros += 1
            log(f"ERRO ao enviar {arquivo}: {erro}")

    log("-" * 60)
    log("Finalizado.")
    log(f"XMLs válidos encontrados: {total_encontrados_validos}")
    log(f"Ignorados por tipo de arquivo: {ignorados_por_tipo}")
    log(f"Pendentes antes da execução: {total_pendentes}")
    log(f"Enviados agora: {enviados}")
    log(f"Ignorados já enviados: {ignorados_ja_enviados}")
    log(f"Erros: {erros}")
    log("=" * 60)

    return {
        "total": total_encontrados_validos,
        "pendentes": total_pendentes,
        "enviados": enviados,
        "ignorados": ignorados_ja_enviados,
        "ignorados_tipo": ignorados_por_tipo,
        "erros": erros
    }


if __name__ == "__main__":
    try:
        resultado = executar_envio()

        print("")
        print("PROCESSO FINALIZADO")
        print("XMLs válidos encontrados:", resultado["total"])
        print("Pendentes:", resultado["pendentes"])
        print("Enviados:", resultado["enviados"])
        print("Ignorados já enviados:", resultado["ignorados"])
        print("Ignorados por tipo:", resultado["ignorados_tipo"])
        print("Erros:", resultado["erros"])

    except KeyboardInterrupt:
        print("")
        print("PROCESSO CANCELADO PELO USUÁRIO")

    except Exception as erro:
        print("ERRO GERAL:", erro)