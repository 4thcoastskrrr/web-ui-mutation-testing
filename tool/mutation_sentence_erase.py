import sys
import os
import shutil

#スクリーンショットのコードをページオブジェクトに追加する関数
def add_screenshot_code(file_path):
    with open(file_path, 'r', encoding='UTF-8') as file:
        lines = file.readlines()
        
    updated_lines = []
    last_screenshot_index = 0  # 最後のスクリーンショット行のインデックスを記録
    screenshot_count = 0

    for i, line in enumerate(lines):
        if line.strip().startswith('self.driver') or line.strip().startswith('#self.driver') or line.strip().startswith('select.select') or line.strip().startswith('#select.select'):
            last_screenshot_index += 1

    for i, line in enumerate(lines):
        updated_lines.append(line)
        if (line.strip().startswith('self.driver') or line.strip().startswith('#self.driver') or line.strip().startswith('select.select') or line.strip().startswith('#select.select'))  and line.strip() != "self.driver = driver":
            updated_lines.insert(-1, "        current_url = self.driver.current_url\n")
            updated_lines.append("        if self.driver.current_url != current_url:\n")
            updated_lines.append("            print(self.driver.current_url)\n")
            updated_lines.append("            WebDriverWait(self.driver, 10).until(expected_conditions.url_changes(current_url))\n")
            updated_lines.append("        WebDriverWait(self.driver, 10).until(\n")
            updated_lines.append("            lambda d: d.execute_script('return document.readyState') == 'complete'\n")
            updated_lines.append("        )\n")
            updated_lines.append("        time.sleep(1)\n")
            updated_lines.append("        WebDriverWait(self.driver, 10).until(expected_conditions.visibility_of_element_located((By.TAG_NAME, 'body')))\n")
            updated_lines.append("        self.driver.switch_to.window(self.driver.window_handles[-1])\n")
            screenshot_line = f"        self.driver.save_screenshot('screenshot{screenshot_count+1}_{last_screenshot_index-1}.png')\n"
            updated_lines.append(screenshot_line)
            screenshot_count += 1

    # ファイルに書き込み
    with open(file_path, 'w', encoding='UTF-8') as file:
        file.writelines(updated_lines)
    
    print(f"コードが {file_path} に正常に追加されました。")


#HTMLファイルを取得するコードを追加する関数(一文ごとに)
def add_html(file_path):
    with open(file_path, 'r', encoding='UTF-8') as file:
        lines = file.readlines()
        
    updated_lines = []
    last_html_index = 0
    get_html = 0

    for i, line in enumerate(lines):
        if line.strip().startswith('self.driver') or line.strip().startswith('#self.driver') or line.strip().startswith('select.select') or line.strip().startswith('#select.select'):
            last_html_index += 1

    for i, line in enumerate(lines):
        updated_lines.append(line)
        if (line.strip().startswith('self.driver') or line.strip().startswith('#self.driver') or line.strip().startswith('select.select') or line.strip().startswith('#select.select')) and line.strip() != "self.driver = driver":
            updated_lines.append(f'        with open("result{get_html+1}_{last_html_index-1}.html", "w", encoding="utf-8") as f:\n')
            updated_lines.append('            f.write(self.driver.page_source)\n')
            get_html += 1

    with open(file_path, 'w', encoding='UTF-8') as file:
        file.writelines(updated_lines)    
    print(f"コードが {file_path} に正常に追加されました。")      

#各ページでの冒頭でwebdriverwait文を追加する関数
def add_webdriverwait(file_path):
    with open(file_path, 'r', encoding='UTF-8') as file:
        lines = file.readlines()
        
    updated_lines = []
    for i, line in enumerate(lines):
        updated_lines.append(line)
        if line.strip().startswith('def') and not line.strip().startswith('def __init__') and not line.strip().startswith('def page_1'):
            updated_lines.append("        WebDriverWait(self.driver, 20).until(\n")
            updated_lines.append("            lambda d: d.execute_script('return document.readyState') == 'complete'\n")
            updated_lines.append("        )\n")
        
        if line.strip().startswith('self.driver.get'):
            updated_lines.append("        WebDriverWait(self.driver, 20).until(\n")
            updated_lines.append("            lambda d: d.execute_script('return document.readyState') == 'complete'\n")
            updated_lines.append("        )\n")

    # ファイルに書き込み
    with open(file_path, 'w', encoding='UTF-8') as file:
        file.writelines(updated_lines)
    
    print(f"コードが {file_path} に正常に追加されました。")

