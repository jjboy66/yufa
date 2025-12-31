"""
C 语言编译器实验 - 语法分析 (修复行号同步版)
"""
import tkinter as tk
from tkinter import filedialog, scrolledtext, messagebox, ttk, font
from lexer_core import Lexer, TYPES, STRING_, CONST_CHAR, EOF
try:
    from parser_core import LL1Parser
except ImportError:
    LL1Parser = None

class LexerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("C 语言编译器实验 - 语法分析表生成")
        self.geometry("1400x850")
        self.text_font = font.Font(family="Consolas", size=10) 
        self.header_font = font.Font(family="Microsoft YaHei", size=11, weight="bold")
        self.create_widgets()

    def create_widgets(self):
        top_frame = ttk.Frame(self, padding="10")
        top_frame.pack(fill='x')

        ttk.Button(top_frame, text="加载 C 文件", command=self.load_file).pack(side='left', padx=5)
        ttk.Button(top_frame, text="运行词法分析", command=self.run_analysis).pack(side='left', padx=5)
        ttk.Button(top_frame, text="生成语法分析表", command=self.run_parser).pack(side='left', padx=5)
        ttk.Button(top_frame, text="生成预测分析表", command=self.on_gen_predict_table_clicked).pack(side='left', padx=5)
        ttk.Button(top_frame, text="清除全部", command=self.clear_all).pack(side='right', padx=5)
        ttk.Button(top_frame, text="执行并导出词法 TXT", command=self.save_txt_as).pack(side='left', padx=5)
        ttk.Button(top_frame, text="执行并导出语法 Excel", command=self.save_xlsx_as).pack(side='left', padx=5)
        ttk.Button(top_frame, text="执行并导出预测分析 Excel", command=self.save_prediction_table).pack(side='left', padx=5)

        self.paned_window = ttk.PanedWindow(self, orient='horizontal')
        self.paned_window.pack(fill='both', expand=True, padx=10, pady=10)

        # --- 左侧：代码输入区 ---
        input_frame = ttk.Frame(self.paned_window, padding=5)
        ttk.Label(input_frame, text="C 源代码输入:", font=self.header_font).pack(anchor='w')
        
        code_container = ttk.Frame(input_frame)
        code_container.pack(fill='both', expand=True)

        # 1. 行号栏
        self.line_num_canvas = tk.Text(code_container, width=4, padx=5, takefocus=0, 
                                      border=0, background="#f0f0f0", state='disabled', 
                                      font=self.text_font, fg="#999999")
        self.line_num_canvas.pack(side='left', fill='y')

        # 2. 输入框
        self.input_text = tk.Text(code_container, wrap=tk.NONE, font=self.text_font, undo=True)
        self.input_text.pack(side='left', fill='both', expand=True)
        
        # 3. 滚动条
        scrollbar = ttk.Scrollbar(code_container, orient="vertical", command=self.sync_scroll)
        scrollbar.pack(side='right', fill='y')
        self.input_text.config(yscrollcommand=scrollbar.set)

        # 绑定事件
        self.input_text.bind('<KeyRelease>', self.update_line_numbers)
        self.input_text.bind('<MouseWheel>', self.update_line_numbers)
        self.input_text.bind('<Button-1>', self.update_line_numbers)
        
        self.paned_window.add(input_frame, weight=1)

        # --- 右侧：结果展示区 ---
        output_frame = ttk.Frame(self.paned_window, padding=5)
        self.notebook = ttk.Notebook(output_frame)
        self.notebook.pack(fill='both', expand=True)

        self.lexer_tab = scrolledtext.ScrolledText(self.notebook, wrap=tk.NONE, font=self.text_font, state='disabled')
        self.notebook.add(self.lexer_tab, text=" 词法 Token 流 ")

        self.parser_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.parser_tab, text=" 语法分析过程表 ")
        
        # 3. 新增：预测分析表可视化 Tab
        self.predict_table_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.predict_table_tab, text=" LL(1)预测分析表 ")
        
        # 在这个 Tab 内部创建表格控件
        self.setup_predict_treeview()

        columns = ("step", "stack", "input", "production", "action")
        self.tree = ttk.Treeview(self.parser_tab, columns=columns, show='headings')

        self.tree.heading("step", text="步骤")
        self.tree.heading("stack", text="分析栈 (Stack)")
        self.tree.heading("input", text="符号串 (Input)")
        self.tree.heading("production", text="所用产生式")
        self.tree.heading("action", text="下一步动作")

        self.tree.column("step", width=50, anchor='center')
        self.tree.column("stack", width=300, anchor='w')
        self.tree.column("input", width=250, anchor='e') 
        self.tree.column("production", width=200, anchor='w')
        self.tree.column("action", width=250, anchor='w')

        vsb = ttk.Scrollbar(self.parser_tab, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(self.parser_tab, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.tree.grid(row=0, column=0, sticky='nsew')
        vsb.grid(row=0, column=1, sticky='ns')
        hsb.grid(row=1, column=0, sticky='ew')
        self.parser_tab.grid_columnconfigure(0, weight=1)
        self.parser_tab.grid_rowconfigure(0, weight=1)

        self.paned_window.add(output_frame, weight=3)

    # --- 新增：滚动同步方法 ---
    def sync_scroll(self, *args):
        """同步滚动代码框和行号栏"""
        self.input_text.yview(*args)
        self.line_num_canvas.yview(*args)

    # --- 新增：行号更新方法 ---
    def update_line_numbers(self, event=None):
        """刷新行号显示"""
        line_count = self.input_text.get('1.0', 'end-1c').count('\n') + 1
        line_numbers_content = "\n".join(str(i) for i in range(1, line_count + 1))
        
        self.line_num_canvas.config(state='normal')
        self.line_num_canvas.delete('1.0', tk.END)
        self.line_num_canvas.insert('1.0', line_numbers_content)
        self.line_num_canvas.config(state='disabled')
        # 确保位置同步
        self.line_num_canvas.yview_moveto(self.input_text.yview()[0])

    def load_file(self):
        filepath = filedialog.askopenfilename(filetypes=[("C Files", "*.c"), ("All Files", "*.*")])
        if filepath:
            content = ""
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
            except UnicodeDecodeError:
                with open(filepath, 'r', encoding='gbk') as f:
                    content = f.read()
            
            self.input_text.delete("1.0", tk.END)
            self.input_text.insert("1.0", content)
            self.update_line_numbers() # 加载后刷新行号

    def run_analysis(self):
        code = self.input_text.get("1.0", tk.END)
        lexer = Lexer(code)
        tokens = lexer.tokenize()
        self.notebook.select(0)
        self.lexer_tab.config(state='normal')
        self.lexer_tab.delete("1.0", tk.END)
        for t in tokens: 
            self.lexer_tab.insert(tk.END, f"[L{t.line:<2}] ({TYPES.get(t.type, 'UNK'):<15} : {t.attribute})\n")
        self.lexer_tab.config(state='disabled')

    def run_parser(self):
        if LL1Parser is None: return
        code = self.input_text.get("1.0", tk.END)
        lexer = Lexer(code)
        tokens = lexer.tokenize()
        parser = LL1Parser()

        records, success, message = parser.analyze(tokens)

        self.notebook.select(1)
        for item in self.tree.get_children(): self.tree.delete(item)

        for step, stack, inp, prod, action in records:
            self.tree.insert("", tk.END, values=(step, stack, inp, prod, action))

        if success: messagebox.showinfo("成功", message)
        else: messagebox.showerror("错误", message)

    def clear_all(self):
        self.input_text.delete("1.0", tk.END)
        self.update_line_numbers() # 清除后重置行号
        self.lexer_tab.config(state='normal')
        self.lexer_tab.delete("1.0", tk.END)
        self.lexer_tab.config(state='disabled')
        for item in self.tree.get_children(): self.tree.delete(item)
        
    def setup_predict_treeview(self):
        # 创建滚动条
        scroll_y = ttk.Scrollbar(self.predict_table_tab, orient="vertical")
        scroll_x = ttk.Scrollbar(self.predict_table_tab, orient="horizontal")
        
        # 创建 Treeview
        # columns 先设置为空，后面动态填充
        self.predict_tree = ttk.Treeview(
            self.predict_table_tab, 
            columns=(), 
            show="headings",
            yscrollcommand=scroll_y.set, 
            xscrollcommand=scroll_x.set
        )
        
        # 样式配置：增加行高，解决你担心的“窄”问题
        style = ttk.Style()
        style.configure("Treeview", rowheight=35, font=('Microsoft YaHei', 10))

        scroll_y.config(command=self.predict_tree.yview)
        scroll_x.config(command=self.predict_tree.xview)

        # 布局
        scroll_y.pack(side='right', fill='y')
        scroll_x.pack(side='bottom', fill='x')
        self.predict_tree.pack(expand=True, fill='both')

if __name__ == '__main__':
    app = LexerApp()
    app.mainloop()