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
    r = p.add_run(); r.text = text; set_font(r, size, font, color, bold)
    if bullet is not None: set_bullet(p, bullet)
    return p

def textbox(slide, x, y, w, h, text, size, font=REG, color=INK, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP):
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h)); tf = tb.text_frame; tf.word_wrap = True
    tf.margin_left = tf.margin_right = Inches(0.05); tf.margin_top = tf.margin_bottom = Inches(0.02); tf.vertical_anchor = anchor
    para(tf, text, size, font, color, first=True, align=align, space_after=0)
    return tb

def box(slide, x, y, w, h, heading, items, size=17, head_size=20, fill=LIGHT):
    """Rounded light-green box with a green heading and bulleted items. items: str | (level, str)"""
    shp = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
    shp.adjustments[0] = 0.078; shp.fill.solid(); shp.fill.fore_color.rgb = fill; shp.line.fill.background(); shp.shadow.inherit = False
    tf = shp.text_frame; tf.word_wrap = True; tf.vertical_anchor = MSO_ANCHOR.TOP
    tf.margin_left = tf.margin_right = Inches(0.3); tf.margin_top = Inches(0.25); tf.margin_bottom = Inches(0.2)
    para(tf, heading, head_size, BOLD, GREEN, first=True, space_after=6)
    for it in items:
        lvl, txt = it if isinstance(it, tuple) else (0, it)
        para(tf, txt, size - (1 if lvl else 0), REG, INK, bullet=lvl, space_after=4)
    return shp

def table(slide, x, y, w, rows, col_w=None, size=15, head_size=16, row_h=0.5, first_col_bold=True):
    nr, nc = len(rows), len(rows[0])
    shp = slide.shapes.add_table(nr, nc, Inches(x), Inches(y), Inches(w), Inches(row_h * nr)); tbl = shp.table
    tblPr = tbl._tbl.tblPr; tblPr.set("bandRow", "1"); tblPr.set("firstRow", "1")
    st = tblPr.find(qn("a:tableStyleId"))
    if st is None: st = etree.SubElement(tblPr, qn("a:tableStyleId"))
    st.text = "{5C22544A-7EE6-4342-B048-85BDC9FD1C3A}"
    if col_w:
        for i, cw in enumerate(col_w): tbl.columns[i].width = Inches(cw)
    for i in range(nr): tbl.rows[i].height = Inches(row_h)
    for i, row in enumerate(rows):
        for j, val in enumerate(row):
            c = tbl.cell(i, j); c.text = ""; tf = c.text_frame; tf.word_wrap = True; c.vertical_anchor = MSO_ANCHOR.MIDDLE
            c.margin_left = c.margin_right = Inches(0.1); c.margin_top = c.margin_bottom = Inches(0.04)
            p = tf.paragraphs[0]; p.alignment = PP_ALIGN.LEFT if j == 0 else PP_ALIGN.CENTER; p.line_spacing = 1.05
            r = p.add_run(); r.text = str(val)
            if i == 0: set_font(r, head_size, BOLD, RGBColor(0xFF, 0xFF, 0xFF), True); c.fill.solid(); c.fill.fore_color.rgb = GREEN
            else:
                set_font(r, size, BOLD if (j == 0 and first_col_bold) else REG, INK, j == 0 and first_col_bold)
                c.fill.solid(); c.fill.fore_color.rgb = RGBColor(0xFF, 0xFF, 0xFF) if i % 2 else RGBColor(0xF3, 0xF6, 0xF5)
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
    textbox(slide, x, y, w, 0.5, text, 13, REG, CAPTION)

