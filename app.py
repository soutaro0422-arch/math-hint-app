import streamlit as st
import json
from google import genai
from google.genai import types
import streamlit.components.v1 as components  # JavaScriptを動かすために追加

st.set_page_config(
    page_title="数学ヒントマシーン", 
    page_icon="🧮",
    layout="centered"
)

client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])

st.title("数学ヒントマシーン 🧮")
st.caption("問題集の写真を撮るだけで、AIがあなた専用の段階的ヒントを作成します。")

if "math_data" not in st.session_state:
    st.session_state.math_data = None
# JavaScriptからの画像データを受け取るためのセッション
if "captured_image" not in st.session_state:
    st.session_state.captured_image = None

def reset_app():
    st.session_state.math_data = None
    st.session_state.captured_image = None

# ---- STEP 1: 写真撮影・アップロード画面 ----
if st.session_state.math_data is None:
    st.markdown("### 📸 問題を撮影")
    
    # 💡 JavaScriptを使って「背面カメラ（environment）」を強制するカスタムカメラコンポーネント
    camera_html = """
    <div style="text-align: center; font-family: sans-serif;">
        <video id="video" width="100%" autoplay playinginline style="border-radius: 10px; background: #000; max-width: 500px;"></video>
        <br><br>
        <button id="snap" style="
            background-color: #FF4B4B; 
            color: white; 
            border: none; 
            padding: 12px 24px; 
            font-size: 16px; 
            border-radius: 8px; 
            cursor: pointer;
            width: 100%;
            max-width: 500px;
            font-weight: bold;
        ">📷 問題をパシャリと撮る</button>
        <canvas id="canvas" width="640" height="480" style="display:none;"></canvas>
    </div>

    <script>
        const video = document.getElementById('video');
        const canvas = document.getElementById('canvas');
        const snap = document.getElementById('snap');

        // 【ここがポイント】 facingMode: "environment" で背面カメラを指定
        const constraints = {
            video: { facingMode: { ideal: "environment" } },
            audio: false
        };

        navigator.mediaDevices.getUserMedia(constraints)
            .then((stream) => {
                video.srcObject = stream;
            })
            .catch((err) => {
                console.error("カメラの起動に失敗しました: ", err);
            });

        snap.addEventListener('click', () => {
            const context = canvas.getContext('2d');
            // ビデオの現在のフレームをキャンバスに描画
            canvas.width = video.videoWidth;
            canvas.height = video.videoHeight;
            context.drawImage(video, 0, 0, canvas.width, canvas.height);
            
            // 画像をBase64（テキストデータ）に変換してStreamlitに送る
            const dataUrl = canvas.toDataURL('image/jpeg');
            
            # 独自のカスタムイベントでStreamlit側へデータを渡す
            window.parent.postMessage({
                type: 'streamlit:setComponentValue',
                value: dataUrl
            }, '*');
        });
    </script>
    """

    # HTMLコンポーネントを実行し、JSからの戻り値（画像データ）を受け取る
    # 返り値は自動的にそのコンポーネントの値になります
    with st.container():
        captured_data = components.html(camera_html, height=450)
        
        # 画像が撮影されたら処理を動かす
        if captured_data:
            st.session_state.captured_image = captured_data

    # 撮影された画像データ（Base64形式）がある場合の処理
    if st.session_state.captured_image:
        with st.spinner("✨ AIが問題を解析しています。答えは隠しているので安心してください..."):
            try:
                # Base64形式のテキストをバイトデータに変換
                import base64
                header, encoded = st.session_state.captured_image.split(",", 1)
                bytes_data = base64.b64decode(encoded)
                
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
                st.error(f"解析エラーが発生しました。もう一度試してください。")
                st.caption(f"エラー詳細: {e}")
                if st.button("もう一度撮る"):
                    reset_app()
                    st.rerun()

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
