import requests

from database import save_economic_data


API_URL = "https://www.stat-search.boj.or.jp/api/v1/getDataCode"

DB_NAME = "IR01"
SERIES_CODE = "MADR1M"


def fetch_boj_data():
    params = {
        "format": "json",
        "lang": "jp",
        "db": DB_NAME,
        "code": SERIES_CODE,
    }

    response = requests.get(
        API_URL,
        params=params,
        timeout=30
    )

    response.raise_for_status()

    return response.json()


def format_month(date_value):
    """
    202608 → 2026-08
    """
    text = str(date_value)

    if len(text) == 6:
        return f"{text[:4]}-{text[4:6]}"

    return text


def main():
    try:
        data = fetch_boj_data()

        print("日本銀行APIからデータを取得しました")

        resultset = data.get("RESULTSET", [])

        if not resultset:
            print("RESULTSETにデータがありません。")
            return

        series = resultset[0]

        print("系列名:", series.get("NAME_OF_TIME_SERIES_J"))
        print("単位:", series.get("UNIT_J"))
        print("頻度:", series.get("FREQUENCY"))

        value_data = series.get("VALUES", {})

        dates = value_data.get("SURVEY_DATES", [])
        values = value_data.get("VALUES", [])

        print("日付件数:", len(dates))
        print("値件数:", len(values))

        if not dates or not values:
            print("日付または値を取得できませんでした。")
            return

        if len(dates) != len(values):
            print("日付件数と値件数が一致していません。")
            return

        records = []

        for date, value in zip(dates, values):
            if value is None:
                continue

            try:
                numeric_value = float(value)
            except (TypeError, ValueError):
                continue

            month = format_month(date)

            records.append(
                (
                    month,
                    numeric_value
                )
            )

        if not records:
            print("保存できるデータがありません。")
            return

        for month, value in records:
            save_economic_data(
                source="BOJ",
                indicator="basic_loan_rate",
                date=month,
                value=value,
                unit="%"
            )

        latest_month, latest_value = records[-1]

        print()
        print("===== 日本銀行 基準割引率・基準貸付利率 =====")
        print("保存件数:", len(records))
        print("最新年月:", latest_month)
        print("最新金利:", latest_value, "%")

    except requests.RequestException as e:
        print("日本銀行API通信エラー:", e)

    except Exception as e:
        print("エラー:", e)


if __name__ == "__main__":
    main()