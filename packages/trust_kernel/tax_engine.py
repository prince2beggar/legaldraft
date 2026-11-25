"""
Professional Bangladesh Taxation & VAT Engine (Module M23).
Deterministic calculation according to:
1. Income Tax Act, 2023 (আয়কর আইন, ২০২৩) and Finance Acts
2. Value Added Tax and Supplementary Duty Act, 2012 (মূল্য সংযোজন কর ও সম্পূরক শুল্ক আইন, ২০১২)
3. Form IT-11GA (আইটি-১১গ) return preparation
4. Mushak-9.1 (মূসক-৯.১) monthly VAT return worksheet
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from packages.trust_kernel.ai_gateway import to_bangla_digits
from packages.trust_kernel.num_to_words import number_to_bangla_words

# -----------------------------------------------------------------------------
# 1. Income Tax Parameters & Constants (Income Tax Act, 2023)
# -----------------------------------------------------------------------------
ASSESSMENT_YEAR_DEFAULT = "2024-2025"

# Tax-Free Thresholds (করমুক্ত আয়ের সীমা)
TAX_FREE_THRESHOLDS = {
    "general": 350000,          # সাধারণ করদাতা (পুরুষ): ৩,৫০,০০০ টাকা
    "female_senior": 400000,    # নারী এবং ৬৫+ বছর বয়সী প্রবীণ: ৪,০০,০০০ টাকা
    "disabled_third_gender": 475000, # তৃতীয় লিঙ্গ ও প্রতিবন্ধী: ৪,৭৫,০০০ টাকা
    "freedom_fighter": 500000,  # গেজেটভুক্ত যুদ্ধাহত মুক্তিযোদ্ধা: ৫,০০,০০০ টাকা
}

# Individual Tax Slabs (ব্যক্তিগত কর হার) - Income Tax Act, 2023
INDIVIDUAL_TAX_SLABS: list[dict[str, Any]] = [
    {"limit": 100000, "rate": 0.05, "label": "পরবর্তী ১,০০,০০০ টাকার উপর ৫%"},
    {"limit": 400000, "rate": 0.10, "label": "পরবর্তী ৪,০০,০০০ টাকার উপর ১০%"},
    {"limit": 500000, "rate": 0.15, "label": "পরবর্তী ৫,০০,০০০ টাকার উপর ১৫%"},
    {"limit": 500000, "rate": 0.20, "label": "পরবর্তী ৫,০০,০০০ টাকার উপর ২০%"},
    {"limit": None,   "rate": 0.25, "label": "অবশিষ্ট আয়ের উপর ২৫%"},
]

# Minimum Tax by Geography (এলাকাভিত্তিক ন্যূনতম কর)
MINIMUM_TAX_RATES = {
    "dhaka_chattogram_cc": 5000,  # ঢাকা ও চট্টগ্রাম সিটি কর্পোরেশন: ৫,০০০ টাকা
    "other_cc": 4000,             # অন্যান্য সিটি কর্পোরেশন: ৪,০০০ টাকা
    "non_cc": 3000,               # সিটি কর্পোরেশন বহির্ভূত অন্যান্য এলাকা: ৩,০০০ টাকা
}

# Standard VAT Rates (মূল্য সংযোজন কর হার) - VAT Act 2012
STANDARD_VAT_RATE = 0.15  # ১৫% প্রমিত হার


class TaxEngine:
    """
    Deterministic tax computation engine adhering to Bangladesh tax law.
    Zero hallucination guarantee: all tax amounts and slabs computed in pure code.
    """

    @staticmethod
    def calculate_income_tax(inputs: dict[str, Any]) -> dict[str, Any]:
        """
        Computes individual income tax under Income Tax Act, 2023.

        inputs:
          category: 'general' | 'female_senior' | 'disabled_third_gender' | 'freedom_fighter'
          location: 'dhaka_chattogram_cc' | 'other_cc' | 'non_cc'
          income_salary: float (বেতন থেকে আয়)
          income_interest: float (আর্থিক পরিসম্পদ / ব্যাংক সুদ)
          income_house: float (গৃহ-সম্পত্তি থেকে আয়)
          income_agriculture: float (কৃষি আয়)
          income_business: float (ব্যবসা বা পেশা থেকে আয়)
          income_capital_gain: float (মূলধনী মুনাফা)
          income_other: float (অন্যান্য উৎস থেকে আয়)
          actual_investment: float (অনুমোদিত বিনিয়োগ - ডিপিএস, সঞ্চয়পত্র ইত্যাদি)
          advance_tax_paid: float (অগ্রিম পরিশোধিত কর - AIT / উৎসে কর্তন)
          net_wealth: float (মোট নীট পরিসম্পদ - সারচার্জের জন্য)
        """
        cat = inputs.get("category", "general")
        loc = inputs.get("location", "dhaka_chattogram_cc")
        threshold = TAX_FREE_THRESHOLDS.get(cat, 350000)
        min_tax_floor = MINIMUM_TAX_RATES.get(loc, 5000)

        # Aggregate total gross taxable income
        income_salary = float(inputs.get("income_salary", 0) or 0)
        income_interest = float(inputs.get("income_interest", 0) or 0)
        income_house = float(inputs.get("income_house", 0) or 0)
        income_agriculture = float(inputs.get("income_agriculture", 0) or 0)
        income_business = float(inputs.get("income_business", 0) or 0)
        income_capital_gain = float(inputs.get("income_capital_gain", 0) or 0)
        income_other = float(inputs.get("income_other", 0) or 0)

        total_income = (
            income_salary
            + income_interest
            + income_house
            + income_agriculture
            + income_business
            + income_capital_gain
            + income_other
        )

        taxable_balance = max(0.0, total_income - threshold)
        slab_breakdown: list[dict[str, Any]] = []

        # 1. Tax Free Tier
        slab_breakdown.append({
            "slab_name": "করমুক্ত সীমা",
            "allocated_amount": min(total_income, threshold),
            "rate_percent": 0,
            "tax_for_slab": 0.0,
        })

        gross_tax = 0.0
        remaining_to_tax = taxable_balance

        for slab in INDIVIDUAL_TAX_SLABS:
            if remaining_to_tax <= 0:
                break
            limit = float(slab["limit"]) if slab["limit"] is not None else None
            rate = float(slab["rate"])
            label = str(slab["label"])

            if limit is not None:
                amount_in_slab = min(remaining_to_tax, limit)
            else:
                amount_in_slab = remaining_to_tax

            tax_on_slab = amount_in_slab * rate
            gross_tax += tax_on_slab
            remaining_to_tax -= amount_in_slab

            slab_breakdown.append({
                "slab_name": label,
                "allocated_amount": amount_in_slab,
                "rate_percent": int(rate * 100),
                "tax_for_slab": round(tax_on_slab, 2),
            })

        # 2. Investment Tax Rebate (বিনিয়োগ কর রেয়াত)
        # Act 2023: Lower of 15% of actual investment or 3% of total taxable income or 10,00,000 Tk
        actual_inv = float(inputs.get("actual_investment", 0) or 0)
        inv_ceiling_1 = actual_inv * 0.15
        inv_ceiling_2 = total_income * 0.03
        inv_ceiling_3 = 1000000.0  # ১০ লাখ টাকা সর্বোচ্চ রেয়াত সীমা

        if actual_inv > 0 and taxable_balance > 0:
            rebate = min(inv_ceiling_1, inv_ceiling_2, inv_ceiling_3)
        else:
            rebate = 0.0

        tax_after_rebate = max(0.0, gross_tax - rebate)

        # 3. Minimum Tax Rule
        # If income exceeds threshold, tax payable cannot be less than minimum tax floor
        applies_min_tax = False
        if total_income > threshold and tax_after_rebate < min_tax_floor:
            final_tax_liability = float(min_tax_floor)
            applies_min_tax = True
        else:
            final_tax_liability = tax_after_rebate

        # 4. Surcharge on Wealth (পরিসম্পদ সারচার্জ)
        net_wealth = float(inputs.get("net_wealth", 0) or 0)
        surcharge_rate = 0.0
        surcharge_amount = 0.0
        if net_wealth > 40000000:  # > ৪ কোটি টাকা
            surcharge_rate = 0.10
            surcharge_amount = final_tax_liability * surcharge_rate
        elif net_wealth > 100000000: # > ১০ কোটি টাকা
            surcharge_rate = 0.20
            surcharge_amount = final_tax_liability * surcharge_rate

        total_tax_with_surcharge = final_tax_liability + surcharge_amount

        # 5. Advance Tax / TDS Adjustment (অগ্রিম কর সমন্বয়)
        advance_paid = float(inputs.get("advance_tax_paid", 0) or 0)
        net_payable = total_tax_with_surcharge - advance_paid
        is_refund = net_payable < 0
        refund_amount = abs(net_payable) if is_refund else 0.0
        payable_amount = net_payable if not is_refund else 0.0

        return {
            "assessment_year": inputs.get("assessment_year", ASSESSMENT_YEAR_DEFAULT),
            "category": cat,
            "threshold": threshold,
            "threshold_bn": to_bangla_digits(f"{threshold:,}"),
            "location": loc,
            "minimum_tax_floor": min_tax_floor,
            "minimum_tax_floor_bn": to_bangla_digits(f"{min_tax_floor:,}"),
            "total_income": total_income,
            "total_income_bn": to_bangla_digits(f"{int(total_income):,}"),
            "taxable_income": taxable_balance,
            "taxable_income_bn": to_bangla_digits(f"{int(taxable_balance):,}"),
            "gross_tax": round(gross_tax, 2),
            "gross_tax_bn": to_bangla_digits(f"{int(gross_tax):,}"),
            "rebate": round(rebate, 2),
            "rebate_bn": to_bangla_digits(f"{int(rebate):,}"),
            "tax_after_rebate": round(tax_after_rebate, 2),
            "tax_after_rebate_bn": to_bangla_digits(f"{int(tax_after_rebate):,}"),
            "applies_minimum_tax": applies_min_tax,
            "surcharge_rate": surcharge_rate,
            "surcharge_amount": round(surcharge_amount, 2),
            "surcharge_amount_bn": to_bangla_digits(f"{int(surcharge_amount):,}"),
            "advance_tax_paid": advance_paid,
            "advance_tax_paid_bn": to_bangla_digits(f"{int(advance_paid):,}"),
            "net_payable": round(payable_amount, 2),
            "net_payable_bn": to_bangla_digits(f"{int(payable_amount):,}"),
            "net_payable_words": number_to_bangla_words(int(payable_amount)),
            "refund_amount": round(refund_amount, 2),
            "refund_amount_bn": to_bangla_digits(f"{int(refund_amount):,}"),
            "is_refund": is_refund,
            "slab_breakdown": slab_breakdown,
            "legal_basis": "আয়কর আইন, ২০২৩ ও সংশ্লিষ্ট অর্থ আইন বিধিমোতাবেক গণনাকৃত।",
        }

    @staticmethod
    def calculate_vat(inputs: dict[str, Any]) -> dict[str, Any]:
        """
        Computes monthly VAT under Value Added Tax & Supplementary Duty Act, 2012.

        inputs:
          tax_period: 'YYYY-MM' (কর মেয়াদ)
          standard_sales: float (১৫% হারে করযোগ্য সরবরাহ)
          reduced_sales: float (হ্রাসকৃত হারে করযোগ্য সরবরাহ - ৫%, ৭.৫%, ১০%)
          reduced_rate: float (হ্রাসকৃত হার - e.g. 0.05, 0.075, 0.10)
          exempt_sales: float (অব্যাহতিপ্রাপ্ত বিক্রয়)
          zero_rated_export: float (শূন্য হারে রপ্তানি)
          input_purchases_standard: float (রেয়াতযোগ্য উপকরণ ক্রয় - ১৫% ভ্যাটযুক্ত)
          vds_deducted_by_buyers: float (ক্রেতা কর্তৃক উৎসে কর্তিত মূসক - VDS)
          vds_withheld_from_suppliers: float (সরবরাহকারীর নিকট হতে উৎসে কর্তিত মূসক)
        """
        std_sales = float(inputs.get("standard_sales", 0) or 0)
        reduced_sales = float(inputs.get("reduced_sales", 0) or 0)
        reduced_rate = float(inputs.get("reduced_rate", 0.05) or 0.05)
        exempt_sales = float(inputs.get("exempt_sales", 0) or 0)
        export_sales = float(inputs.get("zero_rated_export", 0) or 0)

        # Output Tax (প্রদেয় উৎপাদ কর)
        output_vat_std = std_sales * STANDARD_VAT_RATE
        output_vat_reduced = reduced_sales * reduced_rate
        total_output_vat = output_vat_std + output_vat_reduced

        # Input Tax Credit (রেয়াতযোগ্য উপকরণ কর)
        purchases = float(inputs.get("input_purchases_standard", 0) or 0)
        input_vat_credit = purchases * STANDARD_VAT_RATE

        # VDS adjustments
        vds_by_buyers = float(inputs.get("vds_deducted_by_buyers", 0) or 0)
        vds_withheld = float(inputs.get("vds_withheld_from_suppliers", 0) or 0)

        # Final Net VAT Payable for the month
        # Payable = Output VAT - Input Rebate - VDS deducted by buyers + VDS withheld from suppliers
        final_vat_payable = (total_output_vat - input_vat_credit - vds_by_buyers) + vds_withheld
        is_closing_credit = final_vat_payable < 0
        refund_or_credit = abs(final_vat_payable) if is_closing_credit else 0.0
        payable_amount = final_vat_payable if not is_closing_credit else 0.0

        total_turnover = std_sales + reduced_sales + exempt_sales + export_sales

        return {
            "tax_period": inputs.get("tax_period", datetime.now(timezone.utc).strftime("%Y-%m")),
            "total_turnover": total_turnover,
            "total_turnover_bn": to_bangla_digits(f"{int(total_turnover):,}"),
            "standard_sales": std_sales,
            "output_vat_std": round(output_vat_std, 2),
            "output_vat_std_bn": to_bangla_digits(f"{int(output_vat_std):,}"),
            "reduced_sales": reduced_sales,
            "output_vat_reduced": round(output_vat_reduced, 2),
            "output_vat_reduced_bn": to_bangla_digits(f"{int(output_vat_reduced):,}"),
            "total_output_vat": round(total_output_vat, 2),
            "total_output_vat_bn": to_bangla_digits(f"{int(total_output_vat):,}"),
            "input_purchases": purchases,
            "input_vat_credit": round(input_vat_credit, 2),
            "input_vat_credit_bn": to_bangla_digits(f"{int(input_vat_credit):,}"),
            "vds_deducted_by_buyers": vds_by_buyers,
            "vds_deducted_by_buyers_bn": to_bangla_digits(f"{int(vds_by_buyers):,}"),
            "vds_withheld_from_suppliers": vds_withheld,
            "vds_withheld_from_suppliers_bn": to_bangla_digits(f"{int(vds_withheld):,}"),
            "net_vat_payable": round(payable_amount, 2),
            "net_vat_payable_bn": to_bangla_digits(f"{int(payable_amount):,}"),
            "net_vat_payable_words": number_to_bangla_words(int(payable_amount)),
            "is_closing_credit": is_closing_credit,
            "closing_credit_amount": round(refund_or_credit, 2),
            "closing_credit_amount_bn": to_bangla_digits(f"{int(refund_or_credit):,}"),
            "mushak_form": "মূসক-৯.১ মাসিক দাখিলপত্র",
            "legal_basis": "মূল্য সংযোজন কর ও সম্পূরক শুল্ক আইন, ২০১২ এর ধারা ৬৪ বিধিমোতাবেক হিসাবকৃত।",
        }

    @staticmethod
    def generate_it11ga_statement(profile: dict[str, Any], calc_result: dict[str, Any]) -> dict[str, Any]:
        """
        Structures the full Form IT-11GA (আইটি-১১গ) return dossier for individual taxpayers.
        """
        filing_date = profile.get("filing_date") or datetime.now(timezone.utc).strftime("%d/%m/%Y")
        filing_time = profile.get("filing_time") or datetime.now(timezone.utc).strftime("%I:%M %p")
        assessment_yr = profile.get("assessment_year") or calc_result.get("assessment_year", ASSESSMENT_YEAR_DEFAULT)
        return {
            "form_code": "IT-11GA",
            "form_name_bn": "ব্যক্তি করদাতার আয়কর রিটার্ন ফরম (আইটি-১১গ)",
            "assessment_year": assessment_yr,
            "taxpayer_name": profile.get("taxpayer_name", "করদাতার নাম"),
            "tin": profile.get("tin") or profile.get("taxpayer_tin") or "১২ সংখ্যার টিআইএন",
            "nid": profile.get("nid", "জাতীয় পরিচয়পত্র নং"),
            "profession": profile.get("profession", "কর্ম / পেশা"),
            "workplace": profile.get("workplace", "কর্মস্থল / প্রতিষ্ঠান"),
            "circle": profile.get("circle", "কর সার্কেল"),
            "zone": profile.get("zone", "কর অঞ্চল"),
            "resident_status": profile.get("resident_status", "নিবাসী"),
            "source_of_income": profile.get("main_source") or profile.get("profession") or "চাকরি / ব্যবসা / সম্পত্তি",
            "summary_of_income": {
                "salary": profile.get("income_salary", 0),
                "interest": profile.get("income_interest", 0),
                "house": profile.get("income_house", 0),
                "agriculture": profile.get("income_agriculture", 0),
                "business": profile.get("income_business", 0),
                "capital_gain": profile.get("income_capital_gain", 0),
                "other": profile.get("income_other", 0),
                "total": calc_result.get("total_income", 0),
            },
            "tax_computation": {
                "taxable_income": calc_result.get("taxable_income", 0),
                "gross_tax": calc_result.get("gross_tax", 0),
                "investment_rebate": calc_result.get("rebate", 0),
                "net_tax": calc_result.get("tax_after_rebate", 0),
                "surcharge": calc_result.get("surcharge_amount", 0),
                "advance_tax_paid": calc_result.get("advance_tax_paid", 0),
                "net_payable": calc_result.get("net_payable", 0),
                "net_payable_bn": calc_result.get("net_payable_bn", "০"),
                "net_payable_words": calc_result.get("net_payable_words", "শূন্য টাকা"),
                "refund_claim": calc_result.get("refund_amount", 0),
            },
            "assets_summary_it10b": {
                "business_capital": profile.get("asset_business", 0),
                "residential_property": profile.get("asset_property", 0),
                "financial_assets": profile.get("asset_financial", 0),
                "motor_vehicles": profile.get("asset_vehicles", 0),
                "gold_ornaments": profile.get("asset_gold", 0),
                "total_assets": profile.get("total_assets", 0),
                "total_liabilities": profile.get("total_liabilities", 0),
                "net_wealth": profile.get("net_wealth", 0),
            },
            "verification_statement": "আমি শপথ করিয়া ঘোষণা করিতেছি যে, এই বিবরণীতে প্রদত্ত সকল তথ্য আমার জ্ঞান ও বিশ্বাসমতে সত্য এবং সঠিক।",
            "date": filing_date,
            "time": filing_time,
            "system_disclaimer": "এটি এআই-সহায়তায় তৈরি খসড়া বিবরণী, যা আইটিপি বা সনদপ্রাপ্ত আইনজীবীর পর্যালোচনাসাপেক্ষ। এনবিআরের সরাসরি প্রত্যয়ন নয়।",
        }
