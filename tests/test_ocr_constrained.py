import unittest
from unittest.mock import patch

import numpy as np

from resonance.vision import ocr


class ConstrainedOcrTests(unittest.TestCase):
    def test_ctc_decode_limits_labels_to_allowed_characters(self):
        predictions = np.array(
            [
                [
                    [0.10, 0.80, 0.10, 0.90],
                    [0.10, 0.20, 0.70, 0.90],
                    [0.10, 0.80, 0.10, 0.90],
                ]
            ],
            dtype=np.float32,
        )
        character = ["blank", "1", "/", "A"]
        decoded = ocr._decode_ctc_output(predictions, character, frozenset("1/"))

        self.assertEqual(decoded[0][0], "1/1")
        self.assertAlmostEqual(decoded[0][1], (0.8 + 0.7 + 0.8) / 3)

    def test_number_predict_uses_numeric_recognition_path(self):
        predictions = np.array([[[0.10, 0.90, 0.00, 0.00]]], dtype=np.float32)
        image = np.zeros((24, 120, 3), dtype=np.uint8)

        with patch.object(ocr, "model") as fake_model:
            fake_model.text_recognizer.resize_norm_img.return_value = np.zeros(
                (3, 48, 320), dtype=np.float32
            )
            fake_model.text_recognizer.rec_input_name = "input"
            fake_model.text_recognizer.rec_output_name = ["output"]
            fake_model.text_recognizer.run.return_value = [predictions]
            fake_model.character = ["blank", "6", "/", "字"]
            fake_model.text_recognizer.postprocess_op.character = [
                "blank",
                "6",
                "/",
                "字",
            ]

            results = ocr.number_predict(image)

        self.assertEqual(results[0]["text"], "6")


if __name__ == "__main__":
    unittest.main()
