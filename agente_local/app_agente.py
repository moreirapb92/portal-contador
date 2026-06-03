# -*- coding: utf-8 -*-

import contextlib
import datetime
import io
import json
import queue
import shutil
import subprocess
import threading
from pathlib import Path
from tkinter import filedialog, messagebox
import tkinter as tk

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


ARQUIVO_HISTORICO = Path(ARQUIVO_CONFIG).with_name("historico_envio.json")


class LogTempoReal(io.TextIOBase):
    def __init__(self, app, destino="envio"):
        super().__init__()
        self.app = app
        self.destino = destino
        self.buffer = ""

    def write(self, texto):
        if not texto:
            return 0

        self.buffer += texto

        while "\n" in self.buffer:
            linha, self.buffer = self.buffer.split("\n", 1)
            self.app.enfileirar_log(linha, destino=self.destino)

        return len(texto)

    def flush(self):
        if self.buffer:
            self.app.enfileirar_log(self.buffer, destino=self.destino)
            self.buffer = ""


class AgenteXMLApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Agente XML - Portal do Contador")
        self.root.geometry("1060x740")
        self.root.minsize(960, 680)

        self.fila_logs = queue.Queue()
        self.enviando = False

        self.config = self.carregar_config()

        self.var_api = tb.StringVar(value=self.config.get("api_url", "https://portal-contador.onrender.com/api/upload-xml/"))
        self.var_cnpj = tb.StringVar(value=self.config.get("cnpj", ""))
        self.var_token = tb.StringVar(value=self.config.get("token", ""))
        self.var_limite = tb.StringVar(value=str(self.config.get("limite_por_execucao", 100)))
        self.var_subpastas = tb.BooleanVar(value=bool(self.config.get("enviar_subpastas", True)))
        self.var_horario = tb.StringVar(value="23:00")

        self.btn_enviar = None
        self.btn_testar = None
        self.list_pastas = None

        self.montar_interface()
        self.root.after(100, self.processar_fila_logs)

    def carregar_config(self):
        if not ARQUIVO_CONFIG.exists():
            return {
                "api_url": "https://portal-contador.onrender.com/api/upload-xml/",
                "cnpj": "",
                "token": "",
                "pastas_xml": [],
                "enviar_subpastas": True,
                "extensoes": [".xml"],
                "timeout": 60,
                "limite_por_execucao": 100,
                "ignorar_arquivos_com": [
                    "procInutNFe",
                    "procEventoNFe",
                    "evento",
                    "retInutNFe"
                ]
            }

        with open(ARQUIVO_CONFIG, "r", encoding="utf-8-sig") as arquivo:
            return json.load(arquivo)

    def obter_pastas_da_lista(self):
        pastas = []
        vistos = set()

        if not self.list_pastas:
            return pastas

        for i in range(self.list_pastas.size()):
            pasta = self.list_pastas.get(i).strip().replace("\\", "/")

            if not pasta:
                continue

            chave = pasta.lower()

            if chave in vistos:
                continue

            vistos.add(chave)
            pastas.append(pasta)

        return pastas

    def gerar_config_atual(self):
        try:
            limite = int(self.var_limite.get() or 100)
        except Exception:
            limite = 100

        return {
            "api_url": self.var_api.get().strip(),
            "cnpj": self.var_cnpj.get().strip(),
            "token": self.var_token.get().strip(),
            "pastas_xml": self.obter_pastas_da_lista(),
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
            text="Envio automático de XMLs NF-e/NFC-e para o portal online.",
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
        self.notebook.add(self.aba_logs, text="Logs / Manutenção")

        self.montar_aba_envio()
        self.montar_aba_config()
        self.montar_aba_agendamento()
        self.montar_aba_logs()

    def montar_aba_envio(self):
        botoes = tb.Frame(self.aba_envio)
        botoes.pack(fill=X)

        self.btn_enviar = tb.Button(
            botoes,
            text="Enviar XMLs agora",
            bootstyle=SUCCESS,
            command=self.enviar_thread
        )
        self.btn_enviar.pack(side=LEFT, padx=(0, 8))

        self.btn_testar = tb.Button(
            botoes,
            text="Testar conexão com portal",
            bootstyle=PRIMARY,
            command=self.testar_conexao_thread
        )
        self.btn_testar.pack(side=LEFT, padx=8)

        tb.Button(
            botoes,
            text="Abrir pasta de logs",
            bootstyle=SECONDARY,
            command=self.abrir_pasta_logs
        ).pack(side=LEFT, padx=8)

        status = tb.Labelframe(self.aba_envio, text="Status", padding=10)
        status.pack(fill=X, pady=15)

        self.lbl_status = tb.Label(
            status,
            text="Aguardando ação...",
            font=("Segoe UI", 11, "bold")
        )
        self.lbl_status.pack(anchor=W)

        log_frame = tb.Labelframe(self.aba_envio, text="Log da execução em tempo real", padding=10)
        log_frame.pack(fill=BOTH, expand=True)

        self.txt_log = tb.Text(log_frame, height=24, wrap="word")
        self.txt_log.pack(fill=BOTH, expand=True)

    def montar_aba_config(self):
        form = tb.Labelframe(self.aba_config, text="Dados de conexão", padding=12)
        form.pack(fill=X)

        tb.Label(form, text="URL da API:").grid(row=0, column=0, sticky=W, pady=5)
        tb.Entry(form, textvariable=self.var_api, width=86).grid(row=0, column=1, sticky=W, pady=5)

        tb.Label(form, text="CNPJ da empresa:").grid(row=1, column=0, sticky=W, pady=5)
        tb.Entry(form, textvariable=self.var_cnpj, width=32).grid(row=1, column=1, sticky=W, pady=5)

        tb.Label(form, text="Token da empresa:").grid(row=2, column=0, sticky=W, pady=5)
        tb.Entry(form, textvariable=self.var_token, width=86, show="*").grid(row=2, column=1, sticky=W, pady=5)

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

        lista_frame = tb.Frame(pastas_frame)
        lista_frame.pack(fill=BOTH, expand=True)

        self.list_pastas = tk.Listbox(
            lista_frame,
            height=10,
            selectmode=tk.EXTENDED,
            font=("Segoe UI", 10)
        )
        self.list_pastas.pack(side=LEFT, fill=BOTH, expand=True)

        scrollbar = tk.Scrollbar(lista_frame, orient="vertical", command=self.list_pastas.yview)
        scrollbar.pack(side=RIGHT, fill=Y)
        self.list_pastas.configure(yscrollcommand=scrollbar.set)

        for pasta in self.config.get("pastas_xml", []):
            pasta = str(pasta).strip().replace("\\", "/")
            if pasta:
                self.list_pastas.insert("end", pasta)

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
            text="Remover pasta selecionada",
            bootstyle=DANGER,
            command=self.remover_pasta_selecionada
        ).pack(side=LEFT, padx=8)

        tb.Button(
            botoes,
            text="Abrir pasta selecionada",
            bootstyle=SECONDARY,
            command=self.abrir_pasta_selecionada
        ).pack(side=LEFT, padx=8)

        tb.Button(
            botoes,
            text="Limpar duplicadas",
            bootstyle=WARNING,
            command=self.limpar_pastas_duplicadas
        ).pack(side=LEFT, padx=8)

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
            text="Reprocessar todos XMLs",
            bootstyle=DANGER,
            command=self.reprocessar_todos_xmls
        ).pack(side=LEFT, padx=8)

        tb.Button(
            botoes,
            text="Abrir config JSON",
            bootstyle=SECONDARY,
            command=self.abrir_config_json
        ).pack(side=LEFT, padx=8)

        aviso = tb.Label(
            self.aba_logs,
            text=(
                "Reprocessar todos XMLs apaga apenas o histórico local do agente. "
                "Não apaga XMLs do computador nem documentos do portal."
            ),
            bootstyle="secondary"
        )
        aviso.pack(anchor=W, pady=20)

    def enfileirar_log(self, texto, destino="envio"):
        self.fila_logs.put((destino, texto))

    def processar_fila_logs(self):
        try:
            while True:
                destino, texto = self.fila_logs.get_nowait()

                if destino == "agendamento":
                    self._escrever_log_agendamento_ui(texto)
                else:
                    self._escrever_log_ui(texto)

        except queue.Empty:
            pass

        self.root.after(100, self.processar_fila_logs)

    def _escrever_log_ui(self, texto):
        self.txt_log.insert("end", texto + "\n")
        self.txt_log.see("end")

    def _escrever_log_agendamento_ui(self, texto):
        self.txt_agendamento.insert("end", texto + "\n")
        self.txt_agendamento.see("end")

    def set_status(self, texto):
        self.lbl_status.configure(text=texto)

    def set_envio_em_andamento(self, ativo):
        self.enviando = ativo

        if self.btn_enviar:
            self.btn_enviar.configure(state=DISABLED if ativo else NORMAL)

        if self.btn_testar:
            self.btn_testar.configure(state=DISABLED if ativo else NORMAL)

    def limpar_log_envio(self):
        self.txt_log.delete("1.0", "end")

    def enviar_thread(self):
        if self.enviando:
            messagebox.showwarning(
                "Envio em andamento",
                "Já existe um envio em execução. Aguarde finalizar."
            )
            return

        self.salvar_config(silencioso=True)
        self.limpar_pastas_duplicadas(silencioso=True)

        self.set_envio_em_andamento(True)
        self.set_status("Enviando XMLs...")
        self.limpar_log_envio()

        threading.Thread(target=self.enviar_xmls, daemon=True).start()

    def enviar_xmls(self):
        try:
            self.enfileirar_log("Iniciando envio...", destino="envio")

            log_tempo_real = LogTempoReal(self, destino="envio")

            with contextlib.redirect_stdout(log_tempo_real):
                resultado = executar_envio()

            log_tempo_real.flush()

            self.enfileirar_log("", destino="envio")
            self.enfileirar_log("Resumo:", destino="envio")

            if isinstance(resultado, dict):
                self.enfileirar_log(f"Total encontrados: {resultado.get('total')}", destino="envio")
                self.enfileirar_log(f"Pendentes: {resultado.get('pendentes')}", destino="envio")
                self.enfileirar_log(f"Enviados: {resultado.get('enviados')}", destino="envio")
                self.enfileirar_log(f"Ignorados já enviados: {resultado.get('ignorados')}", destino="envio")
                self.enfileirar_log(f"Ignorados por tipo: {resultado.get('ignorados_tipo')}", destino="envio")
                self.enfileirar_log(f"Erros: {resultado.get('erros')}", destino="envio")
            else:
                self.enfileirar_log("Processo finalizado, mas sem resumo retornado.", destino="envio")

            self.root.after(0, lambda: self.set_status("Envio finalizado."))
            self.root.after(0, lambda: messagebox.showinfo(
                "Envio finalizado",
                "Processo de envio concluído."
            ))

        except Exception as erro:
            self.enfileirar_log(f"ERRO: {erro}", destino="envio")
            self.root.after(0, lambda: self.set_status("Erro no envio."))
            self.root.after(0, lambda erro=erro: messagebox.showerror("Erro", str(erro)))

        finally:
            self.root.after(0, lambda: self.set_envio_em_andamento(False))

    def testar_conexao_thread(self):
        api_url = self.var_api.get().strip()
        threading.Thread(target=self.testar_conexao, args=(api_url,), daemon=True).start()

    def testar_conexao(self, api_url):
        try:
            if "/api/" in api_url:
                base_url = api_url.split("/api/")[0] + "/login/"
            else:
                base_url = api_url

            self.enfileirar_log(f"Testando conexão: {base_url}", destino="envio")

            resposta = requests.get(base_url, timeout=10)

            self.enfileirar_log(f"Status HTTP: {resposta.status_code}", destino="envio")

            if resposta.status_code < 500:
                self.root.after(0, lambda: messagebox.showinfo(
                    "Conexão OK",
                    "Portal respondeu com sucesso."
                ))
            else:
                self.root.after(0, lambda: messagebox.showwarning(
                    "Atenção",
                    f"Portal respondeu com status {resposta.status_code}"
                ))

        except Exception as erro:
            self.enfileirar_log(f"ERRO conexão: {erro}", destino="envio")
            self.root.after(0, lambda erro=erro: messagebox.showerror("Erro de conexão", str(erro)))

    def criar_agendamento_thread(self):
        self.salvar_config(silencioso=True)
        threading.Thread(target=self.criar_agendamento, daemon=True).start()

    def criar_agendamento(self):
        try:
            horario = self.var_horario.get().strip() or "23:00"
            self.enfileirar_log(f"Criando agendamento diário às {horario}...", destino="agendamento")

            codigo, saida = criar_tarefa_diaria(horario)
            self.enfileirar_log(saida, destino="agendamento")

            if codigo == 0:
                self.root.after(0, lambda: messagebox.showinfo(
                    "Sucesso",
                    f"Agendamento criado para {horario}."
                ))
            else:
                self.root.after(0, lambda: messagebox.showerror("Erro", saida))

        except Exception as erro:
            self.enfileirar_log(f"ERRO: {erro}", destino="agendamento")
            self.root.after(0, lambda erro=erro: messagebox.showerror("Erro", str(erro)))

    def remover_agendamento_thread(self):
        threading.Thread(target=self.remover_agendamento, daemon=True).start()

    def remover_agendamento(self):
        try:
            self.enfileirar_log("Removendo agendamento...", destino="agendamento")

            codigo, saida = remover_tarefa()
            self.enfileirar_log(saida, destino="agendamento")

            if codigo == 0:
                self.root.after(0, lambda: messagebox.showinfo("Sucesso", "Agendamento removido."))
            else:
                self.root.after(0, lambda: messagebox.showerror("Erro", saida))

        except Exception as erro:
            self.enfileirar_log(f"ERRO: {erro}", destino="agendamento")
            self.root.after(0, lambda erro=erro: messagebox.showerror("Erro", str(erro)))

    def executar_agendamento_thread(self):
        self.salvar_config(silencioso=True)
        threading.Thread(target=self.executar_agendamento, daemon=True).start()

    def executar_agendamento(self):
        try:
            self.enfileirar_log("Executando tarefa agendada agora...", destino="agendamento")

            codigo, saida = executar_tarefa_agora()
            self.enfileirar_log(saida, destino="agendamento")

            if codigo == 0:
                self.root.after(0, lambda: messagebox.showinfo(
                    "Executado",
                    "Tarefa enviada para execução."
                ))
            else:
                self.root.after(0, lambda: messagebox.showerror("Erro", saida))

        except Exception as erro:
            self.enfileirar_log(f"ERRO: {erro}", destino="agendamento")
            self.root.after(0, lambda erro=erro: messagebox.showerror("Erro", str(erro)))

    def consultar_agendamento_thread(self):
        threading.Thread(target=self.consultar_agendamento, daemon=True).start()

    def consultar_agendamento(self):
        try:
            self.enfileirar_log("Consultando agendamento...", destino="agendamento")

            codigo, saida = consultar_tarefa()
            self.enfileirar_log(saida, destino="agendamento")

        except Exception as erro:
            self.enfileirar_log(f"ERRO: {erro}", destino="agendamento")
            self.root.after(0, lambda erro=erro: messagebox.showerror("Erro", str(erro)))

    def adicionar_pasta(self):
        pasta = filedialog.askdirectory(title="Selecione a pasta de XMLs")

        if not pasta:
            return

        pasta = pasta.replace("\\", "/").strip()
        pasta_lower = pasta.lower()

        pastas_existentes = {
            self.list_pastas.get(i).strip().replace("\\", "/").lower()
            for i in range(self.list_pastas.size())
        }

        if pasta_lower in pastas_existentes:
            messagebox.showwarning(
                "Pasta duplicada",
                "Essa pasta já está cadastrada."
            )
            return

        self.list_pastas.insert("end", pasta)

    def remover_pasta_selecionada(self):
        selecionados = list(self.list_pastas.curselection())

        if not selecionados:
            messagebox.showwarning(
                "Nenhuma pasta selecionada",
                "Selecione uma pasta para remover."
            )
            return

        if not messagebox.askyesno(
            "Remover pasta",
            "Deseja remover a pasta selecionada da configuração?\n\nIsso não apaga arquivos do computador."
        ):
            return

        for indice in reversed(selecionados):
            self.list_pastas.delete(indice)

    def abrir_pasta_selecionada(self):
        selecionados = list(self.list_pastas.curselection())

        if not selecionados:
            messagebox.showwarning(
                "Nenhuma pasta selecionada",
                "Selecione uma pasta para abrir."
            )
            return

        pasta = self.list_pastas.get(selecionados[0])

        if not Path(pasta).exists():
            messagebox.showerror("Pasta não encontrada", f"A pasta não existe:\n{pasta}")
            return

        subprocess.Popen(f'explorer "{pasta}"')

    def limpar_pastas_duplicadas(self, silencioso=False):
        pastas = []
        vistos = set()

        for i in range(self.list_pastas.size()):
            pasta = self.list_pastas.get(i).strip().replace("\\", "/")

            if not pasta:
                continue

            chave = pasta.lower()

            if chave in vistos:
                continue

            vistos.add(chave)
            pastas.append(pasta)

        self.list_pastas.delete(0, "end")

        for pasta in pastas:
            self.list_pastas.insert("end", pasta)

        if not silencioso:
            messagebox.showinfo("Pastas", "Pastas duplicadas removidas.")

    def reprocessar_todos_xmls(self):
        if self.enviando:
            messagebox.showwarning(
                "Envio em andamento",
                "Aguarde o envio atual finalizar antes de reprocessar."
            )
            return

        confirmar = messagebox.askyesno(
            "Reprocessar todos XMLs",
            (
                "Isso vai apagar o histórico local do agente e permitir reenviar todos os XMLs novamente.\n\n"
                "Não apaga XMLs do computador.\n"
                "Não apaga documentos do portal.\n\n"
                "Deseja continuar?"
            )
        )

        if not confirmar:
            return

        try:
            if ARQUIVO_HISTORICO.exists():
                agora = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                backup = ARQUIVO_HISTORICO.with_name(f"historico_envio_backup_{agora}.json")

                shutil.copy2(ARQUIVO_HISTORICO, backup)
                ARQUIVO_HISTORICO.unlink()

                messagebox.showinfo(
                    "Histórico resetado",
                    f"Histórico removido com sucesso.\n\nBackup criado:\n{backup}"
                )
            else:
                messagebox.showinfo(
                    "Histórico",
                    "Nenhum histórico encontrado para remover."
                )

        except Exception as erro:
            messagebox.showerror("Erro", str(erro))

    def abrir_pasta_logs(self):
        PASTA_LOGS.mkdir(exist_ok=True)
        subprocess.Popen(f'explorer "{PASTA_LOGS}"')

    def abrir_config_json(self):
        subprocess.Popen(f'notepad "{ARQUIVO_CONFIG}"')

    def abrir_historico(self):
        if not ARQUIVO_HISTORICO.exists():
            messagebox.showwarning("Histórico", "Histórico ainda não existe.")
            return

        subprocess.Popen(f'notepad "{ARQUIVO_HISTORICO}"')

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