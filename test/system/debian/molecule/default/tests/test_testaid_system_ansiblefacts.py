import testaid

testinfra_hosts = testaid.hosts()


def test_testaid_system_ansiblefacts_present(host, testvars):
    assert 'ansible_distribution_version' in testvars['ansible_facts']


def test_testaid_system_ansiblefacts_reference(host, testvars):
    assert type(testvars['factref']) == str
