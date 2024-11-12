import streamlit as st
import pandas as pd
from anthropic import Anthropic
import io

# Streamlitアプリケーションの設定
st.set_page_config(page_title="サンプルデータ生成アプリケーション", layout="wide")

# セッション状態の初期化
if 'generated_data' not in st.session_state:
    st.session_state.generated_data = None
if 'download_clicked' not in st.session_state:
    st.session_state.download_clicked = False

# タイトルの表示
st.title("サンプルデータ生成アプリケーション")

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

    # 項目の要不要の設定
    st.header("項目の要不要の設定")
    if columns:
        # 初期データフレームの作成
        df_columns = pd.DataFrame({
            "項目名": columns,
            "含める": [True] * len(columns)
        })

        # データフレームの表示と編集（チェックボックスのみ）
        edited_df = st.data_editor(df_columns[["項目名", "含める"]], num_rows="dynamic")
        
        # 含める項目のフィルタリング
        filtered_columns = edited_df[edited_df["含める"]]["項目名"].tolist()

        # 項目数の判定
        if len(filtered_columns) <= 15:
            remaining = 15 - len(filtered_columns)
            st.markdown(
                f'<div style="background-color: #d4edda; padding: 10px; border-radius: 5px;">'
                f'選択可能な残り項目数: {remaining}件</div>',
                unsafe_allow_html=True
            )

            # 前提条件の入力欄の表示
            default_precondition = ""
            for column_name in filtered_columns:
                text = column_name + "列は、特に加工しません\n"
                default_precondition += text
                
            precondition = st.text_area("前提条件を記入してください", value=default_precondition)
        else:
            remaining = len(filtered_columns) - 15
            st.markdown(
                f'<div style="background-color: #f8d7da; padding: 10px; border-radius: 5px;">'
                f'項目数が15以下になるように、あと{remaining}件を削除してください。</div>',
                unsafe_allow_html=True
            )

        # データ生成の実行
        if st.button("サンプルデータを生成") and len(filtered_columns) <= 15:
            st.header("サンプルデータ生成")
            # メッセージの作成
            message_content = f"以下の要件に基づき、10行のサンプルデータを生成してください。\n"
            if precondition:
                message_content += f"前提条件：{precondition}\n"
            message_content += "項目一覧：" + ", ".join(filtered_columns) + "前後に余計なメッセージを付けず、カンマ区切りのCSVデータのみを出力してください。１行目は列名の行として、データは２行目から開始してください。"

            # Claude APIへのリクエスト
            try:
                response = client.messages.create(
                    model="claude-3-sonnet-20240229",
                    max_tokens=1000,
                    temperature=0.7,
                    messages=[
                        {
                            "role": "user",
                            "content": message_content
                        }
                    ]
                )

                # Claude APIからのレスポンス内容をDataFrameとして処理
                generated_data = response.content[0].text

                # サンプルデータをDataFrame形式に変換
                data_io = io.StringIO(generated_data)
                df_generated = pd.read_csv(data_io)
                
                # セッション状態に保存
                st.session_state.generated_data = df_generated

            except Exception as e:
                st.error(f"データ生成中にエラーが発生しました: {e}")

        # 生成されたデータの表示（セッション状態から）
        if st.session_state.generated_data is not None:
            st.subheader("生成されたサンプルデータ")
            st.dataframe(st.session_state.generated_data)

            # ダウンロードボタンの配置
            col1, col2 = st.columns([1, 5])  # 1:5の比率でカラムを分割
            with col1:
                # CSVダウンロードボタン
                csv = st.session_state.generated_data.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="CSVファイルをダウンロード",
                    data=csv,
                    file_name='sample_data.csv',
                    mime='text/csv',
                    key='download_csv'  # ユニークなキーを追加
                )
