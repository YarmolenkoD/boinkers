import asyncio
import random
import string
from datetime import datetime, timedelta, timezone
from dateutil import parser
from time import time
from urllib.parse import unquote, quote
import brotli

import aiohttp
import json
from aiocfscrape import CloudflareScraper
from aiohttp_proxy import ProxyConnector
from better_proxy import Proxy
from pyrogram import Client
from pyrogram.errors import Unauthorized, UserDeactivated, AuthKeyUnregistered, FloodWait
from pyrogram.raw.functions.messages import RequestAppWebView
from pyrogram.raw import types
from .agents import generate_random_user_agent
from bot.config import settings

from bot.utils import logger
from bot.utils.logger import SelfTGClient
from bot.exceptions import InvalidSession
from .headers import headers
from .helper import format_duration

self_tg_client = SelfTGClient()

class Tapper:
    def __init__(self, tg_client: Client):
        self.session_name = tg_client.name
        self.tg_client = tg_client
        self.user_id = 0
        self.username = None
        self.first_name = None
        self.last_name = None
        self.fullname = None
        self.start_param = None
        self.peer = None
        self.first_run = None

        self.session_ug_dict = self.load_user_agents() or []

        headers['User-Agent'] = self.check_user_agent()

    async def generate_random_user_agent(self):
        return generate_random_user_agent(device_type='android', browser_type='chrome')

    def info(self, message):
        from bot.utils import info
        info(f"<light-yellow>{self.session_name}</light-yellow> | {message}")

    def debug(self, message):
        from bot.utils import debug
        debug(f"<light-yellow>{self.session_name}</light-yellow> | {message}")

    def warning(self, message):
        from bot.utils import warning
        warning(f"<light-yellow>{self.session_name}</light-yellow> | {message}")

    def error(self, message):
        from bot.utils import error
        error(f"<light-yellow>{self.session_name}</light-yellow> | {message}")

    def critical(self, message):
        from bot.utils import critical
        critical(f"<light-yellow>{self.session_name}</light-yellow> | {message}")

    def success(self, message):
        from bot.utils import success
        success(f"<light-yellow>{self.session_name}</light-yellow> | {message}")

    def save_user_agent(self):
        user_agents_file_name = "user_agents.json"

        if not any(session['session_name'] == self.session_name for session in self.session_ug_dict):
            user_agent_str = generate_random_user_agent()

            self.session_ug_dict.append({
                'session_name': self.session_name,
                'user_agent': user_agent_str})

            with open(user_agents_file_name, 'w') as user_agents:
                json.dump(self.session_ug_dict, user_agents, indent=4)

            logger.success(f"<light-yellow>{self.session_name}</light-yellow> | User agent saved successfully")

            return user_agent_str

    def load_user_agents(self):
        user_agents_file_name = "user_agents.json"

        try:
            with open(user_agents_file_name, 'r') as user_agents:
                session_data = json.load(user_agents)
                if isinstance(session_data, list):
                    return session_data

        except FileNotFoundError:
            logger.warning("User agents file not found, creating...")

        except json.JSONDecodeError:
            logger.warning("User agents file is empty or corrupted.")

        return []

    def check_user_agent(self):
        load = next(
            (session['user_agent'] for session in self.session_ug_dict if session['session_name'] == self.session_name),
            None)

        if load is None:
            return self.save_user_agent()

        return load

    async def get_tg_web_data(self, proxy: str | None) -> str:
        if proxy:
            proxy = Proxy.from_str(proxy)
            proxy_dict = dict(
                scheme=proxy.protocol,
                hostname=proxy.host,
                port=proxy.port,
                username=proxy.login,
                password=proxy.password
            )
        else:
            proxy_dict = None

        self.tg_client.proxy = proxy_dict

        try:
            with_tg = True

            if not self.tg_client.is_connected:
                with_tg = False
                try:
                    await self.tg_client.connect()
                except (Unauthorized, UserDeactivated, AuthKeyUnregistered):
                    raise InvalidSession(self.session_name)

            if settings.USE_REF == True:
                ref_id = settings.REF_ID
            else:
                ref_id = 'boink355876562'

            self.start_param = random.choices([ref_id, "boink355876562"], weights=[90, 10], k=1)[0]
            peer = await self.tg_client.resolve_peer('boinker_bot')
            InputBotApp = types.InputBotAppShortName(bot_id=peer, short_name="boinkapp")

            web_view = await self.tg_client.invoke(RequestAppWebView(
                peer=peer,
                app=InputBotApp,
                platform='android',
                write_allowed=True,
                start_param=self.start_param
            ))

            auth_url = web_view.url

            tg_web_data = unquote(
                string=auth_url.split('tgWebAppData=', maxsplit=1)[1].split('&tgWebAppVersion', maxsplit=1)[0])

            try:
                if self.user_id == 0:
                    information = await self.tg_client.get_me()
                    self.user_id = information.id
                    self.first_name = information.first_name or ''
                    self.last_name = information.last_name or ''
                    self.username = information.username or ''
            except Exception as e:
                self.error(f'Error during get tg web data: {e}')

            if with_tg is False:
                await self.tg_client.disconnect()

            return tg_web_data

        except InvalidSession as error:
            raise error

        except Exception as error:
            logger.error(
                f"<light-yellow>{self.session_name}</light-yellow> | Unknown error during Authorization: {error}")
            await asyncio.sleep(delay=3)

    async def login(self, http_client: aiohttp.ClientSession, initdata):
        try:
            json_data = { "initDataString": initdata }
            resp = await http_client.post(
                "https://boink.astronomica.io/public/users/loginByTelegram?p=android",
                json=json_data,
                ssl=False
            )
            if resp.status == 520:
                self.warning('Relogin')
                await asyncio.sleep(delay=5)

            resp_json = await resp.json()

            login_need = False

            return resp_json.get("token"), resp_json.get("token")

        except Exception as error:
            logger.error(f"<light-yellow>{self.session_name}</light-yellow> | Login error {error}")
            return None, None

    async def upgrade_boinker(self, http_client: aiohttp.ClientSession):
         try:
             resp = await http_client.post(f"https://boink.astronomica.io/api/boinkers/upgradeBoinker?p=android",
                                           ssl=False)
             data = await resp.json()

             if resp.status == 200 and data:
                 logger.success(f"<light-yellow>{self.session_name}</light-yellow> Upgrade Boinker | Coins: <light-yellow>{'{:,}'.format(data['newSoftCurrencyAmount'])}</light-yellow> | Spins: <light-blue>{data['newSlotMachineEnergy']}</light-blue> | Rank: <magenta>{data['rank']}</magenta>")
                 return True
             else:
                 logger.info(f"<light-yellow>{self.session_name}</light-yellow> Upgrade Boinker | Not enough coins | Status: <magenta>{resp.status}</magenta>")
                 return False

             return False
         except Exception as e:
             self.error(f"Error occurred during upgrade boinker: {e}")
             return False

    async def claim_booster(self, http_client: aiohttp.ClientSession, spin: int, multiplier: int = 0):
        json_data = {
            'multiplier': multiplier,
            'optionNumber': 1
        }

        if spin > 30 and multiplier == 0:
            json_data = {
                'multiplier': 2,
                'optionNumber': 3
            }

        try:
            resp = await http_client.post(
                f"https://boink.astronomica.io/api/boinkers/addShitBooster?p=android",
                json=json_data,
                ssl=False
            )

            data = await resp.json()

            if resp.status == 200:
                return True
            else:
                return False

            return True
        except Exception as e:
            self.error(f"Error occurred during claim booster: {e}")
            return False

    async def play_elevator(self, http_client: aiohttp.ClientSession):
        try:
            resp = await http_client.post(
                f"https://boink.astronomica.io/api/play/emptyElevatorPrizeStockpile?p=android",
                ssl=False,
                json={}
            )

            can_elevate = True
            is_win = True
            max_level = settings.ELEVATOR_MAX_LEVEL

            completed_level = 0

            while can_elevate and completed_level < max_level:
                resp = await http_client.post(
                    f"https://boink.astronomica.io/api/play/openElevator?p=android",
                    ssl=False,
                    json={}
                )

                data = None

                if resp.status == 200:
                    data = await resp.json()
                else:
                    return None

                if data and resp.status == 200 and 'isWin' in data and data['isWin'] == True and 'prize' in data and 'prizeName' in data['prize']:
                    completed_level = completed_level + 1
                    name = data['prize']['prizeName']
                    if 'prizeTypeName' in data['prize']:
                        name = data['prize']['prizeTypeName']
                    logger.success(f"<light-yellow>{self.session_name}</light-yellow> Elevator | <magenta>Level</magenta> - <light-green>{completed_level}</light-green> | Prize: <magenta>{name}</magenta> - <light-green>{data['prize']['prizeValue']}</light-green>")
                    can_elevate = True
                    is_win = True
                    continue
                elif data and 'isWin' in data and data['isWin'] == False:
                    can_elevate = False
                    is_win = False
                    completed_level = completed_level + 1
                else:
                    can_elevate = False
                    is_win = False
                    completed_level = completed_level + 1

                await asyncio.sleep(delay=2)

            if is_win == True:
                res = await http_client.post(
                    f"https://boink.astronomica.io/api/play/quitAndCollect?p=android",
                    ssl=False,
                    json={}
                )

                if res.status == 200:
                    self.success(f"You win in elevator | <magenta>Level</magenta> - <light-green>{completed_level}</light-green>")
                else:
                    self.warning(f"You lose in elevator | <magenta>Level</magenta> - <yellow>{completed_level}</yellow>")
            elif is_win == False:
                self.warning(f"You lose in elevator | <magenta>Level</magenta> - <yellow>{completed_level}</yellow>")
            else:
                self.warning(f"Something went wrong in elevator | <magenta>Level</magenta> - <yellow>{completed_level}</yellow>")

            return True
        except Exception as e:
            self.error(f"Error occurred during elevator: {e}")
            return False

    async def spin_wheel_fortune(self, http_client: aiohttp.ClientSession):
        try:
            resp = await http_client.post(
                f"https://boink.astronomica.io/api/play/spinWheelOfFortune?p=android",
                ssl=False
            )

            data = await resp.json()

            if resp.status == 200 and 'prize' in data and 'prizeName' in data['prize']:
                name = data['prize']['prizeName']
                if 'prizeTypeName' in data['prize']:
                    name = data['prize']['prizeTypeName']
                logger.success(f"<light-yellow>{self.session_name}</light-yellow> Wheel of Fortune | Prize: <magenta>{name}</magenta> - <light-green>{data['prize']['prizeValue']}</light-green>")
                return True
            else:
                return False

            return True
        except Exception as e:
            self.error(f"Error occurred during spin wheel of fortune: {e}")
            return False

    async def spin_slot_machine(self, http_client: aiohttp.ClientSession, spins: int):
        spin_amounts = [150, 50, 25, 10, 5, 1]
        remaining_spins = spins

        try:
            while remaining_spins > 0:
                spin_amount = next((amount for amount in spin_amounts if amount <= remaining_spins), 1)

                resp = await http_client.post(
                    f"https://boink.astronomica.io/api/play/spinSlotMachine/{spin_amount}?p=android",
                    ssl=False,
                    json={}
                )

                if resp.status == 200:
                    data = await resp.json()
                    logger.success(f"<light-yellow>{self.session_name}</light-yellow> | Spin prize: <light-blue>{data['prize']['prizeTypeName']}</light-blue> - <light-green>{data['prize']['prizeValue']}</light-green>")

                    await asyncio.sleep(delay=random.randint(1, 4))

                    curr_user = await self.get_user_info(http_client=http_client)
                    curr_spins = curr_user['gamesEnergy']['slotMachine']['energy']

                    remaining_spins = curr_spins
                else:
                    await asyncio.sleep(delay=2)
                    return False

            return True
        except Exception as e:
            self.error(f"Error occurred during spin slot machine: {e}")
            return False

    async def get_user_info(self, http_client: aiohttp.ClientSession):
        try:
            resp = await http_client.get(
                 f"https://boink.astronomica.io/api/users/me?p=android",
                 ssl=False
            )
            if resp.status == 200:
                json = await resp.json()
                return json
            else:
                return None
        except Exception as e:
            self.error(f"Error occurred during getting user info: {e}")
            return None

    async def claim_friend_reward(self, http_client: aiohttp.ClientSession):
        try:
            current_user_info = await self.get_user_info(http_client=http_client)

            if current_user_info and 'friendsInvited' in current_user_info:
                friends_invited = current_user_info['friendsInvited']
                invited_friends_data = {}

                if 'invitedFriendsData' in current_user_info:
                    invited_friends_data = current_user_info['invitedFriendsData']

                if not friends_invited:
                    return None

                for friend in friends_invited:
                    curr_friend_id = friend['_id']
                    curr_friend_username = friend['userName']
                    curr_friend_boinker_level = 0
                    already_claimed_reward_level = 0

                    if friend and 'boinkers' in friend and 'completedBoinkers' in friend['boinkers']:
                        curr_friend_boinker_level = friend['boinkers']['completedBoinkers']

                    if curr_friend_boinker_level == 0:
                        continue

                    if invited_friends_data and curr_friend_id in invited_friends_data:
                        already_claimed_reward_level = invited_friends_data[curr_friend_id]['moonBoinkersRewardClaimed'] or 0

                        if already_claimed_reward_level == 1 and curr_friend_boinker_level >= 2 and curr_friend_boinker_level < 3:
                            continue

                        if already_claimed_reward_level == 3 and curr_friend_boinker_level >= 3 and curr_friend_boinker_level < 5:
                            continue

                        if already_claimed_reward_level == 5:
                            continue

                    claim_available = True
                    while claim_available == True:
                        await asyncio.sleep(delay=2)

                        resp = await http_client.post(
                            f"https://boink.astronomica.io/api/friends/claimFriendMoonBoinkerReward/{curr_friend_id}?p=android",
                            ssl=False
                        )

                        json = await resp.json()

                        if resp.status == 200:
                            already_claimed_reward_level = json['invitedFriendsData']['moonBoinkersRewardClaimed']

                            self.success(f"Claimed friend reward: {curr_friend_username} | <light-green>{already_claimed_reward_level}</light-green> <magenta>boinkers</magenta> sent to the moon 🚀")

                            if already_claimed_reward_level == 1 and curr_friend_boinker_level > 1 and curr_friend_boinker_level < 3:
                                claim_available = False
                            if already_claimed_reward_level == 3 and curr_friend_boinker_level >= 3 and curr_friend_boinker_level < 5:
                                claim_available = False
                            if already_claimed_reward_level == 5:
                                claim_available = False

                            claim_available = True
                        else:
                            claim_available = False
            return True
        except Exception as e:
            self.error(f"Error occurred during claim friend request: {e}")
            return False

    async def perform_rewarded_actions(self, http_client: aiohttp.ClientSession):
        get_rewarded_action_list_url = "https://boink.astronomica.io/api/rewardedActions/getRewardedActionList?p=android"

        skipped_tasks = settings.BLACK_LIST_TASKS

        try:
            # Fetch user info
            user_info = await self.get_user_info(http_client=http_client)

            async with http_client.get(get_rewarded_action_list_url, ssl=False) as response:
                if response.status != 200:
                    return
                rewarded_actions = await response.json()

            if rewarded_actions is None:
                return False

            for action in rewarded_actions:
                name_id = action['nameId']

                is_exist_in_black_list = any(item.lower() in name_id.lower() for item in skipped_tasks)
                if is_exist_in_black_list:
#                     logger.info(f"<light-yellow>{self.session_name}</light-yellow> | Skipping task: {name_id} | Because it's on the blacklist")
                    continue

                # Skip all tasks that have conditions to join a telegram channel or group
                if 'verification' in action and 'paramKey' in action['verification'] and action['verification']['paramKey'] == 'joinedChat':
#                     logger.info(f"<light-yellow>{self.session_name}</light-yellow> | Skipping task: {name_id} | Because you need to join the group or channel.")
                    continue

                current_time = datetime.now(timezone.utc)
                can_perform_task = True
                wait_time = None

                if user_info and user_info.get('rewardedActions', {}).get(name_id):
                    last_claim_time = None
                    last_click_time = None
                    next_available_time = None
                    seconds_to_claim_again = None

                    curr_reward = user_info['rewardedActions'][name_id]

                    if 'secondsToClaimAgain' in action and action['secondsToClaimAgain'] != 0:
                        seconds_to_claim_again = action['secondsToClaimAgain']

                    if 'claimDateTime' in curr_reward:
                        last_claim_time = parser.isoparse(curr_reward['claimDateTime'])

                    if 'clickDateTime' in curr_reward and curr_reward['clickDateTime'] != None:
                        last_click_time = parser.isoparse(curr_reward['clickDateTime'])

                    if seconds_to_claim_again != None:
                        next_available_time = current_time
                        if last_claim_time != None:
                            next_available_time = last_claim_time + timedelta(seconds=seconds_to_claim_again)
                            if current_time < next_available_time:
                                can_perform_task = False
                                wait_time = next_available_time
                            else:
                                can_perform_task = True
                    elif last_claim_time != None:
                        can_perform_task = False
                    else:
                        can_perform_task = True

                if not can_perform_task:
                    if wait_time:
                        wait_seconds = (wait_time - current_time).seconds
                        logger.info(f"<light-yellow>{self.session_name}</light-yellow> | Need to wait {wait_seconds} seconds to perform task {name_id}")
                    continue

                if settings.AD_TASK_PREFIX.lower() in name_id.lower():
                    provider_id = 'adsgram'

                    if 'verification' in action and 'paramKey' in action['verification']:
                        provider_id = action['verification']['paramKey']

                    await self.handle_ad_task(http_client=http_client, name_id=name_id, provider_id=provider_id, action=action)  # Assuming you have a function to handle this
                else:
                    click_url = f"https://boink.astronomica.io/api/rewardedActions/rewardedActionClicked/{name_id}?p=android"
                    try:
                        async with http_client.post(click_url, ssl=False) as click_response:
                            click_result = await click_response.json()
                            logger.info(f"<light-yellow>{self.session_name}</light-yellow> | Performed task {name_id}. Status: pending")

                    except Exception as click_error:
                        logger.error(f"<light-yellow>{self.session_name}</light-yellow> | 😢 Error performing task {name_id}: {click_error}")
                        continue

                    seconds_to_allow_claim = 10

                    if 'secondsToAllowClaim' in action:
                        seconds_to_allow_claim = action['secondsToAllowClaim']

                    if seconds_to_allow_claim > 60:
                        logger.info(f"<light-yellow>{self.session_name}</light-yellow> | Need to wait {seconds_to_allow_claim} seconds to perform task {name_id}")
                        continue

                    logger.info(f"<light-yellow>{self.session_name}</light-yellow> | 💤 Waiting {seconds_to_allow_claim} seconds before claiming reward... 💤")
                    await asyncio.sleep(delay=seconds_to_allow_claim)

                    try:
                        claim_url = f"https://boink.astronomica.io/api/rewardedActions/claimRewardedAction/{name_id}?p=android"
                        async with http_client.post(claim_url, ssl=False) as claim_response:
                            if claim_response.status == 200:
                                result = await claim_response.json()
                                if result != None and 'prizeGotten' in result:
                                    reward = result['prizeGotten']
                                    logger.success(f"<light-yellow>{self.session_name}</light-yellow> | Successfully completed task {name_id} | Reward: 💰<light-green>{reward}</light-green> 💰")
                            else:
                                logger.info(f"<light-yellow>{self.session_name}</light-yellow> | Failed to claim reward for {name_id}. Status code: <light-red>{claim_response.status}</light-red>")
                    except Exception as claim_error:
                        logger.info(f"<light-yellow>{self.session_name}</light-yellow> | 😢 Error claiming reward for {name_id}: {claim_error}")
                        break

                await asyncio.sleep(delay=1)

        except Exception as error:
            logger.info(f"<light-yellow>{self.session_name}</light-yellow> | 😢 Error performing tasks: {error}")

    async def get_raffle_data(self, http_client: aiohttp.ClientSession, name_id, provider_id, action):
        try:
            raffle_url = f"https://boink.astronomica.io/api/raffle/getRafflesData?p=android"

            result = await http_client.get(raffle_url, ssl=False)

            data = await result.json()

            if result.status == 200 and data:
                current_raffle = data.get('currentRaffle', None)
                user_daily_poop = data.get('userDailyPoop', 0)
                user_raffle_data = data.get('userRaffleData', None)

                return user_raffle_data, user_daily_poop, current_raffle
            else:
                self.warning(f"Something went wrong during get raffle data: {data}")
                return None, None, None

        except Exception as error:
            self.error(f" 😢 Error during get raffle data: {error}")
            return None, None, None

    async def handle_ad_task(self, http_client: aiohttp.ClientSession, name_id, provider_id, action):
        try:
            # Click the ad task
            click_url = f"https://boink.astronomica.io/api/rewardedActions/rewardedActionClicked/{name_id}?p=android"
            await http_client.post(click_url, ssl=False)

            logger.info(f"<light-yellow>{self.session_name}</light-yellow> | Ad task {name_id} clicked successfully")

            logger.info(f"<light-yellow>{self.session_name}</light-yellow> | 💤 Sleep 5 seconds before close ad... 💤")
            await asyncio.sleep(delay=5)

            # Confirm ad watched
            ad_watched_url = "https://boink.astronomica.io/api/rewardedActions/ad-watched?p=android"
            await http_client.post(ad_watched_url, json={"providerId": provider_id}, ssl=False)
            logger.info(f"<light-yellow>{self.session_name}</light-yellow> | Ad task {name_id} watched successfully")

            seconds_to_allow_claim = 25

            if 'secondsToAllowClaim' in action:
                seconds_to_allow_claim = action['secondsToAllowClaim'] + 5

            logger.info(f"<light-yellow>{self.session_name}</light-yellow> | 💤 Sleep {seconds_to_allow_claim} seconds before claiming ad reward... 💤")
            await asyncio.sleep(delay=seconds_to_allow_claim)

            # Claim the reward
            claim_url = f"https://boink.astronomica.io/api/rewardedActions/claimRewardedAction/{name_id}?p=android"
            logger.info(f"<light-yellow>{self.session_name}</light-yellow> | Sending reward claim request for ad task {name_id}...")
            async with http_client.post(claim_url, headers=headers) as claim_response:
                if claim_response.status == 200:
                    result = await claim_response.json()
                    if result:
                        reward = result.get('prizeGotten')
                        logger.success(f"<light-yellow>{self.session_name}</light-yellow> | Successfully completed ad task {name_id} | Reward: 💰<light-green>{reward}</light-green> 💰")
                else:
                    logger.error(f"<light-yellow>{self.session_name}</light-yellow> | 😢 Failed to claim reward for ad task {name_id}. Status code: {claim_response.status}")

        except Exception as error:
            logger.error(f"<light-yellow>{self.session_name}</light-yellow> | 😢 Error handling ad task {name_id}: {error}")

    async def check_proxy(self, http_client: aiohttp.ClientSession, proxy: Proxy) -> None:
        try:
            response = await http_client.get(url='https://httpbin.org/ip', timeout=aiohttp.ClientTimeout(5))
            ip = (await response.json()).get('origin')
            logger.info(f"<light-yellow>{self.session_name}</light-yellow> | Proxy IP: {ip}")
        except Exception as error:
            logger.error(f"<light-yellow>{self.session_name}</light-yellow> | Proxy: {proxy} | 😢 Error: {error}")

    async def run(self, proxy: str | None) -> None:
        if settings.USE_RANDOM_DELAY_IN_RUN:
            random_delay = random.randint(settings.RANDOM_DELAY_IN_RUN[0], settings.RANDOM_DELAY_IN_RUN[1])
            logger.info(f"<light-yellow>{self.session_name}</light-yellow> | Bot will start in <ly>{random_delay}s</ly>")
            await asyncio.sleep(delay=random_delay)

        access_token = None
        refresh_token = None
        login_need = True

        proxy_conn = ProxyConnector().from_url(proxy) if proxy else None

        http_client = CloudflareScraper(headers=headers, connector=proxy_conn)

        if proxy:
            await self.check_proxy(http_client=http_client, proxy=proxy)

        while True:
            try:
                if login_need:
                    if "Authorization" in http_client.headers:
                        del http_client.headers["Authorization"]

                    init_data = await self.get_tg_web_data(proxy=proxy)

                    access_token, refresh_token = await self.login(http_client=http_client, initdata=init_data)

                    http_client.headers["Authorization"] = f"{access_token}"

                    if self.first_run is not True:
                        self.success("Logged in successfully")
                        self.first_run = True

                    login_need = False

                await asyncio.sleep(delay=3)

            except Exception as error:
                logger.error(
                    f"<light-yellow>{self.session_name}</light-yellow> | 😢 Unknown error during login: {error}")
                await asyncio.sleep(delay=3)

            try:
                user_info = await self.get_user_info(http_client=http_client)
                await asyncio.sleep(delay=2)
                if user_info is not None:
                    if user_info['boinkers'] and 'completedBoinkers' in user_info['boinkers']:
                        logger.info(f"<light-yellow>{self.session_name}</light-yellow> | Boinkers: <light-blue>{user_info['boinkers']['completedBoinkers']}</light-blue> 👨‍🚀")

                    if 'currencySoft' in user_info:
                        logger.info(f"<light-yellow>{self.session_name}</light-yellow> | Coin Balance: 💰 <light-green>{'{:,}'.format(user_info['currencySoft'])}</light-green> 💰")

                    if 'currencyCrypto' in user_info:
                        logger.info(f"<light-yellow>{self.session_name}</light-yellow> | Shit Balance: 💩 <cyan>{'{:,.3f}'.format(user_info['currencyCrypto'])}</cyan> 💩")

                    current_time = datetime.now(timezone.utc)

                    last_claimed_time_str = user_info.get('boinkers', {}).get('booster', {}).get('x2', {}).get('lastTimeFreeOptionClaimed')
                    last_claimed_time = parser.isoparse(last_claimed_time_str) if last_claimed_time_str else None

                    last_claimed_time_str_x29 = user_info.get('boinkers', {}).get('booster', {}).get('x29', {}).get('lastTimeFreeOptionClaimed')
                    last_claimed_time_x29 = parser.isoparse(last_claimed_time_str_x29) if last_claimed_time_str_x29 else None

                    # Check for booster x29 claim
                    if not last_claimed_time_x29 or current_time > last_claimed_time_x29 + timedelta(hours=2, minutes=5):
                        success = await self.claim_booster(http_client=http_client, spin=user_info['gamesEnergy']['slotMachine']['energy'], multiplier=29)
                        if success:
                            logger.success(f"<light-yellow>{self.session_name}</light-yellow> | 🚀 Claimed boost successfully 🚀")
                            await asyncio.sleep(delay=4)

                    # Check for booster claim
                    if not last_claimed_time or current_time > last_claimed_time + timedelta(hours=2, minutes=5):
                        success = await self.claim_booster(http_client=http_client, spin=user_info['gamesEnergy']['slotMachine']['energy'])
                        if success:
                            logger.success(f"<light-yellow>{self.session_name}</light-yellow> | 🚀 Claimed boost successfully 🚀")
                            await asyncio.sleep(delay=4)

                    if settings.ENABLE_AUTO_WHEEL_FORTUNE:
                        fortune_user = await self.get_user_info(http_client=http_client)
                        await asyncio.sleep(delay=random.randint(1, 3))
                        if fortune_user and 'gamesEnergy' in fortune_user and 'wheelOfFortune' in fortune_user['gamesEnergy']:
                            fortune_energy = fortune_user['gamesEnergy']['wheelOfFortune']['energy']
                            last_claimed_wheel_str = user_info.get('boinkers', {}).get('booster', {}).get('x2', {}).get('lastTimeFreeOptionClaimed')
                            last_claimed_wheel_time = parser.isoparse(last_claimed_wheel_str) if last_claimed_wheel_str else None
                            if fortune_energy > 0:
                                await self.spin_wheel_fortune(http_client=http_client)
                                await asyncio.sleep(delay=random.randint(2, 4))
                            elif not last_claimed_wheel_time or current_time > last_claimed_wheel_time + timedelta(hours=24):
                                await self.spin_wheel_fortune(http_client=http_client)
                                await asyncio.sleep(delay=random.randint(2, 4))

                    if settings.ENABLE_AUTO_TASKS:
                        await self.perform_rewarded_actions(http_client=http_client)
                        await asyncio.sleep(delay=4)

                    await self.claim_friend_reward(http_client=http_client)
                    await asyncio.sleep(delay=4)

                    if settings.ENABLE_AUTO_ELEVATOR:
                        elevator_user = await self.get_user_info(http_client=http_client)
                        await asyncio.sleep(delay=random.randint(1, 3))
                        if elevator_user and 'gamesEnergy' in elevator_user and 'elevators' in elevator_user['gamesEnergy']:
                            elevator_last_used = elevator_user['gamesEnergy']['elevators']['lastUpdated']

                            parsed_date = datetime.strptime(elevator_last_used, "%Y-%m-%dT%H:%M:%S.%fZ")
                            now = datetime.utcnow()
                            one_day_ago = now - timedelta(days=1)

                            if parsed_date < one_day_ago:
                                await self.play_elevator(http_client=http_client)
                                await asyncio.sleep(delay=random.randint(2, 4))

                    if settings.ENABLE_AUTO_SPIN:
                        spin_user = await self.get_user_info(http_client=http_client)
                        await asyncio.sleep(delay=random.randint(1, 3))
                        if spin_user and 'gamesEnergy' in spin_user and 'slotMachine' in spin_user['gamesEnergy']:
                            spins = spin_user['gamesEnergy']['slotMachine']['energy']
                            last_claimed_spins_str = user_info.get('boinkers', {}).get('booster', {}).get('x2', {}).get('lastTimeFreeOptionClaimed')
                            last_claimed_spins_time = parser.isoparse(last_claimed_spins_str) if last_claimed_spins_str else None
                            if spins > 0:
                                self.info(f"Spins: <light-blue>{spins}</light-blue>")
                                await self.spin_slot_machine(http_client=http_client, spins=spins)
                                await asyncio.sleep(delay=random.randint(2, 4))
                            elif not last_claimed_spins_time or current_time > last_claimed_spins_time + timedelta(hours=14):
                                self.info(f"Daily Spins: <light-blue>50</light-blue>")
                                await self.spin_slot_machine(http_client=http_client, spins=50)
                                await asyncio.sleep(delay=random.randint(2, 4))

                    if settings.ENABLE_AUTO_UPGRADE:
                        upgrade_success = True
                        tries = 3
                        while upgrade_success and tries > 0:
                            result = await self.upgrade_boinker(http_client=http_client)
                            if not result:
                                if tries == 0:
                                    upgrade_success = False
                                else:
                                    user_info = await self.get_user_info(http_client=http_client)
                                    if user_info and 'currencySoft' in user_info and user_info['currencySoft'] > 20000000:
                                        tries -= 1
                                    else:
                                        upgrade_success = False
                            await asyncio.sleep(delay=random.randint(2, 4))

                logger.info(f"<light-yellow>{self.session_name}</light-yellow> | 💤 sleep 30 minutes 💤")
                await asyncio.sleep(delay=1800)

            except Exception as error:
                logger.error(
                    f"<light-yellow>{self.session_name}</light-yellow> | 😢 Unknown error: {error}")

async def run_tapper(tg_client: Client, proxy: str | None):
    try:
        await Tapper(tg_client=tg_client).run(proxy=proxy)
    except InvalidSession:
        logger.error(f"{tg_client.name} | 😢 Invalid Session 😢")
