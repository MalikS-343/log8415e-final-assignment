import subprocess
import logging

from constants import USER

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SSH:
    def __init__(self) -> None:
        # subprocess.run(['eval "$(ssh-agent -s)"'])
        # subprocess.run(['ssh-add', KEY_FILENAME])
        pass

    def ssh(self, cmd:str, host:str, jumps: list[str] = [], background=False, file=None):
        logger.info(cmd)
        
        ssh_command = ["ssh", "-o", "StrictHostKeyChecking=no", '-A']

        if len(jumps) > 0:
            ssh_command.append('-J')
            ssh_command.append(','.join(f'{USER}@{jump}' for jump in jumps))
        ssh_command.append(f'{USER}@{host}')
        ssh_command.append(cmd)

        if file:
            return subprocess.run(
                ssh_command,
                stdout=file,
                stderr=subprocess.STDOUT
            )
        elif not background:
            return subprocess.run(
                ssh_command,
                capture_output=False,
                check=True,
            )
        else:
            return subprocess.Popen(
                ssh_command,
            )
        
    def scp(self, source_file, target_file, host, jumps = []):
        logger.info(source_file)

        scp_command = ['scp', '-o', 'StrictHostKeyChecking=no', '-A']

        if len(jumps) > 0:
            scp_command.append('-J')
            scp_command.append(','.join(f'{USER}@{jump}' for jump in jumps))
        scp_command.append(source_file)
        scp_command.append(f'{USER}@{host}:/home/ubuntu/{target_file}')

        return subprocess.run(
            scp_command,
            capture_output=False,
            check=True
        )
