
import json
import sys
from netCDF4 import Dataset
from reportlab.lib.pagesizes import landscape, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
import re
from reportlab.lib import colors
import numpy as np

from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle



# Load JSON metadata
def load_json(json_file):
    with open(json_file, 'r') as f:
        return json.load(f)

# Type mapping between JSON spec and Python/netCDF types
type_map = {
    "string": str,
    "int": (np.int32, np.int32),
    "double": (np.float64, np.float64),
    "float": (np.float32, np.float32),
    "uint8":(np.uint8, np.uint8)
}

def check_global_attributes(nc, metadata, results, section_summaries):
    section_name = "Global_Attributes"
    pass_count = fail_mandatory_count = not_used_count = 0

    for attr in metadata.get("Global_Attributes", []):
        name = attr["name"]
        dtype = type_map.get(attr["type"], str)
        requirement = attr["applicability"]

        available = hasattr(nc, name)
        actual_dtype = type(getattr(nc, name)) if available else None
        expected_dtype = attr["type"]

        value = getattr(nc, name) if available else None
        expected_value = metadata.get("allowed_values", {}).get(name)

        status = "pass"
        if not available and requirement.lower() == "mandatory":
            status = "fail_mandatory"
        elif not available:
            status = "not_used"
        elif available:
            if not isinstance(value, dtype):
                status = "fail_mandatory" if requirement.lower() == "mandatory" else "fail_optional"
            elif expected_value and value not in expected_value:
                status = "fail_mandatory" if requirement.lower() == "mandatory" else "fail_optional"

        if status == "pass":
            pass_count += 1
        elif status == "fail_mandatory":
            fail_mandatory_count += 1
        elif status == "fail_optional":
            not_used_count += 1



        results.append([section_name, name, "Yes" if available else "No", expected_dtype, str(actual_dtype.__name__ if actual_dtype else None), str(expected_value), str(value), requirement, status])

    section_summaries[section_name] = (pass_count, fail_mandatory_count, not_used_count)


def check_variables(nc, metadata, group_name, results, section_summaries):
    pass_count = fail_mandatory_count = not_used_count = 0

    for var in metadata.get(group_name, []):
        name = var["name"]
        dtype = type_map.get(var.get("type", "string"), str)
        requirement = var.get("applicability", "Optional")

        available = name in nc.variables
        ncvar = nc.variables[name] if available else None
        actual_dtype = ncvar.dtype if available else None
        expected_dtype = var.get("type")
        value1 = ncvar.getValue() if available else None
        expected_value1 = metadata.get("allowed_values", {}).get(name)

        status = "pass"
        if not available and requirement.lower() == "mandatory":
            status = "fail_mandatory"
        elif not available:
            status = "not_used"
        elif available and dtype and not np.issubdtype(ncvar.dtype, np.dtype(dtype)):
            status = "fail_mandatory" if requirement.lower() == "mandatory" else "fail_optional"
        elif expected_value1 and value1 not in expected_value1:
                status = "fail_mandatory" if requirement.lower() == "mandatory" else "fail_optional"
        if status == "pass":
            pass_count += 1
        elif status == "fail_mandatory":
            fail_mandatory_count += 1
        elif status == "fail_optional":
            not_used_count += 1

        results.append([group_name, name, "Yes" if available else "No", expected_dtype, str(actual_dtype), str(expected_value1), str(value1), requirement, status])

        # Check attributes of variable
        for attr in var.get("attributes", []):
            aname = attr["attribute_name"]
            adtype = type_map.get(attr["attribute_datatype"], str)
            expected_value = attr.get("attribute_value")
            if expected_value is None:
               expected_value = metadata.get("allowed_values", {}).get(aname)

            a_available = hasattr(ncvar, aname) if available else False
            aval = getattr(ncvar, aname) if a_available else None
            actual_dtype = type(aval) if a_available else None

            astatus = "pass"
            if not a_available and requirement.lower() == "mandatory":
                astatus = "fail_mandatory"
            elif not a_available:
                astatus = "not_used"
            elif a_available:
                if not isinstance(aval, adtype):
                    astatus = "fail_mandatory" if requirement.lower() == "mandatory" else "fail_optional"
                elif expected_value and str(aval) not in expected_value:
                    if not re.match(expected_value, str(aval)):
                        astatus = "fail_mandatory" if requirement.lower() == "mandatory" else "fail_optional"

            if astatus == "pass":
                pass_count += 1
            elif astatus == "fail_mandatory":
                fail_mandatory_count += 1
            elif astatus == "fail_optional":
                not_used_count += 1

            results.append([f"{group_name}:{name}", aname, "Yes" if a_available else "No", attr["attribute_datatype"], str(actual_dtype.__name__ if actual_dtype else None), str(expected_value), str(aval), requirement, astatus])

    section_summaries[group_name] = (pass_count, fail_mandatory_count, not_used_count)

