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
                
                prompt = """
                添付された画像にある、印刷された数学の問題を1問だけ認識し、解いてください。
                ユーザーが自力で解くためのアプリに使用するため、絶対に最初から最終的な答えを見せてはいけません。
                必ず以下のJSONフォーマットのみ（余計な解説の文字やマークダウンの囲みは一切なし）で出力してください。
                数式を表現する場合は、Streamlitの仕様に合わせて、前後に $ を付けたプレーンなテキスト（例: $x^2 + 2x = 0$）にしてください。
                
                {
                  "problem_text": "認識した問題のテキスト",
                  "hint_1": "この問題に取り組むための最初の1手や、思い出すべき公式（答えは絶対に書かない）",
                  "hint_2": "具体的な方針や、計算の次のステップへのアドバイス（答えは絶対に書かない）",
                  "steps": "正しい途中式のプロセス（1行ずつ改行 '\\n' を挟んでください）",
                  "final_answer": "最終的な答え"
                }
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
                
                st.session_state.math_data = json.loads(response.text)
                st.rerun()
                
            except Exception as e:
                st.error("解析エラーが発生しました。写真がボケていないか確認して、もう一度試してください。")
                st.caption(f"エラー詳細: {e}")

# ---- STEP 2: 段階的なヒント表示画面 ----
else:
    data = st.session_state.math_data
    
    st.markdown("### 📝 認識された問題")
    st.info(data['problem_text'])
    
    st.markdown("### 💡 段階的ヒント")
    st.write("上から順番に開けて、自力で解けるかチャレンジしてみよう！")
    
    with st.expander("🔍 【Level 1】 最初のヒント（公式・着眼点）"):
        st.markdown(f"### 💡 ヒント 1\n{data['hint_1']}")
        
    with st.expander("⚡ 【Level 2】 もう一押しのヒント（計算の方針）"):
        st.markdown(f"### 🧭 ヒント 2\n{data['hint_2']}")
        
    with st.expander("🎯 【Level 3】 途中式と最終解答"):
        st.markdown("### 🛠️ 途中式（解法のプロセス）")
        st.markdown(data['steps'])
        
        st.markdown("---")
        st.markdown(f"### 🎯 最終解答\n**{data['final_answer']}**")

    st.write("---")
    if st.button("🔄 別の問題を撮影する", use_container_width=True, type="secondary"):
        reset_app()
        st.rerun()
