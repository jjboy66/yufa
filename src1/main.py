import sys
import os
import pandas as pd
from openpyxl.utils import get_column_letter
from parser_core import LL1Parser
from constants import TYPES  # 或者是你定义该字典的文件名
import tkinter as tk
from tkinter import filedialog, messagebox  # 新增：用于弹出选择框和提示框
from lexer_gui import LexerApp
from lexer_core import Lexer
try:
    from parser_core import LL1Parser
except ImportError:
    LL1Parser = None

class EnhancedApp(LexerApp):
    """
    继承自你原来的 LexerApp，不改动原文件，
    但在主程序中增强功能：增加自动记录到 result.txt 的逻辑。
    """
    
    def __init__(self):
        # 1. 【核心修改】调用父类 LexerApp 的初始化，确保界面生成
        super().__init__()
        
        # 2. 【核心修改】在这里实例化你朋友的代码类
        # 这样你在 save_prediction_table 方法里才能用 self.grammar_converter
        self.grammar_converter = LL1Parser()

    # --- 以下是按钮 5 的功能实现 ---
    def save_prediction_table(self):
        """适配 LL1Parser 的 Excel 导出函数"""
        try:
            # 1. 构造数据矩阵 (确保逻辑与渲染一致)
            p = self.grammar_converter
            all_ts = sorted(list(p.grammar.terminals))
            all_nts = sorted(list(p.grammar.nonterminals))
            header = ["非终结符"] + all_ts
            matrix = [header]
            for nt in all_nts:
                row = [nt]
                for t in all_ts:
                    prod = p.table.get((nt, t))
                    row.append(" ".join(prod) if prod else "")
                matrix.append(row)

            # 2. 弹出带默认文件名的对话框
            import pandas as pd
            file_path = filedialog.asksaveasfilename(
                title="导出预测分析表",
                initialfile="LL(1)预测分析表.xlsx", # 自动显示文件名
                defaultextension=".xlsx",
                filetypes=[("Excel Files", "*.xlsx")]
            )
            
            if file_path:
                df = pd.DataFrame(matrix[1:], columns=matrix[0])
                df.to_excel(file_path, index=False)
                messagebox.showinfo("成功", "文件保存成功！")
        except Exception as e:
            messagebox.showerror("导出错误", str(e))
    
    def on_gen_predict_table_clicked(self):
        """专门适配你提供的 LL1Parser 结构的渲染逻辑"""
        try:
            # 1. 检查 parser 是否已初始化
            if not hasattr(self, 'grammar_converter') or self.grammar_converter is None:
                from parser_core import LL1Parser # 确保导入
                self.grammar_converter = LL1Parser()

            p = self.grammar_converter
            
            # 2. 【核心修改】将字典格式的 self.table 转换成 GUI 需要的二维矩阵 (FORM)
            # 获取所有的终结符和非终结符
            all_ts = sorted(list(p.grammar.terminals))
            all_nts = sorted(list(p.grammar.nonterminals))
            
            # 构建表头：第一列是"非终结符"，后面跟着所有终结符
            header = ["非终结符"] + all_ts
            matrix = [header]
            
            # 填充每一行
            for nt in all_nts:
                row = [nt] # 第一列填非终结符名
                for t in all_ts:
                    # 从 p.table 字典里查表
                    prod = p.table.get((nt, t))
                    if prod:
                        # 格式化产生式，例如: ["Type", "id"] -> "Type id"
                        prod_str = " ".join(prod) if prod != ["epsilon"] else "ε"
                        row.append(f"{nt} -> {prod_str}")
                    else:
                        row.append("") # 无对应产生式则留空
                matrix.append(row)

            # 3. 渲染到 Treeview
            self.predict_tree["columns"] = header
            self.predict_tree["show"] = "headings"
            
            # 清空旧数据
            for item in self.predict_tree.get_children():
                self.predict_tree.delete(item)
            
            # 设置表头
            for col in header:
                self.predict_tree.heading(col, text=p.display(col)) # 使用别名显示
                self.predict_tree.column(col, width=120, anchor='center')
            
            # 插入数据
            for row_data in matrix[1:]:
                self.predict_tree.insert("", tk.END, values=row_data)

            # 4. 切换 Tab
            self.notebook.select(self.predict_table_tab)
            messagebox.showinfo("成功", f"预测分析表已生成！(基于内置C文法)")

        except Exception as e:
            import traceback
            print(traceback.format_exc())
            messagebox.showerror("错误", f"渲染分析表失败: {e}")
   
    def render_table_to_gui(self, data):
        """将二维列表 data 渲染到 predict_tree"""
        # 1. 设置列名
        headers = data[0]
        self.predict_tree["columns"] = headers
        self.predict_tree["show"] = "headings"

        for col in headers:
            self.predict_tree.heading(col, text=col)
            # 根据内容微调列宽
            width = 150 if col == "非终结符" else 100
            self.predict_tree.column(col, width=width, anchor='center')

        # 2. 清空旧数据
        for item in self.predict_tree.get_children():
            self.predict_tree.delete(item)

        # 3. 插入新数据
        for row in data[1:]:
            cleaned_row = [str(item) if item is not None else "" for item in row]
            self.predict_tree.insert("", tk.END, values=cleaned_row)
            
    def save_txt_as(self):
        # 弹出保存对话框
        file_path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt")],
            initialfile="result.txt"
        )
        if not file_path: return

        code = self.input_text.get("1.0", tk.END).strip()
        if not code: return
        
        lexer = Lexer(code)
        tokens = lexer.tokenize()
        
        # 按照截图样式导出词法结果
        with open(file_path, 'w', encoding='utf-8') as f:
            for t in tokens:
                # 关键：将数字类型(如27)转换为文字(如KEYWORD)
                type_name = TYPES.get(t.type, str(t.type))
                line_str = f"[L{t.line:<2}]" 
                type_str = f"({type_name:<15} : {t.attribute})"
                f.write(f"{line_str} {type_str}\n")
        messagebox.showinfo("提示", f"词法分析结果已保存至：\n{file_path}")

    def save_xlsx_as(self):
        # 弹出保存对话框
        file_path = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel files", "*.xlsx")],
            initialfile="analysis_results.xlsx"
        )
        if not file_path: return

        code = self.input_text.get("1.0", tk.END).strip()
        if not code: return
        
        # 重新执行一次分析以获取最新的 records
        lexer = Lexer(code)
        tokens = lexer.tokenize()
        parser = LL1Parser()
        records, _, _ = parser.analyze(tokens)
        
        # 调用之前写好的鲁棒版导出函数
        self.export_to_excel(tokens, records, filename=file_path)
        messagebox.showinfo("提示", f"语法分析 Excel 已保存至：\n{file_path}")
    
    def export_to_excel(self, tokens, records, filename="analysis_results.xlsx"):
        """
        鲁棒性增强版导出函数：
        自动兼容 4 列或 5 列数据，并导出词法+语法两个结果。
        """
        print("正在准备导出数据...")
        
        # 1. 处理语法分析记录 (确保每一行都是 5 列)
        fixed_records = []
        for row in records:
            row_list = list(row)
            # 如果数据只有 4 列，补齐到 5 列
            if len(row_list) == 4:
                row_list.append("（无动作说明）")
            # 如果超过 5 列，截取前 5 列
            fixed_records.append(row_list[:5])

        # 定义表头
        syn_headers = ["步骤", "分析栈 (Stack)", "符号串 (Input)", "所用产生式", "下一步动作"]

        try:
            # 创建 DataFrame
            df_syn = pd.DataFrame(fixed_records, columns=syn_headers)

            # 使用 ExcelWriter 写入一个 Sheet
            with pd.ExcelWriter(filename, engine='openpyxl') as writer:
                df_syn.to_excel(writer, sheet_name='语法分析过程', index=False)
                
                # 自动调整列宽美化（防止文字太长看不见）
                for sheet_name in writer.sheets:
                    worksheet = writer.sheets[sheet_name]
                    for col in worksheet.columns:
                        # 查找该列中最长的内容
                        max_length = 0
                        column_letter = get_column_letter(col[0].column)
                        for cell in col:
                            try:
                                if len(str(cell.value)) > max_length:
                                    max_length = len(str(cell.value))
                            except: pass
                        # 设置宽度，最小 10，最大 60
                        adjusted_width = min(max_length + 2, 60)
                        worksheet.column_dimensions[column_letter].width = adjusted_width

            print(f"✅ 导出成功！文件位置: {os.path.abspath(filename)}")
            
        except PermissionError:
            print("❌ 导出失败：Excel 文件正被其他程序占用，请先关闭它！")
        except Exception as e:
            print(f"❌ 导出过程中发生错误: {e}")
            
    def run_parser(self):
        # 调用父类的原逻辑（界面显示）
        super().run_parser()
        
        # 额外增加：自动将结果同步到 result.txt
        if LL1Parser is not None:
            code = self.input_text.get("1.0", tk.END).strip()
            if not code:
                return
                
            lexer = Lexer(code)
            tokens = lexer.tokenize()
            parser = LL1Parser()
            records, success, message = parser.analyze(tokens)
            
            if records:
                print("\n[调试信息] 数据第一行内容为:", records[0])
                print(f"[调试信息] 每一行包含的元素个数为: {len(records[0])}\n")
            
            # --- 2. 修正后的词法结果导出 (result.txt) ---
            # 目标格式: [L1 ] (PREPROCESSOR     : #include <stdio.h>)
            # --- 修正后的词法结果导出 (result.txt) ---
            with open('result.txt', 'w', encoding='utf-8') as f:
                for t in tokens:
                    # 关键修改点：使用 TYPES.get(t.type) 将数字转换为文字描述
                    # 如果 TYPES 里找不到对应的数字，则保留原样
                    type_name = TYPES.get(t.type, str(t.type))
                    
                    # 格式化输出
                    line_str = f"[L{t.line:<2}]" 
                    type_str = f"({type_name:<15} : {t.attribute})"
                    f.write(f"{line_str} {type_str}\n")
            
            print("词法结果已按截图格式更新至 result.txt")
            
            # --- 新增：插入 Excel 导出调用 ---
            self.export_to_excel(tokens, records)

def main():
    # 1. 环境检查
    print("正在检查编译器组件...")
    if LL1Parser is None:
        print("警告: 未检测到 parser_core.py 或 LL1Parser 类，语法分析功能将不可用。")
    else:
        print("组件加载成功：词法分析器 & 语法分析器 已就绪。")

    # 2. 启动应用
    # 我们使用 EnhancedApp 来代替原来的 LexerApp，实现功能增强而不改动原代码
    app = EnhancedApp()
    
    # 如果你想一启动就加载 c-code.c（可选）
    if os.path.exists("c-code.c"):
        with open("c-code.c", "r", encoding="utf-8") as f:
            app.input_text.insert("1.0", f.read())
        print("已自动加载 c-code.c")

    app.mainloop()

if __name__ == '__main__':
    main()