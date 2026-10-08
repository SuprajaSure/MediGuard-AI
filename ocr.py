"""OCR utilities for prescription and medicine-pack images."""

import cv2
import easyocr


class PrescriptionOCR:
    def __init__(self):
        self.reader = easyocr.Reader(["en"], gpu=False)

    def _image_variants(self, image_path):
        image = cv2.imread(str(image_path))
        if image is None:
            raise ValueError("Could not load image")

        height, width = image.shape[:2]
        scale = max(1.0, min(4.0, 1000 / max(height, width)))
        upscaled = cv2.resize(
            image,
            None,
            fx=scale,
            fy=scale,
            interpolation=cv2.INTER_CUBIC,
        )
        gray = cv2.cvtColor(upscaled, cv2.COLOR_BGR2GRAY)
        enhanced = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(gray)

        return [image, upscaled, enhanced]

    def extract_text(self, image_path):
        snippets = []
        seen = set()

        for image in self._image_variants(image_path):
            results = self.reader.readtext(
                image,
                detail=1,
                paragraph=False,
                decoder="beamsearch",
            )
            for _, text, confidence in results:
                cleaned = " ".join(str(text).split()).strip()
                key = cleaned.lower()
                if len(cleaned) < 2 or key in seen:
                    continue
                # Low-confidence OCR is still useful for high-threshold drug
                # matching, but obvious one-character noise is discarded.
                if confidence < 0.02:
                    continue
                seen.add(key)
                snippets.append(cleaned)

        return "\n".join(snippets)

    def process_prescription(self, image_path):
        text = self.extract_text(image_path)
        return {
            "raw_text": text,
            "medicine_count": 0,
        }


if __name__ == "__main__":
    ocr = PrescriptionOCR()
    print(ocr.process_prescription("sample_prescription.jpg"))
