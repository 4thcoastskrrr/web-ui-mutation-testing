from selenium import webdriver
from selenium.webdriver.common.by import By
import inspect
import fileinput
import sys
from collections import defaultdict
import importlib
import os
import shutil
import re 

# ロケータの部分をロケータファイルからとってきた形に変更する
def replacement(file, previousw, nextw, required=None):
    with open(file, 'r', encoding='UTF-8') as f:
        lines = f.readlines()

    for i, line in enumerate(lines):
        # previousw を含み、かつ required（例: ".find_element"）も含む行だけを置換
        if previousw in line and (required is None or required in line):
            lines[i] = line.replace(previousw, nextw)
            break

    with open(file, 'w', encoding='UTF-8') as f1:
        f1.writelines(lines)

# ページオブジェクトファイルにロケータファイルをインポートする
def locators_import(oldfile, newfile, methods):
    with open(oldfile, 'r', encoding='UTF-8') as f:
        lines = [x.rstrip() for x in f.readlines()]
    
    with open(newfile, 'w', encoding='UTF-8') as f1:
        for method_name, method_code in methods:
            # ソースコードを行ごとに取得
            try:
                source_lines, _ = inspect.getsourcelines(method_code)
            except OSError:
                continue

            # 「assertで始まらない行」かつ「find_element等が含まれる行」があるか探す
            needs_import = False
            for line in source_lines:
                stripped_line = line.strip()
                # assert行は無視して判定する
                if stripped_line.startswith("assert"):
                    continue
                
                if "self.driver.find_element" in line or "visibility_of_element_located" in line:
                    needs_import = True
                    break
            
            # 必要な場合のみ import 文を書く
            if needs_import:
                print(f"from {locators} import {method_name}", file=f1)

        for line in lines:
            print(line, file=f1)


# ページオブジェクトファイルからロケータファイルを生成
def extract_locators_as_class(obj, output_file):
    locators_dict = {}
    methods = inspect.getmembers(obj, predicate=inspect.ismethod)
    
    # import文の生成
    locators_import(f"tool/{module_name}.py", new_pageobject_fname, methods)

    for name, method in methods:
        try:
            lines = inspect.getsourcelines(method)[0]
        except OSError:
            continue

        # 1メソッド内で「ロケータ文字列 -> line名」を管理
        method_loc_map = {}  # { 'By.ID, "username"' : 'line_1', ... }
        next_idx = 1

        def get_line_name(locator_str: str) -> str:
            nonlocal next_idx
            if locator_str in method_loc_map:
                return method_loc_map[locator_str]
            line_name = f"line_{next_idx}"
            next_idx += 1
            method_loc_map[locator_str] = line_name
            return line_name

        # ---------- 1st pass: find_element からロケータを拾う ----------
        regex_find = r"find_element\(((?:[^()]*|\((?:[^()]*|\([^()]*\))*\))*)\)"
        
        for line in lines:
            if line.strip().startswith("assert"):
                continue
            if "self.driver.find_element" not in line:
                continue

            m = re.search(regex_find, line)
            if not m:
                continue
            
            locator_parts = m.group(1).strip()
            line_name = get_line_name(locator_parts)

            replacement(
                new_pageobject_fname,
                locator_parts,
                f"*{name}.{line_name}",
                required=".find_element",
            )

        # ---------- 2nd pass: visibility_of_element_located からも拾う ----------
        regex_wait = r"visibility_of_element_located\(\s*\(\s*((?:[^()]*|\((?:[^()]*|\([^()]*\))*\))*)\s*\)\s*\)"

        for line in lines:
            if line.strip().startswith("assert"):
                continue
            if "visibility_of_element_located" not in line:
                continue

            m = re.search(regex_wait, line)
            if not m:
                continue

            locator_parts = m.group(1).strip()
            line_name = get_line_name(locator_parts)

            # visibility_of_element_located((By....)) の (By....) 部分だけを page_n.line_m に置換
            replacement(
                new_pageobject_fname,
                f"({locator_parts})",
                f"{name}.{line_name}",
                required="visibility_of_element_located",
            )

        if method_loc_map:
            locators_dict[name] = [
                (line_name, locator_str)
                for locator_str, line_name in method_loc_map.items()
            ]

    # ---------- locators.py の書き出し ----------
    with open(output_file, "w", encoding="UTF-8") as f:
        f.write("from selenium.webdriver.common.by import By\n\n")
        for method, elements in locators_dict.items():
            f.write(f"class {method}:\n")
            for line_name, locator_parts in elements:
                f.write(f"    {line_name} = ({locator_parts})\n")
            f.write("\n")

# --- メイン処理 ---
# 引数チェックなどは省略しています
module_name = "old_pageobject"  
object_name = "page_class" 

imported_module = __import__(module_name)
specified_object = getattr(imported_module, object_name)

# ダミーのドライバでインスタンス化（inspect用）
driver = webdriver.Chrome()
page_instance = specified_object(driver)

new_pageobject_fname = "page_object.py"
locators = "locators"

extract_locators_as_class(page_instance, f"{locators}.py")

driver.quit() # ドライバを閉じる

# ファイル移動
scenario = sys.argv[1]
new_folder_name = "new"
trash_folder_name  = "byproduct"

# ディレクトリ作成（存在しない場合エラーにならないように）
os.makedirs(f"{scenario}/{trash_folder_name}", exist_ok=True)
os.makedirs(f"{scenario}/{new_folder_name}", exist_ok=True)
os.makedirs(f"{scenario}/mutants", exist_ok=True)

# 移動
if os.path.exists(f"tool/{module_name}.py"):
    shutil.move(f"tool/{module_name}.py", f"{scenario}/{trash_folder_name}") 
if os.path.exists(new_pageobject_fname):
    shutil.move(new_pageobject_fname, f"{scenario}/{new_folder_name}") 
if os.path.exists(f"{locators}.py"):
    shutil.move(f"{locators}.py", f"{scenario}/{new_folder_name}")