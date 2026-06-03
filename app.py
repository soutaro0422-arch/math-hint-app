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
                prompt = """
                添付された画像にある、印刷された数学の問題を1問だけ認識し、解いてください。
                必ず以下のJSONフォーマットのみ（余計な解説の文字や挨拶は一切なし）で出力してください。
                各ヒントには、絶対に最終的な答え（数値など）を含めないでください。

                {
                "problem_text": "認識した問題のテキスト（LaTeX数式を使用）",
                "hints": [
                {
                "title": "公式・基礎、補助線の引き方、分類のコツなど、問題に最適なアプローチ名",
                "content": "そのヒントの具体的な内容（1行、絶対に最終的な答えは含めない）"
                },
                ...（問題の難易度や性質に応じて、最適な数（2〜4個）だけ配列として出力）
                ],
                "steps": "正しい途中式のプロセス。改行は「\\n」で表現してください。",
                "final_answer": "最終的な答え"
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
# ---- 修正後の「ヒントと解説」の画面表示部分 ----
else:
    data = st.session_state.math_data
    
    st.markdown("### 📋 認識した問題")
    st.info(data['problem_text'])
    st.write("---")
    
    st.markdown("### 💡 えらべるヒント")
    st.write("今のあなたの状態に合わせて、欲しいヒントのタブを切り替えてね！")
    
    # 3つのタブを作成
    tab1, tab2, tab3 = st.tabs(["① 使う公式がわからない", "② 最初の一歩が知りたい", "③ 計算の注意点を知りたい"])
    
    with tab1:
        st.markdown(f"**📚 必要になる基礎・公式:**\n\n{data['hint_formula']}")
        
    with tab2:
        st.markdown(f"**🚀 攻略の手がかり:**\n\n{data['hint_first_step']}")
        
    with tab3:
        st.markdown(f"**⚠️ ここでミスしやすい！:**\n\n{data['hint_trap']}")
        
    # 「答えを見る」は今まで通りボタンを押した後に表示させる制御にする
    st.write("---")
    if st.session_state.app_state != "answer":
        if st.button("完全にギブアップ！答えと途中式を見る 👁️", use_container_width=True):
            st.session_state.app_state = "answer"
            st.rerun()
            
    if st.session_state.app_state == "answer":
        st.success("**📝 途中式と最終解答:**")
        st.markdown(data['steps'])
        st.subheader(f"🎯 答え: {data['final_answer']}")

    # 「別の問題を撮る」ボタン
    st.write("---")
    if st.button("別の問題を撮る 🔄", on_click=reset_app, use_container_width=True):
        st.rerun()
