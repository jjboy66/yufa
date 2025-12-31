"""
C 语言编译器实验 - 语法分析 (修复行号同步版)
"""
import os
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

        # --- 样式配置 ---
        style = ttk.Style()
        # 设置 Treeview 行高，避免太拥挤
        style.configure("Sets.Treeview", font=("Consolas", 10), rowheight=25)
        style.configure("Sets.Treeview.Heading", font=("Microsoft YaHei", 10, "bold"))

        # 保存分析结果供导出使用
        self._parser = None
        self._sets_data = None

        self.create_widgets()

    def create_widgets(self):
        top_frame = ttk.Frame(self, padding="10")
        top_frame.pack(fill='x')

        ttk.Button(top_frame, text="加载 C 文件", command=self.load_file).pack(side='left', padx=5)
        ttk.Button(top_frame, text="运行词法分析", command=self.run_analysis).pack(side='left', padx=5)
        ttk.Button(top_frame, text="生成语法分析表", command=self.run_parser).pack(side='left', padx=5)
        ttk.Button(top_frame, text="生成预测分析表", command=self.on_gen_predict_table_clicked).pack(side='left', padx=5)
        ttk.Button(top_frame, text="导出文法和集合", command=self.export_grammar_sets).pack(side='left', padx=5)
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

        # 4. 新增：文法集合 Tab
        self.sets_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.sets_frame, text=" 文法集合 (Sets) ")

        # 定义三列：左部(右对齐), 符号(居中), 右部(左对齐)
        sets_cols = ("left", "op", "right")
        self.sets_tree = ttk.Treeview(self.sets_frame, columns=sets_cols, show='headings', style="Sets.Treeview")

        # 配置列
        self.sets_tree.heading("left", text="文法/集合 左部")
        self.sets_tree.column("left", width=350, anchor='e')  # 右对齐 -> 往中间靠

        self.sets_tree.heading("op", text="符号")
        self.sets_tree.column("op", width=50, anchor='center') # 居中

        self.sets_tree.heading("right", text="文法右部 / 集合内容")
        self.sets_tree.column("right", width=500, anchor='w')  # 左对齐 -> 往中间靠

        # --- 关键：配置表头行的 Tag 样式 ---
        # background: 浅灰色背景，显眼
        # font: 加粗，大一号
        self.sets_tree.tag_configure("header", background="#e1e1e1", foreground="#000000", font=("Microsoft YaHei", 10, "bold"))

        vsb_sets = ttk.Scrollbar(self.sets_frame, orient="vertical", command=self.sets_tree.yview)
        hsb_sets = ttk.Scrollbar(self.sets_frame, orient="horizontal", command=self.sets_tree.xview)
        self.sets_tree.configure(yscrollcommand=vsb_sets.set, xscrollcommand=hsb_sets.set)

        self.sets_tree.grid(row=0, column=0, sticky='nsew')
        vsb_sets.grid(row=0, column=1, sticky='ns')
        hsb_sets.grid(row=1, column=0, sticky='ew')
        self.sets_frame.grid_columnconfigure(0, weight=1)
        self.sets_frame.grid_rowconfigure(0, weight=1)

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

        # 保存 parser 和 sets_data 供导出使用
        self._parser = parser
        self._sets_data = parser.calc_sets()
        self.display_sets(parser, self._sets_data)

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
        for item in self.sets_tree.get_children(): self.sets_tree.delete(item)
        # Reset saved analysis results
        self._parser = None
        self._sets_data = None

    @staticmethod
    def _fmt_set(s):
        """Format a set for display"""
        elements = sorted(list(s))
        return "{" + ", ".join(elements) + "}"

    def display_sets(self, parser, sets_data):
        # 清空
        for item in self.sets_tree.get_children():
            self.sets_tree.delete(item)

        # --- 核心辅助函数：插入显眼的表头 ---
        def add_section_header(title_left, title_right):
            # 插入一个空行作为分隔
            self.sets_tree.insert("", tk.END, values=("", "", ""))

            # 构造左右填充的文本
            fill_char = "=" * 30
            val_left = f"{fill_char} {title_left}"
            val_right = f"{title_right} {fill_char}"

            # 插入带 tag 的行
            self.sets_tree.insert("", tk.END, values=(val_left, "", val_right), tags=("header",))

        def add_row(left, op, right):
            self.sets_tree.insert("", tk.END, values=(left, op, right))

        # ====== 1. 文法定义 ======
        # 将标题拆分为 "文法定义" 和 "G[S]"，分别放在左右两列
        add_section_header("文法定义", "G[S]")
        for lhs, rhss in parser.grammar.prods.items():
            lhs_disp = parser.display(lhs)
            rhs_texts = []
            for rhs in rhss:
                if rhs == ['epsilon']:
                    rhs_texts.append("ε")
                else:
                    rhs_texts.append(" ".join(parser.display(s) for s in rhs))
            add_row(lhs_disp, "->", ' | '.join(rhs_texts))

        # ====== 2. FIRST 集 ======
        add_section_header("FIRST", "集合")
        first = sets_data.get('first', {})
        for nt in sorted(first.keys()):
            name = parser.display(nt)
            add_row(f"First({name})", "=", self._fmt_set(first[nt]))

        # ====== 3. FOLLOW 集 ======
        add_section_header("FOLLOW", "集合")
        follow = sets_data.get('follow', {})
        for nt in sorted(follow.keys()):
            name = parser.display(nt)
            add_row(f"Follow({name})", "=", self._fmt_set(follow[nt]))

        # ====== 4. SELECT 集 ======
        add_section_header("SELECT", "集合")
        select = sets_data.get('select', {})
        sorted_select = sorted(select.items(), key=lambda x: x[0][0])

        for (lhs, rhs_tuple), terms in sorted_select:
            lhs_disp = parser.display(lhs)
            rhs_list = list(rhs_tuple)
            if not rhs_list or rhs_list == ["epsilon"]:
                rhs_str = "ε"
            else:
                rhs_str = " ".join(parser.display(s) for s in rhs_list)

            prod_str = f"{lhs_disp} -> {rhs_str}"
            add_row(f"Select({prod_str})", "=", self._fmt_set(terms))

    def export_grammar_sets(self):
        """导出文法和集合到本地文件"""
        if self._parser is None:
            messagebox.showwarning("警告", "请先运行词法和语法分析")
            return

        if self._sets_data is None:
            messagebox.showwarning("警告", "没有可导出的文法集合数据")
            return

        # 选择导出目录
        export_dir = filedialog.askdirectory(title="选择导出目录")
        if not export_dir:
            return

        # 导出文法集合
        try:
            self._export_sets(self._parser, self._sets_data, export_dir)
            messagebox.showinfo("成功", f"文法集合已导出到: {export_dir}/grammar_sets.txt")
        except IOError as e:
            messagebox.showerror("导出错误", f"导出文件时出错:\n{e}")

    def _export_sets(self, parser, sets_data, export_dir):
        """导出文法集合到文件"""
        filepath = os.path.join(export_dir, "grammar_sets.txt")

        with open(filepath, 'w', encoding='utf-8') as f:
            # 文法定义
            f.write("=" * 80 + "\n")
            f.write("文法定义 G[S]\n")
            f.write("=" * 80 + "\n\n")
            for lhs, rhss in parser.grammar.prods.items():
                lhs_disp = parser.display(lhs)
                rhs_texts = []
                for rhs in rhss:
                    if rhs == ['epsilon']:
                        rhs_texts.append("ε")
                    else:
                        rhs_texts.append(" ".join(parser.display(s) for s in rhs))
                f.write(f"{lhs_disp} -> {' | '.join(rhs_texts)}\n")

            # FIRST 集
            f.write("\n" + "=" * 80 + "\n")
            f.write("FIRST 集合\n")
            f.write("=" * 80 + "\n\n")
            first = sets_data.get('first', {})
            for nt in sorted(first.keys()):
                name = parser.display(nt)
                f.write(f"First({name}) = {self._fmt_set(first[nt])}\n")

            # FOLLOW 集
            f.write("\n" + "=" * 80 + "\n")
            f.write("FOLLOW 集合\n")
            f.write("=" * 80 + "\n\n")
            follow = sets_data.get('follow', {})
            for nt in sorted(follow.keys()):
                name = parser.display(nt)
                f.write(f"Follow({name}) = {self._fmt_set(follow[nt])}\n")

            # SELECT 集
            f.write("\n" + "=" * 80 + "\n")
            f.write("SELECT 集合\n")
            f.write("=" * 80 + "\n\n")
            select = sets_data.get('select', {})
            sorted_select = sorted(select.items(), key=lambda x: x[0][0])
            for (lhs, rhs_tuple), terms in sorted_select:
                lhs_disp = parser.display(lhs)
                rhs_list = list(rhs_tuple)
                if not rhs_list or rhs_list == ["epsilon"]:
                    rhs_str = "ε"
                else:
                    rhs_str = " ".join(parser.display(s) for s in rhs_list)
                prod_str = f"{lhs_disp} -> {rhs_str}"
                f.write(f"Select({prod_str}) = {self._fmt_set(terms)}\n")
        
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