from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_ignore_empty=True)

    API_ID: int
    API_HASH: str

    USE_REF: bool = True
    REF_ID: str = 'boink355876562'

    USE_RANDOM_DELAY_IN_RUN: bool = True
    RANDOM_DELAY_IN_RUN: list[int] = [5, 30]

    BLACK_LIST_TASKS: list[str] = [
         'twitterQuotePost20',
         'telegramShareStory5',
         'emojiOnPostTelegramNewsChannel',
         'NotGoldReward',
         'NotPlatinumReward',
         'connectTonWallet',
         'telegramJoinBoinkersNewsChannel',
         'telegramJoinAcidGames',
         'inviteAFriend'
    ]

    USE_PROXY_FROM_FILE: bool = True


settings = Settings()


