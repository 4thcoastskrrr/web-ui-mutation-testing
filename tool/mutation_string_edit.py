import sys
import os
import re
import shutil
import random
from typing import List, Tuple


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

# ========= 設定（各ミューテーションの上限設定） =========

# 1行あたりの生成上限数（各タイプごと）
LIMIT_SYMBOL_INSERT = 7      # 記号追加の最大数
LIMIT_PARTIAL_DELETE = 3      # 部分削除の最大数
LIMIT_ADJACENT_SWAP = 3       # 隣接入替の最大数

# 多くの記号候補をスペース区切りで並べた「文字列」
SYMBOLS = "! @ # $ % ^ & * ( ) - _ + = [ ] { } ; : ' \" , . / ? \\ | ~ `"

# POSITIONS 設定は内部ロジックで使用（0=先頭, -1=末尾）
POSITIONS = [0, -1]


# ========= send_keys 検出 =========
SEND_KEYS_RE = re.compile(
    r'(\.send_keys\(\s*)([\'"])(.*?)(?<!\\)\2(\s*\))'
)

def find_send_keys_lines(lines: List[str]) -> List[int]:
    """1行内に .send_keys(".") / ('.') を含む行番号（0-based）を返す。"""
    return [i for i, line in enumerate(lines) if SEND_KEYS_RE.search(line)]

def replace_send_keys_literal(line: str, new_literal: str) -> str:
    """
    行中の最初の send_keys(.) の文字列リテラルだけを new_literal に置換。
    書き戻しは常にダブルクォート。内部の \ と " はエスケープ。
    """
    def _repl(m):
        prefix, _q, _old, suffix = m.groups()
        safe = new_literal.replace('\\', '\\\\').replace('"', r'\"')
        return f'{prefix}"{safe}"{suffix}'
    return SEND_KEYS_RE.sub(_repl, line, count=1)

# ========= 決定的ミューテーション生成 =========
def _real_positions(s: str) -> List[int]:
    """POSITIONS（0, -1）を実長に変換し、重複排除。"""
    n = len(s)
    out: List[int] = []
    for p in POSITIONS:
        pos = 0 if p == 0 else n  # -1 は末尾 = index n
        if pos not in out:
            out.append(pos)
    return out

def gen_symbol_insertions_limited(s: str) -> List[Tuple[str, str]]:
    """
    記号挿入:
      - SYMBOLS リストをランダムシャッフル
      - 各記号につき、先頭/末尾の **どちらか一方にランダムで** 挿入
      - 全候補を返し、呼び出し元で上限数(LIMIT_SYMBOL_INSERT)によりカットする
    """
    out: List[Tuple[str, str]] = []

    symbol_candidates = SYMBOLS.split()
    random.shuffle(symbol_candidates) # ランダム性を確保

    positions = _real_positions(s)

    for sym in symbol_candidates:
        if not positions:
            continue
        
        # 先頭または末尾のどちらか一方をランダム選択
        pos = random.choice(positions)
        
        mutated = s[:pos] + sym + s[pos:]
        out.append(("symbol_insert", mutated))

    # 重複除去
    uniq: List[Tuple[str, str]] = []
    seen = {s}
    for k, v in out:
        if v not in seen:
            uniq.append((k, v)); seen.add(v)
    return uniq

def gen_partial_deletions(s: str) -> List[Tuple[str, str]]:
    """部分削除: 先頭削除 / 末尾削除 / 中央ブロック削除"""
    out: List[Tuple[str, str]] = []
    n = len(s)
    if n == 0:
        return [("partial_delete", "")]
    
    out.append(("partial_delete", s[1:]))     # 先頭削除
    out.append(("partial_delete", s[:-1]))    # 末尾削除
    
    if n >= 3:
        i, j = n // 3, (2 * n) // 3
        if j <= i:
            j = min(n, i + 1)
        out.append(("partial_delete", s[:i] + s[j:]))  # 中央削除

    # 重複除去
    uniq: List[Tuple[str, str]] = []
    seen = {s}
    for k, v in out:
        if v not in seen:
            uniq.append((k, v)); seen.add(v)
    return uniq

