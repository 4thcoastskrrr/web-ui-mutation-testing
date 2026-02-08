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

# ロケーターをローテーションさせて新しいファイルを生成する関数
def generate_rotated_locator_files(input_file_path):
    with open(input_file_path, 'r', encoding="UTF-8") as input_file:
        lines = input_file.readlines()

    functions = {}
    current_function = None
    for line in lines:
        if line.strip().startswith('def '):
            current_function = line.strip().split('(')[0].split(' ')[1]  # 関数名を取得
            functions[current_function] = lines.index(line)  # 関数の開始行のインデックスを取得

    print(functions)

    mutation_file_number = "001"
    for func_name, start_line in functions.items():
        if func_name == '__init__':
            continue
        
        start_line += 1
        code_line = start_line
        rotated_locators = []
        while lines[code_line] != '\n':
            # ロケーターの行から *page_1.line_3 のような部分を取り出す
            if '.find_element' in lines[code_line]:
                locator_line = lines[code_line].partition('(')[-1].partition(')')[0]
                rotated_locators.append(locator_line)
            code_line += 1

        print(rotated_locators)
        
        i = 1
        while rotated_locators and i != len(rotated_locators): #ロケータリストが空じゃないとき実行
            output_lines = list(lines)  

            if i != len(rotated_locators):
                rotated_list = rotate_list_left(rotated_locators, i) #ローテーションさせる
                print(rotated_list)

                #ロケータを置き換える(ロケータの名前が違う前提の話)
                for j, item in enumerate(rotated_locators):
                    code_line = start_line
                    pre_output_lines = list(lines)  # コピーを作成して元のリストを変更しないようにする
                    while pre_output_lines[code_line] != '\n':
                        if item in pre_output_lines[code_line]:
                            output_lines[code_line] = pre_output_lines[code_line].replace(item, rotated_list[j])
                            break
                        code_line += 1

                output_file_path = "page_object.py"  # 出力ファイルパスの設定

                #ミューテーションファイル生成
                with open(output_file_path, 'w', encoding="UTF-8") as output_file:
                    output_file.writelines(output_lines)

                add_webdriverwait(output_file_path)

                add_html(output_file_path)

                add_screenshot_code(output_file_path)

                #ファイル移動
                folder_name = f"03_{mutation_file_number}" 
                os.mkdir(f"{file_path}/mutants/{folder_name}")
                shutil.copy(f"{file_path}/new/test.py", f"{file_path}/mutants/{folder_name}") 
                shutil.move(output_file_path, f"{file_path}/mutants/{folder_name}") 
                shutil.copy(f"{file_path}/new/locators.py", f"{file_path}/mutants/{folder_name}") 
            
                n = int(mutation_file_number) + 1
                mutation_file_number = str(n).zfill(len(mutation_file_number))

            i += 1

    
# ファイルのパスを指定して関数を実行
file_path = sys.argv[1]
generate_rotated_locator_files(f"{file_path}/new/page_object.py")
