import os
import json
import csv
import io
import sqlite3
from datetime import datetime
from flask import (Flask, render_template, request, redirect,
                   url_for, session, jsonify, Response)

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'pet-survey-secret-2569')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'admin1234')
DATABASE = os.path.join(os.path.dirname(__file__), 'survey.db')

# ──────────────────────────────────────────────────────────────────────────────
# Survey content (from GRI Standards 2021 / materiality-survey-plastics-gri)
# ──────────────────────────────────────────────────────────────────────────────
SURVEY_DATA = {
    'investor': {
        'name': 'ผู้ถือหุ้น / นักลงทุน', 'icon': '💼', 'color': '#1565C0',
        'desc': 'ประเมินประเด็น ESG ที่มีนัยสำคัญต่อผลการดำเนินงานและมูลค่าระยะยาวของบริษัท',
        'section_a': 'ความสำคัญต่อผลการดำเนินงานและมูลค่าองค์กร',
        'instruction': 'โปรดประเมินว่าประเด็นต่อไปนี้มีความสำคัญต่อ "ความสามารถในการสร้างมูลค่าระยะยาว" ของบริษัทผลิตพลาสติกมากน้อยเพียงใด',
        'topics': [
            {'id': 'ghg',          'name': 'การปล่อยก๊าซเรือนกระจก (Scope 1, 2, 3) และแผน Net Zero',          'gri': '305'},
            {'id': 'energy',       'name': 'ประสิทธิภาพพลังงานและการเปลี่ยนสู่พลังงานหมุนเวียน',              'gri': '302'},
            {'id': 'circular',     'name': 'การจัดการของเสียพลาสติกและนโยบาย Circular Economy',               'gri': '306'},
            {'id': 'pollution',    'name': 'มลพิษ สารเคมีอันตราย และการปฏิบัติตามกฎหมายสิ่งแวดล้อม',         'gri': '307'},
            {'id': 'water',        'name': 'การใช้น้ำและการบำบัดน้ำเสียในกระบวนการผลิต',                      'gri': '303'},
            {'id': 'safety',       'name': 'สุขภาพและความปลอดภัยของพนักงาน (โรงงาน/คลังสินค้า)',              'gri': '403'},
            {'id': 'talent',       'name': 'การพัฒนาทักษะและรักษาบุคลากรที่มีความสามารถ',                     'gri': '404'},
            {'id': 'supply_chain', 'name': 'ห่วงโซ่อุปทานที่รับผิดชอบ (แรงงาน, สิ่งแวดล้อม)',               'gri': '308'},
            {'id': 'governance',   'name': 'โครงสร้างการกำกับดูแลและความโปร่งใส',                             'gri': '2-9'},
            {'id': 'anticorrupt',  'name': 'การต่อต้านคอร์รัปชันและจรรยาบรรณธุรกิจ',                         'gri': '205'},
            {'id': 'epr',          'name': 'Extended Producer Responsibility (EPR) และกฎระเบียบพลาสติก',      'gri': '307'},
            {'id': 'climate_risk', 'name': 'ความเสี่ยงและโอกาสจากการเปลี่ยนแปลงสภาพภูมิอากาศ',              'gri': '201'},
        ],
        'open_qs': [
            {'id': 'q1', 'text': 'ประเด็น ESG ใดที่ท่านคิดว่ามีความเสี่ยงสูงสุดต่อบริษัทในอีก 3–5 ปีข้างหน้า?'},
            {'id': 'q2', 'text': 'ข้อมูล ESG ใดที่มีผลต่อการตัดสินใจลงทุนของท่านมากที่สุด? (เช่น ตัวเลข GHG, นโยบาย EPR)'},
            {'id': 'q3', 'text': 'บริษัทควรรายงานหรือดำเนินการด้านใดเพิ่มเติมที่ท่านยังไม่เห็นในรายการข้างต้น?'},
        ],
    },
    'customer': {
        'name': 'ลูกค้า / ผู้บริโภค', 'icon': '🛒', 'color': '#00838F',
        'desc': 'แสดงความเห็นเกี่ยวกับผลิตภัณฑ์พลาสติกและบรรจุภัณฑ์',
        'section_a': 'สิ่งที่คุณให้ความสำคัญในการเลือกซื้อผลิตภัณฑ์/บรรจุภัณฑ์',
        'instruction': 'ประเด็นต่อไปนี้มีความสำคัญต่อการตัดสินใจซื้อสินค้าของคุณมากน้อยแค่ไหน?',
        'topics': [
            {'id': 'prod_safety',   'name': 'ความปลอดภัยของผลิตภัณฑ์พลาสติก (ปราศจาก BPA, Phthalates)',        'gri': '416'},
            {'id': 'recyclable',    'name': 'บรรจุภัณฑ์ที่รีไซเคิลได้หรือใช้วัสดุรีไซเคิล (Recycled Content)',  'gri': '306'},
            {'id': 'ingredient',    'name': 'ข้อมูลส่วนประกอบและแหล่งที่มาของวัตถุดิบบนผลิตภัณฑ์',              'gri': '416'},
            {'id': 'carbon_cut',    'name': 'การลดการปล่อยคาร์บอนในกระบวนการผลิต',                              'gri': '305'},
            {'id': 'takeback',      'name': 'นโยบายรับคืนและรีไซเคิลบรรจุภัณฑ์หลังใช้งาน (EPR)',               'gri': '306'},
            {'id': 'renewable',     'name': 'การใช้พลังงานหมุนเวียนในโรงงาน',                                   'gri': '302'},
            {'id': 'bioplastic',    'name': 'ผลิตภัณฑ์จากพลาสติก Bio-based หรือ Biodegradable',                'gri': '306'},
            {'id': 'community',     'name': 'การสนับสนุนชุมชนท้องถิ่นรอบโรงงาน',                               'gri': '413'},
            {'id': 'env_report',    'name': 'ความโปร่งใสในการรายงานข้อมูลสิ่งแวดล้อม',                          'gri': '2-4'},
        ],
        'open_qs': [
            {'id': 'q1', 'text': 'ผลิตภัณฑ์หรือบรรจุภัณฑ์พลาสติกที่คุณใช้อยู่มีด้านใดที่ควรปรับปรุงมากที่สุด?'},
            {'id': 'q2', 'text': 'คุณมีความกังวลด้านสิ่งแวดล้อมหรือสุขภาพจากผลิตภัณฑ์พลาสติกของบริษัทหรือไม่? กรุณาระบุ'},
        ],
    },
    'employee': {
        'name': 'พนักงาน', 'icon': '👷', 'color': '#558B2F',
        'desc': 'แสดงความเห็นเพื่อพัฒนาสภาพแวดล้อมการทำงานและนโยบายองค์กร (ข้อมูลทั้งหมดเป็นความลับ)',
        'section_a': 'ความสำคัญและความพึงพอใจ',
        'instruction': 'ประเด็นต่อไปนี้สำคัญต่อคุณในฐานะพนักงานมากน้อยแค่ไหน?',
        'topics': [
            {'id': 'ohs',        'name': 'ความปลอดภัยและสุขอนามัยในโรงงาน (สารเคมี, เครื่องจักร, ความร้อน)',   'gri': '403'},
            {'id': 'ppe',        'name': 'อุปกรณ์ป้องกันส่วนบุคคล (PPE) และการฝึกอบรมความปลอดภัย',            'gri': '403'},
            {'id': 'wellbeing',  'name': 'สุขภาพและสวัสดิภาพพนักงาน (Well-being) ทั้งกายและใจ',               'gri': '403'},
            {'id': 'fair_pay',   'name': 'ค่าตอบแทนที่ยุติธรรมและเท่าเทียม (ไม่แบ่งแยกเพศ/อายุ)',            'gri': '405'},
            {'id': 'develop',    'name': 'โอกาสพัฒนาทักษะ (Upskill/Reskill) และเติบโตในสายงาน',              'gri': '404'},
            {'id': 'worklife',   'name': 'สมดุลชีวิตการทำงาน (Work-life Balance)',                             'gri': '401'},
            {'id': 'diversity',  'name': 'ความหลากหลายและการไม่เลือกปฏิบัติในที่ทำงาน',                       'gri': '406'},
            {'id': 'culture',    'name': 'วัฒนธรรมองค์กรที่เปิดเผย สามารถแสดงความเห็นได้อย่างอิสระ',         'gri': '2-4'},
            {'id': 'env_policy', 'name': 'นโยบายสิ่งแวดล้อมของโรงงาน (การลดของเสีย, ประหยัดพลังงาน)',        'gri': '302'},
            {'id': 'csr',        'name': 'การมีส่วนร่วมในกิจกรรมชุมชนและ CSR',                                'gri': '413'},
        ],
        'open_qs': [
            {'id': 'q1', 'text': 'ถ้าบริษัทเปลี่ยนได้สิ่งเดียวเพื่อทำให้สภาพแวดล้อมการทำงานดีขึ้น คุณอยากให้เปลี่ยนอะไร?'},
            {'id': 'q2', 'text': 'มีประเด็นด้านความปลอดภัยหรือสุขภาพที่คุณยังกังวลอยู่ แต่ยังไม่ได้รับการแก้ไข? กรุณาระบุ'},
            {'id': 'q3', 'text': 'มีประเด็นอื่นที่บริษัทควรให้ความสำคัญที่ไม่อยู่ในรายการข้างต้น?'},
        ],
    },
    'community': {
        'name': 'ชุมชนท้องถิ่น / NGO', 'icon': '🌳', 'color': '#2E7D32',
        'desc': 'แสดงมุมมองในฐานะตัวแทนชุมชนหรือภาคประชาสังคม',
        'section_a': 'ระดับผลกระทบที่ท่านพบ',
        'instruction': 'กิจกรรมของโรงงานพลาสติกมีผลกระทบต่อชุมชน/สิ่งแวดล้อมมากน้อยแค่ไหน? (ระบุ + บวก หรือ − ลบ ในช่องความเห็น)',
        'topics': [
            {'id': 'air',         'name': 'มลพิษทางอากาศจากกระบวนการผลิตพลาสติก (กลิ่น, สาร VOC)',            'gri': '305'},
            {'id': 'water_poll',  'name': 'มลพิษทางน้ำ (น้ำเสียจากโรงงาน, สีย้อม, สารเคมี)',                 'gri': '303'},
            {'id': 'plastic_w',   'name': 'ขยะพลาสติกและไมโครพลาสติกที่ส่งผลต่อสิ่งแวดล้อมชุมชน',           'gri': '306'},
            {'id': 'noise',       'name': 'เสียงดังและการสั่นสะเทือนจากโรงงาน',                               'gri': '413'},
            {'id': 'ecosystem',   'name': 'ผลกระทบต่อแหล่งน้ำและระบบนิเวศในพื้นที่',                         'gri': '304'},
            {'id': 'local_jobs',  'name': 'การจ้างงานคนในชุมชนท้องถิ่น',                                      'gri': '413'},
            {'id': 'comm_dev',    'name': 'การสนับสนุนการศึกษา สาธารณสุข หรือโครงสร้างพื้นฐานชุมชน',        'gri': '413'},
            {'id': 'emergency',   'name': 'ความโปร่งใสในการแจ้งเตือนเหตุฉุกเฉิน (การรั่วไหลของสารเคมี ฯลฯ)', 'gri': '413'},
            {'id': 'grievance',   'name': 'กระบวนการรับฟังและตอบสนองข้อร้องเรียนของชุมชน',                    'gri': '413'},
        ],
        'open_qs': [
            {'id': 'q1', 'text': 'บริษัทควรดำเนินการอย่างไรเพื่อลดผลกระทบต่อสิ่งแวดล้อมและชุมชนที่เห็นเป็นเรื่องเร่งด่วนที่สุด?'},
            {'id': 'q2', 'text': 'ช่องทางใดที่ชุมชน/NGO อยากมีส่วนร่วมกับบริษัทมากขึ้น? (เช่น การประชุม, เยี่ยมโรงงาน, รายงานสาธารณะ)'},
            {'id': 'q3', 'text': 'มีเหตุการณ์หรือข้อกังวลด้านสิ่งแวดล้อม/สังคมที่ต้องการแจ้งให้บริษัทรับทราบโดยเฉพาะ?'},
        ],
    },
    'supplier': {
        'name': 'ซัพพลายเออร์', 'icon': '🏭', 'color': '#6A1B9A',
        'desc': 'แสดงมุมมองในฐานะพันธมิตรทางธุรกิจในห่วงโซ่อุปทาน',
        'section_a': 'ความสำคัญของมาตรฐาน ESG ในห่วงโซ่อุปทาน',
        'instruction': 'ประเด็นต่อไปนี้มีความสำคัญต่อการดำเนินธุรกิจร่วมกันมากน้อยแค่ไหน?',
        'topics': [
            {'id': 'labor_std',     'name': 'มาตรฐานแรงงาน (ค่าแรงขั้นต่ำ, ชั่วโมงทำงาน, วันหยุด)',                'gri': '401'},
            {'id': 'no_child',      'name': 'การห้ามใช้แรงงานเด็กและแรงงานบังคับในห่วงโซ่อุปทาน',                   'gri': '408'},
            {'id': 'sup_safety',    'name': 'ความปลอดภัยในสถานที่ผลิตของซัพพลายเออร์',                               'gri': '403'},
            {'id': 'env_mgmt',      'name': 'การจัดการสิ่งแวดล้อมในกระบวนการผลิตวัตถุดิบ',                           'gri': '308'},
            {'id': 'ghg_scope3',    'name': 'การเปิดเผยข้อมูลการปล่อย GHG (Scope 3 ของบริษัท)',                      'gri': '305'},
            {'id': 'haz_chem',      'name': 'การใช้สารเคมีอันตรายในกระบวนการผลิตวัตถุดิบพลาสติก',                    'gri': '308'},
            {'id': 'cert',          'name': 'การรับรองมาตรฐาน (ISO 14001, ISO 45001, SA8000 ฯลฯ)',                  'gri': '308'},
            {'id': 'anti_bribe',    'name': 'นโยบายต่อต้านคอร์รัปชันและการให้สินบน',                                 'gri': '205'},
            {'id': 'esg_audit',     'name': 'ความโปร่งใสในการรายงาน ESG และการตรวจสอบ (Audit)',                      'gri': '2-4'},
            {'id': 'carbon_plan',   'name': 'แผนลด Carbon Footprint ของซัพพลายเออร์',                                'gri': '305'},
        ],
        'open_qs': [
            {'id': 'q1', 'text': 'อุปสรรคหลักในการปฏิบัติตามมาตรฐาน ESG ที่บริษัทกำหนดคืออะไร?'},
            {'id': 'q2', 'text': 'บริษัทสามารถสนับสนุนท่านด้านความยั่งยืนได้อย่างไร? (เช่น การอบรม, ทรัพยากร, เงื่อนไขการชำระ)'},
            {'id': 'q3', 'text': 'มีมาตรฐานหรือข้อกำหนดด้าน ESG ใดที่ต้องการให้บริษัทชี้แจงหรือปรับปรุง?'},
        ],
    },
}

