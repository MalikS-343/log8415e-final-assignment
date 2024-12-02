import asyncio
import logging
import datetime
import time
import aiohttp
from aws import get_cloudwatch_infos
from constants import HTTP_PORT, NUM_REQUESTS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def get(session: aiohttp.ClientSession, request_num, url):
    headers = {'content-type': 'application/json'}
    try:
        async with session.get(url, headers=headers) as response:
            status_code = response.status
            response_json = await response.json()
            return status_code, response_json
    except Exception as e:
        logger.error(f"Request {request_num}: Failed - {str(e)}")
        return None, str(e)
    

async def post(session: aiohttp.ClientSession, request_num, url):
    headers = {'content-type': 'application/json'}
    try:
        async with session.post(url, headers=headers) as response:
            status_code = response.status
            response_json = await response.json()
            return status_code, response_json
    except Exception as e:
        logger.error(f"Request {request_num}: Failed - {str(e)}")
        return None, str(e)


async def send_requests(gatekeeper_dns: str, experiment_name: str, names: list[str], ids: list[str]):
    url = f'http://{gatekeeper_dns}:{HTTP_PORT}' 
    start_time = datetime.datetime.now(datetime.timezone.utc)
    logger.info(f"Starting {experiment_name} benchmarking at {start_time}")

    async with aiohttp.ClientSession() as session:
        tasks = [get(session, i, url) for i in range(NUM_REQUESTS)]
        await asyncio.gather(*tasks)
    async with aiohttp.ClientSession() as session:
        tasks = [post(session, i, url) for i in range(NUM_REQUESTS)]
        await asyncio.gather(*tasks)

    end_time = datetime.datetime.now(datetime.timezone.utc)
    logger.info(f"Ending {experiment_name} benchmarking at {end_time}")

    logger.info('Waiting 5 minutes before the data becomes available in CloudWatch')
    time.sleep(300)
    get_cloudwatch_infos(end_time, experiment_name, names, ids)