def check_variables_group(nc_group, metadata, group_name, results, section_summaries, sweep_index=None):
    pass_count = fail_mandatory_count = not_used_count = 0

    for var in metadata.get(group_name, []):
        name = var["name"]

        # Handle sweep_<n> placeholder
        if sweep_index is not None and "sweep_<n>" in name:
            name = name.replace("<n>", str(sweep_index))

        # If variable path has subgroup (e.g., radar_parameters/beam_width_h)
        path_parts = name.split("/")
        if sweep_index is not None and path_parts[0].startswith("sweep_"):
            path_parts = path_parts[1:]
        target_group = nc_group
        for part in path_parts[:-1]:
            if part in target_group.groups:
                target_group = target_group.groups[part]
            else:
                target_group = None
                break
        var_name = path_parts[-1]

        available = target_group is not None and var_name in target_group.variables
        ncvar = target_group.variables[var_name] if available else None

        dtype = type_map.get(var.get("type", "string"), str)
        expected_dtype = var.get("type")
        requirement = var.get("applicability", "Optional")

        actual_dtype = ncvar.dtype if available else None
        # Safe extraction of representative value
        value1 = None
        if available:
            try:
                if ncvar.shape == ():  # scalar
                    value1 = ncvar.getValue()
                else:  # array
                    value1 = ncvar[0].item() if hasattr(ncvar[0], "item") else ncvar[0]
            except Exception:
                value1 = None
        if sweep_index is not None and "sweep_"+str(sweep_index) in name:
            nametr = name.replace(str(sweep_index),"<n>")

            expected_value1 = metadata.get("allowed_values", {}).get(nametr)
        else:
            expected_value1 = metadata.get("allowed_values", {}).get(name)


        status = "pass"
        if not available and requirement.lower() == "mandatory":
            status = "fail_mandatory"
        elif not available:
            status = "not_used"
        elif available and dtype and not np.issubdtype(ncvar.dtype, np.dtype(dtype)):
            status = "fail_mandatory" if requirement.lower() == "mandatory" else "fail_optional"
        elif expected_value1 and value1 not in expected_value1:
            status = "fail_mandatory" if requirement.lower() == "mandatory" else "fail_optional"

        if status == "pass":
            pass_count += 1
        elif status == "fail_mandatory":
            fail_mandatory_count += 1
        elif status == "fail_optional":
            not_used_count += 1

        results.append([group_name, name, "Yes" if available else "No", expected_dtype, str(actual_dtype), str(expected_value1), str(value1), requirement, status])

        # Check attributes of variable
        for attr in var.get("attributes", []):
            aname = attr["attribute_name"]
            adtype = type_map.get(attr["attribute_datatype"], str)
            expected_value = attr.get("attribute_value")
            if expected_value is None:
                expected_value = metadata.get("allowed_values", {}).get(aname)

            a_available = hasattr(ncvar, aname) if available else False
            aval = getattr(ncvar, aname) if a_available else None
            actual_dtype = type(aval) if a_available else None

            astatus = "pass"
            if not a_available and requirement.lower() == "mandatory":
                astatus = "fail_mandatory"
            elif not a_available:
                astatus = "not_used"
            elif a_available:
                if not isinstance(aval, adtype):
                    astatus = "fail_mandatory" if requirement.lower() == "mandatory" else "fail_optional"
                elif expected_value and str(aval) not in expected_value:
                    if not re.match(str(expected_value), str(aval)):
                        astatus = "fail_mandatory" if requirement.lower() == "mandatory" else "fail_optional"

            if astatus == "pass":
                pass_count += 1
            elif astatus == "fail_mandatory":
                fail_mandatory_count += 1
            elif astatus == "fail_optional":
                not_used_count += 1

            results.append([f"{group_name}:{name}", aname, "Yes" if a_available else "No", attr["attribute_datatype"], str(actual_dtype.__name__ if actual_dtype else None), str(expected_value), str(aval), requirement, astatus])

    section_summaries[group_name] = (pass_count, fail_mandatory_count, not_used_count)


