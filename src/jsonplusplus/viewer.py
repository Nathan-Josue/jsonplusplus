"""
Visualiseur GUI pour les fichiers JSON++ (JONX).
Application desktop avec interface moderne.
"""

"""
Visualiseur GUI pour les fichiers JSON++ (JONX).
Nécessite customtkinter pour fonctionner.
"""

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import customtkinter as ctk
from pathlib import Path
import threading
from typing import Optional, List, Dict, Any
import csv
import json
import subprocess
import platform
import shutil

from . import JONXFile, JONXError


# Configuration de CustomTkinter
ctk.set_appearance_mode("light")  # Mode sombre par défaut
ctk.set_default_color_theme("blue")  # Thème bleu


def native_file_dialog(title: str = "Ouvrir un fichier", filetypes: Optional[List[tuple]] = None) -> Optional[str]:
    """Ouvre un dialogue de fichier natif du système.
    
    Args:
        title: Titre du dialogue
        filetypes: Liste de tuples (description, extensions)
        
    Returns:
        Chemin du fichier sélectionné ou None
    """
    system = platform.system()
    
    # Sur Linux, essayer d'utiliser zenity ou kdialog
    if system == "Linux":
        # Essayer zenity (GNOME/GTK)
        if shutil.which("zenity"):
            try:
                cmd = ["zenity", "--file-selection", "--title", title]
                
                # Ajouter les filtres de fichiers
                if filetypes:
                    for desc, exts in filetypes:
                        if exts != "*.*":
                            # Convertir "*.jonx *.json++" en "--file-filter=Fichiers JONX | *.jonx *.json++"
                            filter_str = f"{desc} | {exts}"
                            cmd.extend(["--file-filter", filter_str])
                
                result = subprocess.run(cmd, capture_output=True, text=True, check=True)
                file_path = result.stdout.strip()
                return file_path if file_path else None
            except (subprocess.CalledProcessError, Exception):
                pass
        
        # Essayer kdialog (KDE)
        elif shutil.which("kdialog"):
            try:
                cmd = ["kdialog", "--getopenfilename", str(Path.home()), ""]
                
                # Ajouter les filtres de fichiers
                if filetypes:
                    filters = []
                    for desc, exts in filetypes:
                        filters.append(f"{exts} | {desc}")
                    cmd[-1] = "\n".join(filters)
                
                result = subprocess.run(cmd, capture_output=True, text=True, check=True)
                file_path = result.stdout.strip()
                return file_path if file_path else None
            except (subprocess.CalledProcessError, Exception):
                pass
    
    # Fallback sur le dialogue tkinter standard
    return filedialog.askopenfilename(
        title=title,
        filetypes=filetypes if filetypes else [("Tous les fichiers", "*.*")]
    )


def native_save_dialog(title: str = "Enregistrer", defaultextension: str = "", filetypes: Optional[List[tuple]] = None) -> Optional[str]:
    """Ouvre un dialogue d'enregistrement natif du système.
    
    Args:
        title: Titre du dialogue
        defaultextension: Extension par défaut (ex: ".csv")
        filetypes: Liste de tuples (description, extensions)
        
    Returns:
        Chemin du fichier à enregistrer ou None
    """
    system = platform.system()
    
    # Sur Linux, essayer d'utiliser zenity ou kdialog
    if system == "Linux":
        # Essayer zenity (GNOME/GTK)
        if shutil.which("zenity"):
            try:
                cmd = ["zenity", "--file-selection", "--save", "--title", title, "--confirm-overwrite"]
                
                # Ajouter les filtres de fichiers
                if filetypes:
                    for desc, exts in filetypes:
                        if exts != "*.*":
                            filter_str = f"{desc} | {exts}"
                            cmd.extend(["--file-filter", filter_str])
                
                result = subprocess.run(cmd, capture_output=True, text=True, check=True)
                file_path = result.stdout.strip()
                
                # Ajouter l'extension si nécessaire
                if file_path and defaultextension and not file_path.endswith(defaultextension):
                    file_path += defaultextension
                
                return file_path if file_path else None
            except (subprocess.CalledProcessError, Exception):
                pass
        
        # Essayer kdialog (KDE)
        elif shutil.which("kdialog"):
            try:
                cmd = ["kdialog", "--getsavefilename", str(Path.home()), ""]
                
                # Ajouter les filtres de fichiers
                if filetypes:
                    filters = []
                    for desc, exts in filetypes:
                        filters.append(f"{exts} | {desc}")
                    cmd[-1] = "\n".join(filters)
                
                result = subprocess.run(cmd, capture_output=True, text=True, check=True)
                file_path = result.stdout.strip()
                
                # Ajouter l'extension si nécessaire
                if file_path and defaultextension and not file_path.endswith(defaultextension):
                    file_path += defaultextension
                
                return file_path if file_path else None
            except (subprocess.CalledProcessError, Exception):
                pass
    
    # Fallback sur le dialogue tkinter standard
    return filedialog.asksaveasfilename(
        title=title,
        defaultextension=defaultextension,
        filetypes=filetypes if filetypes else [("Tous les fichiers", "*.*")]
    )


