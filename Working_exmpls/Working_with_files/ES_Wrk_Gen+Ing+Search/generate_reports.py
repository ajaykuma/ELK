"""
pip install reportlab
generate_reports.py
Generates 50 synthetic patient lab reports (PDF) covering a range of ailments.
Outputs to: lab_reports/
"""

import os, random
import reportlab
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

OUT_DIR = "E:\\ES_Wrk_Gen+Ing+Search\\lab_reports"
os.makedirs(OUT_DIR, exist_ok=True)

styles = getSampleStyleSheet()

# ─────────────────────────────────────────────────────────────────────────────
# Patient pool
# ─────────────────────────────────────────────────────────────────────────────
FIRST_NAMES = ["Aarav","Bhavna","Carlos","Diana","Ethan","Fatima","George","Hina",
                "Ivan","Jasmine","Kevin","Lena","Marco","Nadia","Omar","Priya",
                "Quinn","Ravi","Sara","Tariq","Uma","Victor","Wendy","Xena",
                "Yusuf","Zara","Aiden","Brenda","Chen","Daria","Elias","Fiona",
                "Grant","Hana","Igor","Jaya","Kim","Lars","Mia","Noah",
                "Olga","Pedro","Qing","Rita","Sam","Tara","Usman","Vera","Wei","Yuki"]
LAST_NAMES  = ["Smith","Patel","Garcia","Kim","Okafor","Nguyen","Müller","Hassan",
                "Rossi","Park","Brown","Singh","Lopez","Chen","Ali","Johansson",
                "Tanaka","Andersen","Kowalski","Martin","Ferreira","Ahmed","Liu",
                "Williams","Russo","Nakamura","Clark","Das","Meyer","Lee"]
DOCTORS     = ["Dr. Mehta","Dr. Park","Dr. Ali","Dr. Torres","Dr. Müller","Dr. Osei","Dr. Sharma"]
SPECIALTIES = ["Nephrologist","Cardiologist","Endocrinologist","Pulmonologist",
                "General Physician","Gastroenterologist","Hematologist"]

MONTHS = ["January","February","March","April","May","June",
          "July","August","September","October","November","December"]

def rand_date(year=2025):
    m = random.randint(1,12)
    d = random.randint(1,28)
    return f"{MONTHS[m-1]} {d}, {year}"

def dob():
    y = random.randint(1955,2000)
    m = random.randint(1,12)
    d = random.randint(1,28)
    return f"{MONTHS[m-1]} {d}, {y}"

