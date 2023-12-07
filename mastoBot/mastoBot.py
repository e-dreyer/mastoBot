#########################################################################
#                               Imports                                 #
#########################################################################
#region Imports
# Import Python logging library
import logging

# Importing default Python libraries
try:
    from typing import Callable, Dict, Any, NewType, TypedDict, Literal
    import asyncio
    from abc import ABC, abstractmethod
    from datetime import datetime
except:
    logging.critical('Failed to load default Python libraries. These are required for the main implementation')
    raise

# Import Jinja2
try:
    from jinja2 import Environment, FileSystemLoader
except:
    logging.critical('Failed to load Jinja2, this is required by the templating system')
    raise

# Import Redis
try:
    import redis
    from redis.commands.json.path import Path
except:
    logging.critical('Failed to import the required Redis libraries. This is required for the database functionality')
    raise

# Import Mastodon.py
try:
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
except:
    logging.critical('Failed to load the Mastodon.py library, which is required for all API calls')
    raise

# Import custom libraries
try:
    from .helpers import *
    from .configManager import *
except:
    logging.critical('Failed to load custom libraries required by the implementation')
    raise

#endregion Imports

#########################################################################
#                               Types                                   #
#########################################################################
#region Types

StatusVisibility = Literal['public', 'unlisted', 'private', 'direct']

#endregion Types

#########################################################################
#                          Exception Handling                           #
#########################################################################
#region ExceptionHandling

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

#endregion ExceptionHandling

