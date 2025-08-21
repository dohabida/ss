import io
import pandas as pd
import streamlit as st
import plotly.express as px
import seaborn as sns
import matplotlib.pyplot as plt

st.set_page_config(page_title="사이버 범죄 통계 대시보드", page_icon="💻", layout="wide")
st.title("💻 경찰청 연도별 사이버 범죄 통계 대시보드")

uploaded = st.file_uploader("CSV 파일 업로드", type=["csv"])
if uploaded is not None:
    # ✅ 업로드 파일을 바이트로 고정 → 재시도해도 포인터 문제 없음
    raw = uploaded.getvalue()

    def read_csv_safely(raw_bytes):
        # 인코딩 후보 순회 (BOM 포함 utf-8-sig부터)
        for enc in ["utf-8-sig", "utf-8", "cp949", "euc-kr"]:
            try:
                return pd.read_csv(io.BytesIO(raw_bytes), encoding=enc)
            except UnicodeDecodeError:
                continue
        # 구분자 이슈(세미콜론 등) 대비 추가 시도
        for enc in ["utf-8-sig", "utf-8", "cp949", "euc-kr"]:
            try:
                return pd.read_csv(io.BytesIO(raw_bytes), encoding=enc, sep=";")
            except Exception:
                continue
        raise ValueError("지원 인코딩/구분자 조합으로 읽을 수 없습니다.")

    try:
        df = read_csv_safely(raw)
    except Exception as e:
        st.error(f"파일을 읽는 중 오류가 발생했습니다: {e}")
        st.stop()

    # ---- 이후 동일 (필요한 최소 전처리) ----
    # 열 이름 공백 제거
    df.columns = [c.strip() for c in df.columns]
    # 연도 숫자화
    if "연도" in df.columns:
        df["연도"] = pd.to_numeric(df["연도"], errors="coerce").astype("Int64")

    # 발생/검거 분리
    df_cases = df[df["구분"] == "발생건수"].set_index("연도")
    df_arrests = df[df["구분"] == "검거건수"].set_index("연도")

    # 존재한다면 '구분' 열 제거
    if "구분" in df_cases.columns:
        df_cases = df_cases.drop(columns=["구분"])
    if "구분" in df_arrests.columns:
        df_arrests = df_arrests.drop(columns=["구분"])

    # 숫자화
    df_cases = df_cases.apply(pd.to_numeric, errors="coerce")
    df_arrests = df_arrests.apply(pd.to_numeric, errors="coerce")

    # 검거율(%) 계산
    df_rate = (df_arrests / df_cases) * 100

    # ---- 사이드바 ----
    st.sidebar.header("⚙️ 설정")
    year = st.sidebar.selectbox("연도 선택", sorted(df_cases.index.dropna().unique(), reverse=True))
    category = st.sidebar.selectbox("범죄 유형 선택", df_cases.columns)

    # 1) 연도별 전체 추세
    st.subheader("📈 연도별 전체 사이버 범죄 발생 추세")
    total_trend = df_cases.sum(axis=1).reset_index(name="발생건수합계")
    fig_line = px.line(total_trend, x="연도", y="발생건수합계", markers=True,
                       title="연도별 전체 사이버 범죄 발생 건수 추세")
    st.plotly_chart(fig_line, use_container_width=True)

    # 2) 범주별 비중 (파이)
    st.subheader(f"🥧 {int(year)}년 범주별 비중 (Top 10)")
    year_data = df_cases.loc[int(year)].sort_values(ascending=False).head(10)
    fig_pie = px.pie(values=year_data.values, names=year_data.index,
                     title=f"{int(year)}년 사이버 범죄 발생 비중 (Top 10)")
    st.plotly_chart(fig_pie, use_container_width=True)

    # 3) 검거율(히트맵)
    st.subheader("🔍 발생 대비 검거율 (히트맵)")
    fig, ax = plt.subplots(figsize=(14, 6))
    sns.heatmap(df_rate, cmap="coolwarm", cbar_kws={"label": "검거율(%)"}, ax=ax)
    ax.set_title("연도별 범죄 유형별 검거율(%)")
    ax.set_xlabel("범죄 유형")
    ax.set_ylabel("연도")
    st.pyplot(fig)

    # 4) 특정 범주 추세
    st.subheader(f"📊 '{category}' 연도별 발생/검거 추세")
    cat = pd.DataFrame({
        "연도": df_cases.index,
        "발생건수": df_cases[category].values,
        "검거건수": df_arrests[category].values
    })
    fig_cat = px.line(cat, x="연도", y=["발생건수", "검거건수"], markers=True,
                      title=f"{category} 발생 vs 검거 추세")
    st.plotly_chart(fig_cat, use_container_width=True)

else:
    st.info("좌측에서 CSV 파일을 업로드하세요.")
