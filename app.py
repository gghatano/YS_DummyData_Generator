import streamlit as st
import pandas as pd
from anthropic import Anthropic

# Streamlitアプリケーションの設定
st.set_page_config(page_title="サンプルデータ生成アプリケーション", layout="wide")

# タイトルの表示
st.title("サンプルデータ生成アプリケーション  ¥n(※Claude-APIキーを利用します)")

# Claude APIキーの入力
claude_api_key = st.text_input("ClaudeのAPIキーを入力してください", type="password")

if claude_api_key:
    client = Anthropic(api_key=claude_api_key)
    
    # 項目名の入力
    st.header("項目設定")
    default_columns = ["識別番号", "氏名", "性別", "年齢"]
    columns_input = st.text_area(
        "生成したい項目名をカンマ区切りで入力してください（例：識別番号, 氏名, 性別, 年齢）",
        value=", ".join(default_columns)
    )

    # 項目名の解析
    try:
        columns = [col.strip() for col in columns_input.split(',') if col.strip()]
        if not columns:
            raise ValueError("項目名が入力されていません。")
    except Exception as e:
        st.error(f"エラー: {e}")
        st.info("カンマ区切りで項目名を入力してください。")
        columns = default_columns


    # 項目の要不要、粒度、備考の設定
    st.header("項目の要不要と粒度の設定（表形式）")
    if columns:
        # 初期データフレームの作成
        df_columns = pd.DataFrame({
            "項目名": columns,
            "含める": [True] * len(columns),
            "粒度": ["" for _ in columns],
            "備考": ["" for _ in columns]
        })

        # データフレームの表示と編集
        edited_df = st.data_editor(df_columns, num_rows="dynamic")
        
        # 含める項目のフィルタリング
        filtered_columns = edited_df[edited_df["含める"]]["項目名"].tolist()
        remarks = edited_df[edited_df["含める"]]["備考"].tolist()

        # 選択された項目数の表示
        col1, col2 = st.columns([1, 2])
        with col1:
            st.write("選択中の項目数:", len(filtered_columns))
        with col2:
            if len(filtered_columns) > 15:
                st.error("🔴 項目数が上限（15個）を超えています。項目を減らしてください。")
            else:
                st.success(f"🟢 あと{15 - len(filtered_columns)}個まで追加できます")

        # データ生成の設定
        st.header("データ生成の設定")
        
        # 前提条件の入力欄
        precondition = st.text_area(
            "データ生成の前提条件を入力してください（例：年齢は20-60歳の範囲、性別は男性/女性のみ、など）",
            help="生成するデータの制約条件や特記事項があれば入力してください。"
        )

        # 行数の入力
        num_rows = st.number_input("生成するデータの行数を入力してください", min_value=1, value=10)

        # 項目数の検証と生成ボタン
        if len(filtered_columns) > 15:
            st.warning("項目数が15列を超えています。項目数を減らしてください。")
        else:
            # データ生成の実行
            if st.button("サンプルデータを生成"):
                # メッセージの作成
                message_content = "以下の要件に基づき、CSVフォーマットでサンプルデータを生成してください。\n\n"
                message_content += f"■生成行数\n{num_rows}行\n\n"
                
                if precondition:
                    message_content += f"■前提条件\n{precondition}\n\n"
                
                message_content += "■項目一覧\n"
                for col, remark in zip(filtered_columns, remarks):
                    message_content += f"・{col}"
                    if remark:
                        message_content += f"（{remark}）"
                    message_content += "\n"
                
                message_content += "\n■出力形式\n"
                message_content += f"- 以下の列名を使用してください：{', '.join(filtered_columns)}\n"
                message_content += "- カンマ区切りのCSV形式で出力してください\n"
                message_content += "- データは現実的で一貫性のある値にしてください"

                # 生成中の表示
                with st.spinner("データを生成中です..."):
                    try:
                        response = client.messages.create(
                            model="claude-3-5-sonnet-20241022",
                            messages=[
                                {
                                    "role": "user",
                                    "content": message_content
                                }
                            ],
                            max_tokens=1000,
                            temperature=0.7
                        )
                        generated_data = response.content[0].text
                        
                        # CSVテキストをDataFrameに変換
                        import io
                        try:
                            # CSVテキストをDataFrameに変換
                            df = pd.read_csv(io.StringIO(generated_data))
                            
                            # 列名を指定された項目名で上書き
                            if len(df.columns) == len(filtered_columns):
                                df.columns = filtered_columns
                            
                            # 生成成功のメッセージ
                            st.success("データの生成が完了しました！")
                            
                            # DataFrameをテーブルとして表示
                            st.subheader("生成されたデータ")
                            st.dataframe(df)
                            
                            # CSVダウンロードボタン
                            csv = df.to_csv(index=False)
                            st.download_button(
                                label="CSV形式でダウンロード",
                                data=csv,
                                file_name="generated_data.csv",
                                mime="text/csv"
                            )
                        except Exception as e:
                            st.warning("生成されたデータをテーブル形式に変換できませんでした。生のテキストを表示します。")
                            st.text_area("生成されたデータ", value=generated_data, height=300)
                            st.error(f"変換エラーの詳細: {str(e)}")
                            
                    except Exception as e:
                        st.error(f"データ生成中にエラーが発生しました: {e}")
