import pytest
from cognitive_memory.strategy.evaluation import evaluate_policy


def rows():
    return [dict(available_actions=["a","b"],selected_action=a,
                 behavior_policy={"a":0.5,"b":0.5},target_policy={"a":0.75,"b":0.25},
                 baseline_policy={"a":0.5,"b":0.5},q_values={"a":1.0,"b":0.0},
                 propensity=0.5,reward=1 if a=="a" else 0) for a in ["a","b"]*20]


def test_known_policy_values():
    r=evaluate_policy(rows())
    assert r["status"]=="evaluated"
    assert r["ips"]==pytest.approx(0.75)
    assert r["snips"]==pytest.approx(0.75)
    assert r["dr"]==pytest.approx(0.75)
    assert r["baseline_ips"]==pytest.approx(0.5)
    assert r["deploy_allowed"] is False


def test_missing_or_unsupported_propensity_is_insufficient():
    assert evaluate_policy([])["status"]=="insufficient"
    r=rows();r[0]["behavior_policy"]={"a":0.0,"b":1.0}
    assert evaluate_policy(r)["reason"]=="no_overlap"
    r=rows();r[0]["propensity"]=0.9
    assert evaluate_policy(r)["reason"]=="propensity_mismatch"
    r=rows();r[0]["reward"]=float("nan")
    assert evaluate_policy(r)["reason"]=="reward_missing"
