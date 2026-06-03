import streamlit as st
import json
from google import genai
from google.genai import types
from pydantic import BaseModel, Field
from typing import List

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
if "show_answer" not in st.session_state:
    st.session_state.show_answer = False

def full_reset():
    st.session_state.math_data = None
    st.session_state.show_answer = False

# 💡 解決策1: Pydanticを使ってスキーマを定義する
# 辞書型（dict）でスキーマを書くよりも、こちらの方がSDK側で確実にパースされます
class HintItem(BaseModel):
    title: str = Field(description="公式・基礎、補助線の引き方など問題に最適なアプローチ名")
    content: str = Field(description="ヒントの具体的な内容（1行、最終解答は含めない）")

class MathResponseSchema(BaseModel):
    problem_text: str = Field(description="認識した問題のテキスト（LaTeX数式を使用）")
    hints: List[HintItem] = Field(description="問題の難易度や性質に応じた2〜4個のヒント配列")
    steps: str = Field(description="正しい途中式のプロセス。改行は「\\n」で表現。")
    final_answer: str = Field(description="最終的な答え")


# ---- STEP 1: 写真撮影・アップロード画面 ----
if st.session_state.math_data is None:
    st.markdown("### 📸 問題を撮影")
    
    img_file = st.file_uploader(
        "「カメラを起動」を選ぶと、背面カメラで撮影できます 📷", 
        type=["jpg", "jpeg", "png"]
    )
    
    if img_file:
        with st.spinner("✨ AIが問題を解析しています。しばらくお待ちください..."):
            try:
                # バイトデータの読み込み
                bytes_data = img_file.getvalue()
                
                # 💡 解決策2: 画像のMIMEタイプを動的に取得する
                # PNG画像を jpeg として送るとAI側で読み取りエラー（解析エラー）になることがあります
                mime_type = img_file.type if img_file.type else "image/jpeg"
                
                prompt = """
                添付された画像にある、印刷された数学の問題を1問だけ認識し、解いてください。
                各ヒントには、絶対に最終的な答え（数値など）を含めないでください。
                """
                
                response = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=[
                        types.Part.from_bytes(data=bytes_data, mime_type=mime_type),
                        prompt
                    ],
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        # Pydanticモデルをそのままスキーマに渡す
                        response_schema=MathResponseSchema,
                        temperature=0.1, # 💡 回答のブレ（構造の崩れ）を防ぐために低めに設定
                    ),
                )
                
                # 受信データのパースと検証
                raw_text = response.text.strip()
                
                # 念のためのマークダウン剥ぎ取り
                if raw_text.startswith("```"):
                    lines = raw_text.splitlines()
                    if lines[0].startswith("```"):
                        lines = lines[1:]
                    if lines[-1].startswith("```"):
                        lines = lines[:-1]
                    raw_text = "\n".join(lines).strip()
                
                # JSONとしてロードしてセッションに格納
                st.session_state.math_data = json.loads(raw_text)
                st.rerun()
                
            except json.JSONDecodeError as je:
                st.error("AIの出力データが崩れてしまいました。お手数ですがもう一度お試しください。")
                st.caption(f"デバッグ情報 (JSONエラー): {je}")
            except Exception as e:
                st.error("解析エラーが発生しました。写真がボケていないか確認して、もう一度試してください。")
                st.caption(f"デバッグ情報 (一般エラー): {e}")

# ---- STEP 2: 段階的なヒント表示画面 ----
else:
    data = st.session_state.math_data
    
    st.markdown("### 📋 認識した問題")
    st.markdown(data.get('problem_text', '問題を認識できませんでした。'))
    st.write("---")
    
    st.markdown("### 💡 ヒントを見てみよう")
    st.write("上から順番に読んでいくと、自力で解けるようになるよ！")
    
    # ヒントの表示
    hints = data.get("hints", [])
    if hints and isinstance(hints, list):
        for i, hint in enumerate(hints):
            title = hint.get("title", f"ヒント {i+1}")
            content = hint.get("content", "")
            with st.expander(f"🔍 {title}"):
                st.markdown(content)
    else:
        st.warning("ヒントが生成されませんでした。")
        
    st.write("---")
    
    # 答えの表示制御
    if not st.session_state.show_answer:
        if st.button("完全にギブアップ！答えと途中式を見る 👁️", use_container_width=True):
            st.session_state.show_answer = True
            st.rerun()
            
    if st.session_state.show_answer:
        st.success("**📝 途中式と最終解答:**")
        st.markdown(data.get('steps', '途中式がありません。'))
        st.subheader(f"🎯 答え: {data.get('final_answer', '解答がありません。')}")

    # 「別の問題を撮る」ボタン
    st.write("---")
    if st.button("別の問題を撮る 🔄", on_click=full_reset, use_container_width=True):
        st.rerun()
