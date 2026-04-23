#!/usr/bin/env python3
"""Generate a complete synthetic systematic review to demonstrate the pipeline.

Topic: Efficacy of transcription factor X inhibition on tumour response
in solid malignancies -- a fictional but plausible oncology review.
"""

from __future__ import annotations

import random
import sys
from pathlib import Path

# Ensure scripts/ is on the path
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from review_common import (
    BIAS_DIR,
    EXTRACTION_DIR,
    PROTOCOL_DIR,
    QUERIES_DIR,
    RETRIEVAL_DIR,
    REVIEW_ROOT,
    SCREENING_DIR,
    write_csv,
    write_yaml,
)
from review_retrieve import deduplicate, write_dedup_log, write_normalized, write_screening_input
from review_screen import (
    ALL_SCREENING_COLUMNS,
    apply_decisions,
    init_screening_log,
    promote_to_fulltext,
)
from review_extract import init_extraction_table
from review_bias import init_bias_table
from review_prisma import generate_all

# Reproducible random seed
random.seed(42)

# ---------------------------------------------------------------------------
# Synthetic data generators
# ---------------------------------------------------------------------------

FIRST_AUTHORS = [
    "Zhang", "Smith", "Park", "Garcia", "Chen", "Kim", "Patel", "Müller",
    "Tanaka", "Silva", "Johnson", "Lee", "Brown", "Wang", "Anderson",
    "Suzuki", "Martinez", "Thompson", "Yamamoto", "Taylor", "Wilson",
    "Nakamura", "Davis", "Sato", "Rodriguez", "Watanabe", "Clark",
    "Kobayashi", "Lewis", "Ito", "Walker", "Takahashi", "Robinson",
    "Yoshida", "Hall", "Saito", "Young", "Kato", "Allen", "Matsumoto",
]

JOURNALS = [
    "J Clin Oncol", "Cancer Res", "Nat Med", "Lancet Oncol", "Ann Oncol",
    "Clin Cancer Res", "JAMA Oncol", "Br J Cancer", "Eur J Cancer",
    "Int J Cancer", "Oncogene", "Mol Cancer Ther", "Cancer Discov",
    "Cell Rep Med", "Sci Transl Med",
]

TA_EXCLUDE_REASONS = [
    "wrong population",
    "wrong intervention",
    "not primary research",
    "animal study only",
    "review or commentary",
    "duplicate publication",
    "wrong outcome",
    "pediatric only",
]

FT_EXCLUDE_REASONS = [
    "insufficient outcome data",
    "wrong comparator",
    "conference abstract only",
    "overlapping cohort",
    "wrong study design",
]

STUDY_DESIGNS = ["RCT", "cohort", "case-control", "single-arm trial"]
OUTCOMES = ["overall response rate", "progression-free survival", "overall survival"]
MEASURES = ["odds ratio", "hazard ratio", "mean difference"]
ROB2_JUDGMENTS = ["low", "some_concerns", "high"]


def _make_record(idx: int, source_db: str) -> dict[str, str]:
    author = random.choice(FIRST_AUTHORS)
    year = random.randint(2015, 2025)
    journal = random.choice(JOURNALS)
    title_words = random.sample(
        [
            "inhibition", "transcription", "factor", "X", "tumour", "response",
            "solid", "malignancy", "phase", "II", "trial", "cohort", "analysis",
            "biomarker", "expression", "pathway", "resistance", "combination",
            "immunotherapy", "chemotherapy", "targeted", "therapy", "survival",
            "efficacy", "safety", "clinical", "outcome", "patient", "treatment",
        ],
        k=random.randint(6, 10),
    )
    title = " ".join(title_words).capitalize()
    doi = f"10.1000/demo.{year}.{idx:04d}"
    pmid = str(30000000 + idx)

    return {
        "record_id": f"R{idx:04d}",
        "pmid": pmid,
        "doi": doi,
        "title": title,
        "authors": f"{author} et al.",
        "year": str(year),
        "abstract": f"Background: This study evaluates transcription factor X inhibition. "
                     f"Methods: A {random.choice(STUDY_DESIGNS).lower()} of {random.randint(30, 500)} patients. "
                     f"Results: The primary endpoint was met with p={random.uniform(0.001, 0.1):.3f}. "
                     f"Conclusions: TF-X inhibition shows promise in {random.choice(['NSCLC', 'CRC', 'breast cancer', 'melanoma', 'RCC'])}.",
        "source_db": source_db,
    }


def _make_duplicate(original: dict[str, str], new_idx: int, new_db: str) -> dict[str, str]:
    """Create a duplicate record (same DOI and title, different source)."""
    dup = dict(original)
    dup["record_id"] = f"R{new_idx:04d}"
    dup["source_db"] = new_db
    return dup


# ---------------------------------------------------------------------------
# Demo pipeline
# ---------------------------------------------------------------------------


