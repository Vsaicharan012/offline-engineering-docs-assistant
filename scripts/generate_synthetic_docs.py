"""Run from project root: python scripts/generate_synthetic_docs.py"""
from pathlib import Path
import fitz
from docx import Document
from PIL import Image, ImageDraw, ImageFont
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, PageBreak, Table, TableStyle

OUT = Path(__file__).resolve().parent.parent / "documents" / "synthetic"
OUT.mkdir(parents=True, exist_ok=True)
ss = getSampleStyleSheet()
H, B, T = ss["Heading2"], ss["BodyText"], ss["Title"]
P = lambda t, s=B: Paragraph(t, s)

def grid(rows):
    t = Table(rows, repeatRows=1)
    t.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.7, colors.black),
                           ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey), ("FONTSIZE", (0, 0), (-1, -1), 9)]))
    return t

def build_pdf(name, story, marking=None):
    def deco(c, d):
        c.saveState(); c.setFont("Helvetica-Bold", 10)
        if marking:
            c.drawCentredString(A4[0] / 2, A4[1] - 25, marking); c.drawCentredString(A4[0] / 2, 20, marking)
        else:
            c.setFont("Helvetica", 8); c.drawCentredString(A4[0] / 2, 20, f"{name} - page {d.page}")
        c.restoreState()
    SimpleDocTemplate(str(OUT / name), pagesize=A4, topMargin=55, bottomMargin=50).build(story, onFirstPage=deco, onLaterPages=deco)

def cover(title, docno, rev, date):
    s = [P(title, T), P(f"Document No: {docno}")]
    if rev: s.append(P(f"Revision: {rev}"))
    return s + [P(f"Date: {date}")]

# ---------- Equipment specification (Rev A / Rev B) ----------
REQS = {
 "3.1 Functional Requirements": [
  "The PSU shall accept a nominal input voltage of 24 V DC.",
  "The PSU shall operate over an input voltage range of 18 V DC to 32 V DC.",
  "The PSU shall provide a regulated 12 V DC output of up to 8 A.",
  "The PSU shall provide a regulated 5 V DC output of up to 6 A.",
  "The PSU shall achieve an efficiency of not less than 88 percent at full load.",
  "The PSU shall provide over-current protection on all outputs.",
  "The PSU shall assert a power-good signal within 100 ms of output stabilisation.",
  "The PSU shall withstand reverse input polarity without damage."],
 "3.2 Environmental Requirements": [
  "The PSU shall operate at ambient temperatures from {tmin} °C to {tmax} °C.",
  "The PSU shall survive storage temperatures from -55 °C to 105 °C.",
  "The PSU shall operate at altitudes up to 5000 m.",
  "The PSU shall meet the humidity requirements of MIL-STD-810H Method 507.6.",
  "The PSU shall withstand vibration in accordance with MIL-STD-810H Method 514.8.",
  "The PSU shall withstand a shock of 40 g, 11 ms half-sine.",
  "The PSU shall provide an ingress protection rating of IP65."],
 "3.3 Electromagnetic Compatibility": [
  "The PSU shall comply with MIL-STD-461G CE102 conducted emission limits.",
  "The PSU shall comply with MIL-STD-461G RS103 radiated susceptibility limits."],
 "3.4 Physical Requirements": [
  "The PSU mass shall not exceed {mass} kg.",
  "The PSU dimensions shall not exceed 220 x 150 x 80 mm.",
  "The PSU shall use a MIL-DTL-38999 Series III connector for J1.",
  "The PSU shall be marked with P/N 7741-0100."],
 "3.5 Reliability and Maintainability": [
  "The PSU shall achieve an MTBF of not less than {mtbf} hours.",
  "The PSU shall have a mean time to repair not exceeding 30 minutes.",
  "The PSU shall allow cooling fan replacement without removing the unit from the rack."]}

def section(key, v):
    num = key.split()[0]
    return [P(key, H)] + [P(f"{num}.{i} " + t.format(**v)) for i, t in enumerate(REQS[key], 1)]

def spec(rev, v, date):
    s = cover("Power Supply Unit PSU-500 Equipment Specification", "EQ-SPEC-1001", rev, date)
    s += [P("1 Scope", H), P("This specification defines the requirements for the PSU-500 power supply unit."),
          P("2 Applicable Documents", H), P("MIL-STD-810H, MIL-STD-461G."), PageBreak(), P("3 Requirements", H)]
    s += section("3.1 Functional Requirements", v) + [PageBreak()]
    s += section("3.2 Environmental Requirements", v) + section("3.3 Electromagnetic Compatibility", v) + [PageBreak()]
    s += section("3.4 Physical Requirements", v) + section("3.5 Reliability and Maintainability", v) + [PageBreak()]
    s += [P("4 Summary of Limits (Table 1)", H), grid([
        ["Parameter", "Limit", "Requirement"],
        ["Operating temperature (min)", f"{v['tmin']} °C", "3.2.1"], ["Operating temperature (max)", f"{v['tmax']} °C", "3.2.1"],
        ["Input voltage range", "18-32 V DC", "3.1.2"], ["Mass (max)", f"{v['mass']} kg", "3.4.1"],
        ["MTBF (min)", f"{v['mtbf']} h", "3.5.1"], ["Ingress protection", "IP65", "3.2.7"]])]
    return s

VA = dict(tmin=-40, tmax=85, mass="4.2", mtbf="20,000")
VB = dict(tmin=-45, tmax=90, mass="4.0", mtbf="25,000")
build_pdf("EQ-SPEC-1001_RevA.pdf", spec("A", VA, "2024-06-01"))
build_pdf("EQ-SPEC-1001_RevB.pdf", spec("B", VB, "2025-02-10"))