def check_dataset_group(nc_group, metadata, group_name, results,section_summaries,sweep_index=None):

    pass_count = fail_mandatory_count = not_used_count = 0
    for var in metadata.get(group_name, []):
        name = var["name"]

        # Handle sweep_<n> placeholder
        if sweep_index is not None and "sweep_<n>" in name:
            name = name.replace("<n>", str(sweep_index))

        # If variable path has subgroup (e.g., radar_parameters/beam_width_h)
        path_parts = name.split("/")
        if sweep_index is not None and path_parts[0].startswith("sweep_"):
            path_parts = path_parts[1:]
        target_group = nc_group
        for part in path_parts[:-1]:
            if part in target_group.groups:
                target_group = target_group.groups[part]
            else:
                target_group = None
                break
        var_name = path_parts[-1]

        available = target_group is not None and var_name in target_group.variables
        ncvar = target_group.variables[var_name] if available else None
        requirement = "dataset"



        status = "pass"
        if not available:
            status = "not_used"



        results.append([group_name, name, "Yes" if available else "No", None, None, None, None, requirement, status])

        # Check attributes of variable
        if available:

            for attr in var.get("attributes", []):
                aname = attr["attribute_name"]
                adtype = type_map.get(attr.get("attribute_datatype"), str) if available else None

                expected_value = attr.get("attribute_value")
                rbs = attr["attribute_applicability"]
                if expected_value is None:
                    expected_value = metadata.get("allowed_values", {}).get(aname)

                a_available = hasattr(ncvar, aname) if available else False
                aval = getattr(ncvar, aname) if a_available else None
                actual_dtype = type(aval) if a_available else None

                astatus = "pass"
                if not a_available and rbs.lower() == "mandatory":
                    astatus = "fail_mandatory"
                elif not a_available:
                    astatus = "not_used"
                elif a_available:
                    if not isinstance(aval, adtype):
                        astatus = "fail_mandatory" if rbs.lower() == "mandatory" else "not_used"
                    elif expected_value and str(aval) not in expected_value:
                        if not re.match(str(expected_value), str(aval)):
                            astatus = "fail_mandatory" if rbs.lower() == "mandatory" else "not_used"
                if astatus == "pass":
                      pass_count += 1
                elif astatus == "fail_mandatory":
                      fail_mandatory_count += 1
                elif astatus == "fail_optional":
                      not_used_count += 1


                results.append([f"{group_name}:{name}", aname, "Yes" if a_available else "No", attr.get("attribute_datatype"), str(actual_dtype), str(expected_value), str(aval), rbs, astatus])

    section_summaries[group_name] = (pass_count, fail_mandatory_count, not_used_count)



