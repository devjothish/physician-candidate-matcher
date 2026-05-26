"""NPI Healthcare Provider Taxonomy for physician specialty matching.

Source: NUCC Health Care Provider Taxonomy Code Set v25.1
        (National Uniform Claim Committee, CMS)
        https://www.nucc.org/index.php/code-sets-mainmenu-41/provider-taxonomy-mainmenu-40

Three-level hierarchy:
  Grouping -> Classification -> Specialization

Example:
  Allopathic & Osteopathic Physicians -> Internal Medicine -> Interventional Cardiology

This module provides:
  1. normalize_specialty() - Map any specialty name to its canonical classification
  2. specialty_distance() - Compute 0.0-1.0 distance between two specialties
  3. find_related() - Find all specializations under a classification
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class TaxonomyEntry:
    code: str
    classification: str
    specialization: str
    display_name: str


# Built from NUCC v25.1 CSV - Allopathic & Osteopathic Physicians only
# Each classification has a parent entry (specialization="") and child entries
PHYSICIAN_TAXONOMY: list[TaxonomyEntry] = [
    # Allergy & Immunology
    TaxonomyEntry("207K00000X", "Allergy & Immunology", "", "Allergy & Immunology Physician"),
    TaxonomyEntry("207KA0200X", "Allergy & Immunology", "Allergy", "Allergy Physician"),
    TaxonomyEntry(
        "207KI0005X",
        "Allergy & Immunology",
        "Clinical & Laboratory Immunology",
        "Clinical & Laboratory Immunology Physician",
    ),
    # Anesthesiology
    TaxonomyEntry("207L00000X", "Anesthesiology", "", "Anesthesiology Physician"),
    TaxonomyEntry(
        "207LA0401X", "Anesthesiology", "Addiction Medicine", "Addiction Medicine (Anesthesiology) Physician"
    ),
    TaxonomyEntry(
        "207LC0200X", "Anesthesiology", "Critical Care Medicine", "Critical Care Medicine (Anesthesiology) Physician"
    ),
    TaxonomyEntry(
        "207LH0002X",
        "Anesthesiology",
        "Hospice and Palliative Medicine",
        "Hospice and Palliative Medicine (Anesthesiology) Physician",
    ),
    TaxonomyEntry("207LP2900X", "Anesthesiology", "Pain Medicine", "Pain Medicine (Anesthesiology) Physician"),
    TaxonomyEntry("207LP3000X", "Anesthesiology", "Pediatric Anesthesiology", "Pediatric Anesthesiology Physician"),
    # Colon & Rectal Surgery
    TaxonomyEntry("208C00000X", "Colon & Rectal Surgery", "", "Colon & Rectal Surgery Physician"),
    # Dermatology
    TaxonomyEntry("207N00000X", "Dermatology", "", "Dermatology Physician"),
    TaxonomyEntry(
        "207NI0002X",
        "Dermatology",
        "Clinical & Laboratory Dermatological Immunology",
        "Dermatological Immunology Physician",
    ),
    TaxonomyEntry("207ND0900X", "Dermatology", "Dermatopathology", "Dermatopathology Physician"),
    TaxonomyEntry("207ND0101X", "Dermatology", "MOHS-Micrographic Surgery", "MOHS Surgery Physician"),
    TaxonomyEntry("207NP0225X", "Dermatology", "Pediatric Dermatology", "Pediatric Dermatology Physician"),
    TaxonomyEntry("207NS0135X", "Dermatology", "Procedural Dermatology", "Procedural Dermatology Physician"),
    # Emergency Medicine
    TaxonomyEntry("207P00000X", "Emergency Medicine", "", "Emergency Medicine Physician"),
    TaxonomyEntry(
        "207PE0004X", "Emergency Medicine", "Emergency Medical Services", "Emergency Medical Services Physician"
    ),
    TaxonomyEntry("207PT0002X", "Emergency Medicine", "Medical Toxicology", "Medical Toxicology Physician"),
    TaxonomyEntry(
        "207PP0204X", "Emergency Medicine", "Pediatric Emergency Medicine", "Pediatric Emergency Medicine Physician"
    ),
    TaxonomyEntry(
        "207PS0010X", "Emergency Medicine", "Sports Medicine", "Sports Medicine (Emergency Medicine) Physician"
    ),
    TaxonomyEntry(
        "207PE0005X",
        "Emergency Medicine",
        "Undersea and Hyperbaric Medicine",
        "Undersea and Hyperbaric Medicine Physician",
    ),
    # Family Medicine
    TaxonomyEntry("207Q00000X", "Family Medicine", "", "Family Medicine Physician"),
    TaxonomyEntry(
        "207QA0401X", "Family Medicine", "Addiction Medicine", "Addiction Medicine (Family Medicine) Physician"
    ),
    TaxonomyEntry("207QA0000X", "Family Medicine", "Adolescent Medicine", "Adolescent Medicine Physician"),
    TaxonomyEntry(
        "207QG0300X", "Family Medicine", "Geriatric Medicine", "Geriatric Medicine (Family Medicine) Physician"
    ),
    TaxonomyEntry("207QS0010X", "Family Medicine", "Sports Medicine", "Sports Medicine (Family Medicine) Physician"),
    TaxonomyEntry("207QS1201X", "Family Medicine", "Sleep Medicine", "Sleep Medicine (Family Medicine) Physician"),
    # General Practice / Hospitalist
    TaxonomyEntry("208D00000X", "General Practice", "", "General Practice Physician"),
    TaxonomyEntry("208M00000X", "Hospitalist", "", "Hospitalist Physician"),
    # Internal Medicine (largest classification - includes cardiology, GI, pulm, etc.)
    TaxonomyEntry("207R00000X", "Internal Medicine", "", "Internal Medicine Physician"),
    TaxonomyEntry(
        "207RA0001X",
        "Internal Medicine",
        "Advanced Heart Failure and Transplant Cardiology",
        "Advanced Heart Failure Physician",
    ),
    TaxonomyEntry(
        "207RA0002X", "Internal Medicine", "Adult Congenital Heart Disease", "Adult Congenital Heart Disease Physician"
    ),
    TaxonomyEntry(
        "207RA0201X", "Internal Medicine", "Allergy & Immunology", "Allergy & Immunology (Internal Medicine) Physician"
    ),
    TaxonomyEntry("207RC0000X", "Internal Medicine", "Cardiovascular Disease", "Cardiovascular Disease Physician"),
    TaxonomyEntry(
        "207RC0001X",
        "Internal Medicine",
        "Clinical Cardiac Electrophysiology",
        "Clinical Cardiac Electrophysiology Physician",
    ),
    TaxonomyEntry(
        "207RC0200X",
        "Internal Medicine",
        "Critical Care Medicine",
        "Critical Care Medicine (Internal Medicine) Physician",
    ),
    TaxonomyEntry("207RE0101X", "Internal Medicine", "Endocrinology, Diabetes & Metabolism", "Endocrinology Physician"),
    TaxonomyEntry("207RG0100X", "Internal Medicine", "Gastroenterology", "Gastroenterology Physician"),
    TaxonomyEntry(
        "207RG0300X", "Internal Medicine", "Geriatric Medicine", "Geriatric Medicine (Internal Medicine) Physician"
    ),
    TaxonomyEntry("207RH0000X", "Internal Medicine", "Hematology", "Hematology Physician"),
    TaxonomyEntry("207RH0003X", "Internal Medicine", "Hematology & Oncology", "Hematology & Oncology Physician"),
    TaxonomyEntry("207RI0008X", "Internal Medicine", "Hepatology", "Hepatology Physician"),
    TaxonomyEntry("207RH0005X", "Internal Medicine", "Hypertension Specialist", "Hypertension Specialist Physician"),
    TaxonomyEntry("207RI0200X", "Internal Medicine", "Infectious Disease", "Infectious Disease Physician"),
    TaxonomyEntry(
        "207RI0011X", "Internal Medicine", "Interventional Cardiology", "Interventional Cardiology Physician"
    ),
    TaxonomyEntry("207RX0202X", "Internal Medicine", "Medical Oncology", "Medical Oncology Physician"),
    TaxonomyEntry("207RN0300X", "Internal Medicine", "Nephrology", "Nephrology Physician"),
    TaxonomyEntry("207RP1001X", "Internal Medicine", "Pulmonary Disease", "Pulmonary Disease Physician"),
    TaxonomyEntry("207RR0500X", "Internal Medicine", "Rheumatology", "Rheumatology Physician"),
    TaxonomyEntry("207RS0012X", "Internal Medicine", "Sleep Medicine", "Sleep Medicine (Internal Medicine) Physician"),
    TaxonomyEntry(
        "207RS0010X", "Internal Medicine", "Sports Medicine", "Sports Medicine (Internal Medicine) Physician"
    ),
    TaxonomyEntry("207RT0003X", "Internal Medicine", "Transplant Hepatology", "Transplant Hepatology Physician"),
    # Neurological Surgery
    TaxonomyEntry("207T00000X", "Neurological Surgery", "", "Neurological Surgery Physician"),
    # Nuclear Medicine
    TaxonomyEntry("207U00000X", "Nuclear Medicine", "", "Nuclear Medicine Physician"),
    TaxonomyEntry("207UN0901X", "Nuclear Medicine", "Nuclear Cardiology", "Nuclear Cardiology Physician"),
    TaxonomyEntry("207UN0902X", "Nuclear Medicine", "Nuclear Imaging & Therapy", "Nuclear Imaging & Therapy Physician"),
    # Obstetrics & Gynecology
    TaxonomyEntry("207V00000X", "Obstetrics & Gynecology", "", "Obstetrics & Gynecology Physician"),
    TaxonomyEntry(
        "207VC0200X", "Obstetrics & Gynecology", "Critical Care Medicine", "Critical Care Medicine (OB/GYN) Physician"
    ),
    TaxonomyEntry("207VX0201X", "Obstetrics & Gynecology", "Gynecologic Oncology", "Gynecologic Oncology Physician"),
    TaxonomyEntry("207VG0400X", "Obstetrics & Gynecology", "Gynecology", "Gynecology Physician"),
    TaxonomyEntry(
        "207VM0101X", "Obstetrics & Gynecology", "Maternal & Fetal Medicine", "Maternal & Fetal Medicine Physician"
    ),
    TaxonomyEntry("207VX0000X", "Obstetrics & Gynecology", "Obstetrics", "Obstetrics Physician"),
    TaxonomyEntry(
        "207VE0102X", "Obstetrics & Gynecology", "Reproductive Endocrinology", "Reproductive Endocrinology Physician"
    ),
    # Ophthalmology
    TaxonomyEntry("207W00000X", "Ophthalmology", "", "Ophthalmology Physician"),
    TaxonomyEntry("207WX0120X", "Ophthalmology", "Cornea and External Diseases", "Cornea Specialist Physician"),
    TaxonomyEntry("207WX0009X", "Ophthalmology", "Glaucoma Specialist", "Glaucoma Specialist Physician"),
    TaxonomyEntry("207WX0107X", "Ophthalmology", "Retina Specialist", "Retina Specialist Physician"),
    # Orthopaedic Surgery
    TaxonomyEntry("207X00000X", "Orthopaedic Surgery", "", "Orthopaedic Surgery Physician"),
    TaxonomyEntry(
        "207XS0114X",
        "Orthopaedic Surgery",
        "Adult Reconstructive Orthopaedic Surgery",
        "Adult Reconstructive Orthopaedic Surgery Physician",
    ),
    TaxonomyEntry(
        "207XX0004X", "Orthopaedic Surgery", "Foot and Ankle Surgery", "Orthopaedic Foot and Ankle Surgery Physician"
    ),
    TaxonomyEntry("207XS0106X", "Orthopaedic Surgery", "Hand Surgery", "Orthopaedic Hand Surgery Physician"),
    TaxonomyEntry("207XS0117X", "Orthopaedic Surgery", "Orthopaedic Surgery of the Spine", "Spine Surgery Physician"),
    TaxonomyEntry("207XX0801X", "Orthopaedic Surgery", "Orthopaedic Trauma", "Orthopaedic Trauma Physician"),
    TaxonomyEntry(
        "207XP3100X", "Orthopaedic Surgery", "Pediatric Orthopaedic Surgery", "Pediatric Orthopaedic Surgery Physician"
    ),
    TaxonomyEntry(
        "207XX0005X", "Orthopaedic Surgery", "Sports Medicine", "Sports Medicine (Orthopaedic Surgery) Physician"
    ),
    # Otolaryngology
    TaxonomyEntry("207Y00000X", "Otolaryngology", "", "Otolaryngology Physician"),
    TaxonomyEntry("207YP0228X", "Otolaryngology", "Otolaryngic Allergy", "Otolaryngic Allergy Physician"),
    TaxonomyEntry("207YX0905X", "Otolaryngology", "Facial Plastic Surgery", "Facial Plastic Surgery Physician"),
    TaxonomyEntry("207YP0004X", "Otolaryngology", "Sleep Medicine", "Sleep Medicine (Otolaryngology) Physician"),
    # Pathology
    TaxonomyEntry("207Z00000X", "Pathology", "", "Pathology Physician"),
    TaxonomyEntry("207ZB0001X", "Pathology", "Blood Banking & Transfusion Medicine", "Blood Banking Physician"),
    TaxonomyEntry("207ZD0900X", "Pathology", "Cytopathology", "Cytopathology Physician"),
    TaxonomyEntry("207ZF0201X", "Pathology", "Forensic Pathology", "Forensic Pathology Physician"),
    TaxonomyEntry("207ZH0000X", "Pathology", "Hematology", "Hematology (Pathology) Physician"),
    TaxonomyEntry("207ZN0500X", "Pathology", "Neuropathology", "Neuropathology Physician"),
    # Pediatrics
    TaxonomyEntry("208000000X", "Pediatrics", "", "Pediatrics Physician"),
    TaxonomyEntry("2080A0000X", "Pediatrics", "Adolescent Medicine", "Adolescent Medicine (Pediatrics) Physician"),
    TaxonomyEntry("2080C0008X", "Pediatrics", "Child Abuse Pediatrics", "Child Abuse Pediatrics Physician"),
    TaxonomyEntry(
        "2080I0007X",
        "Pediatrics",
        "Clinical & Laboratory Immunology",
        "Clinical & Laboratory Immunology (Pediatrics) Physician",
    ),
    TaxonomyEntry(
        "2080P0006X",
        "Pediatrics",
        "Developmental-Behavioral Pediatrics",
        "Developmental-Behavioral Pediatrics Physician",
    ),
    TaxonomyEntry(
        "2080H0002X",
        "Pediatrics",
        "Hospice and Palliative Medicine",
        "Hospice and Palliative Medicine (Pediatrics) Physician",
    ),
    TaxonomyEntry("2080N0001X", "Pediatrics", "Neonatal-Perinatal Medicine", "Neonatal-Perinatal Medicine Physician"),
    TaxonomyEntry(
        "2080P0008X", "Pediatrics", "Neurodevelopmental Disabilities", "Neurodevelopmental Disabilities Physician"
    ),
    TaxonomyEntry("2080P0201X", "Pediatrics", "Pediatric Allergy/Immunology", "Pediatric Allergy/Immunology Physician"),
    TaxonomyEntry("2080P0202X", "Pediatrics", "Pediatric Cardiology", "Pediatric Cardiology Physician"),
    TaxonomyEntry(
        "2080P0203X", "Pediatrics", "Pediatric Critical Care Medicine", "Pediatric Critical Care Medicine Physician"
    ),
    TaxonomyEntry(
        "2080P0204X",
        "Pediatrics",
        "Pediatric Emergency Medicine",
        "Pediatric Emergency Medicine (Pediatrics) Physician",
    ),
    TaxonomyEntry("2080P0205X", "Pediatrics", "Pediatric Endocrinology", "Pediatric Endocrinology Physician"),
    TaxonomyEntry("2080P0206X", "Pediatrics", "Pediatric Gastroenterology", "Pediatric Gastroenterology Physician"),
    TaxonomyEntry(
        "2080P0207X", "Pediatrics", "Pediatric Hematology-Oncology", "Pediatric Hematology-Oncology Physician"
    ),
    TaxonomyEntry(
        "2080P0208X", "Pediatrics", "Pediatric Infectious Diseases", "Pediatric Infectious Diseases Physician"
    ),
    TaxonomyEntry("2080P0210X", "Pediatrics", "Pediatric Nephrology", "Pediatric Nephrology Physician"),
    TaxonomyEntry("2080P0214X", "Pediatrics", "Pediatric Pulmonology", "Pediatric Pulmonology Physician"),
    TaxonomyEntry("2080P0216X", "Pediatrics", "Pediatric Rheumatology", "Pediatric Rheumatology Physician"),
    TaxonomyEntry("2080S0012X", "Pediatrics", "Sleep Medicine", "Sleep Medicine (Pediatrics) Physician"),
    TaxonomyEntry("2080S0010X", "Pediatrics", "Sports Medicine", "Sports Medicine (Pediatrics) Physician"),
    TaxonomyEntry(
        "2080T0004X", "Pediatrics", "Pediatric Transplant Hepatology", "Pediatric Transplant Hepatology Physician"
    ),
    # Physical Medicine & Rehabilitation
    TaxonomyEntry(
        "208100000X", "Physical Medicine & Rehabilitation", "", "Physical Medicine & Rehabilitation Physician"
    ),
    TaxonomyEntry(
        "2081H0002X",
        "Physical Medicine & Rehabilitation",
        "Hospice and Palliative Medicine",
        "Hospice and Palliative Medicine (PM&R) Physician",
    ),
    TaxonomyEntry(
        "2081N0001X",
        "Physical Medicine & Rehabilitation",
        "Neuromuscular Medicine",
        "Neuromuscular Medicine (PM&R) Physician",
    ),
    TaxonomyEntry(
        "2081P2900X", "Physical Medicine & Rehabilitation", "Pain Medicine", "Pain Medicine (PM&R) Physician"
    ),
    TaxonomyEntry(
        "2081P0010X",
        "Physical Medicine & Rehabilitation",
        "Pediatric Rehabilitation Medicine",
        "Pediatric Rehabilitation Medicine Physician",
    ),
    TaxonomyEntry(
        "2081S0010X", "Physical Medicine & Rehabilitation", "Sports Medicine", "Sports Medicine (PM&R) Physician"
    ),
    TaxonomyEntry(
        "2081P0004X",
        "Physical Medicine & Rehabilitation",
        "Spinal Cord Injury Medicine",
        "Spinal Cord Injury Medicine Physician",
    ),
    # Plastic Surgery
    TaxonomyEntry("208200000X", "Plastic Surgery", "", "Plastic Surgery Physician"),
    TaxonomyEntry(
        "2082S0099X",
        "Plastic Surgery",
        "Plastic Surgery Within the Head and Neck",
        "Plastic Surgery Within the Head and Neck Physician",
    ),
    TaxonomyEntry(
        "2082S0105X", "Plastic Surgery", "Surgery of the Hand", "Surgery of the Hand (Plastic Surgery) Physician"
    ),
    # Preventive Medicine
    TaxonomyEntry("208300000X", "Preventive Medicine", "", "Preventive Medicine Physician"),
    TaxonomyEntry("2083A0100X", "Preventive Medicine", "Aerospace Medicine", "Aerospace Medicine Physician"),
    TaxonomyEntry(
        "2083B0002X", "Preventive Medicine", "Obesity Medicine", "Obesity Medicine (Preventive Medicine) Physician"
    ),
    TaxonomyEntry(
        "2083P0500X",
        "Preventive Medicine",
        "Preventive Medicine/Occupational Environmental Medicine",
        "Occupational Medicine Physician",
    ),
    TaxonomyEntry(
        "2083P0901X", "Preventive Medicine", "Public Health & General Preventive Medicine", "Public Health Physician"
    ),
    # Psychiatry & Neurology
    TaxonomyEntry(
        "2084A0401X", "Psychiatry & Neurology", "Addiction Medicine", "Addiction Medicine (Psychiatry) Physician"
    ),
    TaxonomyEntry("2084A2900X", "Psychiatry & Neurology", "Neurocritical Care", "Neurocritical Care Physician"),
    TaxonomyEntry(
        "2084B0002X",
        "Psychiatry & Neurology",
        "Obesity Medicine",
        "Obesity Medicine (Psychiatry & Neurology) Physician",
    ),
    TaxonomyEntry(
        "2084D0003X", "Psychiatry & Neurology", "Diagnostic Neuroimaging", "Diagnostic Neuroimaging Physician"
    ),
    TaxonomyEntry("2084F0202X", "Psychiatry & Neurology", "Forensic Psychiatry", "Forensic Psychiatry Physician"),
    TaxonomyEntry(
        "2084H0002X",
        "Psychiatry & Neurology",
        "Hospice and Palliative Medicine",
        "Hospice and Palliative Medicine (Psychiatry) Physician",
    ),
    TaxonomyEntry("2084N0008X", "Psychiatry & Neurology", "Neuromuscular Medicine", "Neuromuscular Medicine Physician"),
    TaxonomyEntry("2084N0400X", "Psychiatry & Neurology", "Neurology", "Neurology Physician"),
    TaxonomyEntry(
        "2084N0402X",
        "Psychiatry & Neurology",
        "Neurology with Special Qualifications in Child Neurology",
        "Child Neurology Physician",
    ),
    TaxonomyEntry(
        "2084N0600X", "Psychiatry & Neurology", "Clinical Neurophysiology", "Clinical Neurophysiology Physician"
    ),
    TaxonomyEntry(
        "2084P0005X",
        "Psychiatry & Neurology",
        "Neurodevelopmental Disabilities",
        "Neurodevelopmental Disabilities (Psychiatry) Physician",
    ),
    TaxonomyEntry("2084P0800X", "Psychiatry & Neurology", "Psychiatry", "Psychiatry Physician"),
    TaxonomyEntry("2084P0802X", "Psychiatry & Neurology", "Addiction Psychiatry", "Addiction Psychiatry Physician"),
    TaxonomyEntry(
        "2084P0804X",
        "Psychiatry & Neurology",
        "Child & Adolescent Psychiatry",
        "Child & Adolescent Psychiatry Physician",
    ),
    TaxonomyEntry(
        "2084P0805X",
        "Psychiatry & Neurology",
        "Consultation-Liaison Psychiatry",
        "Consultation-Liaison Psychiatry Physician",
    ),
    TaxonomyEntry(
        "2084P2900X", "Psychiatry & Neurology", "Pain Medicine", "Pain Medicine (Psychiatry & Neurology) Physician"
    ),
    TaxonomyEntry(
        "2084S0010X", "Psychiatry & Neurology", "Sports Medicine", "Sports Medicine (Psychiatry & Neurology) Physician"
    ),
    TaxonomyEntry(
        "2084S0012X", "Psychiatry & Neurology", "Sleep Medicine", "Sleep Medicine (Psychiatry & Neurology) Physician"
    ),
    TaxonomyEntry("2084V0102X", "Psychiatry & Neurology", "Vascular Neurology", "Vascular Neurology Physician"),
    # Radiology
    TaxonomyEntry("2085B0100X", "Radiology", "Body Imaging", "Body Imaging Physician"),
    TaxonomyEntry(
        "2085D0003X", "Radiology", "Diagnostic Neuroimaging", "Diagnostic Neuroimaging (Radiology) Physician"
    ),
    TaxonomyEntry(
        "2085H0002X",
        "Radiology",
        "Hospice and Palliative Medicine",
        "Hospice and Palliative Medicine (Radiology) Physician",
    ),
    TaxonomyEntry("2085N0700X", "Radiology", "Neuroradiology", "Neuroradiology Physician"),
    TaxonomyEntry("2085N0904X", "Radiology", "Nuclear Radiology", "Nuclear Radiology Physician"),
    TaxonomyEntry("2085P0229X", "Radiology", "Pediatric Radiology", "Pediatric Radiology Physician"),
    TaxonomyEntry("2085R0001X", "Radiology", "Radiation Oncology", "Radiation Oncology Physician"),
    TaxonomyEntry("2085R0202X", "Radiology", "Diagnostic Radiology", "Diagnostic Radiology Physician"),
    TaxonomyEntry("2085R0203X", "Radiology", "Therapeutic Radiology", "Therapeutic Radiology Physician"),
    TaxonomyEntry(
        "2085R0204X",
        "Radiology",
        "Vascular & Interventional Radiology",
        "Vascular & Interventional Radiology Physician",
    ),
    TaxonomyEntry("2085R0205X", "Radiology", "Radiological Physics", "Radiological Physics Physician"),
    # Surgery
    TaxonomyEntry("208600000X", "Surgery", "", "Surgery Physician"),
    TaxonomyEntry(
        "2086H0002X",
        "Surgery",
        "Hospice and Palliative Medicine",
        "Hospice and Palliative Medicine (Surgery) Physician",
    ),
    TaxonomyEntry("2086S0120X", "Surgery", "Pediatric Surgery", "Pediatric Surgery Physician"),
    TaxonomyEntry(
        "2086S0122X", "Surgery", "Plastic and Reconstructive Surgery", "Plastic and Reconstructive Surgery Physician"
    ),
    TaxonomyEntry("2086S0105X", "Surgery", "Surgery of the Hand", "Surgery of the Hand Physician"),
    TaxonomyEntry("2086S0102X", "Surgery", "Surgical Critical Care", "Surgical Critical Care Physician"),
    TaxonomyEntry("2086X0206X", "Surgery", "Surgical Oncology", "Surgical Oncology Physician"),
    TaxonomyEntry("2086S0127X", "Surgery", "Trauma Surgery", "Trauma Surgery Physician"),
    TaxonomyEntry("2086S0129X", "Surgery", "Vascular Surgery", "Vascular Surgery Physician"),
    # Thoracic Surgery
    TaxonomyEntry("208G00000X", "Thoracic Surgery (Cardiothoracic Vascular Surgery)", "", "Thoracic Surgery Physician"),
    TaxonomyEntry(
        "2086S0130X",
        "Thoracic Surgery (Cardiothoracic Vascular Surgery)",
        "Congenital Cardiac Surgery",
        "Congenital Cardiac Surgery Physician",
    ),
    # Urology
    TaxonomyEntry("208800000X", "Urology", "", "Urology Physician"),
    TaxonomyEntry(
        "2088P0231X", "Urology", "Female Pelvic Medicine and Reconstructive Surgery", "Female Pelvic Medicine Physician"
    ),
    TaxonomyEntry("2088F0040X", "Urology", "Pediatric Urology", "Pediatric Urology Physician"),
]


# Build lookup indexes on module load
_classification_index: dict[str, str] = {}
_specialization_to_classification: dict[str, str] = {}
_display_name_index: dict[str, str] = {}
_all_names: dict[str, str] = {}

for _entry in PHYSICIAN_TAXONOMY:
    _cls_lower = _entry.classification.lower()
    _spec_lower = _entry.specialization.lower()
    _display_lower = _entry.display_name.lower()

    _classification_index[_cls_lower] = _entry.classification
    if _spec_lower:
        _specialization_to_classification[_spec_lower] = _entry.classification
    _display_name_index[_display_lower] = _entry.classification
    _all_names[_cls_lower] = _entry.classification
    if _spec_lower:
        _all_names[_spec_lower] = _entry.classification

# Common aliases not in the official taxonomy
_ALIASES: dict[str, str] = {
    "cardiology": "Internal Medicine",
    "cardiac electrophysiology": "Internal Medicine",
    "cardiac electrophysiologist": "Internal Medicine",
    "interventional cardiologist": "Internal Medicine",
    "cardiologist": "Internal Medicine",
    "heart failure": "Internal Medicine",
    "heart disease": "Internal Medicine",
    "hospitalist": "Internal Medicine",
    "hospital medicine": "Internal Medicine",
    "gi": "Internal Medicine",
    "gi medicine": "Internal Medicine",
    "pulmonology": "Internal Medicine",
    "pulmonologist": "Internal Medicine",
    "lung medicine": "Internal Medicine",
    "respiratory medicine": "Internal Medicine",
    "nephrologist": "Internal Medicine",
    "oncology": "Internal Medicine",
    "oncologist": "Internal Medicine",
    "hematologist": "Internal Medicine",
    "rheumatologist": "Internal Medicine",
    "endocrinologist": "Internal Medicine",
    "hepatologist": "Internal Medicine",
    "infectious disease specialist": "Internal Medicine",
    "internist": "Internal Medicine",
    "ob/gyn": "Obstetrics & Gynecology",
    "obgyn": "Obstetrics & Gynecology",
    "gynecologist": "Obstetrics & Gynecology",
    "obstetrician": "Obstetrics & Gynecology",
    "reproductive medicine": "Obstetrics & Gynecology",
    "maternal-fetal medicine": "Obstetrics & Gynecology",
    "orthopedics": "Orthopaedic Surgery",
    "orthopedic surgery": "Orthopaedic Surgery",
    "orthopedic surgeon": "Orthopaedic Surgery",
    "spine surgeon": "Orthopaedic Surgery",
    "sports medicine surgeon": "Orthopaedic Surgery",
    "joint replacement surgeon": "Orthopaedic Surgery",
    "psychiatrist": "Psychiatry & Neurology",
    "psychiatry": "Psychiatry & Neurology",
    "neurologist": "Psychiatry & Neurology",
    "neurology": "Psychiatry & Neurology",
    "child psychiatrist": "Psychiatry & Neurology",
    "behavioral health": "Psychiatry & Neurology",
    "mental health": "Psychiatry & Neurology",
    "neuropsychiatry": "Psychiatry & Neurology",
    "epileptologist": "Psychiatry & Neurology",
    "movement disorders": "Psychiatry & Neurology",
    "stroke neurologist": "Psychiatry & Neurology",
    "anesthesiologist": "Anesthesiology",
    "anesthesia": "Anesthesiology",
    "pain management": "Anesthesiology",
    "pain medicine": "Anesthesiology",
    "critical care anesthesiology": "Anesthesiology",
    "dermatologist": "Dermatology",
    "skin specialist": "Dermatology",
    "cosmetic dermatology": "Dermatology",
    "mohs surgeon": "Dermatology",
    "emergency physician": "Emergency Medicine",
    "er physician": "Emergency Medicine",
    "er doctor": "Emergency Medicine",
    "trauma physician": "Emergency Medicine",
    "acute care": "Emergency Medicine",
    "radiologist": "Radiology",
    "diagnostic radiology": "Radiology",
    "interventional radiology": "Radiology",
    "neuroradiology": "Radiology",
    "urologist": "Urology",
    "urologic surgeon": "Urology",
    "urologic oncology": "Urology",
    "pediatrician": "Pediatrics",
    "pediatric medicine": "Pediatrics",
    "neonatologist": "Pediatrics",
    "neonatal medicine": "Pediatrics",
    "child health": "Pediatrics",
    "family physician": "Family Medicine",
    "family doctor": "Family Medicine",
    "family practice": "Family Medicine",
    "general practitioner": "General Practice",
    "general surgeon": "Surgery",
    "surgeon": "Surgery",
    "vascular surgeon": "Surgery",
    "trauma surgeon": "Surgery",
    "surgical oncologist": "Surgery",
    "cardiothoracic surgeon": "Thoracic Surgery (Cardiothoracic Vascular Surgery)",
    "thoracic surgeon": "Thoracic Surgery (Cardiothoracic Vascular Surgery)",
    "pathologist": "Pathology",
    "ophthalmologist": "Ophthalmology",
    "eye doctor": "Ophthalmology",
    "ent": "Otolaryngology",
    "ent specialist": "Otolaryngology",
    "ear nose throat": "Otolaryngology",
    "physiatrist": "Physical Medicine & Rehabilitation",
    "rehab medicine": "Physical Medicine & Rehabilitation",
    "pm&r": "Physical Medicine & Rehabilitation",
    "plastic surgeon": "Plastic Surgery",
    "reconstructive surgeon": "Plastic Surgery",
    "preventive medicine": "Preventive Medicine",
    "occupational medicine": "Preventive Medicine",
    "public health physician": "Preventive Medicine",
    "nuclear medicine": "Nuclear Medicine",
    "nuclear cardiologist": "Nuclear Medicine",
}


# Classifications that share patients / have overlapping scope
_RELATED_CLASSIFICATIONS: dict[str, set[str]] = {
    "Internal Medicine": {"Family Medicine", "General Practice", "Hospitalist", "Pediatrics"},
    "Family Medicine": {"Internal Medicine", "General Practice", "Pediatrics"},
    "General Practice": {"Internal Medicine", "Family Medicine"},
    "Hospitalist": {"Internal Medicine", "Family Medicine"},
    "Pediatrics": {"Family Medicine", "Internal Medicine"},
    "Emergency Medicine": {"Internal Medicine", "Surgery", "Anesthesiology"},
    "Surgery": {
        "Orthopaedic Surgery",
        "Thoracic Surgery (Cardiothoracic Vascular Surgery)",
        "Plastic Surgery",
        "Colon & Rectal Surgery",
    },
    "Orthopaedic Surgery": {"Surgery", "Physical Medicine & Rehabilitation"},
    "Psychiatry & Neurology": {"Internal Medicine", "Pediatrics"},
    "Obstetrics & Gynecology": {"Surgery", "Internal Medicine"},
    "Anesthesiology": {"Emergency Medicine", "Internal Medicine"},
    "Radiology": {"Nuclear Medicine"},
    "Nuclear Medicine": {"Radiology", "Internal Medicine"},
    "Physical Medicine & Rehabilitation": {"Orthopaedic Surgery", "Psychiatry & Neurology"},
    "Pathology": set(),
    "Ophthalmology": set(),
    "Otolaryngology": {"Surgery"},
    "Dermatology": set(),
    "Urology": {"Surgery"},
    "Plastic Surgery": {"Surgery", "Dermatology"},
    "Preventive Medicine": {"Internal Medicine", "Family Medicine"},
}


def normalize_specialty(name: str | None) -> str:
    """Map any specialty name to its NPI classification.

    Checks in order:
    1. Exact classification match
    2. Exact specialization match (maps to parent classification)
    3. Alias lookup (common names, abbreviations, -ist forms)
    4. Substring match against all names
    5. Returns input unchanged if no match found
    """
    if not name:
        return name or ""

    name_lower = name.lower().strip()
    if not name_lower:
        return ""

    if name_lower in _classification_index:
        return _classification_index[name_lower]

    if name_lower in _specialization_to_classification:
        return _specialization_to_classification[name_lower]

    if name_lower in _ALIASES:
        return _ALIASES[name_lower]

    for known_name, classification in _all_names.items():
        if name_lower in known_name or known_name in name_lower:
            return classification

    for alias, classification in _ALIASES.items():
        if name_lower in alias or alias in name_lower:
            return classification

    return name


def specialty_distance(spec_a: str, spec_b: str) -> float:
    """Compute distance between two specialties using NPI taxonomy.

    Returns:
        0.0 - Same classification (perfect match)
        0.3 - Related classifications (shared patient scope)
        0.7 - Same grouping but unrelated classifications
        1.0 - Completely unrelated
    """
    cls_a = normalize_specialty(spec_a)
    cls_b = normalize_specialty(spec_b)

    if cls_a == cls_b:
        return 0.0

    related_a = _RELATED_CLASSIFICATIONS.get(cls_a, set())
    related_b = _RELATED_CLASSIFICATIONS.get(cls_b, set())
    if cls_b in related_a or cls_a in related_b:
        return 0.3

    return 0.7


def find_related(classification: str) -> list[str]:
    """Find all specializations under a classification."""
    cls_normalized = normalize_specialty(classification)
    return [e.specialization for e in PHYSICIAN_TAXONOMY if e.classification == cls_normalized and e.specialization]


def score_specialty(candidate_specialty: str, required_specialty: str, adjacent: list[str]) -> float:
    """Score specialty match using NPI taxonomy distance.

    This replaces the hardcoded synonym map approach.
    """
    dist = specialty_distance(candidate_specialty, required_specialty)

    if dist == 0.0:
        return 1.0
    if dist <= 0.3:
        return 0.7

    for adj in adjacent:
        adj_dist = specialty_distance(candidate_specialty, adj)
        if adj_dist == 0.0:
            return 0.6
        if adj_dist <= 0.3:
            return 0.5

    return 0.1
