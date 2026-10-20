import json
import os
import pytest

from lib import (zip5, unit_bucket, days_between, trailing_window,
                 approx_gfa_per_unit, carry_cost, max_build_budget)


class TestLeakageGuard:

    def test_window_closes_strictly_before_the_issue_year(self):
        for year in range(2015, 2027):
            for y in trailing_window(year):
                assert int(y) < year, (
                    f"window for {year} includes {y}, which the developer could "
                    f"not have known when the permit was issued")

    def test_window_is_the_two_preceding_years(self):
        assert trailing_window(2022) == ["2020", "2021"]
        assert trailing_window(2022, n=3) == ["2019", "2020", "2021"]

    def test_window_never_includes_the_issue_year_itself(self):
        assert "2022" not in trailing_window(2022)

    def test_missing_issue_year_yields_no_window(self):
        assert trailing_window(None) == []


class TestDaysBetween:
    def test_direction_is_a_to_b(self):
        assert days_between("2024-01-01T00:00:00Z", "2024-01-11T00:00:00Z") == 10

    def test_negative_when_b_precedes_a(self):
        assert days_between("2024-01-11T00:00:00Z", "2024-01-01T00:00:00Z") == -10

    @pytest.mark.parametrize("a,b", [
        (None, "2024-01-01T00:00:00Z"),
        ("2024-01-01T00:00:00Z", None),
        (None, None),
        ("", "2024-01-01T00:00:00Z"),
    ])
    def test_missing_dates_return_none_instead_of_raising(self, a, b):
        assert days_between(a, b) is None


class TestUnitBucket:
    def test_none_and_zero_are_different_facts(self):
        assert unit_bucket(None) != unit_bucket(0)

    @pytest.mark.parametrize("n,expected", [
        (1, "1"), (2, "2-4"), (4, "2-4"), (5, "5-19"), (19, "5-19"), (20, "20+"),
    ])
    def test_boundaries(self, n, expected):
        assert unit_bucket(n) == expected


class TestGfa:
    def test_guards_zero_units(self):
        assert approx_gfa_per_unit(800, 3, 0) is None

    @pytest.mark.parametrize("area,stories,units", [
        (None, 3, 1), (800, None, 1), (800, 3, None),
    ])
    def test_guards_missing_inputs(self, area, stories, units):
        assert approx_gfa_per_unit(area, stories, units) is None

    def test_single_family_lands_in_a_plausible_range(self):
        assert 2000 < approx_gfa_per_unit(800, 3, 1) < 3000


class TestCarryCost:
    RATE = 0.09

    def test_longer_build_costs_more(self):
        short = carry_cost(30_000, 300_000, 410, 58, self.RATE)
        long_ = carry_cost(30_000, 300_000, 691, 58, self.RATE)
        assert long_ > short

    def test_land_carries_the_whole_period_construction_does_not(self):
        during = carry_cost(30_000, 300_000, 500, 100, self.RATE)
        after  = carry_cost(30_000, 300_000, 400, 200, self.RATE)
        assert after > during

    def test_zero_rate_is_free(self):
        assert carry_cost(30_000, 300_000, 500, 100, 0.0) == 0


class TestMaxBuildBudget:
    def test_slower_market_allows_a_smaller_budget(self):
        fast = max_build_budget(400_000, 30_000, 410, 58, 0.09, 0.15)
        slow = max_build_budget(400_000, 30_000, 691, 58, 0.09, 0.15)
        assert slow < fast

    def test_round_trip_against_carry_cost(self):
        price, land, build, sell, rate, hurdle = 400_000, 30_000, 500, 60, 0.09, 0.15
        hard  = max_build_budget(price, land, build, sell, rate, hurdle)
        carry = carry_cost(land, hard, build, sell, rate)
        basis = land + hard + carry
        annualised = ((price - basis) / basis) * 365 / (build + sell)
        assert annualised == pytest.approx(hurdle, rel=1e-6)

    def test_higher_hurdle_allows_a_smaller_budget(self):
        lo = max_build_budget(400_000, 30_000, 500, 60, 0.09, 0.10)
        hi = max_build_budget(400_000, 30_000, 500, 60, 0.09, 0.20)
        assert hi < lo


def test_zip5():
    assert zip5("19146-1234") == "19146"
    assert zip5("19146") == "19146"
    assert zip5(None) is None
    assert zip5("") is None


BUILT = "data/built.json"
pytestmark_data = pytest.mark.skipif(
    not os.path.exists(BUILT), reason="run build.py first")


@pytest.fixture(scope="module")
def built():
    if not os.path.exists(BUILT):
        pytest.skip("run build.py first")
    return json.load(open(BUILT))


@pytestmark_data
class TestPopulationInvariants:

    def test_every_permit_is_accounted_for(self, built):
        total = built["matched"] + built["no_deeds"] + built["no_deed_after_co"]
        assert total == built["permits_total"], (
            "a permit fell through a branch in the join")

    def test_record_count_equals_population(self, built):
        assert len(built["records"]) == built["permits_total"], (
            "records should hold EVERY permit, matched or not - the unmatched "
            "ones carry days_observed, which is how censoring gets quantified")

    def test_duration_counters_sum(self, built):
        assert sum(built["build_counts"].values()) == built["permits_total"]
        assert sum(built["gfa_counts"].values()) == built["permits_total"]

    def test_no_permit_predates_its_own_issue_date(self, built):
        bad = [r for r in built["records"]
               if r["permit_to_co_days"] is not None and r["permit_to_co_days"] < 0]
        assert not bad, f"{len(bad)} certificates of occupancy predate issue"


@pytestmark_data
class TestJoinInvariants:

    def test_matched_records_carry_a_sale(self, built):
        for r in built["records"]:
            if r["matched"]:
                assert r["sale_date"] and r["price"] is not None
            else:
                assert r["sale_date"] is None and r["days"] is None

    def test_first_sale_is_always_after_completion(self, built):
        for r in built["records"]:
            if r["matched"]:
                assert r["sale_date"] >= r["co_date"], (
                    f"{r['permitnumber']} sold before it was occupiable")
                assert r["days"] >= 0

    def test_censoring_time_exists_on_every_record(self, built):
        for r in built["records"]:
            assert r["days_observed"] is not None, (
                "drop this and the censoring bias cannot be measured")

    def test_unobservable_records_can_never_be_matched(self, built):
        for r in built["records"]:
            if r["days_observed"] <= 0:
                assert not r["matched"], (
                    f"{r['permitnumber']}: C of O postdates the deed snapshot "
                    f"by {-r['days_observed']} days, yet it matched a sale")
                assert r["observable"] is False


@pytestmark_data
class TestQualityFlags:

    def test_flags_are_none_on_unmatched_rows(self, built):
        for r in built["records"]:
            if not r["matched"]:
                assert r["nominal"] is None
                assert r["bulk"] is None
                assert r["clean"] is None

    def test_clean_implies_matched_and_arms_length(self, built):
        for r in built["records"]:
            if r["clean"]:
                assert r["matched"]
                assert r["price"] >= 10_000
                assert r["property_count"] == 1