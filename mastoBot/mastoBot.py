from typing import List, Dict, Callable
import logging
import time
from abc import ABC, abstractmethod
from mastodon import (
    Mastodon,
    MastodonIllegalArgumentError,
    MastodonFileNotFoundError,
    MastodonNetworkError,
    MastodonAPIError,
    MastodonMalformedEventError,
    MastodonRatelimitError,
    MastodonServerError,
    MastodonVersionError,
)

from .configManager import *


def handleMastodonExceptions(func) -> Callable:
    def wrapper(self, *args, **kwargs):
        try:
            result = func(self, *args, **kwargs)
            return result
        except MastodonServerError as e:
            logging.critical(f"MastodonServerError: {e}")
        except MastodonIllegalArgumentError as e:
            logging.critical(f"MastodonIllegalArgumentError: {e}")
        except MastodonFileNotFoundError as e:
            logging.critical(f"MastodonFileNotFoundError: {e}")
        except MastodonNetworkError as e:
            logging.critical(f"MastodonNetworkError: {e}")
        except MastodonAPIError as e:
            logging.critical(f"MastodonAPIError: {e}")
        except MastodonMalformedEventError as e:
            logging.critical(f"MastodonMalformedEventError: {e}")
        except MastodonRatelimitError as e:
            logging.critical(f"MastodonRatelimitError: {e}")
        except MastodonVersionError as e:
            logging.critical(f"MastodonVersionError: {e}")
        except Exception as e:
            logging.critical(f"Error in function {func.__name__}")
            logging.critical(e)
            raise e
    return wrapper

class MastoBot(ABC):
    """
    A class to create Mastodon bots.

    This is class is used to implement Mastodon bots. The class works by combining the Mastodon API with a database in order to
    allow for local caching and storing of custom fields along side data received from the API.

    Attributes
    ----------
    config: ConfigAccessor
        The config of the user
    credentials: ConfigAccessor
        The credentials used for API and database access of the user
    """
    DEFAULT_REFRESH_RATE = 10 # Sleep time in seconds

    def __init__(self, config: ConfigAccessor, credentials: ConfigAccessor) -> None:
        """

        Parameters
        ----------
        config: ConfigAccessor
            The running config for the bot
        credentials: ConfigAccessor
            The credentials required for database and API access for the bot

        Returns
        -------
        None
        """
        
        self.refresh_rate = self.DEFAULT_REFRESH_RATE
        
        try:
            self.config = config
            self.credentials = credentials
            logging.info("✅ \t Config and credentials initialized")
        except Exception as e:
            logging.info("❌ \t Config and credentials failed to initialized")
            raise e

        try:
            self._api = Mastodon(
                access_token=self.credentials.get("access_token"),
                api_base_url=self.credentials.get("api_base_url"),
                request_timeout=self.config.get("api", {}).get("timeout", 10),
            )
            logging.info("✅ \t Mastodon.py initialized")
        except Exception as e:
            logging.critical("❌ \t Mastodon.py failed to initialized")
            raise e

    @property
    def refresh_rate(self):
        return self._refresh_rate
    
    @refresh_rate.setter
    def refresh_rate(self, value):
        if value <= 0: 
            logging.warning("❌ \t Refresh rate should be greater than 0")
            raise ValueError("Refresh rate should be greater than 0")
        
        try:
            logging.info(f"⌛ \t Refresh rate set to: {value}")
            self._refresh_rate = int(value)
        except:
            logging.warning("❌ \t Invalid refresh rate specified")
    
    def run(self):
        logging.info("⛏️ \t Starting main loop")
        while True:
            notifications = self._fetch_notifications()
            self._process_notifications(notifications)
            time.sleep(self.refresh_rate)

    @handleMastodonExceptions
    def _fetch_notifications(self):
        notifications = self._api.notifications()
        logging.debug(f"📬 \t {len(notifications)} Notifications fetched")
        return notifications

    @handleMastodonExceptions
    def _process_notifications(self, notifications: List[Dict[Any, Any]]) -> None:
        for notification in notifications:
            if notification.get("type") == "mention":
                self.processMention(notification)
            elif notification.get("type") == "reblog":
                self.processReblog(notification)
            elif notification.get("type") == "favourite":
                self.processFavourite(notification)
            elif notification.get("type") == "follow":
                self.processFollow(notification)
            elif notification.get("type") == "poll":
                self.processPoll(notification)
            elif notification.get("type") == "follow_request":
                self.processFollowRequest(notification)
            elif notification.get("type") == "update":
                self.processUpdate(notification)
            else:
                logging.warning(f"❗ \t Invalid notification type: {notification.get('type')}")

    @handleMastodonExceptions
    def getAccount(self, account_id: int) -> Dict:
        return self._api.account(account_id)

    @handleMastodonExceptions
    def getMe(self) -> Dict:
        return self._api.me()

    @handleMastodonExceptions
    def getStatus(self, status_id: int) -> Dict:
        return self._api.status(status_id)

    @handleMastodonExceptions
    def getStatusContext(self, status_id: int) -> Dict:
        return self._api.status_context(status_id)

    @handleMastodonExceptions
    def getStatusRebloggedBy(self, status_id: int) -> List[Dict]:
        return self._api.status_reblogged_by(status_id)

    @handleMastodonExceptions
    def getStatusFavouritedBy(self, status_id: int) -> List[Dict]:
        return self._api.status_favourited_by(status_id)

    @handleMastodonExceptions
    def getNotifications(self) -> List[Dict]:
        return self._api.notifications()

    @handleMastodonExceptions
    def getAccountStatuses(self) -> List[Dict]:
        result = self._api.account_statuses(self.getMe().get("id"))
        statuses = []
        while result is not None:
            statuses.extend(result)
            result = self._api.fetch_next(result)
        return statuses

    @handleMastodonExceptions
    def dismissNotification(self, notification_id: int) -> None:
        try:
            self._api.notifications_dismiss(notification_id)
            logging.info(f"📭 \t Notification {notification_id} dismissed")
        except:
            logging.info(f"❗ \t Failed to dismiss Notification: {notification_id}")
            raise

    @handleMastodonExceptions
    def reblogStatus(self, status_id: int):
        """
        Reblog a status using its original status_id as provided by the API

        Parameters
        ----------
        status_id: int
            The id of the status

        Raises
        ------
        None

        Returns
        -------
        None
        """
        try:
            self._api.status_reblog(status_id)
            logging.info(f"🗣️ \t Status reblogged")
        except Exception as e:
            logging.error(f"❗ \t Failed to reblog status")
            raise e

    @handleMastodonExceptions
    def favoriteStatus(self, status_id: int):
        """
        Favorite a status using its original status_id as provided by the API

        Parameters
        ----------
        status_id: int
            The id of the status

        Raises
        ------
        None

        Returns
        -------
        None
        """
        try:
            self._api.status_favourite(status_id)
            logging.info(f"⭐ \t Status favorited")
        except Exception as e:
            logging.error(f"❗ \t Failed to favorite status")
            raise e

    @abstractmethod
    def processMention(self, mention: Dict) -> None:
        ...

    @abstractmethod
    def processReblog(self, reblog: Dict) -> None:
        ...

    @abstractmethod
    def processFavourite(self, favourite: Dict) -> None:
        ...

    @abstractmethod
    def processFollow(self, follow: Dict) -> None:
        ...

    @abstractmethod
    def processPoll(self, poll: Dict) -> None:
        ...

    @abstractmethod
    def processFollowRequest(self, follow_request: Dict) -> None:
        ...

    @abstractmethod
    def processUpdate(self, update: Dict) -> None:
        ...