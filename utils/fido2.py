# Copyright (C) 2022 Nitrokey GmbH
# SPDX-License-Identifier: CC0-1.0

from fido2.client import Fido2Client, PinRequiredError, UserInteraction
from fido2.hid import open_device
from fido2.server import Fido2Server
from fido2.webauthn import (
    AttestationConveyancePreference,
    AttestedCredentialData,
    AuthenticatorAttachment,
    PublicKeyCredentialRpEntity,
    PublicKeyCredentialUserEntity,
    ResidentKeyRequirement,
    UserVerificationRequirement,
)
from typing import Any, List, Optional


class NoInteraction(UserInteraction):
    def __init__(self, pin: Optional[str]) -> None:
        self.pin = pin

    def prompt_up(self) -> None:
        pass

    def request_pin(self, permissions: Any, rd_id: Any) -> str:
        if self.pin:
            return self.pin
        else:
            # missing type annotations in python-fido2
            raise PinRequiredError()  # type: ignore

    def request_uv(self, permissions: Any, rd_id: Any) -> bool:
        return True


class Fido2:
    def __init__(self, hidraw: str, pin: Optional[str] = None) -> None:
        device = open_device(f"/dev/{hidraw}")
        self.client = Fido2Client(
            device,
            "https://example.com",
            user_interaction=NoInteraction(pin),
        )
        self.server = Fido2Server(
            PublicKeyCredentialRpEntity(id="example.com", name="Example RP"),
            attestation=AttestationConveyancePreference.DIRECT,
        )

    def register(
        self,
        id: bytes,
        name: str,
        resident_key: bool = False,
        require_attestation: Optional[bool] = True,
    ) -> AttestedCredentialData:
        user = PublicKeyCredentialUserEntity(id=id, name=name)

        if resident_key:
            resident_key_requirement = ResidentKeyRequirement.REQUIRED
        else:
            resident_key_requirement = ResidentKeyRequirement.DISCOURAGED
        create_options, state = self.server.register_begin(
            user=user,
            user_verification=UserVerificationRequirement.DISCOURAGED,
            authenticator_attachment=AuthenticatorAttachment.CROSS_PLATFORM,
            resident_key_requirement=resident_key_requirement,
        )

        make_credential_result = self.client.make_credential(
            create_options["publicKey"],
        )
        if require_attestation:
            assert "x5c" in make_credential_result.attestation_object.att_stmt

        auth_data = self.server.register_complete(
            state,
            make_credential_result.client_data,
            make_credential_result.attestation_object,
        )
        assert auth_data.credential_data

        return auth_data.credential_data

    def authenticate(self, credentials: List[AttestedCredentialData]) -> None:
        request_options, state = self.server.authenticate_begin(
            credentials,
            user_verification=UserVerificationRequirement.DISCOURAGED,
        )

        get_assertion_result = self.client.get_assertion(
            request_options["publicKey"],
        )
        get_assertion_response = get_assertion_result.get_response(0)
        assert get_assertion_response.credential_id

        self.server.authenticate_complete(
            state,
            credentials,
            get_assertion_response.credential_id,
            get_assertion_response.client_data,
            get_assertion_response.authenticator_data,
            get_assertion_response.signature,
        )
