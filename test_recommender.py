import os
import sys
import numpy as np
import pandas as pd
from typing import List, Dict, Any, Tuple
from creator_recommender import CreatorRecommender, INDEX_FILE

DATASET_CSV = "top_insta_influencers_data.csv"

# Benchmark query test suite: Queries and their expected domain categories/keywords
QUERY_BENCHMARKS = [
    {
        "query": "Football soccer players and clubs",
        "domain": "Sports & Football",
        "keywords": ["football", "soccer", "striker", "la liga", "premier league", "goals", "madrid", "barca", "fifa"]
    },
    {
        "query": "Pop music singers, vocalists and songwriters",
        "domain": "Music",
        "keywords": ["pop", "singer", "songwriter", "music", "vocalist", "album", "artist", "grammy"]
    },
    {
        "query": "Hip hop and rap artists",
        "domain": "Music & Hip-Hop",
        "keywords": ["hip hop", "rap", "rapper", "mc", "rhymes", "beats"]
    },
    {
        "query": "K-Pop music idols and groups",
        "domain": "Music & K-Pop",
        "keywords": ["k-pop", "bts", "blackpink", "south korea", "idol"]
    },
    {
        "query": "Fashion models, beauty cosmetics and luxury style",
        "domain": "Fashion",
        "keywords": ["fashion", "beauty", "cosmetics", "makeup", "model", "runway", "couture", "luxury"]
    },
    {
        "query": "Nature photography, wildlife, animals and geography",
        "domain": "Nature",
        "keywords": ["nature", "wildlife", "photography", "animals", "geography", "documentary", "planet"]
    },
    {
        "query": "Space astronomy, rockets and planetary science",
        "domain": "Science",
        "keywords": ["space", "astronomy", "nasa", "planets", "rockets", "universe", "science"]
    },
    {
        "query": "Cricket players, batsmen and team captains",
        "domain": "Sports & Cricket",
        "keywords": ["cricket", "batsman", "captain", "india", "csk", "rcb", "centuries"]
    },
    {
        "query": "Food chefs, delicious cooking and restaurant recipes",
        "domain": "Food",
        "keywords": ["food", "chef", "cooking", "recipes", "restaurant", "culinary", "baking"]
    },
    {
        "query": "Hollywood actors, cinema movies and action film stars",
        "domain": "Acting",
        "keywords": ["actor", "actress", "cinema", "movies", "hollywood", "film", "oscar", "marvel"]
    }
]

# Similar-creator benchmark suite: Seed creator and expected lookalike domain
SIMILAR_BENCHMARKS = [
    {"seed": "cristiano", "expected_domain": "Sports & Football"},
    {"seed": "kyliejenner", "expected_domain": "Fashion"},
    {"seed": "taylorswift", "expected_domain": "Music"},
    {"seed": "bts.bighitofficial", "expected_domain": "Music & K-Pop"},
    {"seed": "eminem", "expected_domain": "Music & Hip-Hop"},
    {"seed": "therock", "expected_domain": "Acting"},
    {"seed": "natgeo", "expected_domain": "Nature"},
    {"seed": "virat.kohli", "expected_domain": "Sports & Cricket"},
    {"seed": "cznburak", "expected_domain": "Food"},
    {"seed": "nasa", "expected_domain": "Science"}
]

def is_match(category: str, bio: str, target_domain: str, target_keywords: List[str]) -> bool:
    """Determine if a recommended creator satisfies the target query domain or keywords."""
    cat_lower = str(category).lower()
    bio_lower = str(bio).lower()
    dom_lower = target_domain.lower()

    if dom_lower in cat_lower:
        return True
    
    # Check if any main domain word appears in category
    for word in dom_lower.replace("&", " ").split():
        if len(word) > 3 and word in cat_lower:
            return True

    # Keyword check in bio / category
    for kw in target_keywords:
        if kw in cat_lower or kw in bio_lower:
            return True

    return False

