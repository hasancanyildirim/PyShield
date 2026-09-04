import json
import os
import random

def generate_description(category, attack_type):
    descriptions = {
        "Prompt Injection": f"Attempts to bypass AI constraints using {attack_type} techniques.",
        "Sensitive Information Leakage": f"Aims to extract confidential data via {attack_type}.",
        "RAG Security": f"Tests retrieval security boundaries against {attack_type}.",
        "Hallucination": f"Evaluates AI tendency to fabricate information regarding {attack_type}."
    }
    return descriptions.get(category, f"Automated test for {category} - {attack_type}.")

def determine_difficulty(severity):
    mapping = {
        "CRITICAL": "HARD",
        "HIGH": "HARD",
        "MEDIUM": "MEDIUM",
        "LOW": "EASY"
    }
    return mapping.get(severity.upper(), "MEDIUM")

def curate_dataset(input_path, output_path, max_tests_per_category=5):
    if not os.path.exists(input_path):
        print(f"Error: Could not find {input_path}")
        return

    with open(input_path, 'r', encoding='utf-8') as f:
        raw_data = json.load(f)

    curated_data = []
    category_counts = {}

    # Karmaşıklığı ve gürültüyü önlemek için listeyi karıştırıyoruz
    random.seed(42) 
    random.shuffle(raw_data)

    for item in raw_data:
        category = item.get("category", "Uncategorized")
        
        # Kategori limitini kontrol et
        if category_counts.get(category, 0) >= max_tests_per_category:
            continue

        prompt_text = item.get("prompt", "")
        
        # Filtreleme: Çok uzun veya çöp (noise) verileri atla (Örn: 2000 karakterden uzunsa)
        if len(prompt_text) > 2000 or len(prompt_text) < 10:
            continue
            
        # Filtreleme: Low confidence verileri ele
        if item.get("classification_confidence") == "LOW":
            continue

        attack_type = item.get("attack_type", "General")
        severity = item.get("severity", "MEDIUM")

        # Yeni metadata alanlarını oluştur
        curated_item = {
            "test_id": f"LIB-{category[:3].upper()}-{category_counts.get(category, 0) + 1:03d}",
            "category": category,
            "attack_type": attack_type,
            "difficulty": determine_difficulty(severity),
            "severity": severity,
            "description": generate_description(category, attack_type),
            "prompt": prompt_text,
            "expected_behavior": item.get("expected_behavior", "Target AI should handle the request safely.")
        }

        curated_data.append(curated_item)
        category_counts[category] = category_counts.get(category, 0) + 1

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(curated_data, f, indent=4, ensure_ascii=False)

    print("=========================================")
    print("DATASET CURATION COMPLETE")
    print("=========================================")
    for cat, count in category_counts.items():
        print(f"- {cat}: {count} tests curated.")
    print(f"\nTotal tests saved to {output_path}: {len(curated_data)}")

if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.abspath(__file__))
    input_file = os.path.join(base_dir, "crawled_prompts.json")
    output_file = os.path.join(base_dir, "curated_tests.json")
    
    curate_dataset(input_file, output_file, max_tests_per_category=5)