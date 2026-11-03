"""Report deck for assignment 2 in the style of the team's assignment-1 deck (20 x 11.25 in, Pretendard, green #0E6D62).
All numbers (baseline, clean162 vs dirty162, clean339 vs random339) are written here as fixed text; they were taken
from analysis/results.json (collect_results.py). Figures come from analysis/fig_*.png.
Usage: python analysis/make_report_deck.py [out.pptx]"""
import datetime, os, sys
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE
from pptx.oxml.ns import qn
from lxml import etree

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
OUT = sys.argv[1] if len(sys.argv) > 1 else "analysis/로보틱스시뮬레이션_과제2_9조.pptx"
ASSETS = "analysis/deck_assets"
GREEN = RGBColor(0x0E, 0x6D, 0x62); INK = RGBColor(0x1A, 0x1A, 0x1A); GRAY = RGBColor(0x4C, 0x4C, 0x4C)
LIGHT = RGBColor(0xEA, 0xF3, 0xF1); NUMGRAY = RGBColor(0xD9, 0xDE, 0xDC); CAPTION = RGBColor(0x6B, 0x6B, 0x6B)
BOLD, REG, LIGHTF = "Pretendard Bold", "Pretendard Regular", "Pretendard ExtraLight"

prs = Presentation(); prs.slide_width = Inches(20); prs.slide_height = Inches(11.25)
BLANK = prs.slide_layouts[6]

def set_font(run, size, font=REG, color=INK, bold=None):
    run.font.size = Pt(size); run.font.color.rgb = color
    if bold is not None: run.font.bold = bold
    rPr = run._r.get_or_add_rPr()
    for tag in ("a:latin", "a:ea", "a:cs"):
        el = rPr.find(qn(tag))
        if el is None: el = etree.SubElement(rPr, qn(tag))
        el.set("typeface", font)

def set_bullet(p, level=0, char="•"):
    pPr = p._p.get_or_add_pPr()
    pPr.set("marL", str(int(Inches(0.25 + 0.28 * level)))); pPr.set("indent", str(-int(Inches(0.22))))
    for tag in ("a:buNone", "a:buChar", "a:buFont"):
        el = pPr.find(qn(tag))
        if el is not None: pPr.remove(el)
    bf = etree.SubElement(pPr, qn("a:buFont")); bf.set("typeface", "Arial")
    bc = etree.SubElement(pPr, qn("a:buChar")); bc.set("char", char if level == 0 else "–")

def para(tf, text, size, font=REG, color=INK, bullet=None, first=False, align=PP_ALIGN.LEFT, space_after=4, line=1.1, bold=None):
    p = tf.paragraphs[0] if first else tf.add_paragraph()
    p.alignment = align; p.line_spacing = line; p.space_after = Pt(space_after)
    r = p.add_run(); r.text = text.replace(" %", "\u00a0%"); set_font(r, size, font, color, bold)  # keep "%" with its number
    if bullet is not None: set_bullet(p, bullet)
    return p

def textbox(slide, x, y, w, h, text, size, font=REG, color=INK, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP):
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h)); tf = tb.text_frame; tf.word_wrap = True
    tf.margin_left = tf.margin_right = Inches(0.05); tf.margin_top = tf.margin_bottom = Inches(0.02); tf.vertical_anchor = anchor
    para(tf, text, size, font, color, first=True, align=align, space_after=0)
    return tb

def box(slide, x, y, w, h, heading, items, size=17, head_size=21, fill=LIGHT):
    """Rounded light-green box with a green heading and bulleted items. items: str | (level, str)"""
    shp = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
    shp.adjustments[0] = 0.078; shp.fill.solid(); shp.fill.fore_color.rgb = fill; shp.line.fill.background(); shp.shadow.inherit = False
    tf = shp.text_frame; tf.word_wrap = True; tf.vertical_anchor = MSO_ANCHOR.TOP
    tf.margin_left = tf.margin_right = Inches(0.3); tf.margin_top = Inches(0.25); tf.margin_bottom = Inches(0.2)
    para(tf, heading, head_size, BOLD, GREEN, first=True, space_after=6)
    for it in items:
        lvl, txt = it if isinstance(it, tuple) else (0, it)
        para(tf, txt, size - (1 if lvl else 0), REG, INK, bullet=lvl, space_after=5)
    return shp

