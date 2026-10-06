import subprocess
import sys


PYTHON = sys.executable


def run_step(script_name):
    print()
    print("=" * 60)
    print("実行:", script_name)
    print("=" * 60)

    result = subprocess.run(
        [PYTHON, script_name]
    )

    if result.returncode != 0:
        print()
        print("エラーが発生しました。")
        print("停止した処理:", script_name)
        sys.exit(result.returncode)


def main():
    print()
    print("===== 日本経済監視AI 開始 =====")

    steps = [
        # ----------------------------------------
        # 経済データ取得
        # ----------------------------------------
        "estat.py",
        "gdp.py",
        "unemployment.py",
        "real_wage.py",
        "consumption.py",
        "boj.py",
        "forex.py",
        "industrial_production.py",
        "machinery_orders.py",
        "leading_index.py",
        "coincident_index.py",

        # ----------------------------------------
        # 分析
        # ----------------------------------------
        "risk.py",
        "leading_warning.py",

        # ----------------------------------------
        # 景気後退シグナル V2
        # ----------------------------------------
        "recession_signal.py",

        # ----------------------------------------
        # AIレポート・警告
        # ----------------------------------------
        "ai_report.py",
        "risk_spike_alert.py",
    ]

    total_steps = len(steps)

    for index, script_name in enumerate(
        steps,
        start=1,
    ):
        print()
        print(
            f"[{index}/{total_steps}] "
            f"{script_name}"
        )

        run_step(script_name)

    print()
    print("=" * 60)
    print("===== 日本経済監視AI 完了 =====")
    print("=" * 60)


if __name__ == "__main__":
    main()