import os
import sys
import csv
import re
import time
import argparse
from typing import List, Dict

import pandas as pd
from bs4 import BeautifulSoup, Comment
from bs4.element import Tag

# ====== 設定 ======
SELF_CLOSING_TAGS = {'meta', 'img', 'br', 'hr', 'input', 'link'}

# ====== 正規化ユーティリティ ======
def sort_attrs(tag: Tag):
    """属性順をアルファベット順に整列（比較の安定化）"""
    if not hasattr(tag, 'attrs') or not isinstance(tag.attrs, dict):
        return
    # BeautifulSoupは属性値がlistの場合があるので、文字列化して安定化
    sorted_items = sorted(
        (k, " ".join(v) if isinstance(v, list) else ("" if v is True else str(v)))
        for k, v in tag.attrs.items()
    )
    tag.attrs.clear()
    for k, v in sorted_items:
        # Trueは属性のみ指定(HTML5 boolean)だが、文字列化側に寄せる
        tag.attrs[k] = v

def remove_nodes_by_selectors(soup: BeautifulSoup, selectors: List[str]):
    """CSSセレクタで指定されたノードを削除"""
    for sel in selectors:
        for el in soup.select(sel):
            el.decompose()

def strip_scripts(soup: BeautifulSoup):
    """<script>, <style>, <noscript> を除去"""
    for t in soup(["script", "style", "noscript"]):
        t.decompose()

def strip_comments(soup: BeautifulSoup):
    """HTMLコメントを除去"""
    for c in soup.find_all(string=lambda text: isinstance(text, Comment)):
        c.extract()

def mask_formkey_and_csrf(html: str) -> str:
    """
    CSRF/トークン類をマスク。
    - name="form_key" value="xxxxx" → value="__FORM_KEY__"
    - form_key="xxxxx" → form_key="__FORM_KEY__"
    - csrf|token系属性も __TOKEN__ に
    """
    patterns = [
        (r'(name\s*=\s*["\']form_key["\']\s*[^>]*value\s*=\s*["\']).*?(["\'])', r'\1__FORM_KEY__\2'),
        (r'(form_key\s*=\s*["\']).*?(["\"])', r'\1__FORM_KEY__\2'),
        (r'((?:csrf|token|auth|nonce)[-_]?(?:token|key|nonce)?\s*=\s*["\']).*?(["\"])', r'\1__TOKEN__\2'),
    ]
    for pat, rep in patterns:
        html = re.sub(pat, rep, html, flags=re.IGNORECASE)
    return html

def mask_random_ids_and_attrs(html: str) -> str:
    """
    毎回揺れるID/クライアント生成らしい属性をマスク。
    - id="idXXXX" → id="__AUTO_ID__"
    - data-*, aria-* などで不安定な値にありがちな連番/ランダムを雑にマスク
    """
    html = re.sub(r'(id\s*=\s*["\'])id[-_a-zA-Z0-9]+(["\"])', r'\1__AUTO_ID__\2', html)
    # data-foo="乱数/uuid/10桁以上数字" → __DATA__
    html = re.sub(
        r'(data-[a-zA-Z0-9_-]+\s*=\s*["\'])[a-f0-9-]{8,}(["\"])',
        r'\1__DATA__\2',
        html,
        flags=re.IGNORECASE,
    )
    # nonce=... → __NONCE__
    html = re.sub(
        r'(nonce\s*=\s*["\']).*?(["\"])',
        r'\1__NONCE__\2',
        html,
        flags=re.IGNORECASE,
    )

    # 一般的な静的ファイルのバージョン番号をマスク
    # /static/version1234567890/ → /static/version__VER__/
    html = re.sub(r'(/static/version)\d+(/)', r'\1__VER__\2', html)

    # ?v=1234567890 や ?_=123456 などのクエリ → __VER__
    html = re.sub(r'([?&](?:v|_)=)\d+', r'\1__VER__', html)

    # app.css?123456 や app.js?abcdef など → __VER__
    html = re.sub(
        r'(\.(?:css|js)\?)[0-9a-fA-F]+',
        r'\1__VER__',
        html,
    )

    return html


def zero_timestamps(html: str) -> str:
    """
    タイムスタンプ/epochらしき数字をゼロ化
    - "timestamp": 1234567890 → "timestamp": 0
    - 10桁以上の連続数字を __NUM__ に（副作用注意）
    """
    # \10 だと「グループ10」扱いになるので \g<1>0 を使う
    html = re.sub(r'("timestamp"\s*:\s*)\d+', r'\g<1>0', html, flags=re.IGNORECASE)
    html = re.sub(r'(\b\d{10,}\b)', '__NUM__', html)
    return html


