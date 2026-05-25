import os, json, csv, io, time, sqlite3
from datetime import datetime
from functools import wraps
from flask import (Flask, render_template, request, redirect,
                   url_for, session, jsonify, Response, flash)

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'pet-survey-secret-2569')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'admin1234')
DATABASE = os.path.join(os.path.dirname(__file__), 'survey.db')

# ──────────────────────────────────────────────────────────────────────────────
# Seed data – used only for first-run DB population
# ──────────────────────────────────────────────────────────────────────────────
SEED_DATA = {
    'investor': {
        'name': 'ผู้ถือหุ้น / นักลงทุน', 'icon': '💼', 'color': '#1565C0',
        'desc': 'ประเมินประเด็น ESG ที่มีนัยสำคัญต่อผลการดำเนินงานและมูลค่าระยะยาวของบริษัท',
        'section_a': 'ความสำคัญต่อผลการดำเนินงานและมูลค่าองค์กร',
        'instruction': 'โปรดประเมินว่าประเด็นต่อไปนี้มีความสำคัญต่อ "ความสามารถในการสร้างมูลค่าระยะยาว" ของบริษัทผลิตพลาสติกมากน้อยเพียงใด',
        'topics': [
            {'id':'ghg',         'name':'การปล่อยก๊าซเรือนกระจก (Scope 1, 2, 3) และแผน Net Zero',         'gri':'305'},
            {'id':'energy',      'name':'ประสิทธิภาพพลังงานและการเปลี่ยนสู่พลังงานหมุนเวียน',             'gri':'302'},
            {'id':'circular',    'name':'การจัดการของเสียพลาสติกและนโยบาย Circular Economy',              'gri':'306'},
            {'id':'pollution',   'name':'มลพิษ สารเคมีอันตราย และการปฏิบัติตามกฎหมายสิ่งแวดล้อม',        'gri':'307'},
            {'id':'water',       'name':'การใช้น้ำและการบำบัดน้ำเสียในกระบวนการผลิต',                     'gri':'303'},
            {'id':'safety',      'name':'สุขภาพและความปลอดภัยของพนักงาน (โรงงาน/คลังสินค้า)',             'gri':'403'},
            {'id':'talent',      'name':'การพัฒนาทักษะและรักษาบุคลากรที่มีความสามารถ',                    'gri':'404'},
            {'id':'supply_chain','name':'ห่วงโซ่อุปทานที่รับผิดชอบ (แรงงาน, สิ่งแวดล้อม)',              'gri':'308'},
            {'id':'governance',  'name':'โครงสร้างการกำกับดูแลและความโปร่งใส',                            'gri':'2-9'},
            {'id':'anticorrupt', 'name':'การต่อต้านคอร์รัปชันและจรรยาบรรณธุรกิจ',                        'gri':'205'},
            {'id':'epr',         'name':'Extended Producer Responsibility (EPR) และกฎระเบียบพลาสติก',     'gri':'307'},
            {'id':'climate_risk','name':'ความเสี่ยงและโอกาสจากการเปลี่ยนแปลงสภาพภูมิอากาศ',             'gri':'201'},
        ],
        'open_qs': [
            {'id':'q1','text':'ประเด็น ESG ใดที่ท่านคิดว่ามีความเสี่ยงสูงสุดต่อบริษัทในอีก 3–5 ปีข้างหน้า?'},
            {'id':'q2','text':'ข้อมูล ESG ใดที่มีผลต่อการตัดสินใจลงทุนของท่านมากที่สุด? (เช่น ตัวเลข GHG, นโยบาย EPR)'},
            {'id':'q3','text':'บริษัทควรรายงานหรือดำเนินการด้านใดเพิ่มเติมที่ท่านยังไม่เห็นในรายการข้างต้น?'},
        ],
    },
    'customer': {
        'name': 'ลูกค้า / ผู้บริโภค', 'icon': '🛒', 'color': '#00838F',
        'desc': 'แสดงความเห็นเกี่ยวกับผลิตภัณฑ์พลาสติกและบรรจุภัณฑ์',
        'section_a': 'สิ่งที่คุณให้ความสำคัญในการเลือกซื้อผลิตภัณฑ์/บรรจุภัณฑ์',
        'instruction': 'ประเด็นต่อไปนี้มีความสำคัญต่อการตัดสินใจซื้อสินค้าของคุณมากน้อยแค่ไหน?',
        'topics': [
            {'id':'prod_safety','name':'ความปลอดภัยของผลิตภัณฑ์พลาสติก (ปราศจาก BPA, Phthalates)',       'gri':'416'},
            {'id':'recyclable', 'name':'บรรจุภัณฑ์ที่รีไซเคิลได้หรือใช้วัสดุรีไซเคิล (Recycled Content)','gri':'306'},
            {'id':'ingredient', 'name':'ข้อมูลส่วนประกอบและแหล่งที่มาของวัตถุดิบบนผลิตภัณฑ์',            'gri':'416'},
            {'id':'carbon_cut', 'name':'การลดการปล่อยคาร์บอนในกระบวนการผลิต',                            'gri':'305'},
            {'id':'takeback',   'name':'นโยบายรับคืนและรีไซเคิลบรรจุภัณฑ์หลังใช้งาน (EPR)',              'gri':'306'},
            {'id':'renewable',  'name':'การใช้พลังงานหมุนเวียนในโรงงาน',                                  'gri':'302'},
            {'id':'bioplastic', 'name':'ผลิตภัณฑ์จากพลาสติก Bio-based หรือ Biodegradable',               'gri':'306'},
            {'id':'community',  'name':'การสนับสนุนชุมชนท้องถิ่นรอบโรงงาน',                              'gri':'413'},
            {'id':'env_report', 'name':'ความโปร่งใสในการรายงานข้อมูลสิ่งแวดล้อม',                        'gri':'2-4'},
        ],
        'open_qs': [
            {'id':'q1','text':'ผลิตภัณฑ์หรือบรรจุภัณฑ์พลาสติกที่คุณใช้อยู่มีด้านใดที่ควรปรับปรุงมากที่สุด?'},
            {'id':'q2','text':'คุณมีความกังวลด้านสิ่งแวดล้อมหรือสุขภาพจากผลิตภัณฑ์พลาสติกของบริษัทหรือไม่? กรุณาระบุ'},
        ],
    },
    'employee': {
        'name': 'พนักงาน', 'icon': '👷', 'color': '#558B2F',
        'desc': 'แสดงความเห็นเพื่อพัฒนาสภาพแวดล้อมการทำงานและนโยบายองค์กร (ข้อมูลทั้งหมดเป็นความลับ)',
        'section_a': 'ความสำคัญและความพึงพอใจ',
        'instruction': 'ประเด็นต่อไปนี้สำคัญต่อคุณในฐานะพนักงานมากน้อยแค่ไหน?',
        'topics': [
            {'id':'ohs',       'name':'ความปลอดภัยและสุขอนามัยในโรงงาน (สารเคมี, เครื่องจักร, ความร้อน)',  'gri':'403'},
            {'id':'ppe',       'name':'อุปกรณ์ป้องกันส่วนบุคคล (PPE) และการฝึกอบรมความปลอดภัย',           'gri':'403'},
            {'id':'wellbeing', 'name':'สุขภาพและสวัสดิภาพพนักงาน (Well-being) ทั้งกายและใจ',              'gri':'403'},
            {'id':'fair_pay',  'name':'ค่าตอบแทนที่ยุติธรรมและเท่าเทียม (ไม่แบ่งแยกเพศ/อายุ)',           'gri':'405'},
            {'id':'develop',   'name':'โอกาสพัฒนาทักษะ (Upskill/Reskill) และเติบโตในสายงาน',             'gri':'404'},
            {'id':'worklife',  'name':'สมดุลชีวิตการทำงาน (Work-life Balance)',                            'gri':'401'},
            {'id':'diversity', 'name':'ความหลากหลายและการไม่เลือกปฏิบัติในที่ทำงาน',                      'gri':'406'},
            {'id':'culture',   'name':'วัฒนธรรมองค์กรที่เปิดเผย สามารถแสดงความเห็นได้อย่างอิสระ',        'gri':'2-4'},
            {'id':'env_policy','name':'นโยบายสิ่งแวดล้อมของโรงงาน (การลดของเสีย, ประหยัดพลังงาน)',       'gri':'302'},
            {'id':'csr',       'name':'การมีส่วนร่วมในกิจกรรมชุมชนและ CSR',                               'gri':'413'},
        ],
        'open_qs': [
            {'id':'q1','text':'ถ้าบริษัทเปลี่ยนได้สิ่งเดียวเพื่อทำให้สภาพแวดล้อมการทำงานดีขึ้น คุณอยากให้เปลี่ยนอะไร?'},
            {'id':'q2','text':'มีประเด็นด้านความปลอดภัยหรือสุขภาพที่คุณยังกังวลอยู่ แต่ยังไม่ได้รับการแก้ไข? กรุณาระบุ'},
            {'id':'q3','text':'มีประเด็นอื่นที่บริษัทควรให้ความสำคัญที่ไม่อยู่ในรายการข้างต้น?'},
        ],
    },
    'community': {
        'name': 'ชุมชนท้องถิ่น / NGO', 'icon': '🌳', 'color': '#2E7D32',
        'desc': 'แสดงมุมมองในฐานะตัวแทนชุมชนหรือภาคประชาสังคม',
        'section_a': 'ระดับผลกระทบที่ท่านพบ',
        'instruction': 'กิจกรรมของโรงงานพลาสติกมีผลกระทบต่อชุมชน/สิ่งแวดล้อมมากน้อยแค่ไหน?',
        'topics': [
            {'id':'air',       'name':'มลพิษทางอากาศจากกระบวนการผลิตพลาสติก (กลิ่น, สาร VOC)',           'gri':'305'},
            {'id':'water_poll','name':'มลพิษทางน้ำ (น้ำเสียจากโรงงาน, สีย้อม, สารเคมี)',                'gri':'303'},
            {'id':'plastic_w', 'name':'ขยะพลาสติกและไมโครพลาสติกที่ส่งผลต่อสิ่งแวดล้อมชุมชน',          'gri':'306'},
            {'id':'noise',     'name':'เสียงดังและการสั่นสะเทือนจากโรงงาน',                              'gri':'413'},
            {'id':'ecosystem', 'name':'ผลกระทบต่อแหล่งน้ำและระบบนิเวศในพื้นที่',                        'gri':'304'},
            {'id':'local_jobs','name':'การจ้างงานคนในชุมชนท้องถิ่น',                                     'gri':'413'},
            {'id':'comm_dev',  'name':'การสนับสนุนการศึกษา สาธารณสุข หรือโครงสร้างพื้นฐานชุมชน',       'gri':'413'},
            {'id':'emergency', 'name':'ความโปร่งใสในการแจ้งเตือนเหตุฉุกเฉิน (การรั่วไหลของสารเคมี)',    'gri':'413'},
            {'id':'grievance', 'name':'กระบวนการรับฟังและตอบสนองข้อร้องเรียนของชุมชน',                   'gri':'413'},
        ],
        'open_qs': [
            {'id':'q1','text':'บริษัทควรดำเนินการอย่างไรเพื่อลดผลกระทบต่อสิ่งแวดล้อมและชุมชนที่เห็นเป็นเรื่องเร่งด่วนที่สุด?'},
            {'id':'q2','text':'ช่องทางใดที่ชุมชน/NGO อยากมีส่วนร่วมกับบริษัทมากขึ้น? (เช่น การประชุม, เยี่ยมโรงงาน, รายงานสาธารณะ)'},
            {'id':'q3','text':'มีเหตุการณ์หรือข้อกังวลด้านสิ่งแวดล้อม/สังคมที่ต้องการแจ้งให้บริษัทรับทราบโดยเฉพาะ?'},
        ],
    },
    'supplier': {
        'name': 'ซัพพลายเออร์', 'icon': '🏭', 'color': '#6A1B9A',
        'desc': 'แสดงมุมมองในฐานะพันธมิตรทางธุรกิจในห่วงโซ่อุปทาน',
        'section_a': 'ความสำคัญของมาตรฐาน ESG ในห่วงโซ่อุปทาน',
        'instruction': 'ประเด็นต่อไปนี้มีความสำคัญต่อการดำเนินธุรกิจร่วมกันมากน้อยแค่ไหน?',
        'topics': [
            {'id':'labor_std', 'name':'มาตรฐานแรงงาน (ค่าแรงขั้นต่ำ, ชั่วโมงทำงาน, วันหยุด)',             'gri':'401'},
            {'id':'no_child',  'name':'การห้ามใช้แรงงานเด็กและแรงงานบังคับในห่วงโซ่อุปทาน',               'gri':'408'},
            {'id':'sup_safety','name':'ความปลอดภัยในสถานที่ผลิตของซัพพลายเออร์',                          'gri':'403'},
            {'id':'env_mgmt',  'name':'การจัดการสิ่งแวดล้อมในกระบวนการผลิตวัตถุดิบ',                      'gri':'308'},
            {'id':'ghg_scope3','name':'การเปิดเผยข้อมูลการปล่อย GHG (Scope 3 ของบริษัท)',                 'gri':'305'},
            {'id':'haz_chem',  'name':'การใช้สารเคมีอันตรายในกระบวนการผลิตวัตถุดิบพลาสติก',               'gri':'308'},
            {'id':'cert',      'name':'การรับรองมาตรฐาน (ISO 14001, ISO 45001, SA8000 ฯลฯ)',              'gri':'308'},
            {'id':'anti_bribe','name':'นโยบายต่อต้านคอร์รัปชันและการให้สินบน',                            'gri':'205'},
            {'id':'esg_audit', 'name':'ความโปร่งใสในการรายงาน ESG และการตรวจสอบ (Audit)',                 'gri':'2-4'},
            {'id':'carbon_plan','name':'แผนลด Carbon Footprint ของซัพพลายเออร์',                          'gri':'305'},
        ],
        'open_qs': [
            {'id':'q1','text':'อุปสรรคหลักในการปฏิบัติตามมาตรฐาน ESG ที่บริษัทกำหนดคืออะไร?'},
            {'id':'q2','text':'บริษัทสามารถสนับสนุนท่านด้านความยั่งยืนได้อย่างไร? (เช่น การอบรม, ทรัพยากร, เงื่อนไขการชำระ)'},
            {'id':'q3','text':'มีมาตรฐานหรือข้อกำหนดด้าน ESG ใดที่ต้องการให้บริษัทชี้แจงหรือปรับปรุง?'},
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
    conn.execute('''CREATE TABLE IF NOT EXISTS responses (
        id               INTEGER PRIMARY KEY AUTOINCREMENT,
        stakeholder_type TEXT    NOT NULL,
        respondent_name  TEXT    DEFAULT '',
        respondent_org   TEXT    DEFAULT '',
        submitted_at     TEXT    DEFAULT (datetime('now','localtime')),
        ratings          TEXT    NOT NULL,
        comments         TEXT    DEFAULT '{}',
        open_answers     TEXT    DEFAULT '{}'
    )''')
    conn.execute('''CREATE TABLE IF NOT EXISTS survey_groups (
        id          TEXT PRIMARY KEY,
        name        TEXT NOT NULL,
        icon        TEXT NOT NULL DEFAULT '📋',
        color       TEXT NOT NULL DEFAULT '#2e7d32',
        desc_text   TEXT NOT NULL DEFAULT '',
        section_a   TEXT NOT NULL DEFAULT '',
        instruction TEXT NOT NULL DEFAULT '',
        sort_order  INTEGER DEFAULT 0
    )''')
    conn.execute('''CREATE TABLE IF NOT EXISTS survey_topics (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        group_id   TEXT NOT NULL,
        topic_key  TEXT NOT NULL,
        name       TEXT NOT NULL,
        gri        TEXT NOT NULL DEFAULT '',
        sort_order INTEGER DEFAULT 0
    )''')
    conn.execute('''CREATE TABLE IF NOT EXISTS survey_open_qs (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        group_id   TEXT NOT NULL,
        q_key      TEXT NOT NULL,
        text       TEXT NOT NULL,
        sort_order INTEGER DEFAULT 0
    )''')
    conn.commit()
    conn.close()
    seed_if_empty()

def seed_if_empty():
    conn = get_db()
    count = conn.execute('SELECT COUNT(*) FROM survey_groups').fetchone()[0]
    conn.close()
    if count == 0:
        _do_seed()

def _do_seed():
    conn = get_db()
    conn.execute('DELETE FROM survey_open_qs')
    conn.execute('DELETE FROM survey_topics')
    conn.execute('DELETE FROM survey_groups')
    for i, (gid, g) in enumerate(SEED_DATA.items()):
        conn.execute(
            'INSERT INTO survey_groups VALUES (?,?,?,?,?,?,?,?)',
            (gid, g['name'], g['icon'], g['color'], g['desc'], g['section_a'], g['instruction'], i)
        )
        for j, t in enumerate(g['topics']):
            conn.execute(
                'INSERT INTO survey_topics (group_id,topic_key,name,gri,sort_order) VALUES (?,?,?,?,?)',
                (gid, t['id'], t['name'], t['gri'], j)
            )
        for j, q in enumerate(g['open_qs']):
            conn.execute(
                'INSERT INTO survey_open_qs (group_id,q_key,text,sort_order) VALUES (?,?,?,?)',
                (gid, q['id'], q['text'], j)
            )
    conn.commit()
    conn.close()

def get_survey_data():
    conn = get_db()
    groups = conn.execute('SELECT * FROM survey_groups ORDER BY sort_order, rowid').fetchall()
    result = {}
    for g in groups:
        gid = g['id']
        topics  = conn.execute('SELECT * FROM survey_topics  WHERE group_id=? ORDER BY sort_order, id', (gid,)).fetchall()
        open_qs = conn.execute('SELECT * FROM survey_open_qs WHERE group_id=? ORDER BY sort_order, id', (gid,)).fetchall()
        result[gid] = {
            'name': g['name'], 'icon': g['icon'], 'color': g['color'],
            'desc': g['desc_text'], 'section_a': g['section_a'], 'instruction': g['instruction'],
            'topics':  [{'id': t['topic_key'], 'name': t['name'], 'gri': t['gri'], '_dbid': t['id']}  for t in topics],
            'open_qs': [{'id': q['q_key'],     'text': q['text'],                  '_dbid': q['id']}  for q in open_qs],
        }
    conn.close()
    return result

init_db()

# ──────────────────────────────────────────────────────────────────────────────
# Auth helper
# ──────────────────────────────────────────────────────────────────────────────
def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('admin_ok'):
            return redirect(url_for('admin'))
        return f(*args, **kwargs)
    return decorated

# ──────────────────────────────────────────────────────────────────────────────
# Public routes
# ──────────────────────────────────────────────────────────────────────────────
@app.route('/')
def index():
    return render_template('index.html', survey=get_survey_data())

@app.route('/survey/<stype>')
def survey(stype):
    sd = get_survey_data()
    if stype not in sd:
        return redirect(url_for('index'))
    return render_template('survey.html', stype=stype, data=sd[stype])

@app.route('/submit', methods=['POST'])
def submit():
    stype = request.form.get('stype', '')
    sd = get_survey_data()
    if stype not in sd:
        return redirect(url_for('index'))
    name = request.form.get('respondent_name', '').strip()
    org  = request.form.get('respondent_org',  '').strip()
    ratings  = {}
    comments = {}
    for t in sd[stype]['topics']:
        r = request.form.get(f'r_{t["id"]}')
        c = request.form.get(f'c_{t["id"]}', '').strip()
        if r: ratings[t['id']]  = int(r)
        if c: comments[t['id']] = c
    open_ans = {}
    for q in sd[stype]['open_qs']:
        a = request.form.get(f'open_{q["id"]}', '').strip()
        if a: open_ans[q['id']] = a
    conn = get_db()
    conn.execute(
        'INSERT INTO responses (stakeholder_type,respondent_name,respondent_org,ratings,comments,open_answers) VALUES (?,?,?,?,?,?)',
        (stype, name, org,
         json.dumps(ratings,  ensure_ascii=False),
         json.dumps(comments, ensure_ascii=False),
         json.dumps(open_ans, ensure_ascii=False))
    )
    conn.commit(); conn.close()
    return redirect(url_for('thanks'))

@app.route('/thanks')
def thanks():
    return render_template('thanks.html')

# ──────────────────────────────────────────────────────────────────────────────
# Admin auth
# ──────────────────────────────────────────────────────────────────────────────
@app.route('/admin')
def admin():
    if not session.get('admin_ok'):
        return render_template('admin_login.html', error=False)
    return render_template('admin.html', survey=get_survey_data())

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
# Admin stats API
# ──────────────────────────────────────────────────────────────────────────────
@app.route('/api/stats')
@admin_required
def api_stats():
    sd   = get_survey_data()
    conn = get_db()
    rows = conn.execute('SELECT stakeholder_type,ratings,open_answers,submitted_at FROM responses ORDER BY submitted_at DESC').fetchall()
    conn.close()
    total   = len(rows)
    by_type = {}
    topic_sums = {}
    for row in rows:
        st = row['stakeholder_type']
        by_type[st] = by_type.get(st, 0) + 1
        topic_sums.setdefault(st, {})
        try:
            for tid, score in json.loads(row['ratings']).items():
                topic_sums[st].setdefault(tid, []).append(score)
        except Exception: pass
    averages = {}
    for st, sdata in sd.items():
        averages[st] = []
        for t in sdata['topics']:
            scores = topic_sums.get(st, {}).get(t['id'], [])
            averages[st].append({'id': t['id'], 'name': t['name'], 'gri': t['gri'],
                                 'avg': round(sum(scores)/len(scores), 2) if scores else None, 'n': len(scores)})
    global_pool = {}
    for st_avgs in averages.values():
        for item in st_avgs:
            if item['avg'] is not None:
                global_pool.setdefault(item['name'], []).append(item['avg'])
    global_rank = sorted(
        [{'name': k, 'avg': round(sum(v)/len(v), 2), 'n': len(v)} for k, v in global_pool.items()],
        key=lambda x: -x['avg']
    )
    recent = [{'stype': r['stakeholder_type'],
               'sname': sd.get(r['stakeholder_type'], {}).get('name', ''),
               'at':    r['submitted_at']} for r in rows[:15]]
    return jsonify({'total': total, 'by_type': by_type, 'averages': averages,
                    'global_rank': global_rank, 'recent': recent,
                    'survey': {k: {'name': v['name'], 'icon': v['icon'], 'color': v['color']} for k, v in sd.items()}})

@app.route('/api/responses')
@admin_required
def api_responses():
    stype = request.args.get('stype', '')
    conn  = get_db()
    if stype:
        rows = conn.execute('SELECT * FROM responses WHERE stakeholder_type=? ORDER BY submitted_at DESC', (stype,)).fetchall()
    else:
        rows = conn.execute('SELECT * FROM responses ORDER BY submitted_at DESC').fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route('/export/csv')
@admin_required
def export_csv():
    sd   = get_survey_data()
    conn = get_db()
    rows = conn.execute('SELECT * FROM responses ORDER BY submitted_at DESC').fetchall()
    conn.close()
    buf = io.StringIO()
    w   = csv.writer(buf)
    w.writerow(['ID','ประเภทผู้มีส่วนได้เสีย','ชื่อ','องค์กร','วันเวลา','คะแนนรายประเด็น (JSON)','ความเห็น (JSON)','คำตอบเปิด (JSON)'])
    for r in rows:
        w.writerow([r['id'], sd.get(r['stakeholder_type'], {}).get('name', r['stakeholder_type']),
                    r['respondent_name'], r['respondent_org'], r['submitted_at'],
                    r['ratings'], r['comments'], r['open_answers']])
    buf.seek(0)
    return Response('﻿' + buf.getvalue(), mimetype='text/csv; charset=utf-8',
                    headers={'Content-Disposition': f'attachment; filename=materiality_{datetime.now().strftime("%Y%m%d")}.csv'})

# ──────────────────────────────────────────────────────────────────────────────
# Admin Editor – Survey Content CMS
# ──────────────────────────────────────────────────────────────────────────────
@app.route('/admin/editor')
@admin_required
def editor():
    sd = get_survey_data()
    first = next(iter(sd), 'investor')
    return redirect(url_for('editor_group', stype=first))

@app.route('/admin/editor/<stype>')
@admin_required
def editor_group(stype):
    sd = get_survey_data()
    if stype not in sd:
        return redirect(url_for('editor'))
    conn = get_db()
    group   = conn.execute('SELECT * FROM survey_groups  WHERE id=?',       (stype,)).fetchone()
    topics  = conn.execute('SELECT * FROM survey_topics  WHERE group_id=? ORDER BY sort_order, id', (stype,)).fetchall()
    open_qs = conn.execute('SELECT * FROM survey_open_qs WHERE group_id=? ORDER BY sort_order, id', (stype,)).fetchall()
    conn.close()
    edit_tid = request.args.get('edit_tid', type=int)
    edit_qid = request.args.get('edit_qid', type=int)
    msg      = request.args.get('msg', '')
    return render_template('admin_editor.html',
                           survey=sd, stype=stype, group=group,
                           topics=topics, open_qs=open_qs,
                           edit_tid=edit_tid, edit_qid=edit_qid, msg=msg)

# ── Group metadata ────────────────────────────────────────────────────────────
@app.route('/admin/editor/<stype>/meta', methods=['POST'])
@admin_required
def editor_meta(stype):
    f = request.form
    conn = get_db()
    conn.execute(
        'UPDATE survey_groups SET name=?,icon=?,color=?,desc_text=?,section_a=?,instruction=? WHERE id=?',
        (f.get('name','').strip(), f.get('icon','').strip(), f.get('color','#2e7d32'),
         f.get('desc_text','').strip(), f.get('section_a','').strip(), f.get('instruction','').strip(), stype)
    )
    conn.commit(); conn.close()
    return redirect(url_for('editor_group', stype=stype, msg='บันทึกข้อมูลกลุ่มสำเร็จ'))

# ── Topics ────────────────────────────────────────────────────────────────────
@app.route('/admin/editor/<stype>/topic/add', methods=['POST'])
@admin_required
def topic_add(stype):
    name = request.form.get('name', '').strip()
    gri  = request.form.get('gri',  '').strip()
    if not name:
        return redirect(url_for('editor_group', stype=stype))
    conn = get_db()
    max_ord = conn.execute('SELECT COALESCE(MAX(sort_order),0) FROM survey_topics WHERE group_id=?', (stype,)).fetchone()[0]
    key = f'topic_{int(time.time()*1000) % 10**9}'
    conn.execute('INSERT INTO survey_topics (group_id,topic_key,name,gri,sort_order) VALUES (?,?,?,?,?)',
                 (stype, key, name, gri, max_ord + 1))
    conn.commit(); conn.close()
    return redirect(url_for('editor_group', stype=stype, msg='เพิ่มประเด็นสำเร็จ'))

@app.route('/admin/editor/topic/<int:tid>/save', methods=['POST'])
@admin_required
def topic_save(tid):
    stype = request.form.get('stype', '')
    name  = request.form.get('name',  '').strip()
    gri   = request.form.get('gri',   '').strip()
    conn  = get_db()
    conn.execute('UPDATE survey_topics SET name=?,gri=? WHERE id=?', (name, gri, tid))
    conn.commit(); conn.close()
    return redirect(url_for('editor_group', stype=stype, msg='แก้ไขประเด็นสำเร็จ'))

@app.route('/admin/editor/topic/<int:tid>/delete', methods=['POST'])
@admin_required
def topic_delete(tid):
    stype = request.form.get('stype', '')
    conn  = get_db()
    conn.execute('DELETE FROM survey_topics WHERE id=?', (tid,))
    conn.commit(); conn.close()
    return redirect(url_for('editor_group', stype=stype, msg='ลบประเด็นสำเร็จ'))

@app.route('/admin/editor/topic/<int:tid>/move', methods=['POST'])
@admin_required
def topic_move(tid):
    stype = request.form.get('stype', '')
    direction = request.form.get('direction', 'up')
    conn   = get_db()
    topics = conn.execute('SELECT id FROM survey_topics WHERE group_id=? ORDER BY sort_order, id', (stype,)).fetchall()
    ids    = [t['id'] for t in topics]
    if tid in ids:
        idx = ids.index(tid)
        swap = idx - 1 if direction == 'up' else idx + 1
        if 0 <= swap < len(ids):
            conn.execute('UPDATE survey_topics SET sort_order=? WHERE id=?', (swap,   tid))
            conn.execute('UPDATE survey_topics SET sort_order=? WHERE id=?', (idx, ids[swap]))
            conn.commit()
    conn.close()
    return redirect(url_for('editor_group', stype=stype))

# ── Open questions ────────────────────────────────────────────────────────────
@app.route('/admin/editor/<stype>/openq/add', methods=['POST'])
@admin_required
def openq_add(stype):
    text = request.form.get('text', '').strip()
    if not text:
        return redirect(url_for('editor_group', stype=stype))
    conn    = get_db()
    max_ord = conn.execute('SELECT COALESCE(MAX(sort_order),0) FROM survey_open_qs WHERE group_id=?', (stype,)).fetchone()[0]
    key     = f'q_{int(time.time()*1000) % 10**9}'
    conn.execute('INSERT INTO survey_open_qs (group_id,q_key,text,sort_order) VALUES (?,?,?,?)',
                 (stype, key, text, max_ord + 1))
    conn.commit(); conn.close()
    return redirect(url_for('editor_group', stype=stype, msg='เพิ่มคำถามสำเร็จ'))

@app.route('/admin/editor/openq/<int:qid>/save', methods=['POST'])
@admin_required
def openq_save(qid):
    stype = request.form.get('stype', '')
    text  = request.form.get('text',  '').strip()
    conn  = get_db()
    conn.execute('UPDATE survey_open_qs SET text=? WHERE id=?', (text, qid))
    conn.commit(); conn.close()
    return redirect(url_for('editor_group', stype=stype, msg='แก้ไขคำถามสำเร็จ'))

@app.route('/admin/editor/openq/<int:qid>/delete', methods=['POST'])
@admin_required
def openq_delete(qid):
    stype = request.form.get('stype', '')
    conn  = get_db()
    conn.execute('DELETE FROM survey_open_qs WHERE id=?', (qid,))
    conn.commit(); conn.close()
    return redirect(url_for('editor_group', stype=stype, msg='ลบคำถามสำเร็จ'))

@app.route('/admin/editor/openq/<int:qid>/move', methods=['POST'])
@admin_required
def openq_move(qid):
    stype     = request.form.get('stype', '')
    direction = request.form.get('direction', 'up')
    conn  = get_db()
    items = conn.execute('SELECT id FROM survey_open_qs WHERE group_id=? ORDER BY sort_order, id', (stype,)).fetchall()
    ids   = [q['id'] for q in items]
    if qid in ids:
        idx  = ids.index(qid)
        swap = idx - 1 if direction == 'up' else idx + 1
        if 0 <= swap < len(ids):
            conn.execute('UPDATE survey_open_qs SET sort_order=? WHERE id=?', (swap,   qid))
            conn.execute('UPDATE survey_open_qs SET sort_order=? WHERE id=?', (idx, ids[swap]))
            conn.commit()
    conn.close()
    return redirect(url_for('editor_group', stype=stype))

# ── Reset to default ──────────────────────────────────────────────────────────
@app.route('/admin/editor/reset', methods=['POST'])
@admin_required
def editor_reset():
    _do_seed()
    return redirect(url_for('editor', msg='รีเซ็ตเป็นข้อมูลเริ่มต้นสำเร็จ'))

# ──────────────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