# ---------------------------------------------------------------- 1. title
s = prs.slides.add_slide(BLANK); deco(s)
textbox(s, 1.9, 2.4, 8.0, 1.0, "2026년 2학기", 48, BOLD, GREEN)
textbox(s, 1.9, 3.1, 12.0, 1.4, "로보틱스시뮬레이션", 73, BOLD, GREEN)
bar = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(1.9), Inches(4.75), Inches(0.08), Inches(1.15)); bar.fill.solid(); bar.fill.fore_color.rgb = GREEN; bar.line.fill.background()
textbox(s, 2.1, 4.7, 9.0, 0.6, "실습 과제 2", 30, REG, GREEN)
textbox(s, 2.1, 5.3, 16.5, 0.6, "Agibot Toy2Box 모방학습: 생성 시범의 파지 품질이 정책의 그리퍼 동작에 미치는 영향", 24, REG, GREEN)
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
caption(s, 1.2, 8.95, 10.3, "실패 단계는 rollout 기록에서 손–장난감 최소 거리(8 cm), 장난감 상승(5 cm), 상자까지 거리(15 cm) 기준으로 자동 분류. 20 env 병렬 평가, 두 seed 각 100회.")
box(s, 12.3, 2.9, 6.5, 6.9, "Baseline 구성", [
    "데이터: 키보드 시범 20개(평균 426 step) → 자동 주석 16개 → Mimic 생성 501개(평균 471 step, 생성 시도 대비 성공 14 %)",
    "학습: BC-RNN(low-dim 관측), 2000 epoch × 100 step, batch 100, epoch 2000 체크포인트, 학습 seed 101·111",
    "평가: seed 42, 100회, horizon 800. 공식 play.py(1 env)와 동일 규칙의 20 env 병렬 평가를 병행",
    "성공률: 공식 play.py 19 % / 27 %(평균 23.0 ± 4.0), 20 env 평가 28 % / 27 %(27.5 ± 0.5)",
    "실패 단계(200 rollout): 접근 28 %, 파지 30 %, 운반 34 %, 배치 8 %. 파지·운반 실패가 전체 실패의 64 %",
], size=16, head_size=20)

# ---------------------------------------------------------------- 4. diagnosis: gripper chattering
s = section_slide("01", "Problem Formulation & Research Hypothesis", "실패 rollout의 공통점: 그리퍼 명령의 반복 전환")
pic(s, "analysis/fig_grip_switches.png", 1.2, 3.25, w=5.0)
pic(s, "analysis/fig_rollout_examples.png", 6.35, 2.9, w=5.75)
caption(s, 1.2, 6.85, 10.9, "왼쪽: rollout당 그리퍼 명령 부호 전환 횟수(두 seed 합산 200회). 오른쪽: 성공 rollout과 운반 실패 rollout의 그리퍼 명령·gripper_pos 관측·장난감 높이.")
box(s, 12.3, 2.9, 6.5, 6.9, "관찰", [
    "성공 rollout: 닫기 1회·열기 1회(명령 부호 전환 중앙값 2회)",
    "파지 실패: 전환 중앙값 8회, 운반 실패: 6회. 파지·운반 실패의 74 %가 4회 이상",
    "전환은 장난감이 들려 있지 않은 구간(파지 시도 중, 낙하 후)에 집중. 운반 중 열기 명령으로 놓는 경우는 드묾",
    "접근 실패(실패의 28 %)는 전환이 적은 별개 유형. 정지 상태의 rollout은 0건",
    "연구 질문: 그리퍼 명령의 반복 전환이 학습 데이터의 어떤 특성에서 비롯되는가",
], size=16, head_size=20)

