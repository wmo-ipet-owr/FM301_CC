# FM301_CC

Repository for the compliance checker on FM301 format.

The repository has two files: **fm301_cc.py** and **cf_radial_metadata_Final.json**.  
The **cf_radial_metadata_Final.json** file contains the FM301 structure, including editorial changes proposed as amendments. It includes both **mandatory** and **optional** metadata parameters.

The FM301_CC script generates a PDF report that checks:

### Mandatory parameters
- Availability of all mandatory metadata  
- Correct datatype  
- Correct values if predefined  

### Optional parameters
- Only the **used** optional metadata are checked for datatype and values  
- Optional parameters not used are ignored

### Report Structure
1. **Section summaries**
   - **Pass** – All mandatory and used optional parameters have correct datatype and values  
   - **Fail Mandatory** – Mandatory parameters missing or with incorrect datatype/values  
   - **Fail Optional** – Used optional parameters with incorrect datatype/values  

2. **Detailed Results**
   - **Mandatory parameters:** Availability, expected datatype (and actual), expected values (and actual)  
   - **Optional parameters:** Used optional parameters with expected datatype (and actual), expected values (and actual)

3. **Variable Checks**
   - Only variables **used in the dataset** are checked  
   - Missing variables are **not flagged**, as it depends on radar Level II product definition

You can refer to the FM301 format for all mandatory, optional, and supported variables:  
- [FM301 Radial Profile (GitHub)](https://github.com/wmo-im/cf-extensions-profiles/blob/main/c3-fm301-2022-radial.adoc)  
- [FM301 Documentation (WMO Library)](https://library.wmo.int/idurl/4/35625)

---
## To run in Google colab
Upload the script, json file and the file to be tested for compliance in the folder

## 📦 Installation

Install required dependencies:

```bash
!pip install netCDF4 reportlab
```

## ▶️ Run the Script

```bash
!python fm301_cc.py ODIM.nc validation_report.pdf
```

**ODIM.nc** is the file to be checked and **validation_report.pdf** is the file name of the pdf report. **cf_radial_metadata_Final.json** file is required for the script to be executed and needs to be placed in the same folder location.
