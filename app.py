import streamlit as st
import pandas as pd
from anthropic import Anthropic
import io
import tempfile
import os
import subprocess
import sys

# Streamlitアプリケーションの設定
st.set_page_config(page_title="サンプルデータ生成アプリケーション", layout="wide")

# セッション状態の初期化
if 'phase1_data' not in st.session_state:
    st.session_state.phase1_data = None
if 'phase2_data' not in st.session_state:
    st.session_state.phase2_data = None
if 'approved_precondition' not in st.session_state:
    st.session_state.approved_precondition = None
if 'approved_columns' not in st.session_state:
    st.session_state.approved_columns = None
if 'generator_code' not in st.session_state:
    st.session_state.generator_code = None
if 'show_phase2' not in st.session_state:
    st.session_state.show_phase2 = False

# タイトルの表示
st.title("サンプルデータ生成アプリケーション")

# Claude APIキーの入力
claude_api_key = st.text_input("ClaudeのAPIキーを入力してください", type="password")

if claude_api_key:
    client = Anthropic(api_key=claude_api_key)
    
    # フェーズ1: 品質確認用データの生成と前提条件の調整
    st.header("フェーズ1: 品質確認とルール設定")
    
    # 項目名の入力
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

            # 品質確認用データの生成ボタン
            if st.button("品質確認用データを生成"):
                with st.spinner('データを生成中です。しばらくお待ちください...'):
                    message_content = f"以下の要件に基づき、10行のサンプルデータを生成してください。\n"
                    if precondition:
                        message_content += f"前提条件：{precondition}\n"
                    message_content += "項目一覧：" + ", ".join(filtered_columns) + "\n前後に余計なメッセージを付けず、カンマ区切りのCSVデータのみを出力してください。１行目は列名の行として、データは２行目から開始してください。"

                    try:
                        response = client.messages.create(
                            model="claude-3-sonnet-20240229",
                            max_tokens=1000,
                            temperature=0.7,
                            messages=[{"role": "user", "content": message_content}]
                        )

                        generated_data = response.content[0].text
                        data_io = io.StringIO(generated_data)
                        df_generated = pd.read_csv(data_io)
                        st.session_state.phase1_data = df_generated
                        st.success('データの生成が完了しました！')

                    except Exception as e:
                        st.error(f"データ生成中にエラーが発生しました: {e}")

            # フェーズ1のデータ表示（セッション状態から）
            if st.session_state.phase1_data is not None:
                st.subheader("生成された品質確認用データ")
                st.dataframe(st.session_state.phase1_data)

                # データ内容の承認
                if st.button("この内容で確定する"):
                    st.session_state.approved_precondition = precondition
                    st.session_state.approved_columns = filtered_columns
                    st.session_state.show_phase2 = True
                    st.success("設定を確定しました。フェーズ2に進んでください。")

        else:
            remaining = len(filtered_columns) - 15
            st.markdown(
                f'<div style="background-color: #f8d7da; padding: 10px; border-radius: 5px;">'
                f'項目数が15以下になるように、あと{remaining}件を削除してください。</div>',
                unsafe_allow_html=True
            )

    # フェーズ2: Python生成プログラムの作成
    if st.session_state.show_phase2:
        st.header("フェーズ2: データ生成プログラムの作成")
        st.write("確定した設定内容に基づいて、データ生成プログラムを作成します。")

        # プログラム生成ボタン
        if st.button("データ生成プログラムを作成"):
            with st.spinner('Pythonプログラムを生成中です。しばらくお待ちください...'):
                message_content = f"""
以下の要件に基づき、CSVデータを生成するPythonプログラムを作成してください。
プログラムは以下の要件を満たす必要があります：

1. プログラムは以下の3つの関数を含むこと:
   - generate_single_row(): 1行分のデータを生成する関数
   - generate_data(num_rows): 指定行数分のデータを生成しDataFrameを返す関数
   - main(): コマンドライン引数から行数を受け取り、CSVファイルを生成する関数

2. 必要なライブラリ:
   - pandas
   - faker
   - sys
   - その他必要なライブラリ

3. 出力形式:
   - generate_data()関数はpandas.DataFrameを返すこと
   - main()関数は生成したDataFrameをCSVファイルとして保存すること
   - CSVファイル名は'generated_data.csv'とすること

4. エラーハンドリング:
   - 適切な例外処理を含めること
   - エラーメッセージは標準エラー出力に出力すること

5. コマンドライン実行:
   - プログラムは `python script.py [行数]` の形式で実行できること
   - 行数が指定されない場合のデフォルト値を設定すること

コメントは日本語で記述してください。
余計な説明は不要です。Pythonのコードのみを出力してください。

前提条件：
{st.session_state.approved_precondition}

項目一覧：{", ".join(st.session_state.approved_columns)}
"""
                try:
                    response = client.messages.create(
                        model="claude-3-sonnet-20240229",
                        max_tokens=2000,
                        temperature=0.7,
                        messages=[{"role": "user", "content": message_content}]
                    )

                    # 生成されたコードから余計な文字を除去
                    generated_code = response.content[0].text
                    # コードブロックのマークダウンが含まれている場合は除去
                    if "```python" in generated_code:
                        generated_code = generated_code.split("```python")[1].split("```")[0]
                    elif "```" in generated_code:
                        generated_code = generated_code.split("```")[1]
                    
                    # 余計な空行を除去
                    generated_code = "\n".join(line for line in generated_code.splitlines() if line.strip())
                    
                    st.session_state.generator_code = generated_code
                    st.success('プログラムの生成が完了しました！')

                except Exception as e:
                    st.error(f"プログラム生成中にエラーが発生しました: {e}")

        # 生成されたプログラムの表示と編集（セッション状態から）
        if st.session_state.generator_code is not None:
            st.subheader("生成されたPythonプログラム")
            # 編集可能なテキストエリアとして表示
            edited_code = st.text_area(
                "プログラムを編集できます",
                value=st.session_state.generator_code,
                height=400
            )

            # 元のコードと編集後のコードを比較
            if edited_code != st.session_state.generator_code:
                st.warning("プログラムが編集されています。")

            # プログラムのダウンロードボタン（編集されたバージョン）
            st.download_button(
                label="Pythonプログラムをダウンロード",
                data=edited_code,
                file_name='data_generator.py',
                mime='text/plain'
            )

            # データ生成の実行セクション
            st.subheader("データ生成の実行")
            num_rows = st.number_input("生成する行数", min_value=1, value=100)

            if st.button("プログラムを実行してデータを生成"):
                with st.spinner(f'{num_rows}行のデータを生成中です。しばらくお待ちください...'):
                    try:
                        # 一時ファイルに編集されたプログラムを保存
                        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
                            f.write(edited_code)  # 編集されたコードを使用
                            temp_file = f.name

                        # プログラムを実行
                        result = subprocess.run(
                            [sys.executable, temp_file, str(num_rows)],
                            capture_output=True,
                            text=True,
                            encoding='utf-8'
                        )

                        # 一時ファイルを削除
                        os.unlink(temp_file)

                        if result.returncode == 0:
                            try:
                                df_generated = pd.read_csv('generated_data.csv')
                                st.session_state.phase2_data = df_generated
                                st.success(f"{num_rows}行のデータ生成が完了しました！")
                            except Exception as e:
                                st.error(f"CSVファイルの読み込み中にエラーが発生しました: {e}")
                        else:
                            st.error("プログラムの実行中にエラーが発生しました")
                            # エラーの詳細をデバッグ表示
                            with st.expander("エラーの詳細"):
                                st.code(result.stderr)

                    except Exception as e:
                        st.error(f"実行中にエラーが発生しました: {e}")

                    # 成功した場合のデータ表示とダウンロード
                    if st.session_state.phase2_data is not None:
                        # データの表示
                        st.subheader("生成されたデータ（プレビュー：先頭10行）")
                        st.dataframe(st.session_state.phase2_data.head(10))

                        # CSVダウンロードボタン
                        csv = st.session_state.phase2_data.to_csv(index=False).encode('utf-8')
                        st.download_button(
                            label="生成したCSVファイルをダウンロード",
                            data=csv,
                            file_name='generated_data.csv',
                            mime='text/csv',
                            key='download_generated_csv'
                        )