#########################################################################
#                               MastoBot                                #
#########################################################################
#region MastoBot

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
            # session = grequests.Session()
            self._api = Mastodon(
                access_token=self.credentials.get("access_token"),
                api_base_url=self.credentials.get("api_base_url"),
                request_timeout=self.config.get("api", {}).get("timeout", 10),
                # session=session
            )
            logging.info("✅ \t Mastodon.py initialized")
        except Exception as e:
            logging.critical("❌ \t Mastodon.py failed to initialized")
            raise e # This exception needs to be raised as it stops the bot from working
        
        try:
            self.r = redis.Redis(host=self.config.get("redis", {}).get("host", "localhost"), port=self.config.get("redis", {}).get("port", 6379), decode_responses=True)
            logging.info("✅ \t Redis initialized")
        except:
            logging.critical("❌ \t Redis failed to initialized")
            raise # This exception needs to be raised as it stops the bot from working

    @handleMastodonExceptions
    async def run(self):
        while True:
            notifications = await self.notificationRefresher() # Fetch the notifications
            self._process_notifications(notifications) # Process the notifications
            await asyncio.sleep(10)

    #region localStoreFunctions
    
    def localStoreSet(self, key: str, id: str, data: dict) -> None:
        """
        Add a key value pair with a json data dict to the local store
        
        Parameters
        ----------
        key: str
            The key of the store, i.e 'notifications'
        id: str
            The ID of the object
        data: dict
            dictionary of the data to store as json
        """
        self.r.json().set(f"{key}:{id}", "$", data)
        
    def localStoreGet(self, key: str, id: str) -> dict:
        """
        Get a key value pair from the local store as a dict
        
        Parameters
        ----------
        key: str
            The key of the stored data
        id: str
            The ID of the stored data

        Returns
        -------
        dict of the stored data
        """
        return self.r.json().get(f"{key}:{id}")
    
    def localStoreMerge(self, key: str, id: str, new_data: dict) -> None:
        """
        Merge the new_data dictionary with the existing data in the data store with the given key
        
        Parameters
        ----------
        key: str
            The key for the local store
        id: str
            The ID for the record in the local store
        new_data: dict
            The new data dictionary to merge with or update local existing data
        """
        current = self.r.json().get(f"{key}:{id}")
        current.update(new_data)
        self.r.json().set(f"{key}:{id}", Path.root_path(), current, decode_keys=True)
        
    def localStoreExists(self, key: str, id: str) -> bool:
        """
        Check whether a key exists
        
        Parameters
        ----------
        key: str
            The key of the data
        id: str
            The ID of the data
        """
        return (self.r.exists(f"{key}:{id}") >= 1)
    
    def localStoreDelete(self, key: str, id: str) -> None:
        """
        Delete a key value pair from the local store
        
        Parameters
        ----------
        key: str
            Key of the stored data
        id: str
            ID of the stored data
        """
        self.r.delete(f"{key}:{id}")
        
    def localStoreKeyGetAll(self, key: str) -> list[str]:
        """
        Get all of the keys matching the pattern
        
        Parameters
        ----------
        key: str
            The key to check, i.e. "notification", "notification:*" will then be returned
            
        Returns
        -------
        List
        """
        keys = []
        cursor = 0
        while True:
            cursor, partial_keys = self.r.scan(cursor, match=f"{key}:*")
            keys.extend(partial_keys)
            if cursor == 0:
                break

        return keys

    def localStoreObjectGetAll(self,key: str) -> list[dict]:
        """
        Get all of the json objects stored with the given key
        
        Parameters
        ----------
        key: str
            The key pattern to check, i.e. "notifications, will then return json data for all "notifications:*"
            
        Returns
        -------
        List
        """
        keys = self.localStoreKeyGetAll(key)
        objects = list()
        for k in keys:
            _key, _id = k.split(":")
            objects.append(self.localStoreGet(_key, _id))
            
        return objects
    
    #endregion localStoreFunctions
    
    #region notificationProcessing
    
    @handleMastodonExceptions
    async def notificationRefresher(self) -> list[dict]:
        """
        Fetch the notifications of the bot's account
        """
        logging.info(f'👀 \t Checking for notifications...')
        notifications = self._api.notifications()
        logging.info(f"📬 \t {len(notifications)} Notifications fetched")
        return notifications

    @handleMastodonExceptions
    def _process_notifications(self, notifications: list[dict[Any, Any]]) -> None:
        """
        Process the notifications by type
        """
        for notification in notifications:
            match notification.get("type"):
                case "mention":
                    self.processMention(notification)
                case "reblog":
                    self.processReblog(notification)
                case "favourite":
                    self.processFavourite(notification)
                case "follow":
                    self.processFollow(notification)
                case "poll":
                    self.processPoll(notification)
                case "follow_request":
                    self.processFollowRequest(notification)
                case "update":
                    self.processUpdate(notification)
                case _:
                    logging.warning(f"❗ \t Invalid notification type: {notification.get('type')}")
          
    #endregion notificationProcessing
         
    #region generalPurposeApiCalls
           
    @handleMastodonExceptions
    def getAccount(self, account_id: int) -> Dict[str, Any]:
        """
        Get information of the account by id
        
        Parameters
        ----------
        account_id: int
            ID of the account as per the API
            
        Returns
        -------
        dict:
            Dictionary of the new account
        """
        return self._api.account(account_id)

    @handleMastodonExceptions
    def getMe(self) -> Dict[str, Any]:
        """
        Get information of the bot's account
        
        Returns
        -------
        dict:
            Dictionary of the bot's account
        """
        return self._api.me()

    @handleMastodonExceptions
    def getStatus(self, status_id: int) -> Dict[str, Any]:
        """
        Get the status information as per the API
        
        Parameters
        ----------
        status_id: int
            The ID of the status as provided by the API
            
        Returns
        -------
        dict:
            Dictionary of the status
        """
        return self._api.status(status_id)

    @handleMastodonExceptions
    def getStatusRebloggedBy(self, status_id: int) -> list[Dict[str, Any]]:
        """
       Get all of the users that reblogged a Status 
       
       Parameters
       ----------
       status_id: int
            The ID of the status
        """
        return self._api.status_reblogged_by(status_id)

    @handleMastodonExceptions
    def getStatusFavouritedBy(self, status_id: int) -> list[Dict[str, Any]]:
        """
        Get all the users that favourited a Status
        
        Parameters
        ----------
        status_id: int
            The ID of the status
        """
        return self._api.status_favourited_by(status_id)

    @handleMastodonExceptions
    def getNotifications(self) -> list[Dict[str, Any]]:
       """
       Get all notifications from the API
       """ 
       return self._api.notifications()

    @handleMastodonExceptions
    def getAccountStatuses(self) -> list[Dict[str, Any]]:
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
            logging.info(f"⭐ \t Status favourited")
        except Exception as e:
            logging.error(f"❗ \t Failed to favorite status")
            raise e
      
    #endregion generalPurposeApiCalls
      
    #region helperFunctions
      
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
    
    def getTemplate(self, file_name: str, data: dict) -> str:
        """
        Render the Jinja2 template in the file with file_name using the provided data and 
        return a string
        
        Parameters
        ----------
        file_name: str
            The name of the Jinja2 file in the ./templates directory
        data: dict
            dictionary containing the data to be used by the template
            
        Returns
        -------
        AnyStr rendered template
        """
        try:
            file_loader = FileSystemLoader("templates")
            env = Environment(loader=file_loader)
            template = env.get_template(file_name)
            output = template.render(**data)
        except Exception as e:
            logging.critical("❗ \t Error initializing template")
            raise e

        return output
    
    @handleMastodonExceptions
    def shouldReblog(self, status_id: int) -> bool:
        boostConfig = self.config["boosts"]
        
        isFollower = self.isByFollower(status_id)
        isFollowerRequired = boostConfig.get("followers_only")
        
        isParent = self.isParentStatus(status_id)
        isParentRequired = boostConfig.get("parents_only")
        
        containsMedia = self.containsMedia(status_id)
        hasAltText = self.containsAltText(status_id)
        altTextRequired = boostConfig.get("alt_text_required")
        
        logging.info(f"isFollowerRequired: {isFollowerRequired} isFollower: {isFollower}")
        if isFollowerRequired and not isFollower:
            return False
        
        logging.info(f"isParentRequired: {isParentRequired} isParent: {isParent}")
        if isParentRequired and not isParent:
            return False
        
        logging.info(f"containsMedia: {containsMedia} altTextRequired: {altTextRequired} hasAltText: {hasAltText}")
        if containsMedia and altTextRequired:
            return hasAltText
        
        return True

    @handleMastodonExceptions
    def shouldFavorite(self, status_id: int) -> bool:
        favouriteConfig = self.config["favourites"]
        
        isFollower = self.isByFollower(status_id)
        isFollowerRequired = favouriteConfig.get("followers_only")
        
        isParent = self.isParentStatus(status_id)
        isParentRequired = favouriteConfig.get("parents_only")
        
        containsMedia = self.containsMedia(status_id)
        hasAltText = self.containsAltText(status_id)
        altTextRequired = favouriteConfig.get("alt_text_required")
        
        logging.info(f"isFollowerRequired: {isFollowerRequired} isFollower: {isFollower}")
        if isFollowerRequired and not isFollower:
            return False
        
        logging.info(f"isParentRequired: {isParentRequired} isParent: {isParent}")
        if isParentRequired and not isParent:
            return False
        
        logging.info(f"containsMedia: {containsMedia} altTextRequired: {altTextRequired} hasAltText: {hasAltText}")
        if containsMedia and altTextRequired:
            return hasAltText
        
        return True
    
    @handleMastodonExceptions
    def containsMedia(self, status_id: int) -> bool:
        api_status = self.getStatus(status_id)
        media_attachments = api_status.get('media_attachments', list())
        return len(media_attachments) > 0
    
    @handleMastodonExceptions
    def containsAltText(self, status_id: int) -> bool:
        if not self.containsMedia(status_id):
            return False
        
        api_status = self.getStatus(status_id)
        media_attachments = api_status.get('media_attachments', list())
        
        for media_attachment in media_attachments:
            description = media_attachment.get('description', None)
            if not description:
                return False
            
        return True
    
    @handleMastodonExceptions
    def altTextTestPassed(self, status_id: int, config: str) -> bool:
        containsMedia = self.containsMedia(status_id)
        hasAltText = self.containsAltText(status_id)
        altTextRequired = self.config[config].get("alt_text_required")
        
        if containsMedia and altTextRequired:
            return hasAltText
        
        return True
       
    #endregion helperFunctions
         
    #region processingAbstractMethods
    
    @abstractmethod
    def processMention(self, mention: dict) -> None:
        """
        Abstract function that should be implemented by the user, which is called for every notification of the type.
        The notification is pass to the function automatically
        
        Parameters
        ----------
        mention: dict
        
        """
        ...

    @abstractmethod
    def processReblog(self, reblog: dict) -> None:
        """
        Abstract function that should be implemented by the user, which is called for every notification of the type.
        The notification is pass to the function automatically
        
        Parameters
        ----------
        reblog: dict
        
        """
        ...

    @abstractmethod
    def processFavourite(self, favourite: dict) -> None:
        """
        Abstract function that should be implemented by the user, which is called for every notification of the type.
        The notification is pass to the function automatically
        
        Parameters
        ----------
        favourite: dict
        
        """
        ...

    @abstractmethod
    def processFollow(self, follow: dict) -> None:
        """
        Abstract function that should be implemented by the user, which is called for every notification of the type.
        The notification is pass to the function automatically
        
        Parameters
        ----------
        follow: dict
        
        """
        ...

    @abstractmethod
    def processPoll(self, poll: dict) -> None:
        """
        Abstract function that should be implemented by the user, which is called for every notification of the type.
        The notification is pass to the function automatically
        
        Parameters
        ----------
        poll: dict
        
        """
        ...

    @abstractmethod
    def processFollowRequest(self, follow_request: dict) -> None:
        """
        Abstract function that should be implemented by the user, which is called for every notification of the type.
        The notification is pass to the function automatically
        
        Parameters
        ----------
        follow_request: dict
        
        """
        ...

    @abstractmethod
    def processUpdate(self, update: dict) -> None:
        """
        Abstract function that should be implemented by the user, which is called for every notification of the type.
        The notification is pass to the function automatically
        
        Parameters
        ----------
        update: dict
        
        """
        ...
    #endregion processingAbstractMethods
#endregion MastoBot