def run_demo() -> None:
    """Run the complete demo pipeline."""
    print("=== Generating Synthetic Systematic Review ===\n")

    # --- Protocol ---
    print("1. Creating protocol...")
    protocol = {
        "protocol_id": "sr_demo_001",
        "title": "Efficacy of transcription factor X inhibition on tumour response in solid malignancies: a systematic review",
        "version": "1.0.0",
        "status": "frozen",
        "question": {
            "population": "Adults with histologically confirmed solid malignancies",
            "intervention_or_exposure": "Transcription factor X (TF-X) inhibitor monotherapy or combination",
            "comparator": "Standard of care, placebo, or active comparator",
            "outcomes": [
                "Overall response rate (ORR)",
                "Progression-free survival (PFS)",
                "Overall survival (OS)",
                "Adverse event profile",
            ],
            "study_types": ["RCT", "prospective cohort", "single-arm trial"],
        },
        "inclusion_criteria": [
            "Adults aged 18+ with confirmed solid malignancy",
            "Received TF-X inhibitor as intervention",
            "Reported at least one primary outcome",
            "Published 2015-2025",
            "English language",
        ],
        "exclusion_criteria": [
            "Animal or in-vitro studies only",
            "Haematological malignancies",
            "Reviews, editorials, or commentaries",
            "Paediatric populations",
            "Conference abstracts without full-text",
        ],
        "databases": ["PubMed", "Europe PMC"],
        "primary_outcomes": ["Overall response rate", "Progression-free survival"],
        "secondary_outcomes": ["Overall survival", "Grade 3+ adverse events"],
        "registration": {
            "registry": "internal_frozen_protocol",
            "registration_id": "sr_demo_001_frozen",
            "date": "2026-04-09",
        },
        "amendments": [],
    }
    write_yaml(PROTOCOL_DIR / "protocol.yml", protocol)

    # --- Queries ---
    print("2. Creating search queries...")
    pubmed_records = [_make_record(i, "PubMed") for i in range(1, 91)]
    epmc_unique = [_make_record(i, "Europe PMC") for i in range(91, 151)]

    # Create 30 duplicates in Europe PMC (same DOI/title as some PubMed records)
    epmc_dups = [
        _make_duplicate(pubmed_records[i], 150 + i, "Europe PMC")
        for i in random.sample(range(len(pubmed_records)), 30)
    ]
    epmc_records = epmc_unique + epmc_dups

    # Write raw exports
    raw_dir = RETRIEVAL_DIR / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    fieldnames = ["record_id", "pmid", "doi", "title", "authors", "year", "abstract", "source_db"]
    write_csv(raw_dir / "pubmed_export.csv", pubmed_records, fieldnames)
    write_csv(raw_dir / "epmc_export.csv", epmc_records, fieldnames)

    query_pubmed = {
        "query_id": "query_01_pubmed",
        "protocol_id": "sr_demo_001",
        "database": "PubMed",
        "query_text": '("transcription factor X" OR "TF-X inhibitor") AND (tumour OR tumor) AND (response OR survival)',
        "filters": {
            "date_range": "2015-01-01 to 2025-12-31",
            "language": "English",
            "article_types": ["Journal Article", "Clinical Trial"],
        },
        "date_run": "2026-03-15",
        "export_format": "csv",
        "hit_count": len(pubmed_records),
        "export_file": "retrieval/raw/pubmed_export.csv",
    }
    query_epmc = {
        "query_id": "query_02_epmc",
        "protocol_id": "sr_demo_001",
        "database": "Europe PMC",
        "query_text": '("transcription factor X" OR "TF-X inhibitor") AND (tumour OR tumor)',
        "filters": {
            "date_range": "2015-01-01 to 2025-12-31",
            "language": "English",
            "article_types": ["Research Article"],
        },
        "date_run": "2026-03-15",
        "export_format": "csv",
        "hit_count": len(epmc_records),
        "export_file": "retrieval/raw/epmc_export.csv",
    }
    write_yaml(QUERIES_DIR / "query_01_pubmed.yml", query_pubmed)
    write_yaml(QUERIES_DIR / "query_02_epmc.yml", query_epmc)

    # --- Retrieval & dedup ---
    print("3. Running retrieval and deduplication...")
    all_records = pubmed_records + epmc_records
    write_normalized(all_records)
    unique, removed = deduplicate(all_records)
    write_dedup_log(removed)
    write_screening_input(unique)
    print(f"   {len(all_records)} raw -> {len(removed)} duplicates -> {len(unique)} unique")

    # --- Screening: title/abstract ---
    print("4. Initializing screening log...")
    init_screening_log()

    # Generate title/abstract decisions
    print("5. Applying title/abstract screening decisions...")
    ta_decisions = []
    n_ta_include = 40
    for i, rec in enumerate(unique):
        if i < n_ta_include:
            ta_decisions.append({
                "record_id": rec["record_id"],
                "stage": "title_abstract",
                "decision": "include",
                "exclusion_reason": "",
                "reviewer": "reviewer_A",
                "timestamp": "2026-03-20T10:00:00",
            })
        else:
            ta_decisions.append({
                "record_id": rec["record_id"],
                "stage": "title_abstract",
                "decision": "exclude",
                "exclusion_reason": random.choice(TA_EXCLUDE_REASONS),
                "reviewer": "reviewer_A",
                "timestamp": "2026-03-20T10:00:00",
            })

    dec_path = SCREENING_DIR / "ta_decisions_batch.csv"
    dec_fields = ["record_id", "stage", "decision", "exclusion_reason", "reviewer", "timestamp"]
    write_csv(dec_path, ta_decisions, dec_fields)
    apply_decisions(decisions_path=dec_path)

    # --- Screening: full-text ---
    print("6. Promoting to full-text screening...")
    promote_to_fulltext()

    print("7. Applying full-text screening decisions...")
    screening_log = load_screening_log_raw()
    ft_records = [r for r in screening_log if r["stage"] == "full_text"]
    n_ft_include = 25
    ft_decisions = []
    for i, rec in enumerate(ft_records):
        if i < n_ft_include:
            ft_decisions.append({
                "record_id": rec["record_id"],
                "stage": "full_text",
                "decision": "include",
                "exclusion_reason": "",
                "reviewer": "reviewer_B",
                "timestamp": "2026-04-01T14:00:00",
            })
        else:
            ft_decisions.append({
                "record_id": rec["record_id"],
                "stage": "full_text",
                "decision": "exclude",
                "exclusion_reason": random.choice(FT_EXCLUDE_REASONS),
                "reviewer": "reviewer_B",
                "timestamp": "2026-04-01T14:00:00",
            })

    dec_path2 = SCREENING_DIR / "ft_decisions_batch.csv"
    write_csv(dec_path2, ft_decisions, dec_fields)
    apply_decisions(decisions_path=dec_path2)

    # --- Extraction ---
    print("8. Initializing extraction table...")
    init_extraction_table()

    # Fill extraction with synthetic data
    print("9. Filling extraction table with synthetic data...")
    from review_common import EXTRACTION_OPTIONAL_COLUMNS, EXTRACTION_REQUIRED_COLUMNS, load_csv
    ext_path = EXTRACTION_DIR / "extraction_table.csv"
    ext_rows = load_csv(ext_path)
    for row in ext_rows:
        row["study_design"] = random.choice(STUDY_DESIGNS)
        row["population"] = f"Adults with {random.choice(['NSCLC', 'CRC', 'breast cancer', 'melanoma', 'RCC'])}"
        row["intervention"] = "TF-X inhibitor"
        row["comparator"] = random.choice(["placebo", "standard chemotherapy", "active comparator"])
        row["sample_size"] = str(random.randint(30, 500))
        row["outcome_name"] = random.choice(OUTCOMES)
        row["outcome_measure"] = random.choice(MEASURES)
        row["outcome_timing"] = f"{random.choice([6, 12, 18, 24])} months"
        effect = round(random.uniform(0.3, 1.5), 2)
        row["effect_value"] = str(effect)
        row["ci_lower"] = str(round(effect - random.uniform(0.1, 0.3), 2))
        row["ci_upper"] = str(round(effect + random.uniform(0.1, 0.3), 2))
        row["p_value"] = str(round(random.uniform(0.001, 0.08), 3))
        row["extractor"] = "extractor_A"
        row["timestamp"] = "2026-04-05T09:00:00"

    fieldnames = EXTRACTION_REQUIRED_COLUMNS + EXTRACTION_OPTIONAL_COLUMNS
    write_csv(ext_path, ext_rows, fieldnames)

    # --- Bias ---
    print("10. Initializing bias assessment table...")
    init_bias_table(tool="rob2")

    # Fill bias with synthetic judgments
    print("11. Filling bias assessments with synthetic judgments...")
    from review_common import BIAS_REQUIRED_COLUMNS, ROB2_DOMAINS
    bias_path = BIAS_DIR / "bias_assessments.csv"
    bias_rows = load_csv(bias_path)
    for row in bias_rows:
        domain_judgments = []
        for d in ROB2_DOMAINS:
            j = random.choice(ROB2_JUDGMENTS)
            row[d] = j
            domain_judgments.append(j)
        # Overall is the worst domain judgment
        if "high" in domain_judgments:
            row["overall_judgment"] = "high"
        elif "some_concerns" in domain_judgments:
            row["overall_judgment"] = "some_concerns"
        else:
            row["overall_judgment"] = "low"
        row["assessor"] = "assessor_A"
        row["ai_assisted"] = "false"
        row["timestamp"] = "2026-04-07T11:00:00"

    bias_fields = BIAS_REQUIRED_COLUMNS + ROB2_DOMAINS
    write_csv(bias_path, bias_rows, bias_fields)

    # --- PRISMA ---
    print("12. Generating PRISMA outputs...")
    paths = generate_all()
    for name, path in paths.items():
        print(f"   {name}: {path}")

    print("\n=== Demo Complete ===")
    print(f"All artifacts written under: {REVIEW_ROOT}")


def load_screening_log_raw():
    """Load screening log without going through review_common (avoids import issues)."""
    from review_common import load_csv, SCREENING_DIR
    return load_csv(SCREENING_DIR / "screening_log.csv")


if __name__ == "__main__":
    run_demo()