# ---------------------------------------------------------------- 5. data diagnosis + hypothesis
s = section_slide("01", "Problem Formulation & Research Hypothesis", "학습 데이터 진단과 가설")
pic(s, "analysis/fig_demo_quality.png", 1.2, 2.9, w=10.3)
caption(s, 1.2, 7.15, 10.3, "파지 품질 기준: 닫기 명령 1회, 첫 닫기 후 40 step(2초) 내 장난감 상승 2 cm 이상, 닫힌 상태에서 gripper_pos < −0.75인 step 5개 이하. gripper_pos 관측: 열림 −0.99, 장난감 파지 시 −0.2 ~ −0.4.")
box(s, 12.3, 2.9, 6.5, 6.9, "생성 시범의 파지 품질", [
    "501개 중 162개(32 %)가 다음 중 하나 이상에 해당: 닫기 명령 2회 이상 19 %, 첫 닫기 후 2초 내 미상승 30 %, 닫힌 상태에서 손가락 밀림 5 %",
    "사람 시범 20개 중 6개에 재파지, 35 %가 첫 닫기 후 2초 내 미상승. Mimic은 해당 구간을 그대로 복제",
    "가설: 파지 품질이 낮은 시범이 정책의 그리퍼 반복 전환을 유발한다",
    "예상: 파지 품질이 높은 시범만으로 학습하면 파지·운반 실패와 rollout당 전환 횟수가 감소하고 성공률이 상승한다",
], size=16, head_size=20)

# ---------------------------------------------------------------- 6. design
s = section_slide("02", "Experimental Design", "실험 설계: 파지 품질만 다른 두 데이터셋")
table(s, 1.2, 2.9, 17.6, [
    ["구분", "clean162", "dirty162", "(참고) baseline"],
    ["시범 구성", "파지 품질 기준 충족 339개 중 무작위 162개", "기준 미충족 162개 전부", "생성 시범 501개 전부"],
    ["시범 개수 / 총 step(평균)", "162 / 72,148 (445)", "162 / 92,888 (573)", "501 / 235,936 (471)"],
    ["학습 설정", "BC-RNN, 2000 epoch × 100 step, batch 100, epoch 2000 체크포인트", "동일", "동일"],
    ["학습 seed", "101, 111", "101, 111", "101, 111"],
    ["평가", "seed 42, 100회, horizon 800 (20 env 병렬, 공식 play.py와 동일 규칙)", "동일", "동일 + 공식 play.py"],
], col_w=[3.6, 5.6, 4.0, 4.4], size=15, head_size=17, row_h=0.62)
box(s, 1.2, 6.9, 17.6, 3.1, "통제 요인과 판정 기준", [
    "변경 요인은 시범의 파지 품질 하나. 시범 개수, 학습량, batch, 체크포인트 규칙, 평가 조건은 동일. 통제되지 않은 요인: 총 step 수(dirty 시범이 재파지 구간만큼 평균 128 step 더 긺)",
    "판정 기준(결과 확인 전 기록): clean162의 두 seed 평균 성공률이 dirty162보다 10 %p 이상 높고, 파지·운반 실패 비율과 rollout당 그리퍼 전환 횟수가 함께 감소하면 가설 지지. 성공률만 상승하고 전환 횟수가 감소하지 않으면 다른 요인으로 판단",
    "분석 지표: 실패 단계 분포, 그리퍼 명령 부호 전환 횟수, 첫 닫기로 장난감을 든 비율, 첫 파지 실패 후 재파지로 상승한 비율(회복)",
], size=15, head_size=19)

