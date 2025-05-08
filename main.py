import requests
from bs4 import BeautifulSoup
import tkinter as tk
from tkinter import ttk, filedialog
import threading
import pandas as pd
from sqlalchemy import create_engine
from datetime import datetime

class IMFData:
    
    def __init__(self):
        
        self.window = tk.Tk()
        
        self.window.title("IMF Data")
        
        self.key_family_id = ""
        
        self.attributes = {}
        
        self.info_labels = {}
        
        self.datastructures = None
        
        self.dataflows = None
        
        self.structures_frame = None
        
        self.button_visible = False
        
        self.fetch_button = None
        
        self.display_data = None
        
        self.current_index = 0
        
        self.set_dataflows()

    def fetch_dataflows(self):
        """Fetches Dataflow names and KeyFamilyIDs from the IMF API (runs in a thread)."""
        url = "http://dataservices.imf.org/REST/SDMX_XML.svc/Dataflow"
        try:
            response = requests.get(url)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, "xml")
            dataflows_data = []
            for dataflow in soup.find_all("Dataflow"):
                name_element = dataflow.find("Name")
                key_family_id_element = dataflow.find("KeyFamilyID")
                if name_element and key_family_id_element:
                    dataflows_data.append({
                        "name": name_element.text,
                        "key_family_id": key_family_id_element.text
                    })
            sorted_dataflows = sorted(dataflows_data, key=lambda item: item['name'])
            self.dataflows = sorted_dataflows
            self.window.after(0, self.populate_dataflows)
        except requests.RequestException as e:
            print(f"Error fetching dataflows: {e}")

    def set_dataflows(self):
        """Creates a Listbox with a Scrollbar and spawns a thread to load dataflows."""
        listbox_frame = tk.Frame(self.window)
        listbox_frame.pack(pady=10, padx=10, fill=tk.BOTH, expand=True)

        self.listbox = tk.Listbox(listbox_frame, width=50)
        self.listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = tk.Scrollbar(listbox_frame, orient="vertical", command=self.listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.listbox.config(yscrollcommand=scrollbar.set)

        threading.Thread(target=self.fetch_dataflows).start()
        self.window.mainloop()

        
    def populate_dataflows(self):
        """Populates the listbox with the fetched dataflows."""
        self.listbox.delete(0, tk.END)
        for dataflow in self.dataflows:
            self.listbox.insert(tk.END, dataflow["name"])
        self.listbox.bind('<Double-Button-1>', lambda event: self.on_dataflow_select(event, self.listbox))


    def on_dataflow_select(self, event, listbox):
        """Handles the double-click event on the Dataflow Listbox."""
        selected_index = listbox.curselection()
        if selected_index:
            selected_dataflow = self.dataflows[selected_index[0]]
            self.key_family_id = selected_dataflow["key_family_id"]
            self.set_datastructures()
    
    def fetch_datastructures(self):
        """Fetches data structures (codelists and codes) for a given KeyFamilyID."""
        if not self.key_family_id:
            print("Error: key_family_id is not set.")
            return {}

        url = f"http://dataservices.imf.org/REST/SDMX_XML.svc/DataStructure/{self.key_family_id}"
        
        try:
            response = requests.get(url)
            response.raise_for_status() 
            soup = BeautifulSoup(response.content, "xml")
            codelists = soup.find_all("CodeList")
            ids = {"CL_FREQ", f"CL_INDICATOR_{self.key_family_id}", f"CL_AREA_{self.key_family_id}"}
            for id in ids:
                self.attributes[id] = []
            datastructures = {}
            for codelist in codelists:
                codelist_id = codelist["id"]
                if codelist_id in ids:
                    ids.discard(codelist_id) 
                    codes = codelist.find_all("Code")
                    datastructures[codelist_id] = [{"Description": code.find("Description").text, "value": code["value"]} for code in codes]
            self.datastructures = datastructures
        except requests.exceptions.RequestException as e:
            print(f"Error fetching data structures: {e}")
            self.datastructures = {}
    
    def set_datastructures(self):
        """Manages fetching datastructures from API and initiating updating the GUI"""
        self.attributes = {}
        
        if self.fetch_button is not None:
            self.fetch_button.destroy()
            self.fetch_button = None
        
        def task():
            self.fetch_datastructures()
            self.window.after(0, self.populate_datastructures)
            
        threading.Thread(target=task).start()
        
    def populate_datastructures(self):
        """Creates scrollable columns (Listboxes) for each Codelist in datastructures."""
        if not self.datastructures:
            label = tk.Label(self.window, text="No data structures to display or error fetching.")
            label.pack(pady=10, padx=10)
            return

        if self.structures_frame is not None:
            self.structures_frame.destroy()

        self.structures_frame = tk.Frame(self.window)
        self.structures_frame.pack(fill=tk.BOTH, expand=True)
        
        self.structures_frame.columnconfigure(0, weight=1)
        self.structures_frame.columnconfigure(1, weight=1)
        self.structures_frame.columnconfigure(2, weight=1) 
        
        left_frame = tk.Frame(self.structures_frame)
        left_frame.grid(row=0, column=0, sticky="nsew") 
        
        top_frame = tk.Frame(left_frame)
        top_frame.grid(row=0, column=0, sticky="nw", padx=5, pady=0)

        bottom_frame = tk.Frame(left_frame)
        bottom_frame.grid(row=1, column=0, sticky="nw", padx=5, pady=(10, 0))

        for index, (key, value_list) in enumerate(self.datastructures.items()):
            
            if index < 2:
                parent = top_frame
                width=30
            else:
                parent = bottom_frame
                width=90
            
            col_frame = tk.Frame(parent)
            col_frame.pack(side=tk.LEFT if index < 2 else tk.TOP, fill=tk.Y if index < 2 else tk.BOTH, expand=True, padx=5, pady=0)

            label = tk.Label(col_frame, text=key, font=("Arial", 10, "bold"))
            label.pack(pady=(0, 5))

            listbox_frame = tk.Frame(col_frame)
            listbox_frame.pack()

            scrollbar = tk.Scrollbar(listbox_frame)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

            listbox = tk.Listbox(listbox_frame, width=width, yscrollcommand=scrollbar.set)
            for item in value_list:
                listbox.insert(tk.END, f"{item['Description']}, {item['value']}")
            listbox.pack(side=tk.LEFT, fill=tk.Y)
            listbox.bind('<Double-Button-1>', lambda event, lb=listbox, k=key: self.on_datastructure_select(event, lb, k))

            scrollbar.config(command=listbox.yview)

            text = ", ".join(self.attributes[key])
            info_label = tk.Label(col_frame, text=text, fg="blue", font=("Arial", 9), justify="left", wraplength=200)
            info_label.pack(pady=(5, 0))
            self.info_labels[key] = info_label
    
    def on_datastructure_select(self, event, listbox, key):
        """"Handles double-click event on either of the datastructure items, keeping track of relevant selections"""
        selected_index = listbox.curselection()
        chosen = self.attributes[key]
        selected = self.datastructures[key][selected_index[0]]
        if selected in chosen:
            chosen.remove(selected)
        else:
            self.attributes[key].append(selected)
        text = ", ".join([ f"{_["Description"]}, ({_["value"]})" for _ in self.attributes[key] ])
        self.info_labels[key].config(text=text)
        
        if self.attributes["CL_INDICATOR_" + self.key_family_id] and not self.fetch_button:
            self.fetch_button = tk.Button(self.window, text="Fetch data", font=("Arial", 9), command=self.fetch_data)
            self.fetch_button.pack(side=tk.LEFT, anchor="sw", padx=250, pady=10)
        elif not self.attributes["CL_INDICATOR_" + self.key_family_id] and self.fetch_button:
            self.fetch_button.destroy()
            self.fetch_button = None
            
    def fetch_data(self):
        """Fetches chosen datasets"""
        def task():
            self._fetch_data_thread()
            self.window.after(0,self.populate_datadisplay)
        threading.Thread(target=task).start()

    def _fetch_data_thread(self):
        """"Fetches de selected dataset"""
        print("fetching data")
        freq = "+".join([self.attributes["CL_FREQ"][_]["value"] for _ in range(len(self.attributes["CL_FREQ"]))])
        area = "+".join([self.attributes["CL_AREA_" + self.key_family_id][_]["value"] for _ in range(len(self.attributes["CL_AREA_" + self.key_family_id]))])
        indicator = "+".join(self.attributes["CL_INDICATOR_" + self.key_family_id][_]["value"] for _ in range(len(self.attributes["CL_INDICATOR_" + self.key_family_id])))
        url = f"http://dataservices.imf.org/REST/SDMX_XML.svc/CompactData/{self.key_family_id}/{freq}.{area}.{indicator}"
        try:
            response = requests.get(url, timeout=10)
            soup = BeautifulSoup(response.content, "xml")
            series = soup.find_all("Series")
            output = []
            for serie in series:
                
                obs = serie.find_all("Obs")
                
                data = [{
                    "Frequency" : serie.get("FREQ"),
                    "Area" : serie.get("REF_AREA"),
                    "Indicator" : serie.get("INDICATOR")
                }]
                
                data += [{
                     "Value": o.get("OBS_VALUE"), 
                     "Timeperiod": o.get("TIME_PERIOD")} 
                    for o in obs]
                df = pd.DataFrame(data)
                output.append(df)
            self.display_data = output
                
        except requests.exceptions.RequestException as e:
            print(f"Error fetching data: {e}")

    def populate_datadisplay(self):
        """Generate Listbox and relevant buttons for showcasing various datasets and saving them"""
        if hasattr(self, "data_frame") and self.data_frame:
            self.data_frame.destroy()
            
        self.data_frame = tk.Frame(self.structures_frame)
        self.data_frame.grid(row=0, column=2, sticky="nsew", padx=10)

        label = tk.Label(self.data_frame, text="Fetched Data", font=("Arial", 10, "bold"))
        label.pack()
        
        tree_frame = tk.Frame(self.data_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True)

        self.tree = ttk.Treeview(tree_frame, columns=["Timeperiod", "Value"], show="headings")
        self.tree.heading("Timeperiod", text="Timeperiod")
        self.tree.heading("Value", text="Value")
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = tk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        scrollbar.pack(side=tk.RIGHT, fill="y")
        self.tree.config(yscrollcommand=scrollbar.set)
        
        self.tree_label = tk.Label(self.data_frame, text="", font=("Arial", 10))
        self.tree_label.pack(pady=5)

        nav_frame = tk.Frame(self.data_frame)
        nav_frame.pack(pady=5)

        prev_button = tk.Button(nav_frame, text="Previous", command=self.show_previous_dataset)
        prev_button.pack(side=tk.LEFT, padx=5)

        next_button = tk.Button(nav_frame, text="Next", command=self.show_next_dataset)
        next_button.pack(side=tk.LEFT, padx=5)
        
        save_frame = tk.Frame(self.data_frame)
        save_frame.pack(pady=(10, 5))

        sql_button = tk.Button(save_frame, text="Save to MySQL", command=self.prompt_mysql_credentials)
        sql_button.pack(side=tk.LEFT, padx=5)

        csv_button = tk.Button(save_frame, text="Save to CSV", command=self.prompt_csv_name)
        csv_button.pack(side=tk.LEFT, padx=5)

        self.update_treeview()
        
    def update_treeview(self):
        """Update the shown dataset"""
        for row in self.tree.get_children():
            self.tree.delete(row)

        if self.display_data:
            df = self.display_data[self.current_index]
            print(df.iloc[0])
            freq = df.iloc[0]["Frequency"]
            area = df.iloc[0]["Area"]
            indicator = df.iloc[0]["Indicator"]
            self.tree_label.config(text=f"{freq}_{area}_{indicator}")
            for _, row in df.iterrows():
                self.tree.insert("", tk.END, values=(row["Timeperiod"], row["Value"]))
                
    def show_next_dataset(self):
        """Updating index for next dataset"""
        if self.display_data and self.current_index < len(self.display_data) - 1:
            self.current_index += 1
            self.update_treeview()

    def show_previous_dataset(self):
        """Updating index for previous dataset"""
        if self.display_data and self.current_index > 0:
            self.current_index -= 1
            self.update_treeview()
            
    def prompt_mysql_credentials(self):
        """Ask for relevant informatio to set up mySQL server and save the dataset"""
        top = tk.Toplevel(self.window)
        top.title("MySQL Credentials")

        tk.Label(top, text="Host:").grid(row=0, column=0)
        host_entry = tk.Entry(top)
        host_entry.insert(0, "127.0.0.1")
        host_entry.grid(row=0, column=1)

        tk.Label(top, text="User:").grid(row=1, column=0)
        user_entry = tk.Entry(top)
        user_entry.grid(row=1, column=1)

        tk.Label(top, text="Password:").grid(row=2, column=0)
        password_entry = tk.Entry(top, show="*")
        password_entry.grid(row=2, column=1)

        tk.Label(top, text="Database:").grid(row=3, column=0)
        db_entry = tk.Entry(top)
        db_entry.grid(row=3, column=1)
        
        tk.Label(top, text="Table name:").grid(row=4, column=0)
        db_table_name = tk.Entry(top)
        db_table_name.grid(row=4, column=1)

        def submit():
            host = host_entry.get()
            user = user_entry.get()
            password = password_entry.get()
            database = db_entry.get()
            table_name = db_table_name.get()
            top.destroy()
            self.save_to_mysql(host=host, user=user, password=password, database=database, table_name=table_name)

        tk.Button(top, text="Submit", command=submit).grid(row=5, column=0, columnspan=2, pady=5)
    
    def save_to_mysql(self, host='localhost', user='your_user', password='your_password', database='your_db', table_name='your_table_name'):
        """Prepares dataset for saving to MySQL and then saves it"""
        if not self.display_data:
            print("No data to save.")
            return

        try:
            engine = create_engine(f"mysql+pymysql://{user}:{password}@{host}/{database}")
            df = self.display_data[self.current_index]
            df = df.drop(0, axis=0).reset_index(drop=True) 
            df = df.drop(columns=["Frequency", "Area", "Indicator"]) 
            df.to_sql(name=table_name, con=engine, if_exists='replace', index=False)
        except Exception as e:
            print(f"Error saving to MySQL: {e}")
            
    def prompt_csv_name(self):
        """Asks for the name under which dataset csv file is to be saved"""
        top = tk.Toplevel(self.window)
        
        label = tk.Label(top, text="File name:")
        label.grid(row=0, column=0, pady=5, padx=5)
        
        entry = tk.Entry(top)
        entry.grid(row=0, column=1, pady=5, padx=5)
        
        def submit():
            name = entry.get()
            top.destroy()
            self.save_to_csv(name)
        
        button = tk.Button(top, text="Submit", command=submit)
        button.grid(row=1, column=0, columnspan=2, pady=5, padx=5)
            
    def save_to_csv(self, name=f"imf_data_{datetime.now()}"):
        """Prepares dataset and saves it to csv"""
        if not self.display_data:
            print("No data to save.")
            return
        
        folderpath = filedialog.askdirectory(title="Select Folder to Save CSV")
        print(f"Selected folder: {folderpath}")
        
        if folderpath:  
            try:
                filepath = f"{folderpath}/{name}.csv"
                df = self.display_data[self.current_index]
                print("Saving DataFrame with shape:", df.shape)
                df = df.drop(0, axis=0).reset_index(drop=True).copy()
                df = df.drop(columns=["Frequency", "Area", "Indicator"]) 
                df.to_csv(filepath, index=False)
                print(f"Data saved to {filepath}")
            except Exception as e:
                print(f"Error saving CSV: {e}")
        else:
            print("No folder selected.")

if __name__ == "__main__":
    app = IMFData()
