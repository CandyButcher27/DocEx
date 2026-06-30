"""Build and cache the Axis Max Life GCL Premier LFQ template from the reference docx.

The reference .docx is a confidential blank form (gitignored). This script derives the
template's phash + signature phrases from it and pairs them with hand-authored field
specs, then saves the template YAML to template_store/.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from idp.builder import build_template
from idp.models import FieldSpec
from idp.render import load_first_page
from idp.store import save_template

REFERENCE = Path("proper_docs/GCL Premier_LFQ 1.docx")

FIELDS = [
    FieldSpec("group_policy_number", ["Group Policy Number"], "right", "text"),
    FieldSpec("group_policyholder_name",
              ["Group Policyholder Name", "Group Master Policy Name"], "right", "text"),
    FieldSpec("cust_emp_proposal_id",
              ["CUST/EMP ID/Proposal/Loan Application No", "Proposal/Loan Application No"],
              "right", "text"),
    FieldSpec("loan_type", ["Loan Type"], "right", "text"),
    FieldSpec("loan_account_no", ["Loan A/c No", "Loan Account No"], "right", "text",
              required=True),
    FieldSpec("date_first_disbursement", ["Date of First Loan disbursement"], "right", "date"),
    FieldSpec("loan_amount_sum_assured",
              ["Loan Amount/Sum Assured (in Rs)", "Loan Amount/Sum Assured", "Sum Assured"],
              "right", "number", required=True),
    FieldSpec("product_name", ["Product Name"], "right", "text"),
    FieldSpec("insured_member_name",
              ["Name of the Insured Member", "Name of Insured Member"], "right", "text",
              required=True),
    FieldSpec("date_of_birth",
              ["Date of Birth of Insured Member", "Date of Birth of Member"], "right", "date"),
    FieldSpec("pan_number", ["PAN Number"], "right", "pan"),
    FieldSpec("annual_income", ["Annual Income"], "right", "number"),
    FieldSpec("premium_amount", ["Premium Amount"], "right", "number"),
    FieldSpec("period_of_insurance", ["Period of Insurance"], "right", "number"),
    FieldSpec("mobile_no", ["Mobile No"], "right", "number"),
    FieldSpec("email_id", ["Email ID"], "right", "text"),
    FieldSpec("city", ["City"], "right", "text"),
    FieldSpec("state", ["State"], "right", "text"),
    FieldSpec("pin", ["PIN"], "right", "number"),
    FieldSpec("name_of_proposer", ["Name of Proposer"], "right", "text"),
]

SIGNATURE = [
    "Axis Max Life",
    "Group Credit Life Premier",
    "Member Enrolment Form",
    "Insured Member",
    "PAN Number",
    "Nominee",
    "Premium",
    "Loan",
]


def main():
    img = load_first_page(REFERENCE)
    tmpl = build_template(
        template_id="axis_gcl_premier_lfq",
        name="Axis Max Life Group Credit Life Premier LFQ Member Enrolment Form",
        reference_image=img,
        fields=FIELDS,
        signature_phrases=SIGNATURE,
    )
    path = save_template(tmpl)
    print(f"saved template -> {path}  ({len(tmpl.fields)} fields, "
          f"{len(tmpl.signature_phrases)} signature phrases)")


if __name__ == "__main__":
    main()
