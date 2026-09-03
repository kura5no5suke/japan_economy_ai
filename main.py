import subprocess


def run_step(command):
    print()
    print("=" * 50)
    print("実行:", command)
    print("=" * 50)

    result = subprocess.run(
        command,
        capture_output=False,
        text=True
    )

    if result.returncode != 0:
        print()
        print("エラーが発生しました:", command)
        return False

    return True


def main():
    print()
    print("========================================")
    print("      日本経済監視AI 自動実行")
    print("========================================")

    steps = [
        # ① CPI
        ["py", "estat.py"],

        # ② GDP
        ["py", "gdp.py"],

        # ③ 完全失業率
        ["py", "unemployment.py"],

        # ④ 実質賃金
        ["py", "real_wage.py"],

        # ⑤ 個人消費
        ["py", "consumption.py"],

        # ⑥ 5指標でリスク計算
        ["py", "risk.py"],

        # ⑦ 5指標でAIレポート生成
        ["py", "ai_report.py"],

        # ⑧ 総合リスク急上昇監視
        ["py", "risk_spike_alert.py"],
    ]

    for step in steps:
        success = run_step(step)

        if not success:
            print()
            print("処理を中止しました。")
            return

    print()
    print("========================================")
    print("すべての処理が完了しました")
    print("========================================")


if __name__ == "__main__":
    main()