def normalize_html_text(raw: str,
                        strip_scripts_flag: bool,
                        mask_formkey_flag: bool,
                        mask_random_id_flag: bool,
                        zero_timestamp_flag: bool,
                        exclude_selectors: List[str],
                        body_only_flag: bool = False) -> str:
    """正規化: 文字列→(マスク/除去)→Soup→(除去/属性順)→整形HTML"""
    # 文字列段階でのマスク（正規表現）
    if mask_formkey_flag:
        raw = mask_formkey_and_csrf(raw)
    if mask_random_id_flag:
        raw = mask_random_ids_and_attrs(raw)
    if zero_timestamp_flag:
        raw = zero_timestamps(raw)

    soup = BeautifulSoup(raw, "html.parser")

    # ★ 追加: body-only の場合は <body> 以下だけに絞る
    if body_only_flag and soup.body is not None:
        soup = soup.body

    # セレクタ除外を先に
    if exclude_selectors:
        remove_nodes_by_selectors(soup, exclude_selectors)

    if strip_scripts_flag:
        strip_scripts(soup)

    strip_comments(soup)

    # 属性順ソート
    for tag in soup.find_all(True):
        sort_attrs(tag)

    # 空白の冗長さを抑えつつ、安定化したHTML文字列に戻す
    norm = soup.decode(formatter="minimal")
    norm = re.sub(r'[ \t]+', ' ', norm)
    norm = re.sub(r'\r\n?', '\n', norm).strip()
    return norm


# ====== タグ列の生成（従来ロジック） ======
def traverse(tag: Tag, tags_list: List[str]):
    tags_list.append(f"<{tag.name}>")
    for child in tag.children:
        if isinstance(child, Tag):
            traverse(child, tags_list)
    if tag.name not in SELF_CLOSING_TAGS:
        tags_list.append(f"</{tag.name}>")

def build_tree_from_list(tags: List[str]):
    root = []
    stack = [(None, root)]
    for t in tags:
        if t.startswith("</"):
            stack.pop()
        else:
            name = t[1:-1]
            node = {name: []}
            stack[-1][1].append(node)
            if name not in SELF_CLOSING_TAGS:
                stack.append((name, node[name]))
    return root

def process_html_text(normalized_html: str):
    tags_list: List[str] = []
    soup = BeautifulSoup(normalized_html, "html.parser")
    for element in soup.contents:
        if isinstance(element, Tag):
            traverse(element, tags_list)
    return build_tree_from_list(tags_list)

# ====== ツリー&距離 ======
class DictTree:
    def __init__(self, data):
        if isinstance(data, list) and len(data) == 0:
            self.label = None
            self.children = []
        elif isinstance(data, list) and len(data) == 1 and isinstance(data[0], dict):
            self.label = next(iter(data[0].keys()))
            child_data = data[0][self.label]
            self.children = [DictTree([child]) for child in child_data] if isinstance(child_data, list) else []
        else:
            raise ValueError("Invalid data format")

    def degree(self): return len(self.children)

def cost_graft(tree: 'DictTree') -> int:
    if tree.label is None: return 0
    return 1 + sum(cost_graft(c) for c in tree.children)

def cost_prune(tree: 'DictTree') -> int:
    if tree.label is None: return 0
    return 1 + sum(cost_prune(c) for c in tree.children)

def edit_distance(A: 'DictTree', B: 'DictTree') -> int:
    if A.label is None and B.label is None: return 0
    if A.label is None: return cost_graft(B)
    if B.label is None: return cost_prune(A)

    M, N = A.degree(), B.degree()
    dist = [[0]*(N+1) for _ in range(M+1)]
    dist[0][0] = 0 if A.label == B.label else 1
    for j in range(1, N+1): dist[0][j] = dist[0][j-1] + cost_graft(B.children[j-1])
    for i in range(1, M+1): dist[i][0] = dist[i-1][0] + cost_prune(A.children[i-1])
    for i in range(1, M+1):
        for j in range(1, N+1):
            dist[i][j] = min(
                dist[i-1][j-1] + edit_distance(A.children[i-1], B.children[j-1]),
                dist[i][j-1]   + cost_graft(B.children[j-1]),
                dist[i-1][j]   + cost_prune(A.children[i-1])
            )
    return dist[M][N]

# ====== I/O ======
def normalize_file_to_tree(path: str,
                           strip_scripts_flag: bool,
                           mask_formkey_flag: bool,
                           mask_random_id_flag: bool,
                           zero_timestamp_flag: bool,
                           exclude_selectors: List[str],
                           body_only_flag: bool = False) -> DictTree:
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        raw = f.read()
    norm = normalize_html_text(
        raw,
        strip_scripts_flag=strip_scripts_flag,
        mask_formkey_flag=mask_formkey_flag,
        mask_random_id_flag=mask_random_id_flag,
        zero_timestamp_flag=zero_timestamp_flag,
        exclude_selectors=exclude_selectors,
        body_only_flag=body_only_flag,
    )
    tree = DictTree(process_html_text(norm))
    return tree


