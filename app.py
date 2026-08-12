import streamlit as st
import pandas as pd
import re
import plotly.graph_objects as go
from pypdf import PdfReader
import unicodedata

# 画面基本設定
st.set_page_config(
    page_title="マンション大規模修繕AI診断",
    page_icon="🏢",
    layout="wide"
)

# ----------------------------------------------------
# 金額変換・フォーマット関数
# ----------------------------------------------------
def parse_amount(val):
    if isinstance(val, (int, float)):
        return int(val)
    s = str(val).replace("¥", "").replace("￥", "").replace(",", "").replace("円", "").strip()
    try:
        return int(s)
    except ValueError:
        return 0

def fmt_yen_box(val):
    return f"¥ {int(val):,}"

# ----------------------------------------------------
# 状態同期用コールバック関数
# ----------------------------------------------------
preset_options = ["自由入力", "A社案（管理会社・約7,500万円）", "B社案（直接施工・約5,500万円）", "C社案（最適化・約3,500万円）"]

def on_currency_change(key_name):
    raw_val = st.session_state.get(key_name, "")
    num = parse_amount(raw_val)
    st.session_state[key_name] = fmt_yen_box(num)
    
    if key_name == "shared_cost":
        st.session_state.preset_key = preset_options[0]

def handle_preset_change():
    selected = st.session_state.preset_key
    st.session_state.extraction_context = "" 
    
    if selected == preset_options[1]:
        st.session_state.shared_cost = "¥ 75,000,000"
    elif selected == preset_options[2]:
        st.session_state.shared_cost = "¥ 55,000,000"
    elif selected == preset_options[3]:
        st.session_state.shared_cost = "¥ 35,000,000"

# ----------------------------------------------------
# システム共有ステート初期化
# ----------------------------------------------------
if "shared_units" not in st.session_state:
    st.session_state.shared_units = 50
if "shared_area" not in st.session_state:
    st.session_state.shared_area = 70 
if "shared_repair_count" not in st.session_state:
    st.session_state.shared_repair_count = "1回目"
if "shared_reserve" not in st.session_state:
    st.session_state.shared_reserve = "¥ 50,000,000"
if "shared_cost" not in st.session_state:
    st.session_state.shared_cost = "¥ 75,000,000"
if "shared_rate" not in st.session_state:
    st.session_state.shared_rate = 1.00
if "shared_years" not in st.session_state:
    st.session_state.shared_years = 10
if "shared_inflation" not in st.session_state:
    st.session_state.shared_inflation = 1.25
if "preset_key" not in st.session_state:
    st.session_state.preset_key = preset_options[1]

if "applied_data" not in st.session_state:
    st.session_state.applied_data = {
        "total_units": 50,
        "average_area": 70,
        "repair_count": "1回目",
        "reserve_fund": 50000000,
        "total_cost": 75000000,
        "loan_interest_rate": 1.00,
        "loan_years": 10,
        "inflation_rate": 1.25,
        "has_applied": False
    }
if "extraction_context" not in st.session_state:
    st.session_state.extraction_context = ""

# ----------------------------------------------------
# PDF自動抽出ロジック
# ----------------------------------------------------
def extract_cost_from_file(uploaded_file):
    text = ""
    try:
        if uploaded_file.name.lower().endswith('.pdf'):
            reader = PdfReader(uploaded_file)
            for page in reader.pages:
                extracted = page.extract_text()
                if extracted:
                    text += extracted
        elif uploaded_file.name.lower().endswith(('.xls', '.xlsx')):
            df = pd.read_excel(uploaded_file)
            text = df.to_string()
            
        if not text.strip():
            return 0, "error_scanned"

        clean_text = unicodedata.normalize('NFKC', text).replace('\n', ' ')
        pattern = r"(.{0,15}(?:合計|総額|税込|金額|見積).{0,15}?)([1-9][0-9]{0,2}(?:,[0-9]{3})+|[1-9][0-9]{5,})"
        matches = re.findall(pattern, clean_text)
        
        valid_amounts = []
        for context, num_str in matches:
            num = int(num_str.replace(",", ""))
            if 1000000 <= num <= 2000000000:
                valid_amounts.append((num, context.strip() + num_str))
                
        if valid_amounts:
            best_match = max(valid_amounts, key=lambda x: x[0])
            return best_match[0], f"自動抽出箇所: 「 ... {best_match[1]} ... 」"
            
    except Exception as e:
        pass
    
    return 0, "error_not_found"

