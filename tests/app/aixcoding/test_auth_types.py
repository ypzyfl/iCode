# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""Wire-shape tests for the auth data types.

The backend envelope has two quirks the types must absorb (see the plan's
section 1.4): ``device/*`` answers under ``result`` while ``user/info``
answers under ``data``, and every field can be null or missing.
"""

from __future__ import annotations

import time

from aixcoding.auth import AccountInfo, DeviceCode, Environment, StoredCredential, TokenResult


def test_environment_str_is_plain_value() -> None:
    assert str(Environment.LOCAL) == "local"
    assert Environment.PROD.value == "prod"


def test_device_code_from_full_payload() -> None:
    payload = {
        "interval": 5,
        "device_code": "dc-1",
        "user_code": "YX8S-NOHS",
        "verification_uri": "http://127.0.0.1:7777/device/verify",
        "verification_uri_complete": "http://127.0.0.1:7777/device/verify?user_code=YX8S-NOHS",
        "expires_in": 600,
    }
    code = DeviceCode.from_payload(payload)
    assert code.device_code == "dc-1"
    assert code.user_code == "YX8S-NOHS"
    assert code.interval == 5
    assert code.expires_in == 600


def test_device_code_from_sparse_payload_defaults_zero() -> None:
    code = DeviceCode.from_payload({})
    assert code.device_code == ""
    assert code.interval == 0


def test_token_result_prefers_token_over_access_token() -> None:
    result = TokenResult.from_payload({"token": "primary", "access_token": "secondary"})
    assert result.token == "primary"


def test_token_result_falls_back_to_access_token() -> None:
    result = TokenResult.from_payload({"token": None, "access_token": "secondary"})
    assert result.token == "secondary"


def test_token_result_empty_payload_is_blank() -> None:
    result = TokenResult.from_payload({})
    assert result.token == ""
    assert result.refresh_token == ""


def test_account_info_maps_camel_case_fields() -> None:
    info = AccountInfo.from_payload(
        {
            "ehr": "8769092",
            "name": "大熊猫",
            "region": None,
            "deptName": "上海分中心技术平台研发部",
            "deptId": None,
            "isStWg": 1,
            "userType": 1,
        }
    )
    assert info.ehr == "8769092"
    assert info.name == "大熊猫"
    assert info.dept_name == "上海分中心技术平台研发部"
    assert info.region == ""
    assert info.is_st_wg == 1


def test_account_info_display_name_falls_back_to_ehr() -> None:
    assert AccountInfo(ehr="8769092", name="大熊猫").display_name == "大熊猫"
    assert AccountInfo(ehr="8769092").display_name == "8769092"


def test_stored_credential_round_trips_payload() -> None:
    credential = StoredCredential.issued_now(
        environment_id="prod",
        user_id="8769092",
        token="tok",
        refresh_token="ref",
        ehr="8769092",
    )
    payload = credential.to_payload()
    assert payload["environmentId"] == "prod"
    assert payload["purpose"] == "account_auth"
    assert payload["schemaVersion"] == 2

    restored = StoredCredential.from_payload(payload)
    assert restored.token == "tok"
    assert restored.refresh_token == "ref"
    assert restored.environment_id == "prod"
    assert restored.purpose == "account_auth"


def test_stored_credential_expiry_clock() -> None:
    expired = StoredCredential(environment_id="prod", user_id="u", token="t", expires_at=time.time() - 1)
    assert expired.is_expired

    live = StoredCredential.issued_now("prod", "u", "t", ttl_seconds=60)
    assert not live.is_expired
