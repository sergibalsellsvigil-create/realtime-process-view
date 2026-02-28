"""
Model de Processos GNU/Linux INTERACTIU TEMPS REAL + Modbus TCP server
Autor: Sergi Balsells
Data: 19/02/2026 
Objectiu: Gràf INTERACTIU PPID→PID + Anàlisi jeràrquica + Temps real + TCP
"""

import subprocess
import networkx as nx
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
import tkinter as tk
from tkinter import ttk, messagebox
from collections import defaultdict
import threading
import time
from datetime import datetime
import os
   
pymodbus_disponible = True
pymodbus_version = "desconeguda"

def detectar_pymodbus():
    global pymodbus_disponible, pymodbus_version
    
    # Provar imports de forma progressiva (de nou a vell)
    imports_moderns = [
        # pymodbus 4.x+ (més nou)
        ("from pymodbus.server import start_tcp_server", "4.x+"),
        # pymodbus 3.5+
        ("from pymodbus.server.asynchronous import StartTcpServer", "3.5+"),
        # pymodbus 3.0-3.4 (versió actual)
        ("from pymodbus.server import StartTcpServer", "3.0-3.4"),
    ]
    
    imports_comuns = [
        ("from pymodbus.datastore import ModbusSequentialDataBlock, ModbusSlaveContext, ModbusServerContext", "tots")
    ]
    
    for import_str, versio in imports_moderns:
        try:
            exec(import_str)
            pymodbus_version = versio
            pymodbus_disponible = True
            print(f" pymodbus {versio} detectat correctament!")
            return versio
        except ImportError:
            continue
    
    print(" pymodbus no disponible (versió incompatible)")
    return None

# Auto-detectar al inici
pymodbus_version = detectar_pymodbus()