# ----------------------------------------------------
# タイトル・ヘッダー
# ----------------------------------------------------
st.title("🏢 マンション大規模修繕工事 見積もりAI適正診断（β版）")
st.caption("基準データ：国土交通省「令和3年度 マンション大規模修繕工事に関する実態調査」/ 最新の建設物価高騰を補正済")
st.markdown("左側の入力欄で条件を設定（またはファイルアップロード）し、サイドバー下の **「🔄 更新する」** ボタンを押すと診断結果に反映されます。")
st.divider()

# ----------------------------------------------------
# サイドバー：入力機能
# ----------------------------------------------------
st.sidebar.header("📋 物件・資金情報の入力")
input_mode = st.sidebar.radio("入力方法の選択", ["数値の直接入力", "ファイルアップロード（Excel/PDF）"])

if input_mode == "数値の直接入力":
    st.sidebar.selectbox("💡 試算サンプルの選択", options=preset_options, key="preset_key", on_change=handle_preset_change)
    
    st.sidebar.subheader("1. 物件・組合条件")
    st.sidebar.number_input("総戸数（戸）", min_value=1, max_value=2000, step=1, key="shared_units")
    st.sidebar.number_input("1戸あたりの平均専有面積（㎡）", min_value=10, max_value=300, step=1, key="shared_area")
    st.sidebar.selectbox("今回の大規模修繕は？", ["1回目", "2回目", "3回目以降"], key="shared_repair_count")
    st.sidebar.text_input("現在の修繕積立金残高（円）", key="shared_reserve", on_change=on_currency_change, args=("shared_reserve",))
    
    st.sidebar.subheader("2. 見積金額（税込）")
    st.sidebar.text_input("見積総額（円）", key="shared_cost", on_change=on_currency_change, args=("shared_cost",))
    
    with st.sidebar.expander("借入条件の調整（不足発生時）"):
        st.number_input("借入金利（年率%）", min_value=0.0, step=0.05, format="%.2f", key="shared_rate")
        st.number_input("借入期間（年）", min_value=1, max_value=35, step=1, key="shared_years")

else: # ファイルアップロード
    st.sidebar.subheader("1. ファイル選択")
    uploaded_file = st.sidebar.file_uploader("見積書をドラッグ＆ドロップ", type=["xlsx", "xls", "pdf"], key="file_uploader")
    
    if uploaded_file is not None:
        if st.session_state.get("last_uploaded_filename") != uploaded_file.name:
            st.session_state.last_uploaded_filename = uploaded_file.name
            extracted_cost, context_msg = extract_cost_from_file(uploaded_file)
            
            if extracted_cost == 0:
                st.session_state.shared_cost = ""
                st.session_state.extraction_context = ""
                st.session_state.preset_key = preset_options[0]
                if context_msg == "error_scanned":
                    st.sidebar.error("⚠️ 画像PDFのため文字を読み取れません。手動で入力してください。")
                else:
                    st.sidebar.warning("⚠️ 金額を自動で読み取れませんでした。手動で入力してください。")
            else:
                st.session_state.shared_cost = fmt_yen_box(extracted_cost)
                st.session_state.extraction_context = context_msg
                st.session_state.preset_key = preset_options[0]
                st.sidebar.success(f"ファイルを読み込みました！")

    st.sidebar.subheader("2. 読み込み数値の確認・調整")
    st.sidebar.number_input("総戸数（戸）", min_value=1, max_value=2000, step=1, key="shared_units")
    st.sidebar.number_input("1戸あたりの平均専有面積（㎡）", min_value=10, max_value=300, step=1, key="shared_area")
    st.sidebar.selectbox("今回の大規模修繕は？", ["1回目", "2回目", "3回目以降"], key="shared_repair_count")
    st.sidebar.text_input("現在の修繕積立金残高（円）", key="shared_reserve", on_change=on_currency_change, args=("shared_reserve",))
    
    st.sidebar.caption("※正しく抽出されていない場合は手で修正してください")
    st.sidebar.text_input("抽出された見積もり金額（円）", key="shared_cost", on_change=on_currency_change, args=("shared_cost",))
    
    with st.sidebar.expander("借入条件の調整（不足発生時）"):
        st.number_input("借入金利（年率%）", min_value=0.0, step=0.05, format="%.2f", key="shared_rate")
        st.number_input("借入期間（年）", min_value=1, max_value=35, step=1, key="shared_years")

st.sidebar.write("---")
st.sidebar.subheader("3. 詳細設定（任意）")
with st.sidebar.expander("相場の物価上昇補正"):
    st.number_input("インフレ補正係数（倍）", min_value=1.0, max_value=2.0, step=0.05, key="shared_inflation")
    st.caption("※令和3年の国交省データに対し、直近の建設資材・人件費高騰分を何倍で見積もるか（デフォルト1.25倍）")

