import requests

from database import create_database, save_economic_data


API_URL = "https://www.stat-search.boj.or.jp/api/v1/getDataCode"

DB_NAME = "FM08"
SERIES_CODE = "FXERM09"

SOURCE = "BOJ"
INDICATOR = "usd_jpy"
UNIT = "円/ドル"


def normalize_month(survey_date):
    """
    202608 → 2026-08
    """
    text = str(survey_date)

    if len(text) != 6:
        return None

    return f"{text[:4]}-{text[4:6]}"


def get_usd_jpy_data():
    params = {
        "format": "json",
        "lang": "jp",
        "db": DB_NAME,
        "code": SERIES_CODE,
    }

    response = requests.get(
        API_URL,
        params=params,
        timeout=30,
    )

    print("日銀API HTTPステータス:", response.status_code)

    response.raise_for_status()

    data = response.json()

    if data.get("STATUS") != 200:
        raise RuntimeError(
            f"日銀APIエラー: {data.get('MESSAGE')}"
        )

    result_set = data.get("RESULTSET", [])

    if not result_set:
        raise RuntimeError("ドル円データが見つかりませんでした")

    series = result_set[0]

    print("系列名:", series.get("NAME_OF_TIME_SERIES_J"))
    print("単位:", series.get("UNIT_J"))
    print("頻度:", series.get("FREQUENCY"))
    print("最終更新:", series.get("LAST_UPDATE"))

    values_data = series.get("VALUES", {})

    survey_dates = values_data.get("SURVEY_DATES", [])
    values = values_data.get("VALUES", [])

    if len(survey_dates) != len(values):
        raise RuntimeError(
            "年月データと値データの件数が一致しません"
        )

    records = []

    for survey_date, value in zip(survey_dates, values):
        if value is None:
            continue

        month = normalize_month(survey_date)

        if month is None:
            continue

        try:
            numeric_value = float(value)
        except (TypeError, ValueError):
            continue

        records.append(
            (month, numeric_value)
        )

    return records


def save_usd_jpy_data(records):
    saved_count = 0

    for month, value in records:
        save_economic_data(
            SOURCE,
            INDICATOR,
            month,
            value,
            UNIT,
        )

        saved_count += 1

    return saved_count


def main():
    print()
    print("===== 日本銀行 ドル円 =====")

    create_database()

    records = get_usd_jpy_data()

    if not records:
        print("保存できるドル円データがありません。")
        return

    saved_count = save_usd_jpy_data(records)

    latest_month, latest_value = records[-1]

    print()
    print("===== ドル円 取得結果 =====")
    print("保存件数:", saved_count)
    print("最新年月:", latest_month)
    print("最新ドル円:", latest_value, "円/ドル")


if __name__ == "__main__":
    main()