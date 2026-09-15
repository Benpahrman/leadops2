"""Unit and Integration Tests for GeoCountyResolver and County Docket Match Gate."""

import unittest

from agents.tools.geo_county_resolver import GeoCountyResolver, ResolvedLocation


class GeoCountyResolverTests(unittest.TestCase):
    def test_resolve_major_metros_offline(self):
        """Test authoritative offline resolution of key commercial metros to county and portal."""
        test_cases = [
            # City, State -> Expected County, Expected State Code
            ("Austin", "TX", "Travis County", "TX"),
            ("Houston", "TX", "Harris County", "TX"),
            ("Dallas", "TX", "Dallas County", "TX"),
            ("Fort Worth", "TX", "Tarrant County", "TX"),
            ("Arlington", "TX", "Tarrant County", "TX"),
            ("San Antonio", "TX", "Bexar County", "TX"),
            ("Plano", "TX", "Collin County", "TX"),
            ("Orlando", "FL", "Orange County", "FL"),
            ("Tampa", "FL", "Hillsborough County", "FL"),
            ("Miami", "FL", "Miami-Dade County", "FL"),
            ("Phoenix", "AZ", "Maricopa County", "AZ"),
            ("Scottsdale", "AZ", "Maricopa County", "AZ"),
            ("Chicago", "IL", "Cook County", "IL"),
            ("Naperville", "IL", "DuPage County", "IL"),
            ("Los Angeles", "CA", "Los Angeles County", "CA"),
            ("San Francisco", "CA", "San Francisco County", "CA"),
            ("Atlanta", "GA", "Fulton County", "GA"),
            ("Las Vegas", "NV", "Clark County", "NV"),
            ("Charlotte", "NC", "Mecklenburg County", "NC"),
            ("Seattle", "WA", "King County", "WA"),
        ]

        for city, state, expected_county, expected_st in test_cases:
            loc = GeoCountyResolver.resolve_location(city=city, state=state)
            self.assertEqual(loc.county, expected_county, f"Failed for {city}, {state}: got {loc.county}")
            self.assertEqual(loc.state_code, expected_st)
            self.assertTrue(loc.portal_name, f"Missing portal name for {city}, {state}")
            self.assertTrue(loc.portal_url.startswith("http"), f"Missing or invalid portal url for {city}, {state}")
            self.assertGreaterEqual(loc.confidence, 0.95)

    def test_state_name_normalization(self):
        """Test converting state names and mixed-case abbreviations to standard 2-letter codes."""
        self.assertEqual(GeoCountyResolver.normalize_state("Texas"), "TX")
        self.assertEqual(GeoCountyResolver.normalize_state("florida"), "FL")
        self.assertEqual(GeoCountyResolver.normalize_state("CALIFORNIA"), "CA")
        self.assertEqual(GeoCountyResolver.normalize_state("arizona"), "AZ")
        self.assertEqual(GeoCountyResolver.normalize_state("IL"), "IL")

    def test_parse_address_string(self):
        """Test extracting address, city, state, and zip from unstructured address snippets."""
        snip1 = "1200 Post Oak Blvd, Houston, TX 77056"
        p1 = GeoCountyResolver.parse_address_string(snip1)
        self.assertEqual(p1["city"], "Houston")
        self.assertEqual(p1["state"], "TX")
        self.assertEqual(p1["zip"], "77056")
        self.assertIn("1200 Post Oak Blvd", p1["address"])

        snip2 = "Austin, Texas 78701"
        p2 = GeoCountyResolver.parse_address_string(snip2)
        self.assertEqual(p2["city"], "Austin")
        self.assertEqual(p2["state"], "TX")
        self.assertEqual(p2["zip"], "78701")

        snip3 = "Scottsdale, AZ"
        p3 = GeoCountyResolver.parse_address_string(snip3)
        self.assertEqual(p3["city"], "Scottsdale")
        self.assertEqual(p3["state"], "AZ")

    def test_resolve_from_unstructured_address(self):
        """Test resolving county directly from a full street address string."""
        raw_addr = "701 Brazos St, Austin, TX 78701"
        loc = GeoCountyResolver.resolve_location(address=raw_addr)
        self.assertEqual(loc.city, "Austin")
        self.assertEqual(loc.county, "Travis County")
        self.assertEqual(loc.state_code, "TX")

    def test_validate_county_data_match_pass(self):
        """Test that sample records from matching county pass validation."""
        records = [
            {"case_number": "2026-00123", "county": "Travis County", "parties": "Estate of Miller"},
            {"case_number": "2026-00124", "court_name": "Travis County Probate Court", "parties": "Smith vs Jones"},
        ]
        ok, msg = GeoCountyResolver.validate_county_data_match("Travis County", records)
        self.assertTrue(ok)
        self.assertIn("Verified", msg)

    def test_validate_county_data_match_rejects_mismatch(self):
        """Test that sample records from an incorrect county are rejected with clear error."""
        records = [
            {"case_number": "2026-9999", "court": "Cook County Probate Division Court Portal", "parties": "Estate of Vance"},
        ]
        ok, msg = GeoCountyResolver.validate_county_data_match("Travis County", records)
        self.assertFalse(ok)
        self.assertIn("Jurisdiction mismatch", msg)
        self.assertIn("Cook County", msg)
        self.assertIn("Travis County", msg)


if __name__ == "__main__":
    unittest.main()
