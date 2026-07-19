"""Source of truth for the English golden dataset.

Regenerate ``datasets/golden_en.json`` after editing the samples below::

    python -m tests.evaluation.generate_golden_en

Each sample is a list of parts: plain strings, or (value, entity_type)
tuples. Character offsets are computed by concatenation, so annotations are
correct by construction — never edit the JSON by hand. A sync test
(``test_golden_dataset.py``) fails if the committed JSON drifts from this
module.

Entity values are checksum-valid where the recognizer validates (credit card
Luhn, IBAN mod-97, NHS check digit, SSN excluded ranges) — taken from the
repo's own unit tests where possible.
"""

import json
from pathlib import Path
from typing import Dict

P = "PERSON"
LOC = "LOCATION"
DT = "DATE_TIME"
EMAIL = "EMAIL_ADDRESS"
PHONE = "PHONE_NUMBER"
CC = "CREDIT_CARD"
SSN = "US_SSN"
IP = "IP_ADDRESS"
URL = "URL"
IBAN = "IBAN_CODE"
CRYPTO = "CRYPTO"
NHS = "UK_NHS"

ENTITIES = [P, LOC, DT, EMAIL, PHONE, CC, SSN, IP, URL, IBAN, CRYPTO, NHS]

# (id, category, parts)
SAMPLES = [
    # ------------------------------------------------ simple: one entity each
    ("person_simple_001", "simple",
     ["My name is ", ("David Johnson", P), " and I am calling about my account."]),
    ("person_simple_002", "simple",
     ["Please forward the report to ", ("Maria Garcia", P), " in accounting."]),
    ("email_simple_001", "simple",
     ["Contact us at ", ("support@acme-corp.com", EMAIL), " for further details."]),
    ("email_simple_002", "simple",
     ["Her personal address is ", ("jane.doe+billing@gmail.com", EMAIL), "."]),
    ("phone_simple_001", "simple",
     ["Call ", ("(212) 555-0143", PHONE), " to reschedule your appointment."]),
    ("phone_simple_002", "simple",
     ["You can reach the office at ", ("+1-312-555-0198", PHONE), "."]),
    ("credit_card_simple_001", "simple",
     ["The payment was made with card ", ("4111 1111 1111 1111", CC), "."]),
    ("credit_card_simple_002", "simple",
     ["Charge the amount to ", ("5555555555554444", CC), " as usual."]),
    ("ssn_simple_001", "simple",
     ["The applicant's social security number is ", ("078-05-1123", SSN), "."]),
    ("ip_simple_001", "simple",
     ["A login attempt was made from ", ("192.168.1.101", IP), "."]),
    ("ip_simple_002", "simple",
     ["The server listens on ", ("2001:db8:85a3::8a2e:370:7334", IP), " for IPv6 traffic."]),
    ("url_simple_001", "simple",
     ["The installation guide is at ", ("https://docs.example-project.org/setup", URL), "."]),
    ("iban_simple_001", "simple",
     ["Please transfer the funds to ", ("DE89 3704 0044 0532 0130 00", IBAN), "."]),
    ("crypto_simple_001", "simple",
     ["Send the bitcoin payment to ", ("1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa", CRYPTO), "."]),
    ("nhs_simple_001", "simple",
     ["The patient's NHS number is ", ("401-023-2137", NHS), "."]),
    ("date_simple_001", "simple",
     ["The invoice was issued on ", ("March 5, 2024", DT), "."]),
    ("location_simple_001", "simple",
     ["She recently moved to ", ("Barcelona", LOC), " for a new role."]),
    ("location_simple_002", "simple",
     ["The conference will be hosted in ", ("Toronto", LOC), ", ", ("Canada", LOC), "."]),

    # -------------------------------------------- medium: multi-entity texts
    ("support_ticket_001", "medium",
     ["Customer ", ("Alice Brown", P), " reported that she cannot log in. ",
      "Her registered email is ", ("alice.brown@example.com", EMAIL),
      " and her callback number is ", ("(415) 555-0132", PHONE), "."]),
    ("hr_note_001", "medium",
     [("Robert King", P), " joined the team on ", ("January 12, 2023", DT),
      " and relocated from ", ("Chicago", LOC), " to ", ("Seattle", LOC), "."]),
    ("bank_note_001", "medium",
     ["Wire sent to IBAN ", ("IL62 0108 0000 0009 9999 999", IBAN),
      " on behalf of ", ("Daniel Cohen", P),
      ". Reference card ending was replaced by ", ("4111111111111111", CC), "."]),
    ("server_log_001", "medium",
     ["Failed SSH login from ", ("203.0.113.42", IP),
      " targeting host ", ("198.51.100.7", IP),
      "; alert emailed to ", ("secops@corp-infra.io", EMAIL), "."]),
    ("order_confirmation_001", "medium",
     ["Hi ", ("Emily Watson", P), ", your order will arrive on ",
      ("Friday, June 21", DT), ". Track it at ",
      ("https://shipping.example.com/track?id=98765", URL), "."]),
    ("clinical_note_001", "medium",
     ["Patient ", ("Margaret Hill", P), " (NHS ", ("4010232137", NHS), ")",
      " attended a follow-up on ", ("12 May 2024", DT),
      ". Next of kin can be reached at ", ("+44 20 7946 0958", PHONE), "."]),
    ("travel_itinerary_001", "medium",
     [("James Miller", P), " flies from ", ("London", LOC), " to ", ("New York", LOC),
      " on ", ("October 3rd", DT), ". Confirmation was sent to ",
      ("j.miller@travelmail.net", EMAIL), "."]),
    ("signature_block_001", "medium",
     ["Best regards,\n", ("Sarah Connor", P), "\nHead of Operations\n",
      ("sarah.connor@cyber-systems.com", EMAIL), "\n", ("+1 (617) 555-0170", PHONE),
      "\n", ("https://www.cyber-systems.com", URL)]),
    ("payment_dispute_001", "medium",
     ["On ", ("April 2, 2024", DT), ", a charge on card ",
      ("378282246310005", CC), " was disputed by ", ("Carlos Ruiz", P),
      ". His SSN on file is ", ("078-05-1123", SSN), "."]),
    ("crypto_report_001", "medium",
     ["The wallet ", ("3J98t1WpEZ73CNmQviecrnyiWrnqRhWNLy", CRYPTO),
      " received funds routed through ", ("104.26.10.229", IP),
      "; details published at ", ("https://chain-audit.example.io/report", URL), "."]),

    # ---------------------------------------------- long / complex documents
    ("discharge_summary_001", "long",
     ["DISCHARGE SUMMARY\n\nPatient ", ("Kenji Nakamura", P),
      " was admitted on ", ("3 February 2024", DT),
      " and discharged on ", ("9 February 2024", DT),
      ". NHS number: ", ("401 023 2137", NHS),
      ". The patient lives in ", ("Manchester", LOC),
      " with his daughter ", ("Yuki Nakamura", P),
      ", who can be contacted on ", ("+44 161 496 0735", PHONE),
      " or at ", ("yuki.nakamura@familymail.co.uk", EMAIL),
      ". Follow-up scheduled for ", ("March 1, 2024", DT),
      " at the outpatient clinic."]),
    ("incident_report_001", "long",
     ["INCIDENT 4471 SUMMARY\n\nBetween ", ("02:00 and 04:30 UTC", DT),
      " we observed repeated credential-stuffing attempts against ",
      ("https://login.example-bank.com", URL),
      " originating from ", ("185.220.101.5", IP), " and ", ("185.220.101.34", IP),
      ". The on-call engineer, ", ("Priya Sharma", P),
      ", blocked both addresses and notified ", ("fraud-team@example-bank.com", EMAIL),
      ". No cardholder data was exposed; the honeypot card number ",
      ("4012888888881881", CC), " recorded no authorization attempts."]),
    ("kyc_paragraph_001", "long",
     ["KYC VERIFICATION\n\nApplicant ", ("Fatima Al-Sayed", P),
      ", residing in ", ("Dubai", LOC),
      ", provided SSN ", ("078-05-1123", SSN),
      " and settlement account ", ("GB29 NWBK 6016 1331 9268 19", IBAN),
      ". Identity confirmed via video call on ", ("11 November 2023", DT),
      "; certificate archived at ",
      ("https://kyc.example-verify.com/cases/8842", URL), "."]),
    ("meeting_minutes_001", "long",
     ["Minutes — infrastructure sync, ", ("Tuesday, 14 May", DT),
      "\n\nAttendees: ", ("Lars Eriksson", P), ", ", ("Nina Petrova", P),
      " (remote from ", ("Berlin", LOC), ").\n\n",
      ("Lars Eriksson", P), " reported that the gateway at ", ("10.0.0.254", IP),
      " will be decommissioned. Action items were mailed to ",
      ("infra-sync@corp-example.com", EMAIL), "."]),

    # ----------------------------------------------------------- edge cases
    ("edge_lowercase_name_001", "edge",
     ["appointment note: dr ", ("nakamura kenji", P), " will see the patient today"]),
    ("edge_hyphenated_name_001", "edge",
     [("Anne-Marie O'Neill", P), " signed the consent form."]),
    ("edge_name_at_start_001", "edge",
     [("Thomas Anderson", P), " requested a password reset."]),
    ("edge_entity_at_end_001", "edge",
     ["For any billing questions email ", ("billing@example-corp.net", EMAIL)]),
    ("edge_adjacent_entities_001", "edge",
     ["Escalated to ", ("John Smith", P), " ", ("john.smith@corp-example.com", EMAIL),
      " for review."]),
    ("edge_inline_id_001", "edge",
     ["Case #", ("078-05-1123", SSN), " was closed after identity verification."]),
    ("edge_spaced_card_001", "edge",
     ["Card on file: ", ("5555 5555 5555 4444", CC), " (primary)."]),
    ("edge_url_query_001", "edge",
     ["Reset your password at ",
      ("https://auth.example.com/reset?token=abc123&user=456", URL), "."]),

    # ------------------------------------- negatives: no PII, tempting text
    ("negative_version_001", "negative",
     ["Please upgrade the client to version 10.2.1 before the rollout."]),
    ("negative_numbers_001", "negative",
     ["The warehouse stores 4111 pallets across 16 aisles."]),
    ("negative_tech_001", "negative",
     ["The API returns a JSON object with numeric identifiers for each record."]),
    ("negative_metrics_001", "negative",
     ["Server response time improved by 20 percent after the caching change."]),
    ("negative_room_001", "negative",
     ["The workshop takes place in room 402, building C."]),
    ("negative_product_001", "negative",
     ["Model XR-500 ships with a 250 GB drive and dual fans."]),
]