def generate_pdf(results, output_file, section_summaries,results_data, nc_file):
    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(output_file, pagesize=landscape(A4),
                            leftMargin=20, rightMargin=20, topMargin=20, bottomMargin=20)
    story = []


    # Title
    story.append(Paragraph("WMO FM 301 NetCDF Validation Report of "+ nc_file, styles['Heading1']))
    story.append(Spacer(1, 12))

    # Section summaries
    story.append(Paragraph("Section Summaries", styles['Heading2']))
    summary_data = [["Section", "Pass", "Fail Mandatory", "Fail optional"]]
    total_pass = total_fail_mand = total_fail_opt = 0
    for section, (p, fm, fo) in section_summaries.items():
        summary_data.append([section, str(p), str(fm), str(fo)])
        total_pass += p
        total_fail_mand += fm
        total_fail_opt += fo
    summary_data.append(["Overall", str(total_pass), str(total_fail_mand), str(total_fail_opt)])
    summary_table = Table(summary_data, repeatRows=1, colWidths=[150, 100, 120, 120])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.grey),
        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.black),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE')
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 20))



    # Detailed results table
    story.append(Paragraph("Detailed Results", styles['Heading2']))

    # Column widths dynamically scaled to page width
    page_width, page_height = landscape(A4)
    left_margin = right_margin = 20
    available_width = page_width - left_margin - right_margin
    rel_widths = [1, 1.5, 0.7, 1, 1, 1.2, 1.2, 1, 1]  # relative widths for 9 columns
    total_rel = sum(rel_widths)
    col_widths = [available_width * w / total_rel for w in rel_widths]

    # Small font style for table content
    small_style = ParagraphStyle('small', fontSize=8, leading=10)

    table_data = [["Group", "Name", "Available", "Expected Dtype", "Actual Dtype",
                   "Expected Value", "Actual Value", "Requirement", "Result"]]

    for row in results:
        status = row[-1]
        display_row = []
        for cell in row:
            cell_text = str(cell) if cell is not None else ""
            # Wrap text in small font
            if status == "fail_mandatory":
                display_row.append(Paragraph(f"<font color='red'>{cell_text}</font>", small_style))
            elif status == "not_used":
                display_row.append(Paragraph(f"<font color='blue'>{cell_text}</font>", small_style))
            elif status == "fail_optional":
                display_row.append(Paragraph(f"<font color='red'>{cell_text}</font>", small_style))
            else:
                display_row.append(Paragraph(cell_text, small_style))
        table_data.append(display_row)



    table = Table(table_data, repeatRows=1, colWidths=col_widths, hAlign='LEFT')
    table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.grey),
        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.black),
        ('WORDWRAP', (0,0), (-1,-1), 'CJK')  # wrap long text
    ]))

    story.append(table)

    story.append(Spacer(1, 20))



    # Detailed results table
    story.append(Paragraph("Datasets", styles['Heading2']))

    # Column widths dynamically scaled to page width
    page_width, page_height = landscape(A4)
    left_margin = right_margin = 20
    available_width = page_width - left_margin - right_margin
    rel_widths = [1, 1.5, 0.7, 1, 1, 1.2, 1.2, 1, 1]  # relative widths for 9 columns
    total_rel = sum(rel_widths)
    col_widths = [available_width * w / total_rel for w in rel_widths]

    # Small font style for table content
    small_style = ParagraphStyle('small', fontSize=8, leading=10)

    table_data1 = [["Group", "Name", "Available", "Expected Dtype", "Actual Dtype",
                   "Expected Value", "Actual Value", "Requirement", "Result"]]



    for row in results_data:
        status = row[-1]
        display_row = []
        for cell in row:
            cell_text = str(cell) if cell is not None else ""
            # Wrap text in small font
            if status == "not_used":
                display_row.append(Paragraph(f"<font color='blue'>{cell_text}</font>", small_style))
            elif status == "fail_mandatory":
                display_row.append(Paragraph(f"<font color='red'>{cell_text}</font>", small_style))
            elif status == "fail_optional":
                display_row.append(Paragraph(f"<font color='red'>{cell_text}</font>", small_style))
            else:
                display_row.append(Paragraph(cell_text, small_style))
        table_data1.append(display_row)

    table1 = Table(table_data1, repeatRows=1, colWidths=col_widths, hAlign='LEFT')
    table1.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.grey),
        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.black),
        ('WORDWRAP', (0,0), (-1,-1), 'CJK')  # wrap long text
    ]))

    story.append(table1)
    story.append(Spacer(1, 200))  # Push footnote toward the bottom
    story.append(Paragraph("Measurements, Instrumentation and Traceability Section, WIGOS Division, WMO Secretariat ", styles['Normal']))
    doc.build(story)