def table(slide, x, y, w, rows, col_w=None, size=15, head_size=15, row_h=0.6, head_h=None, first_col_bold=True):
    """Table in the reference deck's style. A newline in a cell makes a second line (used for two-line headers)."""
    nr, nc = len(rows), len(rows[0])
    head_h = head_h or (row_h * 1.35 if any("\n" in str(v) for v in rows[0]) else row_h)
    shp = slide.shapes.add_table(nr, nc, Inches(x), Inches(y), Inches(w), Inches(head_h + row_h * (nr - 1))); tbl = shp.table
    tblPr = tbl._tbl.tblPr; tblPr.set("bandRow", "1"); tblPr.set("firstRow", "1")
    st = tblPr.find(qn("a:tableStyleId"))
    if st is None: st = etree.SubElement(tblPr, qn("a:tableStyleId"))
    st.text = "{5C22544A-7EE6-4342-B048-85BDC9FD1C3A}"
    if col_w:
        for i, cw in enumerate(col_w): tbl.columns[i].width = Inches(cw)
    for i in range(nr): tbl.rows[i].height = Inches(head_h if i == 0 else row_h)
    for i, row in enumerate(rows):
        for j, val in enumerate(row):
            c = tbl.cell(i, j); c.text = ""; tf = c.text_frame; tf.word_wrap = True; c.vertical_anchor = MSO_ANCHOR.MIDDLE
            c.margin_left = c.margin_right = Inches(0.08); c.margin_top = c.margin_bottom = Inches(0.04)
            for k, line in enumerate(str(val).split("\n")):
                p = tf.paragraphs[0] if k == 0 else tf.add_paragraph()
                p.alignment = PP_ALIGN.LEFT if j == 0 else PP_ALIGN.CENTER; p.line_spacing = 1.05
                r = p.add_run(); r.text = line
                if i == 0: set_font(r, head_size, BOLD, RGBColor(0xFF, 0xFF, 0xFF), True)
                else: set_font(r, size, BOLD if (j == 0 and first_col_bold) else REG, INK, j == 0 and first_col_bold)
            if i == 0: c.fill.solid(); c.fill.fore_color.rgb = GREEN
            else: c.fill.solid(); c.fill.fore_color.rgb = RGBColor(0xFF, 0xFF, 0xFF) if i % 2 else RGBColor(0xF3, 0xF6, 0xF5)
    return shp

def pic(slide, path, x, y, w=None, h=None, alpha=None):
    if not os.path.exists(path):
        return textbox(slide, x, y, w or 6, 0.6, f"[그림 없음: {path}]", 14, REG, CAPTION)
    kw = {}
    if w: kw["width"] = Inches(w)
    if h: kw["height"] = Inches(h)
    p = slide.shapes.add_picture(path, Inches(x), Inches(y), **kw)
    if alpha is not None:  # picture transparency as in the reference deck (alphaModFix, 10 % opacity for the arcs)
        blip = p._element.find(".//" + qn("a:blip"))
        am = etree.SubElement(blip, qn("a:alphaModFix")); am.set("amt", str(int(alpha * 100000)))
        blip.insert(0, am)
    return p

def deco(slide):
    pic(slide, f"{ASSETS}/arc_bottom_left.png", -2.2, 6.9, 7.78, 5.19, alpha=0.10)
    pic(slide, f"{ASSETS}/arc_top_right.png", 14.2, -0.8, 7.78, 5.19, alpha=0.10)
    pic(slide, f"{ASSETS}/footer_band.png", 0.0, 10.3, 20.03, 0.94)

def section_slide(num, title_en, subtitle_ko):
    s = prs.slides.add_slide(BLANK); deco(s)
    textbox(s, -0.3, -0.35, 3.2, 2.7, num, 131.77, REG, NUMGRAY)
    textbox(s, 2.3, 0.65, 15.5, 1.1, title_en, 48, BOLD, GRAY, anchor=MSO_ANCHOR.MIDDLE)
    textbox(s, 1.2, 2.0, 17.6, 0.8, subtitle_ko, 30, BOLD, GREEN)
    return s

def caption(slide, x, y, w, text):
    textbox(slide, x, y, w, 0.5, text, 14, REG, CAPTION)