class MonitorProcessosInteractiu:
    def __init__(self):
        self.processos_actuals = {}
        self.processos_anterior = {}
        self.G = nx.DiGraph()
        self.realtemp_actiu = False
        self.modbus_actiu = False
        self.pid_seleccionat = None
        self.processos_creats = set()
        self.processos_eliminats = set()
        
        self.root = tk.Tk()
        self.root.title("MODEL PROCESSOS INTERACTIU - Temps Real")
        self.root.geometry("1600x1000")
        self.setup_gui()
        
    def obtenir_processos_complet(self):
        cmd = ['ps', 'ax', '-o', 'pid,ppid,user,%cpu,%mem,etime,state,comm']
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=3)
        processos_nous = {}

        lines = result.stdout.strip().split('\n')[1:]
        for line in lines:
            if not line.strip(): 
                continue
            parts = line.split(maxsplit=7)
            if len(parts) >= 8:
                pid, ppid, user, cpu, mem, etime, estat, comanda = parts[:8]
                processos_nous[pid] = {
                    'pid': pid.strip(),
                    'ppid': ppid.strip(),
                    'user': user.strip(),
                    'cpu': cpu.strip(),
                    'mem': mem.strip(),
                    'etime': etime.strip(),
                    'estat': estat.strip(),
                    'comanda': comanda.strip()
                }
        
        # Fer servir .keys() per comparar només PIDs
        self.processos_anterior = self.processos_actuals.copy()
        self.processos_actuals = processos_nous
        self.processos_creats = set(processos_nous.keys()) - set(self.processos_anterior.keys())
        self.processos_eliminats = set(self.processos_anterior.keys()) - set(processos_nous.keys())
        
        # DEBUG: Veure canvis reals
        if self.processos_creats or self.processos_eliminats:
            print(f"🔍 +{len(self.processos_creats)} VERDES | -{len(self.processos_eliminats)} ROJOS")
        
        return len(processos_nous)
    
    def construir_graf_dirigit_complet(self):
        # No netejar tot el graf, només actualitzar nodes i arestes
        nodos_anteriors = set(self.G.nodes())
        
        # Actualitzar/Afegir processos actuals
        for pid, info in self.processos_actuals.items():
            self.G.add_node(pid, **info)
        
        # Mantenir nodes eliminats però marcar-los com eliminat
        for pid in self.processos_eliminats:
            if pid in nodos_anteriors and pid in self.processos_anterior:
                self.G.add_node(pid, **self.processos_anterior[pid], estat='ELIMINAT')
        
        # Netejar només arestes i reconstruir (només processos actuals tenen connexions vàlides)
        self.G.clear_edges()
        for pid, info in self.processos_actuals.items():
            ppid = info['ppid']
            if ppid in self.processos_actuals and ppid != pid:
                self.G.add_edge(ppid, pid, relacio="pare-fill")
    
    def analisis_jerarquic(self, pid):
        if pid not in self.G:
            return {}
        try:
            ancestors = nx.ancestors(self.G, pid)
            descendants = nx.descendants(self.G, pid)
            predecessors = list(self.G.predecessors(pid))
            pare = predecessors[0] if predecessors else None
            fills = list(self.G.successors(pid))
            nivel = nx.shortest_path_length(self.G, '1', pid) if '1' in self.G else 0
        except:
            return {}
        return {
            'pare': pare,
            'fills': fills,
            'ancestors': list(ancestors),
            'descendants': list(descendants),
            'nivel': nivel,
            'total_context': len(ancestors) + len(descendants) + 1
        }
    
    def resaltar_context_interactiu(self):
        colors = []
        node_labels = {}
        for node in self.G.nodes():
            if node in self.processos_creats:
                colors.append('#00FF00')  # 🟢 VERD
                node_labels[node] = str(node)
            elif node in self.processos_eliminats:
                colors.append('#FF0000')  # 🔴 VERMELL
                node_labels[node] = str(node)
            elif node == self.pid_seleccionat:
                colors.append('#FFA500')  # 🟠 TARONJA
                node_labels[node] = str(node)
            else:
                colors.append('#87CEEB')  # 🔵 BLAU
                node_labels[node] = str(node)
        return colors, node_labels
    
    def setup_gui(self):
        control_frame = ttk.Frame(self.root)
        control_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Button(control_frame, text="Actualitzar", command=self.actualitzar_dades).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="Temps Real", command=self.toggle_realtemp_grafic).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="Gràfic", command=self.mostrar_grafic).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="Exportar", command=self.exportar_grafic).pack(side=tk.LEFT, padx=5)
        
        self.status_label = ttk.Label(control_frame, text=" Inicialitzant...")
        self.status_label.pack(side=tk.RIGHT)
        
        left_frame = ttk.LabelFrame(self.root, text="Processos Actius")
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(10,5), pady=5)
        
        columns = ('PID', 'PPID', 'CPU%', 'MEM%', 'ETIME', 'ESTAT', 'COMANDA')
        self.tree = ttk.Treeview(left_frame, columns=columns, show='headings', height=20)
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=90)
        
        v_scroll = ttk.Scrollbar(left_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=v_scroll.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        v_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.bind('<<TreeviewSelect>>', self.on_pid_select)
        
        right_frame = ttk.Frame(self.root)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5,10), pady=5)
        
        info_frame = ttk.LabelFrame(right_frame, text="Anàlisi Jeràrquica")
        info_frame.pack(fill=tk.X, pady=(0,5))
        self.info_text = tk.Text(info_frame, height=8, wrap=tk.WORD)
        self.info_text.pack(fill=tk.BOTH, padx=5, pady=5)
        
        modbus_frame = ttk.LabelFrame(right_frame, text="Modbus TCP Server")
        modbus_frame.pack(fill=tk.X, pady=(0,5))
        
        port_frame = ttk.Frame(modbus_frame)
        port_frame.pack(fill=tk.X, padx=5, pady=2)
        ttk.Label(port_frame, text="IP:").pack(side=tk.LEFT)
        self.ip_var = tk.StringVar(value="0.0.0.0")
        ttk.Entry(port_frame, textvariable=self.ip_var, width=12).pack(side=tk.LEFT, padx=5)
        
        if pymodbus_disponible:
            ttk.Button(modbus_frame, text=" Iniciar TCP", command=self.iniciar_modbus).pack(fill=tk.X, padx=5, pady=1)
            ttk.Button(modbus_frame, text=" Aturar TCP", command=self.aturar_modbus).pack(fill=tk.X, padx=5, pady=1)
            self.modbus_status = ttk.Label(modbus_frame, text=f"● Disponible ({pymodbus_version})", foreground="green")
        else:
            ttk.Label(modbus_frame, text="pymodbus no disponible", foreground="red").pack(fill=tk.X, padx=5, pady=5)
            self.modbus_status = ttk.Label(modbus_frame, text="● Offline", foreground="red")
        self.modbus_status.pack(pady=2)
        
        self.graph_frame = ttk.LabelFrame(right_frame, text="Gràf Interactiu PPID→PID")
        self.graph_frame.pack(fill=tk.BOTH, expand=True)
    
    def popular_treeview(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        if '1' in self.processos_actuals:
            root_info = self.processos_actuals['1']
            self.tree.insert('', 'end', values=(
                root_info['pid'], root_info['ppid'], root_info['cpu'], root_info['mem'], 
                root_info['etime'], root_info['estat'], root_info['comanda'][:15]
            ), open=True)
        if '1' in self.G:
            for fill in list(self.G.successors('1'))[:50]:
                if fill in self.processos_actuals:
                    info = self.processos_actuals[fill]
                    self.tree.insert('', 'end', values=(
                        info['pid'], info['ppid'], info['cpu'], info['mem'],
                        info['etime'], info['estat'], info['comanda'][:15]
                    ))
    
    def on_pid_select(self, event):
        selection = self.tree.selection()
        if selection:
            item = self.tree.item(selection[0])
            self.pid_seleccionat = item['values'][0]
            analisis = self.analisis_jerarquic(self.pid_seleccionat)
            info = self.mostrar_info_pid(self.pid_seleccionat, analisis)
            self.info_text.delete(1.0, tk.END)
            self.info_text.insert(1.0, info)
            self.mostrar_grafic()
    
    def mostrar_info_pid(self, pid, analisis):
        if pid not in self.processos_actuals and pid not in self.processos_anterior:
            return "PID no trobat"
        info = self.processos_actuals.get(pid, self.processos_anterior.get(pid, {}))
        text = f" PID ANALITZAT: {pid}\n"
        text += f"PPID: {info.get('ppid', 'N/A')} | USER: {info.get('user', 'N/A')}\n"
        text += f" CPU: {info.get('cpu', 'N/A')}% | MEM: {info.get('mem', 'N/A')}%\n"
        text += f"  ETIME: {info.get('etime', 'N/A')} | ESTAT: {info.get('estat', 'N/A')}\n"
        text += f" COMANDA: {info.get('comanda', 'N/A')}\n\n"
        text += f" JERARQUIA:\n"
        text += f"   Pare: {analisis.get('pare', 'ROOT')}\n"
        text += f"   Fills: {len(analisis.get('fills', []))}\n"
        text += f"   Nivell: {analisis.get('nivel', 0)}\n"
        text += f"   Context: {analisis.get('total_context', 0)} nodes"
        return text
    
    def actualitzar_dades(self):
        count = self.obtenir_processos_complet()
        self.construir_graf_dirigit_complet()
        self.popular_treeview()
        status = f" {count} processos | +{len(self.processos_creats)}🟢 -{len(self.processos_eliminats)}🔴"
        self.status_label.config(text=status)
    
    def toggle_realtemp_grafic(self):
        self.realtemp_actiu = not self.realtemp_actiu
        if self.realtemp_actiu:
            self.bucle_realtemp_grafic()
            self.status_label.config(text="🔴 TEMPS REAL + GRÀFIC (1.5s)")
        else:
            self.status_label.config(text="⏸ Temps real pausat")
    
    def bucle_realtemp_grafic(self):
        if self.realtemp_actiu:
            self.actualitzar_dades()
            self.mostrar_grafic()
            self.root.after(1500, self.bucle_realtemp_grafic)  # 1.5s per proves
    
    def mostrar_grafic(self):
        if not self.G.nodes():
            return
        for widget in self.graph_frame.winfo_children():
            widget.destroy()
        plt.close('all')
        
        fig = plt.figure(figsize=(10, 8))
        
        # Colors sincronitzats amb nodes del graf
        node_colors = []
        node_labels = {}
        
        for node in self.G.nodes():
            if node in self.processos_creats:
                node_colors.append('#00FF00')  # 🟢 VERD- NOUS
                node_labels[node] = str(node)
            elif node in self.processos_eliminats:
                node_colors.append('#FF0000')  # 🔴 VERMELLS- ELIMINATS
                node_labels[node] = str(node)
            elif node == self.pid_seleccionat:
                node_colors.append('#FFA500')  # 🟠 TARONJES - SELECCIONAT
                node_labels[node] = str(node)
            else:
                node_colors.append('#87CEEB')  # 🔵 BLAUS - NORMALS
                node_labels[node] = str(node)
        
        # Graf complet amb tots els nodes (verds, vermells, taronjes, blaus)
        pos = nx.spring_layout(self.G, k=1.5)
        
        nx.draw(
            self.G, pos,
            node_color=node_colors,
            node_size=1200,
            with_labels=False,
            arrows=True,
            font_size=8
        )
        
        nx.draw_networkx_labels(self.G, pos, node_labels)
        plt.title(f"Gràf Interactiu PPID→PID | +{len(self.processos_creats)}🟢 -{len(self.processos_eliminats)}🔴 | PID: {self.pid_seleccionat or 'Cap'}")
        
        canvas = FigureCanvasTkAgg(fig, self.graph_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        toolbar = NavigationToolbar2Tk(canvas, self.graph_frame)
        toolbar.update()
    
    def exportar_grafic(self):
        try:
            if not self.G.nodes():
                messagebox.showwarning("Avís", "No hi ha dades per exportar")
                return
            filename = f"graf_processos_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            plt.figure(figsize=(12, 9))
            
            node_colors = []
            node_labels = {}
            for node in self.G.nodes():
                if node in self.processos_creats:
                    node_colors.append('#00FF00')
                    node_labels[node] = str(node)
                elif node in self.processos_eliminats:
                    node_colors.append('#FF0000')
                    node_labels[node] = str(node)
                elif node == self.pid_seleccionat:
                    node_colors.append('#FFA500')
                    node_labels[node] = str(node)
                else:
                    node_colors.append('#87CEEB')
                    node_labels[node] = str(node)
            
            pos = nx.spring_layout(self.G, k=2)
            nx.draw(
                self.G, pos,
                node_color=node_colors,
                node_size=1500,
                with_labels=False,
                arrows=True,
                font_size=10,
                font_weight='bold'
            )
            nx.draw_networkx_labels(self.G, pos, node_labels)
            plt.title(f"Gràf Processos Interactiu - {datetime.now().strftime('%d/%m/%Y %H:%M')}", fontsize=14, fontweight='bold')
            plt.savefig(filename, dpi=300, bbox_inches='tight')
            plt.close()
            messagebox.showinfo("Exportat!", f"Guardat: {filename}")
        except Exception as e:
            messagebox.showerror("Error", f"Error exportant: {str(e)}")
    
    def iniciar_modbus(self):
        if not pymodbus_disponible:
            messagebox.showwarning("Avís", "pymodbus no disponible")
            return
        if not self.modbus_actiu:
            self.modbus_thread = threading.Thread(target=self.servidor_modbus_thread, daemon=True)
            self.modbus_thread.start()
            self.modbus_actiu = True
            self.modbus_status.config(text="● TCP ACTIU (Port 5020)", foreground="green")
    
    def aturar_modbus(self):
        self.modbus_actiu = False
        self.modbus_status.config(text="● Offline", foreground="red")
    
    def servidor_modbus_thread(self):
        global pymodbus_version
        try:
            # Auto-adaptar-se a la versió detectada
            from pymodbus.datastore import ModbusSequentialDataBlock, ModbusSlaveContext, ModbusServerContext
            
            store = ModbusSlaveContext(hr=ModbusSequentialDataBlock(0, [12345]*100))
            context = ModbusServerContext(slaves=store, single=True)
            
            if pymodbus_version == "4.x+":
                from pymodbus.server import start_tcp_server
                address = (self.ip_var.get(), 5020)
                print(f"🚀 Modbus TCP 4.x+ iniciat a {address}")
                start_tcp_server(context, address=address)
                
            elif pymodbus_version == "3.5+":
                from pymodbus.server.asynchronous import StartTcpServer
                from pymodbus.device import ModbusDeviceIdentification
                identity = ModbusDeviceIdentification()
                identity.VendorName = 'KaliProcessMonitor'
                StartTcpServer(context, identity=identity, address=(self.ip_var.get(), 5020))
                
            elif pymodbus_version == "3.0-3.4":
                from pymodbus.server import StartTcpServer
                from pymodbus.device import ModbusDeviceIdentification
                identity = ModbusDeviceIdentification()
                identity.VendorName = 'KaliProcessMonitor'
                identity.ProductName = 'ProcessTree_TCP'
                StartTcpServer(context=context, identity=identity, address=(self.ip_var.get(), 5020))
                
        except Exception as e:
            print(f"Modbus error: {e}")
    
    def executar(self):
        self.actualitzar_dades()
        self.root.mainloop()

def main():
    print("="*80)
    print("  MODEL PROCESSOS INTERACTIU TEMPS REAL + MODBUS TCP")
    print(f"  {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print("  Autor: Sergi Balsells - VSCode Python3 Kali Linux")
    print(" PYMODBUS AUTO-DETECTOR activat!")
    print("="*80)
    app = MonitorProcessosInteractiu()
    app.executar()

if __name__ == "__main__":
    main()
