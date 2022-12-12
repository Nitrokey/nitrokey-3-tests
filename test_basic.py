# Copyright (C) 2022 Nitrokey GmbH
# SPDX-License-Identifier: CC0-1.0

import subprocess
from pexpect import spawn


def test_lsusb(device) -> None:
    devices = subprocess.check_output(
        ["lsusb", "-d", "20a0:42b2"]
    ).splitlines()
    assert len(devices) == 1


def test_list(device) -> None:
    p = spawn("nitropy nk3 list")
    p.expect("'Nitrokey 3' keys")
    p.expect(f"/dev/{device.hidraw}: Nitrokey 3 {device.serial}")
    # TODO: assert that there are no other keys


def test_fido(device) -> None:
    from fido2.client import Fido2Client
    from fido2.hid import open_device
    from fido2.server import Fido2Server
    from fido2.webauthn import (
        AttestationConveyancePreference,
        AuthenticatorAttachment,
        PublicKeyCredentialRpEntity,
        PublicKeyCredentialUserEntity,
        UserVerificationRequirement,
    )

    ctap_device = open_device(f"/dev/{device.hidraw}")
    client = Fido2Client(ctap_device, "https://example.com")
    server = Fido2Server(
        PublicKeyCredentialRpEntity(id="example.com", name="Example RP"),
        attestation=AttestationConveyancePreference.DIRECT,
    )
    uv = UserVerificationRequirement.DISCOURAGED
    user = PublicKeyCredentialUserEntity(id=b"user_id", name="A. User")

    create_options, state = server.register_begin(
        user=user,
        user_verification=uv,
        authenticator_attachment=AuthenticatorAttachment.CROSS_PLATFORM,
    )

    make_credential_result = client.make_credential(
        create_options["publicKey"],
    )
    assert "x5c" in make_credential_result.attestation_object.att_stmt

    auth_data = server.register_complete(
        state,
        make_credential_result.client_data,
        make_credential_result.attestation_object,
    )
    if not auth_data.credential_data:
        raise RuntimeError("Missing credential data in auth data")
    credentials = [auth_data.credential_data]

    request_options, state = server.authenticate_begin(
        credentials, user_verification=uv
    )

    get_assertion_result = client.get_assertion(request_options["publicKey"])
    get_assertion_response = get_assertion_result.get_response(0)
    if not get_assertion_response.credential_id:
        raise RuntimeError(
            "Missing credential ID in GetAssertion response"
        )

    server.authenticate_complete(
        state,
        credentials,
        get_assertion_response.credential_id,
        get_assertion_response.client_data,
        get_assertion_response.authenticator_data,
        get_assertion_response.signature,
    )
