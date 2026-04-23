#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import random
import sys
from datetime import date, timedelta
from pathlib import Path


DEFAULT_LABELS = [
    "invoice",
    "receipt",
    "bank_statement",
    "id_card",
    "utility_bill",
    "contract",
    "medical_record",
    "tax_form",
    "unknown_other",
]

COMPANIES = [
    "Acme Supplies Ltd",
    "Northwind Logistics",
    "BluePeak Energy",
    "Riverside Medical Group",
    "Summit Retail Partners",
    "Delta Office Systems",
    "Cedar Grove Properties",
    "Horizon Freight Services",
]

PEOPLE = [
    "Ada Okafor",
    "Musa Bello",
    "Grace Mensah",
    "Chinedu Nwosu",
    "Ifeoma Obi",
    "Daniel Mensimah",
    "Kemi Adebayo",
    "Samuel Otieno",
]

STREETS = [
    "12 Marina Road, Lagos",
    "44 Airport Avenue, Abuja",
    "87 Broad Street, Accra",
    "19 Palm Crescent, Ibadan",
    "5 Unity Close, Enugu",
    "73 Market Lane, Kumasi",
]

BANKS = [
    "Unity Trust Bank",
    "Coastal Commercial Bank",
    "First Community Credit",
    "Sterling Metro Bank",
]

UTILITIES = [
    "Electricity Distribution Plc",
    "City Water Board",
    "Metro Gas Services",
    "Regional Waste Authority",
]

PROVIDERS = [
    "Riverside Family Clinic",
    "St. Anne Diagnostic Centre",
    "Green Cross Hospital",
    "Metro Specialist Clinic",
]

UNKNOWN_TOPICS = [
    "Team meeting notes",
    "Project retrospective",
    "Delivery status update",
    "Product brainstorming session",
    "Shift handover summary",
    "Internal memo",
]


def _load_labels(labels_json: str | None) -> list[str]:
    if not labels_json:
        return list(DEFAULT_LABELS)
    labels = json.loads(labels_json)
    if not isinstance(labels, list) or not all(isinstance(x, str) for x in labels):
        raise SystemExit("--labels-json must be a JSON array of strings")
    return labels


def _pick(rng: random.Random, values: list[str]) -> str:
    return rng.choice(values)


def _money(rng: random.Random, minimum: float, maximum: float) -> str:
    return f"{rng.uniform(minimum, maximum):,.2f}"


def _digits(rng: random.Random, length: int) -> str:
    return "".join(rng.choice("0123456789") for _ in range(length))


def _date(rng: random.Random, *, start_year: int = 2022, end_year: int = 2026) -> str:
    start = date(start_year, 1, 1)
    end = date(end_year, 12, 31)
    offset = rng.randint(0, (end - start).days)
    return (start + timedelta(days=offset)).isoformat()


def _invoice_text(rng: random.Random) -> str:
    vendor = _pick(rng, COMPANIES)
    customer = _pick(rng, COMPANIES)
    subtotal = float(_money(rng, 120.0, 9500.0).replace(",", ""))
    tax = round(subtotal * rng.uniform(0.03, 0.12), 2)
    total = subtotal + tax
    return "\n".join(
        [
            f"INVOICE #{_digits(rng, 6)}",
            f"Vendor: {vendor}",
            f"Bill To: {customer}",
            f"Invoice Date: {_date(rng)}",
            f"Due Date: {_date(rng)}",
            f"Subtotal: USD {subtotal:,.2f}",
            f"Tax: USD {tax:,.2f}",
            f"Total Due: USD {total:,.2f}",
            f"Payment Terms: Net {rng.choice([7, 14, 30])}",
        ]
    )


def _receipt_text(rng: random.Random) -> str:
    store = _pick(rng, COMPANIES)
    cashier = _pick(rng, PEOPLE)
    items = [
        f"{rng.choice(['Paper', 'Milk', 'USB Cable', 'Notebook', 'Batteries'])} x{rng.randint(1, 4)}",
        f"{rng.choice(['Coffee', 'Bread', 'Printer Ink', 'Soap'])} x{rng.randint(1, 3)}",
    ]
    total = _money(rng, 5.0, 240.0)
    return "\n".join(
        [
            f"SALES RECEIPT {_digits(rng, 8)}",
            f"Store: {store}",
            f"Date: {_date(rng)}",
            f"Cashier: {cashier}",
            *items,
            f"Payment Method: {rng.choice(['Card', 'Cash', 'Transfer'])}",
            f"Total: USD {total}",
        ]
    )


