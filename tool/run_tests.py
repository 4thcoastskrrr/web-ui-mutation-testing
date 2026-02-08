import os
import subprocess
import sys
import time


start = time.perf_counter()

# 対象ディレクトリを指定
target_directory = sys.argv[1]


# ログ保存ディレクトリ
log_dir = os.path.join(target_directory, "pytest_logs")
os.makedirs(log_dir, exist_ok=True)

# test.py ファイルを検索して pytest を実行
for root, _, files in os.walk(target_directory):
    for file in files:
        if file == "test.py":
            file_path = os.path.join(root, file)
            print(f"Running pytest on: {file_path}")

            # 各 test.py ごとにログファイル名を作成（日時＋ディレクトリ名）
            folder_name = os.path.basename(root)
            log_path = os.path.join(log_dir, f"{folder_name}.log")

            # pytestを実行し、出力をファイルに書き出す
            with open(log_path, "w", encoding="utf-8") as log_file:
                subprocess.run(
                    ["pytest", file, "-v", "-s"],
                    cwd=root,
                    stdout=log_file,
                    stderr=subprocess.STDOUT
                )

            print(f"→ ログを保存しました: {log_path}\n")



end = time.perf_counter()
print(f"実行時間: {end - start:.4f} 秒")