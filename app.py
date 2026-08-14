import urllib.parse
import streamlit as st

# ---------------------------------------------------------
# ページ基本設定
# ---------------------------------------------------------
st.set_page_config(
    page_title="大規模修繕AI適正診断ツール",
    page_icon="🏢",
    layout="centered",
)

# ---------------------------------------------------------
# X（旧Twitter）共有ボタン表示関数
# ---------------------------------------------------------
def create_x_share_button(
    units: int,
    estimated_cost: int,
    fair_cost: int,
    diff: int,
    times: str,
    app_url: str,
    is_default: bool,
):
    """診断結果をXに共有するボタンを生成（安全対策・URLエンコード済み）"""
    if diff > 0:
        status_text = f"相場より約{diff:,}万円高めの可能性あり"
    elif diff < 0:
        status_text = f"相場より約{abs(diff):,}万円抑えられた試算"
    else:
        status_text = "ほぼ相場通りの試算"

    share_text = (
        f"【大規模修繕AI適正診断】\n"
        f"🏢 戸数: {units}戸（{times}）\n"
        f"💰 管理会社の提示額: 約{estimated_cost:,}万円\n"
        f"📊 相場目安（推計）: 約{fair_cost:,}万円\n"
        f"📢 判定: {status_text}\n"
        f"※国交省実態調査データ基準の簡易試算です\n\n"
        f"自分のマンションも気になったら一発診断👇\n"
    )

    hashtags = "大規模修繕,マンション管理,修繕積立金"

    encoded_text = urllib.parse.quote(share_text)
    encoded_url = urllib.parse.quote(app_url)
    encoded_hashtags = urllib.parse.quote(hashtags)

    x_share_url = f"https://x.com/intent/tweet?text={encoded_text}&url={encoded_url}&hashtags={encoded_hashtags}"

    st.markdown("---")
    st.subheader("📲 診断結果をX（旧Twitter）で共有する")

    # 1. サンプル値（デフォルト）のまま投稿しようとしている場合の警告
    if is_default:
        st.warning(
            "⚠️ **現在の入力値は初期設定（サンプル値）のままです。** ご自身のマンションの数値に変更してから共有することをおすすめします。"
        )

    # 2. 実物件特定に関する安全注意書き
    st.caption(
        "🔒 **投稿時のご注意**\n"
        "・実在する物件名や、特定につながる詳細情報の記載はお控えください。\n"
        "・ポスト内容はXの投稿画面が開いたあとに自由に変更できます。"
    )

    st.link_button("𝕏 で診断結果を投稿する", x_share_url, type="primary")


# ---------------------------------------------------------
# メイン画面ヘッダー
# ---------------------------------------------------------
st.title("🏢 大規模修繕 AI適正診断ツール")
st.caption(
    "国交省「令和3年度 マンション大規模修繕工事に関する実態調査」データに基づく回数別・㎡単価試算"
)

st.info(
    "💡 **「見積もり金額が適正かわからない…」とお悩みの理事・修繕委員さんへ**\n\n"
    "戸数・面積・修繕回数と管理会社の提示額を入力するだけで、国交省の実態調査データに基づいた標準相場とのギャップをチェックできます。"
)

# ---------------------------------------------------------
# 入力フォーム
# ---------------------------------------------------------
st.subheader("1. マンション情報の入力")

col1, col2 = st.columns(2)

with col1:
    units = st.number_input(
        "総戸数（戸）", min_value=5, max_value=1000, value=50, step=5
    )
    avg_area = st.number_input(
        "平均専有面積（㎡）", min_value=20, max_value=200, value=70, step=5
    )
    repair_times = st.selectbox(
        "大規模修繕の回数",
        options=["1回目", "2回目", "3回目以降"],
        index=1,  # デフォルトは「2回目」
        help="修繕回数によって工事内容や施工部位が変わるため、相場単価が異なります。",
    )

with col2:
    estimated_cost = st.number_input(
        "管理会社の見積額（万円）",
        min_value=100,
        max_value=100000,
        value=7000,
        step=100,
    )
    inflation_rate = st.slider(
        "昨今の資材・人件費高騰の補正率（%）",
        min_value=0,
        max_value=50,
        value=25,  # メインアプリ（1.25倍）に合わせてデフォルトを+25%に統一
        step=5,
        help="近年の物価高・人件費上昇を考慮した補正値です（標準目安: +25%前後）",
    )