# ---------------------------------------------------------------- 7. results (main experiment)
s = section_slide("03", "Performance Evaluation & Analysis", "평가 결과: clean162 vs dirty162")
pic(s, "analysis/fig_experiment.png", 1.2, 2.85, w=10.3)
table(s, 1.2, 6.05, 10.3, [
    ["조건", "seed 101 / 111", "평균 ± 표준편차", "첫 닫기로 상승", "첫 파지 실패 후 회복", "회복 거친 성공", "파지 실패 전환 중앙값"],
    ["clean162", "13 / 11", "12.0 ± 1.0 %", "42 % (67/161)", "16 % (15/94)", "4 / 24", "11"],
    ["dirty162", "20 / 23", "21.5 ± 1.5 %", "28 % (44/159)", "26 % (30/115)", "17 / 43", "15"],
    ["baseline 501", "28 / 27", "27.5 ± 0.5 %", "54 % (87/160)", "40 % (29/73)", "12 / 55", "8"],
], col_w=[1.6, 1.4, 1.7, 1.5, 1.6, 1.2, 1.3], size=13, head_size=13, row_h=0.5)
caption(s, 1.2, 8.15, 10.3, "20 env 평가, seed 42, 조건당 두 seed × 100회. 표준편차는 두 seed 값의 표준편차(ddof=0). 회복·전환 수치는 두 seed 합산 200회 기준. 공식 play.py 성공률은 baseline만 측정(19 % / 27 %).")
box(s, 12.3, 2.9, 6.5, 6.9, "비교", [
    "성공률: clean162 12.0 ± 1.0 %, dirty162 21.5 ± 1.5 %. 차이 −9.5 %p, 두 seed 모두 dirty162가 높음(합산 24/200 vs 43/200, 두 비율 z 검정 p ≈ 0.01). 판정 기준 미충족, 가설 기각",
    "그리퍼 전환: clean162에서도 감소하지 않음(파지 실패 중앙값 11회, dirty162 15회, baseline 8회)",
    "첫 닫기로 장난감을 든 비율: clean162 42 %, dirty162 28 %. 저품질 시범의 낮은 파지 정밀도는 정책에 전이됨",
    "첫 파지 실패 후 재파지로 상승(회복): clean162 16 %, dirty162 26 %, baseline 40 %. 회복을 거친 성공 4/24 vs 17/43",
    "운반 실패: clean162 42건, dirty162 23건(200회 기준)",
], size=15.5, head_size=20)

# ---------------------------------------------------------------- 7b. mechanism: behaviour after a failed first grasp
s = section_slide("03", "Performance Evaluation & Analysis", "첫 파지 실패 후의 행동: 반복 전환과 회복")
pic(s, "analysis/fig_recovery_examples.png", 1.2, 2.85, w=10.3)
caption(s, 1.2, 9.1, 10.3, "첫 닫기가 실패한 뒤의 rollout 예시(20 env 평가, seed 101 정책). 왼쪽: clean162 정책, 닫기 구간 43회, 상승 없음. 오른쪽: dirty162 정책, 다시 닫은 뒤 상승·성공.")
box(s, 12.3, 2.9, 6.5, 6.9, "해석", [
    "두 정책 모두 첫 파지가 실패하는 상태에 도달함(첫 닫기로 상승 42 % / 28 %)",
    "clean162 정책: 이후 열기·닫기를 반복하며 손가락이 물체에 닿았다 떨어지기를 되풀이하고 상승에 이르지 못함. 학습 시범에 첫 파지 실패 후의 상태가 없음",
    "dirty162 정책: 열었다가 다시 닫아 물체를 들어 올림. 학습 시범의 재파지 구간이 같은 상태에서의 행동을 제공",
    "집계(두 seed 합산): 첫 파지 실패 후 회복 16 % vs 26 %, 회복을 거친 성공 4/24 vs 17/43",
    "해석(실험 1): 그리퍼 명령의 반복 전환은 저품질 시범의 모방이 아니라 시범 분포 밖 상태에서 나타나는 행동이며, 재파지 구간은 해당 상태에서의 행동을 제공함. 시범 개수를 늘렸을 때도 유지되는지는 후속 실험에서 확인",
], size=15.5, head_size=20)