st.sidebar.write("---")

# 更新ボタン
cur_cost_val = parse_amount(st.session_state.shared_cost)
if cur_cost_val == 0:
    st.sidebar.error("※見積もり金額が入力されていません。")
    update_btn = st.sidebar.button("🔄 更新する", type="primary", use_container_width=True, disabled=True)
else:
    update_btn = st.sidebar.button("🔄 更新する", type="primary", use_container_width=True)

if update_btn:
    st.session_state.applied_data = {
        "total_units": st.session_state.shared_units,
        "average_area": st.session_state.shared_area,
        "repair_count": st.session_state.shared_repair_count,
        "reserve_fund": parse_amount(st.session_state.shared_reserve),
        "total_cost": parse_amount(st.session_state.shared_cost),
        "loan_interest_rate": st.session_state.shared_rate,
        "loan_years": st.session_state.shared_years,
        "inflation_rate": st.session_state.shared_inflation,
        "has_applied": True
    }
    st.sidebar.success("✅ 画面のデータを更新しました！")

# ----------------------------------------------------
# 右側メイン画面出力
# ----------------------------------------------------
applied = st.session_state.applied_data

is_sample_data = not applied["has_applied"]
if is_sample_data:
    st.warning("⚠️ **【現在表示されているのはデモ用のサンプルデータです】**\n左側のメニューからご自身のマンションの数値を入力し、**「🔄 更新する」** ボタンを押して診断を実行してください。")

if st.session_state.extraction_context:
    with st.expander("🔍 見積書からの自動抽出根拠を確認", expanded=True):
        st.code(st.session_state.extraction_context, language="text")
        st.caption("※書類内に複数金額がある場合、最大値を採用しています。意図しない金額の場合は左側で手修正してください。")

total_units = applied["total_units"]
average_area = applied["average_area"]
repair_count = applied["repair_count"]
reserve_fund_input = applied["reserve_fund"]
total_cost_input = applied["total_cost"]
loan_interest_rate = applied["loan_interest_rate"]
loan_years = applied["loan_years"]
inflation_rate = applied["inflation_rate"]

total_building_area = total_units * average_area

# ----------------------------------------------------
# 🎯 適正相場の精密計算（中央値 ＋ レンジ ＋ インフレ補正）
# ----------------------------------------------------
# 【出典】国交省「令和3年度 実態調査」P.15 大規模修繕工事回数と床面積（㎡）あたり工事金額
if repair_count == "1回目":
    mlit_unit_price = 11000  # 中央値
    mlit_low = 9000          # 下位25%
    mlit_high = 14000        # 上位25%
elif repair_count == "2回目":
    mlit_unit_price = 13000  # 中央値
    mlit_low = 11000         # 下位25%
    mlit_high = 16000        # 上位25%
else: # 3回目以降
    mlit_unit_price = 12000  # 中央値
    mlit_low = 9000          # 下位25%
    mlit_high = 17000        # 上位25%

# ㎡単価の計算（中央値・下限・上限それぞれにインフレ補正を適用）
cost_per_sqm = total_cost_input / total_building_area if total_building_area > 0 else 0
benchmark_per_sqm = mlit_unit_price * inflation_rate
benchmark_low = mlit_low * inflation_rate
benchmark_high = mlit_high * inflation_rate

diff_sqm = cost_per_sqm - benchmark_per_sqm

# 全体金額の計算
total_cost_man = total_cost_input / 10000
reserve_fund_man = reserve_fund_input / 10000
per_unit_cost_man = total_cost_man / total_units if total_units > 0 else 0

mlit_avg_total_yen = total_building_area * benchmark_per_sqm
mlit_avg_total_man = mlit_avg_total_yen / 10000

diff_fund_man = reserve_fund_man - total_cost_man
shortfall_man = abs(diff_fund_man) if diff_fund_man < 0 else 0
shortfall_yen = shortfall_man * 10000

diff_from_mlit_avg = total_cost_man - mlit_avg_total_man
ratio_to_mlit_avg = total_cost_man / mlit_avg_total_man if mlit_avg_total_man > 0 else 0

