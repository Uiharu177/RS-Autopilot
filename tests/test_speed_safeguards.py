import unittest
from unittest.mock import patch

from resonance.solvers import exchange


class ExchangeCacheSafetyTests(unittest.TestCase):
    def setUp(self):
        exchange.OUTLET_TAP_CACHE.clear()

    def tearDown(self):
        exchange.OUTLET_TAP_CACHE.clear()

    def test_verified_cache_uses_only_the_matching_city_and_outlet(self):
        exchange.OUTLET_TAP_CACHE[("岚心城", "交易所")] = (900, 300)

        with patch("resonance.solvers.exchange.input_tap") as tap, patch(
            "resonance.solvers.exchange._wait_exchange_open", return_value=True
        ):
            self.assertTrue(exchange._try_cached_outlet("岚心城", "交易所"))

        tap.assert_called_once_with((900, 300))
        self.assertNotIn(("海角城", "交易所"), exchange.OUTLET_TAP_CACHE)

    def test_failed_cache_is_removed_and_allows_dynamic_ocr_fallback(self):
        key = ("岚心城", "交易所")
        exchange.OUTLET_TAP_CACHE[key] = (900, 300)

        with patch("resonance.solvers.exchange.input_tap"), patch(
            "resonance.solvers.exchange._wait_exchange_open", return_value=False
        ):
            self.assertFalse(exchange._try_cached_outlet(*key))

        self.assertNotIn(key, exchange.OUTLET_TAP_CACHE)


if __name__ == "__main__":
    unittest.main()
