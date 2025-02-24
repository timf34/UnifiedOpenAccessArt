import torch
from PIL import Image
import requests
from transformers import AutoProcessor, AutoModelForZeroShotImageClassification


def run_clip():
    # Load model and processor
    processor = AutoProcessor.from_pretrained("openai/clip-vit-base-patch32")
    model = AutoModelForZeroShotImageClassification.from_pretrained("openai/clip-vit-base-patch32")

    # Move model to GPU if available
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = model.to(device)

    # Download a sample image (or use a local path to your image)
    url = "http://images.cocodataset.org/val2017/000000039769.jpg"
    image = Image.open(requests.get(url, stream=True).raw)

    # Prepare candidate labels
    candidate_labels = ["a photo of a cat", "a photo of a dog", "a photo of a bird"]

    # Process the image and labels
    inputs = processor(
        images=image,
        text=candidate_labels,
        return_tensors="pt",
        padding=True
    )

    # Move inputs to the same device as the model
    inputs = {k: v.to(device) for k, v in inputs.items()}

    # Get predictions
    with torch.no_grad():
        outputs = model(**inputs)
        logits = outputs.logits_per_image[0]
        probs = logits.softmax(dim=0)

    # Print results
    for label, prob in zip(candidate_labels, probs):
        print(f"{label}: {prob.item():.3f}")


if __name__ == "__main__":
    run_clip()