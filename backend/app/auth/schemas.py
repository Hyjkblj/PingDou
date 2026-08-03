from app.core.schemas import AppSchema


class SendSmsRequest(AppSchema):
    phone: str
    scene: str = "LOGIN"


class SendSmsResponse(AppSchema):
    cooldown_seconds: int = 60


class SmsLoginRequest(AppSchema):
    phone: str
    code: str


class SmsLoginResponse(AppSchema):
    access_token: str
    expires_in: int
    refresh_token: str
    user: "UserView"


class RefreshTokenRequest(AppSchema):
    refresh_token: str


class RefreshTokenResponse(AppSchema):
    access_token: str
    expires_in: int
    refresh_token: str


class UserView(AppSchema):
    id: str
    phone_masked: str
