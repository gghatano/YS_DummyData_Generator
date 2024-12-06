# YS_DummyData_Generator

## デモ環境
[こちらから利用できます](https://ysdummydatagenerator-8zuxbeqserrd3fxgpmv4de.streamlit.app/)

## デモ動画
![demo](./demo.gif)

## 前提条件
- ClaudeのAPIキーを持っていること
- 生成したいデータの項目名がわかっていること
- (ローカル環境で実行する場合)Python 3.12が利用できること

## ローカルでの起動方法
1. 必要なライブラリをインストールします
    ```bash
    pip install -r requirements.txt
    ```

2. アプリを起動します
    ```bash
    streamlit run app.py
    ```

## 注意
- 生成するデータの行数が多いほど、ClaudeのAPI利用料が増加します。
- Claudeが0から生成するデータであり、本番データとは内容が全く異なる場合があります。
- データの形式が本番データと一致しない可能性もあります。