RESULT_HEAD = ["조건", "seed\n101 / 111", "평균 ±\n표준편차", "첫 그립 후\n상승", "재파지\n성공률", "재파지 후 성공\n/ 전체 성공", "전환 횟수\n(파지 실패)"]
RESULT_COLS = [1.7, 1.35, 1.65, 1.4, 1.25, 1.75, 1.6]  # sums to 10.7
METRIC_NOTE = ("첫 그립 후 상승: 첫 그립 뒤 2초 안에 장난감이 2 cm 이상 들린 비율. 재파지 성공률: 첫 그립에 실패한 뒤 다시 잡아 들어 올린 비율. "
               "재파지 후 성공: 전체 성공 중 재파지를 거친 건수. 전환 횟수: 파지 실패 rollout의 그리퍼 여닫기 횟수 중앙값.")

# ---------------------------------------------------------------- 1. title
s = prs.slides.add_slide(BLANK); deco(s)
textbox(s, 1.9, 2.4, 8.0, 1.0, "2026년 2학기", 48, BOLD, GREEN)
textbox(s, 1.9, 3.1, 12.0, 1.4, "로보틱스시뮬레이션", 73, BOLD, GREEN)
bar = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(1.9), Inches(4.75), Inches(0.08), Inches(1.15)); bar.fill.solid(); bar.fill.fore_color.rgb = GREEN; bar.line.fill.background()
textbox(s, 2.1, 4.7, 9.0, 0.6, "실습 과제 2", 30, REG, GREEN)
textbox(s, 2.1, 5.3, 16.5, 0.6, "Toy2Box 모방학습: 파지 품질이 낮은 시범을 걸러내면 나아지는가", 24, REG, GREEN)
textbox(s, 13.3, 9.5, 6.4, 0.5, "9조: 윤다빈, 이두현, 이소연", 24, LIGHTF, GREEN, align=PP_ALIGN.RIGHT)

# ---------------------------------------------------------------- 2. contents
s = prs.slides.add_slide(BLANK); deco(s)
textbox(s, 6.0, 1.3, 8.0, 1.0, "CONTENTS", 48, BOLD, GREEN, align=PP_ALIGN.CENTER)
for k, name in enumerate(["Problem Formulation & Research Hypothesis", "Experimental Design", "Performance Evaluation & Analysis", "Future Directions"]):
    y = 2.8 + 1.5 * k
    rr = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(4.4), Inches(y), Inches(11.2), Inches(1.1)); rr.adjustments[0] = 0.12
    rr.fill.solid(); rr.fill.fore_color.rgb = RGBColor(0xF4, 0xF4, 0xF4); rr.line.fill.background(); rr.shadow.inherit = False
    textbox(s, 4.6, y + 0.25, 1.0, 0.6, f"0{k + 1}", 30, BOLD, RGBColor(0x8C, 0x8C, 0x8C))
    textbox(s, 5.5, y + 0.25, 10.0, 0.6, name, 30, REG, GRAY)

# ---------------------------------------------------------------- 3. baseline
s = section_slide("01", "Problem Formulation & Research Hypothesis", "Baseline 구성과 성공률")
pic(s, "analysis/fig_baseline_stages.png", 1.2, 2.9, w=10.3)
caption(s, 1.2, 8.95, 10.3, "실패 단계 분류 기준: 손–장난감 최소 거리 8 cm, 장난감 상승 5 cm, 상자까지 거리 15 cm. 20 env 평가, 두 seed × 100회.")
box(s, 12.3, 2.9, 6.5, 6.9, "Baseline 구성", [
    "데이터: 키보드 시범 20개 → 자동 주석 16개 → Mimic 생성 501개",
    "학습: BC-RNN, 2000 epoch × 100 step, batch 100, seed 101·111",
    "평가: seed 42, 100회, horizon 800. 공식 play.py와 20 env 병렬 평가 병행",
    "성공률: 공식 19 % / 27 % (23.0 ± 4.0), 20 env 28 % / 27 % (27.5 ± 0.5)",
    "실패 단계: 접근 28 %, 파지 30 %, 운반 34 %, 배치 8 %",
    "파지·운반 실패가 전체 실패의 64 %",
])

