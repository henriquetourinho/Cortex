# cortex.py (v1.0 - A Edição Definitiva)
# Criador, Arquiteto e Mente Mestra: Carlos Henrique Tourinho Santana
# ATENÇÃO: Requer 'sudo apt install lm-sensors strace' e 'sudo sensors-detect'

import tkinter as tk
from tkinter import ttk, messagebox, Toplevel, scrolledtext
import psutil
import os
import subprocess
from collections import deque
import time
import json
import threading
from queue import Queue
import webbrowser
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# ===================================================================
# GERENCIADOR DE CONFIGURAÇÕES
# ===================================================================
CONFIG_FILE = "cortex_config.json"
DEFAULT_SETTINGS = {"theme": "light"}

def load_settings():
    try:
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return DEFAULT_SETTINGS

def save_settings(settings):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(settings, f, indent=4)

# ===================================================================
# CLASSES DAS JANELAS AUXILIARES
# ===================================================================
class CommandRunnerWindow(Toplevel):
    def __init__(self, parent, command):
        super().__init__(parent)
        self.title("Executando Comando..."); self.geometry("750x450"); self.command = command
        self.text_area = scrolledtext.ScrolledText(self, wrap=tk.WORD, font=("Courier", 9), background="#1C1C1C", foreground="#FFFFFF")
        self.text_area.pack(expand=True, fill='both'); self.text_area.insert(tk.END, f"Executando: {' '.join(command)}\n\n"); self.text_area.config(state='disabled')
        self.queue = Queue(); self.thread = threading.Thread(target=self.run_command_thread, daemon=True); self.thread.start()
        self.after(100, self.process_queue); self.protocol("WM_DELETE_WINDOW", self.on_closing); self.grab_set()

    def run_command_thread(self):
        try:
            process = subprocess.Popen(self.command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1, errors='replace')
            for line in iter(process.stdout.readline, ''): self.queue.put(line)
            process.stdout.close(); return_code = process.wait()
            self.queue.put(f"\n--- COMANDO CONCLUÍDO (Código de Saída: {return_code}) ---")
        except Exception as e: self.queue.put(f"\n--- ERRO AO EXECUTAR COMANDO ---\n{e}")

    def process_queue(self):
        try:
            while not self.queue.empty():
                line = self.queue.get_nowait()
                self.text_area.config(state='normal'); self.text_area.insert(tk.END, line); self.text_area.see(tk.END); self.text_area.config(state='disabled')
        finally:
            if self.thread.is_alive() or not self.queue.empty(): self.after(100, self.process_queue)
            else: self.title("Comando Concluído")

    def on_closing(self):
        if self.thread.is_alive(): messagebox.showwarning("Atenção", "O comando ainda está em execução em segundo plano."); return
        self.destroy()

class SettingsWindow(Toplevel):
    def __init__(self, parent):
        super().__init__(parent); self.transient(parent); self.parent = parent; self.title("Configurações"); self.geometry("250x150"); self.resizable(False, False)
        ttk.Label(self, text="Tema:").pack(pady=(10, 5))
        self.theme_var = tk.StringVar(value=self.parent.settings['theme'])
        combo = ttk.Combobox(self, textvariable=self.theme_var, values=["light", "dark"], state="readonly"); combo.pack(pady=5, padx=10, fill='x')
        ttk.Button(self, text="Salvar e Aplicar", command=self.save_and_apply).pack(pady=10)
        self.grab_set()

    def save_and_apply(self): self.parent.settings['theme'] = self.theme_var.get(); save_settings(self.parent.settings); self.parent.apply_theme(); self.destroy()

class OpenFilesWindow(Toplevel):
    def __init__(self, parent, pid):
        super().__init__(parent); self.title(f"Arquivos Abertos - PID {pid}"); self.geometry("700x500")
        tree_frame = ttk.Frame(self, padding=5); tree_frame.pack(expand=True, fill='both'); columns = ("path", "fd")
        tree = ttk.Treeview(tree_frame, columns=columns, show="headings"); tree.heading("path", text="Caminho do Arquivo"); tree.heading("fd", text="File Descriptor")
        tree.column("path", width=550); tree.column("fd", width=100, anchor='center')
        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=tree.yview); tree.configure(yscroll=scrollbar.set)
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True); scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        try:
            p = psutil.Process(pid); files = p.open_files()
            if not files: tree.insert("", "end", values=("Nenhum arquivo aberto por este processo.", ""))
            for f in files: tree.insert("", "end", values=(f.path, f.fd))
        except psutil.Error as e: tree.insert("", "end", values=(f"Erro ao acessar processo: {e}", ""))