# ─────────────────────────────────────────────────────────────────────────────
# Ailment profiles – each defines abnormal ranges for various tests
# ─────────────────────────────────────────────────────────────────────────────
AILMENTS = [
    # ── 1. Type 2 Diabetes ───────────────────────────────────────────────────
    {
        "name": "Type 2 Diabetes",
        "notes": (
            "HbA1c above 6.5% confirms poor glycaemic control. Fasting glucose elevated. "
            "Microalbuminuria detected — early nephropathy screening required. "
            "Lipid panel shows dyslipidaemia pattern common in metabolic syndrome. "
            "Recommend titrating metformin dose and lifestyle counselling."
        ),
        "cbc": {"Hemoglobin":("12.8","12.0-16.0","Normal"),"WBC Count":("8.5","4.0-11.0","Normal"),
                "Platelets":("230","150-400","Normal"),"Eosinophils":("2.1","1-4","Normal")},
        "thyroid": {"TSH":("2.4","0.4-4.0","Normal"),"Free T4":("1.1","0.8-1.8","Normal")},
        "metabolic": {"Glucose (Fasting)":("182","70-100","HIGH ⚠"),"HbA1c":("8.2","< 5.7 %","HIGH ⚠"),
                      "Creatinine":("0.92","0.5-1.1","Normal"),"eGFR":("74","> 60","Normal"),
                      "ALT":("35","7-40","Normal"),"Cholesterol":("218","< 200","HIGH ⚠")},
        "extra": {"Microalbumin/Creatinine":("42","< 30","HIGH ⚠"),"Insulin":("28","2-25","HIGH ⚠")},
        "extra_title": "5. Diabetes & Renal Markers",
        "specialty": "Endocrinologist",
    },
    # ── 2. Hypothyroidism ────────────────────────────────────────────────────
    {
        "name": "Hypothyroidism",
        "notes": (
            "TSH markedly elevated with low Free T4 — consistent with primary hypothyroidism. "
            "Patient reports fatigue, weight gain, and cold intolerance. "
            "Lipid elevation secondary to thyroid dysfunction. "
            "Initiate levothyroxine 50 mcg; recheck TFT in 6 weeks."
        ),
        "cbc": {"Hemoglobin":("11.2","12.0-16.0","LOW ⚠"),"WBC Count":("5.8","4.0-11.0","Normal"),
                "Platelets":("195","150-400","Normal"),"MCV":("102","80-100","HIGH ⚠")},
        "thyroid": {"TSH":("14.6","0.4-4.0","HIGH ⚠"),"Free T4":("0.5","0.8-1.8","LOW ⚠"),
                    "Free T3":("1.9","2.3-4.2","LOW ⚠"),"Anti-TPO":("285","< 35","HIGH ⚠")},
        "metabolic": {"Glucose (Fasting)":("98","70-100","Normal"),"Cholesterol":("242","< 200","HIGH ⚠"),
                      "LDL":("158","< 100","HIGH ⚠"),"Creatinine":("0.85","0.5-1.1","Normal")},
        "extra": {},
        "extra_title": "",
        "specialty": "Endocrinologist",
    },
    # ── 3. Iron-Deficiency Anaemia ───────────────────────────────────────────
    {
        "name": "Iron-Deficiency Anaemia",
        "notes": (
            "Microcytic hypochromic anaemia with low serum ferritin and iron. "
            "TIBC elevated consistent with iron deficiency. "
            "Review dietary intake; rule out GI blood loss. "
            "Start oral ferrous sulphate 200 mg twice daily with vitamin C."
        ),
        "cbc": {"Hemoglobin":("8.6","12.0-16.0","LOW ⚠"),"WBC Count":("6.1","4.0-11.0","Normal"),
                "Platelets":("410","150-400","HIGH ⚠"),"MCV":("68","80-100","LOW ⚠"),
                "MCH":("21","27-33","LOW ⚠")},
        "thyroid": {"TSH":("1.9","0.4-4.0","Normal"),"Free T4":("1.0","0.8-1.8","Normal")},
        "metabolic": {"Glucose (Fasting)":("88","70-100","Normal"),"Creatinine":("0.70","0.5-1.1","Normal")},
        "extra": {"Serum Iron":("38","60-170","LOW ⚠"),"TIBC":("450","240-450","HIGH ⚠"),
                  "Ferritin":("4","20-200","LOW ⚠"),"Transferrin Saturation":("8","20-50","LOW ⚠")},
        "extra_title": "5. Iron Studies",
        "specialty": "Hematologist",
    },
    # ── 4. Chronic Kidney Disease ────────────────────────────────────────────
    {
        "name": "Chronic Kidney Disease (Stage 3)",
        "notes": (
            "eGFR 38 — consistent with CKD Stage 3b. Creatinine and BUN elevated. "
            "Hyperphosphataemia and mild anaemia of chronic disease noted. "
            "Blood pressure management critical to slow progression. "
            "Restrict dietary protein and phosphate; nephrology follow-up monthly."
        ),
        "cbc": {"Hemoglobin":("10.4","12.0-16.0","LOW ⚠"),"WBC Count":("7.2","4.0-11.0","Normal"),
                "Platelets":("188","150-400","Normal")},
        "thyroid": {"TSH":("3.1","0.4-4.0","Normal"),"Free T4":("1.0","0.8-1.8","Normal")},
        "metabolic": {"Glucose (Fasting)":("102","70-100","HIGH ⚠"),"Creatinine":("2.4","0.5-1.1","HIGH ⚠"),
                      "eGFR":("38","> 60","LOW ⚠"),"BUN":("42","7-20","HIGH ⚠"),
                      "Potassium":("5.6","3.5-5.1","HIGH ⚠"),"Phosphorus":("5.8","2.5-4.5","HIGH ⚠")},
        "extra": {},
        "extra_title": "",
        "specialty": "Nephrologist",
    },
    # ── 5. Liver Cirrhosis ───────────────────────────────────────────────────
    {
        "name": "Liver Cirrhosis (Child-Pugh B)",
        "notes": (
            "Markedly elevated AST/ALT and bilirubin indicate significant hepatic dysfunction. "
            "INR prolonged — synthetic function impaired. Low albumin, thrombocytopaenia. "
            "Refer for hepatology evaluation and variceal screening endoscopy. "
            "Alcohol cessation mandatory; nutritional support initiated."
        ),
        "cbc": {"Hemoglobin":("10.8","12.0-16.0","LOW ⚠"),"WBC Count":("3.2","4.0-11.0","LOW ⚠"),
                "Platelets":("88","150-400","LOW ⚠")},
        "thyroid": {"TSH":("2.0","0.4-4.0","Normal"),"Free T4":("1.1","0.8-1.8","Normal")},
        "metabolic": {"Glucose (Fasting)":("78","70-100","Normal"),"ALT":("112","7-40","HIGH ⚠"),
                      "AST":("158","10-40","HIGH ⚠"),"Bilirubin (Total)":("4.2","< 1.2","HIGH ⚠"),
                      "Albumin":("2.4","3.5-5.0","LOW ⚠"),"INR":("1.8","0.8-1.1","HIGH ⚠")},
        "extra": {},
        "extra_title": "",
        "specialty": "Gastroenterologist",
    },
    # ── 6. Hypertensive Heart Disease ────────────────────────────────────────
    {
        "name": "Hypertensive Heart Disease",
        "notes": (
            "BNP significantly elevated indicating cardiac strain. "
            "LDL cholesterol above target despite statin. Troponin borderline. "
            "ECG shows LVH pattern. Echocardiogram recommended. "
            "Optimise antihypertensive regimen; add ACE inhibitor if not contraindicated."
        ),
        "cbc": {"Hemoglobin":("14.2","12.0-16.0","Normal"),"WBC Count":("7.8","4.0-11.0","Normal"),
                "Platelets":("215","150-400","Normal")},
        "thyroid": {"TSH":("1.8","0.4-4.0","Normal"),"Free T4":("1.2","0.8-1.8","Normal")},
        "metabolic": {"Glucose (Fasting)":("108","70-100","HIGH ⚠"),"Cholesterol":("228","< 200","HIGH ⚠"),
                      "LDL":("148","< 100","HIGH ⚠"),"HDL":("38","≥ 60","LOW ⚠"),
                      "Creatinine":("1.1","0.5-1.1","Normal"),"eGFR":("65","> 60","Normal")},
        "extra": {"BNP":("420","< 100","HIGH ⚠"),"Troponin I":("0.06","< 0.04","HIGH ⚠"),
                  "hsCRP":("6.8","< 3.0","HIGH ⚠")},
        "extra_title": "5. Cardiac Markers",
        "specialty": "Cardiologist",
    },
    # ── 7. Asthma / Allergy ──────────────────────────────────────────────────
    {
        "name": "Allergic Asthma",
        "notes": (
            "Elevated eosinophils and Total IgE consistent with atopic asthma. "
            "Positive specific IgE to house dust mites and pollen. "
            "Peak expiratory flow below predicted — moderate airflow limitation. "
            "Step up to ICS/LABA combination; consider allergen immunotherapy."
        ),
        "cbc": {"Hemoglobin":("13.8","12.0-16.0","Normal"),"WBC Count":("9.2","4.0-11.0","Normal"),
                "Eosinophils":("6.2","1-4","HIGH ⚠")},
        "thyroid": {"TSH":("2.1","0.4-4.0","Normal"),"Free T4":("1.2","0.8-1.8","Normal")},
        "metabolic": {"Glucose (Fasting)":("94","70-100","Normal"),"Creatinine":("0.78","0.5-1.1","Normal")},
        "extra": {"Total IgE":("420","< 100","HIGH ⚠"),"Specific IgE (Dust mites)":("3.8","< 0.35","HIGH ⚠"),
                  "CRP":("8.4","< 5.0","HIGH ⚠"),"Peak Expiratory Flow":("310","380-500","LOW ⚠")},
        "extra_title": "5. Allergy & Pulmonary Markers",
        "specialty": "Pulmonologist",
    },
    # ── 8. Sepsis / Bacterial Infection ──────────────────────────────────────
    {
        "name": "Bacterial Sepsis",
        "notes": (
            "Markedly elevated WBC with left shift; CRP and PCT sky-high consistent with sepsis. "
            "Lactate elevated — tissue hypoperfusion. Cultures pending. "
            "IV broad-spectrum antibiotics initiated. ICU monitoring warranted. "
            "Reassess in 24 h; de-escalate antibiotics per culture sensitivity."
        ),
        "cbc": {"Hemoglobin":("11.6","12.0-16.0","LOW ⚠"),"WBC Count":("24.8","4.0-11.0","HIGH ⚠"),
                "Neutrophils":("88","40-75","HIGH ⚠"),"Bands":("14","< 5","HIGH ⚠"),
                "Platelets":("96","150-400","LOW ⚠")},
        "thyroid": {"TSH":("1.5","0.4-4.0","Normal"),"Free T4":("1.0","0.8-1.8","Normal")},
        "metabolic": {"Glucose (Fasting)":("148","70-100","HIGH ⚠"),"Creatinine":("1.6","0.5-1.1","HIGH ⚠"),
                      "Lactate":("4.2","< 2.0","HIGH ⚠"),"ALT":("68","7-40","HIGH ⚠")},
        "extra": {"CRP":("248","< 5.0","HIGH ⚠"),"Procalcitonin":("18.4","< 0.5","HIGH ⚠"),
                  "Blood Culture":"Pending","INR":("1.6","0.8-1.1","HIGH ⚠")},
        "extra_title": "5. Infection & Inflammation Markers",
        "specialty": "General Physician",
    },
    # ── 9. Polycystic Ovary Syndrome ─────────────────────────────────────────
    {
        "name": "Polycystic Ovary Syndrome (PCOS)",
        "notes": (
            "Elevated LH:FSH ratio and free testosterone consistent with PCOS. "
            "Mild insulin resistance present — HOMA-IR elevated. "
            "AMH markedly elevated. Ultrasound confirmed polycystic ovarian morphology. "
            "Lifestyle modification first-line; metformin for insulin resistance."
        ),
        "cbc": {"Hemoglobin":("13.2","12.0-16.0","Normal"),"WBC Count":("7.1","4.0-11.0","Normal"),
                "Platelets":("210","150-400","Normal")},
        "thyroid": {"TSH":("1.6","0.4-4.0","Normal"),"Free T4":("1.1","0.8-1.8","Normal"),
                    "Anti-TPO":("18","< 35","Normal")},
        "metabolic": {"Glucose (Fasting)":("105","70-100","HIGH ⚠"),"Insulin (Fasting)":("22","2-25","HIGH ⚠"),
                      "HOMA-IR":("5.8","< 2.5","HIGH ⚠"),"Cholesterol":("205","< 200","HIGH ⚠")},
        "extra": {"LH":("18","2-15 mIU/mL","HIGH ⚠"),"FSH":("5.2","2-10 mIU/mL","Normal"),
                  "Free Testosterone":("4.8","< 2.0 pg/mL","HIGH ⚠"),"AMH":("8.4","1-3.5 ng/mL","HIGH ⚠")},
        "extra_title": "5. Hormonal Panel",
        "specialty": "Endocrinologist",
    },
    # ── 10. Rheumatoid Arthritis ─────────────────────────────────────────────
    {
        "name": "Rheumatoid Arthritis",
        "notes": (
            "Positive RF and anti-CCP antibodies confirm seropositive RA. "
            "ESR and CRP markedly elevated — active disease. "
            "Anaemia of chronic disease noted. X-ray shows early erosive changes. "
            "Initiate methotrexate; folic acid supplementation; DMARD review in 3 months."
        ),
        "cbc": {"Hemoglobin":("10.6","12.0-16.0","LOW ⚠"),"WBC Count":("9.4","4.0-11.0","Normal"),
                "Platelets":("480","150-400","HIGH ⚠"),"ESR":("78","< 20","HIGH ⚠")},
        "thyroid": {"TSH":("2.2","0.4-4.0","Normal"),"Free T4":("1.0","0.8-1.8","Normal")},
        "metabolic": {"Glucose (Fasting)":("92","70-100","Normal"),"Creatinine":("0.82","0.5-1.1","Normal"),
                      "ALT":("28","7-40","Normal")},
        "extra": {"Rheumatoid Factor":("128","< 20 IU/mL","HIGH ⚠"),"Anti-CCP":("320","< 17 U/mL","HIGH ⚠"),
                  "CRP":("42","< 5.0","HIGH ⚠"),"ANA Titre":"1:320 (Positive)"},
        "extra_title": "5. Autoimmune Markers",
        "specialty": "General Physician",
    },
]