# 借入計算
monthly_payment_total = 0
if shortfall_yen > 0:
    n = loan_years * 12
    if loan_interest_rate == 0.0:
        monthly_payment_total = shortfall_yen / n
    else:
        r = (loan_interest_rate / 100) / 12
        monthly_payment_total = shortfall_yen * (r * (1 + r)**n) / ((1 + r)**n - 1)
        
    monthly_payment_per_unit = monthly_payment_total / total_units
    total_repayment_total = monthly_payment_total * n
    total_repayment_per_unit = total_repayment_total / total_units
    total_interest_total = total_repayment_total - shortfall_yen

# ① 収支診断
st.subheader("💰 ① 修繕積立金残高 と 工事費の収支診断")
col_a, col_b, col_c = st.columns(3)
col_a.metric("現在の積立金残高", f"{reserve_fund_man:,.0f} 万円", delta=f"¥ {int(reserve_fund_input):,}", delta_color="off")
col_b.metric("工事見積総額", f"{total_cost_man:,.0f} 万円", delta=f"¥ {int(total_cost_input):,}", delta_color="off")

if diff_fund_man >= 0:
    col_c.metric("収支差額（余剰金）", f"+{diff_fund_man:,.0f} 万円", delta="自己資金で全額充当可能", delta_color="normal")
    if not is_sample_data:
        st.success(f"🎉 **【自己資金で完結可能】** 現在の積立金残高の範囲内で工事を実施できます。借入は不要です。")
else:
    col_c.metric("収支差額（資金不足）", f"-{shortfall_man:,.0f} 万円", delta="手元資金超過・借入が必要", delta_color="inverse")
    if not is_sample_data:
        st.error(f"⚠️ **【手元資金オーバー】** 工事実施には **¥ {int(shortfall_yen):,}** の不足が発生します。借入または修繕積立金の値上げが必要です。")

st.divider()

# ② ㎡単価での適正チェック
st.subheader("💡 ② ㎡単価での適正チェック（相場比較）")
col_s1, col_s2, col_s3 = st.columns(3)

# 高い＝赤／安い＝緑 を常に維持するため "inverse" に固定
delta_color_sqm = "inverse"
delta_text_sqm = f"{'+' if diff_sqm > 0 else ''}{int(diff_sqm):,} 円/㎡"

col_s1.metric("今回の見積単価", f"{int(cost_per_sqm):,} 円/㎡", delta=f"中央値相場より {delta_text_sqm}", delta_color=delta_color_sqm)
col_s2.metric("適正相場単価（中央値・補正後）", f"{int(benchmark_per_sqm):,} 円/㎡", delta=f"国交省相場({repair_count}) {mlit_unit_price:,}円 × {inflation_rate}倍", delta_color="off")

st.caption(f"※国交省データ（{repair_count}）における一般的な価格幅（下位25%〜上位25%）は **{int(mlit_low):,}円〜{int(mlit_high):,}円/㎡** です。今回のインフレ補正（{inflation_rate}倍）を適用すると、適正と呼べる価格幅の目安は **{int(benchmark_low):,}円〜{int(benchmark_high):,}円/㎡** となります（※上下限の目安も中央値と同じ倍率で補正した概算です）。")

st.divider()

# ③ 借入シミュレーション
st.subheader("🏦 ③ 借入シミュレーション")
if shortfall_man > 0:
    col_l1, col_l2, col_l3 = st.columns(3)
    col_l1.metric("必要借入金額（組合総額）", f"¥ {int(shortfall_yen):,}", delta=f"{shortfall_man:,.0f} 万円", delta_color="off")
    col_l2.metric("1戸あたりの毎月返済負担増", f"¥ {monthly_payment_per_unit:,.0f} / 月", delta=f"組合全体：月 ¥ {int(monthly_payment_total):,}", delta_color="inverse")
    col_l3.metric("1戸あたりの総返済額（元利合計）", f"{total_repayment_per_unit/10000:,.1f} 万円 / 戸", delta=f"利息総額: ¥ {int(total_interest_total):,}", delta_color="inverse")
    if not is_sample_data:
        st.warning(f"**💡 インパクト:** 組合は今後{loan_years}年間にわたり、毎月の修繕積立金を **「＋ ¥ {monthly_payment_per_unit:,.0f} / 月」** 値上げしなければなりません。")
else:
    st.info("💡 手元資金内に収まっているため、借入および毎月の積立金値上げは発生しません。")

st.divider()

# ④ Plotlyグラフ
st.subheader("📊 ④ 全体相場との比較＆資金バランス")

# 改行タグ（<br>）を使用して正しく表示されるように修正
labels = ['★ 今回見積もり', '積立金残高（手元資金）', f'国交省相場ベース<br>({repair_count}・補正後)']
vals = [total_cost_man, reserve_fund_man, mlit_avg_total_man]
colors = ['#FF5722' if total_cost_man > reserve_fund_man else '#00BCD4', '#2196F3', '#4CAF50']