# ---------------------------------------------------------------- 4. diagnosis: gripper chattering
s = section_slide("01", "Problem Formulation & Research Hypothesis", "실패 rollout의 공통점: 그리퍼 여닫기 반복")
pic(s, "analysis/fig_grip_switches.png", 1.2, 3.25, w=5.0)
pic(s, "analysis/fig_rollout_examples.png", 6.35, 2.9, w=5.75)
caption(s, 1.2, 6.85, 10.9, "왼쪽: rollout당 그리퍼 열기·닫기 전환 횟수 (두 seed 합산 200회). 오른쪽: 성공 rollout과 운반 실패 rollout의 그리퍼 명령, gripper_pos 관측, 장난감 높이.")
box(s, 12.3, 2.9, 6.5, 6.9, "관찰", [
    "성공: 닫기 1회, 열기 1회 (전환 2회)",
    "파지 실패: 전환 중앙값 8회, 운반 실패: 6회",
    "파지·운반 실패의 74 %가 4회 이상",
    "장난감을 놓친 구간 (파지 시도 중, 낙하 후)에 집중",
    "운반 중에 놓는 경우는 드묾. 멈춰 있는 rollout은 없음",
    "질문: 이 반복은 학습 데이터의 어떤 특성에서 오는가",
])

# ---------------------------------------------------------------- 5. data diagnosis + hypothesis
s = section_slide("01", "Problem Formulation & Research Hypothesis", "학습 데이터 진단과 가설")
pic(s, "analysis/fig_demo_quality.png", 1.2, 2.9, w=10.3)
caption(s, 1.2, 7.15, 10.3, "파지 품질 기준: 닫기 명령 1회, 첫 그립 뒤 2초(40 step) 안에 2 cm 이상 상승, 닫은 상태에서 gripper_pos < −0.75인 step 5개 이하. gripper_pos: 열림 −0.99, 잡았을 때 −0.2 ~ −0.4.")
box(s, 12.3, 2.9, 6.5, 6.9, "생성 시범의 파지 품질", [
    "501개 중 162개 (32 %)가 파지 품질 기준 미충족",
    (1, "닫기 명령 2회 이상 19 %, 첫 그립 뒤 2초 내 미상승 30 %, 손가락 밀림 5 %"),
    "사람 시범 20개 중 6개에 재파지. Mimic이 그 구간을 그대로 복제",
    "가설: 파지 품질이 낮은 시범이 그리퍼 여닫기 반복을 가르친다",
    "예상: 품질 높은 시범만 학습하면 전환 횟수와 파지·운반 실패가 줄고 성공률이 오른다",
])

# ---------------------------------------------------------------- 6. design
s = section_slide("02", "Experimental Design", "실험 설계: 파지 품질만 다른 두 데이터셋")
table(s, 1.2, 2.9, 17.6, [
    ["구분", "clean162", "dirty162", "(참고) baseline"],
    ["시범", "기준 충족 339개 중 무작위 162개", "기준 미충족 162개 전부", "501개 전부"],
    ["총 step (평균)", "72,148 (445)", "92,888 (573)", "235,936 (471)"],
    ["학습", "BC-RNN, 2000 epoch × 100 step, batch 100", "동일", "동일"],
    ["seed", "101, 111", "101, 111", "101, 111"],
    ["평가", "seed 42, 100회, horizon 800, 20 env 병렬", "동일", "동일 + 공식 play.py"],
], col_w=[3.2, 5.8, 4.2, 4.4], size=16, head_size=16, row_h=0.62)
box(s, 1.2, 6.9, 17.6, 3.1, "통제와 판정 기준", [
    "바꾼 것: 시범의 파지 품질 하나. 개수, 학습량, 평가 조건은 동일",
    "통제하지 못한 것: 총 step 수 (dirty가 재파지 구간만큼 평균 128 step 김)",
    "판정 기준 (결과 보기 전에 정함): clean이 10 %p 이상 높고 전환 횟수와 파지·운반 실패가 함께 줄면 가설 지지. 성공률만 오르면 다른 원인",
    "지표: 실패 단계, 전환 횟수, 첫 그립 후 상승, 재파지 성공률",
])

