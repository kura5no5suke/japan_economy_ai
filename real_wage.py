import os
import requests
import xlrd

from database import save_economic_data

FILE_URL = "https://www.e-stat.go.jp/stat-search/file-download?fileKind=4&statInfId=000040277106"
FILE_PATH = "real_wage_source"


def download_real_wage_file():
    print()
    print("===== 実質賃金データ取得 =====")
    print("e-Statから最新版ファイルを取得しています...")

    response = requests.get(
        FILE_URL,
        timeout=60
    )

    print("HTTPステータス:", response.status_code)

    response.raise_for_status()

    with open(FILE_PATH, "wb") as f:
        f.write(response.content)

    print("ファイルを更新しました")
    print("保存先:", FILE_PATH)
    print("ファイルサイズ:", len(response.content), "bytes")


def get_real_wage():
    download_real_wage_file()

    book = xlrd.open_workbook(FILE_PATH)
    sheet = book.sheet_by_index(0)

    print()
    print("===== 実質賃金・前年比 =====")
    print()
    print("対象: 5人以上・就業形態計・調査産業計")
    print()

    count = 0
    latest_date = None
    latest_value = None

    for row in range(56, sheet.nrows):
        year_value = sheet.cell_value(row, 0)

        if year_value in ("", None):
            continue

        try:
            year = int(year_value)
        except (ValueError, TypeError):
            continue

        for month_index in range(12):
            col = 8 + month_index
            value = sheet.cell_value(row, col)

            if value in ("", "-", None):
                continue

            try:
                value = float(value)
            except (ValueError, TypeError):
                continue

            month = month_index + 1
            date = f"{year}-{month:02d}"

            print(
                "日付:",
                date,
                "| 実質賃金前年比:",
                value,
                "%"
            )

            save_economic_data(
                source="厚生労働省・毎月勤労統計調査",
                indicator="実質賃金_前年比",
                date=date,
                value=value,
                unit="%"
            )

            count += 1
            latest_date = date
            latest_value = value

    print()
    print("保存件数:", count)

    if latest_date is not None:
        print(
            "最新実質賃金:",
            latest_date,
            latest_value,
            "%"
        )


if __name__ == "__main__":
    get_real_wage()