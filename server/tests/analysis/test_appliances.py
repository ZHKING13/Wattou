from datetime import datetime, timedelta, timezone
from uuid import uuid4

from wattou.analysis.appliances import assign, attribute, visible
from wattou.analysis.types import Activation, ApplianceSig, Sample

T0 = datetime(2026, 11, 2, tzinfo=timezone.utc)


def act(w, start_min=0, dur_min=10, pf=0.9):
    s = T0 + timedelta(minutes=start_min)
    return Activation(s, s + timedelta(minutes=dur_min), w, pf)


def test_same_appliance_grouped():
    acts = [act(w, i * 30) for i, w in enumerate([1090, 1110, 1100, 1080, 1120])]
    assigned, sigs = assign(acts, [])
    assert len(sigs) == 1 and sigs[0].n_obs == 5
    assert abs(sigs[0].delta_w - 1100) < 10
    assert {a_id for _, a_id in assigned} == {sigs[0].id}


def test_distinct_appliances():
    _, sigs = assign([act(120, 0, pf=0.8), act(1100, 30), act(118, 60, pf=0.8)], [])
    assert sorted(round(s.delta_w) for s in sigs) == [119, 1100]


def test_existing_signature_reused():
    known = ApplianceSig(uuid4(), "clim", 1100, 0.9, 10)
    assigned, sigs = assign([act(1105)], [known])
    assert assigned[0][1] == known.id and sigs[0].n_obs == 11 and sigs[0].label == "clim"


def test_promoted_after_three():
    _, sigs = assign([act(500, 0), act(500, 30)], [])
    assert visible(sigs) == []
    _, sigs = assign([act(500, 60)], sigs)
    assert len(visible(sigs)) == 1


def flat(minutes, p):
    return [Sample(T0 + timedelta(seconds=s), p) for s in range(minutes * 60)]


def test_attribution_sums_to_total():
    samples = flat(60, 1300)  # 1,3 kWh sur 1 h
    sig = ApplianceSig(uuid4(), "clim", 1100, 0.9, 5)
    assigned = [(act(1100, 0, 60), sig.id)]
    out = attribute(samples, assigned, [sig], {})
    assert abs(sum(out.values()) - 1.3) < 0.0013
    assert abs(out[str(sig.id)] - 1.1) < 1e-6
    assert out["autres"] >= 0


def test_attribution_clips_activation_to_window():
    samples = flat(60, 1100)
    sig = ApplianceSig(uuid4(), "clim", 1100, 0.9, 5)
    out = attribute(samples, [(act(1100, -30, 60), sig.id)], [sig], {})
    assert abs(out[str(sig.id)] - 0.55) < 1e-6


def test_plug_energy_not_double_counted():
    samples = flat(60, 1000)
    fer = ApplianceSig(uuid4(), "fer", 1000, 1.0, 5, device_id="prise-fer")
    out = attribute(samples, [(act(1000, 0, 60), fer.id)], [fer], {"prise-fer": 0.9})
    assert abs(out[str(fer.id)] - 0.9) < 1e-6
    assert abs(sum(out.values()) - 1.0) < 0.001
