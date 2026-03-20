'''
web/app.py

uvicorn api.server:app --reload --port 8000
streamlit run web/app.py

访问http://localhost:8501/

注意代理网络问题

'''
import streamlit as st
import requests

st.title("Citation Agent")

uploaded_file = st.file_uploader("上传PDF", type=["pdf"])

if uploaded_file is not None:
    if st.button("开始分析"):

        st.info("正在上传并分析，请稍等……")

        files = {
            "file": (
                uploaded_file.name,
                uploaded_file.getvalue(),  # ✅ 关键
                "application/pdf"
            )
        }

        try:
            response = requests.post(
                "http://localhost:8000/verify_paper",
                files=files
            )

            st.write("状态码:", response.status_code)
            # st.write("原始返回:", response.text)

            if response.status_code == 200:
                data = response.json()  # ✅ 必须加()

                if data.get("cache"):
                    st.success("命中缓存，快")
                else:
                    st.warning("实时计算，慢")

                st.success("分析完成！")

                for item in data.get("results", []):
                    st.markdown("---")
                    st.write("引用：", item.get("ref", ""))
                    st.write("类型:", item.get("type", ""))

                    verdict = item.get("verdict", "")

                    if verdict == "valid":
                        st.success("正确！")
                    else:
                        st.error("错误！")

                    st.write("原因：", item.get("reason", ""))  # ✅ 修复
                    st.write("置信度：", item.get("confidence", ""))

        except Exception as e:
            st.error(f"API调用失败: {e}")