def _bank_statement_text(rng: random.Random) -> str:
    account_name = _pick(rng, PEOPLE)
    lines = []
    running_balance = rng.uniform(2000.0, 9000.0)
    for _ in range(4):
        delta = rng.uniform(-950.0, 1800.0)
        running_balance += delta
        direction = "CR" if delta >= 0 else "DR"
        lines.append(
            f"{_date(rng)} | {rng.choice(['Transfer', 'POS Purchase', 'Salary', 'ATM Withdrawal'])} | "
            f"{direction} {abs(delta):,.2f} | Balance {running_balance:,.2f}"
        )
    return "\n".join(
        [
            _pick(rng, BANKS),
            "ACCOUNT STATEMENT",
            f"Account Name: {account_name}",
            f"Account Number: {_digits(rng, 10)}",
            f"Statement Period: {_date(rng)} to {_date(rng)}",
            *lines,
        ]
    )


def _id_card_text(rng: random.Random) -> str:
    person = _pick(rng, PEOPLE)
    return "\n".join(
        [
            f"{rng.choice(['NATIONAL ID CARD', 'IDENTITY CARD', 'RESIDENT ID'])}",
            f"Full Name: {person}",
            f"Date of Birth: {_date(rng, start_year=1970, end_year=2004)}",
            f"ID Number: {_digits(rng, 11)}",
            f"Issue Date: {_date(rng)}",
            f"Expiry Date: {_date(rng, start_year=2027, end_year=2035)}",
            f"Address: {_pick(rng, STREETS)}",
        ]
    )


def _utility_bill_text(rng: random.Random) -> str:
    provider = _pick(rng, UTILITIES)
    customer = _pick(rng, PEOPLE)
    return "\n".join(
        [
            provider,
            rng.choice(["UTILITY BILL", "MONTHLY BILLING STATEMENT", "CUSTOMER BILL"]),
            f"Customer Name: {customer}",
            f"Service Address: {_pick(rng, STREETS)}",
            f"Account Number: {_digits(rng, 9)}",
            f"Billing Period: {_date(rng)} to {_date(rng)}",
            f"Current Charges: USD {_money(rng, 25.0, 420.0)}",
            f"Previous Balance: USD {_money(rng, 0.0, 80.0)}",
            f"Amount Due: USD {_money(rng, 30.0, 480.0)}",
        ]
    )


def _contract_text(rng: random.Random) -> str:
    party_a = _pick(rng, COMPANIES)
    party_b = _pick(rng, COMPANIES)
    return "\n".join(
        [
            rng.choice(["SERVICE AGREEMENT", "CONSULTING AGREEMENT", "MASTER SERVICES AGREEMENT"]),
            f"Between {party_a} and {party_b}",
            f"Effective Date: {_date(rng)}",
            f"Term: {rng.choice(['12 months', '24 months', '36 months'])}",
            f"Scope: Provide {rng.choice(['software support', 'maintenance services', 'document processing services'])}.",
            f"Fees: USD {_money(rng, 2500.0, 45000.0)} payable monthly.",
            f"Termination Notice: {rng.choice(['30 days', '60 days', '90 days'])}.",
            "Confidentiality: Both parties shall protect non-public information.",
            "Signatures: ____________________",
        ]
    )


def _medical_record_text(rng: random.Random) -> str:
    patient = _pick(rng, PEOPLE)
    provider = _pick(rng, PROVIDERS)
    return "\n".join(
        [
            provider,
            "MEDICAL RECORD",
            f"Patient Name: {patient}",
            f"Patient ID: MRN-{_digits(rng, 7)}",
            f"Visit Date: {_date(rng)}",
            f"Chief Complaint: {rng.choice(['headache', 'cough', 'abdominal pain', 'follow-up review'])}",
            f"Diagnosis: {rng.choice(['viral infection', 'hypertension', 'migraine', 'type 2 diabetes'])}",
            f"Prescription: {rng.choice(['Paracetamol', 'Amoxicillin', 'Metformin', 'Ibuprofen'])}",
            "Notes: Return for review in two weeks if symptoms persist.",
        ]
    )