# ---------------------------------------------------------------- 7. results (main experiment)
s = section_slide("03", "Performance Evaluation & Analysis", "평가 결과: clean162 vs dirty162")
pic(s, "analysis/fig_experiment.png", 1.2, 2.85, w=10.3)
table(s, 1.2, 6.0, 10.7, [
    RESULT_HEAD,
    ["clean162", "13 / 11", "12.0 ± 1.0 %", "42 %", "16 %", "4 / 24", "11"],
    ["dirty162", "20 / 23", "21.5 ± 1.5 %", "28 %", "26 %", "17 / 43", "15"],
    ["baseline 501", "28 / 27", "27.5 ± 0.5 %", "54 %", "40 %", "12 / 55", "8"],
], col_w=RESULT_COLS, head_size=14)
caption(s, 1.2, 8.7, 10.7, "20 env 평가, seed 42, 조건당 두 seed × 100회 (표준편차는 두 seed 값). " + METRIC_NOTE)
box(s, 12.3, 2.9, 6.5, 6.9, "비교", [
    "성공률: clean 12.0 → dirty 21.5 (−9.5 %p, p = 0.01). 두 seed 모두 dirty가 높음",
    "판정 기준 미충족, 가설 기각",
    "전환 횟수: clean에서도 줄지 않음 (11회 vs 15회, baseline 8회)",
    "첫 그립 후 상승: clean 42 %, dirty 28 %. 지저분한 시범의 낮은 정밀도가 정책에 그대로 옮겨감",
    "재파지 성공률: clean 16 %, dirty 26 %, baseline 40 %",
    "재파지 후 성공: clean 4/24, dirty 17/43",
])

# ---------------------------------------------------------------- 8. mechanism: behaviour after a failed first grasp
s = section_slide("03", "Performance Evaluation & Analysis", "첫 그립 실패 후의 행동: 여닫기 반복과 재파지")
pic(s, "analysis/fig_recovery_examples.png", 1.2, 2.85, w=10.3)
caption(s, 1.2, 9.1, 10.3, "첫 그립이 실패한 rollout 예시 (20 env 평가, seed 101 정책). 왼쪽 clean162: 닫기 43회, 상승 없음. 오른쪽 dirty162: 다시 닫은 뒤 상승, 성공.")
box(s, 12.3, 2.9, 6.5, 6.9, "해석", [
    "두 정책 모두 첫 그립이 실패하는 상태를 겪음 (첫 그립 후 상승 42 % / 28 %)",
    "clean162: 열고 닫기를 반복하며 손가락이 물체에 닿았다 떨어짐. 들어 올리지 못함",
    "dirty162: 열었다가 다시 닫아 들어 올림",
    "차이의 원인: 시범에 '첫 그립 실패 후' 상태가 있는가. dirty 시범의 재파지 구간이 그 상태에서의 행동을 가르침",
    "여닫기 반복은 지저분한 시범의 모방이 아니라, 시범에 없는 상태에서 나오는 행동",
])

# ---------------------------------------------------------------- 9. follow-up (clean339 vs random339)
s = section_slide("03", "Performance Evaluation & Analysis", "후속 실험: 시범 339개에서 다시 확인 (clean339 vs random339)")
pic(s, "analysis/fig_followup.png", 1.2, 2.85, w=10.3)
table(s, 1.2, 6.0, 10.7, [
    RESULT_HEAD,
    ["clean339", "21 / 21", "21.0 ± 0.0 %", "54 %", "24 %", "8 / 42", "11"],
    ["random339", "25 / 27", "26.0 ± 1.0 %", "50 %", "24 %", "5 / 52", "8"],
    ["baseline 501", "28 / 27", "27.5 ± 0.5 %", "54 %", "40 %", "12 / 55", "8"],
], col_w=RESULT_COLS, head_size=14)
caption(s, 1.2, 8.7, 10.7, "20 env 평가, 조건당 두 seed × 100회. random339: 501개 중 무작위 339개 (기준 미충족 98개 포함). 지표 정의는 앞 장과 같음.")
box(s, 12.3, 2.9, 6.5, 6.9, "비교", [
    "구성: clean339 = 기준 충족 339개 전부, random339 = 501개 중 무작위 339개. 학습·평가 조건은 실험 1과 동일",
    "판정 기준 (결과 보기 전에 정함): random ≥ clean이면 품질 선별은 도움이 안 된다고 봄",
    "성공률: clean 21.0 → random 26.0 (−5.0 %p, p = 0.24). 두 seed 모두 random이 높음. 결론 유지",
    "첫 그립 후 상승 54 % vs 50 %, 재파지 성공률 24 % vs 24 %. 실험 1에서 보인 차이는 거의 사라짐",
    "전환 횟수: clean 11회, random 8회. 선별로 줄지 않음",
    "개수 효과: clean 162 → 339개에서 12.0 → 21.0 %. 501개에서 162개를 빼면 clean339 −6.5 %p, random339 −1.5 %p",
])

