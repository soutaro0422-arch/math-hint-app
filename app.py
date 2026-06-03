import streamlit as st
import json
from google import genai
from google.genai import types

# ページ設定
st.set_page_config(
    page_title="数学ヒントマシーン", 
    page_icon="🧮",
    layout="centered"
)

# APIクライアント初期化
client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])

st.title("数学ヒントマシーン 🧮")
st.caption("問題集の写真を撮るだけで、AIがあなた専用の段階的ヒントを作成します。")

# セッション状態の初期化
if "math_data" not in st.session_state:
    st.session_state.math_data = None

def reset_app():
    st.session_state.math_data = None

# ---- STEP 1: 写真撮影・アップロード画面 ----
if st.session_state.math_data is None:
    st.markdown("### 📸 問題を撮影")
    
    # 💡 ポイント：st.file_uploader を使います。
    # スマホでこれをタップすると、アルバムから選ぶだけでなく「カメラで撮影」が選べます。
    # その場合はスマホ標準のカメラアプリが起動するため、確実に「背面カメラ」で綺麗に撮影できます！
    img_file = st.file_uploader(
        "「カメラを起動」を選ぶと、背面カメラで撮影できます 📷", 
        type=["jpg", "jpeg", "png"]
    )
    
    if img_file:
        with st.spinner("✨ AIが問題を解析しています。しばらくお待ちください..."):
            try:
                # アップロードされたファイルをそのままバイトデータとして読み込み
                bytes_data = img_file.getvalue()
                
                # プロンプトの部分を以下のように書き換えます
                # プロンプトはシンプルに役割を伝えるだけでOKになります
                prompt = """
                添付された画像にある、印刷された数学の問題を1問だけ認識し、解いてください。
                各ヒントには、絶対に最終的な答え（数値など）を含めないでください。
                """
                
                # 💡 解決策：AIが返すJSONの「型（スキーマ）」を厳密に定義する
                # これにより、指定したキー以外は絶対に返ってこなくなります
                response_schema = {
                    "type": "OBJECT",
                    "properties": {
                        "problem_text": {"type": "STRING", "description": "認識した問題のテキスト（LaTeX数式を使用）"},
                        "hints": {
                            "type": "ARRAY",
                            "items": {
                                "type": "OBJECT",
                                "properties": {
                                    "title": {"type": "STRING", "description": "公式・基礎、補助線の引き方など最適なアプローチ名"},
                                    "content": {"type": "STRING", "description": "ヒントの具体的な内容（1行、最終解答は含めない）"}
                                },
                                "required": ["title", "content"]
                            },
                            "description": "問題の難易度や性質に応じた2〜4個のヒント配列"
                        },
                        "steps": {"type": "STRING", "description": "正しい途中式のプロセス。改行は「\\n」で表現。"},
                        "final_answer": {"type": "STRING", "description": "最終的な答え"}
                    },
                    "required": ["problem_text", "hints", "steps", "final_answer"]
                }
                
                response = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=[
                        types.Part.from_bytes(data=bytes_data, mime_type="image/jpeg"),
                        prompt
                    ],
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        # 💡 ここでスキーマを流し込む
                        response_schema=response_schema,
                    ),
                )
                
                # 💡 念のための対策：もし文字列の前後に ```json などが含まれていたら剥ぎ取る
                raw_text = response.text.strip()
                if raw_text.startswith("```"):
                    # 最初と最後の行（```json と ```）を削る
                    lines = raw_text.splitlines()
                    if lines[0].startswith("```"):
                        lines = lines[1:]
                    if lines[-1].startswith("```"):
                        lines = lines[:-1]
                    raw_text = "\n".join(lines).strip()
                
                st.session_state.math_data = json.loads(raw_text)
                st.rerun()

# ---- STEP 2: 段階的なヒント表示画面 ----
else:
    data = st.session_state.math_data
    
    st.markdown("### 📋 認識した問題")
    # LaTeX数式がきれいに表示されるよう st.latex か st.markdown を使用
    st.markdown(data['problem_text'])
    st.write("---")
    
    st.markdown("### 💡 ヒントを見てみよう")
    st.write("上から順番に読んでいくと、自力で解けるようになるよ！")
    
    # 💡 改善のポイント：動的に生成されたヒントの数だけ、折りたたみ（手動開閉型）で表示します
    # これなら2個でも4個でもエラーにならず、UIもすっきりします
    if "hints" in data and isinstance(data["hints"], list):
        for i, hint in enumerate(data["hints"]):
            # タイトルと中身を取り出す（念のためデフォルト値を用意）
            title = hint.get("title", f"ヒント {i+1}")
            content = hint.get("content", "")
            
            with st.expander(f"🔍 {title}"):
                st.markdown(content)
    else:
        st.warning("ヒントのデータ形式が正しく取得できませんでした。")
        
    st.write("---")
    
    # 💡 状態管理のバグ防止：「答えを表示するかどうか」のフラグをセッション状態で管理
    if "show_answer" not in st.session_state:
        st.session_state.show_answer = False

    if not st.session_state.show_answer:
        if st.button("完全にギブアップ！答えと途中式を見る 👁️", use_container_width=True):
            st.session_state.show_answer = True
            st.rerun()
            
    if st.session_state.show_answer:
        st.success("**📝 途中式と最終解答:**")
        st.markdown(data['steps'])
        st.subheader(f"🎯 答え: {data['final_answer']}")

    # 「別の問題を撮る」ボタン
    st.write("---")
    # 💡 別の問題を撮るときは、答えの表示フラグもリセット
    def full_reset():
        st.session_state.math_data = None
        st.session_state.show_answer = False

    if st.button("別の問題を撮る 🔄", on_click=full_reset, use_container_width=True):
        st.rerun()