# ---------------------------------------------------------------- 8. follow-up (clean339 vs random339)
s = section_slide("03", "Performance Evaluation & Analysis", "후속 실험: 시범 개수 339개에서의 재확인 (clean339 vs random339)")
pic(s, "analysis/fig_followup.png", 1.2, 2.85, w=10.3)
table(s, 1.2, 6.05, 10.3, [
    ["조건", "seed 101 / 111", "평균 ± 표준편차", "첫 닫기로 상승", "첫 파지 실패 후 회복", "회복 거친 성공", "파지 실패 전환 중앙값"],
    ["clean339", "21 / 21", "21.0 ± 0.0 %", "54 % (87/161)", "24 % (18/74)", "8 / 42", "11"],
    ["random339", "25 / 27", "26.0 ± 1.0 %", "50 % (84/168)", "24 % (20/84)", "5 / 52", "8"],
    ["baseline 501", "28 / 27", "27.5 ± 0.5 %", "54 % (87/160)", "40 % (29/73)", "12 / 55", "8"],
], col_w=[1.6, 1.4, 1.7, 1.5, 1.6, 1.2, 1.3], size=13, head_size=13, row_h=0.5)
caption(s, 1.2, 8.15, 10.3, "20 env 평가, seed 42, 조건당 두 seed × 100회. 표준편차는 두 seed 값의 표준편차(ddof=0). 회복·전환 수치는 두 seed 합산 200회 기준. random339는 501개 중 무작위 339개로 파지 품질 기준 미충족 시범 98개(29 %)를 포함.")
box(s, 12.3, 2.9, 6.5, 6.9, "비교", [
    "구성: clean339는 기준 충족 시범 339개 전부, random339는 501개 중 무작위 339개(기준 미충족 98개 포함). 학습·평가 조건은 실험 1과 동일",
    "판정 기준(결과 확인 전 기록): random339가 clean339와 같거나 높으면 품질 기준 선별은 성공률에 도움이 되지 않는다고 판단",
    "성공률: clean339 21.0 ± 0.0 %, random339 26.0 ± 1.0 %. 차이 −5.0 %p, 두 seed 모두 random339가 높음(합산 42/200 vs 52/200, p ≈ 0.24). 실험 1의 결론 유지",
    "첫 닫기로 든 비율 54 % vs 50 %, 첫 파지 실패 후 회복 24 % vs 24 %. 실험 1의 첫 파지 정밀도·회복률 차이는 339개에서 거의 사라짐",
    "그리퍼 전환: 파지 실패 전환 중앙값 clean339 11회, random339 8회. 품질 기준 선별로 전환이 감소하지 않음",
    "시범 개수의 영향: 기준 충족 시범만으로 162 → 339개에서 12.0 → 21.0 %. 501개에서 기준 미충족 162개를 제외하면(clean339) 6.5 %p, 무작위 162개를 제외하면(random339) 1.5 %p 감소",
], size=15, head_size=20)

# ---------------------------------------------------------------- 9. conclusion
s = section_slide("04", "Future Directions", "결론 및 한계")
box(s, 1.2, 2.9, 5.7, 6.9, "결론", [
    "가설(저품질 파지 시범이 반복 전환의 원인) 기각: clean162 12.0 ± 1.0 % vs dirty162 21.5 ± 1.5 %, clean339 21.0 ± 0.0 % vs random339 26.0 ± 1.0 %. 두 실험 모두 두 seed에서 같은 방향",
    "반복 전환은 첫 파지 실패 후 시범 분포 밖의 상태에서 발생하며, 품질 기준 선별로 감소하지 않음(파지 실패 전환 중앙값 clean162 11회, clean339 11회)",
    "재파지 구간의 역할: 162개에서는 회복률 차이(16 % vs 26 %)로 확인되었으나 339개에서는 차이가 없음(24 % vs 24 %). 기준 충족 시범만으로도 회복률이 16 %에서 24 %로 상승하였고 전체 501개에서 40 %로 가장 높음",
    "성공률은 품질 기준 선별보다 시범 개수에 좌우됨(기준 충족 시범 162 → 339개: 12.0 → 21.0 %, 전체 501개: 27.5 %). 재파지·미끄러짐 구간은 제거 대상이 아님",
], size=15, head_size=21)
box(s, 7.2, 2.9, 5.7, 6.9, "한계", [
    "조건별 시범 개수(162, 339)가 baseline(501)보다 적음. 절대 성공률이 아닌 조건 간 차이로 판정",
    "조건 간 차이가 작음: 실험 1의 9.5 %p는 두 비율 z 검정 p ≈ 0.01, 후속 실험의 5.0 %p는 p ≈ 0.24로 단독으로는 유의하지 않음. seed 2개의 방향 일치로 판정",
    "시범 개수는 동일하나 총 step 수는 상이(실험 1: 평균 573 vs 445 step)",
    "파지 품질·실패 단계 분류가 임계값 규칙에 의존",
    "공식 play.py(1 env)와 20 env 평가의 성공률 차이(baseline seed 101: 19 % vs 28 %). 실험 조건은 공식 평가 미실시",
    "WSL2 CPU 물리 환경으로 생성 1회(501개)만 수행. 생성 seed에 따른 변동은 미확인",
], size=15, head_size=21)
box(s, 13.1, 2.9, 5.7, 6.9, "향후 과제", [
    "회복 구간을 의도적으로 포함하는 데이터 구성: 재파지 시범 추가 수집, 생성 시 첫 파지 실패 후 회복한 시범 선별",
    "시범 개수 확대(생성 1,000개 이상)와 품질 선별의 상호작용 확인",
    "첫 파지 정밀도와 회복 능력의 분리 학습(파지 지점 주석 보정 등)",
    "전환 횟수를 회복 시도와 비생산적 전환으로 구분하는 지표",
    "공식 play.py로 전체 조건 재평가, 학습 seed 추가",
], size=15, head_size=21)

