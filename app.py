import streamlit as st
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import easyocr
import arabic_reshaper
from bidi.algorithm import get_display
from deep_translator import GoogleTranslator
import urllib.request
import os
import io

st.set_page_config(page_title="مترجم المانجا الذكي", page_icon="📚", layout="centered")

st.markdown("""
    <div style="text-align: right; direction: rtl;">
        <h1>📚 مترجم المانجا والقصص المصورة</h1>
        <p>ارفع أي صفحة بالإنجليزية، وسيقوم الذكاء الاصطناعي بمسح النص وترجمته إلى العربية فوراً.</p>
    </div>
""", unsafe_allow_html=True)

# تحميل خط عربي واضح للمانجا
font_path = "Cairo-Bold.ttf"
if not os.path.exists(font_path):
    urllib.request.urlretrieve("https://github.com/googlefonts/cairo/raw/main/fonts/ttf/Cairo-Bold.ttf", font_path)

@st.cache_resource
def load_ocr():
    return easyocr.Reader(['en'], gpu=False)

reader = load_ocr()

uploaded_file = st.file_uploader("اختر صفحة مانجا (JPG, PNG, WEBP)", type=["png", "jpg", "jpeg", "webp"])

if uploaded_file is not None:
    image = Image.open(uploaded_file).convert("RGB")
    st.image(image, caption="الصفحة الأصلية", use_container_width=True)

    if st.button("🚀 ترجمة الصفحة الآن", use_container_width=True):
        with st.spinner("جارٍ اكتشاف النصوص، تفريغ الفقاعات، والترجمة للعربية..."):
            img_bgr = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
            h_img, w_img = img_bgr.shape[:2]

            # 1. كشف أماكن النصوص
            results = reader.readtext(img_bgr)

            if not results:
                st.warning("لم يتم اكتشاف نصوص في هذه الصفحة.")
            else:
                mask = np.zeros((h_img, w_img), dtype=np.uint8)
                boxes = []

                for (bbox, text, conf) in results:
                    if conf < 0.2 or len(text.strip()) == 0:
                        continue
                    pts = np.array(bbox, dtype=np.int32)
                    x_min = max(0, int(np.min(pts[:, 0])))
                    x_max = min(w_img, int(np.max(pts[:, 0])))
                    y_min = max(0, int(np.min(pts[:, 1])))
                    y_max = min(h_img, int(np.max(pts[:, 1])))
                    w, h = x_max - x_min, y_max - y_min

                    # رسم القناع لمسح النص
                    cv2.rectangle(mask, (x_min, y_min), (x_max, y_max), 255, -1)

                    # ترجمة النص إلى العربية
                    try:
                        ar_text = GoogleTranslator(source='en', target='ar').translate(text)
                    except:
                        ar_text = text

                    boxes.append((x_min, y_min, w, h, ar_text))

                # 2. إزالة النص الإنجليزي وترميم الخلفية
                cleaned = cv2.inpaint(img_bgr, mask, 3, cv2.INPAINT_TELEA)
                res_pil = Image.fromarray(cv2.cvtColor(cleaned, cv2.COLOR_BGR2RGB))
                draw = ImageDraw.Draw(res_pil)

                # 3. كتابة النص العربي وتنسيقه داخل الفقاعات
                for (x, y, w, h, ar_text) in boxes:
                    reshaped = arabic_reshaper.reshape(ar_text)
                    bidi_text = get_display(reshaped)
                    font_size = max(12, int(h * 0.42))
                    try:
                        font = ImageFont.truetype(font_path, font_size)
                    except:
                        font = ImageFont.load_default()

                    draw.text((x + 5, y + int(h * 0.2)), bidi_text, fill=(0, 0, 0), font=font)

                st.success("تمت الترجمة بنجاح!")
                st.image(res_pil, caption="النتيجة المترجمة للعربية", use_container_width=True)

                # زر تنزيل الصورة الناتجة
                buf = io.BytesIO()
                res_pil.save(buf, format="PNG")
                st.download_button(
                    label="📥 تحميل الصفحة المترجمة",
                    data=buf.getvalue(),
                    file_name="manga_translated_ar.png",
                    mime="image/png",
                    use_container_width=True
                )
