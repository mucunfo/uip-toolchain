"""Run once to generate config_sample.xlsx fixture."""
from pathlib import Path
import openpyxl

FIX = Path(__file__).parent
wb = openpyxl.Workbook()
ws = wb.active
ws.title = "Settings"
ws.append(["Name", "Value", "Description"])
ws.append(["KeyA", "valueA", "desc"])
ws.append(["KeyB", "valueB", "desc"])
wb.create_sheet("Constants")
wb["Constants"].append(["Name", "Value", "Description"])
wb["Constants"].append(["ExceptionMsgX", "Erro X", ""])
wb.save(FIX / "config_sample.xlsx")
print("created config_sample.xlsx")