# ──────────────────────────────────────────────────────────────────────────────
# Database
# ──────────────────────────────────────────────────────────────────────────────
def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS responses (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            stakeholder_type TEXT    NOT NULL,
            respondent_name  TEXT    DEFAULT '',
            respondent_org   TEXT    DEFAULT '',
            submitted_at     TEXT    DEFAULT (datetime('now','localtime')),
            ratings          TEXT    NOT NULL,
            comments         TEXT    DEFAULT '{}',
            open_answers     TEXT    DEFAULT '{}'
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# ──────────────────────────────────────────────────────────────────────────────
# Routes – public
# ──────────────────────────────────────────────────────────────────────────────
@app.route('/')
def index():
    return render_template('index.html', survey=SURVEY_DATA)

@app.route('/survey/<stype>')
def survey(stype):
    if stype not in SURVEY_DATA:
        return redirect(url_for('index'))
    return render_template('survey.html', stype=stype, data=SURVEY_DATA[stype])

@app.route('/submit', methods=['POST'])
def submit():
    stype = request.form.get('stype', '')
    if stype not in SURVEY_DATA:
        return redirect(url_for('index'))

    name = request.form.get('respondent_name', '').strip()
    org  = request.form.get('respondent_org',  '').strip()

    ratings  = {}
    comments = {}
    for t in SURVEY_DATA[stype]['topics']:
        r = request.form.get(f'r_{t["id"]}')
        c = request.form.get(f'c_{t["id"]}', '').strip()
        if r:
            ratings[t['id']] = int(r)
        if c:
            comments[t['id']] = c

    open_ans = {}
    for q in SURVEY_DATA[stype]['open_qs']:
        a = request.form.get(f'open_{q["id"]}', '').strip()
        if a:
            open_ans[q['id']] = a

    conn = get_db()
    conn.execute(
        'INSERT INTO responses (stakeholder_type,respondent_name,respondent_org,ratings,comments,open_answers) VALUES (?,?,?,?,?,?)',
        (stype, name, org,
         json.dumps(ratings,  ensure_ascii=False),
         json.dumps(comments, ensure_ascii=False),
         json.dumps(open_ans, ensure_ascii=False))
    )
    conn.commit()
    conn.close()
    return redirect(url_for('thanks'))

@app.route('/thanks')
def thanks():
    return render_template('thanks.html')

# ──────────────────────────────────────────────────────────────────────────────
# Routes – admin
# ──────────────────────────────────────────────────────────────────────────────
@app.route('/admin')
def admin():
    if not session.get('admin_ok'):
        return render_template('admin_login.html', error=False)
    return render_template('admin.html', survey=SURVEY_DATA)

@app.route('/admin/login', methods=['POST'])
def admin_login():
    if request.form.get('password') == ADMIN_PASSWORD:
        session['admin_ok'] = True
        return redirect(url_for('admin'))
    return render_template('admin_login.html', error=True)

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_ok', None)
    return redirect(url_for('index'))

# ──────────────────────────────────────────────────────────────────────────────
# API – statistics (JSON)
# ──────────────────────────────────────────────────────────────────────────────
@app.route('/api/stats')
def api_stats():
    if not session.get('admin_ok'):
        return jsonify({'error': 'Unauthorized'}), 401

    conn = get_db()
    rows = conn.execute(
        'SELECT stakeholder_type,ratings,open_answers,submitted_at FROM responses ORDER BY submitted_at DESC'
    ).fetchall()
    conn.close()

    total = len(rows)
    by_type = {}
    topic_sums = {}   # stype -> topic_id -> [scores]

    for row in rows:
        st = row['stakeholder_type']
        by_type[st] = by_type.get(st, 0) + 1
        if st not in topic_sums:
            topic_sums[st] = {}
        try:
            for tid, score in json.loads(row['ratings']).items():
                topic_sums[st].setdefault(tid, []).append(score)
        except Exception:
            pass

    # Build per-type averages
    averages = {}
    for st, sdata in SURVEY_DATA.items():
        averages[st] = []
        for t in sdata['topics']:
            scores = topic_sums.get(st, {}).get(t['id'], [])
            averages[st].append({
                'id':   t['id'],
                'name': t['name'],
                'gri':  t['gri'],
                'avg':  round(sum(scores)/len(scores), 2) if scores else None,
                'n':    len(scores),
            })

    # Global top topics (across all types)
    global_pool = {}
    for st_avgs in averages.values():
        for item in st_avgs:
            if item['avg'] is not None:
                global_pool.setdefault(item['name'], []).append(item['avg'])
    global_rank = sorted(
        [{'name': k, 'avg': round(sum(v)/len(v), 2), 'n': len(v)} for k, v in global_pool.items()],
        key=lambda x: -x['avg']
    )

    # Recent 15 rows
    recent = [{'stype': r['stakeholder_type'],
               'sname': SURVEY_DATA.get(r['stakeholder_type'], {}).get('name', ''),
               'at':    r['submitted_at']} for r in rows[:15]]

    return jsonify({
        'total': total,
        'by_type': by_type,
        'averages': averages,
        'global_rank': global_rank,
        'recent': recent,
        'survey': {k: {'name': v['name'], 'icon': v['icon'], 'color': v['color']}
                   for k, v in SURVEY_DATA.items()},
    })

# ──────────────────────────────────────────────────────────────────────────────
# API – individual responses
# ──────────────────────────────────────────────────────────────────────────────
@app.route('/api/responses')
def api_responses():
    if not session.get('admin_ok'):
        return jsonify({'error': 'Unauthorized'}), 401
    stype = request.args.get('stype', '')
    conn  = get_db()
    if stype and stype in SURVEY_DATA:
        rows = conn.execute(
            'SELECT * FROM responses WHERE stakeholder_type=? ORDER BY submitted_at DESC', (stype,)
        ).fetchall()
    else:
        rows = conn.execute('SELECT * FROM responses ORDER BY submitted_at DESC').fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

# ──────────────────────────────────────────────────────────────────────────────
# Export CSV
# ──────────────────────────────────────────────────────────────────────────────
@app.route('/export/csv')
def export_csv():
    if not session.get('admin_ok'):
        return redirect(url_for('admin'))
    conn  = get_db()
    rows  = conn.execute('SELECT * FROM responses ORDER BY submitted_at DESC').fetchall()
    conn.close()

    buf = io.StringIO()
    w   = csv.writer(buf)
    w.writerow(['ID', 'ประเภทผู้มีส่วนได้เสีย', 'ชื่อ', 'องค์กร', 'วันเวลา',
                'คะแนนรายประเด็น (JSON)', 'ความเห็นเพิ่มเติม (JSON)', 'คำตอบเปิด (JSON)'])
    for r in rows:
        w.writerow([r['id'],
                    SURVEY_DATA.get(r['stakeholder_type'], {}).get('name', r['stakeholder_type']),
                    r['respondent_name'], r['respondent_org'], r['submitted_at'],
                    r['ratings'], r['comments'], r['open_answers']])
    buf.seek(0)
    return Response(
        '﻿' + buf.getvalue(),
        mimetype='text/csv; charset=utf-8',
        headers={'Content-Disposition': f'attachment; filename=materiality_{datetime.now().strftime("%Y%m%d")}.csv'}
    )

# ──────────────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