def gen_adjacent_swaps_all(s: str) -> List[Tuple[str, str]]:
    """隣接入替: 左から順に可能な交換をすべて生成"""
    out: List[Tuple[str, str]] = []
    n = len(s)
    for i in range(max(0, n - 1)):
        mutated = s[:i] + s[i+1] + s[i] + s[i+2:]
        out.append(("adjacent_swap", mutated))
    
    # 重複除去
    uniq: List[Tuple[str, str]] = []
    seen = {s}
    for k, v in out:
        if v not in seen:
            uniq.append((k, v)); seen.add(v)
    return uniq

# ========= 出力ユーティリティ =========
def _write_mutant(project_root: str,
                  base_lines: List[str],
                  target_line_idx: int,
                  kind: str,
                  mutated_value: str,
                  serial_num: int) -> None:
    """
    mutants/04_### を作成しファイルを出力
    """
    out_folder = os.path.join(project_root, "mutants", f"04_{str(serial_num).zfill(3)}")
    os.makedirs(out_folder, exist_ok=True)

    new_lines = list(base_lines)
    new_lines[target_line_idx] = replace_send_keys_literal(new_lines[target_line_idx], mutated_value)

    out_po = os.path.join(out_folder, "page_object.py")
    with open(out_po, "w", encoding="utf-8") as f:
        f.writelines(new_lines)

    # 既存インストゥルメントを注入
    add_webdriverwait(out_po)
    add_html(out_po)
    add_screenshot_code(out_po)

    # 付帯ファイル
    src_test = os.path.join(project_root, "new", "test.py")
    src_loc = os.path.join(project_root, "new", "locators.py")
    if os.path.exists(src_test): shutil.copy(src_test, out_folder)
    if os.path.exists(src_loc): shutil.copy(src_loc, out_folder)

    # メタ情報
    with open(os.path.join(out_folder, "MUTATION_INFO.txt"), "w", encoding="utf-8") as f:
        f.write(f"target_line={target_line_idx+1}\n")
        f.write(f"kind={kind}\n")
        safe_val = mutated_value[:1000].replace("\n", "\\n")
        f.write(f"value={safe_val}\n")

# 元の new/page_object.py にだけ WebDriverWait / HTML保存 / スクショ保存を追加するスクリプト
def instrument_page_object(project_root):
    target_po = os.path.join(project_root, "new", "page_object.py")
    if not os.path.exists(target_po):
        print(f"not found: {target_po}")
        return

    add_webdriverwait(target_po)
    add_html(target_po)
    add_screenshot_code(target_po)
    print(f"instrumented: {target_po}")

# ========= メイン =========
def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python mutation_string_edit_deterministic.py <project_root>")
        sys.exit(1)

    project_root = sys.argv[1]
    src_po = os.path.join(project_root, "new", "page_object.py")
    if not os.path.exists(src_po):
        print(f"not found: {src_po}")
        sys.exit(1)

    with open(src_po, "r", encoding="utf-8") as f:
        lines = f.readlines()

    target_idxs = find_send_keys_lines(lines)
    if not target_idxs:
        print("send_keys(.) が見つかりませんでした。")
        sys.exit(0)

    serial = 1
    for idx in target_idxs:
        m = SEND_KEYS_RE.search(lines[idx])
        if not m:
            continue
        seed_value = m.group(3)

        candidates: List[Tuple[str, str]] = []

        # 1) 記号追加 (上限 LIMIT_SYMBOL_INSERT)
        # 既にランダム順・ランダム位置選択になっているので、先頭からスライスするだけでOK
        cand_symbols = gen_symbol_insertions_limited(seed_value)
        candidates.extend(cand_symbols[:LIMIT_SYMBOL_INSERT])

        # 2) 部分削除 (上限 LIMIT_PARTIAL_DELETE)
        cand_deletes = gen_partial_deletions(seed_value)
        candidates.extend(cand_deletes[:LIMIT_PARTIAL_DELETE])

        # 3) 隣接入替 (上限 LIMIT_ADJACENT_SWAP)
        cand_swaps = gen_adjacent_swaps_all(seed_value)
        candidates.extend(cand_swaps[:LIMIT_ADJACENT_SWAP])

        # 書き出し
        for kind, mutated in candidates:
            _write_mutant(project_root, lines, idx, kind, mutated, serial)
            serial += 1

        print(f"[line {idx+1}] seed='{seed_value}' -> generated={len(candidates)} mutants")

    print(f"done. generated {serial-1} mutants under {os.path.join(project_root, 'mutants')}")
    
    # 最後に元のファイルにも注入を実行
    instrument_page_object(project_root)

if __name__ == "__main__":
    main()