def _tax_form_text(rng: random.Random) -> str:
    taxpayer = _pick(rng, PEOPLE)
    tax_year = rng.choice([2022, 2023, 2024, 2025])
    return "\n".join(
        [
            rng.choice(["TAX RETURN FORM", "WITHHOLDING TAX CERTIFICATE", "ANNUAL TAX DECLARATION"]),
            f"Taxpayer Name: {taxpayer}",
            f"Taxpayer ID: TIN-{_digits(rng, 9)}",
            f"Tax Year: {tax_year}",
            f"Gross Income: USD {_money(rng, 15000.0, 150000.0)}",
            f"Taxable Income: USD {_money(rng, 12000.0, 120000.0)}",
            f"Tax Due: USD {_money(rng, 500.0, 35000.0)}",
            f"Filed Date: {_date(rng)}",
        ]
    )


def _unknown_other_text(rng: random.Random) -> str:
    topic = _pick(rng, UNKNOWN_TOPICS)
    owner = _pick(rng, PEOPLE)
    return "\n".join(
        [
            topic,
            f"Prepared by: {owner}",
            f"Date: {_date(rng)}",
            rng.choice(
                [
                    "Agenda: review milestones, blockers, and next actions for the week.",
                    "Summary: discussed customer feedback, release timing, and engineering priorities.",
                    "Action items: update dashboard copy, confirm launch checklist, schedule follow-up.",
                    "Notes: no invoice, receipt, bank data, or medical encounter information included.",
                ]
            ),
            rng.choice(
                [
                    "The document is an internal working note for coordination.",
                    "This text records operational updates for the team.",
                    "These notes capture a non-regulated business discussion.",
                ]
            ),
        ]
    )


GENERATORS = {
    "invoice": _invoice_text,
    "receipt": _receipt_text,
    "bank_statement": _bank_statement_text,
    "id_card": _id_card_text,
    "utility_bill": _utility_bill_text,
    "contract": _contract_text,
    "medical_record": _medical_record_text,
    "tax_form": _tax_form_text,
    "unknown_other": _unknown_other_text,
}


def _apply_ocr_noise(rng: random.Random, text: str) -> str:
    noisy = text
    if rng.random() < 0.25:
        noisy = noisy.replace("O", "0", 1)
    if rng.random() < 0.20:
        noisy = noisy.replace("I", "1", 1)
    if rng.random() < 0.20:
        noisy = noisy.replace(": ", ":  ")
    if rng.random() < 0.15:
        noisy = noisy.replace("USD", "USO", 1)
    return noisy


def _generate_row(rng: random.Random, *, label: str, index: int, apply_noise: bool) -> dict[str, object]:
    if label not in GENERATORS:
        raise SystemExit(f"Unsupported label '{label}'. Add a generator or pass a supported label set.")

    text = GENERATORS[label](rng)
    if apply_noise:
        text = _apply_ocr_noise(rng, text)

    return {
        "id": f"synthetic-{label}-{index:05d}",
        "label": label,
        "text": text,
        "source_media_type": "text/plain",
        "synthetic": True,
    }


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Generate balanced synthetic text-only training data for document classification fine-tuning."
    )
    ap.add_argument("--out", required=True, help="Output JSONL path to write.")
    ap.add_argument("--examples-per-label", type=int, default=250, help="Number of rows to generate per label.")
    ap.add_argument("--labels-json", default=None, help="Optional JSON array of labels to generate.")
    ap.add_argument("--seed", type=int, default=1337, help="Random seed for reproducible output.")
    ap.add_argument(
        "--disable-ocr-noise",
        action="store_true",
        help="Disable light OCR-style text imperfections.",
    )
    args = ap.parse_args()

    if args.examples_per_label <= 0:
        raise SystemExit("--examples-per-label must be > 0")

    labels = _load_labels(args.labels_json)
    rng = random.Random(args.seed)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, object]] = []
    for label in labels:
        for index in range(1, args.examples_per_label + 1):
            rows.append(
                _generate_row(
                    rng,
                    label=label,
                    index=index,
                    apply_noise=not args.disable_ocr_noise,
                )
            )

    rng.shuffle(rows)

    with out_path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=True) + "\n")

    summary = {
        "out": str(out_path),
        "labels": labels,
        "examples_per_label": args.examples_per_label,
        "total_rows": len(rows),
        "seed": args.seed,
        "ocr_noise_enabled": not args.disable_ocr_noise,
    }
    sys.stderr.write(json.dumps(summary, indent=2) + "\n")


if __name__ == "__main__":
    main()
