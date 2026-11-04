"""
Modification Plan Generator Module.

Analyzes natural-language modification instructions and outputs a structured execution plan.
Supports semantic value replacement (e.g. 'Change the employee name Rahul to Charan'),
cell-coordinate updates (e.g. 'Update cell B2 to 100'), duplicate removal, sorting, and PDF/TXT operations.
Does not generate or execute arbitrary Python code.
"""

import re
from typing import Dict, Any, Optional


def generate_structured_plan(instruction: str, filename: str) -> Dict[str, Any]:
    """
    Parses natural language modification instruction for TXT, XLSX, or PDF.
    Returns structured execution parameters.
    """
    ext = "." + filename.split(".")[-1].lower() if "." in filename else ""
    inst = instruction.strip()
    lower = inst.lower()

    plan: Dict[str, Any] = {
        "filename": filename,
        "format": ext,
        "action": "unknown",
        "parameters": {},
        "description": ""
    }

    # =========================================================
    # 1. TXT Plans
    # =========================================================
    if ext == ".txt":
        if "append" in lower or "add" in lower:
            quoted = re.findall(r'["\'](.*?)["\']', inst)
            text_to_add = quoted[0] if quoted else inst.split("append")[-1].replace("text", "").replace("notes:", "").replace("notes", "").strip()
            plan["action"] = "TXT_APPEND"
            plan["parameters"] = {"text": text_to_add}
            plan["description"] = f"Append text: '{text_to_add}' to {filename}."

        elif "replace" in lower or "change" in lower:
            quoted = re.findall(r'["\'](.*?)["\']', inst)
            if len(quoted) >= 2:
                plan["action"] = "TXT_REPLACE"
                plan["parameters"] = {"target": quoted[0], "replacement": quoted[1]}
                plan["description"] = f"Replace exact occurrences of '{quoted[0]}' with '{quoted[1]}'."
            else:
                # Regex pattern: replace X with Y or change X to Y (supports multi-word phrases)
                m = re.search(r"(?:replace|change)\s+(?:the\s+)?(?:text\s+)?(.+?)\s+(?:with|to)\s+(.+)$", inst, re.IGNORECASE)
                if m:
                    target_txt = m.group(1).strip().strip("'\"")
                    repl_txt = m.group(2).strip().strip("'\"").rstrip(".!?,")
                    plan["action"] = "TXT_REPLACE"
                    plan["parameters"] = {"target": target_txt, "replacement": repl_txt}
                    plan["description"] = f"Replace exact text '{target_txt}' with '{repl_txt}' in {filename}."
                else:
                    plan["action"] = "TXT_REPLACE"
                    plan["parameters"] = {"target": "", "replacement": ""}
                    plan["description"] = "Replace specified text."


        elif "delete" in lower or "remove" in lower:
            quoted = re.findall(r'["\'](.*?)["\']', inst)
            target = quoted[0] if quoted else ""
            plan["action"] = "TXT_DELETE"
            plan["parameters"] = {"target": target}
            plan["description"] = f"Delete exact text: '{target}' from {filename}."

    # =========================================================
    # 2. Excel Plans (.xlsx)
    # =========================================================
    elif ext == ".xlsx":
        # Check for duplicate removal
        if "duplicate" in lower:
            plan["action"] = "EXCEL_REMOVE_DUPLICATES"
            sheet_name = "Sheet1"
            quoted = re.findall(r'sheet\s*["\'](.*?)["\']', lower)
            if quoted:
                sheet_name = quoted[0]
            plan["parameters"] = {"sheet_name": sheet_name}
            plan["description"] = f"Remove duplicate rows from worksheet in {filename}."

        # Check for data sorting
        elif "sort" in lower:
            quoted = re.findall(r'by\s*["\'](.*?)["\']', lower)
            if not quoted:
                m_col = re.search(r"by\s+(?:column\s+)?([A-Za-z0-9_]+)", inst, re.IGNORECASE)
                col = m_col.group(1) if m_col else "ID"
            else:
                col = quoted[0]
            descending = ("descending" in lower or "desc" in lower)
            plan["action"] = "EXCEL_SORT"
            plan["parameters"] = {"sheet_name": "Sheet1", "column": col, "ascending": not descending}
            plan["description"] = f"Sort worksheet by column '{col}' in {'descending' if descending else 'ascending'} order."

        # Check for coordinate-based cell update (e.g. 'Update cell B5 to 90000')
        elif re.search(r"\b(?:cell\s+)?([A-Za-z]+[1-9][0-9]*)\b", inst):
            cell_match = re.search(r"\b(?:cell\s+)?([A-Za-z]+[1-9][0-9]*)\b", inst)
            coord = cell_match.group(1).upper()
            val_match = re.search(r"(?:to|with|value)\s+([^\s,]+)", inst, re.IGNORECASE)
            new_val = val_match.group(1) if val_match else "0"
            plan["action"] = "EXCEL_UPDATE_CELL"
            plan["parameters"] = {"sheet_name": "Sheet1", "coordinate": coord, "value": new_val}
            plan["description"] = f"Update cell {coord} to '{new_val}' in {filename}."

        # Check for value/name replacement (e.g. 'Change the employee name Rahul to Charan')
        else:
            # Pattern: change [the] [every / all / employee name / value / text] X to Y
            clean_inst = inst.rstrip(".!?, ")
            name_pattern = re.search(
                r"(?:change|update|replace)\s+(?:the\s+)?(?:every\s+|all\s+|employee\s+name\s+|name\s+|value\s+|entry\s+)?([A-Za-z0-9_\-]+)\s+(?:to|with)\s+([A-Za-z0-9_\-]+)",
                clean_inst,
                re.IGNORECASE
            )
            if name_pattern:
                old_val = name_pattern.group(1).strip()
                new_val = name_pattern.group(2).strip()
                match_all = ("all" in lower or "every" in lower)
                plan["action"] = "EXCEL_REPLACE_VALUE"
                plan["parameters"] = {
                    "target_value": old_val,
                    "replacement_value": new_val,
                    "match_all": match_all
                }
                plan["description"] = f"Change {'all occurrences of ' if match_all else ''}value '{old_val}' to '{new_val}' in {filename}."



    # =========================================================
    # 3. PDF Plans (.pdf)
    # =========================================================
    elif ext == ".pdf":
        if "annotate" in lower or "annotation" in lower or "stamp" in lower:
            quoted = re.findall(r'["\'](.*?)["\']', inst)
            if not quoted:
                m_txt = re.search(r"(?:text|annotation|stamp):\s*(.+)$", inst, re.IGNORECASE)
                note = m_txt.group(1).strip() if m_txt else "Approved"
            else:
                note = quoted[0]
            plan["action"] = "PDF_ANNOTATE"
            plan["parameters"] = {"page": 1, "text": note}
            plan["description"] = f"Add annotation text '{note}' to page 1 of {filename}."

        elif "extract" in lower or "page" in lower:
            pages = [int(p) for p in re.findall(r"\b\d+\b", inst)]
            plan["action"] = "PDF_EXTRACT_PAGES"
            plan["parameters"] = {"pages": pages or [1]}
            plan["description"] = f"Extract pages {pages or [1]} from {filename}."


    return plan