# デフォルト入力値のままか判定するフラグ（補正率25%を含む）
is_default_input = (
    units == 50
    and avg_area == 70
    and estimated_cost == 7000
    and repair_times == "2回目"
    and inflation_rate == 25
)

# ---------------------------------------------------------
# 診断ロジック（計算）
# 国交省データ（令和3年度実態調査・回数別専有面積当たり工事費中央値）
# 1回目：約1.1万円/㎡（11,000円/㎡）
# 2回目：約1.3万円/㎡（13,000円/㎡）
# 3回目以降：約1.2万円/㎡（12,000円/㎡）
# ---------------------------------------------------------
sqm_price_map = {
    "1回目": 1.1,
    "2回目": 1.3,
    "3回目以降": 1.2,
}

base_sqm_price = sqm_price_map[repair_times]  # 万円/㎡
total_private_area = units * avg_area  # 総専有面積（㎡）

# 基礎相場（万円） ＝ 総専有面積 × 回数別㎡単価
raw_fair_cost = total_private_area * base_sqm_price

# インフレ補正後の相場（万円）
fair_cost = int(raw_fair_cost * (1 + inflation_rate / 100))

# 差額（万円）
diff = estimated_cost - fair_cost

# ---------------------------------------------------------
# 診断結果の表示
# ---------------------------------------------------------
st.markdown("---")
st.subheader("2. 診断結果")

m_col1, m_col2, m_col3 = st.columns(3)

m_col1.metric(
    label="相場目安（推計）",
    value=f"約{fair_cost:,}万円",
)

m_col2.metric(
    label="管理会社提示額",
    value=f"{estimated_cost:,}万円",
)

# deltaに差額数値を正しく渡して表示バグ（矢印と色の反転）を解消
m_col3.metric(
    label="相場との乖離",
    value=f"{diff:+,}万円",
    delta=f"{diff:+,}万円",
    delta_color="inverse",  # プラス（高額）だと赤字、マイナス（割安）だと緑字
)

# アドバイスコメント
if diff > (fair_cost * 0.2):
    st.error(
        f"⚠️ **【注意】提示額が相場より大幅に高い可能性があります（＋約{diff:,}万円）**\n\n"
        "見積もり内訳の査定や、第三者（セカンドオピニオン）への相見積もり検討をおすすめします。"
    )
elif diff > 0:
    st.warning(
        f"💡 **提示額はやや高めの傾向です（＋約{diff:,}万円）**\n\n"
        "不要な工事項目が含まれていないか、仕様の見直しを行うことでコストカットできる可能性があります。"
    )
else:
    st.success(
        "✅ **提示額は標準的な相場範囲内、または比較的抑えられたプランです**\n\n"
        "金額面での大きな乖離は見られません。保証内容や施工品質を中心に確認を進めてください。"
    )

st.caption(
    "※表示される「相場目安」は調査データの中央値を基準とした試算値です。建物の形状（タワー・団地型等）や設備仕様、劣化状況により実際には一定の幅（レンジ）が存在します。"
)

# ---------------------------------------------------------
# X（旧Twitter）共有ボタンの設置
# ---------------------------------------------------------
APP_URL = "https://mansion-shuzen-ai.streamlit.app/"
create_x_share_button(
    units,
    estimated_cost,
    fair_cost,
    diff,
    repair_times,
    APP_URL,
    is_default_input,
)

# ---------------------------------------------------------
# フッター・注意事項
# ---------------------------------------------------------
st.markdown("---")
st.caption(
    "※本ツールは国土交通省「[令和3年度 マンション大規模修繕工事に関する実態調査](https://www.mlit.go.jp/jutakukentiku/house/content/001619430.pdf)」"
    "の回数別専有面積当たり工事費データをベースとした簡易シミュレーションです。\n\n"
    "🛠 **ベータ版フィードバック受付中**：ご意見や不具合の報告はXのアカウント（@shiroutomansion）までお願いいたします。"
)
