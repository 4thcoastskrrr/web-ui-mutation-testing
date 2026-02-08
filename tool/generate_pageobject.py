import subprocess
import sys
import os
import shutil
import re

# ファイル名やURLのリストを設定
#file_name = "test_syuugakutest1.py"
ide_testf = f"{sys.argv[1]}/original/test_org.py"
old_pageobject_name = "old_pageobject.py"
class_name = "page_class"
new_pageobject_fname = "page_object"
test_fname ="test.py"
old_test_fname = "old_test.py"
scenario = sys.argv[1]


#self.driver.current_urlを書き込む関数
def add_print_statements(input_file, output_file, start_line, end_line):
  with open(input_file, 'r', encoding="UTF-8") as infile:
    lines = infile.readlines()

  modified_lines = []
  for i, line in enumerate(lines, 1):
    if i < start_line:
      modified_lines.append(line)  #元の文
    elif i == start_line:
      modified_lines.append("    with open('c.txt', 'w', encoding='UTF-8') as f:\n")  # コードの追加
      modified_lines.append('  ' + line)
    else:
      modified_lines.append('  ' + line)  # インデントの追加

    if i >= start_line and i <= end_line:
      modified_lines.append('      ' + 'print(self.driver.current_url, file=f)\n')  

  with open(output_file, 'w', encoding="UTF-8") as outfile:
    outfile.writelines(modified_lines)



#取得したいコードが何行目から何行目かを取得する
def find_start_and_end_lines(input_file, target_string):
  with open(input_file, 'r', encoding='UTF-8') as f:
    lines = [x.rstrip() for x in f.readlines()]
    lines.pop()

  start_line = None
  end_line = None

  for i, line in enumerate(lines, 1):
    if target_string in line:
      if start_line is None:
        start_line = i

    else:
      end_line = i

  return start_line, end_line


#特定の範囲のコードを取得する関数
def extract_code(input_file, start_line, end_line):
  with open(input_file, 'r', encoding='UTF-8') as f:
    lines = [x.rstrip() for x in f.readlines()]

  extracted_code = lines[start_line - 1:end_line]  # POに移したいコードの開始行から終了行までのコードを抽出
  return extracted_code


#コードをURLごとに分割 URLのリストも取得
def divide_code(code_lines):
  with open('c.txt', 'r', encoding='UTF-8')as f1:
      lines = f1.readlines()

  list_url = []
  divided_codes = []
  current_url = lines[0]
  x = 0

  list_url.append(current_url)
  for i, line in enumerate(lines):
      if line != current_url:
          # ここで 1 ブロック確定
          block = code_lines[x:i+1]
          if block:                 # ★空ブロックは捨てる
              divided_codes.append(block)
          else:
              # ★空なら URL も増やさない（同期維持）
              list_url.pop()

          current_url = line
          list_url.append(current_url)
          x = i+1

  # 最後のブロック
  last_block = code_lines[x:]
  if last_block:                   # ★空ブロックは捨てる
      divided_codes.append(last_block)
  else:
      # ★最後が空なら URL も消して同期させる
      list_url.pop()

  list_url = [x.rstrip() for x in list_url]
  return divided_codes, list_url



def genelate_new_testfile(oldtestf, newtestf):
  with open(oldtestf, 'r', encoding='UTF-8') as f:
    file_content = f.read()

  with open(newtestf, 'w', encoding='UTF-8') as f1:
    f1.write(file_content)



#テストファイルのテストの関数をメソッドの形に変更する
def testf_replacement_method(file, old_str, new_str):
  with open(file, 'r', encoding='UTF-8') as f:
    file_content = f.read()

  file_content = file_content.replace(old_str, new_str)
  with open(file, 'w', encoding='UTF-8') as f1:
    f1.write(file_content)
    