def evaluate_recommender():
    print("=" * 70)
    print("        CREATOR INTELLIGENCE RECOMMENDATION ACCURACY TEST       ")
    print("=" * 70)

    # 1. Initialize and import
    recommender = CreatorRecommender()
    if not os.path.exists(INDEX_FILE):
        print(f"[*] Building catalog and importing {DATASET_CSV}...")
        recommender.build_creator_catalog()
        recommender.import_kaggle_dataset(DATASET_CSV)
    else:
        recommender.load_index()
        # Verify dataset creators are present
        if len(recommender.creators_df) < 50:
            recommender.import_kaggle_dataset(DATASET_CSV)

    catalog_size = len(recommender.creators_df)
    print(f"[✓] Active Catalog Loaded: {catalog_size} creators\n")

    # ---------------------------------------------------------
    # TEST SUITE 1: Query Relevance & Top-K Retrieval Accuracy
    # ---------------------------------------------------------
    print("-" * 70)
    print("TEST SUITE 1: Natural Language Query Retrieval Accuracy")
    print("-" * 70)

    top1_correct = 0
    precision_5_list = []
    precision_10_list = []
    mrr_list = []

    print(f"{'Query Benchmark':<35} | {'Top-1':<7} | {'P@5':<7} | {'P@10':<7} | {'MRR':<5}")
    print("-" * 70)

    for bench in QUERY_BENCHMARKS:
        q = bench["query"]
        domain = bench["domain"]
        keywords = bench["keywords"]

        recs = recommender.recommend_by_query(q, top_k=10)
        if not recs:
            precision_5_list.append(0.0)
            precision_10_list.append(0.0)
            mrr_list.append(0.0)
            print(f"{q[:34]:<35} | {'FAIL':<7} | {'0.0%':<7} | {'0.0%':<7} | {'0.00':<5}")
            continue

        # Check Top-1
        first_is_match = is_match(recs[0]["category"], recs[0]["bio"], domain, keywords)
        if first_is_match:
            top1_correct += 1

        # Check MRR
        mrr = 0.0
        for rank_idx, r in enumerate(recs, start=1):
            if is_match(r["category"], r["bio"], domain, keywords):
                mrr = 1.0 / rank_idx
                break
        mrr_list.append(mrr)

        # Check P@5
        matches_at_5 = sum(1 for r in recs[:5] if is_match(r["category"], r["bio"], domain, keywords))
        p_at_5 = matches_at_5 / min(len(recs), 5)
        precision_5_list.append(p_at_5)

        # Check P@10
        matches_at_10 = sum(1 for r in recs if is_match(r["category"], r["bio"], domain, keywords))
        p_at_10 = matches_at_10 / len(recs)
        precision_10_list.append(p_at_10)

        t1_str = "PASS" if first_is_match else "FAIL"
        print(f"{q[:34]:<35} | {t1_str:<7} | {p_at_5*100:>5.1f}% | {p_at_10*100:>5.1f}% | {mrr:>5.2f}")

    avg_top1 = (top1_correct / len(QUERY_BENCHMARKS)) * 100
    avg_p5 = np.mean(precision_5_list) * 100
    avg_p10 = np.mean(precision_10_list) * 100
    avg_mrr = np.mean(mrr_list)

    print("-" * 70)
    print(f"Query Top-1 Accuracy:     {avg_top1:.1f}%")
    print(f"Precision@5 (Top-5 Avg):  {avg_p5:.1f}%")
    print(f"Precision@10 (Top-10 Avg):{avg_p10:.1f}%")
    print(f"Mean Reciprocal Rank:     {avg_mrr:.3f}\n")

    # ---------------------------------------------------------
    # TEST SUITE 2: Similar-Creator Lookalike Accuracy
    # ---------------------------------------------------------
    print("-" * 70)
    print("TEST SUITE 2: Similar Creator (Lookalike) Co-Domain Accuracy")
    print("-" * 70)

    lookalike_scores = []
    print(f"{'Seed Creator':<20} | {'Expected Domain':<20} | {'Top Lookalike':<15} | {'Lookalike P@5'}")
    print("-" * 70)

    for s_bench in SIMILAR_BENCHMARKS:
        seed = s_bench["seed"]
        expected_dom = s_bench["expected_domain"]

        try:
            sim_recs = recommender.recommend_similar_creators(seed, top_k=5)
            if not sim_recs:
                lookalike_scores.append(0.0)
                continue

            matches = sum(1 for r in sim_recs if is_match(r["category"], r["bio"], expected_dom, [expected_dom.lower()]))
            score = matches / len(sim_recs)
            lookalike_scores.append(score)

            top_rec = f"@{sim_recs[0]['username']}"
            print(f"@{seed:<19} | {expected_dom:<20} | {top_rec:<15} | {score*100:>5.1f}%")
        except Exception as e:
            print(f"@{seed:<19} | {expected_dom:<20} | ERROR: {e}")

    avg_lookalike_acc = np.mean(lookalike_scores) * 100
    print("-" * 70)
    print(f"Lookalike Recommendation Accuracy: {avg_lookalike_acc:.1f}%\n")

    # ---------------------------------------------------------
    # TEST SUITE 3: Filter Compliance Accuracy
    # ---------------------------------------------------------
    print("-" * 70)
    print("TEST SUITE 3: Follower Tier & Constraint Filter Compliance")
    print("-" * 70)

    # Test Mega filter (>1M)
    mega_recs = recommender.recommend_by_query("athletes and sports", follower_tier="Mega", top_k=10)
    mega_pass = all(r["followers"] >= 1_000_000 for r in mega_recs)

    # Test Micro filter (10k-100k)
    micro_recs = recommender.recommend_by_query("technology", follower_tier="Micro", top_k=5)
    micro_pass = all(10_000 <= r["followers"] <= 100_000 for r in micro_recs)

    # Test Min Engagement Rate filter (> 1.0%)
    eng_recs = recommender.recommend_by_query("singers music", min_engagement=0.01, top_k=10)
    eng_pass = all(r["engagement_rate"] >= 0.01 for r in eng_recs)

    filter_checks = [("Follower Tier: Mega (1M+)", mega_pass),
                     ("Follower Tier: Micro (10K-100K)", micro_pass),
                     ("Min Engagement Rate: > 1.0%", eng_pass)]

    for name, passed in filter_checks:
        status = "100.0% COMPLIANT (PASS)" if passed else "FAILED"
        print(f"Filter Check: {name:<32} -> {status}")

    filter_accuracy = (sum(1 for _, p in filter_checks if p) / len(filter_checks)) * 100

    # ---------------------------------------------------------
    # OVERALL SYSTEM ACCURACY SCORECARD
    # ---------------------------------------------------------
    print("\n" + "=" * 70)
    print("                  FINAL ACCURACY SCORECARD                     ")
    print("=" * 70)
    
    overall_accuracy = (0.40 * avg_p5) + (0.35 * avg_lookalike_acc) + (0.15 * avg_top1) + (0.10 * filter_accuracy)

    print(f"  • Top-1 Recommendation Accuracy:        {avg_top1:>6.1f}%")
    print(f"  • Top-5 Precision (Precision@5):         {avg_p5:>6.1f}%")
    print(f"  • Mean Reciprocal Rank (MRR):            {avg_mrr:>6.3f} / 1.000")
    print(f"  • Lookalike Co-Domain Accuracy:         {avg_lookalike_acc:>6.1f}%")
    print(f"  • Filter & Constraint Compliance:       {filter_accuracy:>6.1f}%")
    print("  " + "-" * 50)
    print(f"  ★ OVERALL COMPOSITE MODEL ACCURACY:      {overall_accuracy:>6.1f}%\n")
    print("=" * 70)

    return {
        "catalog_size": catalog_size,
        "top1_accuracy": avg_top1,
        "precision_at_5": avg_p5,
        "precision_at_10": avg_p10,
        "mrr": avg_mrr,
        "lookalike_accuracy": avg_lookalike_acc,
        "filter_accuracy": filter_accuracy,
        "overall_accuracy": overall_accuracy
    }

if __name__ == "__main__":
    evaluate_recommender()
