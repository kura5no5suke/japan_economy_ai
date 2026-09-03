import os
import requests
from dotenv import load_dotenv
from database import save_economic_data

load_dotenv()

ESTAT_APP_ID = os.getenv("ESTAT_APP_ID")

STATS_DATA_ID = "0004023601"

CD_TAB = "01"
CD_CAT01 = "001100000"
CD_CAT02 = "03"
CD_AREA = "00000"

URL = "https://api.e-stat.go.jp/rest/3.0/app/json/getStatsData"


def get_consumption():

    if not ESTAT_APP_ID:
        print("ESTAT_APP_IDが設定されていません。")
        return

    params = {
        "appId": ESTAT_APP_ID,
        "statsDataId": STATS_DATA_ID,

        # 金額
        "cdTab": CD_TAB,

        # 消費支出
        "cdCat01": CD_CAT01,

        # 二人以上の世帯
        "cdCat02": CD_CAT02,

        # 全国
        "cdArea": CD_AREA,

        "cntGetFlg": "N",
        "metaGetFlg": "N",

        # 全期間
        "startPosition": "1",
        "limit": "1000",
    }

    print()
    print("===== 個人消費データ取得 =====")

    try:
        response = requests.get(
            URL,
            params=params,
            timeout=(10, 90)
        )
    except Exception as e:
        print("API接続エラー:", e)
        return

    print("HTTPステータス:", response.status_code)

    try:
        data = response.json()
    except Exception as e:
        print("JSON解析エラー:", e)
        return

    result = data["GET_STATS_DATA"]["RESULT"]

    print("APIステータス:", result["STATUS"])

    if result["STATUS"] != 0:
        print("取得失敗")
        print("エラー:", result.get("ERROR_MSG"))
        return

    statistical_data = data["GET_STATS_DATA"].get(
        "STATISTICAL_DATA",
        {}
    )

    data_inf = statistical_data.get("DATA_INF", {})

    values = data_inf.get("VALUE", [])

    if not values:
        print("データが見つかりませんでした。")
        return

    print("取得件数:", len(values))

    consumption_data = {}

    print()
    print("===== 消費支出 =====")

    for value in values:

        if (
            value.get("@tab") != CD_TAB
            or value.get("@cat01") != CD_CAT01
            or value.get("@cat02") != CD_CAT02
            or value.get("@area") != CD_AREA
        ):
            continue

        time = value.get("@time")
        number = value.get("$")

        if not time or number in ("", "-", None):
            continue

        year = time[:4]
        month = time[-2:]

        if month == "00":
            continue

        try:
            number = float(number)
        except (ValueError, TypeError):
            continue

        date = f"{year}-{month}"

        consumption_data[date] = number

    if not consumption_data:
        print("消費支出データが見つかりませんでした。")
        return

    sorted_dates = sorted(consumption_data.keys())

    save_count = 0

    for date in sorted_dates:

        value = consumption_data[date]

        print(
            "日付:", date,
            "| 消費支出:", value,
            "円"
        )

        save_economic_data(
            source="総務省・家計調査",
            indicator="個人消費_消費支出",
            date=date,
            value=value,
            unit="円"
        )

        save_count += 1

    print()
    print("===== 個人消費・前年同月比 =====")

    yoy_count = 0

    for date in sorted_dates:

        year = int(date[:4])
        month = int(date[-2:])

        previous_year = year - 1

        previous_date = f"{previous_year}-{month:02d}"

        if previous_date not in consumption_data:
            continue

        current_value = consumption_data[date]
        previous_value = consumption_data[previous_date]

        if previous_value == 0:
            continue

        yoy = round(
            (current_value / previous_value - 1) * 100,
            2
        )

        print(
            "日付:", date,
            "| 前年同月比:", yoy,
            "%"
        )

        save_economic_data(
            source="総務省・家計調査",
            indicator="個人消費_前年同月比",
            date=date,
            value=yoy,
            unit="%"
        )

        yoy_count += 1

    print()
    print("消費支出保存件数:", save_count)
    print("前年同月比保存件数:", yoy_count)

    latest_date = sorted_dates[-1]
    latest_value = consumption_data[latest_date]

    print()
    print("===== 最新データ =====")
    print("最新年月:", latest_date)
    print("最新消費支出:", latest_value, "円")

    year = int(latest_date[:4])
    month = int(latest_date[-2:])

    previous_date = f"{year - 1}-{month:02d}"

    if previous_date in consumption_data:

        previous_value = consumption_data[previous_date]

        yoy = round(
            (latest_value / previous_value - 1) * 100,
            2
        )

        print("前年同月:", previous_date)
        print("前年同月の消費支出:", previous_value, "円")
        print("前年同月比:", yoy, "%")


if __name__ == "__main__":
    get_consumption()