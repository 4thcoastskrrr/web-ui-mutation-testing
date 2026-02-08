import argparse, csv, logging, hashlib
from pathlib import Path
import cv2, numpy as np
from skimage.metrics import structural_similarity as ssim
from PIL import Image
import time

NDIFF_DIRNAME_MATCH    = "diff_0_output"            # 一致側の出力ルート
NDIFF_DIRNAME_UNMATCH  = "diff_output_unmatched"  # 不一致側の出力ルート

# ───────────── 汎用 I/O ─────────────────────────────
def robust_load(p: Path):
    img = cv2.imread(str(p))
    if img is None:
        try:
            img = cv2.cvtColor(np.asarray(Image.open(p).convert("RGB")),
                               cv2.COLOR_RGB2BGR)
        except Exception as e:
            logging.error("[FAIL] load %s : %s", p, e)
            return None
    return img

def robust_save(img, p: Path) -> bool:
    p.parent.mkdir(parents=True, exist_ok=True)
    if cv2.imwrite(str(p), img):
        return True
    try:
        Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB)).save(p, "PNG")
        return True
    except Exception as e:
        logging.error("[FAIL] save %s : %s", p, e)
        return False

# ───────────── CSV 判定（中身が一致するか） ─────────────
def csv_fingerprint(csv_path: Path) -> str | None:
    try:
        raw = csv_path.read_bytes()
        return hashlib.sha256(raw).hexdigest()
    except Exception as e:
        logging.error("[FAIL] read %s : %s", csv_path, e)
        return None

def same_report(folder: Path, ref_hash: str) -> bool:
    """フォルダ内の *.csv のいずれかが ref_hash と一致すれば True"""
    for csv_path in folder.glob("*.csv"):
        h = csv_fingerprint(csv_path)
        if h is not None and h == ref_hash:
            return True
    return False

# ───────────── 差分検出（SSIM + 輪郭抽出） ─────────────
def diff_bbox(a, b, *, thresh=30, kernel=3, min_area=400):
    g1, g2 = cv2.cvtColor(a, cv2.COLOR_BGR2GRAY), cv2.cvtColor(b, cv2.COLOR_BGR2GRAY)
    _, m = ssim(g1, g2, full=True)
    d = ((1 - m) * 255).astype(np.uint8)
    _, bin_ = cv2.threshold(d, thresh, 255, cv2.THRESH_BINARY)
    if kernel > 0:
        k = cv2.getStructuringElement(cv2.MORPH_RECT, (kernel, kernel))
        bin_ = cv2.morphologyEx(bin_, cv2.MORPH_OPEN, k)
    cnts, _ = cv2.findContours(bin_, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    boxes = [cv2.boundingRect(c) for c in cnts if cv2.contourArea(c) >= min_area]
    if not boxes:
        return None
    out = b.copy()
    for x, y, w, h in boxes:
        cv2.rectangle(out, (x, y), (x + w, y + h), (0, 0, 255), 2)
    return out

# ───────────── メイン処理 ─────────────────────────────
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("base_dir"), ap.add_argument("target_dir")
    ap.add_argument("--threshold", type=int, default=20)
    ap.add_argument("--kernel",    type=int, default=3)
    ap.add_argument("--min-area",  type=int, default=50)
    args = ap.parse_args()

    base_dir   = Path(args.base_dir).resolve()
    target_dir = Path(args.target_dir).resolve()
    diff_root_match   = target_dir / NDIFF_DIRNAME_MATCH
    diff_root_unmatch = target_dir / NDIFF_DIRNAME_UNMATCH

    # ① 基準 CSV を base_dir から探す（最初の1つ）
    base_csvs = list(base_dir.glob("*.csv"))
    if not base_csvs:
        print(f"[ERROR] {base_dir} に .csv ファイルが見つかりません"); return
    base_csv = base_csvs[0]
    base_fp = csv_fingerprint(base_csv)
    if base_fp is None:
        print("[ERROR] 基準CSVの読み込みに失敗しました"); return

    # ② base_dir の PNG 一覧を取得（名前→Pathの辞書）
    base_pngs = {p.name: p for p in base_dir.rglob("*.png")}
    if not base_pngs:
        print(f"[ERROR] PNG が {base_dir} にありません"); return

    # ③ target_dir 以下の「PNG を持つフォルダ」を列挙して、一致/不一致に分類
    #    ここでは *.csv の有無にかかわらず、PNG が存在する最下位フォルダを候補とする
    candidate_folders = set()
    for png_path in target_dir.rglob("*.png"):
        candidate_folders.add(png_path.parent)

    matched_folders, unmatched_folders = [], []
    for folder in sorted(candidate_folders):
        # そのフォルダ内に CSV が1枚も無い場合も「不一致」グループに入れる
        if same_report(folder, base_fp):
            matched_folders.append(folder)
        else:
            unmatched_folders.append(folder)

    if not matched_folders:
        print("[INFO] 基準と同じ .csv を持つフォルダが見つかりません（一致グループなし）")
    if not unmatched_folders:
        print("[INFO] 不一致グループに該当するフォルダが見つかりません")

    # ④ 共通の処理関数
    def process_group(folders, root_out: Path, tag: str):
        proc = saved = same = 0
        for folder in folders:
            rel_folder = folder.relative_to(target_dir)
            # 差分ゼロでもディレクトリは必ず作成
            (root_out / rel_folder).mkdir(parents=True, exist_ok=True)

            for tgt in folder.rglob("*.png"):
                base = base_pngs.get(tgt.name)
                if not base:
                    # 同名の基準PNGがなければスキップ
                    continue
                proc += 1
                a, b = robust_load(base), robust_load(tgt)
                if a is None or b is None:
                    continue
                overlay = diff_bbox(a, b, thresh=args.threshold,
                                    kernel=args.kernel, min_area=args.min_area)
                if overlay is None:
                    same += 1
                    print(f"[{tag}][SAME] {tgt.relative_to(target_dir)}")
                    continue
                out_path = root_out / tgt.relative_to(target_dir).parent / f"diff_{tgt.name}"
                if robust_save(overlay, out_path):
                    saved += 1
                    print(f"[{tag}][DIFF] {tgt.relative_to(target_dir)} → "
                          f"{out_path.relative_to(target_dir)}")
        return proc, saved, same

    # ⑤ 一致/不一致をそれぞれ処理
    m_proc, m_saved, m_same = process_group(matched_folders,   diff_root_match,   "MATCH")
    u_proc, u_saved, u_same = process_group(unmatched_folders, diff_root_unmatch, "UNMATCH")

    total_proc = m_proc + u_proc
    total_saved = m_saved + u_saved
    print(f"Processed {total_proc} file(s); saved {total_saved} diff image(s)")
    print(f"  MATCH   : processed={m_proc}, saved={m_saved}, same={m_same}, out={diff_root_match}")
    print(f"  UNMATCH : processed={u_proc}, saved={u_saved}, same={u_same}, out={diff_root_unmatch}")

if __name__ == "__main__":
    start = time.perf_counter()
    logging.getLogger("cv2").setLevel(logging.ERROR)
    main()
    end = time.perf_counter()
    print(f"実行時間: {end - start:.4f} 秒")
