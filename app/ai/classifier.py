from PIL import Image, ImageOps
from transformers import pipeline
import torch


class CivicImageClassifier:
    def __init__(self):
        self.device = 0 if torch.cuda.is_available() else -1

        # Multiple descriptions help CLIP distinguish similar hazards.
        self.prompt_sets = [
            {
                "Pothole": "a deep pothole in the middle of a paved road",
                "Road Damage": "cracked and broken asphalt road surface",
                "Streetlight Failure": "a broken or non-working street lamp beside a road",
                "Drainage Problem": "an open roadside drainage channel filled with dirty water or sewage",
                "Garbage Accumulation": "a pile of dumped household garbage and waste on a roadside",
                "Unrelated": "a photograph unrelated to civic infrastructure problems"
            },
            {
                "Pothole": "a vehicle road with a large circular hole in its asphalt surface",
                "Road Damage": "road surface showing long cracks and damaged pavement",
                "Streetlight Failure": "a damaged streetlight pole or broken street lamp",
                "Drainage Problem": "a blocked stormwater drain with stagnant water and drainage waste",
                "Garbage Accumulation": "overflowing garbage bins and scattered rubbish in a public area",
                "Unrelated": "a portrait, selfie, animal, food or indoor photograph"
            },
            {
                "Pothole": "a road crater with missing asphalt and exposed soil",
                "Road Damage": "a damaged road with uneven broken asphalt but no deep pothole",
                "Streetlight Failure": "a street lamp that is fallen, damaged or has a broken light",
                "Drainage Problem": "a concrete drainage gutter, manhole or sewer overflowing with wastewater",
                "Garbage Accumulation": "garbage dumped on a street or public roadside",
                "Unrelated": "a normal everyday photograph with no visible civic hazard"
            },
            {
                "Pothole": "a close-up photograph of a deep hole in a public road",
                "Road Damage": "a close-up photograph of cracks and fractures in road pavement",
                "Streetlight Failure": "a close-up photograph of damaged electrical street lighting infrastructure",
                "Drainage Problem": "a close-up photograph of a clogged roadside drain, sewer or open drainage system",
                "Garbage Accumulation": "a close-up photograph of accumulated solid waste in a public place",
                "Unrelated": "a photograph of an object or scene that is not a civic infrastructure issue"
            }
        ]

        self.classifier = pipeline(
            "zero-shot-image-classification",
            model="openai/clip-vit-base-patch32",
            device=self.device
        )

    def classify(self, image_path):
        with Image.open(image_path) as source:
            image = ImageOps.exif_transpose(source).convert("RGB")

        category_scores = {
            "Pothole": [],
            "Road Damage": [],
            "Streetlight Failure": [],
            "Drainage Problem": [],
            "Garbage Accumulation": [],
            "Unrelated": []
        }

        print("\n========== CIVIC AI IMAGE ANALYSIS ==========")

        # Run classification with four different prompt sets.
        for prompt_number, prompts in enumerate(self.prompt_sets, start=1):
            results = self.classifier(
                image,
                candidate_labels=list(prompts.values()),
                hypothesis_template="A photograph showing {}."
            )

            description_to_category = {
                description: category
                for category, description in prompts.items()
            }

            for result in results:
                category = description_to_category[result["label"]]
                category_scores[category].append(float(result["score"]))

            print(f"Prompt analysis {prompt_number}/4 completed")

        # Average scores across the four prompt sets.
        averaged_scores = {
            category: sum(scores) / len(scores)
            for category, scores in category_scores.items()
        }

        ranked = sorted(
            averaged_scores.items(),
            key=lambda item: item[1],
            reverse=True
        )

        for category, score in ranked:
            print(f"{category}: {score:.4f}")

        print("=============================================\n")

        best_category, best_score = ranked[0]
        second_score = ranked[1][1]
        margin = best_score - second_score

        # Conservative acceptance: uncertain images are rejected.
        if (
            best_category == "Unrelated"
            or best_score < 0.32
            or margin < 0.10
        ):
            return {
                "accepted": False,
                "category": None,
                "confidence": best_score,
                "message": (
                    "AI could not confidently identify a supported civic "
                    "hazard. Please upload a clearer photograph."
                )
            }

        return {
            "accepted": True,
            "category": best_category,
            "confidence": best_score,
            "message": f"AI detected: {best_category}"
        }


_classifier_instance = None


def get_classifier():
    global _classifier_instance

    if _classifier_instance is None:
        _classifier_instance = CivicImageClassifier()

    return _classifier_instance
