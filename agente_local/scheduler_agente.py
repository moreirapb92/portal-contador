# -*- coding: utf-8 -*-

import subprocess
import sys
from pathlib import Path


NOME_TAREFA = "AgenteXMLPortalContador"


def esta_em_exe():
    return getattr(sys, "frozen", False)


def pasta_app():
    """
    DEV:
      C:/Users/NONATO/Documents/portalcontador

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

    return Path(__file__).resolve().parent.parent


def pasta_agente_dev():
    return Path(__file__).resolve().parent


def caminho_python_dev():
    base = pasta_app()

    python_venv = base / ".venv" / "Scripts" / "python.exe"
    if python_venv.exists():
        return str(python_venv)

    python_venv2 = base / "venv" / "Scripts" / "python.exe"
    if python_venv2.exists():
        return str(python_venv2)

    return sys.executable


def caminho_logs():
    logs = pasta_app() / "logs"
    logs.mkdir(exist_ok=True)
    return logs


def caminho_agente():
    """
    Mantive esse nome porque o app_agente.py usa essa função.
    Agora ela aponta para a pasta principal do aplicativo.
    """
    return pasta_app()


def criar_arquivo_bat():
    base = pasta_app()
    logs = caminho_logs()

    bat_path = base / "run_agente_xml.bat"
    log_path = logs / "agendador_agente.log"

    runner_exe = base / "AgenteXMLRunner" / "AgenteXMLRunner.exe"

    if runner_exe.exists():
        comando_execucao = f'"{runner_exe}"'
    else:
        python_exe = caminho_python_dev()
        script = base / "agente_local" / "enviar_xmls.py"

        if not script.exists():
            script = pasta_agente_dev() / "enviar_xmls.py"

        comando_execucao = f'"{python_exe}" "{script}"'

    conteudo = f'''@echo off
cd /d "{base}"

if not exist "logs" mkdir "logs"

echo ================================================ >> "{log_path}"
echo Iniciando envio agendado em %date% %time% >> "{log_path}"
echo ================================================ >> "{log_path}"

{comando_execucao} >> "{log_path}" 2>&1

echo ================================================ >> "{log_path}"
echo Envio agendado finalizado em %date% %time% >> "{log_path}"
echo ================================================ >> "{log_path}"
echo. >> "{log_path}"
'''

    with open(bat_path, "w", encoding="utf-8") as arquivo:
        arquivo.write(conteudo)

    return str(bat_path)


def criar_tarefa_diaria(horario="23:00"):
    bat_path = criar_arquivo_bat()

    comando = [
        "schtasks",
        "/create",
        "/tn", NOME_TAREFA,
        "/tr", f'"{bat_path}"',
        "/sc", "daily",
        "/st", horario,
        "/f"
    ]

    processo = subprocess.run(
        comando,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        shell=False
    )

    return processo.returncode, processo.stdout


def remover_tarefa():
    comando = [
        "schtasks",
        "/delete",
        "/tn", NOME_TAREFA,
        "/f"
    ]

    processo = subprocess.run(
        comando,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        shell=False
    )

    return processo.returncode, processo.stdout


def executar_tarefa_agora():
    comando = [
        "schtasks",
        "/run",
        "/tn", NOME_TAREFA
    ]

    processo = subprocess.run(
        comando,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        shell=False
    )

    return processo.returncode, processo.stdout


def consultar_tarefa():
    comando = [
        "schtasks",
        "/query",
        "/tn", NOME_TAREFA,
        "/fo", "LIST",
        "/v"
    ]

    processo = subprocess.run(
        comando,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace"
    )

    return processo.returncode, processo.stdout


if __name__ == "__main__":
    print("Agendador - Agente XML Portal do Contador")
    print("1 - Criar tarefa diária")
    print("2 - Remover tarefa")
    print("3 - Executar tarefa agora")
    print("4 - Consultar tarefa")
    print("5 - Criar apenas BAT")
    opcao = input("Escolha: ").strip()

    if opcao == "1":
        horario = input("Horário diário, exemplo 23:00: ").strip() or "23:00"
        codigo, saida = criar_tarefa_diaria(horario)
        print(saida)

    elif opcao == "2":
        codigo, saida = remover_tarefa()
        print(saida)

    elif opcao == "3":
        codigo, saida = executar_tarefa_agora()
        print(saida)

    elif opcao == "4":
        codigo, saida = consultar_tarefa()
        print(saida)

    elif opcao == "5":
        bat = criar_arquivo_bat()
        print("BAT criado:")
        print(bat)

    else:
        print("Opção inválida.")