fig = go.Figure()
fig.add_trace(go.Bar(
    y=labels,
    x=vals,
    orientation='h',
    marker_color=colors,
    text=[f"{v:,.0f}万円" for v in vals],
    textposition='auto',
    textfont=dict(color='white', weight='bold')
))

fig.add_vline(x=reserve_fund_man, line_dash="dash", line_color="blue", annotation_text="手元資金ライン", annotation_position="top right")

fig.update_layout(
    xaxis_title="金額（万円）",
    margin=dict(l=0, r=0, t=30, b=0),
    height=300,
    font=dict(family="sans-serif", size=14)
)

st.plotly_chart(fig, use_container_width=True)

st.caption(f"""
🔗 **データ出典・算出根拠:** 
・**ベース単価:** [国土交通省「令和3年度 マンション大規模修繕工事に関する実態調査結果」](https://www.mlit.go.jp/jutakukentiku/house/content/001619430.pdf) の **「④大規模修繕工事回数と床面積（㎡）あたり工事金額」（PDF P.15）** に掲載されている実績データに基づいています。本アプリでは外れ値の影響を受けにくい「中央値」をベースとし、1回目:11,000円/㎡、2回目:13,000円/㎡、3回目以降:12,000円/㎡ を採用しています（※修繕積立金のガイドラインとは別の実証データです）。
・**インフレ補正:** 上記の過去のベース単価に、サイドバーで設定した「インフレ補正係数（デフォルト1.25倍）」を掛けたものを、本アプリ独自の適正相場としています（公式統計の確定値ではありません。上下限の目安も中央値と同じ倍率で補正した概算です）。
・**総面積計算:** 各戸の面積が異なる場合でも、入力された「平均専有面積」を用いて一律計算した簡易的な概算値です。
""")

st.divider()

# ⑤ サマリーテキスト出力
st.subheader("📝 ⑤ 理事会・住民総会提出用サマリーテキスト")
if shortfall_man > 0:
    shortage_msg = f"手元資金（積立金残高：{reserve_fund_man:,.0f}万円）に対して【¥ {int(shortfall_yen):,}（{shortfall_man:,.0f}万円）】不足します。\n借入（金利{loan_interest_rate:.2f}%・{loan_years}年返済）を利用した場合、全住民の毎月修繕積立金を【＋ ¥ {monthly_payment_per_unit:,.0f} / 月】引き上げる必要があります。"
else:
    shortage_msg = f"手元資金（積立金残高：{reserve_fund_man:,.0f}万円）の枠内に収まっており、借入および積立金の値上げは不要です。"

script_text = f"""【大規模修繕工事 収支・相場診断結果サマリー（{repair_count}）】
■ 見積総額：¥ {int(total_cost_input):,}（{total_cost_man:,.0f}万円 / 1戸あたり {per_unit_cost_man:.1f}万円）
■ ㎡単価：{int(cost_per_sqm):,} 円/㎡
（中央値相場：{int(benchmark_per_sqm):,} 円/㎡ / 適正価格幅の目安：{int(benchmark_low):,}〜{int(benchmark_high):,} 円/㎡）
■ 適正相場との乖離：インフレ補正後の中央値相場総額より {diff_from_mlit_avg:,.0f}万円（{ratio_to_mlit_avg:.2f}倍）
■ 資金収支：{shortage_msg}"""

st.text_area("コピペ用サマリー", value=script_text, height=150)

st.divider()

# β版表示とセキュリティ明記
st.subheader("💬 β版へのご意見・不具合報告")
st.info("💡 本アプリは現在β版です。今後の改善の参考にさせていただきますので、ぜひフィードバックをお寄せください。")

st.markdown("👉 **[ご意見・不具合報告フォームはこちら（匿名で回答できます）](https://forms.gle/Svy4oDZUsVYwoTBP9)**")

st.caption("""
**【セキュリティ・データ管理について】**
本アプリのプログラム自体は、入力されたデータやアップロードされたファイルをサーバーに永続保存・収集する処理を行っておりません（※お使いのブラウザやホスティング環境の一時メモリ上でのみ処理・破棄されます）。

**【免責事項】**
本ツールは前述のデータに基づく概算診断です。実際の工事費は建物の劣化状況、構造、施工環境、仕様変更等により変動します。最終的な工事判断・契約にあたっては、必ず施工会社や専門家による現地調査・正式見積もりをご確認ください。
""")