# ---------- ECN (DOCX) ----------
d = Document()
d.add_heading("Engineering Change Notice", 0)
for l in ["ECN Number: ECN-2025-014", "Date: 2025-02-10",
          "Title: Update of PSU-500 environmental and reliability limits",
          "Reason: Qualification testing showed margin beyond the Revision A limits.",
          "Description: This ECN changes the operating temperature range, mass limit and MTBF of the PSU-500, "
          "moving EQ-SPEC-1001 from Revision A to Revision B."]:
    d.add_paragraph(l)
d.add_page_break()
d.add_heading("Changes", 1)
rows = [("Parameter", "Revision A", "Revision B", "Requirement"),
        ("Maximum operating temperature", "85 °C", "90 °C", "3.2.1"),
        ("Minimum operating temperature", "-40 °C", "-45 °C", "3.2.1"),
        ("Maximum mass", "4.2 kg", "4.0 kg", "3.4.1"),
        ("Minimum MTBF", "20,000 hours", "25,000 hours", "3.5.1")]
t = d.add_table(rows=len(rows), cols=4); t.style = "Table Grid"
for i, r in enumerate(rows):
    for j, x in enumerate(r): t.cell(i, j).text = x
d.add_heading("Affected Documents", 1)
d.add_paragraph("EQ-SPEC-1001 Revision A (superseded), EQ-SPEC-1001 Revision B (effective), TR-2025-031.")
d.save(OUT / "ECN-2025-014.docx")

# ---------- Test report (against Rev B) ----------
build_pdf("TR-2025-031.pdf",
    cover("PSU-500 Qualification Test Report", "TR-2025-031", None, "2025-03-18") +
    [P("Unit under test: PSU-500, P/N 7741-0100."), P("Requirements baseline: EQ-SPEC-1001 Revision B."),
     P("Overall result: FAIL (1 of 5 tests failed)."), PageBreak(), P("2 Test Results", H),
     grid([["Test ID", "Requirement", "Conditions", "Result"],
           ["T-01", "3.2.1", "High temperature, 90 °C, 4 h", "PASS"],
           ["T-02", "3.2.1", "Low temperature, -45 °C, 4 h", "PASS"],
           ["T-03", "3.2.5", "Vibration, MIL-STD-810H Method 514.8", "PASS"],
           ["T-04", "3.2.4", "Humidity, MIL-STD-810H Method 507.6", "FAIL"],
           ["T-05", "3.4.1", "Mass measurement, 3.97 kg", "PASS"]])])

# ---------- Maintenance manual ----------
build_pdf("MM-3300_RevA.pdf",
    cover("PSU-500 Maintenance Manual", "MM-3300", "A", "2024-07-15") + [PageBreak(), P("1 Warnings", H),
     P("WARNING: Disconnect input power and wait 5 minutes before opening the enclosure. Capacitors may retain a hazardous charge."),
     P("WARNING: Wear ESD protection when handling internal assemblies."),
     P("CAUTION: Do not operate the unit without the cooling fan installed."), PageBreak(),
     P("2 Cooling Fan Replacement", H), P("Step 1. Disconnect connector J1."),
     P("Step 2. Remove the four fan retaining screws."), P("Step 3. Remove the fan assembly, P/N 7741-0032."),
     P("Step 4. Install the new fan assembly, P/N 7741-0032."),
     P("Step 5. Torque the fan retaining screws to 1.2 N·m."), P("Step 6. Reconnect J1 and run the self-test."),
     PageBreak(), P("3 Parts List", H),
     grid([["P/N", "Description", "Qty"], ["7741-0032", "Cooling fan assembly", "1"],
           ["7741-0118", "Input fuse, 10 A", "1"], ["7741-0204", "Gasket kit", "1"]])])

# ---------- Marked document ----------
build_pdf("ICD-5001_RevA.pdf",
    cover("PSU-500 Interface Control Document", "ICD-5001", "A", "2024-09-01") +
    [P("1 Scope", H), P("The PSU-500 shall communicate with the host over RS-422 at 115200 baud."), PageBreak(),
     P("2 Connector J1 Pin Assignment", H),
     grid([["Pin", "Signal", "Direction"], ["1", "+24V_IN", "In"], ["2", "GND", "-"], ["3", "TX+", "Out"],
           ["4", "TX-", "Out"], ["5", "RX+", "In"], ["6", "RX-", "In"]])], marking="RESTRICTED")

# ---------- Scanned (image-only) PDF ----------
lines = ["TM-SYN-0001  HYDRAULIC PUMP MAINTENANCE", "", "WARNING: RELIEVE SYSTEM PRESSURE BEFORE",
         "DISCONNECTING ANY HOSE.", "", "TORQUE THE PUMP COVER BOLTS TO 35 FT-LB.",
         "INSPECT THE SEALS EVERY 200 HOURS OF OPERATION."]
img = Image.new("RGB", (1654, 2339), "white"); dr = ImageDraw.Draw(img)
try: font = ImageFont.truetype("arial.ttf", 50)
except OSError: font = ImageFont.load_default()
for i, ln in enumerate(lines): dr.text((120, 150 + i * 90), ln, fill="black", font=font)
png = OUT / "_tmp.png"; img.save(png)
pdf = fitz.open(); pg = pdf.new_page(width=595, height=842); pg.insert_image(pg.rect, filename=str(png))
pdf.save(OUT / "SCAN-TM-0001.pdf"); pdf.close(); png.unlink()
print("Created:", *sorted(p.name for p in OUT.iterdir()), sep="\n  ")