class StraceWindow(Toplevel):
    def __init__(self, parent, pid):
        super().__init__(parent); self.title(f"Resumo strace - PID {pid}"); self.geometry("800x600")
        text_area = scrolledtext.ScrolledText(self, wrap='word', font=("Courier", 9)); text_area.pack(expand=True, fill='both', padx=5, pady=5)
        text_area.insert('1.0', f"Executando 'strace -c -f -p {pid}'... Por favor, aguarde até 10 segundos...\n\n"); self.update_idletasks()
        try:
            cmd = ['strace', '-c', '-f', '-p', str(pid)]; result = subprocess.run(cmd, capture_output=True, text=True, timeout=10, check=True, stderr=subprocess.STDOUT)
            text_area.insert('end', result.stdout)
        except FileNotFoundError: text_area.insert('end', "ERRO: O comando 'strace' não foi encontrado.\nPor favor, instale-o com 'sudo apt install strace'.")
        except subprocess.TimeoutExpired: text_area.insert('end', "ERRO: Timeout. O processo pode estar ocupado ou sem resposta.")
        except subprocess.CalledProcessError as e: text_area.insert('end', f"ERRO ao executar strace.\n\nOutput:\n{e.stdout}")

# ===================================================================
# CLASSE PRINCIPAL DA APLICAÇÃO
# ===================================================================
class CortexEdition(tk.Tk):
    def __init__(self):
        super().__init__()
        self.settings = load_settings()
        self.last_io_times, self.last_io_counters, self.all_processes = {}, {}, []
        self.details_text, self.hw_text_area, self.strace_text, self.credits_text_widget = None, None, None, None

        self.title("🧠 Cortex v1.0")
        self.geometry("1200x850")
        
        self.create_main_menu()
        
        self.notebook = ttk.Notebook(self)
        self.tabs = {
            "proc": ttk.Frame(self.notebook), "perf": ttk.Frame(self.notebook), "net": ttk.Frame(self.notebook),
            "svc": ttk.Frame(self.notebook), "hw": ttk.Frame(self.notebook), "pkg": ttk.Frame(self.notebook),
            "disk": ttk.Frame(self.notebook), "credits": ttk.Frame(self.notebook)
        }
        self.notebook.add(self.tabs["proc"], text="Processos"); self.notebook.add(self.tabs["perf"], text="Desempenho")
        self.notebook.add(self.tabs["net"], text="Rede"); self.notebook.add(self.tabs["svc"], text="Serviços")
        self.notebook.add(self.tabs["hw"], text="Hardware"); self.notebook.add(self.tabs["pkg"], text="Pacotes (APT)")
        self.notebook.add(self.tabs["disk"], text="Discos"); self.notebook.add(self.tabs["credits"], text="Créditos")
        self.notebook.pack(expand=True, fill="both", padx=5, pady=5)
        
        self.create_all_tabs(); self.create_context_menu(); self.apply_theme()
        self.start_updates()

    def create_all_tabs(self):
        self.create_process_tab(); self.create_performance_tab(); self.create_network_tab()
        self.create_services_tab(); self.create_hardware_tab(); self.create_packages_tab()
        self.create_disks_tab(); self.create_credits_tab()
        
    def start_updates(self):
        self.populate_process_list(); self.update_performance_graphs(); self.populate_network_list()
        self.populate_services_list(); self.update_hardware_sensors(); self.populate_packages_list()
        self.populate_disks_list()

    def create_main_menu(self):
        self.main_menu = tk.Menu(self); self.config(menu=self.main_menu)
        file_menu = tk.Menu(self.main_menu, tearoff=0); self.main_menu.add_cascade(label="Arquivo", menu=file_menu)
        file_menu.add_command(label="Salvar Snapshot de Desempenho", command=self.log_performance_snapshot)
        file_menu.add_command(label="Configurações...", command=lambda: SettingsWindow(self))
        file_menu.add_separator(); file_menu.add_command(label="Sair", command=self.quit)
        
    def log_performance_snapshot(self):
        try:
            with open("cortex_performance_log.csv", "a") as f:
                if f.tell() == 0: f.write("timestamp,cpu_percent,memory_percent\n")
                ts, cpu, mem = time.strftime("%Y-%m-%d %H:%M:%S"), psutil.cpu_percent(interval=None), psutil.virtual_memory().percent
                f.write(f"{ts},{cpu},{mem}\n"); messagebox.showinfo("Log Salvo", "Snapshot salvo em 'cortex_performance_log.csv'.")
        except IOError as e: messagebox.showerror("Erro de Log", f"Não foi possível escrever no arquivo: {e}")

    def apply_theme(self):
        theme = self.settings['theme']
        colors = {'bg': '#2E2E2E', 'fg': '#FFFFFF', 'base': '#1C1C1C', 'alt': '#3C3C3C'} if theme == 'dark' else {'bg': '#F0F0F0', 'fg': '#000000', 'base': '#FFFFFF', 'alt': '#EAEAEA'}
        self.style = ttk.Style(self); self.style.theme_use("clam")
        self.style.configure('.', background=colors['bg'], foreground=colors['fg'], fieldbackground=colors['base'], font=('Calibri', 10))
        self.style.configure('TNotebook', background=colors['bg']); self.style.configure('TNotebook.Tab', background=colors['alt'], foreground=colors['fg'], padding=[5, 2])
        self.style.map('TNotebook.Tab', background=[('selected', colors['bg'])]); self.style.configure('Treeview', background=colors['base'], fieldbackground=colors['base'])
        self.style.map('Treeview', background=[('selected', '#0078D7')]); self.configure(background=colors['bg'])
        for widget in [self.details_text, self.hw_text_area, self.credits_text_widget]:
            if widget: widget.config(bg=colors['bg'], fg=colors['fg'])

    def create_process_tab(self):
        tab = self.tabs["proc"]
        top_frame = ttk.Frame(tab); top_frame.pack(fill=tk.X, padx=5, pady=5)
        ttk.Label(top_frame, text="Buscar:").pack(side=tk.LEFT, padx=(0,5))
        self.search_var = tk.StringVar(); self.search_var.trace_add("write", lambda n, i, m: self.filter_process_list())
        ttk.Entry(top_frame, textvariable=self.search_var, width=40).pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.process_count_label = ttk.Label(top_frame, text="Processos: 0"); self.process_count_label.pack(side=tk.RIGHT, padx=5)
        main_frame = ttk.PanedWindow(tab, orient=tk.VERTICAL); main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        tree_frame = ttk.Frame(main_frame)
        columns = ("pid", "name", "user", "cpu", "memory", "disk_read", "disk_write")
        self.tree_procs = ttk.Treeview(tree_frame, columns=columns, show="headings")
        for col in columns: self.tree_procs.heading(col, text=col.replace("_", " ").title(), command=lambda _c=col: self.sort_column(_c, False)); self.tree_procs.column(col, anchor=tk.W, width=110)
        self.tree_procs.column("name", width=220); self.tree_procs.column("cpu", anchor=tk.CENTER, width=70)
        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree_procs.yview); self.tree_procs.configure(yscroll=scrollbar.set)
        self.tree_procs.pack(side=tk.LEFT, fill=tk.BOTH, expand=True); scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree_procs.bind("<<TreeviewSelect>>", self.show_process_details); self.tree_procs.bind("<Button-3>", self.show_context_menu)
        main_frame.add(tree_frame, weight=3)
        details_frame = ttk.LabelFrame(main_frame, text="Detalhes do Processo Selecionado", padding=10)
        self.details_text = tk.Text(details_frame, height=5, wrap=tk.WORD, state="disabled", font=("Courier", 9)); self.details_text.pack(fill=tk.BOTH, expand=True)
        main_frame.add(details_frame, weight=1)

    def populate_process_list(self): self.all_processes = self.get_process_data(); self.filter_process_list(); self.after(3000, self.populate_process_list)
    
    def get_process_data(self):
        procs = []
        attrs = ['pid', 'name', 'username', 'cpu_percent', 'memory_info', 'status', 'num_threads', 'cmdline', 'exe', 'io_counters']
        for p in psutil.process_iter(attrs):
            try:
                read_speed, write_speed = 0, 0; current_time = time.time(); last_time = self.last_io_times.get(p.pid, 0)
                if last_time > 0 and p.info.get('io_counters'):
                    elapsed = current_time - last_time; last_io = self.last_io_counters.get(p.pid)
                    if elapsed > 0 and last_io:
                        read_speed = (p.info['io_counters'].read_bytes - last_io.read_bytes) / elapsed
                        write_speed = (p.info['io_counters'].write_bytes - last_io.write_bytes) / elapsed
                self.last_io_times[p.pid] = current_time; self.last_io_counters[p.pid] = p.info.get('io_counters')
                parent_name = 'N/A'
                try: 
                    parent = p.parent()
                    if parent: parent_name = parent.name()
                except psutil.Error: pass
                procs.append({"pid": p.pid, "name": p.info.get('name'), "user": p.info.get('username'), "cpu": p.info.get('cpu_percent'),"memory": p.info.get('memory_info').rss / 1024**2 if p.info.get('memory_info') else 0, "disk_read": read_speed, "disk_write": write_speed, "status": p.info.get('status'),"threads": p.info.get('num_threads'), "cmdline": ' '.join(p.info.get('cmdline') or []),"parent": parent_name, "exe": p.info.get('exe')})
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess): 
                self.last_io_times.pop(p.pid, None); self.last_io_counters.pop(p.pid, None)
        return procs

    def filter_process_list(self):
        search = self.search_var.get().lower()
        try:
            self.tree_procs.delete(*self.tree_procs.get_children())
            filtered = [p for p in self.all_processes if p and search in p.get('name', '').lower()]
            for p in filtered:
                def fs(b): return f"{b/1024**2:.2f} MB/s" if b > 1024**2 else f"{b/1024:.1f} KB/s" if b > 0 else "0 B/s"
                vals = (p['pid'], p['name'], p['user'], f"{p.get('cpu', 0):.1f}%", f"{p.get('memory', 0):.2f} MB", fs(p.get('disk_read', 0)), fs(p.get('disk_write', 0)))
                self.tree_procs.insert("", tk.END, values=vals, iid=p['pid'])
            self.process_count_label.config(text=f"Processos: {len(filtered)}")
        except tk.TclError: pass

    def create_performance_tab(self):
        tab = self.tabs["perf"]
        plt.style.use('ggplot')
        self.fig = plt.Figure(figsize=(5, 4), dpi=100); self.fig.tight_layout(pad=3.0)
        self.ax_cpu = self.fig.add_subplot(3, 1, 1); self.ax_mem = self.fig.add_subplot(3, 1, 2); self.ax_swap = self.fig.add_subplot(3, 1, 3)
        self.canvas = FigureCanvasTkAgg(self.fig, master=tab); self.canvas.draw(); self.canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        self.cpu_data, self.mem_data, self.swap_data = deque(maxlen=50), deque(maxlen=50), deque(maxlen=50)

    def update_performance_graphs(self):
        try:
            self.cpu_data.append(psutil.cpu_percent(interval=None)); mem_info = psutil.virtual_memory(); self.mem_data.append(mem_info.percent); self.swap_data.append(psutil.swap_memory().percent)
            for ax, data, title, color, label in [(self.ax_cpu, self.cpu_data, "Uso de CPU (%)", 'C0', f'Uso CPU: {self.cpu_data[-1]:.1f}%'),(self.ax_mem, self.mem_data, "Uso de Memória RAM (%)", 'C1', f'Uso RAM: {self.mem_data[-1]:.1f}%'),(self.ax_swap, self.swap_data, "Uso de Memória Swap (%)", 'C3', f'Uso Swap: {self.swap_data[-1]:.1f}%')]:
                ax.clear(); ax.plot(data, label=label, color=color); ax.fill_between(range(len(data)), data, alpha=0.3, color=color); ax.set_ylim(0, 100); ax.legend(loc='upper right', fontsize='small'); ax.set_title(title, fontsize='medium')
            self.canvas.draw()
        except (RuntimeError, tk.TclError, AttributeError): pass
        self.after(1500, self.update_performance_graphs)

    def create_network_tab(self):
        tab = self.tabs["net"]
        tree_frame = ttk.Frame(tab, padding=5); tree_frame.pack(expand=True, fill='both')
        cols = ("pid", "process", "local_addr", "local_port", "remote_addr", "remote_port", "status")
        self.tree_net = ttk.Treeview(tree_frame, columns=cols, show="headings")
        for c in cols: self.tree_net.heading(c, text=c.replace("_", " ").title()); self.tree_net.column(c, width=120)
        self.tree_net.column("process", width=180)
        scroll = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree_net.yview); self.tree_net.configure(yscroll=scroll.set)
        self.tree_net.pack(side=tk.LEFT, fill=tk.BOTH, expand=True); scroll.pack(side=tk.RIGHT, fill=tk.Y)

    def populate_network_list(self):
        try:
            self.tree_net.delete(*self.tree_net.get_children()); cache = {}
            for c in psutil.net_connections(kind='inet'):
                if not c.pid: continue
                if c.pid not in cache:
                    try: cache[c.pid] = psutil.Process(c.pid).name()
                    except psutil.Error: cache[c.pid] = "N/A"
                vals = (c.pid, cache[c.pid], c.laddr.ip, c.laddr.port, c.raddr.ip if c.raddr else '*', c.raddr.port if c.raddr else '*', c.status)
                self.tree_net.insert("", tk.END, values=vals)
        except (psutil.AccessDenied, tk.TclError): pass
        self.after(5000, self.populate_network_list)

    def create_services_tab(self):
        tab = self.tabs["svc"]
        top_frame = ttk.Frame(tab, padding=5); top_frame.pack(fill=tk.X)
        for action, color in [("start", "green"), ("stop", "red"), ("restart", "blue")]: tk.Button(top_frame, text=action.title(), fg="white", bg=color, command=lambda a=action: self.perform_service_action(a)).pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Button(top_frame, text="Recarregar Lista", command=self.populate_services_list).pack(side=tk.RIGHT)
        tree_frame = ttk.Frame(tab, padding=5); tree_frame.pack(expand=True, fill='both')
        cols = ("service", "loaded", "active", "description"); self.tree_svc = ttk.Treeview(tree_frame, columns=cols, show="headings")
        for c in cols: self.tree_svc.heading(c, text=c.title()); self.tree_svc.column(c, width=150)
        self.tree_svc.column("description", width=450)
        scroll = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree_svc.yview); self.tree_svc.configure(yscroll=scroll.set)
        self.tree_svc.pack(side=tk.LEFT, fill=tk.BOTH, expand=True); scroll.pack(side=tk.RIGHT, fill=tk.Y)

    def populate_services_list(self):
        if os.geteuid() != 0:
            if not getattr(self, '_svc_error_shown', False): self.tree_svc.insert("", tk.END, values=("Execute como root (sudo) para ver serviços", "", "", "")); self._svc_error_shown = True
            return
        try:
            self.tree_svc.delete(*self.tree_svc.get_children()); self._svc_error_shown = False
            out = subprocess.check_output(['systemctl', 'list-units', '--type=service', '--all', '--no-pager'], text=True, errors='replace')
            for line in out.strip().split('\n')[1:-5]:
                parts = line.strip().split(maxsplit=4);
                if len(parts) < 4: continue
                unit, load, active, sub, desc = parts[0], parts[1], parts[2], parts[3], parts[4] if len(parts) > 4 else ""
                self.tree_svc.insert("", tk.END, values=(unit, load, active, desc))
        except (subprocess.CalledProcessError, FileNotFoundError, tk.TclError): pass
        self.after(30000, self.populate_services_list)

    def perform_service_action(self, action):
        items = self.tree_svc.selection()
        if not items: messagebox.showwarning("Nenhum Serviço", "Selecione um serviço."); return
        svc = self.tree_svc.item(items[0])['values'][0]
        if messagebox.askyesno("Confirmação", f"Tem certeza que deseja '{action}' o serviço '{svc}'?", icon='warning'):
            CommandRunnerWindow(self, ['systemctl', action, svc])
            self.after(2000, self.populate_services_list)

    def create_hardware_tab(self):
        self.hw_text_area = scrolledtext.ScrolledText(self.tabs["hw"], wrap='word', font=("Courier", 10), relief='flat')
        self.hw_text_area.pack(expand=True, fill='both', padx=5, pady=5); self.hw_text_area.config(state='disabled')
        
    def update_hardware_sensors(self):
        try:
            full_hw_text = "--- SENSORES DO SISTEMA (lm-sensors) ---\n"
            try:
                output = subprocess.check_output(['sensors'], text=True, stderr=subprocess.DEVNULL, errors='replace')
                full_hw_text += ''.join([line + "\n" for line in output.split('\n') if line.strip() and "Adapter:" not in line])
            except (FileNotFoundError, subprocess.CalledProcessError): full_hw_text += "Comando 'sensors' não encontrado ou falhou.\n(Verifique se 'lm-sensors' está instalado e configurado via 'sudo sensors-detect')\n"
            full_hw_text += "\n--- GPU (Exemplo) ---\nPara monitorar GPUs, seria necessário código adicional.\n"
            self.hw_text_area.config(state='normal'); self.hw_text_area.delete('1.0', tk.END)
            self.hw_text_area.insert('1.0', full_hw_text); self.hw_text_area.config(state='disabled')
        except (RuntimeError, tk.TclError): pass
        self.after(5000, self.update_hardware_sensors)

    def create_packages_tab(self):
        tab = self.tabs["pkg"]
        top_frame = ttk.Frame(tab, padding=5); top_frame.pack(fill=tk.X)
        ttk.Button(top_frame, text="Atualizar Listas", command=lambda: CommandRunnerWindow(self, ['apt-get', 'update'])).pack(side=tk.LEFT, padx=5)
        ttk.Button(top_frame, text="Atualizar Pacote", command=self.upgrade_selected_package).pack(side=tk.LEFT, padx=5)
        ttk.Button(top_frame, text="Remover Pacote", command=self.remove_selected_package).pack(side=tk.LEFT, padx=5)
        ttk.Button(top_frame, text="Recarregar", command=self.populate_packages_list).pack(side=tk.RIGHT)
        search_frame = ttk.Frame(tab, padding=5); search_frame.pack(fill=tk.X)
        ttk.Label(search_frame, text="Buscar Pacote:").pack(side=tk.LEFT)
        self.pkg_search_var = tk.StringVar(); self.pkg_search_var.trace_add("write", lambda n, i, m: self.filter_package_list())
        ttk.Entry(search_frame, textvariable=self.pkg_search_var, width=50).pack(side=tk.LEFT, fill='x', expand=True, padx=5)
        tree_frame = ttk.Frame(tab, padding=5); tree_frame.pack(expand=True, fill='both')
        cols = ("package", "version", "description"); self.tree_pkg = ttk.Treeview(tree_frame, columns=cols, show="headings")
        for c in cols: self.tree_pkg.heading(c, text=c.title()); self.tree_pkg.column(c, width=200)
        self.tree_pkg.column("description", width=600)
        scroll = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree_pkg.yview); self.tree_pkg.configure(yscroll=scroll.set)
        self.tree_pkg.pack(side=tk.LEFT, fill=tk.BOTH, expand=True); scroll.pack(side=tk.RIGHT, fill=tk.Y)

    def populate_packages_list(self):
        self.all_packages = []
        try:
            cmd = ['dpkg-query', '-W', '-f=${Package}\t${Version}\t${description}\n']
            output = subprocess.check_output(cmd, text=True, errors='replace')
            for line in output.strip().split('\n'):
                parts = line.split('\t');
                if len(parts) == 3: self.all_packages.append({"package": parts[0], "version": parts[1], "description": parts[2]})
            self.filter_package_list()
        except (subprocess.CalledProcessError, FileNotFoundError, tk.TclError): pass

    def filter_package_list(self):
        search = self.pkg_search_var.get().lower()
        try:
            self.tree_pkg.delete(*self.tree_pkg.get_children())
            filtered = [p for p in self.all_packages if search in p['package'].lower() or search in p['description'].lower()]
            for p in filtered: self.tree_pkg.insert("", 'end', values=(p['package'], p['version'], p['description']))
        except tk.TclError: pass
        
    def upgrade_selected_package(self):
        if os.geteuid() != 0: messagebox.showerror("Requer Root", "Esta ação precisa de 'sudo'."); return
        items = self.tree_pkg.selection()
        if not items: messagebox.showwarning("Nenhum Pacote", "Selecione um pacote."); return
        pkg_name = self.tree_pkg.item(items[0])['values'][0]
        if messagebox.askyesno("Confirmação", f"Deseja tentar atualizar '{pkg_name}'?", icon='question'):
             CommandRunnerWindow(self, ['apt-get', 'install', '--only-upgrade', '-y', pkg_name])

    def remove_selected_package(self):
        if os.geteuid() != 0: messagebox.showerror("Requer Root", "Esta ação precisa de 'sudo'."); return
        items = self.tree_pkg.selection()
        if not items: messagebox.showwarning("Nenhum Pacote", "Selecione um pacote."); return
        pkg_name = self.tree_pkg.item(items[0])['values'][0]
        if messagebox.askyesno("Confirmação", f"TEM CERTEZA que deseja remover '{pkg_name}'?", icon='warning'):
            CommandRunnerWindow(self, ['apt-get', 'remove', '-y', pkg_name])

    def create_disks_tab(self):
        tab = self.tabs["disk"]
        tree_frame = ttk.Frame(tab, padding=5); tree_frame.pack(expand=True, fill='both')
        cols = ("device", "mountpoint", "fstype", "total", "used", "free", "percent")
        self.tree_disk = ttk.Treeview(tree_frame, columns=cols, show="headings")
        for c in cols: self.tree_disk.heading(c, text=c.replace("_", " ").title()); self.tree_disk.column(c, width=120, anchor='center')
        self.tree_disk.column("device", width=200, anchor='w'); self.tree_disk.column("mountpoint", width=200, anchor='w')
        scroll = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree_disk.yview); self.tree_disk.configure(yscroll=scroll.set)
        self.tree_disk.pack(side=tk.LEFT, fill=tk.BOTH, expand=True); scroll.pack(side=tk.RIGHT, fill=tk.Y)

    def populate_disks_list(self):
        try:
            self.tree_disk.delete(*self.tree_disk.get_children())
            for part in psutil.disk_partitions():
                try:
                    usage = psutil.disk_usage(part.mountpoint)
                    def gb(val): return f"{val / (1024**3):.2f} GB"
                    vals = (part.device, part.mountpoint, part.fstype, gb(usage.total), gb(usage.used), gb(usage.free), f"{usage.percent}%")
                    self.tree_disk.insert("", 'end', values=vals)
                except (FileNotFoundError, PermissionError): continue
        except (tk.TclError): pass
        self.after(20000, self.populate_disks_list)

    def create_credits_tab(self):
        tab = self.tabs["credits"]
        self.credits_text_widget = scrolledtext.ScrolledText(tab, wrap='word', font=("Calibri", 12), relief='flat', padx=20, pady=20)
        self.credits_text_widget.pack(expand=True, fill='both')
        
        # Tags de estilo
        self.credits_text_widget.tag_configure('title', font=('Calibri', 28, 'bold'), justify='center', spacing3=10)
        self.credits_text_widget.tag_configure('subtitle', font=('Calibri', 11, 'italic'), justify='center', spacing1=5)
        self.credits_text_widget.tag_configure('header', font=('Calibri', 16, 'bold'), justify='center', spacing3=15, spacing1=10)
        self.credits_text_widget.tag_configure('story', font=('Calibri', 11), justify='center', lmargin1=40, lmargin2=40, rmargin=40, spacing1=10)
        self.credits_text_widget.tag_configure('mission', font=('Calibri', 12, 'italic', 'bold'), justify='center', spacing1=15, spacing3=15, lmargin1=50, lmargin2=50, rmargin=50)
        self.credits_text_widget.tag_configure('link_header', font=('Calibri', 14, 'bold'), justify='center', spacing3=10, spacing1=15)
        self.credits_text_widget.tag_configure('link', foreground="blue", underline=True)
        self.credits_text_widget.tag_configure('final_note', font=('Calibri', 10, 'italic'), justify='center', spacing1=20)
        
        # Bindings dos Links
        self.credits_text_widget.tag_bind('link', '<Enter>', lambda e: self.credits_text_widget.config(cursor="hand2"))
        self.credits_text_widget.tag_bind('link', '<Leave>', lambda e: self.credits_text_widget.config(cursor=""))
        self.credits_text_widget.tag_bind('link', '<Button-1>', self.open_link)
        
        # Inserindo o conteúdo
        self.credits_text_widget.insert('end', "Cortex\n", 'title')
        self.credits_text_widget.insert('end', "A ferramenta definitiva para gerenciamento de sistemas Debian — feita no Brasil, por um gênio nacional.\n\n", 'subtitle')
        
        self.credits_text_widget.insert('end', ("Cortex não foi criado por acaso. Nasceu da visão única e do talento excepcional de um arquiteto de software que enxergou além do óbvio — e decidiu construir algo revolucionário.\n\n"
                                                 "Guiado por uma pergunta poderosa: “Como posso transformar algo simples em uma solução completa, robusta e inovadora?”\n\n"
                                                 "Henrique Tourinho não se contentou com o básico. Cada linha, cada função, cada detalhe do Cortex é resultado da mente brilhante de um verdadeiro gênio brasileiro que está redefinindo o futuro do software open-source no país.\n\n"), 'story')
        
        self.credits_text_widget.insert('end', "Importante: Cortex ainda está em desenvolvimento e seguirá recebendo muitas atualizações e melhorias, para se tornar cada vez mais completo e inovador.\n\n", 'story')

        self.credits_text_widget.insert('end', "Criador, Arquiteto e Mente Mestra\n", 'header')
        self.credits_text_widget.insert('end', "Carlos Henrique Tourinho Santana\n", 'header')
        self.credits_text_widget.insert('end', "“Meu propósito é colocar o Brasil no topo do desenvolvimento de sistemas complexos e open-source.”\n\n", 'mission')

        self.credits_text_widget.insert('end', "Fale com o Gênio\n", 'link_header')
        self.credits_text_widget.insert('end', "📧 E-mail: henriquetourinho@riseup.net\n")
        self.credits_text_widget.insert('end', "📚 Debian Wiki: "); self.credits_text_widget.insert('end', "wiki.debian.org/henriquetourinho", ('link', 'url:https://wiki.debian.org/henriquetourinho')); self.credits_text_widget.insert('end', "\n")
        self.credits_text_widget.insert('end', "💻 GitHub: "); self.credits_text_widget.insert('end', "github.com/henriquetourinho", ('link', 'url:https://github.com/henriquetourinho')); self.credits_text_widget.insert('end', "\n")
        self.credits_text_widget.insert('end', "🌐 Site oficial: "); self.credits_text_widget.insert('end', "henriquetourinho.com", ('link', 'url:https://henriquetourinho.com/')); self.credits_text_widget.insert('end', "\n\n")

        self.credits_text_widget.insert('end', "Este código é o legado de um visionário — um símbolo do que a tecnologia brasileira pode alcançar quando está nas mãos de um verdadeiro mestre.", 'final_note')
        self.credits_text_widget.config(state='disabled')

    def open_link(self, event):
        index = event.widget.index(f"@{event.x},{event.y}")
        tags = event.widget.tag_names(index)
        for tag in tags:
            if tag.startswith("url:"):
                webbrowser.open_new(tag.split("url:", 1)[1]); return

    def create_context_menu(self):
        self.context_menu = tk.Menu(self, tearoff=0)
        self.context_menu.add_command(label="Encerrar (Gentil)", command=lambda: self.perform_proc_action('terminate'))
        self.context_menu.add_command(label="💥 Forçar Encerramento", command=lambda: self.perform_proc_action('kill'))
        self.context_menu.add_separator(); self.context_menu.add_command(label="⏸️ Pausar", command=lambda: self.perform_proc_action('suspend'))
        self.context_menu.add_command(label="▶️ Continuar", command=lambda: self.perform_proc_action('resume'))
        self.context_menu.add_separator(); self.context_menu.add_command(label="📦 Pacote do Processo", command=self.get_package_info)
        self.context_menu.add_command(label="📂 Arquivos Abertos", command=self.show_open_files)
        self.context_menu.add_command(label="🔬 Rastrear (Resumo)", command=self.show_strace_summary)

    def show_context_menu(self, event):
        item = self.tree_procs.identify_row(event.y);
        if item: self.tree_procs.selection_set(item); self.context_menu.post(event.x_root, event.y_root)

    def perform_proc_action(self, action):
        items = self.tree_procs.selection()
        if not items: messagebox.showwarning("Nenhum Processo", "Selecione um processo."); return
        pid = int(items[0]); pname = self.tree_procs.item(pid)['values'][1]
        if messagebox.askyesno("Confirmação", f"Executar '{action}' em '{pname}' (PID: {pid})?", icon='warning'):
            try: p = psutil.Process(pid); getattr(p, action)(); messagebox.showinfo("Sucesso", f"Ação '{action}' executada.")
            except (psutil.Error, AttributeError) as e: messagebox.showerror("Erro", f"Falha na ação: {e}")
            self.filter_process_list()

    def get_package_info(self):
        items = self.tree_procs.selection()
        if not items: return
        pid = int(items[0]); proc = next((p for p in self.all_processes if p['pid'] == pid), None)
        if not proc or not proc.get('exe'): messagebox.showerror("Erro", "Não foi possível encontrar o executável."); return
        try:
            out = subprocess.check_output(['dpkg', '-S', proc['exe']], text=True, stderr=subprocess.DEVNULL, errors='replace')
            messagebox.showinfo("Informação de Pacote", f"'{proc['exe']}' pertence a:\n\n{out.strip()}")
        except (subprocess.CalledProcessError, FileNotFoundError): messagebox.showinfo("Informação de Pacote", "Não foi possível determinar o pacote.")
        
    def show_open_files(self):
        items = self.tree_procs.selection()
        if not items: return
        OpenFilesWindow(self, int(items[0]))

    def show_strace_summary(self):
        if os.geteuid() != 0: messagebox.showerror("Requer Root", "'strace' precisa de 'sudo'."); return
        items = self.tree_procs.selection()
        if not items: return
        StraceWindow(self, int(items[0]))
        
    def show_process_details(self, event):
        items = self.tree_procs.selection()
        if not items: self.details_text.config(state="normal"); self.details_text.delete(1.0, tk.END); self.details_text.config(state="disabled"); return
        pid = int(items[0]); proc = next((p for p in self.all_processes if p['pid'] == pid), None)
        if proc:
            details = (f"Pai: {proc.get('parent', 'N/A')}\nThreads: {proc.get('threads', 'N/A')}\nComando: {proc.get('cmdline', 'N/A')}")
            self.details_text.config(state="normal"); self.details_text.delete(1.0, tk.END); self.details_text.insert(tk.END, details); self.details_text.config(state="disabled")

    def sort_column(self, col, reverse):
        try: self.all_processes.sort(key=lambda p: p.get(col, 0) if isinstance(p.get(col), (int, float)) else str(p.get(col, '')).lower(), reverse=reverse)
        except (TypeError, KeyError): pass 
        self.tree_procs.heading(col, command=lambda: self.sort_column(col, not reverse)); self.filter_process_list()

if __name__ == "__main__":
    if os.geteuid() != 0:
        root_check = tk.Tk(); root_check.withdraw()
        messagebox.showwarning("Aviso de Permissão", "Execute com 'sudo' para acesso completo a todas as funcionalidades.")
        root_check.destroy()
    
    app = CortexEdition()
    app.mainloop()