from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_ignore_empty=True)

    API_ID: int
    API_HASH: str

    USE_REF: bool = True
    REF_ID: str = 'boink355876562'

    USE_RANDOM_DELAY_IN_RUN: bool = True
    RANDOM_DELAY_IN_RUN: list[int] = [5, 60]

    AD_TASK_PREFIX: str = 'AdTask'

    BLACK_LIST_TASKS: list[str] = [
         'telegramShareStory',
         'emojiOnPostTelegramNewsChannel',
         'NotGoldReward',
         'NotPlatinumReward',
         'connectTonWallet',
         'telegramJoinBoinkersNewsChannel',
         'telegramBoost',
         'telegramJoinAcidGames',
         'AnimalsAndCoins',
         'AnimalsAndCoinsIsland',
         'AnimalsAndCoinsInstall',
         'playCornBattle',
         'NBPSep',
         'inviteAFriend',
         'MergePalsQuests',
         'playAAO',
         'playPiggyPiggy'
    ]

    USE_PROXY_FROM_FILE: bool = True

    ENABLE_AUTO_TASKS: bool = True
    ENABLE_AUTO_WHEEL_FORTUNE: bool = True
    ENABLE_AUTO_ELEVATOR: bool = True
    ELEVATOR_MAX_LEVEL: int = 4
    ENABLE_AUTO_SPIN: bool = True
    ENABLE_AUTO_UPGRADE: bool = True


settings = Settings()


