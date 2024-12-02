from enums import ProxyMode
from ssh_interface import SSH
from constants import PROXY_PORT, SAKILA_ARCHIVE

ssh = SSH()

def setup_gatekeeper(host: str, trusted_host_dns: str):
    # setup the node app
    ssh.ssh("sudo apt-get update -y", host)
    ssh.ssh('sudo apt-get install nodejs npm -y', host)

    ssh.scp('./js/package.json', 'package.json', host)
    ssh.scp('./js/package-lock.json', 'package-lock.json', host)
    ssh.scp('./js/gatekeeper.js', 'gatekeeper.js', host)

    ssh.ssh('npm install', host)

    # setup the proxy
    ssh.ssh('sudo apt-get install tinyproxy -y', host)
    ssh.ssh(f'echo "Allow {trusted_host_dns}" | sudo tee -a /etc/tinyproxy/tinyproxy.conf > /dev/null', host)

    # start the node app and the proxy
    ssh.ssh(f'sudo node gatekeeper.js {trusted_host_dns}', host, background=True)
    ssh.ssh('sudo systemctl restart tinyproxy', host)

def setup_trusted_host(host: str, gatekeeper_dns:str, proxy_dns: str, master_dns:str, worker1_dns:str, worker2_dns: str, jumps: list[str]):
    http_proxy_url = f'http://{gatekeeper_dns}:{PROXY_PORT}'
    http_proxy = f'http_proxy={http_proxy_url}'

    # setup the node app
    ssh.ssh(f"sudo {http_proxy} apt-get update -y", host, jumps)
    ssh.ssh(f'sudo {http_proxy} apt-get install nodejs npm -y', host, jumps)

    ssh.scp('./js/package.json', 'package.json', host, jumps)
    ssh.scp('./js/package-lock.json', 'package-lock.json', host, jumps)
    ssh.scp('./js/trusted_host.js', 'trusted_host.js', host, jumps)

    ssh.ssh(f'sudo npm config set proxy "{http_proxy_url}"', host, jumps)
    ssh.ssh(f'sudo {http_proxy} npm install', host, jumps)

    # setup the proxy
    ssh.ssh(f'sudo {http_proxy} apt-get install tinyproxy -y', host, jumps)
    ssh.ssh(f'echo "Allow {proxy_dns}" | sudo tee -a /etc/tinyproxy/tinyproxy.conf > /dev/null', host, jumps)
    ssh.ssh(f'echo "Allow {master_dns}" | sudo tee -a /etc/tinyproxy/tinyproxy.conf > /dev/null', host, jumps)
    ssh.ssh(f'echo "Allow {worker1_dns}" | sudo tee -a /etc/tinyproxy/tinyproxy.conf > /dev/null', host, jumps)
    ssh.ssh(f'echo "Allow {worker2_dns}" | sudo tee -a /etc/tinyproxy/tinyproxy.conf > /dev/null', host, jumps)
    ssh.ssh(f'echo "Upstream http {gatekeeper_dns}:{PROXY_PORT}" | sudo tee -a /etc/tinyproxy/tinyproxy.conf > /dev/null', host, jumps)

    ssh.ssh(f'sudo node trusted_host.js {proxy_dns}', host, jumps, background=True)
    ssh.ssh('sudo systemctl restart tinyproxy', host, jumps)

def setup_proxy(host: str, trusted_host_dns: str, jumps: list[str]):
    http_proxy_url = f'http://{trusted_host_dns}:{PROXY_PORT}'
    http_proxy = f'http_proxy={http_proxy_url}'

    # setup the node app
    ssh.ssh(f"sudo {http_proxy} apt-get update -y", host, jumps)
    ssh.ssh(f'sudo {http_proxy} apt-get install nodejs npm -y', host, jumps)

    ssh.scp('./js/package.json', 'package.json', host, jumps)
    ssh.scp('./js/package-lock.json', 'package-lock.json', host, jumps)
    ssh.scp('./js/proxy.js', 'proxy.js', host, jumps)

    ssh.ssh(f'sudo npm config set proxy "{http_proxy_url}"', host, jumps)
    ssh.ssh(f'sudo {http_proxy} npm install', host, jumps)


def setup_instance(host: str, trusted_host_dns: str, jumps: list[str], file):
    http_proxy_url = f'http://{trusted_host_dns}:{PROXY_PORT}'
    http_proxy = f'http_proxy={http_proxy_url}'

    # setup the node app
    ssh.ssh(f"sudo {http_proxy} apt-get update -y", host, jumps)
    ssh.ssh(f'sudo {http_proxy} apt-get install nodejs npm -y', host, jumps)

    ssh.scp('./js/package.json', 'package.json', host, jumps)
    ssh.scp('./js/package-lock.json', 'package-lock.json', host, jumps)
    ssh.scp('./js/instance.js', 'instance.js', host, jumps)

    ssh.ssh(f'sudo npm config set proxy "{http_proxy_url}"', host, jumps)
    ssh.ssh(f'sudo {http_proxy} npm install', host, jumps)

    # setup mysql
    ssh.ssh(f"sudo {http_proxy} apt-get install mysql-server -y", host, jumps)

    ssh.scp(f'./{SAKILA_ARCHIVE}', SAKILA_ARCHIVE, host, jumps)
    ssh.ssh(f"tar -xvzf {SAKILA_ARCHIVE}", host, jumps)

    ssh.ssh('sudo mysql -u root -e "SOURCE ./sakila-db/sakila-schema.sql; SOURCE ./sakila-db/sakila-data.sql;"', host, jumps)

    # setup sysbench
    ssh.ssh(f'sudo {http_proxy} apt-get install sysbench -y', host, jumps)
    ssh.ssh('sudo sysbench /usr/share/sysbench/oltp_read_only.lua --mysql-db=sakila --mysql-user="root" prepare', host, jumps)
    ssh.ssh('sudo sysbench /usr/share/sysbench/oltp_read_only.lua --mysql-db=sakila --mysql-user="root" run', host, jumps, file=file)

    ssh.ssh("sudo mysql -u root -e \"ALTER USER 'root'@'localhost' IDENTIFIED WITH mysql_native_password BY 'password'; FLUSH PRIVILEGES;\"", host, jumps)

    ssh.ssh('sudo node instance.js', host, jumps, background=True)


def start_proxy(host: str, jumps: list[str], master_dns: str, worker1_dns: str, worker2_dns: str, mode: ProxyMode):
    ssh.ssh('sudo pkill -f node', host, jumps)
    ssh.ssh(f'sudo node proxy.js {master_dns} {worker1_dns} {worker2_dns} {mode}', host, jumps, background=True)
    