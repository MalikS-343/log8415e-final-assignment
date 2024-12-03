import asyncio
import time
from aws import authorize_traffic_between_sgs, create_gatekeeper_sc, create_sg, get_default_vpc_id, create_instances, get_private_ips, wait_for_instances, get_public_dns_names
from benchmarking import send_requests
from constants import HTTP_PORT, PROXY_PORT, SSH_PORT, KEY_FILENAME
from enums import ProxyMode
from setups import setup_gatekeeper, setup_instance, setup_proxy, setup_trusted_host, start_proxy
import platform
import os

vpc_id = get_default_vpc_id()


# Create the Gatekeeper
gatekeeper_security_group_id = create_gatekeeper_sc(vpc_id)
gatekeeper_id   = create_instances('t2.large', 1, gatekeeper_security_group_id, 'gatekeeper')[0]

# Create the Trusted Host
trusted_host_sg_id = create_sg(vpc_id, 'trusted host sg')
trusted_host_id    = create_instances('t2.large', 1, trusted_host_sg_id, 'trusted host')[0]

authorize_traffic_between_sgs(trusted_host_sg_id, gatekeeper_security_group_id, SSH_PORT)
authorize_traffic_between_sgs(trusted_host_sg_id, gatekeeper_security_group_id, HTTP_PORT)
authorize_traffic_between_sgs(trusted_host_sg_id, gatekeeper_security_group_id, PROXY_PORT)

# Create the Proxy
proxy_sg_id = create_sg(vpc_id, 'proxy sg')
proxy_id    = create_instances('t2.large', 1, proxy_sg_id, 'proxy')[0]

authorize_traffic_between_sgs(proxy_sg_id, trusted_host_sg_id, SSH_PORT)
authorize_traffic_between_sgs(proxy_sg_id, trusted_host_sg_id, HTTP_PORT)
authorize_traffic_between_sgs(proxy_sg_id, trusted_host_sg_id, PROXY_PORT)

# Create the Instances
instances_sg_id = create_sg(vpc_id, 'instances sg')
master_id = create_instances('t2.micro', 1, instances_sg_id, 'master')[0]
worker1_id = create_instances('t2.micro', 1, instances_sg_id, 'worker1')[0]
worker2_id = create_instances('t2.micro', 1, instances_sg_id, 'worker2')[0]

instance_names = ['master', 'worker1', 'worker2']
instance_ids = [master_id, worker1_id, worker2_id]

authorize_traffic_between_sgs(instances_sg_id, trusted_host_sg_id, SSH_PORT)
authorize_traffic_between_sgs(instances_sg_id, trusted_host_sg_id, PROXY_PORT)
authorize_traffic_between_sgs(instances_sg_id, proxy_sg_id, HTTP_PORT)

# Wait for instances to be ready
wait_for_instances([gatekeeper_id, trusted_host_id, proxy_id, master_id, worker1_id, worker2_id])


# Setups
gatekeeper_dns          = get_public_dns_names([gatekeeper_id])[0]
private_gatekeeper_dns  = get_private_ips([gatekeeper_id])[0]
trusted_host_dns        = get_private_ips([trusted_host_id])[0]
proxy_dns               = get_private_ips([proxy_id])[0]
master_dns              = get_private_ips([master_id])[0]
worker1_dns             = get_private_ips([worker1_id])[0]
worker2_dns             = get_private_ips([worker2_id])[0]

if platform.system() == 'Linux':
    os.system(f"chmod 400 {KEY_FILENAME}")

setup_gatekeeper(gatekeeper_dns, trusted_host_dns)
setup_trusted_host(trusted_host_dns, private_gatekeeper_dns, proxy_dns, master_dns, worker1_dns, worker2_dns, [gatekeeper_dns])
setup_proxy(proxy_dns, trusted_host_dns, [gatekeeper_dns, trusted_host_dns])
with open('sysbench_benchmark_results.txt', 'w') as f:
    setup_instance(master_dns, trusted_host_dns, [gatekeeper_dns, trusted_host_dns], f)
    setup_instance(worker1_dns, trusted_host_dns, [gatekeeper_dns, trusted_host_dns], f)
    setup_instance(worker2_dns, trusted_host_dns, [gatekeeper_dns, trusted_host_dns], f)

time.sleep(300)

start_proxy(proxy_dns, [gatekeeper_dns, trusted_host_dns], master_dns, worker1_dns, worker2_dns, ProxyMode.DIRECT_HIT.value)
time.sleep(60)
asyncio.run(send_requests(gatekeeper_dns, 'direct hit proxy mode', instance_names, instance_ids))

start_proxy(proxy_dns, [gatekeeper_dns, trusted_host_dns], master_dns, worker1_dns, worker2_dns, ProxyMode.RANDOM.value)
time.sleep(60)
asyncio.run(send_requests(gatekeeper_dns, 'random proxy mode', instance_names, instance_ids))

start_proxy(proxy_dns, [gatekeeper_dns, trusted_host_dns], master_dns, worker1_dns, worker2_dns, ProxyMode.CUSTOMIZED.value)
time.sleep(60)
asyncio.run(send_requests(gatekeeper_dns, 'customized proxy mode', instance_names, instance_ids))
