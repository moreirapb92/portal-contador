# -*- coding: utf-8 -*-

import contextlib
import io
import json
import subprocess
import threading
from pathlib import Path
from tkinter import filedialog, messagebox

import requests
import ttkbootstrap as tb
from ttkbootstrap.constants import *

from enviar_xmls import executar_envio, ARQUIVO_CONFIG, PASTA_LOGS
from scheduler_agente import (
    criar_tarefa_diaria,
    remover_tarefa,
    executar_tarefa_agora,
    consultar_tarefa,
    caminho_agente,
)


class AgenteXMLApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Agente XML - Portal do Contador")
        self.root.geometry("1020x720")
        self.root.minsize(940, 650)

        self.config = self.carregar_config()

        self.var_api = tb.StringVar(value=self.config.get("api_url", ""))
        self.var_cnpj = tb.StringVar(value=self.config.get("cnpj", ""))
        self.var_token = tb.StringVar(value=self.config.get("token", ""))
        self.var_limite = tb.StringVar(value=str(self.config.get("limite_por_execucao", 20)))
        self.var_subpastas = tb.BooleanVar(value=bool(self.config.get("enviar_subpastas", True)))
        self.var_horario = tb.StringVar(value="23:00")

        self.montar_interface()

    def carregar_config(self):
        if not ARQUIVO_CONFIG.exists():
            return {
                "api_url": "http://127.0.0.1:8000/api/upload-xml/",
                "cnpj": "",
                "token": "",
                "pastas_xml": [],
                "enviar_subpastas": True,
                "extensoes": [".xml"],
                "timeout": 60,
                "limite_por_execucao": 20,
                "ignorar_arquivos_com": [
                    "procInutNFe",
                    "procEventoNFe",
                    "evento",
                    "retInutNFe"
                ]
            }

        with open(ARQUIVO_CONFIG, "r", encoding="utf-8-sig") as arquivo:
            return json.load(arquivo)

    def gerar_config_atual(self):
        pastas = []

        texto_pastas = self.txt_pastas.get("1.0", "end").strip()
        for linha in texto_pastas.splitlines():
            linha = linha.strip()
            if linha:
                pastas.append(linha)

        try:
            limite = int(self.var_limite.get() or 20)
        except Exception:
            limite = 20

        return {
            "api_url": self.var_api.get().strip(),
            "cnpj": self.var_cnpj.get().strip(),
            "token": self.var_token.get().strip(),
            "pastas_xml": pastas,
            "enviar_subpastas": bool(self.var_subpastas.get()),
            "extensoes": [".xml"],
            "timeout": 60,
            "limite_por_execucao": limite,
            "ignorar_arquivos_com": [
                "procInutNFe",
                "procEventoNFe",
                "evento",
                "retInutNFe"
            ]
        }

    def salvar_config(self, silencioso=False):
        config = self.gerar_config_atual()

        with open(ARQUIVO_CONFIG, "w", encoding="utf-8") as arquivo:
            json.dump(config, arquivo, indent=4, ensure_ascii=False)

        self.config = config

        if not silencioso:
            messagebox.showinfo("Configuração", "Configuração salva com sucesso.")

    def montar_interface(self):
        container = tb.Frame(self.root, padding=15)
        container.pack(fill=BOTH, expand=True)

        titulo = tb.Label(
            container,
            text="Agente XML - Portal do Contador",
            font=("Segoe UI", 22, "bold")
        )
        titulo.pack(anchor=W)

        subtitulo = tb.Label(
            container,
            text="Envia XMLs de NF-e/NFC-e automaticamente para o portal.",
            bootstyle="secondary"
        )
        subtitulo.pack(anchor=W, pady=(0, 15))

        self.notebook = tb.Notebook(container)
        self.notebook.pack(fill=BOTH, expand=True)

        self.aba_envio = tb.Frame(self.notebook, padding=15)
        self.aba_config = tb.Frame(self.notebook, padding=15)
        self.aba_agendamento = tb.Frame(self.notebook, padding=15)
        self.aba_logs = tb.Frame(self.notebook, padding=15)

        self.notebook.add(self.aba_envio, text="Envio")
        self.notebook.add(self.aba_config, text="Configurações")
        self.notebook.add(self.aba_agendamento, text="Agendamento")
        self.notebook.add(self.aba_logs, text="Logs")

        self.montar_aba_envio()
        self.montar_aba_config()
        self.montar_aba_agendamento()
        self.montar_aba_logs()

    def montar_aba_envio(self):
        botoes = tb.Frame(self.aba_envio)
        botoes.pack(fill=X)

        tb.Button(
            botoes,
            text="Enviar XMLs agora",
            bootstyle=SUCCESS,
            command=self.enviar_thread
        ).pack(side=LEFT, padx=(0, 8))

        tb.Button(
            botoes,
            text="Testar conexão com portal",
            bootstyle=PRIMARY,
            command=self.testar_conexao_thread
        ).pack(side=LEFT, padx=8)

        tb.Button(
            botoes,
            text="Abrir pasta de logs",
            bootstyle=SECONDARY,
            command=self.abrir_pasta_logs
        ).pack(side=LEFT, padx=8)

        status = tb.Labelframe(self.aba_envio, text="Status", padding=10)
        status.pack(fill=X, pady=15)

        self.lbl_status = tb.Label(status, text="Aguardando ação...", font=("Segoe UI", 11, "bold"))
        self.lbl_status.pack(anchor=W)

        log_frame = tb.Labelframe(self.aba_envio, text="Log da execução", padding=10)
        log_frame.pack(fill=BOTH, expand=True)

        self.txt_log = tb.Text(log_frame, height=22, wrap="word")
        self.txt_log.pack(fill=BOTH, expand=True)

    def montar_aba_config(self):
        form = tb.Labelframe(self.aba_config, text="Dados de conexão", padding=12)
        form.pack(fill=X)

        tb.Label(form, text="URL da API:").grid(row=0, column=0, sticky=W, pady=5)
        tb.Entry(form, textvariable=self.var_api, width=80).grid(row=0, column=1, sticky=W, pady=5)

        tb.Label(form, text="CNPJ da empresa:").grid(row=1, column=0, sticky=W, pady=5)
        tb.Entry(form, textvariable=self.var_cnpj, width=30).grid(row=1, column=1, sticky=W, pady=5)

        tb.Label(form, text="Token da empresa:").grid(row=2, column=0, sticky=W, pady=5)
        tb.Entry(form, textvariable=self.var_token, width=80, show="*").grid(row=2, column=1, sticky=W, pady=5)

        tb.Label(form, text="Limite por execução:").grid(row=3, column=0, sticky=W, pady=5)
        tb.Entry(form, textvariable=self.var_limite, width=12).grid(row=3, column=1, sticky=W, pady=5)

        tb.Checkbutton(
            form,
            text="Enviar XMLs também de subpastas",
            variable=self.var_subpastas,
            bootstyle="round-toggle"
        ).grid(row=4, column=1, sticky=W, pady=5)

        pastas_frame = tb.Labelframe(self.aba_config, text="Pastas de XML", padding=12)
        pastas_frame.pack(fill=BOTH, expand=True, pady=15)

        self.txt_pastas = tb.Text(pastas_frame, height=8, wrap="word")
        self.txt_pastas.pack(fill=BOTH, expand=True)

        for pasta in self.config.get("pastas_xml", []):
            self.txt_pastas.insert("end", pasta + "\n")

        botoes = tb.Frame(self.aba_config)
        botoes.pack(fill=X)

        tb.Button(
            botoes,
            text="Adicionar pasta",
            bootstyle=INFO,
            command=self.adicionar_pasta
        ).pack(side=LEFT, padx=(0, 8))

        tb.Button(
            botoes,
            text="Salvar configurações",
            bootstyle=SUCCESS,
            command=lambda: self.salvar_config(silencioso=False)
        ).pack(side=LEFT, padx=8)

        tb.Button(
            botoes,
            text="Abrir config JSON",
            bootstyle=SECONDARY,
            command=self.abrir_config_json
        ).pack(side=LEFT, padx=8)

    def montar_aba_agendamento(self):
        box = tb.Labelframe(self.aba_agendamento, text="Envio automático diário", padding=12)
        box.pack(fill=X)

        linha = tb.Frame(box)
        linha.pack(fill=X, pady=5)

        tb.Label(linha, text="Horário diário:", width=18).pack(side=LEFT)

        tb.Entry(
            linha,
            textvariable=self.var_horario,
            width=10
        ).pack(side=LEFT, padx=(0, 10))

        tb.Label(
            linha,
            text="Formato HH:MM. Exemplo: 23:00"
        ).pack(side=LEFT)

        botoes = tb.Frame(self.aba_agendamento)
        botoes.pack(fill=X, pady=15)

        tb.Button(
            botoes,
            text="Criar agendamento diário",
            bootstyle=SUCCESS,
            command=self.criar_agendamento_thread
        ).pack(side=LEFT, padx=(0, 8))

        tb.Button(
            botoes,
            text="Executar agendamento agora",
            bootstyle=PRIMARY,
            command=self.executar_agendamento_thread
        ).pack(side=LEFT, padx=8)

        tb.Button(
            botoes,
            text="Consultar agendamento",
            bootstyle=INFO,
            command=self.consultar_agendamento_thread
        ).pack(side=LEFT, padx=8)

        tb.Button(
            botoes,
            text="Remover agendamento",
            bootstyle=DANGER,
            command=self.remover_agendamento_thread
        ).pack(side=LEFT, padx=8)

        tb.Button(
            botoes,
            text="Abrir log do agendador",
            bootstyle=SECONDARY,
            command=self.abrir_log_agendador
        ).pack(side=LEFT, padx=8)

        log_frame = tb.Labelframe(self.aba_agendamento, text="Log do agendamento", padding=10)
        log_frame.pack(fill=BOTH, expand=True)

        self.txt_agendamento = tb.Text(log_frame, height=22, wrap="word")
        self.txt_agendamento.pack(fill=BOTH, expand=True)

    def montar_aba_logs(self):
        botoes = tb.Frame(self.aba_logs)
        botoes.pack(fill=X)

        tb.Button(
            botoes,
            text="Abrir pasta de logs",
            bootstyle=PRIMARY,
            command=self.abrir_pasta_logs
        ).pack(side=LEFT, padx=(0, 8))

        tb.Button(
            botoes,
            text="Abrir histórico de envio",
            bootstyle=SECONDARY,
            command=self.abrir_historico
        ).pack(side=LEFT, padx=8)

        tb.Button(
            botoes,
            text="Abrir config JSON",
            bootstyle=SECONDARY,
            command=self.abrir_config_json
        ).pack(side=LEFT, padx=8)

        aviso = tb.Label(
            self.aba_logs,
            text="Os logs ficam salvos na pasta agente_local/logs.",
            bootstyle="secondary"
        )
        aviso.pack(anchor=W, pady=20)

    def escrever_log(self, texto):
        self.txt_log.insert("end", texto + "\n")
        self.txt_log.see("end")
        self.root.update_idletasks()

    def escrever_log_agendamento(self, texto):
        self.txt_agendamento.insert("end", texto + "\n")
        self.txt_agendamento.see("end")
        self.root.update_idletasks()

    def enviar_thread(self):
        threading.Thread(target=self.enviar_xmls, daemon=True).start()

    def enviar_xmls(self):
        try:
            self.salvar_config(silencioso=True)

            self.lbl_status.configure(text="Enviando XMLs...")
            self.txt_log.delete("1.0", "end")
            self.escrever_log("Iniciando envio...")

            buffer = io.StringIO()

            with contextlib.redirect_stdout(buffer):
                resultado = executar_envio()

            saida = buffer.getvalue()
            self.escrever_log(saida)

            self.escrever_log("")
            self.escrever_log("Resumo:")
            self.escrever_log(f"Total encontrados: {resultado.get('total')}")
            self.escrever_log(f"Pendentes: {resultado.get('pendentes')}")
            self.escrever_log(f"Enviados: {resultado.get('enviados')}")
            self.escrever_log(f"Ignorados já enviados: {resultado.get('ignorados')}")
            self.escrever_log(f"Ignorados por tipo: {resultado.get('ignorados_tipo')}")
            self.escrever_log(f"Erros: {resultado.get('erros')}")

            self.lbl_status.configure(text="Envio finalizado.")
            messagebox.showinfo("Envio finalizado", "Processo de envio concluído.")

        except Exception as erro:
            self.lbl_status.configure(text="Erro no envio.")
            self.escrever_log(f"ERRO: {erro}")
            messagebox.showerror("Erro", str(erro))

    def testar_conexao_thread(self):
        threading.Thread(target=self.testar_conexao, daemon=True).start()

    def testar_conexao(self):
        try:
            api_url = self.var_api.get().strip()

            if "/api/" in api_url:
                base_url = api_url.split("/api/")[0] + "/login/"
            else:
                base_url = api_url

            self.escrever_log(f"Testando conexão: {base_url}")

            resposta = requests.get(base_url, timeout=10)

            self.escrever_log(f"Status HTTP: {resposta.status_code}")

            if resposta.status_code < 500:
                messagebox.showinfo("Conexão OK", "Portal respondeu com sucesso.")
            else:
                messagebox.showwarning("Atenção", f"Portal respondeu com status {resposta.status_code}")

        except Exception as erro:
            self.escrever_log(f"ERRO conexão: {erro}")
            messagebox.showerror("Erro de conexão", str(erro))

    def criar_agendamento_thread(self):
        threading.Thread(target=self.criar_agendamento, daemon=True).start()

    def criar_agendamento(self):
        try:
            self.salvar_config(silencioso=True)

            horario = self.var_horario.get().strip() or "23:00"
            self.escrever_log_agendamento(f"Criando agendamento diário às {horario}...")

            codigo, saida = criar_tarefa_diaria(horario)
            self.escrever_log_agendamento(saida)

            if codigo == 0:
                messagebox.showinfo("Sucesso", f"Agendamento criado para {horario}.")
            else:
                messagebox.showerror("Erro", saida)

        except Exception as erro:
            self.escrever_log_agendamento(f"ERRO: {erro}")
            messagebox.showerror("Erro", str(erro))

    def remover_agendamento_thread(self):
        threading.Thread(target=self.remover_agendamento, daemon=True).start()

    def remover_agendamento(self):
        try:
            self.escrever_log_agendamento("Removendo agendamento...")

            codigo, saida = remover_tarefa()
            self.escrever_log_agendamento(saida)

            if codigo == 0:
                messagebox.showinfo("Sucesso", "Agendamento removido.")
            else:
                messagebox.showerror("Erro", saida)

        except Exception as erro:
            self.escrever_log_agendamento(f"ERRO: {erro}")
            messagebox.showerror("Erro", str(erro))

    def executar_agendamento_thread(self):
        threading.Thread(target=self.executar_agendamento, daemon=True).start()

    def executar_agendamento(self):
        try:
            self.salvar_config(silencioso=True)

            self.escrever_log_agendamento("Executando tarefa agendada agora...")

            codigo, saida = executar_tarefa_agora()
            self.escrever_log_agendamento(saida)

            if codigo == 0:
                messagebox.showinfo("Executado", "Tarefa enviada para execução.")
            else:
                messagebox.showerror("Erro", saida)

        except Exception as erro:
            self.escrever_log_agendamento(f"ERRO: {erro}")
            messagebox.showerror("Erro", str(erro))

    def consultar_agendamento_thread(self):
        threading.Thread(target=self.consultar_agendamento, daemon=True).start()

    def consultar_agendamento(self):
        try:
            self.escrever_log_agendamento("Consultando agendamento...")

            codigo, saida = consultar_tarefa()
            self.escrever_log_agendamento(saida)

        except Exception as erro:
            self.escrever_log_agendamento(f"ERRO: {erro}")
            messagebox.showerror("Erro", str(erro))

    def adicionar_pasta(self):
        pasta = filedialog.askdirectory(title="Selecione a pasta de XMLs")

        if pasta:
            pasta = pasta.replace("\\", "/")
            self.txt_pastas.insert("end", pasta + "\n")

    def abrir_pasta_logs(self):
        PASTA_LOGS.mkdir(exist_ok=True)
        subprocess.Popen(f'explorer "{PASTA_LOGS}"')

    def abrir_config_json(self):
        subprocess.Popen(f'notepad "{ARQUIVO_CONFIG}"')

    def abrir_historico(self):
        historico = Path(__file__).resolve().parent / "historico_envio.json"

        if not historico.exists():
            messagebox.showwarning("Histórico", "Histórico ainda não existe.")
            return

        subprocess.Popen(f'notepad "{historico}"')

    def abrir_log_agendador(self):
        log_agendador = caminho_agente() / "logs" / "agendador_agente.log"

        if not log_agendador.exists():
            messagebox.showwarning("Log", "Log do agendador ainda não existe.")
            return

        subprocess.Popen(f'notepad "{log_agendador}"')


if __name__ == "__main__":
    app = tb.Window(themename="superhero")
    AgenteXMLApp(app)
    app.mainloop()