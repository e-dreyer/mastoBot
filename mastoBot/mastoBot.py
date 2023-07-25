from typing import List, Dict
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


def handleMastodonExceptions(func):
    def wrapper(self, *args, **kwargs):
        try:
            result = func(self, *args, **kwargs)
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
        except MastodonServerError as e:
            logging.critical(f"MastodonServerError: {e}")
        except MastodonVersionError as e:
            logging.critical(f"MastodonVersionError: {e}")
        except Exception as e:
            logging.critical(f"Error in function {func.__name__}")
            raise e

        return result

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
        self.config = config
        self.credentials = credentials

        try:
            self._api = Mastodon(
                access_token=self.credentials.get("access_token"),
                api_base_url=self.credentials.get("api_base_url"),
                request_timeout=self.config.get("api").get("timeout"),
            )
            logging.info("Mastodon API initialized successfully.")
        except Exception as e:
            logging.critical("Failed to initialize Mastodon API: {0}".format(e))
            raise e

    def run(self):
        while True:
            logging.info("Starting run_loop")

            notifications = self._fetch_notifications()
            self._process_notifications(notifications)

            logging.info("Ending run_loop")
            time.sleep(10)

    @handleMastodonExceptions
    def _fetch_notifications(self):
        logging.debug("Starting notification_fetch")
        notifications = self._api.notifications()
        logging.debug(f"Ending notification_fetch: {len(notifications)} Notifications")
        return notifications

    @handleMastodonExceptions
    def _process_notifications(self, notifications: List[Dict]):
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
            else:
                pass

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
        logging.info("Starting account notification fetch")
        result = self._api.account_statuses(self.getMe().get("id"))
        statuses = []
        # Use the received page to get the next page from the API
        while result is not None:
            statuses.extend(result)
            result = self._api.fetch_next(result)

        logging.info(f"Fetched {len(statuses)} statuses")
        return statuses

    @handleMastodonExceptions
    def dismissNotification(self, notification_id: int) -> None:
        self._api.notifications_dismiss(notification_id)

    @handleMastodonExceptions
    def fetchNotifications(self):
        """
        Fetch new notifications from the Mastodon API and add them to the database

        Parameters
        ----------
        None

        Raises
        ------
        None

        Returns
        -------
        None
        """
        try:
            api_new_notifications = self.getNotifications()
            logging.info(
                f"Fetched {len(api_new_notifications)} new notifications from API"
            )
        except Exception as e:
            logging.warning(
                "Failed to fetch new notifications from API"
            )  # ConnectionResetError:
            raise e

        # Process new notifications
        for notification in api_new_notifications:
            try:
                api_user = self.getAccount(notification.get("account").get("id"))
                self.createLocalUser(api_user)  # Add user

                self.createLocalNotification(notification)
                self.dismissNotification(notification.get("id"))  # Dismiss notification

            except Exception as e:
                logging.warning(
                    f"Error while processing {notification.get('type')} notification {notification.get('id')}"
                )
                raise e

        logging.info("Fetch completed")

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
            logging.info(f"Status reblogged: {status_id}")
        except Exception as e:
            logging.error(f"Failed to reblog status: {status_id}")
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
            logging.info(f"Status favorited: {status_id}")
        except Exception as e:
            logging.error(f"Failed to favorite status: {status_id}")
            raise e

    @abstractmethod
    def processMention(mention: Dict):
        ...

    @abstractmethod
    def processReblog(reblog: Dict):
        ...

    @abstractmethod
    def processFavourite(favourite: Dict):
        ...

    @abstractmethod
    def processFollow(follow: Dict):
        ...

    @abstractmethod
    def processPoll(poll: Dict):
        ...

    @abstractmethod
    def processFollowRequest(follow_request: Dict):
        ...