# ─────────────────────────────────────────────────────────────────────────────
# Expand to 50 patients by cycling through ailments with random perturbations
# ─────────────────────────────────────────────────────────────────────────────
def perturb(val_str, pct=0.08):
    """Slightly jitter a numeric string value."""
    try:
        v = float(val_str)
        v *= random.uniform(1 - pct, 1 + pct)
        return f"{v:.1f}" if '.' in val_str else str(int(round(v)))
    except ValueError:
        return val_str

def make_table(data_dict, col_widths):
    header = ["Test", "Result", "Reference Range", "Unit/Info", "Status"]
    rows = [header]
    for test, vals in data_dict.items():
        if isinstance(vals, tuple):
            rows.append([test, perturb(vals[0]), vals[1], "", vals[2]])
        else:
            rows.append([test, vals, "", "", ""])
    t = Table(rows, colWidths=col_widths)
    red_rows = [i for i, r in enumerate(rows) if "HIGH" in r[4] or "LOW" in r[4]]
    style = [
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#2E86AB")),
        ("TEXTCOLOR",  (0,0), (-1,0), colors.white),
        ("FONTNAME",   (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE",   (0,0), (-1,-1), 9),
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#F0F4F8")]),
        ("BOX",        (0,0), (-1,-1), 0.5, colors.grey),
        ("INNERGRID",  (0,0), (-1,-1), 0.25, colors.grey),
        ("PADDING",    (0,0), (-1,-1), 6),
    ]
    for r in red_rows:
        style += [("TEXTCOLOR", (4,r), (4,r), colors.red),
                  ("FONTNAME",  (4,r), (4,r), "Helvetica-Bold")]
    t.setStyle(TableStyle(style))
    return t

def generate_report(patient_id, first, last, ailment, sample_date, report_date, birth):
    path = os.path.join(OUT_DIR, f"P{patient_id:03d}_{first}_{last}_lab_report.pdf")
    doc = SimpleDocTemplate(path, pagesize=letter,
                            rightMargin=50, leftMargin=50, topMargin=50, bottomMargin=50)
    elements = []

    # Header
    elements.append(Paragraph("CITY MEDICAL CENTER", styles["Title"]))
    elements.append(Paragraph("Laboratory Investigation Report", styles["Heading2"]))
    elements.append(Spacer(1, 12))

    # Patient info
    gender = random.choice(["Male","Female"])
    doctor = random.choice(DOCTORS)
    info = [
        ["Patient Name:", f"{first} {last}", "Patient ID:", f"P{patient_id:03d}"],
        ["Date of Birth:", birth,             "Gender:", gender],
        ["Ordering Doctor:", doctor,           "Specialty:", ailment["specialty"]],
        ["Sample Collected:", sample_date,    "Report Date:", report_date],
        ["Clinical Notes:", ailment["name"] + " follow-up.", "", ""],
    ]
    ti = Table(info, colWidths=[120,150,100,150])
    ti.setStyle(TableStyle([
        ("FONTNAME", (0,0), (-1,-1), "Helvetica"),
        ("FONTSIZE", (0,0), (-1,-1), 9),
        ("FONTNAME", (0,0), (0,-1), "Helvetica-Bold"),
        ("FONTNAME", (2,0), (2,-1), "Helvetica-Bold"),
        ("BACKGROUND", (0,0), (-1,0), colors.lightblue),
        ("BOX", (0,0), (-1,-1), 0.5, colors.grey),
        ("INNERGRID", (0,0), (-1,-1), 0.25, colors.grey),
        ("PADDING", (0,0), (-1,-1), 6),
    ]))
    elements.append(ti)
    elements.append(Spacer(1,16))

    # CBC
    elements.append(Paragraph("1. Complete Blood Count (CBC)", styles["Heading3"]))
    elements.append(make_table(ailment["cbc"], [150,70,130,70,70]))
    elements.append(Spacer(1,14))

    # Thyroid
    elements.append(Paragraph("2. Thyroid Function Tests", styles["Heading3"]))
    elements.append(make_table(ailment["thyroid"], [150,70,130,70,70]))
    elements.append(Spacer(1,14))

    # Metabolic
    elements.append(Paragraph("3. Basic Metabolic Panel", styles["Heading3"]))
    elements.append(make_table(ailment["metabolic"], [150,70,130,70,70]))
    elements.append(Spacer(1,14))

    # Extra section (optional)
    if ailment.get("extra"):
        elements.append(Paragraph(f"4. {ailment['extra_title'].lstrip('5. ')}", styles["Heading3"]))
        elements.append(make_table(ailment["extra"], [180,70,130,50,60]))
        elements.append(Spacer(1,14))

    # Physician notes
    elements.append(Paragraph("Interpreting Physician Notes", styles["Heading3"]))
    note_text = (
        f"<b>Dr. Priya Sharma (Pulmonology / {ailment['specialty']}) — {report_date}</b><br/><br/>"
        f"<b>Primary Diagnosis:</b> {ailment['name']}<br/><br/>"
        f"{ailment['notes'].replace(chr(10), '<br/>')}<br/><br/>"
        "Signed: Dr. Priya Sharma, MD | City Medical Center"
    )
    elements.append(Paragraph(note_text, styles["Normal"]))

    doc.build(elements)
    return path

# ─────────────────────────────────────────────────────────────────────────────
# Generate 50 reports
# ─────────────────────────────────────────────────────────────────────────────
random.seed(42)
generated = []

for i in range(50):
    pid   = i + 1
    first = FIRST_NAMES[i]
    last  = random.choice(LAST_NAMES)
    a     = AILMENTS[i % len(AILMENTS)]
    sd    = rand_date(2025)
    rd    = rand_date(2025)
    bd    = dob()
    path  = generate_report(pid, first, last, a, sd, rd, bd)
    generated.append(path)
    print(f"[{pid:02d}/50] {os.path.basename(path)}")

print(f"\n {len(generated)} PDFs saved to {OUT_DIR}")
