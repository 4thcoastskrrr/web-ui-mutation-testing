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

#ローテーションする関数
def rotate_list_left(arr, rotations):
    length = len(arr)

    if length == 0:
        return arr

    arr = arr[rotations:] + arr[:rotations]  # リストの中身を書き換え
    return arr


#同じページ内のテストコードの順番をローテーションするミュータントを生成する関数
def generate_code_rotation_files(input_file_path):
    with open(input_file_path, 'r', encoding="UTF-8") as input_file:
        lines = input_file.readlines()

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
            code_line = start_line
            code_list = []
            while lines[code_line] != "\n":
                code_list.append(lines[code_line])
                code_line += 1

            i = 1
            code_line = start_line
            while lines[start_line] != "\n":
                output_lines = list(lines)  # コピーを作成して元のリストを変更しないようにする

                if i != len(code_list):
                    rotated_list = rotate_list_left(code_list, i) #ローテーションさせる

                    #コード置き換え
                    for j, item in enumerate(rotated_list):
                        output_lines[code_line + j] = item

                    output_file_path = "page_object.py"  # 出力ファイルパスの設定

                    with open(output_file_path, 'w', encoding="UTF-8") as output_file:
                        output_file.writelines(output_lines)

                    add_webdriverwait(output_file_path)

                    add_html(output_file_path)

                    add_screenshot_code(output_file_path)

                    folder_name = f"02_{mutation_file_number}" 
                    os.mkdir(f"{file_path}/mutants/{folder_name}")
                    shutil.copy(f"{file_path}/new/test.py", f"{file_path}/mutants/{folder_name}") 
                    shutil.move(output_file_path, f"{file_path}/mutants/{folder_name}") 
                    shutil.copy(f"{file_path}/new/locators.py", f"{file_path}/mutants/{folder_name}") 

                    n = int(mutation_file_number) + 1
                    mutation_file_number = str(n).zfill(len(mutation_file_number))
                start_line += 1
                i += 1


        else:
            start_line += 1
            code_line = start_line
            code_list = []
            while lines[code_line] != "\n":
                code_list.append(lines[code_line])
                code_line += 1

            i = 1
            code_line = start_line
            while lines[start_line] != "\n":
                output_lines = list(lines)  # コピーを作成して元のリストを変更しないようにする

                if i != len(code_list):
                    rotated_list = rotate_list_left(code_list, i) #ローテーションさせる

                    #コード置き換え
                    for j, item in enumerate(rotated_list):
                        output_lines[code_line + j] = item

                    output_file_path = "page_object.py"  # 出力ファイルパスの設定


                    with open(output_file_path, 'w', encoding="UTF-8") as output_file:
                        output_file.writelines(output_lines)

                    add_webdriverwait(output_file_path)

                    add_html(output_file_path)

                    add_screenshot_code(output_file_path)

                    folder_name = f"02_{mutation_file_number}" 
                    os.mkdir(f"{file_path}/mutants/{folder_name}")
                    shutil.copy(f"{file_path}/new/test.py", f"{file_path}/mutants/{folder_name}") 
                    shutil.move(output_file_path, f"{file_path}/mutants/{folder_name}") 
                    shutil.copy(f"{file_path}/new/locators.py", f"{file_path}/mutants/{folder_name}") 
            
                    n = int(mutation_file_number) + 1
                    mutation_file_number = str(n).zfill(len(mutation_file_number))
                start_line += 1
                i += 1

                
# ファイルのパスを指定して関数を実行
file_path = sys.argv[1]  
generate_code_rotation_files(f"{file_path}/new/page_object.py")