class JONXViewer(ctk.CTk):
    """Application principale de visualisation JONX."""
    
    def __init__(self, initial_file: Optional[str] = None):
        super().__init__()
        
        self.jonx_file: Optional[JONXFile] = None
        self.current_data: List[Dict[str, Any]] = []
        self.filtered_data: List[Dict[str, Any]] = []
        self.current_page = 1
        self.rows_per_page = 100
        self.total_pages = 1
        
        self.setup_window()
        self.create_widgets()
        
        # Ouvrir un fichier si spécifié
        if initial_file:
            self.after(100, lambda: self.load_file(initial_file))
        
    def setup_window(self):
        """Configure la fenêtre principale."""
        self.title("JSON++ Viewer - Visualiseur JONX")
        self.geometry("1400x900")
        self.minsize(1000, 600)
        
        # Icône (si disponible)
        try:
            # self.iconbitmap("icon.ico")  # Décommenter si vous avez une icône
            pass
        except:
            pass
    
    def create_widgets(self):
        """Crée tous les widgets de l'interface."""
        # Menu bar
        self.create_menu_bar()
        
        # Layout principal
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        
        # Barre d'outils supérieure
        self.create_toolbar()
        
        # Panneau latéral (métadonnées)
        self.create_sidebar()
        
        # Zone principale (tableau de données)
        self.create_main_area()
        
        # Barre de statut
        self.create_status_bar()
    
    def create_menu_bar(self):
        """Crée la barre de menu."""
        menubar = tk.Menu(self)
        self.config(menu=menubar)
        
        # Menu Fichier
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Fichier", menu=file_menu)
        file_menu.add_command(label="Ouvrir...", command=self.open_file, accelerator="Ctrl+O")
        file_menu.add_separator()
        file_menu.add_command(label="Exporter en CSV...", command=self.export_csv)
        file_menu.add_command(label="Exporter en JSON...", command=self.export_json)
        file_menu.add_separator()
        file_menu.add_command(label="Quitter", command=self.quit, accelerator="Ctrl+Q")
        
        # Menu Affichage
        view_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Affichage", menu=view_menu)
        view_menu.add_command(label="Mode clair", command=lambda: ctk.set_appearance_mode("light"))
        view_menu.add_command(label="Mode sombre", command=lambda: ctk.set_appearance_mode("dark"))
        view_menu.add_separator()
        view_menu.add_command(label="Actualiser", command=self.refresh_data, accelerator="F5")
        
        # Menu Aide
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Aide", menu=help_menu)
        help_menu.add_command(label="À propos", command=self.show_about)
        
        # Raccourcis clavier
        self.bind("<Control-o>", lambda e: self.open_file())
        self.bind("<Control-q>", lambda e: self.quit())
        self.bind("<F5>", lambda e: self.refresh_data())
    
    def create_toolbar(self):
        """Crée la barre d'outils."""
        toolbar = ctk.CTkFrame(self)
        toolbar.grid(row=0, column=0, columnspan=2, sticky="ew", padx=10, pady=5)
        toolbar.grid_columnconfigure(1, weight=1)
        
        # Bouton Ouvrir
        open_btn = ctk.CTkButton(
            toolbar,
            text="📂 Ouvrir",
            command=self.open_file,
            width=120
        )
        open_btn.grid(row=0, column=0, padx=5)
        
        # Champ de recherche
        search_frame = ctk.CTkFrame(toolbar)
        search_frame.grid(row=0, column=1, sticky="ew", padx=10)
        search_frame.grid_columnconfigure(0, weight=1)
        
        self.search_var = ctk.StringVar()
        self.search_var.trace("w", lambda *args: self.filter_data())
        
        search_entry = ctk.CTkEntry(
            search_frame,
            textvariable=self.search_var,
            placeholder_text="Rechercher dans les données..."
        )
        search_entry.grid(row=0, column=0, sticky="ew", padx=5)
        
        # Bouton de recherche
        search_btn = ctk.CTkButton(
            search_frame,
            text="🔍",
            command=self.filter_data,
            width=40
        )
        search_btn.grid(row=0, column=1, padx=5)
        
        # Bouton Actualiser
        refresh_btn = ctk.CTkButton(
            toolbar,
            text="🔄 Actualiser",
            command=self.refresh_data,
            width=120
        )
        refresh_btn.grid(row=0, column=2, padx=5)
    
    def create_sidebar(self):
        """Crée le panneau latéral avec les métadonnées."""
        sidebar = ctk.CTkFrame(self, width=300)
        sidebar.grid(row=1, column=0, sticky="nsew", padx=(10, 5), pady=5)
        sidebar.grid_propagate(False)
        
        # Titre
        title = ctk.CTkLabel(sidebar, text="📊 Métadonnées", font=ctk.CTkFont(size=16, weight="bold"))
        title.pack(pady=10)
        
        # Scrollable frame pour les métadonnées
        scroll_frame = ctk.CTkScrollableFrame(sidebar)
        scroll_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Labels pour les métadonnées
        self.metadata_labels = {}
        metadata_fields = [
            ("Fichier", "path"),
            ("Version", "version"),
            ("Lignes", "num_rows"),
            ("Colonnes", "num_columns"),
            ("Taille", "file_size"),
        ]
        
        for label_text, key in metadata_fields:
            frame = ctk.CTkFrame(scroll_frame)
            frame.pack(fill="x", pady=5)
            
            label = ctk.CTkLabel(frame, text=f"{label_text}:", font=ctk.CTkFont(weight="bold"))
            label.pack(side="left", padx=5)
            
            value_label = ctk.CTkLabel(frame, text="-")
            value_label.pack(side="left", padx=5)
            self.metadata_labels[key] = value_label
        
        # Séparateur
        separator = ctk.CTkFrame(scroll_frame, height=2, fg_color="gray")
        separator.pack(fill="x", pady=10)
        
        # Liste des colonnes
        cols_title = ctk.CTkLabel(scroll_frame, text="Colonnes", font=ctk.CTkFont(size=14, weight="bold"))
        cols_title.pack(pady=5)
        
        self.columns_frame = ctk.CTkFrame(scroll_frame)
        self.columns_frame.pack(fill="both", expand=True)
        
        # Statistiques
        stats_title = ctk.CTkLabel(scroll_frame, text="Statistiques", font=ctk.CTkFont(size=14, weight="bold"))
        stats_title.pack(pady=(10, 5))
        
        self.stats_frame = ctk.CTkFrame(scroll_frame)
        self.stats_frame.pack(fill="both", expand=True)
    
    def create_main_area(self):
        """Crée la zone principale avec le tableau de données."""
        main_frame = ctk.CTkFrame(self)
        main_frame.grid(row=1, column=1, sticky="nsew", padx=(5, 10), pady=5)
        main_frame.grid_columnconfigure(0, weight=1)
        main_frame.grid_rowconfigure(1, weight=1)
        
        # Titre
        title = ctk.CTkLabel(main_frame, text="📋 Données", font=ctk.CTkFont(size=16, weight="bold"))
        title.grid(row=0, column=0, pady=10)
        
        # Frame pour le tableau avec scrollbars - largeur fixe avec scroll horizontal
        table_frame = ctk.CTkFrame(main_frame, width=800)
        table_frame.grid(row=1, column=0, sticky="ns", padx=10, pady=5)
        table_frame.grid_propagate(False)  # Empêche le frame de s'agrandir automatiquement
        table_frame.grid_columnconfigure(0, weight=1)
        table_frame.grid_rowconfigure(0, weight=1)
        
        # Treeview pour le tableau
        self.tree = ttk.Treeview(table_frame, show="headings", selectmode="browse")
        
        # Scrollbars
        v_scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        h_scrollbar = ttk.Scrollbar(table_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        
        # Grid layout
        self.tree.grid(row=0, column=0, sticky="nsew")
        v_scrollbar.grid(row=0, column=1, sticky="ns")
        h_scrollbar.grid(row=1, column=0, sticky="ew")
        
        table_frame.grid_columnconfigure(0, weight=1)
        table_frame.grid_rowconfigure(0, weight=1)
        
        # Pagination
        self.create_pagination(main_frame)
    
    def create_pagination(self, parent):
        """Crée les contrôles de pagination."""
        pagination_frame = ctk.CTkFrame(parent)
        pagination_frame.grid(row=2, column=0, pady=10)
        
        # Bouton Précédent
        self.prev_btn = ctk.CTkButton(
            pagination_frame,
            text="◀ Précédent",
            command=self.prev_page,
            width=100,
            state="disabled"
        )
        self.prev_btn.pack(side="left", padx=5)
        
        # Label page
        self.page_label = ctk.CTkLabel(
            pagination_frame,
            text="Page 1 / 1",
            font=ctk.CTkFont(size=12)
        )
        self.page_label.pack(side="left", padx=10)
        
        # Bouton Suivant
        self.next_btn = ctk.CTkButton(
            pagination_frame,
            text="Suivant ▶",
            command=self.next_page,
            width=100,
            state="disabled"
        )
        self.next_btn.pack(side="left", padx=5)
        
        # Sélecteur de lignes par page
        rows_label = ctk.CTkLabel(pagination_frame, text="Lignes/page:")
        rows_label.pack(side="left", padx=(20, 5))
        
        self.rows_var = ctk.StringVar(value="100")
        rows_combo = ctk.CTkComboBox(
            pagination_frame,
            values=["50", "100", "200", "500", "1000"],
            variable=self.rows_var,
            command=self.change_rows_per_page,
            width=80
        )
        rows_combo.pack(side="left", padx=5)
    
    def create_status_bar(self):
        """Crée la barre de statut."""
        status_frame = ctk.CTkFrame(self)
        status_frame.grid(row=2, column=0, columnspan=2, sticky="ew", padx=10, pady=5)
        status_frame.grid_columnconfigure(0, weight=1)
        
        self.status_label = ctk.CTkLabel(
            status_frame,
            text="Prêt - Ouvrez un fichier JONX pour commencer",
            anchor="w"
        )
        self.status_label.grid(row=0, column=0, sticky="ew", padx=10, pady=5)
    
    def open_file(self):
        """Ouvre un fichier JONX."""
        file_path = native_file_dialog(
            title="Ouvrir un fichier JONX",
            filetypes=[
                ("Fichiers JONX", "*.jonx *.json++"),
                ("Tous les fichiers", "*.*")
            ]
        )
        
        if file_path:
            self.load_file(file_path)
    
    def load_file(self, file_path: str):
        """Charge un fichier JONX."""
        self.status_label.configure(text=f"Chargement de {Path(file_path).name}...")
        self.update()
        
        try:
            # Charger le fichier dans un thread pour ne pas bloquer l'UI
            def load_thread():
                try:
                    self.jonx_file = JONXFile(file_path)
                    info = self.jonx_file.info()
                    
                    # Charger les données
                    result = self.jonx_file.get_columns(self.jonx_file.fields)
                    
                    # Reconstruire les données ligne par ligne
                    num_rows = len(result[self.jonx_file.fields[0]]) if self.jonx_file.fields else 0
                    data = []
                    for i in range(num_rows):
                        row = {field: result[field][i] for field in self.jonx_file.fields}
                        data.append(row)
                    
                    # Mettre à jour l'UI dans le thread principal
                    self.after(0, lambda: self.on_file_loaded(info, data))
                    
                except JONXError as e:
                    self.after(0, lambda: messagebox.showerror("Erreur", f"Erreur lors du chargement:\n{str(e)}"))
                except Exception as e:
                    self.after(0, lambda: messagebox.showerror("Erreur", f"Erreur inattendue:\n{str(e)}"))
            
            threading.Thread(target=load_thread, daemon=True).start()
            
        except Exception as e:
            messagebox.showerror("Erreur", f"Impossible de charger le fichier:\n{str(e)}")
            self.status_label.configure(text="Erreur lors du chargement")
    
    def on_file_loaded(self, info: Dict, data: List[Dict]):
        """Appelé quand le fichier est chargé."""
        self.current_data = data
        self.filtered_data = data.copy()
        
        # Mettre à jour les métadonnées
        self.update_metadata(info)
        
        # Mettre à jour le tableau
        self.update_table()
        
        # Mettre à jour la pagination
        self.update_pagination()
        
        # Mettre à jour les statistiques
        self.update_statistics()
        
        self.status_label.configure(text=f"Fichier chargé: {info['num_rows']:,} lignes, {info['num_columns']} colonnes")
    
    def update_metadata(self, info: Dict):
        """Met à jour l'affichage des métadonnées."""
        # Métadonnées de base
        self.metadata_labels["path"].configure(text=Path(info["path"]).name)
        self.metadata_labels["version"].configure(text=str(info["version"]))
        self.metadata_labels["num_rows"].configure(text=f"{info['num_rows']:,}")
        self.metadata_labels["num_columns"].configure(text=str(info["num_columns"]))
        
        # Taille du fichier
        file_size = info.get("file_size", 0)
        if file_size:
            size_str = self.format_size(file_size)
            self.metadata_labels["file_size"].configure(text=size_str)
        else:
            self.metadata_labels["file_size"].configure(text="-")
        
        # Colonnes
        for widget in self.columns_frame.winfo_children():
            widget.destroy()
        
        for field in info["fields"]:
            col_type = info["types"].get(field, "?")
            has_index = "✓" if field in info["indexes"] else " "
            
            frame = ctk.CTkFrame(self.columns_frame)
            frame.pack(fill="x", pady=2, padx=5)
            
            label = ctk.CTkLabel(
                frame,
                text=f"[{has_index}] {field}",
                font=ctk.CTkFont(size=11)
            )
            label.pack(side="left", padx=5)
            
            type_label = ctk.CTkLabel(
                frame,
                text=f"({col_type})",
                font=ctk.CTkFont(size=10),
                text_color="gray"
            )
            type_label.pack(side="right", padx=5)
    
    def update_table(self):
        """Met à jour le tableau de données."""
        # Vider le tableau
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        if not self.jonx_file or not self.filtered_data:
            return
        
        # Configurer les colonnes
        columns = self.jonx_file.fields
        self.tree["columns"] = columns
        
        # Configurer les en-têtes
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=150, minwidth=100)
        
        # Calculer la plage de données à afficher
        start_idx = (self.current_page - 1) * self.rows_per_page
        end_idx = start_idx + self.rows_per_page
        page_data = self.filtered_data[start_idx:end_idx]
        
        # Ajouter les lignes
        for row_data in page_data:
            values = [str(row_data.get(col, "")) for col in columns]
            # Tronquer les valeurs longues
            values = [v[:100] + "..." if len(v) > 100 else v for v in values]
            self.tree.insert("", "end", values=values)
    
    def update_pagination(self):
        """Met à jour les contrôles de pagination."""
        if not self.filtered_data:
            self.total_pages = 1
            self.current_page = 1
        else:
            self.total_pages = max(1, (len(self.filtered_data) + self.rows_per_page - 1) // self.rows_per_page)
            if self.current_page > self.total_pages:
                self.current_page = self.total_pages
        
        # Mettre à jour le label
        self.page_label.configure(text=f"Page {self.current_page} / {self.total_pages}")
        
        # Activer/désactiver les boutons
        self.prev_btn.configure(state="normal" if self.current_page > 1 else "disabled")
        self.next_btn.configure(state="normal" if self.current_page < self.total_pages else "disabled")
    
    def update_statistics(self):
        """Met à jour les statistiques."""
        for widget in self.stats_frame.winfo_children():
            widget.destroy()
        
        if not self.jonx_file:
            return
        
        # Calculer les statistiques pour les colonnes numériques
        for field in self.jonx_file.fields:
            if self.jonx_file.is_numeric(field):
                try:
                    col = self.jonx_file.get_column(field)
                    if col:
                        min_val = self.jonx_file.find_min(field, use_index=True)
                        max_val = self.jonx_file.find_max(field, use_index=True)
                        avg_val = self.jonx_file.avg(field)
                        
                        stats_text = f"{field}:\n  Min: {min_val}\n  Max: {max_val}\n  Moy: {avg_val:.2f}"
                        
                        stats_label = ctk.CTkLabel(
                            self.stats_frame,
                            text=stats_text,
                            font=ctk.CTkFont(size=10),
                            anchor="w",
                            justify="left"
                        )
                        stats_label.pack(fill="x", pady=2, padx=5)
                except:
                    pass
    
    def filter_data(self):
        """Filtre les données selon la recherche."""
        search_term = self.search_var.get().lower()
        
        if not search_term:
            self.filtered_data = self.current_data.copy()
        else:
            self.filtered_data = [
                row for row in self.current_data
                if any(search_term in str(value).lower() for value in row.values())
            ]
        
        self.current_page = 1
        self.update_table()
        self.update_pagination()
        self.status_label.configure(
            text=f"{len(self.filtered_data):,} lignes affichées (sur {len(self.current_data):,} totales)"
        )
    
    def prev_page(self):
        """Page précédente."""
        if self.current_page > 1:
            self.current_page -= 1
            self.update_table()
            self.update_pagination()
    
    def next_page(self):
        """Page suivante."""
        if self.current_page < self.total_pages:
            self.current_page += 1
            self.update_table()
            self.update_pagination()
    
    def change_rows_per_page(self, value):
        """Change le nombre de lignes par page."""
        try:
            self.rows_per_page = int(value)
            self.current_page = 1
            self.update_table()
            self.update_pagination()
        except:
            pass
    
    def refresh_data(self):
        """Actualise les données."""
        if self.jonx_file:
            self.load_file(self.jonx_file.path)
    
    def export_csv(self):
        """Exporte les données en CSV."""
        if not self.filtered_data:
            messagebox.showwarning("Avertissement", "Aucune donnée à exporter")
            return
        
        file_path = native_save_dialog(
            title="Exporter en CSV",
            defaultextension=".csv",
            filetypes=[("CSV", "*.csv"), ("Tous les fichiers", "*.*")]
        )
        
        if file_path:
            try:
                with open(file_path, 'w', newline='', encoding='utf-8') as f:
                    if self.jonx_file and self.jonx_file.fields:
                        writer = csv.DictWriter(f, fieldnames=self.jonx_file.fields)
                        writer.writeheader()
                        writer.writerows(self.filtered_data)
                
                messagebox.showinfo("Succès", f"Données exportées vers {file_path}")
            except Exception as e:
                messagebox.showerror("Erreur", f"Erreur lors de l'export:\n{str(e)}")
    
    def export_json(self):
        """Exporte les données en JSON."""
        if not self.filtered_data:
            messagebox.showwarning("Avertissement", "Aucune donnée à exporter")
            return
        
        file_path = native_save_dialog(
            title="Exporter en JSON",
            defaultextension=".json",
            filetypes=[("JSON", "*.json"), ("Tous les fichiers", "*.*")]
        )
        
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(self.filtered_data, f, indent=2, ensure_ascii=False)
                
                messagebox.showinfo("Succès", f"Données exportées vers {file_path}")
            except Exception as e:
                messagebox.showerror("Erreur", f"Erreur lors de l'export:\n{str(e)}")
    
    def show_about(self):
        """Affiche la boîte À propos."""
        about_text = """JSON++ Viewer v1.0.7

Visualiseur pour les fichiers JONX (JSON++)

Développé pour jsonplusplus
© 2024 Nathan Josué

Licence: MIT"""
        messagebox.showinfo("À propos", about_text)
    
    @staticmethod
    def format_size(size_bytes: int) -> str:
        """Formate une taille en bytes."""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} TB"


def main(initial_file: Optional[str] = None):
    """Point d'entrée principal du visualiseur.
    
    Args:
        initial_file: Chemin vers un fichier JONX à ouvrir automatiquement (optionnel)
    """
    import os
    
    # Vérifier si un fichier est passé via variable d'environnement
    if not initial_file:
        initial_file = os.environ.get('JONX_VIEWER_FILE')
    
    app = JONXViewer(initial_file=initial_file)
    app.mainloop()


if __name__ == "__main__":
    main()

