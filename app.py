import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import psycopg2
from psycopg2 import extras

# =====================================================
# НАСТРОЙКИ ПОДКЛЮЧЕНИЯ (ИЗМЕНИ ПАРОЛЬ ТУТ!)
# =====================================================
DB_HOST = "localhost"
DB_NAME = "demo"  # Или имя твоей базы, если отличается
DB_USER = "student"
DB_PASS = "student"      # <--- ВПИШИ СЮДА СВОЙ ПАРОЛЬ

class FurnitureApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("ИС Производство мебели")
        self.geometry("1000x700")
        
        self.conn = None
        self.connect_db()

        # Создаем вкладки
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill='both', expand=True)

        # Вкладка 1: Таблицы (CRUD)
        self.tab_tables = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_tables, text="Таблицы (Справочники)")
        self.init_tables_tab()

        # Вкладка 2: Мастер-деталь (Создание заказа)
        self.tab_orders = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_orders, text="Оформление заказа")
        self.init_orders_tab()

        # Вкладка 3: Отчеты
        self.tab_reports = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_reports, text="Отчеты")
        self.init_reports_tab()

    def connect_db(self):
        try:
            self.conn = psycopg2.connect(
                host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASS
            )
        except Exception as e:
            messagebox.showerror("Ошибка БД", f"Не удалось подключиться к базе:\n{e}")

    # =====================================================
    # Вкладка 1: Работа с таблицами
    # =====================================================
    def init_tables_tab(self):
        frame_top = ttk.Frame(self.tab_tables, padding=10)
        frame_top.pack(fill='x')

        ttk.Label(frame_top, text="Выберите таблицу:").pack(side='left')
        
        self.tables_map = {
            "Материалы": "materials",
            "Комплектующие": "components",
            "Изделия": "products",
            "Сотрудники": "employees",
            "Заказы (Список)": "production_orders"
        }
        
        self.combo_table = ttk.Combobox(frame_top, values=list(self.tables_map.keys()), state="readonly")
        self.combo_table.current(0)
        self.combo_table.pack(side='left', padx=5)
        self.combo_table.bind("<<ComboboxSelected>>", self.load_table_data)

        ttk.Button(frame_top, text="Обновить", command=self.load_table_data).pack(side='left', padx=5)
        
        # Поиск
        ttk.Label(frame_top, text="Поиск:").pack(side='left', padx=10)
        self.entry_search = ttk.Entry(frame_top)
        self.entry_search.pack(side='left')
        ttk.Button(frame_top, text="Найти", command=self.search_data).pack(side='left', padx=2)

        # Таблица данных
        self.tree = ttk.Treeview(self.tab_tables, show='headings')
        self.tree.pack(fill='both', expand=True, padx=10, pady=5)
        
        # Кнопки управления
        frame_bot = ttk.Frame(self.tab_tables, padding=10)
        frame_bot.pack(fill='x')
        ttk.Button(frame_bot, text="Добавить запись", command=self.add_record).pack(side='left')
        ttk.Button(frame_bot, text="Удалить выбранное", command=self.delete_record).pack(side='left', padx=5)

    def get_current_table_sql(self):
        return self.tables_map[self.combo_table.get()]

    def load_table_data(self, event=None):
        table_name = self.get_current_table_sql()
        cur = self.conn.cursor()
        try:
            cur.execute(f"SELECT * FROM {table_name} ORDER BY 1")
            rows = cur.fetchall()
            colnames = [desc[0] for desc in cur.description]
        except Exception as e:
            messagebox.showerror("Ошибка", str(e))
            return

        self.tree.delete(*self.tree.get_children())
        self.tree["columns"] = colnames
        for col in colnames:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=100)

        for row in rows:
            self.tree.insert("", "end", values=row)

    def search_data(self):
        query = self.entry_search.get()
        if not query:
            self.load_table_data()
            return
            
        table_name = self.get_current_table_sql()
        # Примитивный поиск по текстовым полям (для демонстрации)
        # Ищем только если в таблице есть поле 'name' или похожие
        search_col = ""
        if "materials" in table_name: search_col = "material_name"
        elif "products" in table_name: search_col = "product_name"
        elif "employees" in table_name: search_col = "last_name"
        
        if not search_col:
            messagebox.showinfo("Поиск", "Поиск для этой таблицы не настроен в демо-версии")
            return

        cur = self.conn.cursor()
        sql = f"SELECT * FROM {table_name} WHERE {search_col} ILIKE %s"
        cur.execute(sql, (f"%{query}%",))
        rows = cur.fetchall()
        
        self.tree.delete(*self.tree.get_children())
        for row in rows:
            self.tree.insert("", "end", values=row)

    def delete_record(self):
        selected = self.tree.selection()
        if not selected:
            return
        
        if not messagebox.askyesno("Подтверждение", "Удалить запись?"):
            return

        item = self.tree.item(selected[0])
        id_val = item['values'][0] # Предполагаем, что ID всегда первый
        table_name = self.get_current_table_sql()
        pk_col = table_name[:-1] + "_id" # material_id, product_id...
        
        # Коррекция для orders
        if table_name == "production_orders": pk_col = "order_id"
        
        try:
            cur = self.conn.cursor()
            cur.execute(f"DELETE FROM {table_name} WHERE {pk_col} = %s", (id_val,))
            self.conn.commit()
            self.load_table_data()
        except Exception as e:
            messagebox.showerror("Ошибка", str(e))

    def add_record(self):
        messagebox.showinfo("Инфо", "В этой демо-версии добавление реализовано через прямые SQL запросы.\nДля полноценной работы нужна отдельная форма для каждой таблицы.")

    # =====================================================
    # Вкладка 2: Мастер-деталь (Создание заказа)
    # =====================================================
    def init_orders_tab(self):
        frame = ttk.Frame(self.tab_orders, padding=20)
        frame.pack(fill='both', expand=True)

        ttk.Label(frame, text="Создание нового заказа", font=("Arial", 14, "bold")).pack(pady=10)

        # 1. Выбор сотрудника
        ttk.Label(frame, text="Ответственный сотрудник (ID):").pack(anchor='w')
        self.order_emp_entry = ttk.Entry(frame)
        self.order_emp_entry.pack(fill='x', pady=5)
        self.order_emp_entry.insert(0, "1") # По умолчанию

        # 2. Дата дедлайна
        ttk.Label(frame, text="Дата сдачи (ГГГГ-ММ-ДД):").pack(anchor='w')
        self.order_date_entry = ttk.Entry(frame)
        self.order_date_entry.pack(fill='x', pady=5)
        self.order_date_entry.insert(0, "2023-12-31")

        # 3. Добавление товаров
        ttk.Label(frame, text="Список товаров (ID изделия и кол-во через пробел, например '1 5'):").pack(anchor='w', pady=(10,0))
        ttk.Label(frame, text="(Можно добавлять несколько строк)").pack(anchor='w', font=("Arial", 8))
        
        self.text_items = tk.Text(frame, height=5)
        self.text_items.pack(fill='x', pady=5)

        ttk.Button(frame, text="Оформить заказ", command=self.create_order).pack(pady=20)

    def create_order(self):
        emp_id = self.order_emp_entry.get()
        deadline = self.order_date_entry.get()
        items_raw = self.text_items.get("1.0", tk.END).strip().split('\n')

        if not items_raw or items_raw == ['']:
            messagebox.showwarning("Ошибка", "Укажите хотя бы один товар!")
            return

        try:
            cur = self.conn.cursor()
            # 1. Создаем заказ
            cur.execute("""
                INSERT INTO Production_Orders (deadline_date, assigned_employee_id, status)
                VALUES (%s, %s, 'Pending') RETURNING order_id
            """, (deadline, emp_id))
            new_order_id = cur.fetchone()[0]

            # 2. Добавляем позиции
            for line in items_raw:
                if not line.strip(): continue
                prod_id, qty = line.split()
                cur.execute("""
                    INSERT INTO Order_Items (order_id, product_id, quantity_to_produce)
                    VALUES (%s, %s, %s)
                """, (new_order_id, prod_id, qty))
            
            self.conn.commit()
            messagebox.showinfo("Успех", f"Заказ №{new_order_id} успешно создан!")
            self.text_items.delete("1.0", tk.END)
            
        except Exception as e:
            self.conn.rollback()
            messagebox.showerror("Ошибка создания заказа", str(e))

    # =====================================================
    # Вкладка 3: Отчеты
    # =====================================================
    def init_reports_tab(self):
        frame = ttk.Frame(self.tab_reports, padding=20)
        frame.pack(fill='both', expand=True)

        ttk.Label(frame, text="Генерация отчетов", font=("Arial", 12, "bold")).pack(pady=10)

        ttk.Button(frame, text="1. Себестоимость и рентабельность изделий", 
                   command=lambda: self.show_report_window("SELECT * FROM Products", "Финансы")).pack(fill='x', pady=5)

        ttk.Button(frame, text="2. Дефицит материалов (View)", 
                   command=lambda: self.show_report_window("SELECT * FROM v_low_stock", "Дефицит")).pack(fill='x', pady=5)

        ttk.Button(frame, text="3. Потребность материалов под заказы (SQL)", 
                   command=self.report_materials_needed).pack(fill='x', pady=5)

    def show_report_window(self, sql, title):
        top = tk.Toplevel(self)
        top.title(title)
        top.geometry("800x400")

        tree = ttk.Treeview(top, show='headings')
        tree.pack(fill='both', expand=True)
        
        cur = self.conn.cursor()
        cur.execute(sql)
        rows = cur.fetchall()
        colnames = [desc[0] for desc in cur.description]

        tree["columns"] = colnames
        for col in colnames:
            tree.heading(col, text=col)
            tree.column(col, width=100)
        
        for row in rows:
            tree.insert("", "end", values=row)

    def report_materials_needed(self):
        sql = """
        SELECT 
            m.material_name,
            SUM(pc.quantity * oi.quantity_to_produce) as needed,
            m.stock_quantity as in_stock,
            CASE WHEN m.stock_quantity >= SUM(pc.quantity * oi.quantity_to_produce) THEN 'OK' ELSE 'НЕДОСТАТОЧНО' END as status
        FROM Production_Orders po
        JOIN Order_Items oi ON po.order_id = oi.order_id
        JOIN Product_Composition pc ON oi.product_id = pc.product_id
        JOIN Materials m ON pc.material_id = m.material_id
        WHERE po.status IN ('Pending', 'In Progress')
        GROUP BY m.material_name, m.stock_quantity;
        """
        self.show_report_window(sql, "Потребность в материалах")

if __name__ == "__main__":
    app = FurnitureApp()
    app.mainloop()