#同じページ内のテストコードを一文除去するミューテーションを生成する関数
def generate_commented_files(input_file_path):
    with open(input_file_path, 'r', encoding='utf-8') as input_file:
        lines = input_file.readlines()
        print(lines)

    functions = {}
    current_function = None
    for line in lines:
        if line.strip().startswith('def '):
            current_function = line.strip().split('(')[0].split(' ')[1]  # 関数名を取得
            functions[current_function] = lines.index(line) # 関数の開始行のインデックスを取得
            print(functions)
    
    mutation_file_number = "001"
    for func_name, start_line in functions.items():
        if func_name == '__init__':
            continue
        
        elif func_name == 'page_1':
            start_line += 3
            while lines[start_line] != "\n":
                if "=" in lines[start_line] or lines[start_line].strip().startswith("WebDriverWait"):
                    start_line += 1
                    continue

                output_lines = list(lines)  # コピーを作成して元のリストを変更しないようにする
                output_lines[start_line] = "       #" + output_lines[start_line].lstrip()  # 特定の行をコメントアウト
                m_line = start_line
                output_file_path = "page_object.py"  # 出力ファイルパスの設定
                output_lines.insert(start_line, "       #下の行をコメントアウトした\n")

                with open(output_file_path, 'w', encoding="UTF-8") as output_file:
                    output_file.writelines(output_lines)

                add_webdriverwait(output_file_path)

                add_html(output_file_path)
                
                add_screenshot_code(output_file_path)


                folder_name = f"01_{mutation_file_number}" 
                os.mkdir(f"{file_path}/mutants/{folder_name}")
                shutil.copy(f"{file_path}/new/test.py", f"{file_path}/mutants/{folder_name}") 
                shutil.move(output_file_path, f"{file_path}/mutants/{folder_name}") 
                shutil.copy(f"{file_path}/new/locators.py", f"{file_path}/mutants/{folder_name}") 
            
                n = int(mutation_file_number) + 1
                mutation_file_number = str(n).zfill(len(mutation_file_number))
                start_line += 1


        else:
            start_line += 1
            while lines[start_line] != "\n":
                if "=" in lines[start_line] or lines[start_line].strip().startswith("WebDriverWait"):
                    start_line += 1
                    continue

                output_lines = list(lines)  # コピーを作成して元のリストを変更しないようにする
                output_lines[start_line] = "       #" + output_lines[start_line].lstrip()  # 特定の行をコメントアウト
                m_line = start_line
                output_file_path = "page_object.py"  # 出力ファイルパスの設定
                output_lines.insert(start_line, "       #下の行をコメントアウトした\n")

                with open(output_file_path, 'w', encoding="UTF-8") as output_file:
                    output_file.writelines(output_lines)

                add_webdriverwait(output_file_path)

                add_html(output_file_path)

                add_screenshot_code(output_file_path)
                
                folder_name = f"01_{mutation_file_number}" 
                os.mkdir(f"{file_path}/mutants/{folder_name}")
                shutil.copy(f"{file_path}/new/test.py", f"{file_path}/mutants/{folder_name}") 
                shutil.move(output_file_path, f"{file_path}/mutants/{folder_name}") 
                shutil.copy(f"{file_path}/new/locators.py", f"{file_path}/mutants/{folder_name}") 
            
                n = int(mutation_file_number) + 1
                mutation_file_number = str(n).zfill(len(mutation_file_number))
                start_line += 1

# ファイルのパスを指定して関数を実行するメイン関数
def main():
    global file_path
    # このスクリプトが直接実行されたときだけ、引数から file_path を受け取って 01_xxx を生成する
    if len(sys.argv) < 2:
        print("Usage: python mutation_sentence_erase.py <project_root>")
        sys.exit(1)

    file_path = sys.argv[1]
    generate_commented_files(f"{file_path}/new/page_object.py")


# この条件のときだけ main() を呼ぶので、
# 他ファイルから import されたときには 01_xxx は生成されない
if __name__ == "__main__":
    main()