# ---------------------------------------------------------------- 10. appendix
s = section_slide("A", "Appendix", "재현 정보")
box(s, 1.2, 2.9, 17.6, 5.9, "제출물과 명령", [
    "제출 체크포인트: checkpoints/bc_rnn_seed101/model_epoch_2000.pth, checkpoints/bc_rnn_seed111/model_epoch_2000.pth (생성 시범 501개 전부로 학습한 baseline, epoch 2000, 학습 seed 101 / 111)",
    "평가 명령(강의자료 44쪽 형식, play_command.txt): ./isaaclab.sh -p scripts/imitation_learning/robomimic/play.py --task Isaac-Place-Toy2Box-Agibot-Right-Arm-RmpFlow-v0 --checkpoint ./checkpoints/bc_rnn_seed101/model_epoch_2000.pth --num_rollouts 100 --horizon 800 --seed 42 --headless (seed 111은 체크포인트 경로만 변경)",
    "학습: 공식 train.py(bc_rnn_low_dim.json, --algo bc)와 같은 학습 코드를 Isaac Sim 없이 실행하는 train_bc_nokit.py --dataset datasets/<조건>.hdf5 --seed 101 / 111. 학습량 2000 epoch × 100 step, batch 100, epoch 2000 체크포인트",
    "데이터: datasets/toy2box_all.hdf5(키보드 20개) → annotate_demos.py(16개) → generate_seeded.py / generate_parallel.sh(Mimic 생성, 3 프로세스 × 34 env, 501개) → analysis/grasp_quality.py(파지 품질 분할) → subset_hdf5.py(clean162 / dirty162 / clean339 / random339)",
    "평가·진단: eval_multienv.py(20 env, seed 42, 100회) + diagnose_failures.py(접근/파지/운반/배치) + analysis/regrasp_analysis.py(첫 파지·회복) + analysis/collect_results.py(집계·그림)",
    "저장소: 과목 저장소(IsaacLab_RS)에 위 스크립트, analysis/, checkpoints/, play_command.txt, 과제2_README.md, 분석_노트.md 추가. 데이터셋·로그는 용량 때문에 제외",
], size=15, head_size=20)

# ---------------------------------------------------------------- 11. end
s = prs.slides.add_slide(BLANK); deco(s)
textbox(s, 1.7, 4.3, 16.6, 2.6, "감사합니다", 96, BOLD, GREEN, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)

cp = prs.core_properties
cp.title = "로보틱스시뮬레이션 실습 과제 2 (9조)"; cp.subject = "Agibot Toy2Box 모방학습: 생성 시범의 파지 품질이 정책의 그리퍼 동작에 미치는 영향"
cp.author = cp.last_modified_by = "9조"; cp.created = cp.modified = datetime.datetime.now().replace(microsecond=0); cp.revision = 1
prs.save(OUT); print("wrote", OUT, len(prs.slides), "slides")