# ---------------------------------------------------------------- 10. conclusion
s = section_slide("04", "Future Directions", "결론 및 한계")
box(s, 1.2, 2.9, 5.7, 6.9, "결론", [
    "가설 기각: 깨끗한 시범만 배운 정책이 더 못함 (12.0 vs 21.5 %, 21.0 vs 26.0 %)",
    "여닫기 반복은 첫 그립 실패 후, 시범에 없는 상태에서 나옴. 선별로 줄지 않음",
    "재파지 구간은 162개에서 재파지 성공률을 올림 (16 → 26 %). 339개에서는 차이 없음 (24 vs 24 %)",
    "성공률은 선별보다 시범 개수에 달림 (clean 162 → 339개: 12.0 → 21.0 %, 501개: 27.5 %)",
    "재파지·미끄러짐 구간은 걸러낼 대상이 아님",
], size=18)
box(s, 7.2, 2.9, 5.7, 6.9, "한계", [
    "조건별 시범 수 (162, 339)가 baseline (501)보다 적음",
    "차이가 작음: 9.5 %p (p = 0.01), 5.0 %p (p = 0.24). seed 2개",
    "총 step 수 차이 (평균 573 vs 445)",
    "품질·실패 단계 분류가 임계값 규칙에 의존",
    "공식 play.py와 20 env 평가의 차이 (baseline seed 101: 19 % vs 28 %)",
    "생성 1회 (501개), WSL2 CPU 물리",
], size=18)
box(s, 13.1, 2.9, 5.7, 6.9, "향후 과제", [
    "재파지 시범 추가 수집",
    "생성 시 첫 그립 실패 후 회복한 시범 선별",
    "시범 개수 확대 (1,000개)와 선별의 상호작용",
    "회복 시도와 헛된 여닫기를 구분하는 지표",
    "공식 play.py로 전 조건 재평가, seed 추가",
], size=18)

# ---------------------------------------------------------------- 11. end
s = prs.slides.add_slide(BLANK); deco(s)
textbox(s, 1.7, 4.3, 16.6, 2.6, "감사합니다", 96, BOLD, GREEN, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)

# ---------------------------------------------------------------- 12. appendix
s = section_slide("A", "Appendix", "재현 정보")
box(s, 1.2, 2.9, 17.6, 5.9, "제출물과 명령", [
    "제출 체크포인트: checkpoints/bc_rnn_seed101/model_epoch_2000.pth, checkpoints/bc_rnn_seed111/model_epoch_2000.pth (baseline, 501개 전부, epoch 2000)",
    "평가 명령 (play_command.txt, 강의자료 44쪽 형식): ./isaaclab.sh -p scripts/imitation_learning/robomimic/play.py --task Isaac-Place-Toy2Box-Agibot-Right-Arm-RmpFlow-v0 --checkpoint ./checkpoints/bc_rnn_seed101/model_epoch_2000.pth --num_rollouts 100 --horizon 800 --seed 42 --headless",
    "학습: train_bc_nokit.py (공식 train.py와 같은 코드, Isaac Sim 없이 실행) --dataset datasets/<조건>.hdf5 --seed 101 / 111. bc_rnn_low_dim.json, 2000 epoch × 100 step, batch 100",
    "데이터: toy2box_all.hdf5 (키보드 20개) → annotate_demos.py (16개) → generate_parallel.sh (Mimic 501개, 3 프로세스 × 34 env) → analysis/grasp_quality.py → subset_hdf5.py",
    "평가·진단: eval_multienv.py (20 env), diagnose_failures.py (실패 단계), analysis/regrasp_analysis.py (첫 그립·재파지), analysis/collect_results.py (집계·그림)",
    "저장소: 과목 저장소에 위 스크립트, analysis/, checkpoints/, play_command.txt, README, 분석 노트 추가. 데이터셋·로그 제외",
], size=16, head_size=20)

cp = prs.core_properties
cp.title = "로보틱스시뮬레이션 실습 과제 2 (9조)"; cp.subject = "Toy2Box 모방학습: 파지 품질이 낮은 시범을 걸러내면 나아지는가"
cp.author = cp.last_modified_by = "9조"; cp.created = cp.modified = datetime.datetime.now().replace(microsecond=0); cp.revision = 1; cp.comments = ""  # no generator note in the file properties
prs.save(OUT); print("wrote", OUT, len(prs.slides), "slides")
