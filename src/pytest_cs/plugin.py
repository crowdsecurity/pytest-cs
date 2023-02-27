# -*- coding: utf-8 -*-

import pytest
import trustme

keep_kind_cluster = True


@pytest.fixture(scope='session')
def certs_dir(tmp_path_factory):
    def create(lapi_hostname, agent_ou='agent-ou'):
        path = tmp_path_factory.mktemp('certs')

        ca = trustme.CA()
        ca.cert_pem.write_to_path(path / 'ca.crt')

        lapi_cert = ca.issue_server_cert('localhost', lapi_hostname)
        lapi_cert.cert_chain_pems[0].write_to_path(path / 'lapi.crt')
        lapi_cert.private_key_pem.write_to_path(path / 'lapi.key')

        agent_cert = ca.issue_cert('agent', common_name='agent', organization_unit_name=agent_ou)
        agent_cert.cert_chain_pems[0].write_to_path(path / 'agent.crt')
        agent_cert.private_key_pem.write_to_path(path / 'agent.key')

        return path
    return create