#分割したコードをページオブジェクトのそれぞれのメソッドに保存する
def save_code_as_pageobject(output_file, method_data, class_name):
  with open(output_file, 'w', encoding="UTF-8") as f:
    print("from selenium import webdriver", file=f)
    print("from selenium.webdriver.common.by import By", file=f)
    print("from selenium.webdriver.common.keys import Keys", file=f)
    print("from selenium.webdriver.support.ui import Select", file=f)
    print("from selenium.webdriver.support.wait import WebDriverWait", file=f)
    print("from selenium.common.exceptions import TimeoutException", file=f)
    print("from selenium.webdriver.support import expected_conditions", file=f)
    print("import time", file=f)
    print(f"\n\nclass {class_name}:", file=f)
    print("    def __init__(self, driver):", file=f)
    print("        self.driver = driver\n", file=f)

    for method_name, code_lines in method_data.items():
      print(f"    #{code_lines[0]}", file = f)
      print(f"    def {method_name}(self):", file=f)

      
      testf_replacement_method(test_fname, '\n'.join(code_lines[1]), f"    {class_name}.{method_name}(self)")

      
      for line in code_lines[1]:
        print(f"    {line}", file=f)
      print("\n", file=f)

#行を指定してファイルに一行追加する
def insert_line_to_file(file_path, line, line_number):
    with open(file_path, 'r', encoding='UTF-8') as file:
        lines = file.readlines()

    lines.insert(line_number - 1, line + '\n')

    with open(file_path, 'w', encoding='UTF-8') as file:
        file.writelines(lines)
  
#selectタグの処理
def select_process(test_fname):
  with open(test_fname, 'r', encoding='UTF-8') as f:
    lines = f.readlines()

  new_lines = []
  for i,line in enumerate(lines):
    if i == 11:
      new_lines.append("from selenium.webdriver.support.ui import Select\n")

    #通常のプルダウン処理
    if line.strip().startswith("dropdown.") and line.strip().endswith(".click()"):
      #new_lines.append("    select = Select(dropdown)\n")
      match = re.search(r"'(.*?)'", line)

      if match:
        extracted_text = match.group(1)
        new_lines.append(f"    Select(dropdown).select_by_visible_text('{extracted_text}')\n")
        
    else:
      new_lines.append(line)

  with open(test_fname, 'w', encoding='UTF-8') as f:
    f.writelines(new_lines)

# テストファイルを複製する(IDEで生成したオリジナルを保持)
genelate_new_testfile(ide_testf, old_test_fname)

#IDEで生成したファイルのselect文を処理
select_process(old_test_fname)

# テストファイルを複製する
genelate_new_testfile(old_test_fname , test_fname)

# ページオブジェクトを作成するために必要な行を自動で取得するために'self.driver.get' が含まれる行から最後の行を取得
start_line, end_line = find_start_and_end_lines(old_test_fname, 'self.driver.get')

# start_lineから始まり、1行ごとに「'      ' + 'print(self.driver.current_url, file=f)\n'」を追加する
add_print_statements(old_test_fname, 'output.py', start_line, end_line)

subprocess.run(["pytest", "output.py"])

print(f"コードの開始行: {start_line}, 終了行: {end_line}")
#print(divide_code(extract_code(sys.argv[1], start_line, end_line)))
method_code = extract_code(old_test_fname, start_line, end_line)

#print(method_code)

#ページオブジェクトを得るために必要なメソッドごとにコードを分ける
divided_codes, list_url = divide_code(method_code)

#pageのコードとURLを辞書の形にする
method_and_url_list = []
for i in range(len(divided_codes)):
  list1 = []
  list1.append(list_url[i])
  list1.append(divided_codes[i])
  method_and_url_list.append(list1) 

#print(method_and_url_list)

method_name = {}
for i, ele in enumerate(method_and_url_list, 1):
  method_name.setdefault(f'page_{i}', ele)

#ページオブジェクトを作成
save_code_as_pageobject(old_pageobject_name , method_name, class_name)

#import文を挿入
insert_line_to_file(test_fname, f"from {new_pageobject_fname} import {class_name}", 12)

#各フォルダに生成したファイルを移動
#original_folder_name = "original"
new_folder_name = "new"
trash_folder_name  = "byproduct"

#os.makedirs(f"{scenario}/{original_folder_name}")
os.makedirs(f"{scenario}/{new_folder_name}")
os.makedirs(f"{scenario}/{trash_folder_name}")

shutil.move("c.txt", f"{scenario}/{trash_folder_name}") 
shutil.move("output.py", f"{scenario}/{trash_folder_name}") 
shutil.move(old_test_fname, f"{scenario}/{trash_folder_name}") 
shutil.move(test_fname, f"{scenario}/{new_folder_name}") 
shutil.move(old_pageobject_name, "tool")