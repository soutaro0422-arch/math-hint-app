import streamlit as st
import json
from google import genai
from google.genai import types

# ページ設定：最初からすっきりした見た目に
st.set_page_config(
    page_title="数学ヒントマシーン", 
    page_icon="🧮",
    layout="centered"
)

# APIクライアント初期化
client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])

# タイトルエリア（絵文字とキャッチコピーで今風に）
st.title("数学ヒントマシーン 🧮")
st.caption("問題集の写真を撮るだけで、AIがあなた専用の段階的ヒントを作成します。")

# セッション状態の初期化
if "math_data" not in st.session_state:
    st.session_state.math_data = None

# リセット関数
def reset_app():
    st.session_state.math_data = None

# ---- STEP 1: 写真撮影・アップロード画面 ----
if st.session_state.math_data is None:
    st.markdown("### 📸 問題を撮影")
    img_file = st.camera_input("問題集を真上から、文字がハッキリ見えるように撮影してください")
    
    if img_file:
        with st.spinner("✨ AIが問題を解析しています。答えは隠しているので安心してください..."):
            bytes_data = img_file.getvalue()
            
            # AIへのプロンプト（よりJSONが安定するように指示を最適化）
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
                
                # パースして保存
                st.session_state.math_data = json.loads(response.text)
                st.rerun()
                
            except Exception as e:
                st.error(f"解析エラーが発生しました。もう一度きれいに撮影し直すか、時間を置いて試してください。")
                st.caption(f"エラー詳細: {e}")

# ---- STEP 2: 段階的なヒント表示画面（おしゃれレイアウト） ----
else:
    data = st.session_state.math_data
    
    # 認識した問題（カード風に見せる）
    st.markdown("### 📝 認識された問題")
    st.info(data['problem_text'])
    
    st.markdown("### 💡 段階的ヒント")
    st.write("上から順番に開けて、自力で解けるかチャレンジしてみよう！")
    
    # アコーディオン（Expander）を使って、ユーザーが自分でクリックして開くお洒落UI
    with st.expander("🔍 【Level 1】 最初のヒント（公式・着眼点）"):
        st.markdown(f"### 💡 ヒント 1\n{data['hint_1']}")
        
    with st.expander("⚡ 【Level 2】 もう一押しのヒント（計算の方針）"):
        st.markdown(f"### 🧭 ヒント 2\n{data['hint_2']}")
        
    with st.expander("🎯 【Level 3】 途中式と最終解答"):
        st.markdown("### 🛠️ 途中式（解法のプロセス）")
        st.markdown(data['steps'])
        
        st.markdown("---")
        st.markdown(f"### 🎯 最終解答\n**{data['final_answer']}**")

    # 下部にアクションボタンを配置
    st.write("---")
    
    # リセットボタン（再撮影）を目立たせる
    if st.button("🔄 別の問題を撮影する", use_container_width=True, type="secondary"):
        reset_app()
        st.rerun()