def build_dataset() -> Dict:
    """Build the dataset dict from the sample definitions above."""
    samples_json = []
    for sample_id, category, parts in SAMPLES:
        text = ""
        spans = []
        for part in parts:
            if isinstance(part, str):
                text += part
            else:
                value, entity_type = part
                spans.append({
                    "entity_type": entity_type,
                    "start": len(text),
                    "end": len(text) + len(value),
                    "entity_value": value,
                })
                text += value
        samples_json.append({
            "id": sample_id,
            "category": category,
            "text": text,
            "spans": spans,
        })

    return {
        "version": 1,
        "language": "en",
        "entities": ENTITIES,
        "samples": samples_json,
    }


def dataset_to_json(dataset: Dict) -> str:
    """Serialize a dataset dict exactly as the committed file stores it."""
    return json.dumps(dataset, indent=2, ensure_ascii=False) + "\n"


def main() -> None:
    """Regenerate the committed golden dataset file."""
    dataset = build_dataset()
    out = Path(__file__).parent / "datasets" / "golden_en.json"
    out.write_text(dataset_to_json(dataset), encoding="utf-8")
    print(
        f"wrote {out} with {len(dataset['samples'])} samples, "
        f"{sum(len(s['spans']) for s in dataset['samples'])} spans"
    )


if __name__ == "__main__":
    main()
