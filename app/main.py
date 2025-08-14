from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Optional
import re
import json

app = FastAPI(
    title="Obsolete SAP Report Detector (SAP Note 2480067)"
)

# List of obsolete reports
OBSOLETE_REPORTS = [
    "/ATL/PCN874", "/BGLOCS/FI_AA_TAX_DEPR", "/BGLOCS/FI_CFS", "/BGLOCS/FI_FIXASSREP01",
    "/BGLOCS/FI_RFASLD20", "/CCEE/HRFI_EC_TAX", "/CCEE/HRFI_RFUVDE00", "/CCEE/HR_GL_ACCOUNT_STATEMENT",
    "/CCEE/HR_OPZ_STAT_1", "/CCEE/ROFI_394_2016", "/CCEE/ROFIRFUVDE2017", "/CCEE/ROFI_VIES_390_XML",
    "/CCEE/ROFITRIAL", "/CCEE/RO_ACHART", "/CCEE/RSFIAA_TAX_DEPR_GROUP", "/CCEE/SIFIDDV1",
    "/CCEE/SIFI_EXPORT_GL_LINE", "/CCEE/SIFI_KRD", "/CCEE/SIFI_POBOTI1", "/CCEE/SIFI_POBOTI3",
    "/CCEE/SIFI_RFASLM00_SI", "/CCEE/SIFI_SFR", "/SAPTR/KDVBaBs", "CL_WHT_AT", "CO_WHT_INCOME_DCL",
    "CO_WHT_VAT_DCL", "FITR_INVTRY", "FOT_B2A_ADMIN", "J_1AFONR", "J_1AF205", "J_1AF217", "J_1AF317",
    "J_1GCL000", "J_1GFPAREPORT", "J_1GGL000", "J_1GTBDE0", "J_1GTBGL0", "J_1GTBKR0", "J_1GVL000",
    "J_3RFFORM4", "J_3RF_BUY_BOOK_03", "J_3RF_REGISTERS", "J_3RF_REGINV", "J_3RF_SELL_BOOK_02",
    "J_3RF_TAX_REPORT", "J_3RF_TAX_XML_EXPORT", "J_3RF_VAT_CLARIF_REQUEST", "J_3RM_RN_OPERATIONS",
    "J_3RVATDECL", "J_3R_PTAX_DECL", "J_3R_TTAX_DECL", "J_CL_BALANCE_SHEET", "RAIDSG_CAP_ALLOW",
    "RAIDSG_CAP_RETIRE", "RAITAR01", "RAITAR02", "RAIDIT_DEPR", "RFASLD02", "RFASLD11B", "RFASLD12",
    "RFASLD15", "RFASLD20", "RFBILA00", "RFCLLIB01", "RFCLLIB01_PE", "RFCLLIB02", "RFCLLIB03_PE",
    "RFCLLIB04_PE", "RFGLKR00", "RFIDHU_AUDIT_REPORT", "RFIDHU_DSP", "RFIDMXFORMAT29", "RFIDPL07",
    "RFIDPL10", "RFIDPL15", "RFIDYYWT", "RFITEMAR_NO", "RFITEMAP_NO", "RFITEMGL_NO", "RFQSCI01",
    "RFUMSV00", "RFUMSV45R", "RFUMSV49R", "RFUSVB10", "RFUTAX00", "RFUVDE00", "RFVEPBOOK", "RFVESBOOK",
    "RPFIEG_TXCLR", "RPFIEG_TXREM", "RPFIFR_OVERDUE_INV", "RPFIGLMX_AUXACCOUNTING", "RPFIGLMX_EACCOUNTING",
    "RPFIGLMX_JE_DETAILS", "RPFIKZ_VATRET", "RPFISKEVAT", "RPFIWTAR_SIRE_SICORE", "RPFIWTIT_CU",
    "RPFIWTQA_TAXR", "RPFIWTSA_CERT", "RPFIWTIN_QRETURNS", "RPFIAAPT_MAPAS_FISCAIS", "RPFIMY_GST",
    "TRIVAT", "TRSLIST"
]

# Regex to find any occurrence of obsolete reports
REPORT_RE = re.compile(
    rf"(?P<report>{'|'.join(re.escape(r) for r in OBSOLETE_REPORTS)})",
    re.IGNORECASE
)

class Unit(BaseModel):
    pgm_name: str
    inc_name: str
    type: str
    name: Optional[str] = None
    class_implementation: Optional[str] = None
    start_line: Optional[int] = None
    end_line: Optional[int] = None
    code: Optional[str] = ""

def report_comment(report: str) -> str:
    return f"Report {report} is obsolete in S4 HANA, migrated to DRC as per SAP Note 2480067"

def find_obsolete_report_usage(txt: str):
    matches = []
    seen_reports = set()  # track already found reports
    for m in REPORT_RE.finditer(txt):
        report = m.group("report")
        if report.lower() in seen_reports:
            continue  # skip duplicates
        seen_reports.add(report.lower())

        comment = report_comment(report)
        matches.append({
            "full": report,
            "report": report,
            "suggested_statement": comment,
            "span": m.span("report")
        })
    return matches

@app.post("/detect-obsolete-reports")
def detect_obsolete_reports(units: List[Unit]):
    results = []
    for u in units:
        src = u.code or ""
        matches = find_obsolete_report_usage(src)
        metadata = []

        for m in matches:
            metadata.append({
                "table": "None",
                "target_type": "Report",
                "target_name": m["report"],
                "start_char_in_unit": m["span"][0],
                "end_char_in_unit": m["span"][1],
                "used_fields": [],
                "ambiguous": False,
                "suggested_statement": m["suggested_statement"],  # Moved here
                "suggested_fields": None
            })

        obj = json.loads(u.model_dump_json())
        obj["mb_txn_usage"] = metadata
        results.append(obj)

    return results
