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
    """
    This is an exception handler that can be used as a wrapper via a decorator to handle Mastodon.py exceptions.
    """
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

    This is class is used to implement Mastodon bots. The class is intended to be inherited 
    and the abstract functions should be implemented to handle notifications and define the behavior of your
    bot.
    
    The ConfigAccessor class is used by MastoBot to import the config and credentials of the user's bot. This
    allows for additional fields to be added to the files without needing a rewrite of the initialization.

    Attributes
    ----------
    config: ConfigAccessor
        The config of the user
    credentials: ConfigAccessor
        The credentials used for API and database access of the user
    """
    def __init__(self, config: ConfigAccessor, credentials: ConfigAccessor) -> None:
        """
        This is the initialization of MastoBot. It takes the config and credentials as parameters

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
        # Config and credentials are imported
        try:
            self.config = config
            self.credentials = credentials
            logging.info("✅ \t Config and credentials initialized")
        except Exception as e:
            logging.info("❌ \t Config and credentials failed to initialized")
            raise e # This exception needs to be raised as it stops the bot from working

        # Initialization of the Mastodon.py API 
        try:
            self._api = Mastodon(
                access_token=self.credentials.get("access_token"),
                api_base_url=self.credentials.get("api_base_url"),
                request_timeout=self.config.get("api", {}).get("timeout", 10),
            )
            logging.info("✅ \t Mastodon.py initialized")
        except Exception as e:
            logging.critical("❌ \t Mastodon.py failed to initialized")
            raise e # This exception needs to be raised as it stops the bot from working

    @handleMastodonExceptions
    def run(self):
        notifications = self._fetch_notifications() # Fetch the notifications
        self._process_notifications(notifications) # Process the notifications

    @handleMastodonExceptions
    def _fetch_notifications(self):
        """
        Fetch the notifications of the bot's account
        """
        notifications = self._api.notifications()
        logging.debug(f"📬 \t {len(notifications)} Notifications fetched")
        return notifications

    @handleMastodonExceptions
    def _process_notifications(self, notifications: List[Dict[Any, Any]]) -> None:
        """
        Process the notifications by type
        """
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
        """
        Get information of the account by id
        
        Parameters
        ----------
        account_id: int
            ID of the account as per the API
        """
        return self._api.account(account_id)

    @handleMastodonExceptions
    def getMe(self) -> Dict:
        """
        Get information of the bot's account
        """
        return self._api.me()

    @handleMastodonExceptions
    def getStatus(self, status_id: int) -> Dict:
        """
        Get the status information as per the API
        
        Parameters
        ----------
        status_id: int
            The ID of the status as provided by the API
        """
        return self._api.status(status_id)

    @handleMastodonExceptions
    def getStatusContext(self, status_id: int) -> Dict:
        """
        Get the context of the Status from 
        """
        return self._api.status_context(status_id)

    @handleMastodonExceptions
    def getStatusRebloggedBy(self, status_id: int) -> List[Dict]:
        """
       Get all of the users that reblogged a Status 
       
       Parameters
       ----------
       status_id: int
            The ID of the status
        """
        return self._api.status_reblogged_by(status_id)

    @handleMastodonExceptions
    def getStatusFavouritedBy(self, status_id: int) -> List[Dict]:
        """
        Get all the users that favourited a Status
        
        Parameters
        ----------
        status_id: int
            The ID of the status
        """
        return self._api.status_favourited_by(status_id)

    @handleMastodonExceptions
    def getNotifications(self) -> List[Dict]:
       """
       Get all notifications from the API
       """ 
       return self._api.notifications()

    @handleMastodonExceptions
    def getAccountStatuses(self) -> List[Dict]:
        """
        Get all account statuses 
        
        # TODO: This needs to be improved to be async or something as it can run for a long time and block everything else
        """
        result = self._api.account_statuses(self.getMe().get("id"))
        statuses = []
        while result is not None:
            statuses.extend(result)
            result = self._api.fetch_next(result)
        return statuses

    @handleMastodonExceptions
    def dismissNotification(self, notification_id: int) -> None:
        """
        Dismiss a notification
        """
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
        
    @handleMastodonExceptions
    def isParentStatus(self, status_id: int) -> bool:
        """
        Check whether a status is a parent or root, i.e it isn't a reply to another post
        
        Parameters
        ----------
        status_id: int
            The ID of the status
        """
        api_status = self.getStatus(status_id)
        in_reply_to_id = api_status.get("in_reply_to_id", None)
        
        if in_reply_to_id:
            return False
        else:
            return True

    @handleMastodonExceptions
    def isByFollower(self, status_id: int) -> bool:
        """
        Check whether a post was made by a follower of the account
        
        Parameters
        ----------
        status_id: int
            The ID of the status
        """
        api_mention = self.getStatus(status_id)
        return self.isFollower(api_mention.get("account")) 

    @handleMastodonExceptions
    def isFollower(self, account_id: int) -> bool:
        """
        Check whether an account is a follower of the bot account
        
        Parameter
        ---------
        account_id: int
            The id of the account
        """
        api_account = self.getAccount(account_id)
        relationships = self._api.account_relationships(api_account.get("id"))
        return relationships[0].get("followed_by", False)
    
    @abstractmethod
    def processMention(self, mention: Dict) -> None:
        """
        Abstract function that should be implemented by the user, which is called for every notification of the type.
        The notification is pass to the function automatically
        
        Parameters
        ----------
        mention: Dict
        
        """
        ...

    @abstractmethod
    def processReblog(self, reblog: Dict) -> None:
        """
        Abstract function that should be implemented by the user, which is called for every notification of the type.
        The notification is pass to the function automatically
        
        Parameters
        ----------
        reblog: Dict
        
        """
        ...

    @abstractmethod
    def processFavourite(self, favourite: Dict) -> None:
        """
        Abstract function that should be implemented by the user, which is called for every notification of the type.
        The notification is pass to the function automatically
        
        Parameters
        ----------
        favourite: Dict
        
        """
        ...

    @abstractmethod
    def processFollow(self, follow: Dict) -> None:
        """
        Abstract function that should be implemented by the user, which is called for every notification of the type.
        The notification is pass to the function automatically
        
        Parameters
        ----------
        follow: Dict
        
        """
        ...

    @abstractmethod
    def processPoll(self, poll: Dict) -> None:
        """
        Abstract function that should be implemented by the user, which is called for every notification of the type.
        The notification is pass to the function automatically
        
        Parameters
        ----------
        poll: Dict
        
        """
        ...

    @abstractmethod
    def processFollowRequest(self, follow_request: Dict) -> None:
        """
        Abstract function that should be implemented by the user, which is called for every notification of the type.
        The notification is pass to the function automatically
        
        Parameters
        ----------
        followe_request: Dict
        
        """
        ...

    @abstractmethod
    def processUpdate(self, update: Dict) -> None:
        """
        Abstract function that should be implemented by the user, which is called for every notification of the type.
        The notification is pass to the function automatically
        
        Parameters
        ----------
        update: Dict
        
        """
        ...