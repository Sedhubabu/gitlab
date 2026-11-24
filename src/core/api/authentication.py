from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import AuthenticationFailed
from rest_framework_simplejwt.tokens import RefreshToken

TOKEN_VERSION_CLAIM = "token_version"


def issue_tokens_for_user(user):
    """
    Create a refresh + access token pair carrying the user's current token_version.
    Always use this (never RefreshToken.for_user directly) when logging a user in.
    """
    refresh = RefreshToken.for_user(user)
    refresh[TOKEN_VERSION_CLAIM] = user.token_version
    access = refresh.access_token  # copies the token_version claim
    return {"refresh": str(refresh), "access": str(access)}


def check_token_version(user, validated_token):
    if validated_token.get(TOKEN_VERSION_CLAIM) != user.token_version:
        raise AuthenticationFailed("Token has been revoked. Please sign in again.", code="token_revoked")


class TokenVersionJWTAuthentication(JWTAuthentication):
    """
    SimpleJWT authentication plus:
      - rejects tokens whose token_version no longer matches the user
        (bumped on logout, force sign-out, block/ban in the admin)
      - inactive users (state != active) are already rejected by SimpleJWT,
        because User.is_active follows User.state.
    """

    def get_user(self, validated_token):
        user = super().get_user(validated_token)
        check_token_version(user, validated_token)
        return user
