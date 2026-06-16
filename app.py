import streamlit as st
import json
import re  # エラー修復のための正規表現モジュールを追加
from google import genai
from google.genai import types

# ページ設定（ブラウザのタブやレイアウトの設定）
st.set_page_config(
    page_title="数学ヒントマシーン", 
    page_icon="🧮",
    layout="centered"
)

# APIクライアント初期化（StreamlitのSecretsから安全に読み込み）
client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])

# アプリのタイトルエリア
st.title("数学ヒントマシーン 🧮")
st.caption("問題集の写真を撮るだけで、AIがあなた専用の段階的ヒントを作成します。")

# セッション状態（アプリ内のデータ保存箱）の初期化
if "math_data" not in st.session_state:
    st.session_state.math_data = None

def reset_app():
    st.session_state.math_data = None

# ---- STEP 1: 写真撮影・アップロード画面 ----
if st.session_state.math_data is None:
    st.markdown("### 📸 問題を撮影")
    
    # ファイルアップローダー（スマホだと自動的に背面カメラが選択肢に出ます）
    img_file = st.file_uploader(
        "「カメラを起動」を選ぶと、背面カメラで撮影できます 📷", 
        type=["jpg", "jpeg", "png"]
    )
    
    if img_file:
        # 安全装置：ファイルサイズが大きすぎる(5MB以上)場合はユーザーに案内（503対策）
        if img_file.size > 5 * 1024 * 1024:
            st.warning("⚠️ 写真のファイルサイズが大きすぎます。スマホのカメラ設定で画質を少し下げるか、スクエア（正方形）モードで撮影し直すとさらに安定します。")
            
        with st.spinner("✨ AIが問題を解析しています。しばらくお待ちください..."):
            try:
                bytes_data = img_file.getvalue()
                
                # AIへの厳密なプロンプト指示
                prompt = """
                添付された画像にある、印刷された数学の問題を1問だけ認識し、解いてください。
                ユーザーが自力で解くためのアプリに使用するため、絶対に最初から最終的な答えを見せてはいけません。
                
                出力は指定されたJSONスキーマに完全に準拠してください。
                マークダウンのコードブロック（```json ... ```）は絶対に含めず、純粋なJSONオブジェクトのみを出力してください。
                
                【数式および図形記号に関する厳格なルール】
                1. 数式を表現する場合は、Streamlitの仕様に合わせて、前後に $ を付けたインライン形式（例: $x^2 + 2x = 0$）にしてください。
                2. 三角関数（sin, cos, tan）や対数（log）などは、必ず頭にバックスラッシュを付けた正しいLaTeXコマンド（例: $\\sin x$, $\\cos \\theta$, $\\log_2 x$）を使用してください。※JSON文字列内なのでバックスラッシュは2つ（\\\\）重ねてください。
                3. 図形問題における「辺AB」「角C」「三角形ABC」などの表現について、「ext=AB」や「text=AB」といったアルファベットの誤表示を絶対にしないでください。日本語で普通に「辺AB」とするか、数式にする場合でも「$AB$」や「辺 $AB$」のようにシンプルに出力してください。
                
                【テキストの読みやすさに関するルール】
                1. "hint_1" と "hint_2" は、文字が1行に詰まって読みにくくならないよう、適切な場所に改行（\\n）を挟むか、2〜3項目の箇条書き（- から始まる行）にしてください。
                2. "steps" は1行ごとに改行（\\n）を挟み、計算のプロセスを分かりやすく展開してください。
                
                【期待するJSONのキー】
                - "problem_text": 認識した問題のテキスト
                - "hint_1": この問題に取り組むための最初の1手や、思い出すべき公式・定義（答えは絶対に書かない）
                - "hint_2": 具体的な方針や、計算の次のステップへのアドバイス（答えは絶対に書かない）
                - "steps": 正しい途中式のプロセス
                - "final_answer": 最終的な答え
                """
                
                response = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=[
                        types.Part.from_bytes(data=bytes_data, mime_type="image/jpeg"),
                        prompt
                    ],
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                    ),
                )
                
                # ---- AIの出力データのクリーニング処理 ----
                clean_text = response.text.strip()
                
                # 1. もしGeminiが ```json などのマークダウン装飾を付けてきたら強制的に剥ぎ取る
                if clean_text.startswith("```"):
                    clean_text = clean_text.split("\n", 1)[1]
                if clean_text.endswith("```"):
                    clean_text = clean_text.rsplit("\n", 1)[0]
                clean_text = clean_text.strip("`").strip()
                
                # 2. 【最重要】invalid \escape エラー（無効なエスケープ）を防止する自動修復
                # \\sin ではなく \\を忘れて \\s と表現されたバックスラッシュを自動的に2重（\\\\）に置換
                clean_text = re.sub(r'\\(?!["\\/bfnrtu])', r'\\\\', clean_text)
                
                # 修復したJSON文字列をPythonの辞書型に変換して保存
                st.session_state.math_data = json.loads(clean_text)
                st.rerun()
                
            except Exception as e:
                # サーバー負荷（503）や回数制限（429）などのエラーハンドリング
                if "429" in str(e):
                    st.error("🚨 短時間にリクエストが集中しました。一時的な制限ですので、1分ほど待ってからもう一度試してください。")
                else:
                    st.error("❌ 解析エラーが発生しました。写真がボケていないか確認して、もう一度試してください。")
                st.caption(f"エラー詳細: {e}")

# ---- STEP 2: 段階的なヒント表示画面 ----
else:
    data = st.session_state.math_data
    
    # 認識された問題の表示（st.info で見やすいカード風に表示）
    st.markdown("### 📝 認識された問題")
    st.info(data['problem_text'])
    
    st.markdown("### 💡 段階的ヒント")
    st.write("上から順番にアコーディオンを開けて、自力で解けるかチャレンジしてみよう！")
    
    # ユーザーがクリックして中身を見るアコーディオン（Expander）UI
    with st.expander("🔍 【Level 1】 最初のヒント（公式・着眼点）"):
        st.write("📌 **まずはここをチェック：**")
        st.markdown(data['hint_1'])
        
    with st.expander("⚡ 【Level 2】 もう一押しのヒント（計算の方針）"):
        st.write("🧭 **次の方針：**")
        st.markdown(data['hint_2'])
        
    with st.expander("🎯 【Level 3】 途中式と最終解答"):
        st.markdown("### 🛠️ 途中式（解法のプロセス）")
        st.markdown(data['steps'])
        
        st.markdown("---")
        st.markdown(f"### 🎯 最終解答\n### {data['final_answer']}")

    # 別ページに遷移させず、下部に戻るボタンを配置してスマートにリセット
    st.write("---")
    if st.button("🔄 別の問題を撮影する", use_container_width=True, type="secondary"):
        reset_app()
        st.rerun()
