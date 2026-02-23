import pytest

from src.utils import calcurate_hierarcihical_path

def test_calcurate_hierarcihical_path():
    config = [
        "interface GigabitEthernet0/1",
        " description Uplink to Core Switch",
        " ip address 192.168.1.1 255.255.255.0",
        "interface GigabitEthernet0/2",
        " description Connection to Server",
        " ip address 192.168.1.2 255.255.255.0"
    ]
    expected_paths = [
        ["interface GigabitEthernet0/1"],
        ["interface GigabitEthernet0/1", "description Uplink to Core Switch"],
        ["interface GigabitEthernet0/1", "ip address 192.168.1.1 255.255.255.0"],
        ["interface GigabitEthernet0/2"],
        ["interface GigabitEthernet0/2", "description Connection to Server"],
        ["interface GigabitEthernet0/2", "ip address 192.168.1.2 255.255.255.0"]
    ]
    assert calcurate_hierarcihical_path(config) == expected_paths