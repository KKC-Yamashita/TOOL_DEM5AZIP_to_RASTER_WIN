# ==================================================
# check_fgd_dem_metadata.py
# 基盤地図情報DEM 測地系・仕様整合性チェッカー
# ==================================================

import os
import zipfile
import xml.etree.ElementTree as ET
import pandas as pd

# --------------------------------------------------
# 設定
# --------------------------------------------------

# 対象のZIPファイル、またはZIPが格納されているフォルダパス
target_path = r"C:\path\to\your_dem_data.zip"

# 出力するCSVファイルのパス
output_csv = r"C:\path\to\fgd_dem_metadata_report.csv"

# --------------------------------------------------
# ZIP一覧の取得
# --------------------------------------------------

zip_files = []
if os.path.isfile(target_path) and target_path.lower().endswith(".zip"):
    zip_files.append(target_path)
elif os.path.isdir(target_path):
    zip_files = [
        os.path.join(target_path, f)
        for f in os.listdir(target_path)
        if f.lower().endswith(".zip")
    ]
else:
    raise FileNotFoundError("指定されたファイルまたはフォルダが見つかりません。")

# --------------------------------------------------
# XMLメタデータの抽出処理
# --------------------------------------------------

records = []

for zpath in zip_files:
    zip_name = os.path.basename(zpath)
    with zipfile.ZipFile(zpath, "r") as zf:
        xml_names = [f for f in zf.namelist() if f.lower().endswith(".xml")]

        for xname in xml_names:
            try:
                content = zf.read(xname)
                root = ET.fromstring(content)

                # 1. 座標参照系 (srsName) の取得
                envelope = None
                for elem in root.iter():
                    if elem.tag.endswith("Envelope"):
                        envelope = elem
                        break
                srs_name = envelope.attrib.get("srsName", "不明") if envelope is not None else "なし"
                crs = srs_name.split(":")[-1].replace(".bl", "").upper()

                # 2. DEM種別 (type) と メッシュコード (mesh)
                dem_type = "不明"
                mesh_code = "不明"
                for elem in root.iter():
                    if elem.tag.endswith("type"):
                        dem_type = elem.text.strip()
                    elif elem.tag.endswith("mesh"):
                        mesh_code = elem.text.strip()

                # 3. ファイル名から作成年月日（yyyymmdd）と種別を抽出
                # 例: FG-GML-5336-06-77-DEM5A-20161001.xml
                parts = os.path.splitext(xname)[0].split("-")
                date_str = parts[-1] if len(parts) >= 5 and parts[-1].isdigit() else "不明"
                dem_category = parts[-2] if len(parts) >= 5 else "不明"

                records.append({
                    "ZIP名": zip_name,
                    "XMLファイル名": os.path.basename(xname),
                    "メッシュコード": mesh_code,
                    "測地系": crs,
                    "DEM種別": dem_type,
                    "種別記号": dem_category,
                    "作成日": date_str,
                    "生srsName": srs_name
                })
            except Exception as e:
                records.append({
                    "ZIP名": zip_name,
                    "XMLファイル名": os.path.basename(xname),
                    "メッシュコード": "エラー",
                    "測地系": "エラー",
                    "DEM種別": "-",
                    "種別記号": "-",
                    "作成日": "-",
                    "生srsName": str(e)
                })

# --------------------------------------------------
# 集計と画面表示
# --------------------------------------------------

df = pd.DataFrame(records)

print(f"検査したXMLファイル総数: {len(df)} 件\n")

unique_crs = df["測地系"].unique()
unique_types = df["DEM種別"].unique()
unique_dates = df["作成日"].unique()

print("=" * 50)
print("【相違点・混在チェック結果】")
print("=" * 50)

if len(unique_crs) > 1:
    print(f"⚠️ 警告: 複数の測地系が混在しています -> {list(unique_crs)}")
else:
    print(f"✔ 測地系: 統一されています ({unique_crs[0]})")

if len(unique_types) > 1:
    print(f"⚠️ 警告: 複数のDEM種別が混在しています -> {list(unique_types)}")
else:
    print(f"✔ DEM種別: 統一されています ({unique_types[0]})")

if len(unique_dates) > 1:
    print(f"ℹ️ 備考: 作成時期（計測日）が複数存在します -> {list(unique_dates)}")
else:
    print(f"✔ 作成日: 統一されています ({unique_dates[0]})")

print("=" * 50)

# --------------------------------------------------
# CSVファイルへ出力
# --------------------------------------------------

# 出力先ディレクトリが存在しない場合は作成
os.makedirs(os.path.dirname(os.path.abspath(output_csv)), exist_ok=True)

# Excel対応のためBOM付きUTF-8 (utf-8-sig) で出力
df.to_csv(output_csv, index=False, encoding="utf-8-sig")

print(f"\n詳細レポートをCSVに出力しました:")
print(f" -> {output_csv}")