def generate_pdf_used(results, output_file, section_summaries,results_data, nc_file):
    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(output_file, pagesize=landscape(A4),
                            leftMargin=20, rightMargin=20, topMargin=20, bottomMargin=20)
    story = []


    # Title
    story.append(Paragraph("WMO FM 301 NetCDF Validation Report of "+ nc_file, styles['Heading1']))
    story.append(Spacer(1, 12))

    # Section summaries
    story.append(Paragraph("Section Summaries", styles['Heading2']))
    summary_data = [["Section", "Pass", "Fail Mandatory", "Fail optional"]]
    total_pass = total_fail_mand = total_fail_opt = 0
    for section, (p, fm, fo) in section_summaries.items():
        summary_data.append([section, str(p), str(fm), str(fo)])
        total_pass += p
        total_fail_mand += fm
        total_fail_opt += fo
    summary_data.append(["Overall", str(total_pass), str(total_fail_mand), str(total_fail_opt)])
    summary_table = Table(summary_data, repeatRows=1, colWidths=[150, 100, 120, 120])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.grey),
        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.black),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE')
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 20))



    # Detailed results table
    story.append(Paragraph("Detailed Results", styles['Heading2']))

    # Column widths dynamically scaled to page width
    page_width, page_height = landscape(A4)
    left_margin = right_margin = 20
    available_width = page_width - left_margin - right_margin
    rel_widths = [1, 1.5, 0.7, 1, 1, 1.2, 1.2, 1, 1]  # relative widths for 9 columns
    total_rel = sum(rel_widths)
    col_widths = [available_width * w / total_rel for w in rel_widths]

    # Small font style for table content
    small_style = ParagraphStyle('small', fontSize=8, leading=10)

    table_data = [["Group", "Name", "Available", "Expected Dtype", "Actual Dtype",
                   "Expected Value", "Actual Value", "Requirement", "Result"]]

    for row in results:
        status = row[-1]
        display_row = []
        if status == "not_used":
            continue
        for cell in row:
            cell_text = str(cell) if cell is not None else ""
            # Wrap text in small font
            if status == "fail_mandatory":
                display_row.append(Paragraph(f"<font color='red'>{cell_text}</font>", small_style))
            elif status == "fail_optional":
                display_row.append(Paragraph(f"<font color='red'>{cell_text}</font>", small_style))
            elif status == "pass":
                display_row.append(Paragraph(cell_text, small_style))

        table_data.append(display_row)



    table = Table(table_data, repeatRows=1, colWidths=col_widths, hAlign='LEFT')
    table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.grey),
        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.black),
        ('WORDWRAP', (0,0), (-1,-1), 'CJK')  # wrap long text
    ]))

    story.append(table)

    story.append(Spacer(1, 20))



    # Detailed results table
    story.append(Paragraph("Datasets", styles['Heading2']))

    # Column widths dynamically scaled to page width
    page_width, page_height = landscape(A4)
    left_margin = right_margin = 20
    available_width = page_width - left_margin - right_margin
    rel_widths = [1, 1.5, 0.7, 1, 1, 1.2, 1.2, 1, 1]  # relative widths for 9 columns
    total_rel = sum(rel_widths)
    col_widths = [available_width * w / total_rel for w in rel_widths]

    # Small font style for table content
    small_style = ParagraphStyle('small', fontSize=8, leading=10)

    table_data1 = [["Group", "Name", "Available", "Expected Dtype", "Actual Dtype",
                   "Expected Value", "Actual Value", "Requirement", "Result"]]



    for row in results_data:
        status = row[-1]
        display_row = []
        if status == "not_used":
            continue
        for cell in row:
            cell_text = str(cell) if cell is not None else ""
            # Wrap text in small font
            if status == "fail_mandatory":
                display_row.append(Paragraph(f"<font color='red'>{cell_text}</font>", small_style))
            elif status == "fail_optional":
                display_row.append(Paragraph(f"<font color='red'>{cell_text}</font>", small_style))
            elif status == "pass":
                display_row.append(Paragraph(cell_text, small_style))
        table_data1.append(display_row)

    table1 = Table(table_data1, repeatRows=1, colWidths=col_widths, hAlign='LEFT')
    table1.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.grey),
        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.black),
        ('WORDWRAP', (0,0), (-1,-1), 'CJK')  # wrap long text
    ]))

    story.append(table1)
    story.append(Spacer(1, 200))  # Push footnote toward the bottom
    story.append(Paragraph("Measurements, Instrumentation and Traceability Section, WIGOS Division, WMO Secretariat ", styles['Normal']))
    doc.build(story)






