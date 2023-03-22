# -*- coding: utf-8 -*-

import pytest
import secrets
import string
import trustme

keep_kind_cluster = True


@pytest.fixture(scope='session')
def certs_dir(tmp_path_factory):
    def closure(lapi_hostname, agent_ou='agent-ou', bouncer_ou='bouncer-ou'):
        path = tmp_path_factory.mktemp('certs')

        ca = trustme.CA()
        ca.cert_pem.write_to_path(path / 'ca.crt')

        lapi_cert = ca.issue_server_cert('localhost', lapi_hostname)
        lapi_cert.cert_chain_pems[0].write_to_path(path / 'lapi.crt')
        lapi_cert.private_key_pem.write_to_path(path / 'lapi.key')

        agent_cert = ca.issue_cert('agent', common_name='agent', organization_unit_name=agent_ou)
        agent_cert.cert_chain_pems[0].write_to_path(path / 'agent.crt')
        agent_cert.private_key_pem.write_to_path(path / 'agent.key')

        bouncer_cert = ca.issue_cert('bouncer', common_name='bouncer', organization_unit_name=bouncer_ou)
        bouncer_cert.cert_chain_pems[0].write_to_path(path / 'bouncer.crt')
        bouncer_cert.private_key_pem.write_to_path(path / 'bouncer.key')

        return path
    yield closure


@pytest.fixture(scope='session')
def api_key_factory():
    def closure(alphabet=string.ascii_letters + string.digits):
        return ''.join(secrets.choice(alphabet) for i in range(32))
    yield closure