def compare_multiple_html_files(base_dir: str, target_dir: str, args):
    # 基準HTMLのツリーを事前生成
    base_trees: Dict[str, DictTree] = {}
    for file_name in os.listdir(base_dir):
        if file_name.endswith(".html"):
            full_path = os.path.join(base_dir, file_name)
            base_trees[file_name] = normalize_file_to_tree(
                full_path,
                args.strip_scripts, args.mask_formkey,
                args.mask_random_id, args.zero_timestamp,
                args.exclude,
                args.body_only,
            )

    # target_dir直下のサブフォルダを調査
    for subdir in sorted(os.listdir(target_dir)):
        subdir_path = os.path.join(target_dir, subdir)
        if not os.path.isdir(subdir_path):
            continue
        csv_path = os.path.join(subdir_path, f"report_{subdir}.csv")
        rows = [['file_name', 'edit_distance']]

        for file_name in os.listdir(subdir_path):
            if not file_name.endswith(".html"): continue
            if file_name not in base_trees:     continue
            target_path = os.path.join(subdir_path, file_name)
            target_tree = normalize_file_to_tree(
                target_path,
                args.strip_scripts, args.mask_formkey,
                args.mask_random_id, args.zero_timestamp,
                args.exclude,
                args.body_only,
            )
            dist = edit_distance(base_trees[file_name], target_tree)
            print(f"[{subdir}] {file_name}: 距離 = {dist}")
            rows.append([file_name, dist])

        # CSV出力と連番ソート
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f); writer.writerows(rows)
        try:
            df = pd.read_csv(csv_path)
            df['file_number'] = df['file_name'].apply(lambda x: int(re.search(r'\d+', x).group()))
            df.sort_values(by='file_number').drop(columns=['file_number']).to_csv(csv_path, index=False)
        except Exception as e:
            print(f"[{subdir}] CSVソート中にエラー発生: {e}")

def compare_standard_files(base_dir: str, args):
    """BASE_DIR vs BASE_DIR（新規群などの一括比較）"""
    base_trees: Dict[str, DictTree] = {}
    for file_name in os.listdir(base_dir):
        if file_name.endswith(".html"):
            full_path = os.path.join(base_dir, file_name)
            base_trees[file_name] = normalize_file_to_tree(
                full_path,
                args.strip_scripts, args.mask_formkey,
                args.mask_random_id, args.zero_timestamp,
                args.exclude,
                args.body_only,
            )

    csv_path = os.path.join(base_dir, "report_new.csv")
    rows = [["file_name", "edit_distance"]]
    for file_name in os.listdir(base_dir):
        if not file_name.endswith(".html"): continue
        if file_name not in base_trees:     continue
        mutant_path = os.path.join(base_dir, file_name)
        mutant_tree = normalize_file_to_tree(
            mutant_path,
            args.strip_scripts, args.mask_formkey,
            args.mask_random_id, args.zero_timestamp,
            args.exclude,
            args.body_only,
        )
        dist = edit_distance(base_trees[file_name], mutant_tree)
        print(f"[new] {file_name}: 距離 = {dist}")
        rows.append([file_name, dist])

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f); writer.writerows(rows)
    try:
        df = pd.read_csv(csv_path)
        df['file_number'] = df['file_name'].apply(lambda x: int(re.search(r'\d+', x).group()))
        df.sort_values(by='file_number').drop(columns=['file_number']).to_csv(csv_path, index=False)
    except Exception as e:
        print(f"[new] CSVソート中にエラー発生: {e}")

# ====== main ======
def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("base_dir", help="基準HTML群のディレクトリ")
    p.add_argument("target_dir", help="比較対象フォルダ群の親ディレクトリ")
    p.add_argument("--strip-scripts", action="store_true",
                   help="script/style/noscriptの除去")
    p.add_argument("--mask-formkey", action="store_true",
                   help="CSRF/form_key/トークンのマスク")
    p.add_argument("--mask-random-id", action="store_true",
                   help="ランダムIDやdata-*, nonce等のマスク")
    p.add_argument("--zero-timestamp", action="store_true",
                   help="タイムスタンプ/epoch数値のゼロ化")
    p.add_argument("--exclude", type=str, default="",
                   help="除外CSSセレクタ(カンマ区切り) 例: '#minicart,.modal'")
    # ★ 追加：<body> 以下だけを見るオプション
    p.add_argument("--body-only", action="store_true",
                   help="HTMLの<body>以下だけを比較対象にする（<head>や外枠は無視）")

    args = p.parse_args()
    args.exclude = [s.strip() for s in args.exclude.split(",") if s.strip()]
    return args


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python html_editdistance.py BASE_DIR TARGET_DIR [options]")
        sys.exit(1)

    args = parse_args()
    start = time.perf_counter()
    compare_multiple_html_files(args.base_dir, args.target_dir, args)
    compare_standard_files(args.base_dir, args)
    end = time.perf_counter()
    print(f"実行時間: {end - start:.4f} 秒")
