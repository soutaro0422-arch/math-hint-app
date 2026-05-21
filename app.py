import streamlit as st
import json
from google import genai
from google.genai import types

st.set_page_config(page_title="数学ヒントマシーン", layout="centered")

# APIキーは直接書かずに、Streamlitの隠し箱（Secrets）から安全に読み込みます
client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])

st.title("数学ヒントマシーン 🧮")
st.write("印刷された問題集の写真を撮ると、答えを隠してヒントを段階的に出します。")

# セッション状態の初期化
if "app_state" not in st.session_state:
    st.session_state.app_state = "upload"
if "math_data" not in st.session_state:
    st.session_state.math_data = None

# リセット関数
def reset_app():
    st.session_state.app_state = "upload"
    st.session_state.math_data = None

# ---- STEP 1: 写真撮影画面 ----
if st.session_state.app_state == "upload":
    img_file = st.camera_input("問題集をきれいに真上から撮影してください")
    
    if img_file:
        with st.spinner("AIが問題を解析中...（答えは隠しています）"):
            bytes_data = img_file.getvalue()
            
            # AIへのプロンプト
            prompt = """
            添付された画像にある、印刷された数学の問題を1問だけ認識し、解いてください。
            ユーザーが自力で解くためのアプリに使用するため、絶対に最初から最終的な答えを見せてはいけません。
            必ず以下のJSONフォーマットのみ（余計な解説の文字や挨拶は一切なし）で出力してください。
            数式にはLaTeX（$や$$）を自由に使用してください。
            
            {
              "problem_text": "認識した問題のテキスト（LaTeX数式を使用）",
              "hint_1": "この問題に取り組むための最初の1手や、思い出すべき公式（1行で、答えは絶対に書かない）",
              "hint_2": "具体的な方針や、計算の次のステップへのアドバイス（1行で、答えは絶対に書かない）",
              "steps": "正しい途中式のプロセス。改行は「\\n」で表現してください。",
              "final_answer": "最終的な答え"
            }
            """
            
            try:
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
                
                st.session_state.math_data = json.loads(response.text)
                st.session_state.app_state = "hint1"
                st.rerun()
                
            except Exception as e:
                st.error(f"エラーが発生しました。もう一度試すか、プロンプトを確認してください: {e}")

# ---- STEP 2: 段階的なヒント表示画面 ----
else:
    data = st.session_state.math_data
    
    st.markdown("### 📋 認識した問題")
    st.info(data['problem_text'])
    st.write("---")
    
    st.markdown("### 💡 ヒントと解説")
    
    st.markdown(f"**【ステップ1: 最初のヒント】**\n\n{data['hint_1']}")
    
    if st.session_state.app_state in ["hint2", "answer"]:
        st.markdown("---")
        st.markdown(f"**【ステップ2: もう一押しのヒント】**\n\n{data['hint_2']}")
        
    if st.session_state.app_state == "answer":
        st.markdown("---")
        st.success("**【ステップ3: 途中式と最終解答】**")
        st.markdown(data['steps'])
        st.subheader(f"🎯 答え: {data['final_answer']}")

    st.write("---")
    col1, col2 = st.columns(2)
    
    with col1:
        if st.session_state.app_state == "hint1":
            if st.button("次のヒントを見る ➡️", use_container_width=True):
                st.session_state.app_state = "hint2"
                st.rerun()
        elif st.session_state.app_state == "hint2":
            if st.button("答えと途中式を見る 👁️", use_container_width=True):
                st.session_state.app_state = "answer"
                st.rerun()
                
    with col2:
        if st.button("別の問題を撮る 🔄", on_click=reset_app, use_container_width=True):
            st.rerun()