def validate(json_file, nc_file, pdf_file, Sopt):
    metadata = load_json(json_file)
    nc = Dataset(nc_file, 'r')
    results = []
    section_summaries = {}
    results_data = []


    check_global_attributes(nc, metadata, results, section_summaries)
    check_variables(nc, metadata, "Global_Ancillary_variables", results, section_summaries)


    # Check sweep groups dynamically
    if Sopt == "f":
        if "sweep_variables" in metadata:
            sweep_groups = [g for g in nc.groups.keys() if g.startswith("sweep_")]
            for i, gname in enumerate(sorted(sweep_groups)):
                sweep_group = nc.groups[gname]
                check_variables_group(sweep_group, metadata, "sweep_variables", results, section_summaries, sweep_index=i)
                check_dataset_group(sweep_group, metadata, "data_variables", results_data,section_summaries, sweep_index=i)
    elif Sopt == "o":
        if "sweep_variables" in metadata:
                sweep_group = nc.groups["sweep_0"]
                check_variables_group(sweep_group, metadata, "sweep_variables", results, section_summaries, sweep_index=0)
                check_dataset_group(sweep_group, metadata, "data_variables", results_data,section_summaries, sweep_index=0)
    #Check radar_parameters subgroup
    if "radar_parameters" in metadata:
        check_variables_group(nc, metadata, "radar_parameters", results, section_summaries)
    if "radar_calibration" in metadata:
        check_variables_group(nc, metadata, "radar_calibration", results, section_summaries)

    nc.close()
    with open('results.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=4)
    generate_pdf_used(results, pdf_file, section_summaries,results_data,nc_file)
    print(f"✅ Validation complete. Report saved to {pdf_file}")

if __name__ == "__main__":
    if len(sys.argv) < 3 or len(sys.argv) > 4:
        print("Usage: python fm301_cc.py <file.nc> <report.pdf> ")
        sys.exit(1)
    json_file = "cf_radial_metadata_Final.json"
    nc_file, pdf_file = sys.argv[1], sys.argv[2]
    Sopt = sys.argv[3].lower() if len(sys.argv) == 4 else "o"  # default = "f"

    if Sopt not in ("f","o"):
        print("Usage: python fm301_cc.py <file.nc> <report.pdf> ")
        sys.exit(1)
    try:
      validate(json_file, nc_file, pdf_file, Sopt)
    except Exception:
      print("Invalid input file, Please use FM301 Netcdf file for compliance check")